# Keyword alerts — get pinged in Saved Messages when your words come up in any group.
#
#   .kw add internship, hackathon, my name     add words/phrases (comma separated)
#   .kw del hackathon      .kw list      .kw clear
#   .kw ignore             stop watching this chat     .kw unignore
#   .kw off / on           pause everything

import json
import re
import time

from telethon import events

from userbot import catub

from ..Config import Config
from ..core.logger import logging
from ..core.managers import edit_delete, edit_or_reply
from ..helpers.functions.kittychat import esc, message_link, name_of
from ..sql_helper.globals import addgvar, gvarstatus

plugin_category = "utils"
LOGS = logging.getLogger(__name__)

_state = {"words": [], "ignored": [], "on": True}
_regex = None
_last_hit = {}  # (chat, word) -> time


def _load():
    try:
        _state.update(json.loads(gvarstatus("KW_STATE") or "{}"))
    except Exception:
        pass
    _compile()


def _save():
    addgvar("KW_STATE", json.dumps(_state, ensure_ascii=False))
    _compile()


def _compile():
    global _regex
    words = sorted(_state["words"], key=len, reverse=True)
    _regex = re.compile(r"(?<!\w)(" + "|".join(re.escape(w) for w in words) + r")(?!\w)", re.I) if words else None


_load()


@catub.on(events.NewMessage(incoming=True, func=lambda e: not e.is_private))
async def _kw_watcher(event):
    if not _regex or not _state["on"] or not event.raw_text:
        return
    if event.chat_id in _state["ignored"]:
        return
    m = _regex.search(event.raw_text)
    if not m:
        return
    sender = await event.get_sender()
    if getattr(sender, "bot", False) or getattr(sender, "is_self", False):
        return
    word = m.group(1).lower()
    key = (event.chat_id, word)
    if time.monotonic() - _last_hit.get(key, 0) < 120:
        return
    _last_hit[key] = time.monotonic()

    chat = await event.get_chat()
    text = event.raw_text
    start = max(0, m.start() - 150)
    snippet = text[start : m.end() + 250]
    highlighted = esc(snippet[: m.start() - start]) + f"<b><u>{esc(snippet[m.start() - start : m.end() - start])}</u></b>" + esc(snippet[m.end() - start :])
    link = message_link(chat, event.id)
    where = f'<a href="{link}">{esc(name_of(chat))}</a>' if link else f"<b>{esc(name_of(chat))}</b>"
    try:
        await event.client.send_message(
            "me",
            f"🔔 <b>{esc(word)}</b> mentioned in {where}\n"
            f"👤 {esc(name_of(sender, 'someone'))}:\n"
            f"{'…' if start else ''}{highlighted}{'…' if m.end() + 250 < len(text) else ''}",
            parse_mode="html",
            link_preview=False,
        )
    except Exception as e:
        LOGS.debug(f"kw alert failed: {e}")


@catub.cat_cmd(
    pattern=r"kw(?:\s+([\s\S]+))?$",
    command=("kw", plugin_category),
    info={
        "header": "Keyword alerts across all your groups and channels.",
        "description": "When someone says one of your words in a group, you get a Saved Messages alert "
        "with the highlighted message and a link to it. Whole words only, case-insensitive. "
        "Max one alert per word per chat every 2 minutes.",
        "options": {
            "add <a, b>": "watch words / phrases",
            "del <a, b>": "stop watching",
            "list": "show words and ignored chats",
            "ignore / unignore": "skip / watch the current chat",
            "on / off": "pause or resume",
            "clear": "remove all words",
        },
        "usage": "{tr}kw <option>",
        "examples": ["{tr}kw add internship, hackathon, Henok", "{tr}kw ignore", "{tr}kw list"],
    },
)
async def kw_cmd(event):
    "Keyword alerts."
    raw = (event.pattern_match.group(1) or "").strip()
    sub, _, rest = raw.partition(" ")
    sub = sub.lower()
    words = [w.strip() for w in rest.split(",") if w.strip()]

    if sub == "add" and words:
        new = [w for w in words if w.lower() not in (x.lower() for x in _state["words"])]
        _state["words"] += new
        _save()
        return await edit_delete(event, f"🔔 Watching: {', '.join(new) or '(already watched)'}", 6)
    if sub in ("del", "rm", "remove") and words:
        low = {w.lower() for w in words}
        _state["words"] = [w for w in _state["words"] if w.lower() not in low]
        _save()
        return await edit_delete(event, "🗑 Removed.", 5)
    if sub == "clear":
        _state["words"] = []
        _save()
        return await edit_delete(event, "🧹 All keywords removed.", 5)
    if sub in ("on", "off"):
        _state["on"] = sub == "on"
        _save()
        return await edit_delete(event, f"Keyword alerts {'resumed ▶️' if _state['on'] else 'paused ⏸'}.", 5)
    if sub == "ignore":
        if event.chat_id not in _state["ignored"]:
            _state["ignored"].append(event.chat_id)
            _save()
        return await edit_delete(event, "🙈 Not watching this chat any more.", 5)
    if sub == "unignore":
        _state["ignored"] = [c for c in _state["ignored"] if c != event.chat_id]
        _save()
        return await edit_delete(event, "👀 Watching this chat again.", 5)
    if sub in ("list", ""):
        lines = [f"🔔 <b>Keyword alerts</b> — {'on' if _state['on'] else 'paused'}\n"]
        lines.append(", ".join(f"<code>{esc(w)}</code>" for w in _state["words"]) or "<i>no words yet</i>")
        if _state["ignored"]:
            lines.append(f"\n🙈 Ignored chats: {len(_state['ignored'])}")
        lines.append(f"\n<code>{Config.COMMAND_HAND_LER}kw add word, another phrase</code>")
        return await edit_or_reply(event, "\n".join(lines), parse_mode="html")
    await edit_delete(event, f"`Usage: {Config.COMMAND_HAND_LER}kw add|del|list|ignore|on|off`", 6)
