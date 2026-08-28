# Football data helpers — API-Football (api-sports) + football-data.org v4.
#
# Commands: .fball / .afball (API_FOOTBALL_KEY), .fdata / .ffdata (FOOTBALL_DATA_API_KEY)
# Help text: build_fball_help(), build_fballset_help() — used by plugins/football.py for .help
from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import httpx

from ...Config import Config

APISPORTS_BASE = "https://v3.football.api-sports.io"
FDATA_BASE = "https://api.football-data.org/v4"

MAX_MATCHES_REPLY = 20

# Major leagues only (default) — England, Germany, Spain, Italy, Champions League
MAJOR_APISPORTS_LEAGUE_IDS = frozenset({39, 2, 140, 78, 135})  # PL, UCL, La Liga, Bundesliga, Serie A
MAJOR_FDATA_CODES = frozenset({"PL", "CL", "PD", "BL1", "SA"})
MAJOR_LEAGUE_CODES = ("PL", "UCL", "PD", "BL1", "SA")

# API-Football free tier season window (team queries only; not used for live/today)
def _apisports_season_bounds() -> Tuple[int, int]:
    try:
        lo = int(
            os.environ.get("API_FOOTBALL_FREE_SEASON_MIN")
            or getattr(Config, "API_FOOTBALL_FREE_SEASON_MIN", 2022)
        )
        hi = int(
            os.environ.get("API_FOOTBALL_FREE_SEASON_MAX")
            or getattr(Config, "API_FOOTBALL_FREE_SEASON_MAX", 2024)
        )
    except (TypeError, ValueError):
        lo, hi = 2022, 2024
    return lo, hi

# football-data.org competition codes
FDATA_LEAGUE_CODES = {
    "PL": "PL",
    "EPL": "PL",
    "PREMIER": "PL",
    "UCL": "CL",
    "CL": "CL",
    "UEL": "EL",
    "EL": "EL",
    "LALIGA": "PD",
    "PD": "PD",
    "BUNDESLIGA": "BL1",
    "BL1": "BL1",
    "SERIEA": "SA",
    "SA": "SA",
    "LIGUE1": "FL1",
    "FL1": "FL1",
}

# API-Sports league id shortcuts
APISPORTS_LEAGUE_IDS = {
    "PL": 39,
    "EPL": 39,
    "UCL": 2,
    "CL": 2,
    "UEL": 3,
    "EL": 3,
    "PD": 140,
    "LALIGA": 140,
    "BL1": 78,
    "SA": 135,
    "FL1": 61,
}


@dataclass
class MatchSnapshot:
    home: str
    away: str
    home_goals: Optional[int]
    away_goals: Optional[int]
    status: str  # LIVE, SCHEDULED, FINISHED, etc.
    competition: str
    kickoff: Optional[datetime] = None
    minute: Optional[str] = None
    league_id: Optional[int] = None
    league_code: str = ""

    @property
    def is_live(self) -> bool:
        return self.status.upper() in {"LIVE", "IN_PLAY", "PAUSED", "1H", "2H", "HT", "ET", "P"}

    @property
    def is_finished(self) -> bool:
        return self.status.upper() in {"FINISHED", "FT", "AET", "PEN"}

    @property
    def is_scheduled(self) -> bool:
        return self.status.upper() in {"SCHEDULED", "TIMED", "NS", "TBD", "NOT_STARTED"}


@dataclass
class Trophy:
    name: str
    count: int
    seasons: List[str] = field(default_factory=list)


@dataclass
class FootballQuery:
    mode: str
    days: int = 3
    team_name: str = ""
    season: Optional[int] = None
    league: str = ""


@dataclass
class TeamFootballReport:
    team_name: str
    recent: List[MatchSnapshot] = field(default_factory=list)
    upcoming: List[MatchSnapshot] = field(default_factory=list)
    trophies: List[Trophy] = field(default_factory=list)
    trophies_note: str = ""


# Simple TTL cache: key -> (expires, value)
_CACHE: Dict[str, Tuple[float, Any]] = {}


def _cache_get(key: str) -> Any:
    item = _CACHE.get(key)
    if not item:
        return None
    if time.time() > item[0]:
        _CACHE.pop(key, None)
        return None
    return item[1]


