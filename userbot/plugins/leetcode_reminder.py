# LeetCode twice-daily reminder — 14:00 & 21:00 Africa/Addis_Ababa (UTC+3)

import contextlib

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from userbot import catub
from userbot.Config import Config
from userbot.core.logger import logging
from userbot.core.managers import edit_delete, edit_or_reply
from userbot.helpers.functions.digest_builder import ADDIS_TZ, addis_now
from userbot.helpers.functions.leetcode_checker import (
    _leetcode_username,
    solved_today,
    today_status_text,
)
from userbot.sql_helper.globals import addgvar, gvarstatus

plugin_category = "utils"
LOGS = logging.getLogger(__name__)

_scheduler = None

AFTERNOON_HOUR = 14
NIGHT_HOUR = 21
REMIND_MINUTE = 0


def _remind_auto() -> bool:
    val = gvarstatus("LEETCODE_REMIND_AUTO")
    if val is None:
        raw = getattr(Config, "LEETCODE_REMIND_AUTO", "true")
        return str(raw).lower() not in ("false", "0", "off", "no")
    return str(val).lower() not in ("false", "0", "off", "no")


def _owner_id() -> int:
    return Config.OWNER_ID if Config.OWNER_ID else catub.uid


def _group_id() -> int:
    gid = int(Config.PRIVATE_GROUP_BOT_API_ID or 0)
    if gid == 0:
        gid = int(gvarstatus("PRIVATE_GROUP_BOT_API_ID") or 0)
    return gid


def _mention_html() -> str:
    name = Config.ALIVE_NAME or "Henok"
    oid = _owner_id()
    return f'<a href="tg://user?id={oid}">{name}</a>'


def _build_reminder_text(period_label: str) -> str:
    username = _leetcode_username()
    mention = _mention_html()
    today_str = addis_now().strftime("%Y-%m-%d")
    profile = f"https://leetcode.com/u/{username}/"
    return (
        f"⚠️ <b>LeetCode reminder</b> ({period_label})\n\n"
        f"{mention}, you have <b>not solved any LeetCode problem today</b> "
        f"({today_str}, UTC+3).\n\n"
        f"Keep your streak — solve at least one before the day ends.\n"
        f"Profile: <a href=\"{profile}\">{username}</a>"
    )


async def _send_reminder(period_label: str) -> bool:
    """Send reminder to group + Saved Messages. Returns True if sent."""
    text = _build_reminder_text(period_label)
    group_id = _group_id()
    sent_any = False

    if group_id:
        try:
            await catub.send_message(
                group_id,
                text,
                parse_mode="html",
                link_preview=False,
            )
            sent_any = True
        except Exception as e:
            LOGS.error(f"leetcode reminder group send failed: {e}")
    else:
        LOGS.warning(
            "leetcode reminder: PRIVATE_GROUP_BOT_API_ID not set — skipping group"
        )

    try:
        await catub.send_message(
            "me",
            text,
            parse_mode="html",
            link_preview=False,
        )
        sent_any = True
    except Exception as e:
        LOGS.error(f"leetcode reminder saved-messages send failed: {e}")

    return sent_any


async def _run_reminder_check(period_label: str) -> None:
    if not _remind_auto():
        LOGS.info("leetcode reminder skipped (auto off)")
        return

    username = _leetcode_username()
    try:
        solved, titles = solved_today(username)
    except Exception as e:
        LOGS.error(f"leetcode check failed: {e}")
        return

    if solved:
        LOGS.info(
            f"leetcode reminder skipped — already solved today ({len(titles)}): "
            f"{', '.join(titles[:3])}"
        )
        return

    LOGS.info(f"leetcode reminder firing ({period_label})")
    await _send_reminder(period_label)


async def _scheduled_afternoon():
    try:
        await _run_reminder_check("2 PM")
    except Exception as e:
        LOGS.error(f"leetcode afternoon reminder failed: {e}")


async def _scheduled_night():
    try:
        await _run_reminder_check("9 PM")
    except Exception as e:
        LOGS.error(f"leetcode night reminder failed: {e}")


def _reschedule_jobs(sched: AsyncIOScheduler) -> None:
    sched.add_job(
        _scheduled_afternoon,
        "cron",
        hour=AFTERNOON_HOUR,
        minute=REMIND_MINUTE,
        id="leetcode_remind_afternoon",
        replace_existing=True,
    )
    sched.add_job(
        _scheduled_night,
        "cron",
        hour=NIGHT_HOUR,
        minute=REMIND_MINUTE,
        id="leetcode_remind_night",
        replace_existing=True,
    )


