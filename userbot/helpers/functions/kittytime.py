# Shared time helpers for the "modern" plugins (remind, snooze, seen, stories...)
#
# Everything user-facing is shown in Africa/Addis_Ababa time, same as the
# digest / leetcode plugins.

import re
from datetime import datetime, timedelta, timezone

from .digest_builder import ADDIS_TZ

_UNIT_SECONDS = {
    "s": 1,
    "sec": 1,
    "secs": 1,
    "second": 1,
    "seconds": 1,
    "m": 60,
    "min": 60,
    "mins": 60,
    "minute": 60,
    "minutes": 60,
    "h": 3600,
    "hr": 3600,
    "hrs": 3600,
    "hour": 3600,
    "hours": 3600,
    "d": 86400,
    "day": 86400,
    "days": 86400,
    "w": 604800,
    "week": 604800,
    "weeks": 604800,
}

_DURATION_TOKEN = re.compile(r"(\d+(?:\.\d+)?)\s*([a-z]+)", re.I)
_CLOCK = re.compile(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$", re.I)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_local() -> datetime:
    return datetime.now(ADDIS_TZ)


def to_local(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(ADDIS_TZ)


def parse_duration(text: str):
    """'1h30m' / '2 days' / '45min' -> timedelta, or None if it isn't a duration.

    The whole string must be made of duration tokens, so '2h buy milk' is not a
    duration (use split_when() for that).
    """
    raw = (text or "").strip().lower().replace(",", "")
    if not raw:
        return None
    pos, total = 0, 0.0
    for m in _DURATION_TOKEN.finditer(raw):
        if raw[pos : m.start()].strip():
            return None
        unit = _UNIT_SECONDS.get(m.group(2))
        if unit is None:
            return None
        total += float(m.group(1)) * unit
        pos = m.end()
    if raw[pos:].strip() or total <= 0:
        return None
    return timedelta(seconds=int(total))


def _parse_clock(token: str):
    m = _CLOCK.match(token.strip())
    if not m:
        return None
    hour, minute, ampm = int(m.group(1)), int(m.group(2) or 0), m.group(3)
    if ampm:
        if not 1 <= hour <= 12:
            return None
        hour = hour % 12 + (12 if ampm.lower() == "pm" else 0)
    elif m.group(2) is None:
        # a bare number like "5" is ambiguous; require "5pm" or "17:00"
        return None
    if hour > 23 or minute > 59:
        return None
    return hour, minute


def split_when(text: str):
    """Split '<when> <rest>' into (aware UTC datetime, rest).

    Understands:
      10m / 1h30m / 2d / "2 hours"        -> relative
      18:30 / 6pm / 6:30pm / at 18:30      -> next occurrence today/tomorrow
      tomorrow 9:00 / tomorrow             -> tomorrow (default 09:00)
    Returns (None, text) when no time could be read.
    """
    words = (text or "").strip().split()
    if not words:
        return None, ""
    if words[0].lower() in ("in", "at"):
        words = words[1:]
    if not words:
        return None, ""

    now = now_local()

    if words[0].lower() in ("tomorrow", "tmr", "tmrw"):
        clock = _parse_clock(words[1]) if len(words) > 1 else None
        rest = words[2:] if clock else words[1:]
        hour, minute = clock or (9, 0)
        when = (now + timedelta(days=1)).replace(
            hour=hour, minute=minute, second=0, microsecond=0
        )
        return when.astimezone(timezone.utc), " ".join(rest)

    clock = _parse_clock(words[0])
    if clock is None and len(words) > 1:
        clock_two = _parse_clock(f"{words[0]}{words[1]}")  # "6 pm"
        if clock_two:
            clock, words = clock_two, [f"{words[0]}{words[1]}"] + words[2:]
    if clock:
        when = now.replace(hour=clock[0], minute=clock[1], second=0, microsecond=0)
        if when <= now:
            when += timedelta(days=1)
        return when.astimezone(timezone.utc), " ".join(words[1:])

    # longest prefix of words that is a pure duration ("1h 30m", "2 days")
    for cut in range(min(len(words), 6), 0, -1):
        delta = parse_duration(" ".join(words[:cut]))
        if delta:
            return now_utc() + delta, " ".join(words[cut:])
    return None, text.strip()


def human_delta(delta: timedelta) -> str:
    secs = int(abs(delta.total_seconds()))
    if secs < 60:
        return f"{secs}s"
    parts = []
    for name, size in (("d", 86400), ("h", 3600), ("m", 60)):
        if secs >= size:
            parts.append(f"{secs // size}{name}")
            secs %= size
    return " ".join(parts[:2])


def ago(dt: datetime) -> str:
    if dt is None:
        return "unknown"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = now_utc() - dt
    if delta.total_seconds() < 45:
        return "just now"
    return f"{human_delta(delta)} ago"


def fmt_local(dt: datetime, with_date=True) -> str:
    local = to_local(dt)
    if not with_date:
        return local.strftime("%H:%M")
    today = now_local().date()
    if local.date() == today:
        return f"today {local:%H:%M}"
    if local.date() == today + timedelta(days=1):
        return f"tomorrow {local:%H:%M}"
    if local.date() == today - timedelta(days=1):
        return f"yesterday {local:%H:%M}"
    return local.strftime("%a %d %b %H:%M")