def _cache_set(key: str, value: Any, ttl: int) -> None:
    _CACHE[key] = (time.time() + ttl, value)


def _tz() -> ZoneInfo:
    try:
        return ZoneInfo(getattr(Config, "TZ", None) or "UTC")
    except Exception:
        return ZoneInfo("UTC")


def _today() -> date:
    return datetime.now(_tz()).date()


def _api_football_key() -> Optional[str]:
    for source in (
        os.environ.get("API_FOOTBALL_KEY"),
        getattr(Config, "API_FOOTBALL_KEY", None),
    ):
        if source and str(source).strip().lower() not in {"", "none", "null"}:
            return str(source).strip()
    return None


def _fdata_key() -> Optional[str]:
    for source in (
        os.environ.get("FOOTBALL_DATA_API_KEY"),
        getattr(Config, "FOOTBALL_DATA_API_KEY", None),
    ):
        if source and str(source).strip().lower() not in {"", "none", "null"}:
            return str(source).strip()
    return None


def _current_season() -> int:
    today = _today()
    return today.year if today.month >= 7 else today.year - 1


def _clamp_apisports_season(season: Optional[int]) -> int:
    """Keep season inside API-Football free-plan range (team/history queries)."""
    lo, hi = _apisports_season_bounds()
    s = season or _current_season()
    if s > hi:
        return hi
    if s < lo:
        return lo
    return s


def _major_only_enabled() -> bool:
    raw = os.environ.get("FBALL_MAJOR_ONLY", getattr(Config, "FBALL_MAJOR_ONLY", "true"))
    return str(raw).strip().lower() not in {"0", "false", "no", "off"}


def _name_is_major_competition(name: str) -> bool:
    n = (name or "").lower()
    if not n:
        return False
    # Avoid English Championship, regional leagues, etc.
    if "championship" in n and "champions league" not in n:
        return False
    markers = (
        "premier league",
        "bundesliga",
        "la liga",
        "serie a",
        "uefa champions league",
        "champions league",
    )
    return any(m in n for m in markers)


def _is_major_apisports_match(match: MatchSnapshot) -> bool:
    if match.league_id is not None:
        return match.league_id in MAJOR_APISPORTS_LEAGUE_IDS
    return _name_is_major_competition(match.competition)


def _is_major_fdata_match(match: MatchSnapshot) -> bool:
    if match.league_code:
        return match.league_code.upper() in MAJOR_FDATA_CODES
    return _name_is_major_competition(match.competition)


def _filter_major_matches(
    matches: List[MatchSnapshot], provider: str = "apisports"
) -> List[MatchSnapshot]:
    if not _major_only_enabled():
        return matches
    fn = _is_major_fdata_match if provider == "fdata" else _is_major_apisports_match
    return [m for m in matches if fn(m)]


def parse_football_args(raw: str, gvars: dict) -> FootballQuery:
    text = (raw or "").strip()
    if not text:
        return FootballQuery(mode="today")

    parts = text.split(maxsplit=1)
    mode = parts[0].lower()
    rest = parts[1].strip() if len(parts) > 1 else ""

    default_up = int(gvars.get("FBALL_UP_DAYS") or 3)
    default_past = int(gvars.get("FBALL_PAST_DAYS") or 3)
    default_league = gvars.get("FBALL_LEAGUE") or getattr(
        Config, "FBALL_DEFAULT_LEAGUE", None
    ) or ""

    if mode in {"live", "today"}:
        return FootballQuery(mode=mode, league=default_league)

    if mode in {"up", "upcoming"}:
        days = default_up
        if rest.isdigit():
            days = int(rest)
        return FootballQuery(mode="up", days=max(1, min(days, 14)), league=default_league)

    if mode in {"past", "results"}:
        days = default_past
        if rest.isdigit():
            days = int(rest)
        return FootballQuery(
            mode="past", days=max(1, min(days, 30)), league=default_league
        )

    if mode == "team":
        season = None
        name = rest
        m = re.match(r"^(.+?)\s+(\d{4})$", rest)
        if m:
            name, season = m.group(1).strip(), int(m.group(2))
        return FootballQuery(mode="team", team_name=name, season=season)

    if mode == "league":
        league = rest or default_league
        return FootballQuery(mode="league", league=league)

    # default: treat whole string as today with note — or league filter
    return FootballQuery(mode="today", league=default_league)


