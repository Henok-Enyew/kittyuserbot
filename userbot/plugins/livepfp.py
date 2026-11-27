# Living profile photo — your avatar becomes a tiny pixel city that shows your day.
#
#   .livepfp                    status: what the picture shows right now and why
#   .livepfp on [scene] | off   start / stop (off restores your previous photo)
#   .livepfp scene city|both|kitty    .livepfp preview [scene]    .livepfp now
#   .livepfp every <minutes>    .livepfp shuffle
#
# What drives the picture:
#   * one window of your tower lights up per LeetCode problem solved today
#   * the beacon on your antenna turns green at a 3-day streak, gold at 7;
#     the billboard shows the streak number
#   * real sky over Addis: dawn, day, dusk, night with the real moon phase
#   * real Addis weather: clouds, rain, storms with lightning, fog
#   * when you're offline the city sleeps: lamps off, most windows dark
#   * Kitty (.kitty) sits on your rooftop or at your window, in its current mood
#
# A new photo is uploaded only when the picture would actually change, and at most
# once every N minutes (default 15). Each upload deletes the previous generated
# photo, so your profile history doesn't fill up. Settings: kitty_kv["LIVEPFP"].

import asyncio
import contextlib
import io
import time

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telethon import events, utils
from telethon.errors import FloodWaitError
from telethon.tl import functions

from userbot import catub

from ..Config import Config
from ..core.logger import logging
from ..core.managers import edit_delete, edit_or_reply
from ..helpers.functions.digest_builder import ADDIS_TZ
from ..helpers.functions.kittylife import moon_name, moon_phase, note_outgoing, sky_phase
from ..helpers.functions.kittystore import kitty_signals, load_pfp, refresh_kitty, save_pfp, scene_for
from ..helpers.functions.pixelscene import TOWER_WINDOWS, render_scene, scene_signature
from ..sql_helper.globals import gvarstatus

plugin_category = "utils"
LOGS = logging.getLogger(__name__)

SCENES = {
    "city": "the city only",
    "both": "the city with Kitty on your rooftop",
    "kitty": "close-up: Kitty at your window, the city behind",
}
TICK_MINUTES = 5
MIN_EVERY, MAX_EVERY = 10, 240
_sched = None
_lock = asyncio.Lock()

# autoprofile.py loops that also change the profile photo -> how to stop them
_CONFLICTS = {
    "autopic": "end autopic",
    "digitalpic": "end digitalpfp",
    "bloom": "end bloom",
    "CUSTOM_PFP": "cpfp -s",
    "autopfp_strings": "end batmanpfp",
}


def _h() -> str:
    return Config.COMMAND_HAND_LER


def _seed(cfg: dict) -> int:
    return int(cfg.get("seed") or 0) or (int(catub.uid or 7) % 9973)


def _conflicts() -> list:
    out = []
    for key, stop in _CONFLICTS.items():
        val = gvarstatus(key)
        if val is not None and str(val).lower() not in ("false", "0", ""):
            out.append(stop)
    return out


# --------------------------------------------------------------------------- #
# Core: build the scene, upload if it changed
# --------------------------------------------------------------------------- #


async def _current_scene(cfg: dict, scene: str = None):
    """(signals, kitty, SceneState, scene name) for right now."""
    signals = await kitty_signals(catub)
    kitty = await refresh_kitty(catub, signals)
    scene = scene or cfg["scene"]
    state = scene_for(signals, kitty, _seed(cfg))
    if state.kitty_mood is None and scene == "kitty":
        scene = "city"  # no Kitty adopted / paused: fall back to the plain city
    return signals, kitty, state, scene


def _png(img, name: str) -> io.BytesIO:
    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.name = name
    buf.seek(0)
    return buf


async def _delete_generated(keep: set = frozenset()) -> int:
    """Delete profile photos this plugin uploaded (except `keep`). Returns how many."""
    cfg = load_pfp()
    ours = set(cfg.get("photos") or []) - set(keep)
    if not ours:
        return 0
    photos = await catub.get_profile_photos("me", limit=20)
    doomed = [utils.get_input_photo(p) for p in photos if p.id in ours]
    if doomed:
        await catub(functions.photos.DeletePhotosRequest(id=doomed))
    return len(doomed)


