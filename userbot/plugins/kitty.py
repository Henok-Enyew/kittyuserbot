# Kitty — a pixel cat that lives in your userbot and follows your real life.
#
#   .kitty                     status card (Kitty at your window + stats)
#   .kitty on | off            adopt / pause Kitty (paused = frozen, no hunger)
#   .kitty pet | treat         care for it (cooldowns; real food = LeetCode solves)
#   .kitty name <name> | coat <coat> | public on|off | notify on|off | stats | reset
#
# Kitty eats LeetCode problems (one fish per accepted problem), sulks when your
# streak breaks, falls asleep on your keyboard if you're on Telegram at 2-5 AM,
# and grows from kitten to legend over the months. It also sits on your rooftop
# in the living profile photo (.livepfp). State: kitty_kv["KITTY_PET"].

import asyncio
import contextlib
import io
import time
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telethon import events

from userbot import catub

from ..Config import Config
from ..core.logger import logging
from ..core.managers import edit_delete, edit_or_reply
from ..helpers.functions.digest_builder import ADDIS_TZ, addis_now
from ..helpers.functions.kittychat import esc
from ..helpers.functions.kittylife import moon_name, moon_phase, note_outgoing, sky_phase
from ..helpers.functions.kittypet import COATS, STAGES, VISITOR_COOLDOWN, Kitty, bar, xp_for_level
from ..helpers.functions.kittystore import (
    kitty_signals,
    load_kitty,
    load_pfp,
    pet_lock,
    refresh_kitty,
    save_kitty,
    scene_for,
)
from ..helpers.functions.pixelscene import render_card

plugin_category = "fun"
LOGS = logging.getLogger(__name__)

TICK_MINUTES = 10
VISITOR_HOURLY_CAP = 12  # max replies to friends per hour, so a group can't spam through you
_sched = None
_visitors: dict = {}  # user_id -> last interaction (in memory)
_visitor_log: list = []  # timestamps of replies to friends in the last hour
_ON = ("on", "yes", "true", "1", "enable")
_OFF = ("off", "no", "false", "0", "disable")


def _h() -> str:
    return Config.COMMAND_HAND_LER


def _seed() -> int:
    seed = int(load_pfp().get("seed") or 0)
    return seed or (int(catub.uid or 7) % 9973)


# --------------------------------------------------------------------------- #
# Background life
# --------------------------------------------------------------------------- #


async def _tick():
    try:
        await refresh_kitty(catub)
    except Exception as e:
        LOGS.error(f"kitty tick failed: {e}")


def _ensure_sched():
    global _sched
    if _sched is None:
        _sched = AsyncIOScheduler(timezone=ADDIS_TZ)
        _sched.add_job(_tick, "interval", minutes=TICK_MINUTES, id="kitty_tick",
                       replace_existing=True, max_instances=1, coalesce=True)
    if not _sched.running:
        _sched.start()
    return _sched


try:
    _k = load_kitty()
    if _k and _k.enabled:
        _ensure_sched()
except Exception as e:
    LOGS.error(f"kitty init failed: {e}")


@catub.on(events.NewMessage(outgoing=True))
async def _kitty_activity(event):
    note_outgoing()


# --------------------------------------------------------------------------- #
# Rendering helpers
# --------------------------------------------------------------------------- #