def _ensure_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone=ADDIS_TZ)
    try:
        _reschedule_jobs(_scheduler)
    except Exception as e:
        LOGS.error(f"leetcode scheduler reschedule failed: {e}")
    if _remind_auto() and not _scheduler.running:
        try:
            _scheduler.start()
        except Exception as e:
            LOGS.error(f"leetcode scheduler start failed: {e}")
    return _scheduler


def _next_runs_label(sched: AsyncIOScheduler | None) -> str:
    if not sched:
        return "scheduler not initialized"
    times = []
    for jid in ("leetcode_remind_afternoon", "leetcode_remind_night"):
        job = sched.get_job(jid)
        if job and job.next_run_time:
            times.append(job.next_run_time.strftime("%Y-%m-%d %H:%M %Z"))
    return " | ".join(times) if times else "not scheduled"


def _schedule_label() -> str:
    return (
        f"{AFTERNOON_HOUR:02d}:{REMIND_MINUTE:02d} & "
        f"{NIGHT_HOUR:02d}:{REMIND_MINUTE:02d} Africa/Addis_Ababa (UTC+3)"
    )


@catub.cat_cmd(
    pattern=r"lcstatus$",
    command=("lcstatus", plugin_category),
    info={
        "header": "LeetCode — today's solve status (Addis timezone)",
        "usage": "{tr}lcstatus",
        "examples": "{tr}lcstatus",
    },
)
async def lcstatus_cmd(event):
    "LeetCode today status."
    await edit_or_reply(event, today_status_text())


@catub.cat_cmd(
    pattern=r"lcremind$",
    command=("lcremind", plugin_category),
    info={
        "header": "Force LeetCode reminder check now",
        "description": (
            "Checks if you solved today; if not, sends reminder to your private "
            "bot group (with mention) and Saved Messages."
        ),
        "usage": "{tr}lcremind",
    },
)
async def lcremind_cmd(event):
    "Force reminder check."
    catevent = await edit_or_reply(event, "**Checking LeetCode…**")
    username = _leetcode_username()
    try:
        solved, titles = solved_today(username)
    except Exception as e:
        return await edit_delete(catevent, f"**Check failed:** `{e}`", 12)

    if solved:
        return await catevent.edit(
            f"**Already solved today** ({len(titles)})\n"
            + "\n".join(f"• {t}" for t in titles)
        )

    sent = await _send_reminder("manual")
    if sent:
        await catevent.edit(
            "**Reminder sent** to private group + Saved Messages."
        )
    else:
        await catevent.edit(
            "**Could not send reminder** — check PRIVATE_GROUP_BOT_API_ID and logs."
        )


@catub.cat_cmd(
    pattern=r"lcset(?:\s+(.+))?$",
    command=("lcset", plugin_category),
    info={
        "header": "Configure LeetCode reminder scheduler",
        "usage": [
            "{tr}lcset on",
            "{tr}lcset off",
            "{tr}lcset times",
        ],
        "examples": ["{tr}lcset on", "{tr}lcset times"],
    },
)
async def lcset_cmd(event):
    "LeetCode reminder settings."
    raw = (event.pattern_match.group(1) or "").strip().lower()
    sched = _ensure_scheduler()

    if raw == "on":
        addgvar("LEETCODE_REMIND_AUTO", "true")
        if not sched.running:
            sched.start()
        return await edit_delete(
            event,
            f"**LeetCode reminders:** ON\nSchedule: `{_schedule_label()}`",
            8,
        )

    if raw == "off":
        addgvar("LEETCODE_REMIND_AUTO", "false")
        if sched.running:
            with contextlib.suppress(Exception):
                sched.shutdown(wait=False)
        return await edit_delete(event, "**LeetCode reminders:** OFF", 6)

    if raw == "times" or not raw:
        auto = "ON" if _remind_auto() else "OFF"
        gid = _group_id()
        return await edit_or_reply(
            event,
            f"**LeetCode reminder config**\n"
            f"Auto: **{auto}**\n"
            f"Username: `{_leetcode_username()}`\n"
            f"Group: `{gid or 'not set'}`\n"
            f"Schedule: `{_schedule_label()}`\n"
            f"Next runs: `{_next_runs_label(sched)}`",
        )

    await edit_delete(
        event,
        "**Usage:** `.lcset on` | `.lcset off` | `.lcset times`",
        8,
    )


def _init_leetcode_scheduler():
    try:
        if _remind_auto():
            _ensure_scheduler()
    except Exception as e:
        LOGS.error(f"leetcode scheduler init skipped: {e}")


try:
    _init_leetcode_scheduler()
except Exception as e:
    LOGS.error(f"leetcode module scheduler init failed: {e}")
