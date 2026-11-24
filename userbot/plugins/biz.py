# Free "Telegram Business" — away messages outside working hours and greetings for new
# or returning chats. (Telegram sells these as Premium Business features.)
#
#   .biz on | off                          master switch
#   .biz hours 09:00-18:00 mon-fri         working hours (Addis time; overnight ranges work)
#   .biz away <text> | off                 auto-reply outside working hours
#   .biz greet <text> | off                greet people who message after N quiet days
#   .biz greetdays 14                      what counts as "returning"
#   .biz contacts skip | include           ignore your contacts?
#   .biz test                              preview      .biz   status
#
# Placeholders: {name} {first} {back} (when you're back, e.g. "Mon 09:00")

import json
import time
from datetime import timedelta

from telethon import events

from userbot import catub

from ..Config import Config
from ..core.logger import logging
from ..core.managers import edit_delete, edit_or_reply
from ..helpers.functions.kittychat import name_of
from ..helpers.functions.kittytime import now_local
from ..sql_helper.globals import addgvar, gvarstatus

plugin_category = "utils"
LOGS = logging.getLogger(__name__)

DAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DEFAULTS = {
    "on": False,
    "away": "Hi {first}! I'm offline right now 🌙 I'll get back to you {back}.",
    "greet": "Hey {first}! 👋 Thanks for your message, I'll reply as soon as I can.",
    "start": "09:00",
    "end": "18:00",
    "days": [0, 1, 2, 3, 4],
    "greet_days": 14,
    "skip_contacts": False,
}
_cfg = dict(DEFAULTS)
_last_away, _last_greet = {}, {}


def _load():
    try:
        _cfg.update(json.loads(gvarstatus("BIZ_STATE") or "{}"))
    except Exception:
        pass


def _save():
    addgvar("BIZ_STATE", json.dumps(_cfg, ensure_ascii=False))


_load()


