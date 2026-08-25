# Daily personal briefing — morning & night digests

import contextlib

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telethon import events
from telethon.tl.types import User

from userbot import catub
from userbot.ai_assistant.state import ai_state
from userbot.core.logger import logging
from userbot.core.managers import edit_delete, edit_or_reply
from userbot.helpers.functions.digest_builder import (
    ADDIS_TZ,
    addis_now,
    build_digest_text,
    resolve_period,
)
from userbot.helpers.functions.digest_inbox import collect_unread_inbox
from userbot.sql_helper import digest_sql
from userbot.sql_helper.globals import addgvar, gvarstatus

plugin_category = "utils"
LOGS = logging.getLogger(__name__)

_scheduler = None
_github_cache = {}


def _digest_auto() -> bool:
    val = gvarstatus("DIGEST_AUTO")
    if val is None:
        return True
    return str(val).lower() not in ("false", "0", "off", "no")


def _digest_hour() -> int:
    """Morning hour (default 8)."""
    val = gvarstatus("DIGEST_HOUR")
    try:
        hour = int(val) if val is not None else 8
    except (TypeError, ValueError):
        hour = 8
    return max(0, min(hour, 23))


def _digest_evening_hour() -> int:
    """Night hour (default 20 = 8 PM)."""
    val = gvarstatus("DIGEST_EVENING_HOUR")
    try:
        hour = int(val) if val is not None else 20
    except (TypeError, ValueError):
        hour = 20
    return max(0, min(hour, 23))


def _digest_minute() -> int:
    val = gvarstatus("DIGEST_MINUTE")
    try:
        minute = int(val) if val is not None else 0
    except (TypeError, ValueError):
        minute = 0
    return max(0, min(minute, 59))


def _digest_target():
    return gvarstatus("DIGEST_CHAT") or "me"


def _schedule_time_label() -> str:
    m = _digest_minute()
    return (
        f"{_digest_hour():02d}:{m:02d} & {_digest_evening_hour():02d}:{m:02d} "
        "Africa/Addis_Ababa"
    )


async def _optional_football_line():
    try:
        from userbot.plugins.ai_assistant import get_ai_components

        provider, conv_engine = get_ai_components()
        messages = conv_engine.build_messages(
            current_message="One short witty line about Man United or Real Madrid today.",
            include_full_profile=False,
            is_owner_direct=True,
        )
        line = await provider.generate_response(messages, temperature=0.9, max_tokens=60)
        return line.strip() if line else None
    except Exception:
        return None


# Telegram photo caption hard limit
_CAPTION_LIMIT = 1024


def _fit_caption(text: str, limit: int = _CAPTION_LIMIT) -> str:
    """Fit digest into one photo caption without breaking mid-word when possible."""
    if len(text) <= limit:
        return text
    cut = text[: limit - 1]
    # Prefer breaking on a newline so markdown stays cleaner
    nl = cut.rfind("\n")
    if nl >= limit // 2:
        cut = cut[:nl]
    return cut.rstrip() + "…"


async def send_digest(client, chat_id=None, period: str | None = None):
    """Build and deliver digest as one message (photo + caption)."""
    chat = chat_id or _digest_target()
    period = resolve_period(period)

    inbox = await collect_unread_inbox(client)
    football = await _optional_football_line()
    text, _greeting, image_url = await build_digest_text(
        inbox=inbox,
        ai_football_line=football,
        period=period,
        github_cache=_github_cache,
    )

    caption = _fit_caption(text)
    sent = False
    with contextlib.suppress(Exception):
        await client.send_file(
            chat,
            image_url,
            caption=caption,
            parse_mode="md",
            link_preview=False,
        )
        sent = True

    # Fallback: text-only if photo download/send failed
    if not sent:
        if len(text) <= 4000:
            await client.send_message(chat, text, parse_mode="md", link_preview=False)
        else:
            await client.send_message(chat, text[:3900] + "\n…", parse_mode="md")
            await client.send_message(chat, text[3900:7800], parse_mode="md")

    # Clear AFK ring buffer if anything was logged (legacy supplemental)
    with contextlib.suppress(Exception):
        digest_sql.get_pm_log_since(clear_after=True)


async def _scheduled_digest_morning():
    try:
        await send_digest(catub, "me", period="morning")
    except Exception as e:
        LOGS.error(f"morning digest failed: {e}")


async def _scheduled_digest_night():
    try:
        await send_digest(catub, "me", period="night")
    except Exception as e:
        LOGS.error(f"night digest failed: {e}")


def _reschedule_digest_jobs(sched):
    """Morning + night cron jobs (Addis Ababa)."""
    minute = _digest_minute()
    sched.add_job(
        _scheduled_digest_morning,
        "cron",
        hour=_digest_hour(),
        minute=minute,
        id="daily_digest_morning",
        replace_existing=True,
    )
    sched.add_job(
        _scheduled_digest_night,
        "cron",
        hour=_digest_evening_hour(),
        minute=minute,
        id="daily_digest_night",
        replace_existing=True,
    )
    # Remove legacy single job if present
    with contextlib.suppress(Exception):
        sched.remove_job("daily_digest")


def _ensure_scheduler():
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone=ADDIS_TZ)
    try:
        _reschedule_digest_jobs(_scheduler)
    except Exception as e:
        LOGS.error(f"digest scheduler reschedule failed: {e}")
    if _digest_auto() and not _scheduler.running:
        try:
            _scheduler.start()
        except Exception as e:
            LOGS.error(f"digest scheduler start failed: {e}")
    return _scheduler


