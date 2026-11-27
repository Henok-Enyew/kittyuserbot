# Storage + glue shared by plugins/kitty.py and plugins/livepfp.py.
#
#   load_kitty() / save_kitty()     Kitty state in kitty_kv["KITTY_PET"]
#   refresh_kitty(client, signals)  advance Kitty to now (under a lock), send its
#                                   notes to Saved Messages, return it
#   scene_for(signals, kitty, seed) SceneState for the pixel renderer
#   load_pfp() / save_pfp()         living-profile-photo settings in kitty_kv["LIVEPFP"]
from __future__ import annotations

import asyncio
import contextlib
from typing import Optional

from ...core.logger import logging
from ...sql_helper.kitty_kv_sql import kv_get_json, kv_set_json
from .kittylife import Signals, get_signals, moon_phase, sky_phase
from .kittypet import Kitty
from .pixelscene import SceneState

LOGS = logging.getLogger(__name__)

KEY_PET = "KITTY_PET"
KEY_PFP = "LIVEPFP"
_pet_lock = asyncio.Lock()

PFP_DEFAULTS = {
    "enabled": False,
    "scene": "both",  # city | both | kitty
    "every": 15,  # minimum minutes between uploads
    "seed": 0,  # skyline layout, 0 = derived from your user id
    "sig": "",  # signature of the picture currently on your profile
    "last": 0.0,  # unix time of the last upload
    "photos": [],  # ids of profile photos we uploaded (deleted when replaced / on off)
    "backoff": 0.0,  # FloodWait: don't upload before this unix time
    "uploads": 0,
    "error": "",
}


def load_kitty() -> Optional[Kitty]:
    """None if Kitty was never adopted."""
    data = kv_get_json(KEY_PET, None)
    return Kitty.from_dict(data) if data else None


def save_kitty(kitty: Kitty) -> None:
    kv_set_json(KEY_PET, kitty.to_dict())


def pet_lock() -> asyncio.Lock:
    return _pet_lock


async def kitty_signals(client, force: bool = False) -> Signals:
    """Live signals, using Kitty's own solve record as a streak backup."""
    kitty = load_kitty()
    extra = set()
    if kitty:
        from datetime import date

        for d in kitty.solve_days[-120:]:
            with contextlib.suppress(ValueError):
                extra.add(date.fromisoformat(d))
    return await get_signals(client, force=force, extra_days=extra)


async def refresh_kitty(client, signals: Optional[Signals] = None, notify: bool = True) -> Optional[Kitty]:
    """Advance Kitty to now and persist. Event notes (level-ups, streak parties,
    hunger...) go to Saved Messages when Kitty's notify setting is on."""
    if signals is None:
        signals = await kitty_signals(client)
    async with _pet_lock:
        kitty = load_kitty()
        if kitty is None or not kitty.enabled:
            return kitty
        notes = kitty.advance(signals)
        save_kitty(kitty)
    if notes and notify and kitty.notify:
        try:
            await client.send_message("me", "🐾 <b>Kitty</b>\n\n" + "\n".join(notes), parse_mode="html")
        except Exception as e:
            LOGS.warning(f"kitty note failed: {e}")
    return kitty


def scene_for(signals: Signals, kitty: Optional[Kitty], seed: int) -> SceneState:
    show_cat = kitty is not None and kitty.enabled
    return SceneState(
        phase=sky_phase(signals.now),
        weather=signals.weather.kind if signals.weather.ok else "clear",
        awake=signals.presence.awake,
        solved=signals.leetcode.solved_today,
        streak=signals.leetcode.streak,
        moon=moon_phase(signals.now),
        kitty_mood=kitty.mood if show_cat else None,
        kitty_stage=kitty.stage if show_cat else "kitten",
        kitty_coat=kitty.coat if show_cat else "orange",
        seed=seed,
    )


def load_pfp() -> dict:
    cfg = dict(PFP_DEFAULTS)
    cfg.update(kv_get_json(KEY_PFP, {}) or {})
    return cfg


def save_pfp(cfg: dict) -> None:
    kv_set_json(KEY_PFP, cfg)