def _stats_text(kitty: Kitty, signals) -> str:
    emoji, line = kitty.mood_line(signals)
    lc, w, p = signals.leetcode, signals.weather, signals.presence
    lo, hi = xp_for_level(kitty.level), xp_for_level(kitty.level + 1)
    seen = "now" if p.minutes_ago == 0 else (f"{p.minutes_ago} min ago" if p.minutes_ago is not None else "unknown")
    weather = f"{w.emoji} {w.kind}" + (f", {w.temp_c:.0f}°C" if w.temp_c is not None else "") if w.ok else "unavailable"
    return (
        f"{emoji} <b>{esc(kitty.name)}</b> · level {kitty.level} {kitty.stage} · {kitty.age_days} days old\n"
        f"<i>{esc(line)}</i>\n\n"
        f"🐟 Food   <code>{bar(kitty.food)}</code> {kitty.food:.0f}\n"
        f"💗 Joy    <code>{bar(kitty.joy)}</code> {kitty.joy:.0f}\n"
        f"⚡ Energy <code>{bar(kitty.energy)}</code> {kitty.energy:.0f}\n"
        f"⭐ XP     <code>{int(kitty.xp - lo)}/{hi - lo}</code> to level {kitty.level + 1}\n\n"
        f"🔥 Streak <b>{lc.streak}</b> days (best {kitty.best_streak}) · solved today <b>{lc.solved_today}</b>"
        + ("" if lc.ok else " <i>(LeetCode unreachable)</i>")
        + f"\n🌍 Addis: {weather} · {sky_phase(signals.now)}"
        + (f" · {moon_name(moon_phase(signals.now))}" if sky_phase(signals.now) == "night" else "")
        + f"\n👀 You were online {seen}"
    )


async def _send_card(event, status_msg, kitty: Kitty, signals):
    """Send the card to the command's chat, then remove the "checking..." message."""
    state = scene_for(signals, kitty, _seed())
    _, mood_text = kitty.mood_line(signals)
    extra = (("STREAK", f"{signals.leetcode.streak}D"), ("TODAY", f"{signals.leetcode.solved_today} SOLVED"),
             ("AGE", f"{kitty.age_days}D"))
    img = await asyncio.to_thread(render_card, kitty, state, mood_text, extra)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.name = "kitty.png"
    buf.seek(0)
    await event.client.send_file(event.chat_id, buf, caption=_stats_text(kitty, signals), parse_mode="html",
                                 reply_to=event.reply_to_msg_id)
    with contextlib.suppress(Exception):
        await status_msg.delete()


# --------------------------------------------------------------------------- #
# .kitty
# --------------------------------------------------------------------------- #