def _next_run_str(sched) -> str:
    times = []
    for jid in ("daily_digest_morning", "daily_digest_night"):
        job = sched.get_job(jid) if sched else None
        if job and job.next_run_time:
            times.append(job.next_run_time.strftime("%Y-%m-%d %H:%M %Z"))
    return " | ".join(times) if times else "not scheduled"


@catub.cat_cmd(
    pattern=r"digest(?:\s+(.+))?$",
    command=("digest", plugin_category),
    info={
        "header": "Morning & night personal briefing",
        "description": (
            "Delivers to Saved Messages by default as one message (photo + digest caption) "
            "with weather (°C), unread DMs, group mentions, and greeting. "
            "Auto runs twice daily (Addis Ababa)."
        ),
        "usage": [
            "{tr}digest",
            "{tr}digest me",
            "{tr}digest here",
            "{tr}digest auto on",
            "{tr}digest auto off",
            "{tr}digest time 8 0",
            "{tr}digest time night 20 0",
            "{tr}digest status",
        ],
        "examples": [
            "{tr}digest",
            "{tr}digest time 8 0",
            "{tr}digest time night 20 0",
            "{tr}digest here",
        ],
    },
)
async def digest_cmd(event):
    "Run or configure daily digest."
    raw = (event.pattern_match.group(1) or "").strip()
    parts = raw.split() if raw else []

    if parts and parts[0] == "auto":
        toggle = parts[1].lower() if len(parts) > 1 else ""
        if toggle == "on":
            addgvar("DIGEST_AUTO", "true")
            sched = _ensure_scheduler()
            if not sched.running:
                sched.start()
            return await edit_delete(
                event,
                f"**Digest auto:** ON ({_schedule_time_label()})",
                6,
            )
        if toggle == "off":
            addgvar("DIGEST_AUTO", "false")
            if _scheduler and _scheduler.running:
                _scheduler.shutdown(wait=False)
            return await edit_delete(event, "**Digest auto:** OFF", 5)

    if parts and parts[0] == "status":
        auto = _digest_auto()
        sched = _ensure_scheduler()
        return await edit_or_reply(
            event,
            f"**Digest status**\n"
            f"Auto: {'ON' if auto else 'OFF'}\n"
            f"Schedule: `{_schedule_time_label()}`\n"
            f"Next runs: {_next_run_str(sched)}\n"
            f"Target: Saved Messages (`me`)\n"
            f"Now (Addis): `{addis_now().strftime('%H:%M')}`",
        )

    if parts and parts[0] == "time":
        # .digest time 8 0  OR  .digest time night 20 0  OR  .digest time morning 8 0
        rest = parts[1:]
        which = "morning"
        if rest and rest[0].lower() in ("night", "evening", "morning"):
            which = "night" if rest[0].lower() in ("night", "evening") else "morning"
            rest = rest[1:]
        if len(rest) < 2:
            return await edit_delete(
                event,
                "**Usage:**\n"
                "`.digest time 8 0` — morning hour & minute\n"
                "`.digest time night 20 0` — night hour & minute",
            )
        try:
            hour = max(0, min(int(rest[0]), 23))
            minute = max(0, min(int(rest[1]), 59))
        except ValueError:
            return await edit_delete(event, "**Hour and minute must be numbers.**")
        addgvar("DIGEST_MINUTE", str(minute))
        if which == "night":
            addgvar("DIGEST_EVENING_HOUR", str(hour))
        else:
            addgvar("DIGEST_HOUR", str(hour))
        sched = _ensure_scheduler()
        _reschedule_digest_jobs(sched)
        if _digest_auto() and not sched.running:
            sched.start()
        return await edit_delete(
            event,
            f"**Digest {which} set:** `{hour:02d}:{minute:02d}` Addis\n"
            f"Full schedule: `{_schedule_time_label()}`\n"
            f"Next: {_next_run_str(sched)}",
            10,
        )

    period = resolve_period()
    if parts and parts[0] == "here":
        catevent = await edit_or_reply(event, "**Building briefing...**")
        await send_digest(event.client, event.chat_id, period=period)
        return await catevent.delete()

    # Default and explicit "me" → Saved Messages
    catevent = await edit_or_reply(event, "**Building briefing...**")
    await send_digest(event.client, "me", period=period)
    await catevent.delete()


@catub.on(events.NewMessage(incoming=True))
async def digest_pm_logger(event):
    """Optional AFK supplemental log (primary inbox uses live unread scan)."""
    if not event.is_private:
        return
    try:
        import userbot as _ub

        is_afk = getattr(_ub, "ISAFK", False) or ai_state.aiafk_enabled
    except Exception:
        is_afk = ai_state.aiafk_enabled
    if not is_afk:
        return
    sender = await event.get_sender()
    if not sender or not isinstance(sender, User) or sender.bot:
        return
    text = (event.message.message or "").strip()
    if not text:
        return
    name = getattr(sender, "first_name", "Unknown")
    digest_sql.log_pm(sender.id, name, text[:200])


def _init_digest_scheduler():
    try:
        if _digest_auto():
            _ensure_scheduler()
    except Exception as e:
        LOGS.error(f"digest scheduler init skipped: {e}")


try:
    _init_digest_scheduler()
except Exception as e:
    LOGS.error(f"digest module scheduler init failed: {e}")
