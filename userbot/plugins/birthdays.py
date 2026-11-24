# Birthdays — uses the birthday field Telegram added to profiles in 2024.
#
#   .bdays [refresh]           upcoming birthdays of your contacts
#   .bdwish                    status
#   .bdwish remind|auto|off    daily 08:00 check: remind you (default) / auto-send wishes / nothing
#   .bdwish msg <template>     wish text; {name} {first} {age}
#   .bdwish send               wish everyone whose birthday is today, now
#   .bdwish test               preview the wish

import asyncio
import contextlib
import random
from datetime import date, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telethon.errors import FloodWaitError, RPCError
from telethon.tl import functions, types

from userbot import catub

from ..Config import Config
from ..core.logger import logging
from ..core.managers import edit_delete, edit_or_reply
from ..helpers.functions.digest_builder import ADDIS_TZ
from ..helpers.functions.kittychat import esc, mention_html, name_of
from ..helpers.functions.kittytime import now_local
from ..sql_helper.kitty_kv_sql import kv_get, kv_get_json, kv_set, kv_set_json

plugin_category = "utils"
LOGS = logging.getLogger(__name__)

DEFAULT_WISH = "Happy birthday {first}! 🎂🎉 Wishing you an amazing year full of good things!"
WISH_HOUR = 8
_scheduler = None


def _mode() -> str:
    return (kv_get("BDWISH_MODE") or getattr(Config, "BDWISH_MODE", "remind")).lower()


def _template() -> str:
    return kv_get("BDWISH_MSG") or DEFAULT_WISH


def _age(b) -> int | None:
    if not b.year:
        return None
    today = now_local().date()
    return today.year - b.year - ((today.month, today.day) < (b.month, b.day))


def _next_occurrence(day: int, month: int, today: date) -> date:
    for year in (today.year, today.year + 1, today.year + 2):
        try:
            d = date(year, month, day)
        except ValueError:  # 29 Feb
            d = date(year, 3, 1)
        if d >= today:
            return d
    return today


def _render_wish(user, b) -> str:
    age = _age(b)
    text = _template()
    return (
        text.replace("{name}", name_of(user))
        .replace("{first}", (user.first_name or name_of(user)).strip())
        .replace("{age}", str(age) if age is not None else "")
    )


async def _todays_birthdays(client):
    """[(user, Birthday)] whose birthday is today (Addis time), via contacts.getBirthdays."""
    res = await client(functions.contacts.GetBirthdaysRequest())
    users = {u.id: u for u in res.users}
    today = now_local().date()
    return [
        (users[c.contact_id], c.birthday)
        for c in res.contacts
        if c.contact_id in users and c.birthday.day == today.day and c.birthday.month == today.month
    ]


async def _send_wish(client, user, b) -> bool:
    text = _render_wish(user, b)
    peer = await client.get_input_entity(user)
    effect = None
    with contextlib.suppress(Exception):
        res = await client(functions.messages.GetAvailableEffectsRequest(hash=0))
        effect = next(
            (e.id for e in res.effects if e.emoticon.replace("️", "") == "🎉" and not e.premium_required), None
        )
    try:
        await client(functions.messages.SendMessageRequest(peer=peer, message=text, effect=effect))
    except RPCError:
        try:
            await client.send_message(user.id, text)
        except Exception as e:
            LOGS.error(f"birthday wish to {user.id} failed: {e}")
            return False
    return True


def _sent_today() -> set:
    data = kv_get_json("BDWISH_SENT", {}) or {}
    return set(data.get(now_local().date().isoformat(), []))


def _mark_sent(ids):
    today = now_local().date().isoformat()
    kv_set_json("BDWISH_SENT", {today: sorted(_sent_today() | set(ids))})


