# Daily digest section builders

import contextlib
from datetime import datetime

import requests

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


async def fetch_weather(city: str = "Addis Ababa") -> str:
    try:
        url = f"https://wttr.in/{city.replace(' ', '+')}?format=3"
        resp = requests.get(url, timeout=15, headers={"User-Agent": "curl/7"})
        if resp.ok and resp.text.strip():
            return resp.text.strip()
    except Exception:
        pass
    return "Weather unavailable"


def fetch_github_activity(username: str = "henok-enyew", cache: dict = None) -> str:
    cache = cache or {}
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


def format_pm_section(log_entries: list) -> str:
    if not log_entries:
        return "No PMs logged while you were away."
    names = {}
    for entry in log_entries:
        name = entry.get("name", "Unknown")
        names[name] = names.get(name, 0) + 1
    top = sorted(names.items(), key=lambda x: -x[1])[:5]
    summary = ", ".join(f"{n} ({c})" for n, c in top)
    return f"{len(log_entries)} message(s) — {summary}"


def coding_tip_of_day() -> str:
    day = datetime.utcnow().timetuple().tm_yday
    return CODING_TIPS[day % len(CODING_TIPS)]


FOOTBALL_LINE = "Man United & Real Madrid fan — CR7 is the GOAT."


async def build_digest_text(
    pm_log: list,
    ai_football_line: str = None,
) -> str:
    weather = await fetch_weather()
    github = fetch_github_activity()
    pm_section = format_pm_section(pm_log)
    tip = coding_tip_of_day()
    football = ai_football_line or FOOTBALL_LINE
    today = datetime.now().strftime("%A, %B %d, %Y")
    return (
        f"**Daily Briefing — {today}**\n\n"
        f"**Weather (Addis Ababa):** {weather}\n\n"
        f"**GitHub:**\n{github}\n\n"
        f"**PMs while away:** {pm_section}\n\n"
        f"**Football:** {football}\n\n"
        f"**Coding tip:** {tip}"
    )