def _status_emoji(match: MatchSnapshot) -> str:
    if match.is_live:
        return "🔴"
    if match.is_finished:
        return "✅"
    return "🕐"


def _score_or_time(match: MatchSnapshot, tz: ZoneInfo) -> str:
    if match.is_live and match.home_goals is not None and match.away_goals is not None:
        base = f"{match.home_goals} - {match.away_goals}"
        if match.minute:
            return f"{base} ({match.minute}')"
        return base
    if match.is_finished and match.home_goals is not None and match.away_goals is not None:
        return f"{match.home_goals} - {match.away_goals}"
    if match.kickoff:
        return match.kickoff.astimezone(tz).strftime("%H:%M")
    return "vs"


def format_matches(
    matches: List[MatchSnapshot],
    title: str,
    tz: Optional[ZoneInfo] = None,
) -> str:
    tz = tz or _tz()
    if not matches:
        return f"**{title}**\n_No matches found._"

    live = [m for m in matches if m.is_live]
    upcoming = [m for m in matches if m.is_scheduled]
    finished = [m for m in matches if m.is_finished]
    other = [m for m in matches if m not in live + upcoming + finished]

    lines = [f"**{title}**"]
    total = len(matches)
    shown = 0
    overflow = 0

    def _section(label: str, items: List[MatchSnapshot]) -> None:
        nonlocal shown, overflow
        if not items:
            return
        lines.append(f"\n**{label}** ({len(items)})")
        for m in items:
            if shown >= MAX_MATCHES_REPLY:
                overflow += 1
                continue
            ko = ""
            if m.kickoff:
                ko = m.kickoff.astimezone(tz).strftime("%d %b %H:%M")
            lines.append(
                f"{_status_emoji(m)} **{m.home}** {_score_or_time(m, tz)} **{m.away}**"
                f" — {m.competition}" + (f" ({ko})" if ko else "")
            )
            shown += 1

    _section("LIVE", live)
    _section("UPCOMING", upcoming)
    _section("RESULTS", finished)
    _section("OTHER", other)

    if overflow:
        lines.append(
            f"\n_+{overflow} more — narrow with `league` or fewer days._"
        )
    lines.append(f"\n_Total: {total} match(es)_")
    return "\n".join(lines)


def format_team_report(report: TeamFootballReport, tz: Optional[ZoneInfo] = None) -> str:
    tz = tz or _tz()
    parts = [f"**Team — {report.team_name}**"]

    if report.recent:
        parts.append("\n**Last results**")
        for m in report.recent[:5]:
            parts.append(
                f"✅ **{m.home}** {_score_or_time(m, tz)} **{m.away}** — {m.competition}"
            )
    if report.upcoming:
        parts.append("\n**Next fixtures**")
        for m in report.upcoming[:5]:
            ko = m.kickoff.astimezone(tz).strftime("%d %b %H:%M") if m.kickoff else "TBD"
            parts.append(
                f"🕐 **{m.home}** vs **{m.away}** — {m.competition} ({ko})"
            )

    parts.append("\n**Honours**")
    if report.trophies:
        for t in report.trophies[:12]:
            extra = f" ({', '.join(t.seasons[:3])})" if t.seasons else ""
            parts.append(f"🏆 {t.name}: **{t.count}**{extra}")
    else:
        parts.append(report.trophies_note or "_No trophy data returned._")

    return "\n".join(parts)


# ─── API-Sports (API-Football) ───────────────────────────────────────────────


async def _apisports_get(path: str, params: dict) -> Any:
    key = _api_football_key()
    if not key:
        raise ValueError(
            "API_FOOTBALL_KEY is not set. Get a key at https://www.api-football.com/"
        )
    cache_key = f"apisports:{path}:{params}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    url = f"{APISPORTS_BASE}/{path.lstrip('/')}"
    headers = {"x-apisports-key": key}
    async with httpx.AsyncClient(timeout=25, follow_redirects=True) as client:
        r = await client.get(url, params=params, headers=headers)
        data = r.json()

    if r.status_code == 429:
        raise RuntimeError("API-Football rate limit (429). Try again later.")
    if r.status_code != 200:
        raise RuntimeError(f"API-Football HTTP {r.status_code}: {data}")

    errors = data.get("errors") or {}
    if errors:
        raise RuntimeError(f"API-Football error: {errors}")

    ttl = 60 if params.get("live") else 600
    _cache_set(cache_key, data, ttl)
    return data


