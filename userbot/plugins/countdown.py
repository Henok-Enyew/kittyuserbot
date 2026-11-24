# Live countdowns — a message that keeps updating itself until the moment arrives.
#
#   .countdown genna                       Ethiopian holiday by name (see .holidays)
#   .countdown 2026-12-31 23:59 | New Year  a date (and time), optional "| title"
#   .countdown 2h30m | pizza               a duration / 18:30 / tomorrow 9am
#   .countdowns                            list    .countdown stop [n|all] (or reply)
#
# Countdowns are stored in the database and resume after restarts.

import contextlib
import re
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telethon.errors import FloodWaitError, MessageIdInvalidError, MessageNotModifiedError, RPCError

from userbot import catub

from ..Config import Config
from ..core.logger import logging
from ..core.managers import edit_delete, edit_or_reply
from ..helpers.functions.digest_builder import ADDIS_TZ
from ..helpers.functions.ethiocal import HOLIDAY_KEYS, MONTHS_AM, next_holiday, to_ethiopian
from ..helpers.functions.kittychat import esc
from ..helpers.functions.kittytime import fmt_local, now_local, now_utc, split_when, to_local
from ..sql_helper.kitty_kv_sql import kv_get_json, kv_set_json

plugin_category = "utils"
LOGS = logging.getLogger(__name__)

_KEY = "COUNTDOWNS"
MAX_ACTIVE = 10
ALIASES = {"newyear": "enkutatash", "christmas": "genna", "easter": "fasika", "eid": "eid-fitr", "arefa": "eid-adha"}
_DATE = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})(?:\s+(\d{1,2}):(\d{2}))?$|^(\d{1,2})/(\d{1,2})/(\d{4})(?:\s+(\d{1,2}):(\d{2}))?$")
_sched = None


def _load() -> list:
    try:
        return kv_get_json(_KEY, []) or []
    except Exception:
        return []


def _save(items: list):
    kv_set_json(_KEY, items)


def _bar(frac: float, width=12) -> str:
    frac = min(max(frac, 0.0), 1.0)
    full = int(round(frac * width))
    return "▰" * full + "▱" * (width - full)


def _render(cd: dict) -> str:
    target = datetime.fromtimestamp(cd["t"], timezone.utc)
    left = (target - now_utc()).total_seconds()
    local = to_local(target)
    y, m, d = to_ethiopian(local.date())
    when = f"🗓 {local:%a %d %b %Y %H:%M} · {MONTHS_AM[m - 1]} {d} {y}"
    title = esc(cd["title"])
    if left <= 0:
        return f"🎉 <b>{title}</b>\n\n<b>It's time!</b>\n{when}"
    days, rem = divmod(int(left), 86400)
    hours, rem = divmod(rem, 3600)
    mins = rem // 60
    if days:
        big = f"<b>{days}</b> day{'s' if days != 1 else ''}  <b>{hours:02d}</b> h  <b>{mins:02d}</b> min"
    elif hours:
        big = f"<b>{hours}</b> h  <b>{mins:02d}</b> min"
    else:
        big = f"<b>{max(mins, 1)}</b> min" if left >= 60 else "<b>less than a minute</b>"
    total = max(cd["t"] - cd["s"], 1)
    frac = 1 - left / total
    return f"⏳ <b>{title}</b>\n\n{big}\n{_bar(frac)} {frac * 100:.0f}%\n{when}"


async def _tick():
    items = _load()
    if not items:
        return
    dropped = set()
    minute = now_utc().minute
    for cd in items:
        left = cd["t"] - now_utc().timestamp()
        # far-away countdowns only need an edit every 5 minutes
        if left > 86400 and minute % 5:
            continue
        try:
            await catub.edit_message(cd["c"], cd["m"], _render(cd), parse_mode="html")
        except MessageNotModifiedError:
            pass
        except (MessageIdInvalidError, ValueError):
            dropped.add((cd["c"], cd["m"]))  # message deleted -> drop the countdown
            continue
        except FloodWaitError:
            pass
        except RPCError as e:
            LOGS.debug(f"countdown edit failed: {e}")
        if left <= 0:
            dropped.add((cd["c"], cd["m"]))
            with contextlib.suppress(Exception):
                await catub.send_message(cd["c"], f"🎉 <b>{esc(cd['title'])}</b> — it's time!", parse_mode="html", reply_to=cd["m"])
    if dropped:
        # reload: a countdown may have been added while we were editing
        _save([cd for cd in _load() if (cd["c"], cd.get("m")) not in dropped])


def _ensure_sched():
    global _sched
    if _sched is None:
        _sched = AsyncIOScheduler(timezone=ADDIS_TZ)
        _sched.add_job(_tick, "interval", seconds=60, id="countdown_tick", replace_existing=True, max_instances=1, coalesce=True)
    if not _sched.running:
        _sched.start()
    return _sched


def _schedule_finish(cd):
    """Fire one extra tick exactly at the target so 'It's time!' isn't up to a minute late."""
    sched = _ensure_sched()
    run = datetime.fromtimestamp(cd["t"] + 1, timezone.utc)
    if run > now_utc():
        sched.add_job(_tick, "date", run_date=run, id=f"cd_{cd['c']}_{cd['m']}", replace_existing=True)


try:
    if _load():
        _ensure_sched()
        for _cd in _load():
            _schedule_finish(_cd)
except Exception as e:
    LOGS.error(f"countdown init failed: {e}")


