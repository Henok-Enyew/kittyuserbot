# Daily digest section builders

from __future__ import annotations

import random
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

ADDIS_TZ = ZoneInfo("Africa/Addis_Ababa")

CODING_TIPS = [
    "Prefer early returns over deep nesting.",
    "Name functions after what they do, not how they do it.",
    "Write the test for the bug before fixing the bug.",
    "Keep PRs small — one logical change per PR.",
    "Read error messages fully before Googling.",
    "Use type hints on public functions.",
    "Cache expensive reads; invalidate explicitly.",
    "Log context (ids, states) not just 'failed'.",
    "Profile before optimizing.",
    "Document why, not what — the code shows what.",
    "Avoid premature abstraction — three uses, then extract.",
    "Use migrations for every schema change.",
    "Validate at system boundaries only.",
    "Prefer composition over inheritance.",
    "Make illegal states unrepresentable when possible.",
    "Use feature flags for risky rollouts.",
    "Keep config in env, not hardcoded.",
    "Retry with backoff on transient failures.",
    "Close resources in finally blocks.",
    "Review your own diff before opening a PR.",
    "Split IO and pure logic for testability.",
    "Use meaningful commit messages.",
    "Delete dead code — git remembers.",
    "Prefer idempotent handlers for webhooks.",
    "Limit function parameters; use a config object.",
    "Use linters in CI, not just locally.",
    "Read one source file before adding a new dependency.",
    "Batch DB writes when safe.",
    "Use indexes for columns you filter on.",
    "Ship small, ship often.",
]

# Curated Unsplash images (direct CDN — no API key)
MORNING_IMAGES = [
    "https://images.unsplash.com/photo-1470252649378-9c29740c9fa8?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1495616811223-4d98c6e9c869?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1469474968028-56623f02e42e?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1414609245224-afa02bfb3fda?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?auto=format&fit=crop&w=1200&q=80",
]

NIGHT_IMAGES = [
    "https://images.unsplash.com/photo-1419242902214-272b3f66ee7a?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1507400492013-162706c8c05e?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1534796636912-3b95bdea80fd?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1444703686981-a3abbc4d4fe3?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1519681393784-d120267933ba?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1502134249126-9f3755a50d78?auto=format&fit=crop&w=1200&q=80",
]

MORNING_GREETINGS = [
    "☀️ **Good morning!** Rise and shine — here's your briefing.",
    "🌅 **Good morning!** Fresh day, clear mind. Your digest is ready.",
    "☕ **Good morning!** Coffee up — here's what's waiting for you.",
]

NIGHT_GREETINGS = [
    "🌙 **Good night!** Wind down — here's your evening wrap-up.",
    "✨ **Good evening!** Before you rest — your night digest.",
    "🌃 **Good night!** One last look at what landed today.",
]

FOOTBALL_LINE = "Man United & Real Madrid fan — CR7 is the GOAT."

_WEATHER_SHORT = {
    "sunny": "Sunny day",
    "clear": "Clear skies",
    "partly cloudy": "Partly cloudy",
    "cloudy": "Cloudy",
    "overcast": "Overcast",
    "mist": "Misty",
    "fog": "Foggy",
    "haze": "Hazy",
    "rain": "Rainy",
    "light rain": "Light rain",
    "moderate rain": "Rainy",
    "heavy rain": "Heavy rain",
    "drizzle": "Drizzle",
    "shower": "Showers",
    "thunder": "Thunderstorms",
    "snow": "Snowy",
    "sleet": "Sleet",
}


def addis_now() -> datetime:
    return datetime.now(ADDIS_TZ)


def resolve_period(period: str | None = None) -> str:
    """Return 'morning' or 'night'."""
    if period in ("morning", "night"):
        return period
    return "morning" if addis_now().hour < 17 else "night"


def greeting_for(period: str) -> str:
    pool = MORNING_GREETINGS if period == "morning" else NIGHT_GREETINGS
    return random.choice(pool)


def image_for(period: str) -> str:
    pool = MORNING_IMAGES if period == "morning" else NIGHT_IMAGES
    return random.choice(pool)


def _short_condition(condition: str) -> str:
    low = (condition or "").strip().lower()
    if not low:
        return "Mixed conditions"
    for key, label in _WEATHER_SHORT.items():
        if key in low:
            return label
    # fallback: first two words, title-case
    words = condition.strip().split()
    return " ".join(words[:3]).title() if words else "Mixed conditions"