def _parse_apisports_fixture(item: dict) -> MatchSnapshot:
    fixture = item.get("fixture") or {}
    league = item.get("league") or {}
    teams = item.get("teams") or {}
    goals = item.get("goals") or {}
    status = fixture.get("status") or {}

    kickoff = None
    if fixture.get("date"):
        try:
            kickoff = datetime.fromisoformat(
                fixture["date"].replace("Z", "+00:00")
            )
        except ValueError:
            pass

    return MatchSnapshot(
        home=(teams.get("home") or {}).get("name") or "?",
        away=(teams.get("away") or {}).get("name") or "?",
        home_goals=goals.get("home"),
        away_goals=goals.get("away"),
        status=(status.get("short") or status.get("long") or "NS"),
        competition=(league.get("name") or league.get("country") or "League"),
        kickoff=kickoff,
        minute=status.get("elapsed") and f"{status['elapsed']}",
        league_id=league.get("id"),
    )


async def _apisports_fixtures(params: dict) -> List[MatchSnapshot]:
    data = await _apisports_get("fixtures", params)
    items = data.get("response") or []
    return [_parse_apisports_fixture(i) for i in items]


def _apisports_league_param(league: str) -> dict:
    """League id filter only — do not attach season (breaks live/today on free tier)."""
    if not league:
        return {}
    league = league.strip().upper()
    if league.isdigit():
        return {"league": int(league)}
    lid = APISPORTS_LEAGUE_IDS.get(league)
    if lid:
        return {"league": lid}
    return {}


async def apisports_live(league: str = "") -> List[MatchSnapshot]:
    params = {"live": "all", **_apisports_league_param(league)}
    matches = await _apisports_fixtures(params)
    if league and not params.get("league"):
        key = league.lower()
        matches = [
            m
            for m in matches
            if key in m.competition.lower()
        ]
    return _filter_major_matches(matches, "apisports")


async def apisports_today(league: str = "") -> List[MatchSnapshot]:
    params = {"date": _today().isoformat(), **_apisports_league_param(league)}
    return _filter_major_matches(await _apisports_fixtures(params), "apisports")


async def apisports_range(
    start: date, end: date, league: str = "", status: Optional[str] = None
) -> List[MatchSnapshot]:
    params = {
        "from": start.isoformat(),
        "to": end.isoformat(),
        **_apisports_league_param(league),
    }
    if status:
        params["status"] = status
    matches = await _apisports_fixtures(params)
    return _filter_major_matches(matches, "apisports")


async def apisports_upcoming(days: int, league: str = "") -> List[MatchSnapshot]:
    start = _today()
    end = start + timedelta(days=days)
    matches = await apisports_range(start, end, league=league)
    return [m for m in matches if m.is_scheduled or not m.is_finished]


async def apisports_past(days: int, league: str = "") -> List[MatchSnapshot]:
    end = _today()
    start = end - timedelta(days=days)
    matches = await apisports_range(start, end, league=league)
    return [m for m in matches if m.is_finished]


async def _apisports_find_team(name: str) -> Optional[dict]:
    cache_key = f"apisports:team:{name.lower()}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    data = await _apisports_get("teams", {"search": name})
    items = data.get("response") or []
    if not items:
        return None
    name_l = name.lower()

    def _team_major(item: dict) -> bool:
        team = item.get("team") or {}
        country = (team.get("country") or "").lower()
        # Prefer teams from major European leagues
        return country in {"england", "germany", "spain", "italy", "france"}

    ranked = sorted(
        items,
        key=lambda i: (
            0 if name_l in ((i.get("team") or {}).get("name") or "").lower() else 1,
            0 if _team_major(i) else 1,
        ),
    )
    team = (ranked[0].get("team") or {})
    _cache_set(cache_key, team, 3600)
    return team