def _mins(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _is_open(dt) -> bool:
    start, end, t = _mins(_cfg["start"]), _mins(_cfg["end"]), dt.hour * 60 + dt.minute
    if start == end:
        return dt.weekday() in _cfg["days"]
    if start < end:
        return dt.weekday() in _cfg["days"] and start <= t < end
    # overnight shift, e.g. 22:00-06:00: belongs to the day it started
    if t >= start:
        return dt.weekday() in _cfg["days"]
    return t < end and (dt.weekday() - 1) % 7 in _cfg["days"]


def _next_open(now):
    if _is_open(now):
        return "soon"
    probe = now.replace(second=0, microsecond=0)
    for _ in range(7 * 24 * 4):  # 15-minute steps, one week
        probe += timedelta(minutes=15)
        if _is_open(probe):
            if probe.date() == now.date():
                return f"today at {probe:%H:%M}"
            if probe.date() == now.date() + timedelta(days=1):
                return f"tomorrow at {probe:%H:%M}"
            return f"on {probe:%A} at {probe:%H:%M}"
    return "soon"


def _fill(text: str, user) -> str:
    return (
        text.replace("{name}", name_of(user, "there"))
        .replace("{first}", (getattr(user, "first_name", None) or name_of(user, "there")).strip())
        .replace("{back}", _next_open(now_local()))
    )


def _days_label() -> str:
    d = sorted(_cfg["days"])
    if d == list(range(7)):
        return "every day"
    if d == list(range(5)):
        return "Mon–Fri"
    return ", ".join(DAY_NAMES[i].title() for i in d)


@catub.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def _biz_watcher(event):
    if not _cfg["on"]:
        return
    sender = await event.get_sender()
    if not sender or sender.bot or sender.is_self or sender.id == 777000 or sender.verified:
        return
    if _cfg["skip_contacts"] and sender.contact:
        return
    now, chat = time.time(), event.chat_id
    parts = []

    if _cfg["greet"] and now - _last_greet.get(chat, 0) > 86400:
        try:
            msgs = await event.client.get_messages(chat, limit=2)
            prev = msgs[1] if len(msgs) > 1 else None
            if prev is None or (event.date - prev.date).days >= int(_cfg["greet_days"]):
                parts.append(_fill(_cfg["greet"], sender))
                _last_greet[chat] = now
        except Exception as e:
            LOGS.debug(f"biz greet check failed: {e}")

    if _cfg["away"] and not _is_open(now_local()) and now - _last_away.get(chat, 0) > 6 * 3600:
        parts.append(_fill(_cfg["away"], sender))
        _last_away[chat] = now

    if parts:
        try:
            await event.reply("\n\n".join(parts))
        except Exception as e:
            LOGS.debug(f"biz reply failed: {e}")


def _parse_days(tok: str):
    tok = tok.lower()
    if tok in ("everyday", "daily", "all", "mon-sun"):
        return list(range(7))
    if tok in ("weekdays", "mon-fri"):
        return list(range(5))
    if tok in ("weekend", "weekends", "sat-sun"):
        return [5, 6]
    if "-" in tok:
        a, b = tok.split("-", 1)
        if a[:3] in DAY_NAMES and b[:3] in DAY_NAMES:
            i, j = DAY_NAMES.index(a[:3]), DAY_NAMES.index(b[:3])
            return [(i + k) % 7 for k in range((j - i) % 7 + 1)]
    days = [DAY_NAMES.index(p[:3]) for p in tok.split(",") if p[:3] in DAY_NAMES]
    return days or None


@catub.cat_cmd(
    pattern=r"biz(?:\s+([\s\S]+))?$",
    command=("biz", plugin_category),
    info={
        "header": "Business-style auto replies for private chats (free).",
        "description": "Away message: sent when someone writes outside your working hours "
        "(once per chat every 6h). Greeting: sent when someone writes for the first time or after "
        "N quiet days (default 14). Bots, Telegram and verified accounts are ignored. "
        "Placeholders: {name}, {first}, {back}.",
        "options": {
            "on / off": "master switch",
            "hours 09:00-18:00 mon-fri": "working hours, Addis time",
            "away <text> / away off": "outside-hours reply",
            "greet <text> / greet off": "greeting",
            "greetdays <n>": "quiet days before greeting again",
            "contacts skip / include": "ignore your contacts",
            "test": "preview the messages",
        },
        "usage": "{tr}biz [option]",
        "examples": ["{tr}biz hours 08:30-17:30 mon-sat", "{tr}biz away Out of office 🌴 back {back}", "{tr}biz on"],
    },
)
async def biz_cmd(event):
    "Business auto replies."
    raw = (event.pattern_match.group(1) or "").strip()
    sub, _, rest = raw.partition(" ")
    sub, rest = sub.lower(), rest.strip()

    if sub in ("on", "off"):
        _cfg["on"] = sub == "on"
        _save()
        return await edit_delete(event, f"💼 Business replies **{sub}**.", 5)
    if sub == "hours":
        parts = rest.split()
        try:
            start, end = parts[0].split("-")
            _mins(start), _mins(end)
            days = _parse_days(parts[1]) if len(parts) > 1 else _cfg["days"]
            if not days:
                raise ValueError
        except Exception:
            return await edit_delete(event, "`Use: .biz hours 09:00-18:00 mon-fri`", 8)
        _cfg.update(start=start, end=end, days=days)
        _save()
        return await edit_delete(event, f"🕘 Working hours: **{start}–{end}**, {_days_label()}.", 6)
    if sub in ("away", "greet"):
        if not rest:
            return await edit_delete(event, f"`Give the text, or '{sub} off'.`", 6)
        _cfg[sub] = None if rest.lower() == "off" else rest
        _save()
        return await edit_delete(event, f"✅ {sub.title()} message {'disabled' if _cfg[sub] is None else 'saved'}.", 5)
    if sub == "greetdays" and rest.isdigit():
        _cfg["greet_days"] = int(rest)
        _save()
        return await edit_delete(event, f"✅ Greeting after {rest} quiet days.", 5)
    if sub == "contacts" and rest in ("skip", "include"):
        _cfg["skip_contacts"] = rest == "skip"
        _save()
        return await edit_delete(event, f"✅ Contacts will be {'skipped' if rest == 'skip' else 'included'}.", 5)
    if sub == "test":
        me = await event.client.get_me()
        out = []
        if _cfg["greet"]:
            out.append(f"**Greeting:**\n{_fill(_cfg['greet'], me)}")
        if _cfg["away"]:
            out.append(f"**Away:**\n{_fill(_cfg['away'], me)}")
        return await edit_or_reply(event, "\n\n".join(out) or "Both messages are off.")

    status = "🟢 on" if _cfg["on"] else "⚪ off"
    open_now = "open" if _is_open(now_local()) else f"closed (back {_next_open(now_local())})"
    await edit_or_reply(
        event,
        f"💼 **Business replies** — {status}\n"
        f"🕘 Hours: `{_cfg['start']}–{_cfg['end']}`, {_days_label()} · now {open_now}\n"
        f"🌙 Away: {('`' + _cfg['away'] + '`') if _cfg['away'] else 'off'}\n"
        f"👋 Greeting (after {_cfg['greet_days']} quiet days): {('`' + _cfg['greet'] + '`') if _cfg['greet'] else 'off'}\n"
        f"👥 Contacts: {'skipped' if _cfg['skip_contacts'] else 'included'}\n\n"
        f"`{Config.COMMAND_HAND_LER}help -c biz` for all options",
    )