async def update_pfp(force: bool = False) -> str:
    """Upload a new picture if it changed (or `force`). Returns what happened."""
    async with _lock:
        cfg = load_pfp()
        if not cfg["enabled"] and not force:
            return "off"
        now = time.time()
        if now < cfg.get("backoff", 0):
            return f"waiting out a Telegram flood limit ({int(cfg['backoff'] - now)} s)"
        _, _, state, scene = await _current_scene(cfg)
        sig = scene_signature(state, scene)
        if not force:
            if sig == cfg.get("sig"):
                return "unchanged"
            if now - cfg.get("last", 0) < cfg["every"] * 60:
                return "changed, waiting for the interval"
        img = await asyncio.to_thread(render_scene, state, scene)
        try:
            uploaded = await catub.upload_file(_png(img, "livepfp.png"))
            # keyword arg matters: the first positional parameter of this request is `fallback`
            result = await catub(functions.photos.UploadProfilePhotoRequest(file=uploaded))
        except FloodWaitError as e:
            cfg["backoff"] = now + e.seconds + 30
            cfg["error"] = f"flood wait {e.seconds}s"
            save_pfp(cfg)
            return cfg["error"]
        except Exception as e:
            cfg["error"] = str(e)[:200]
            save_pfp(cfg)
            LOGS.error(f"livepfp upload failed: {e}")
            return f"upload failed: {e}"
        new_id = result.photo.id
        try:
            await _delete_generated(keep={new_id})
        except Exception as e:
            LOGS.warning(f"livepfp: couldn't delete the previous photo: {e}")
        cfg = load_pfp()
        cfg.update(photos=[new_id], sig=sig, last=now, error="", uploads=int(cfg.get("uploads", 0)) + 1)
        save_pfp(cfg)
        return "updated"


async def _tick():
    try:
        result = await update_pfp()
        if result not in ("off", "unchanged", "changed, waiting for the interval"):
            LOGS.info(f"livepfp: {result}")
    except Exception as e:
        LOGS.error(f"livepfp tick failed: {e}")


def _ensure_sched():
    global _sched
    if _sched is None:
        _sched = AsyncIOScheduler(timezone=ADDIS_TZ)
        _sched.add_job(_tick, "interval", minutes=TICK_MINUTES, id="livepfp_tick",
                       replace_existing=True, max_instances=1, coalesce=True)
    if not _sched.running:
        _sched.start()
    return _sched


try:
    if load_pfp()["enabled"]:
        _ensure_sched()
except Exception as e:
    LOGS.error(f"livepfp init failed: {e}")


@catub.on(events.NewMessage(outgoing=True))
async def _livepfp_activity(event):
    note_outgoing()


# --------------------------------------------------------------------------- #
# Status text
# --------------------------------------------------------------------------- #