async def _apisports_team_fixtures(tid: int, season: Optional[int]) -> List[MatchSnapshot]:
    """Fetch team fixtures; clamp season and retry within free-tier window."""
    wanted = _clamp_apisports_season(season)
    seasons_to_try = [wanted]
    lo, hi = _apisports_season_bounds()
    for s in range(hi, lo - 1, -1):
        if s not in seasons_to_try:
            seasons_to_try.append(s)

    for try_season in seasons_to_try:
        try:
            fixtures = await _apisports_fixtures(
                {"team": tid, "season": try_season, "last": 40}
            )
            major = _filter_major_matches(fixtures, "apisports")
            if major:
                return major
            if fixtures and not _major_only_enabled():
                return fixtures
        except RuntimeError as e:
            err = str(e).lower()
            if "season" in err or "plan" in err:
                continue
            raise
    return []


async def apisports_team_report(name: str, season: Optional[int] = None) -> TeamFootballReport:
    team = await _apisports_find_team(name)
    if not team:
        raise ValueError(f"Team not found: {name}")
    tid = team.get("id")
    used_season = _clamp_apisports_season(season)
    fixtures = await _apisports_team_fixtures(tid, season)
    recent = [m for m in fixtures if m.is_finished][-5:]
    upcoming = [m for m in fixtures if m.is_scheduled][:5]

    trophies: List[Trophy] = []
    note_parts: List[str] = []
    requested_season = season if season is not None else _current_season()
    if used_season != requested_season:
        note_parts.append(
            f"Using season {used_season} (API-Football free tier: "
            f"{_apisports_season_bounds()[0]}–{_apisports_season_bounds()[1]})."
        )
    if _major_only_enabled():
        note_parts.append(
            "Major leagues only: PL, Bundesliga, La Liga, Serie A, UCL."
        )
    try:
        tdata = await _apisports_get("trophies", {"team": tid})
        counts: dict = {}
        seasons_map: dict = {}
        for entry in tdata.get("response") or []:
            if not isinstance(entry, dict):
                continue
            place = (entry.get("place") or "").lower()
            if place and place not in {"winner", "1st", "champion"}:
                continue
            trophy_name = entry.get("league") or entry.get("name") or "Trophy"
            counts[trophy_name] = counts.get(trophy_name, 0) + 1
            s = entry.get("season")
            if s:
                seasons_map.setdefault(trophy_name, []).append(str(s))
        trophies = [
            Trophy(name=n, count=c, seasons=seasons_map.get(n, [])[:5])
            for n, c in sorted(counts.items(), key=lambda x: -x[1])
        ]
    except Exception:
        note_parts.append("Trophy details unavailable right now.")

    note = ("_" + " ".join(note_parts) + "_") if note_parts else ""

    return TeamFootballReport(
        team_name=team.get("name") or name,
        recent=recent,
        upcoming=upcoming,
        trophies=trophies,
        trophies_note=note,
    )


async def apisports_league_matches(league: str) -> List[MatchSnapshot]:
    params = _apisports_league_param(league)
    if not params:
        raise ValueError(
            f"Unknown league `{league}`. Major codes: PL, UCL, PD, BL1, SA."
        )
    start = _today() - timedelta(days=3)
    end = _today() + timedelta(days=7)
    return await apisports_range(start, end, league=league)


# ─── football-data.org ───────────────────────────────────────────────────────


async def _fdata_get(path: str, params: dict) -> Any:
    key = _fdata_key()
    if not key:
        raise ValueError(
            "FOOTBALL_DATA_API_KEY is not set. Get a key at https://www.football-data.org/"
        )
    cache_key = f"fdata:{path}:{params}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    url = f"{FDATA_BASE}/{path.lstrip('/')}"
    headers = {"X-Auth-Token": key}
    async with httpx.AsyncClient(timeout=25, follow_redirects=True) as client:
        r = await client.get(url, params=params, headers=headers)
        data = r.json()

    if r.status_code == 429:
        raise RuntimeError("football-data.org rate limit (429). Try again later.")
    if r.status_code != 200:
        msg = data.get("message") or data
        raise RuntimeError(f"football-data.org HTTP {r.status_code}: {msg}")

    ttl = 60 if params.get("status") == "LIVE" else 600
    _cache_set(cache_key, data, ttl)
    return data


