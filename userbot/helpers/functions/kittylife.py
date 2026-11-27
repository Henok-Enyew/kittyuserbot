# Live "life signals" shared by the Kitty pet (plugins/kitty.py) and the living
# profile photo (plugins/livepfp.py).
#
#   presence  — are you awake on Telegram right now? (your real online status,
#               plus the time of your last outgoing message)
#   weather   — current weather in Addis Ababa from Open-Meteo (free, no key)
#   leetcode  — accepted problems today (LeetCode's UTC day) and current streak
#
# Every fetch is cached and never raises: on a network error the last good value
# is reused, so a flaky API can't crash a scheduler tick or blank the scene.
from __future__ import annotations

import asyncio
import json
import math
import time
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import httpx

from .digest_builder import ADDIS_TZ, addis_now
from .leetcode_checker import (
    LC_GRAPHQL_URL,
    LC_HEADERS,
    _leetcode_username,
    fetch_recent_submissions,
    leetcode_today,
)

ADDIS_LAT, ADDIS_LON = 9.03, 38.74
METEO_URL = "https://api.open-meteo.com/v1/forecast"

AWAKE_WINDOW_MIN = 15  # online within the last N minutes counts as awake
WEATHER_TTL = 20 * 60
LEETCODE_TTL = 5 * 60
PRESENCE_TTL = 60

# Night-owl hours (Addis time): being awake now makes Kitty fall asleep on the keyboard.
NIGHT_OWL_HOURS = (2, 3, 4)


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #


@dataclass
class Weather:
    kind: str = "clear"  # clear | cloudy | fog | drizzle | rain | storm
    temp_c: Optional[float] = None
    cloud: int = 0  # cloud cover %
    is_day: bool = True
    ok: bool = False  # False until the first successful fetch

    @property
    def wet(self) -> bool:
        return self.kind in ("drizzle", "rain", "storm")

    @property
    def emoji(self) -> str:
        return {"clear": "☀️" if self.is_day else "🌙", "cloudy": "☁️", "fog": "🌫",
                "drizzle": "🌦", "rain": "🌧", "storm": "⛈"}[self.kind]


@dataclass
class LeetCode:
    day: str = ""  # the LeetCode (UTC) day these numbers are for, ISO date
    solved_today: int = 0  # unique accepted problems on that day
    titles: list = field(default_factory=list)
    streak: int = 0  # consecutive active days, alive if today or yesterday counts
    active_days: list = field(default_factory=list)  # ISO dates, newest last
    full: bool = False  # streak came from LeetCode's full calendar (not just the last 20 solves)
    ok: bool = False


@dataclass
class Presence:
    awake: bool = False
    minutes_ago: Optional[int] = None  # minutes since you were last online
    source: str = "unknown"  # "online" | "last seen" | "message" | "unknown"


@dataclass
class Signals:
    now: datetime
    presence: Presence
    weather: Weather
    leetcode: LeetCode

    @property
    def night_owl(self) -> bool:
        """Awake on Telegram during the small hours (02:00-04:59 Addis)."""
        return self.presence.awake and self.now.hour in NIGHT_OWL_HOURS

    def as_dict(self) -> dict:
        return {"now": self.now.isoformat(), "presence": asdict(self.presence),
                "weather": asdict(self.weather), "leetcode": asdict(self.leetcode)}


# --------------------------------------------------------------------------- #
# Activity from your own outgoing messages (fed by the plugins' event handler)
# --------------------------------------------------------------------------- #

_last_outgoing: float = 0.0


def note_outgoing(ts: Optional[float] = None) -> None:
    """Record that you just sent a message (call from an outgoing NewMessage handler)."""
    global _last_outgoing
    _last_outgoing = ts or time.time()


# --------------------------------------------------------------------------- #
# Fetchers (cached, never raise)
# --------------------------------------------------------------------------- #

_cache: dict = {}
_locks: dict = {}