async def _daily_check(force=False):
    mode = _mode()
    today = now_local().date().isoformat()
    if mode == "off" or (not force and kv_get("BDWISH_LAST") == today):
        return
    try:
        people = await _todays_birthdays(catub)
    except Exception as e:
        LOGS.error(f"birthday check failed: {e}")
        return
    kv_set("BDWISH_LAST", today)
    if not people:
        return
    lines = ["🎂 <b>Birthdays today</b>\n"]
    sent = []
    done = _sent_today()
    for user, b in people:
        age = _age(b)
        turns = f" — turns {age}" if age else ""
        status = ""
        if mode == "auto" and user.id not in done:
            ok = await _send_wish(catub, user, b)
            status = " ✅ wished" if ok else " ⚠️ wish failed"
            if ok:
                sent.append(user.id)
            await asyncio.sleep(random.uniform(2, 5))
        elif user.id in done:
            status = " ✅ already wished"
        lines.append(f"• {mention_html(user)}{turns}{status}")
    if sent:
        _mark_sent(sent)
    if mode != "auto":
        lines.append(f"\nSend wishes: <code>{Config.COMMAND_HAND_LER}bdwish send</code>")
    with contextlib.suppress(Exception):
        await catub.send_message("me", "\n".join(lines), parse_mode="html")


def _ensure_scheduler():
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone=ADDIS_TZ)
        _scheduler.add_job(_daily_check, "cron", hour=WISH_HOUR, minute=0, id="bdwish_daily", replace_existing=True)
        # catch up if the container (re)started after 08:00
        if now_local().hour >= WISH_HOUR:
            _scheduler.add_job(
                _daily_check, "date", run_date=datetime.now(ADDIS_TZ) + timedelta(seconds=90), id="bdwish_catchup"
            )
    if not _scheduler.running:
        _scheduler.start()
    return _scheduler


try:
    if _mode() != "off":
        _ensure_scheduler()
except Exception as e:
    LOGS.error(f"birthday scheduler init failed: {e}")


# ─────────────────────────────── .bdays ───────────────────────────────


async def _scan_contacts(client, status):
    """Birthdays of all contacts via users.getFullUser (cached for 7 days)."""
    res = await client(functions.contacts.GetContactsRequest(hash=0))
    users = [u for u in getattr(res, "users", []) if not u.bot and not u.deleted]
    found = {}
    for i, u in enumerate(users, 1):
        try:
            full = await client(functions.users.GetFullUserRequest(types.InputUser(u.id, u.access_hash)))
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds + 1)
            continue
        except RPCError:
            continue
        b = getattr(full.full_user, "birthday", None)
        if b:
            found[str(u.id)] = {"name": name_of(u), "d": b.day, "m": b.month, "y": b.year}
        if i % 25 == 0:
            with contextlib.suppress(Exception):
                await status.edit(f"`Scanning contacts… {i}/{len(users)}`")
        await asyncio.sleep(0.4)
    kv_set_json("BDAY_CACHE", {"at": now_local().date().isoformat(), "people": found})
    return found


@catub.cat_cmd(
    pattern=r"bdays(?:\s+(refresh))?$",
    command=("bdays", plugin_category),
    info={
        "header": "Upcoming birthdays of your contacts.",
        "description": "Reads the birthday your contacts set on their Telegram profile. The first run scans "
        "all contacts (slow; results are cached for 7 days).",
        "usage": ["{tr}bdays", "{tr}bdays refresh"],
    },
)
async def bdays_cmd(event):
    "Upcoming birthdays."
    refresh = bool(event.pattern_match.group(1))
    status = await edit_or_reply(event, "`Checking birthdays…`")
    cache = kv_get_json("BDAY_CACHE", {}) or {}
    stale = not cache or (now_local().date() - date.fromisoformat(cache.get("at", "2000-01-01"))).days >= 7
    people = await _scan_contacts(event.client, status) if refresh or stale else cache.get("people", {})
    if not people:
        return await status.edit("No contacts have shared a birthday with you (yet).")

    today = now_local().date()
    rows = []
    for uid, p in people.items():
        nxt = _next_occurrence(p["d"], p["m"], today)
        age = nxt.year - p["y"] if p.get("y") else None
        rows.append(((nxt - today).days, nxt, uid, p, age))
    rows.sort(key=lambda r: r[0])
    lines = ["🎂 <b>Upcoming birthdays</b>\n"]
    for days, nxt, uid, p, age in rows[:25]:
        when = "🎉 <b>TODAY</b>" if days == 0 else ("tomorrow" if days == 1 else f"in {days} days")
        turns = f" · turns {age}" if age else ""
        lines.append(
            f'• <a href="tg://user?id={uid}">{esc(p["name"])}</a> — {nxt:%d %b} ({when}){turns}'
        )
    lines.append(f"\n{len(people)} contacts with birthdays · daily check: <b>{_mode()}</b>")
    await status.edit("\n".join(lines), parse_mode="html")