def _parse_fdata_match(item: dict) -> MatchSnapshot:
    score = item.get("score") or {}
    ft = score.get("fullTime") or score.get("regularTime") or {}
    status = (item.get("status") or "SCHEDULED").upper()
    comp = (item.get("competition") or {}).get("name") or "Competition"

    kickoff = None
    if item.get("utcDate"):
        try:
            kickoff = datetime.fromisoformat(
                item["utcDate"].replace("Z", "+00:00")
            )
        except ValueError:
            pass

    minute = None
    if status == "IN_PLAY" and item.get("minute"):
        minute = str(item["minute"])

    return MatchSnapshot(
        home=(item.get("homeTeam") or {}).get("name") or "?",
        away=(item.get("awayTeam") or {}).get("name") or "?",
        home_goals=ft.get("home"),
        away_goals=ft.get("away"),
        status=status,
        competition=comp,
        kickoff=kickoff,
        minute=minute,
        league_code=(item.get("competition") or {}).get("code") or "",
    )


async def _fdata_matches(params: dict) -> List[MatchSnapshot]:
    data = await _fdata_get("matches", params)
    items = data.get("matches") or []
    return [_parse_fdata_match(i) for i in items]


def _fdata_league_code(league: str) -> str:
    league = league.strip().upper()
    return FDATA_LEAGUE_CODES.get(league, league)


async def fdata_live(league: str = "") -> List[MatchSnapshot]:
    params: dict = {"status": "LIVE"}
    if league:
        code = _fdata_league_code(league)
        data = await _fdata_get(f"competitions/{code}/matches", {"status": "LIVE"})
        return [_parse_fdata_match(i) for i in data.get("matches") or []]
    matches = await _fdata_matches(params)
    return _filter_major_matches(matches, "fdata")


async def fdata_today(league: str = "") -> List[MatchSnapshot]:
    d = _today().isoformat()
    if league:
        code = _fdata_league_code(league)
        data = await _fdata_get(
            f"competitions/{code}/matches",
            {"dateFrom": d, "dateTo": d},
        )
        return [_parse_fdata_match(i) for i in data.get("matches") or []]
    matches = await _fdata_matches({"dateFrom": d, "dateTo": d})
    return _filter_major_matches(matches, "fdata")


async def fdata_range(start: date, end: date, league: str = "") -> List[MatchSnapshot]:
    params = {"dateFrom": start.isoformat(), "dateTo": end.isoformat()}
    if league:
        code = _fdata_league_code(league)
        data = await _fdata_get(
            f"competitions/{code}/matches",
            params,
        )
        return [_parse_fdata_match(i) for i in data.get("matches") or []]
    matches = await _fdata_matches(params)
    return _filter_major_matches(matches, "fdata")


async def fdata_upcoming(days: int, league: str = "") -> List[MatchSnapshot]:
    start = _today()
    end = start + timedelta(days=days)
    matches = await fdata_range(start, end, league=league)
    return [m for m in matches if m.is_scheduled]


async def fdata_past(days: int, league: str = "") -> List[MatchSnapshot]:
    end = _today()
    start = end - timedelta(days=days)
    matches = await fdata_range(start, end, league=league)
    return [m for m in matches if m.is_finished]


async def _fdata_find_team(name: str) -> Optional[dict]:
    cache_key = f"fdata:team:{name.lower()}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    name_l = name.lower()
    for code in MAJOR_LEAGUE_CODES:
        try:
            data = await _fdata_get(f"competitions/{code}/teams", {})
            for t in data.get("teams") or []:
                if name_l in (t.get("name") or "").lower() or name_l in (
                    t.get("shortName") or ""
                ).lower():
                    _cache_set(cache_key, t, 3600)
                    return t
        except Exception:
            continue
    return None


