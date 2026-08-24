# Daily personal briefing

import contextlib

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telethon import events
from telethon.tl.types import User

from userbot import catub
from userbot.ai_assistant.state import ai_state
from userbot.core.logger import logging
from userbot.core.managers import edit_delete, edit_or_reply
from userbot.helpers.functions.digest_builder import build_digest_text
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
    val = gvarstatus("DIGEST_HOUR")
    try:
        hour = int(val) if val is not None else 8
    except (TypeError, ValueError):
        hour = 8
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
    return f"{_digest_hour():02d}:{_digest_minute():02d} Africa/Addis_Ababa"


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


async def send_digest(client, chat_id=None):
    chat = chat_id or _digest_target()
    pm_log = digest_sql.get_pm_log_since(clear_after=True)
    football = await _optional_football_line()
    text = await build_digest_text(pm_log, ai_football_line=football)
    await client.send_message(chat, text, parse_mode="md")


async def _scheduled_digest():
    try:
        await send_digest(catub, "me")
    except Exception as e:
        LOGS.error(f"scheduled digest failed: {e}")


def _reschedule_digest_job(sched):
    """Add or update the daily digest cron job from gvars."""
    sched.add_job(
        _scheduled_digest,
        "cron",
        hour=_digest_hour(),
        minute=_digest_minute(),
        id="daily_digest",
        replace_existing=True,
    )


def _ensure_scheduler():
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="Africa/Addis_Ababa")
    _reschedule_digest_job(_scheduler)
    if _digest_auto() and not _scheduler.running:
        _scheduler.start()
    return _scheduler


@catub.cat_cmd(
    pattern=r"digest(?:\s+(.+))?$",
    command=("digest", plugin_category),
    info={
        "header": "Daily personal briefing",
        "description": (
            "Morning briefing delivered to Saved Messages by default. "
            "Auto schedule uses Africa/Addis_Ababa timezone."
        ),
        "usage": [
            "{tr}digest",
            "{tr}digest me",
            "{tr}digest here",
            "{tr}digest auto on",
            "{tr}digest auto off",
            "{tr}digest time 8 0",
            "{tr}digest status",
        ],
        "examples": [
            "{tr}digest",
            "{tr}digest time 9 15",
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
                5,
            )
        if toggle == "off":
            addgvar("DIGEST_AUTO", "false")
            if _scheduler and _scheduler.running:
                _scheduler.shutdown(wait=False)
            return await edit_delete(event, "**Digest auto:** OFF", 5)

    if parts and parts[0] == "status":
        auto = _digest_auto()
        sched = _ensure_scheduler()
        job = sched.get_job("daily_digest") if sched else None
        nxt = job.next_run_time if job else None
        nxt_str = nxt.strftime("%Y-%m-%d %H:%M %Z") if nxt else "not scheduled"
        return await edit_or_reply(
            event,
            f"**Digest status**\n"
            f"Auto: {'ON' if auto else 'OFF'}\n"
            f"Schedule: `{_schedule_time_label()}`\n"
            f"Next run: {nxt_str}\n"
            f"Target: Saved Messages (`me`)\n"
            f"PM log: {digest_sql.pm_log_count()} entries",
        )

    if parts and parts[0] == "time":
        if len(parts) < 3:
            return await edit_delete(
                event,
                "**Usage:** `.digest time <hour> <minute>`\n"
                "**Example:** `.digest time 8 0` (8:00 AM Addis)",
            )
        try:
            hour = max(0, min(int(parts[1]), 23))
            minute = max(0, min(int(parts[2]), 59))
        except ValueError:
            return await edit_delete(event, "**Hour and minute must be numbers.**")
        addgvar("DIGEST_HOUR", str(hour))
        addgvar("DIGEST_MINUTE", str(minute))
        sched = _ensure_scheduler()
        _reschedule_digest_job(sched)
        if _digest_auto() and not sched.running:
            sched.start()
        job = sched.get_job("daily_digest")
        nxt = job.next_run_time.strftime("%Y-%m-%d %H:%M %Z") if job and job.next_run_time else "—"
        return await edit_delete(
            event,
            f"**Digest schedule set:** `{hour:02d}:{minute:02d}` Addis Ababa\n"
            f"Next run: {nxt}",
            8,
        )

    if parts and parts[0] == "here":
        catevent = await edit_or_reply(event, "**Building briefing...**")
        await send_digest(event.client, event.chat_id)
        return await catevent.delete()

    # Default and explicit "me" → Saved Messages
    catevent = await edit_or_reply(event, "**Building briefing...**")
    await send_digest(event.client, "me")
    await catevent.delete()


@catub.on(events.NewMessage(incoming=True))
async def digest_pm_logger(event):
    """Log PMs while owner is AFK for digest."""
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
    with contextlib.suppress(Exception):
        if _digest_auto():
            _ensure_scheduler()


_init_digest_scheduler()