@catub.cat_cmd(
    pattern=r"kitty(?:\s+([\s\S]+))?$",
    command=("kitty", plugin_category),
    info={
        "header": "Kitty, a pixel cat whose life follows yours.",
        "description": (
            "Kitty eats LeetCode problems: every accepted problem is a fish. It gets hungry over a day "
            "without solving, sulks when your streak breaks, throws a party at streak milestones "
            "(3, 7, 14, 30, 50, 100...), and falls asleep on your keyboard if you're on Telegram "
            "between 2 and 5 AM. It sleeps when you're offline at night, watches the rain when it rains "
            "in Addis, and grows from kitten to young cat, adult (collar and bell) and legend (crown) "
            "as it ages and levels up. Kitty never dies. Pausing freezes it (no hunger while off). "
            "With notify on, level-ups, streak parties and hunger are noted in Saved Messages. "
            "Kitty also sits on your rooftop in the living profile photo, see .help livepfp."
        ),
        "options": {
            "(nothing)": "status card: Kitty at your window, stats, streak",
            "on / off": "adopt or wake Kitty / pause it (state is kept)",
            "pet": "pet Kitty (+joy, every 10 min)",
            "treat": "give a treat (+food, 3 a day, 3 h apart). Real food is LeetCode problems",
            "name <name>": "rename Kitty",
            "coat <coat>": f"fur: {', '.join(COATS)}",
            "public on / off": "let friends in groups use .pet / .feed (30 min cooldown each, off by default)",
            "notify on / off": "level-up, streak and hunger notes in Saved Messages",
            "stats": "lifetime stats",
            "reset": "start over with a new kitten (asks for confirmation)",
        },
        "usage": ["{tr}kitty", "{tr}kitty <option>"],
        "examples": ["{tr}kitty on", "{tr}kitty", "{tr}kitty pet", "{tr}kitty coat black", "{tr}kitty name Mimi"],
    },
)
async def kitty_cmd(event):
    "Your pixel cat."
    raw = (event.pattern_match.group(1) or "").strip()
    sub, _, arg = raw.partition(" ")
    sub, arg = sub.lower(), arg.strip()

    if sub == "on":
        async with pet_lock():
            kitty = load_kitty()
            born = kitty is None
            kitty = kitty or Kitty()
            kitty.enabled = True
            kitty.updated = time.time()  # no hunger for the time it was paused
            save_kitty(kitty)
        _ensure_sched()
        await refresh_kitty(event.client, notify=False)
        msg = (f"🐣 <b>{esc(kitty.name)} was born!</b>\n\nIt eats LeetCode problems, so solve one to feed it. "
               f"See it with <code>{_h()}kitty</code>, put it on your profile with <code>{_h()}livepfp on</code>."
               if born else f"😺 <b>{esc(kitty.name)} is awake again.</b>")
        return await edit_or_reply(event, msg, parse_mode="html")

    kitty = load_kitty()
    if kitty is None:
        return await edit_or_reply(event, f"🥚 You don't have a Kitty yet. Adopt one with <code>{_h()}kitty on</code>.",
                                   parse_mode="html")

    if sub == "off":
        async with pet_lock():
            kitty = load_kitty()
            kitty.enabled = False
            save_kitty(kitty)
        return await edit_delete(event, f"💤 {kitty.name} is paused. Nothing changes until <code>{_h()}kitty on</code>.",
                                 10, parse_mode="html")

    if sub in ("name", "coat", "public", "notify"):
        async with pet_lock():
            kitty = load_kitty()
            if sub == "name":
                name = " ".join(arg.split())[:24]
                if not name:
                    return await edit_delete(event, f"`Usage: {_h()}kitty name <name>`", 6)
                kitty.name = name
                reply = f"✏️ Kitty is now called <b>{esc(name)}</b>."
            elif sub == "coat":
                if arg.lower() not in COATS:
                    return await edit_delete(event, f"`Coats: {', '.join(COATS)}`", 8)
                kitty.coat = arg.lower()
                reply = f"🎨 {esc(kitty.name)} now has a <b>{kitty.coat}</b> coat."
            else:
                if arg.lower() not in _ON + _OFF:
                    return await edit_delete(event, f"`Usage: {_h()}kitty {sub} on|off`", 6)
                value = arg.lower() in _ON
                setattr(kitty, sub, value)
                reply = {
                    ("public", True): f"👋 Friends in groups can now <code>.pet</code> / <code>.feed</code> {esc(kitty.name)}.",
                    ("public", False): "🔒 Only you can care for Kitty now.",
                    ("notify", True): "🔔 Kitty notes go to Saved Messages.",
                    ("notify", False): "🔕 Kitty notes are off.",
                }[(sub, value)]
            save_kitty(kitty)
        return await edit_or_reply(event, reply, parse_mode="html")

    if sub == "reset":
        if arg.lower() != "confirm":
            return await edit_or_reply(
                event, f"⚠️ This replaces <b>{esc(kitty.name)}</b> (level {kitty.level}, {kitty.age_days} days) "
                f"with a new kitten. Send <code>{_h()}kitty reset confirm</code> to do it.", parse_mode="html")
        async with pet_lock():
            fresh = Kitty(name=kitty.name, coat=kitty.coat, public=kitty.public, notify=kitty.notify)
            save_kitty(fresh)
        return await edit_or_reply(event, f"🐣 A new {esc(fresh.name)} was born.", parse_mode="html")

    if not kitty.enabled:
        return await edit_or_reply(event, f"💤 {esc(kitty.name)} is paused. Wake it with <code>{_h()}kitty on</code>.",
                                   parse_mode="html")

    if sub in ("pet", "treat", "feed"):
        signals = await kitty_signals(event.client)
        await refresh_kitty(event.client, signals)
        async with pet_lock():
            kitty = load_kitty()
            if sub == "pet":
                _, text = kitty.pet()
            else:
                _, text = kitty.treat(today=addis_now().date().isoformat())
            kitty.advance(signals)  # re-pick the mood (a pet can cheer up a bored Kitty)
            save_kitty(kitty)
        return await edit_or_reply(event, f"{text}\n💗 <code>{bar(kitty.joy)}</code>  🐟 <code>{bar(kitty.food)}</code>",
                                   parse_mode="html")

    if sub == "stats":
        t = kitty.totals
        stage_line = " → ".join(s[0] for s in STAGES)
        born = datetime.fromtimestamp(kitty.born, timezone.utc).astimezone(ADDIS_TZ)
        text = (
            f"📊 <b>{esc(kitty.name)}'s life</b>\n\n"
            f"Born {born:%d %b %Y} · {kitty.age_days} days · level {kitty.level} ({int(kitty.xp)} XP)\n"
            f"Stage: <b>{kitty.stage}</b>  <i>({stage_line})</i>\n\n"
            f"🐟 Fish eaten (problems solved): <b>{t.get('fish', 0)}</b>\n"
            f"🔥 Best streak: <b>{kitty.best_streak}</b> days\n"
            f"💞 Pets: <b>{t.get('pets', 0)}</b> · from friends: <b>{t.get('visitor_pets', 0)}</b>"
            + (f" (last: {esc(kitty.last_visitor)})" if kitty.last_visitor else "")
            + f"\n🍪 Treats: <b>{t.get('treats', 0)}</b>\n"
            f"⌨️ 2-5 AM nights: <b>{t.get('owl_nights', 0)}</b>\n\n"
            f"Public: {'on' if kitty.public else 'off'} · notes: {'on' if kitty.notify else 'off'} · coat: {kitty.coat}"
        )
        return await edit_or_reply(event, text, parse_mode="html")

    if sub in ("", "card", "status"):
        catevent = await edit_or_reply(event, "🐾 <i>Checking on Kitty…</i>", parse_mode="html")
        signals = await kitty_signals(event.client)
        kitty = await refresh_kitty(event.client, signals)
        try:
            await _send_card(event, catevent, kitty, signals)
        except Exception as e:
            LOGS.error(f"kitty card failed: {e}")
            await catevent.edit(_stats_text(kitty, signals), parse_mode="html")
        return

    await edit_delete(event, f"`Unknown option. See {_h()}help kitty`", 8)