async def fdata_team_report(name: str, season: Optional[int] = None) -> TeamFootballReport:
    team = await _fdata_find_team(name)
    if not team:
        raise ValueError(
            f"Team not found: {name}. Free tier covers top leagues only (PL, PD, BL1, SA, FL1, CL)."
        )
    tid = team.get("id")
    data = await _fdata_get(f"teams/{tid}/matches", {"limit": 40})
    fixtures = _filter_major_matches(
        [_parse_fdata_match(i) for i in data.get("matches") or []],
        "fdata",
    )
    recent = [m for m in fixtures if m.is_finished][-5:]
    upcoming = [m for m in fixtures if m.is_scheduled][:5]

    note = ""
    if _major_only_enabled():
        note = "_Major leagues only: PL, Bundesliga, La Liga, Serie A, UCL._"

    return TeamFootballReport(
        team_name=team.get("name") or name,
        recent=recent,
        upcoming=upcoming,
        trophies=[],
        trophies_note=note or (
            "_Title wins not exposed on football-data.org free tier — use `.fball team` for trophies._"
        ),
    )


async def fdata_league_matches(league: str) -> List[MatchSnapshot]:
    code = _fdata_league_code(league)
    start = _today() - timedelta(days=3)
    end = _today() + timedelta(days=7)
    return await fdata_range(start, end, league=code)


async def run_football_query(provider: str, query: FootballQuery) -> str:
    """Execute query and return formatted Telegram HTML text."""
    tz = _tz()
    league = query.league

    if provider == "apisports":
        if query.mode == "live":
            matches = await apisports_live(league)
            return format_matches(matches, "Live scores (API-Football)", tz)
        if query.mode == "today":
            matches = await apisports_today(league)
            return format_matches(matches, f"Today ({_today().isoformat()})", tz)
        if query.mode == "up":
            matches = await apisports_upcoming(query.days, league)
            return format_matches(
                matches, f"Upcoming {query.days} day(s) (API-Football)", tz
            )
        if query.mode == "past":
            matches = await apisports_past(query.days, league)
            return format_matches(
                matches, f"Past {query.days} day(s) (API-Football)", tz
            )
        if query.mode == "team":
            if not query.team_name:
                raise ValueError("Usage: `.fball team <name> [season]`")
            report = await apisports_team_report(query.team_name, query.season)
            return format_team_report(report, tz)
        if query.mode == "league":
            if not query.league:
                raise ValueError("Usage: `.fball league PL` (or set FBALL_LEAGUE gvar)")
            matches = await apisports_league_matches(query.league)
            return format_matches(matches, f"League {query.league} (API-Football)", tz)
        raise ValueError(f"Unknown mode: {query.mode}")

    # football-data.org
    if query.mode == "live":
        matches = await fdata_live(league)
        return format_matches(matches, "Live scores (football-data.org)", tz)
    if query.mode == "today":
        matches = await fdata_today(league)
        return format_matches(matches, f"Today ({_today().isoformat()})", tz)
    if query.mode == "up":
        matches = await fdata_upcoming(query.days, league)
        return format_matches(
            matches, f"Upcoming {query.days} day(s) (football-data.org)", tz
        )
    if query.mode == "past":
        matches = await fdata_past(query.days, league)
        return format_matches(
            matches, f"Past {query.days} day(s) (football-data.org)", tz
        )
    if query.mode == "team":
        if not query.team_name:
            raise ValueError("Usage: `.fdata team <name>`")
        report = await fdata_team_report(query.team_name, query.season)
        return format_team_report(report, tz)
    if query.mode == "league":
        if not query.league:
            raise ValueError("Usage: `.fdata league PL`")
        matches = await fdata_league_matches(query.league)
        return format_matches(
            matches, f"League {query.league} (football-data.org)", tz
        )
    raise ValueError(f"Unknown mode: {query.mode}")


# ─── .help text builders (each call returns a fresh dict for cat_cmd info=) ───