def _lock(name: str) -> asyncio.Lock:
    if name not in _locks:
        _locks[name] = asyncio.Lock()
    return _locks[name]


def _fresh(name: str, ttl: int):
    hit = _cache.get(name)
    return hit[1] if hit and time.time() - hit[0] < ttl else None


def _stale(name: str):
    hit = _cache.get(name)
    return hit[1] if hit else None


def _weather_kind(code: int, cloud: int) -> str:
    """WMO weather code -> one of our scene kinds."""
    if code >= 95:
        return "storm"
    if code in (61, 63, 65, 66, 67, 80, 81, 82):
        return "rain"
    if code in (51, 53, 55, 56, 57):
        return "drizzle"
    if code in (45, 48):
        return "fog"
    if code in (2, 3) or cloud >= 60:
        return "cloudy"
    return "clear"


async def get_weather(force: bool = False) -> Weather:
    if not force and (hit := _fresh("weather", WEATHER_TTL)):
        return hit
    async with _lock("weather"):
        if not force and (hit := _fresh("weather", WEATHER_TTL)):
            return hit
        try:
            params = {"latitude": ADDIS_LAT, "longitude": ADDIS_LON,
                      "current": "temperature_2m,weather_code,cloud_cover,is_day",
                      "timezone": "Africa/Addis_Ababa"}
            async with httpx.AsyncClient(timeout=15) as http:
                r = await http.get(METEO_URL, params=params)
                r.raise_for_status()
                cur = r.json()["current"]
            cloud = int(cur.get("cloud_cover") or 0)
            w = Weather(kind=_weather_kind(int(cur.get("weather_code") or 0), cloud),
                        temp_c=cur.get("temperature_2m"), cloud=cloud,
                        is_day=bool(cur.get("is_day", 1)), ok=True)
            _cache["weather"] = (time.time(), w)
            return w
        except Exception:
            return _stale("weather") or Weather()


_CALENDAR_QUERY = """
query userCalendar($username: String!) {
  matchedUser(username: $username) {
    userCalendar { streak totalActiveDays submissionCalendar }
  }
}
"""


def _calendar_days(username: str) -> set:
    """UTC dates with at least one submission, from LeetCode's yearly calendar."""
    import requests

    resp = requests.post(LC_GRAPHQL_URL, headers=LC_HEADERS, timeout=20,
                         json={"query": _CALENDAR_QUERY, "variables": {"username": username}})
    resp.raise_for_status()
    user = (resp.json().get("data") or {}).get("matchedUser") or {}
    raw = (user.get("userCalendar") or {}).get("submissionCalendar") or "{}"
    cal = json.loads(raw) if isinstance(raw, str) else raw
    return {datetime.fromtimestamp(int(ts), timezone.utc).date() for ts, n in cal.items() if int(n) > 0}


def current_streak(days: set, today: date) -> int:
    """Consecutive active days ending today, or yesterday if today isn't done yet."""
    day = today if today in days else today - timedelta(days=1)
    streak = 0
    while day in days:
        streak += 1
        day -= timedelta(days=1)
    return streak


def _fetch_leetcode_sync(extra_days: set) -> LeetCode:
    username = _leetcode_username()
    today = leetcode_today()
    subs = fetch_recent_submissions(username=username, limit=20)
    titles, seen = [], set()
    ac_days = set()
    for s in subs:
        try:
            d = datetime.fromtimestamp(int(s.get("timestamp")), timezone.utc).date()
        except (TypeError, ValueError):
            continue
        ac_days.add(d)
        slug = s.get("titleSlug") or s.get("title")
        if d == today and slug not in seen:
            seen.add(slug)
            titles.append(str(s.get("title") or slug))
    try:
        days, full = _calendar_days(username), True
    except Exception:
        days, full = set(), False  # recent submissions + our own record still give a streak
    days |= ac_days | extra_days
    recent = sorted(d for d in days if d >= today - timedelta(days=400))
    return LeetCode(day=today.isoformat(), solved_today=len(titles), titles=titles, streak=current_streak(days, today),
                    active_days=[d.isoformat() for d in recent[-60:]], full=full, ok=True)