def _ago(ts: float) -> str:
    if not ts:
        return "never"
    mins = int((time.time() - ts) // 60)
    if mins < 1:
        return "just now"
    if mins < 60:
        return f"{mins} min ago"
    return f"{mins // 60} h {mins % 60} min ago"


def _status_text(cfg: dict, signals, kitty, state, scene) -> str:
    p, w, lc = signals.presence, signals.weather, signals.leetcode
    phase = sky_phase(signals.now)
    sky = phase + (f", {moon_name(moon_phase(signals.now))}" if phase == "night" else "")
    beacon = "gold" if lc.streak >= 7 else "green" if lc.streak >= 3 else "red"
    lit = min(lc.solved_today, TOWER_WINDOWS)
    if p.minutes_ago is None:
        presence = "unknown (counts as offline)"
    else:
        presence = f"{'awake' if p.awake else 'asleep'}: online {p.minutes_ago} min ago via {p.source}"
    if kitty and kitty.enabled:
        cat = f"{kitty.name}, {kitty.mood}"
    else:
        cat = f"not shown (<code>{_h()}kitty on</code> to adopt)"
    next_note = ""
    if cfg["enabled"]:
        wait = cfg["every"] * 60 - (time.time() - cfg.get("last", 0))
        changed = scene_signature(state, scene) != cfg.get("sig")
        if not changed:
            next_note = "Picture is up to date."
        elif wait > 0:
            next_note = f"Picture changed, next upload in about {int(wait // 60) + 1} min."
        else:
            next_note = f"Picture changed, uploading within {TICK_MINUTES} min."
    return (
        f"🌆 <b>Living profile photo</b>: {'ON' if cfg['enabled'] else 'OFF'}\n"
        f"Scene: <b>{scene}</b> ({SCENES[scene]}) · every {cfg['every']} min\n\n"
        f"🪟 Lit windows: <b>{lit}</b>/{TOWER_WINDOWS} (problems solved today)"
        + ("" if lc.ok else " <i>LeetCode unreachable</i>")
        + f"\n🔥 Streak {lc.streak} days: {beacon} beacon"
        + f"\n🌍 Sky: {sky} · weather: {w.emoji} {w.kind if w.ok else 'unknown'}"
        + f"\n👀 You: {presence}"
        + f"\n🐱 Kitty: {cat}\n\n"
        f"Last upload: {_ago(cfg.get('last', 0))} · total {cfg.get('uploads', 0)}"
        + (f"\n⚠️ Last error: <code>{cfg['error']}</code>" if cfg.get("error") else "")
        + (f"\n{next_note}" if next_note else "")
    )


# --------------------------------------------------------------------------- #
# .livepfp
# --------------------------------------------------------------------------- #


@catub.cat_cmd(
    pattern=r"livepfp(?:\s+([\s\S]+))?$",
    command=("livepfp", plugin_category),
    info={
        "header": "A profile photo that's alive: a pixel city showing your day.",
        "description": (
            "Your profile photo becomes a tiny pixel city. One window of your tower lights up for "
            "every LeetCode problem you solve today, the antenna beacon turns green at a 3-day streak "
            "and gold at 7, and a billboard shows the streak. The sky follows the real time in Addis "
            "(dawn, day, dusk, night with the real moon phase) and the real weather (clouds, rain, "
            "storms, fog). When you're offline the city sleeps: lamps off, windows dark. If you've "
            "adopted Kitty (.kitty on), it sits on your rooftop in its current mood. "
            "A new photo is uploaded only when the picture changes, at most every 15 minutes by default, "
            "and the previous generated photo is deleted each time. Turning it off deletes the "
            "generated photo so your previous one is back. It won't start while an autoprofile loop "
            "(autopic, digitalpfp, bloom, cpfp, batman/thor pfp) is running."
        ),
        "options": {
            "(nothing)": "status: what the picture shows right now and why",
            "on [scene]": "start (default scene: both)",
            "off": "stop and restore your previous photo",
            "off keep": "stop but keep the current picture",
            "scene <name>": "city = city only, both = Kitty on the rooftop, kitty = Kitty at your window",
            "preview [scene]": "send the current picture here without changing your profile",
            "now": "upload the current picture right away",
            "every <minutes>": f"minimum minutes between uploads ({MIN_EVERY}-{MAX_EVERY}, default 15)",
            "shuffle": "build a new random skyline",
        },
        "usage": ["{tr}livepfp", "{tr}livepfp <option>"],
        "examples": ["{tr}livepfp preview", "{tr}livepfp on", "{tr}livepfp scene kitty", "{tr}livepfp every 30",
                     "{tr}livepfp off"],
    },
)
async def livepfp_cmd(event):
    "Living profile photo."
    raw = (event.pattern_match.group(1) or "").strip().lower()
    sub, _, arg = raw.partition(" ")
    arg = arg.strip()
    cfg = load_pfp()

    if sub == "on":
        if arg and arg not in SCENES:
            return await edit_delete(event, f"`Scenes: {', '.join(SCENES)}`", 8)
        clash = _conflicts()
        if clash:
            stops = ", ".join(f"<code>{_h()}{c}</code>" for c in clash)
            return await edit_or_reply(
                event, f"⚠️ Another profile photo loop is running. Stop it first with {stops}, "
                f"then run <code>{_h()}livepfp on</code> again.", parse_mode="html")
        cfg.update(enabled=True, sig="", error="", backoff=0.0)
        if arg:
            cfg["scene"] = arg
        save_pfp(cfg)
        _ensure_sched()
        catevent = await edit_or_reply(event, "🌆 <i>Building your city…</i>", parse_mode="html")
        result = await update_pfp(force=True)
        if result != "updated":
            return await catevent.edit(f"⚠️ Living photo is on, but the first upload failed: <code>{result}</code>\n"
                                       f"It will retry every {TICK_MINUTES} min.", parse_mode="html")
        return await catevent.edit(
            f"🌆 <b>Living profile photo is ON</b> (scene: {cfg['scene']}).\n"
            f"It updates when your day changes, at most every {cfg['every']} min. "
            f"<code>{_h()}livepfp</code> shows what it's showing, <code>{_h()}livepfp off</code> restores your old photo.",
            parse_mode="html")

    if sub == "off":
        async with _lock:
            cfg = load_pfp()
            cfg["enabled"] = False
            removed = 0
            if arg != "keep":
                try:
                    removed = await _delete_generated()
                    cfg["photos"], cfg["sig"] = [], ""
                except Exception as e:
                    save_pfp(cfg)
                    return await edit_or_reply(event, f"⏹ Stopped, but couldn't remove the generated photo: <code>{e}</code>",
                                               parse_mode="html")
            save_pfp(cfg)
        if arg == "keep":
            return await edit_delete(event, "⏹ Living photo stopped. The current picture stays.", 8)
        tail = "your previous photo is back." if removed else "nothing to remove."
        return await edit_delete(event, f"⏹ Living photo stopped, {tail}", 8)

    if sub == "scene":
        if arg not in SCENES:
            opts = "\n".join(f"<code>{k}</code>: {v}" for k, v in SCENES.items())
            return await edit_or_reply(event, f"🎬 Pick a scene:\n{opts}", parse_mode="html")
        cfg["scene"] = arg
        save_pfp(cfg)
        note = f" Uploading within {TICK_MINUTES} min." if cfg["enabled"] else ""
        return await edit_delete(event, f"🎬 Scene set to <b>{arg}</b>: {SCENES[arg]}.{note}", 8, parse_mode="html")

    if sub == "every":
        if not arg.isdigit() or not MIN_EVERY <= int(arg) <= MAX_EVERY:
            return await edit_delete(event, f"`Usage: {_h()}livepfp every <{MIN_EVERY}-{MAX_EVERY}>`", 8)
        cfg["every"] = int(arg)
        save_pfp(cfg)
        return await edit_delete(event, f"⏱ At most one upload every {arg} min.", 6)

    header = ""
    if sub == "shuffle":
        cfg["seed"] = int(time.time()) % 9973 or 1
        cfg["sig"] = ""
        save_pfp(cfg)
        note = f" Your profile updates within {TICK_MINUTES} min." if cfg["enabled"] else ""
        header = f"🏙 <b>New skyline.</b>{note}\n\n"
        sub, arg = "preview", ""

    if sub == "preview":
        if arg and arg not in SCENES:
            return await edit_delete(event, f"`Scenes: {', '.join(SCENES)}`", 8)
        catevent = await edit_or_reply(event, "🎨 <i>Painting…</i>", parse_mode="html")
        signals, kitty, state, scene = await _current_scene(cfg, arg or None)
        img = await asyncio.to_thread(render_scene, state, scene)
        await event.client.send_file(event.chat_id, _png(img, "livepfp_preview.png"),
                                     caption=header + _status_text(load_pfp(), signals, kitty, state, scene),
                                     parse_mode="html")
        with contextlib.suppress(Exception):
            await catevent.delete()
        return

    if sub == "now":
        catevent = await edit_or_reply(event, "🌆 <i>Uploading…</i>", parse_mode="html")
        if not cfg["enabled"]:
            return await catevent.edit(f"Living photo is off. Start it with <code>{_h()}livepfp on</code>.", parse_mode="html")
        result = await update_pfp(force=True)
        return await edit_delete(catevent, "✅ Profile photo updated." if result == "updated" else f"⚠️ {result}", 8)

    if sub in ("", "status"):
        catevent = await edit_or_reply(event, "🌆 <i>Looking at your city…</i>", parse_mode="html")
        signals, kitty, state, scene = await _current_scene(cfg)
        return await catevent.edit(_status_text(cfg, signals, kitty, state, scene), parse_mode="html")

    await edit_delete(event, f"`Unknown option. See {_h()}help livepfp`", 8)