def build_fball_help(provider: str = "apisports", **overrides) -> dict:
    """Structured help for .fball / .fdata and aliases. Pass a new dict per command."""
    import copy
    modes = {
        "live": "In-play matches right now (worldwide or filtered league)",
        "today": "Today's matches — live, finished, and scheduled",
        "up": "Upcoming fixtures for N days (default 3, max 14)",
        "upcoming": "Same as up",
        "past": "Finished results for the last N days (default 3, max 30)",
        "results": "Same as past",
        "team": "Team card — last 5 results, next 5 fixtures, honours",
        "league": "League window — recent + upcoming for a competition code",
    }
    leagues = {
        "PL / EPL": "Premier League (England)",
        "UCL / CL": "UEFA Champions League",
        "PD / LALIGA": "La Liga (Spain)",
        "BL1": "Bundesliga (Germany)",
        "SA": "Serie A (Italy)",
    }

    if provider == "fdata":
        info = {
            "header": "Football scores via football-data.org",
            "description": (
                "Live scores, today, upcoming/past fixtures, team view, and league filter "
                "using the football-data.org v4 API. Free tier covers top European competitions."
            ),
            "flags": modes,
            "types": list(leagues.keys()),
            "usage": [
                "{tr}fdata live",
                "{tr}fdata today",
                "{tr}fdata up 7",
                "{tr}fdata past 5",
                "{tr}fdata team Arsenal",
                "{tr}fdata team Real Madrid",
                "{tr}fdata league PL",
                "{tr}fdata league UCL",
            ],
            "examples": [
                "{tr}ffdata live",
                "{tr}fdata up 5",
                "{tr}fdata past 3",
                "{tr}fdata team Chelsea",
                "{tr}fdata league PD",
            ],
            "api keys": {
                "FOOTBALL_DATA_API_KEY": "Required — token from football-data.org (header X-Auth-Token)",
            },
            "providers": {
                "fdata / ffdata": "football-data.org — top leagues on free tier",
                "fball / afball": "API-Football — broader coverage + trophies (separate key)",
            },
            "note": (
                "Default: major leagues only (PL, Bundesliga, La Liga, Serie A, UCL). "
                "Free tier covers those competitions. Defaults via {tr}fballset."
            ),
        }
    else:
        info = {
            "header": "Football scores via API-Football (api-sports)",
            "description": (
                "Live scores, today, upcoming/past fixtures, team honours, and league filter "
                "using API-Sports v3.football.api-sports.io. Best coverage and team trophies."
            ),
            "flags": modes,
            "types": list(leagues.keys()),
            "usage": [
                "{tr}fball live",
                "{tr}fball today",
                "{tr}fball up 7",
                "{tr}fball past 5",
                "{tr}fball team Arsenal",
                "{tr}fball team Real Madrid 2024",
                "{tr}fball league PL",
                "{tr}fball league UCL",
            ],
            "examples": [
                "{tr}afball live",
                "{tr}fball up 7",
                "{tr}fball past 5",
                "{tr}fball team Liverpool 2023",
                "{tr}fball league SA",
            ],
            "api keys": {
                "API_FOOTBALL_KEY": "Required — key from api-football.com (header x-apisports-key)",
            },
            "providers": {
                "fball / afball": "API-Football (this command)",
                "fdata / ffdata": "football-data.org — alternate provider, separate key",
            },
            "note": (
                "Default: major leagues only (PL, Bundesliga, La Liga, Serie A, UCL). "
                "Free tier seasons {min}–{max} — omit season or use e.g. 2024. "
                "Env FBALL_MAJOR_ONLY=false to show all leagues. "
                "Defaults: {tr}fballset."
            ).format(
                min=_apisports_season_bounds()[0],
                max=_apisports_season_bounds()[1],
            ),
        }

    info.update(overrides)
    return copy.deepcopy(info)


def build_fballset_help() -> dict:
    import copy

    return copy.deepcopy(
        {
        "header": "Football plugin defaults (saved gvars)",
        "description": (
            "Stores your preferred upcoming/past day counts and default league filter "
            "for {tr}fball and {tr}fdata when you omit day counts or league."
        ),
        "options": {
            "up / upcoming <n>": "Default days for {tr}fball up (max 14)",
            "past / results <n>": "Default days for {tr}fball past (max 30)",
            "league <code>": "Default league filter — PL, UCL, PD, BL1, SA, FL1, etc.",
        },
        "usage": [
            "{tr}fballset",
            "{tr}fballset up 7",
            "{tr}fballset past 5",
            "{tr}fballset league PL",
        ],
        "examples": [
            "{tr}fballset up 7",
            "{tr}fballset league UCL",
        ],
        "note": "Gvars: FBALL_UP_DAYS, FBALL_PAST_DAYS, FBALL_LEAGUE.",
        }
    )