async def get_leetcode(force: bool = False, extra_days: Optional[set] = None) -> LeetCode:
    """`extra_days`: dates you're known to have solved on (kept by the pet), so a
    streak survives even if LeetCode's calendar endpoint is down."""
    if not force and (hit := _fresh("leetcode", LEETCODE_TTL)):
        return hit
    async with _lock("leetcode"):
        if not force and (hit := _fresh("leetcode", LEETCODE_TTL)):
            return hit
        try:
            lc = await asyncio.to_thread(_fetch_leetcode_sync, set(extra_days or ()))
            _cache["leetcode"] = (time.time(), lc)
            return lc
        except Exception:
            old = _stale("leetcode")
            if old and old.ok and old.day != leetcode_today().isoformat():
                old.day = leetcode_today().isoformat()  # a new LeetCode day began since the last good fetch
                old.solved_today = 0
                old.titles = []
            return old or LeetCode()


async def get_presence(client, force: bool = False) -> Presence:
    if not force and (hit := _fresh("presence", PRESENCE_TTL)):
        return hit
    from telethon.tl import functions, types

    minutes, source = None, "unknown"
    try:
        users = await client(functions.users.GetUsersRequest(id=[types.InputUserSelf()]))
        status = users[0].status if users else None
        if isinstance(status, types.UserStatusOnline):
            minutes, source = 0, "online"
        elif isinstance(status, types.UserStatusOffline) and status.was_online:
            was = status.was_online
            if was.tzinfo is None:
                was = was.replace(tzinfo=timezone.utc)
            minutes = max(0, int((datetime.now(timezone.utc) - was).total_seconds() // 60))
            source = "last seen"
    except Exception:
        pass
    if _last_outgoing:
        msg_min = int((time.time() - _last_outgoing) // 60)
        if minutes is None or msg_min < minutes:
            minutes, source = msg_min, "message"
    p = Presence(awake=minutes is not None and minutes <= AWAKE_WINDOW_MIN, minutes_ago=minutes, source=source)
    _cache["presence"] = (time.time(), p)
    return p


async def get_signals(client, force: bool = False, extra_days: Optional[set] = None) -> Signals:
    """All three signals at once (fetched concurrently)."""
    presence, weather, leetcode = await asyncio.gather(
        get_presence(client, force), get_weather(force), get_leetcode(force, extra_days)
    )
    return Signals(now=addis_now(), presence=presence, weather=weather, leetcode=leetcode)


# --------------------------------------------------------------------------- #
# Sky helpers (Addis is near the equator: sunrise ~06:15, sunset ~18:30 all year)
# --------------------------------------------------------------------------- #


def sky_phase(now: datetime) -> str:
    """night | dawn | day | dusk, from Addis local time."""
    h = now.astimezone(ADDIS_TZ).hour + now.astimezone(ADDIS_TZ).minute / 60
    if 5.75 <= h < 7:
        return "dawn"
    if 7 <= h < 17.75:
        return "day"
    if 17.75 <= h < 19.25:
        return "dusk"
    return "night"


_NEW_MOON = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
_SYNODIC = 29.530588853


def moon_phase(now: datetime) -> float:
    """0 = new moon, 0.5 = full moon, back to 1."""
    days = (now.astimezone(timezone.utc) - _NEW_MOON).total_seconds() / 86400
    return (days / _SYNODIC) % 1.0


def moon_name(phase: float) -> str:
    names = ["new moon", "waxing crescent", "first quarter", "waxing gibbous",
             "full moon", "waning gibbous", "last quarter", "waning crescent"]
    return names[int(math.floor(phase * 8 + 0.5)) % 8]