# --------------------------------------------------------------------------- #
# Friends: .pet / .feed in groups (only when public mode is on)
# --------------------------------------------------------------------------- #


@catub.on(events.NewMessage(incoming=True, pattern=r"(?i)^[./!](pet|feed)(?:@\w+)?(?:\s+\S+)?\s*$"))
async def _visitor(event):
    if event.is_private:
        return
    kitty = load_kitty()
    if not kitty or not kitty.enabled or not kitty.public:
        return
    sender = await event.get_sender()
    if not sender or getattr(sender, "bot", False):
        return
    now = time.time()
    if now - _visitors.get(sender.id, 0) < VISITOR_COOLDOWN:
        return
    _visitor_log[:] = [t for t in _visitor_log if now - t < 3600]
    if len(_visitor_log) >= VISITOR_HOURLY_CAP:
        return
    _visitors[sender.id] = now
    _visitor_log.append(now)
    who = " ".join(filter(None, [getattr(sender, "first_name", ""), getattr(sender, "last_name", "")])) or "a friend"
    action = event.pattern_match.group(1).lower()
    async with pet_lock():
        kitty = load_kitty()
        text = kitty.visitor(who[:32], action)
        save_kitty(kitty)
    with contextlib.suppress(Exception):
        await event.reply(f"{esc(text)}\n💗 <code>{bar(kitty.joy)}</code>", parse_mode="html")