async def fetch_weather(city: str = "Addis Ababa") -> str:
    """Celsius + short sunny/rain style line via wttr.in (metric)."""
    try:
        # %t = temp with unit, %C = condition text, m = metric (°C)
        url = (
            f"https://wttr.in/{city.replace(' ', '+')}"
            f"?m&format=%t|%C"
        )
        resp = requests.get(url, timeout=15, headers={"User-Agent": "curl/7"})
        if resp.ok and resp.text.strip() and "|" in resp.text:
            temp_raw, condition = resp.text.strip().split("|", 1)
            temp = temp_raw.strip().replace("+", "")
            short = _short_condition(condition.strip())
            return f"{temp} · {short}"
        # fallback format=3 still often includes °C with ?m
        resp2 = requests.get(
            f"https://wttr.in/{city.replace(' ', '+')}?m&format=3",
            timeout=15,
            headers={"User-Agent": "curl/7"},
        )
        if resp2.ok and resp2.text.strip():
            return resp2.text.strip()
    except Exception:
        pass
    return "Weather unavailable"


def fetch_github_activity(username: str = "henok-enyew", cache: dict | None = None) -> str:
    cache = cache if cache is not None else {}
    now = datetime.utcnow()
    if cache.get("ts") and (now - cache["ts"]).total_seconds() < 3600:
        return cache.get("text", "GitHub activity unavailable")
    try:
        resp = requests.get(
            f"https://api.github.com/users/{username}/events/public",
            params={"per_page": 5},
            timeout=15,
            headers={"Accept": "application/vnd.github+json"},
        )
        if not resp.ok:
            return "GitHub activity unavailable (rate limit or error)"
        events = resp.json()
        if not events:
            return "No recent public GitHub activity"
        lines = []
        for ev in events[:5]:
            etype = ev.get("type", "Event").replace("Event", "")
            repo = ev.get("repo", {}).get("name", "?")
            lines.append(f"• {etype} on {repo}")
        text = "\n".join(lines)
        cache["text"] = text
        cache["ts"] = now
        return text
    except Exception:
        return "GitHub activity unavailable"


def format_inbox_section(inbox: dict) -> str:
    """
    inbox = {
      "dms": [{"name", "chat_title", "messages": [{"text", "name"}], "extra"}],
      "mentions": [{"chat_title", "messages": [...], "extra"}],
    }
    """
    dms = inbox.get("dms") or []
    mentions = inbox.get("mentions") or []
    if not dms and not mentions:
        return "Inbox clear — no unread DMs or mentions."

    blocks = []
    if dms:
        blocks.append(f"**Unread DMs ({len(dms)} chat(s)):**")
        for item in dms:
            name = item.get("name") or item.get("chat_title") or "Unknown"
            msgs = item.get("messages") or []
            extra = item.get("extra", 0)
            if not msgs:
                blocks.append(f"• **{name}** — {item.get('unread', '?')} unread")
                continue
            preview = msgs[0].get("text", "")
            line = f"• **{name}:** {preview}"
            more = max(0, len(msgs) - 1) + extra
            if more:
                line += f" _(+{more} more)_"
            blocks.append(line)

    if mentions:
        blocks.append(f"\n**Group mentions ({len(mentions)} chat(s)):**")
        for item in mentions:
            title = item.get("chat_title") or "Group"
            msgs = item.get("messages") or []
            extra = item.get("extra", 0)
            if not msgs:
                blocks.append(f"• **{title}** — {item.get('unread', '?')} mention(s)")
                continue
            who = msgs[0].get("name", "Someone")
            preview = msgs[0].get("text", "")
            line = f"• **{title}** — {who}: {preview}"
            more = max(0, len(msgs) - 1) + extra
            if more:
                line += f" _(+{more} more)_"
            blocks.append(line)

    return "\n".join(blocks)


def coding_tip_of_day() -> str:
    day = addis_now().timetuple().tm_yday
    return CODING_TIPS[day % len(CODING_TIPS)]


async def build_digest_text(
    inbox: dict | None = None,
    ai_football_line: str | None = None,
    period: str | None = None,
    github_cache: dict | None = None,
) -> tuple[str, str, str]:
    """
    Returns (full_text, greeting, image_url).
    """
    period = resolve_period(period)
    greeting = greeting_for(period)
    image_url = image_for(period)
    weather = await fetch_weather()
    github = fetch_github_activity(cache=github_cache)
    inbox_section = format_inbox_section(inbox or {})
    tip = coding_tip_of_day()
    football = ai_football_line or FOOTBALL_LINE
    today = addis_now().strftime("%A, %B %d, %Y · %H:%M")
    title = "Morning Briefing" if period == "morning" else "Night Briefing"
    text = (
        f"{greeting}\n\n"
        f"**{title} — {today}** _(Addis Ababa)_\n\n"
        f"**Weather:** {weather}\n\n"
        f"**GitHub:**\n{github}\n\n"
        f"**Inbox:**\n{inbox_section}\n\n"
        f"**Football:** {football}\n\n"
        f"**Coding tip:** {tip}"
    )
    return text, greeting, image_url