def _parse_target(raw: str):
    """-> (aware UTC datetime, default title) or (None, error)."""
    head = raw.split()[0].lower() if raw.split() else ""
    key = ALIASES.get(head, head)
    if key in HOLIDAY_KEYS:
        h = next_holiday(key, now_local().date())
        if h:
            start = datetime(h[0].year, h[0].month, h[0].day, tzinfo=ADDIS_TZ)
            if start <= now_local():
                h = next_holiday(key, now_local().date() + timedelta(days=1))
                start = datetime(h[0].year, h[0].month, h[0].day, tzinfo=ADDIS_TZ)
            return start.astimezone(timezone.utc), f"{h[3]} · {h[2]}{' ≈' if h[4] else ''}"
    m = _DATE.match(raw.strip())
    if m:
        g = m.groups()
        if g[0]:
            y, mo, d, hh, mm = int(g[0]), int(g[1]), int(g[2]), g[3], g[4]
        else:
            d, mo, y, hh, mm = int(g[5]), int(g[6]), int(g[7]), g[8], g[9]
        try:
            dt = datetime(y, mo, d, int(hh or 0), int(mm or 0), tzinfo=ADDIS_TZ)
        except ValueError as e:
            return None, str(e)
        return dt.astimezone(timezone.utc), dt.strftime("%d %b %Y")
    when, rest = split_when(raw)
    if when and not rest:
        return when, fmt_local(when)
    return None, "Couldn't read the time"


@catub.cat_cmd(
    pattern=r"countdown(?:\s+([\s\S]+))?$",
    command=("countdown", plugin_category),
    info={
        "header": "A live countdown message that updates itself.",
        "description": "Targets: an Ethiopian holiday name (genna, timket, fasika, meskel, enkutatash, "
        "eid-fitr, eid-adha, adwa, ...), a date like 2026-12-31 or 31/12/2026 with optional HH:MM, "
        "or a time like 2h30m / 18:30 / tomorrow 9am. Add '| title' for a custom title. "
        "It survives restarts; delete the message or use stop to end it.",
        "usage": ["{tr}countdown <target> [| title]", "{tr}countdown stop [n|all]  (or reply to it)"],
        "examples": [
            "{tr}countdown genna",
            "{tr}countdown 2026-12-31 23:59 | New Year 🎆",
            "{tr}countdown 45m | exam starts",
        ],
    },
)
async def countdown_cmd(event):
    "Live countdown."
    raw = (event.pattern_match.group(1) or "").strip()
    items = _load()

    if raw.lower().startswith("stop"):
        arg = raw[4:].strip().lower()
        reply = await event.get_reply_message()
        if arg == "all":
            gone = [cd for cd in items if cd["c"] == event.chat_id]
            items = [cd for cd in items if cd["c"] != event.chat_id]
        elif reply:
            gone = [cd for cd in items if cd["c"] == event.chat_id and cd["m"] == reply.id]
            items = [cd for cd in items if cd not in gone]
        elif arg.isdigit() and 1 <= int(arg) <= len(items):
            gone = [items.pop(int(arg) - 1)]
        else:
            return await edit_delete(event, "`Reply to a countdown, or give its number from .countdowns, or all.`", 8)
        _save(items)
        return await edit_delete(event, f"⏹ Stopped {len(gone)} countdown{'s' if len(gone) != 1 else ''}.", 5)

    if not raw:
        return await edit_delete(event, f"`Usage: {Config.COMMAND_HAND_LER}countdown genna | 2026-12-31 | 2h [| title]`", 8)
    if len(items) >= MAX_ACTIVE:
        return await edit_delete(event, f"`Max {MAX_ACTIVE} live countdowns. Stop one first.`", 6)

    target_raw, _, title = raw.partition("|")
    target, default_title = _parse_target(target_raw.strip())
    if target is None:
        return await edit_delete(event, f"`{default_title}. Try genna, 2026-12-31 18:00 or 2h.`", 8)
    if target <= now_utc() + timedelta(seconds=30):
        return await edit_delete(event, "`That time has already passed.`", 6)

    cd = {"t": target.timestamp(), "s": now_utc().timestamp(), "title": title.strip() or default_title, "c": event.chat_id}
    msg = await event.client.send_message(event.chat_id, _render(cd), parse_mode="html", reply_to=event.reply_to_msg_id)
    cd["m"] = msg.id
    items.append(cd)
    _save(items)
    _schedule_finish(cd)
    if event.out:
        with contextlib.suppress(Exception):
            await event.delete()


@catub.cat_cmd(
    pattern=r"countdowns$",
    command=("countdowns", plugin_category),
    info={"header": "List live countdowns.", "usage": "{tr}countdowns"},
)
async def countdowns_cmd(event):
    "List countdowns."
    items = _load()
    if not items:
        return await edit_delete(event, "No live countdowns.", 5)
    lines = ["⏳ <b>Live countdowns</b>\n"]
    for i, cd in enumerate(items, 1):
        target = datetime.fromtimestamp(cd["t"], timezone.utc)
        lines.append(f"<code>{i}</code> {esc(cd['title'])} — {fmt_local(target)} · chat <code>{cd['c']}</code>")
    lines.append(f"\n<code>{Config.COMMAND_HAND_LER}countdown stop &lt;n&gt;</code>")
    await edit_or_reply(event, "\n".join(lines), parse_mode="html")