# ────────────────────────────── .bdwish ───────────────────────────────


@catub.cat_cmd(
    pattern=r"bdwish(?:\s+([\s\S]+))?$",
    command=("bdwish", plugin_category),
    info={
        "header": "Never forget a birthday.",
        "description": "Every day at 08:00 (Addis) the bot checks your contacts' birthdays.\n"
        "remind: sends you a list in Saved Messages (default).\n"
        "auto: also sends each person your wish, with the 🎉 effect.\n"
        "Template placeholders: {name}, {first}, {age}.",
        "options": {
            "remind": "only remind me (default)",
            "auto": "auto-send wishes",
            "off": "disable",
            "msg <text>": "set the wish template",
            "send": "wish today's birthdays now",
            "test": "preview the wish on yourself",
        },
        "usage": ["{tr}bdwish", "{tr}bdwish <remind|auto|off|send|test>", "{tr}bdwish msg <template>"],
        "examples": ["{tr}bdwish auto", "{tr}bdwish msg Happy birthday {first}! 🥳 Have an awesome {age}th!"],
    },
)
async def bdwish_cmd(event):
    "Birthday wishes settings."
    raw = (event.pattern_match.group(1) or "").strip()
    sub, _, rest = raw.partition(" ")
    sub = sub.lower()

    if sub in ("remind", "auto", "off"):
        kv_set("BDWISH_MODE", sub)
        if sub == "off":
            if _scheduler and _scheduler.running:
                with contextlib.suppress(Exception):
                    _scheduler.shutdown(wait=False)
        else:
            _ensure_scheduler()
        desc = {
            "remind": "I'll list today's birthdays in Saved Messages at 08:00.",
            "auto": "I'll wish your contacts automatically at 08:00 🎉",
            "off": "Birthday checks disabled.",
        }[sub]
        return await edit_delete(event, f"🎂 **{sub}** — {desc}", 8)

    if sub == "msg":
        if not rest.strip():
            return await edit_delete(event, "`Give the template text.`", 6)
        kv_set("BDWISH_MSG", rest.strip())
        return await edit_delete(event, f"✅ Wish template saved:\n{rest.strip()}", 10)

    if sub == "test":
        me = await event.client.get_me()
        return await edit_or_reply(event, "**Preview:**\n" + _render_wish(me, types.Birthday(day=1, month=1, year=2000)))

    if sub == "send":
        status = await edit_or_reply(event, "`Checking today's birthdays…`")
        try:
            people = await _todays_birthdays(event.client)
        except RPCError as e:
            return await status.edit(f"Couldn't fetch birthdays: `{e}`")
        if not people:
            return await status.edit("No birthdays today 🎈")
        done = _sent_today()
        sent, skipped = [], 0
        for user, b in people:
            if user.id in done:
                skipped += 1
                continue
            if await _send_wish(event.client, user, b):
                sent.append(user.id)
            await asyncio.sleep(random.uniform(1.5, 3.5))
        _mark_sent(sent)
        extra = f" ({skipped} already wished today)" if skipped else ""
        return await status.edit(f"🎉 Wished {len(sent)} {'person' if len(sent) == 1 else 'people'}{extra}.")

    nxt = ""
    if _scheduler and _scheduler.get_job("bdwish_daily"):
        nxt = _scheduler.get_job("bdwish_daily").next_run_time
        nxt = f"\nNext check: `{nxt:%a %d %b %H:%M}`" if nxt else ""
    await edit_or_reply(
        event,
        f"🎂 **Birthday wishes**\nMode: **{_mode()}**\nTemplate: `{_template()}`{nxt}\n\n"
        f"`{Config.COMMAND_HAND_LER}bdwish remind|auto|off|send|test` · `{Config.COMMAND_HAND_LER}bdwish msg <text>`",
    )
