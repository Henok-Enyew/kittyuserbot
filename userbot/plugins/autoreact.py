# Auto-react — react to a person's (or a whole chat's) messages automatically.
#
#   .autoreact 🔥            (reply)  react 🔥 to everything that person sends, anywhere
#   .autoreact ❤️             (no reply) react ❤️ to every incoming message in this chat
#   .autoreact random        pick a random emoji each time
#   .autoreact off           (reply / in chat) stop
#   .autoreacts              list rules     .autoreact clear   remove all

import asyncio
import json
import random
import time

from telethon import events
from telethon.errors import FloodWaitError, RPCError
from telethon.tl import functions, types

from userbot import catub

from ..Config import Config
from ..core.logger import logging
from ..core.managers import edit_delete, edit_or_reply
from ..helpers.functions.kittychat import esc, name_of
from ..sql_helper.globals import addgvar, gvarstatus

plugin_category = "fun"
LOGS = logging.getLogger(__name__)

_KEY = "AUTOREACT_RULES"

# The standard reactions a non-Premium account can send (where the chat allows them).
FREE_REACTIONS = (
    "👍 👎 ❤ 🔥 🥰 👏 😁 🤔 🤯 😱 🤬 😢 🎉 🤩 🤮 💩 🙏 👌 🕊 🤡 🥱 🥴 😍 🐳 ❤‍🔥 🌚 🌭 💯 🤣 ⚡ 🍌 🏆 💔 "
    "🤨 😐 🍓 🍾 💋 🖕 😈 😴 😭 🤓 👻 👨‍💻 👀 🎃 🙈 😇 😨 🤝 ✍ 🤗 🫡 🎅 🎄 ☃ 💅 🤪 🗿 🆒 💘 🙉 🦄 😘 "
    "💊 🙊 😎 👾 🤷‍♂ 🤷 🤷‍♀ 😡"
).split()
RANDOM_POOL = "👍 ❤ 🔥 🥰 👏 😁 🤩 💯 🏆 ⚡ 😍 🤣 🫡 😎 🆒 🦄 🎉".split()

_rules = {}  # "u:<id>" / "c:<id>" -> emoji or "random"
_last_sent = {}  # chat_id -> monotonic time, to stay far from flood limits
_dead_chats = set()  # chats where reactions are disabled / the emoji isn't allowed


def _norm(emoji: str) -> str:
    """Telegram stores reactions without the emoji variation selector (❤ not ❤️)."""
    return emoji.replace("️", "").strip()


def _load():
    global _rules
    try:
        _rules = json.loads(gvarstatus(_KEY) or "{}")
    except Exception:
        _rules = {}


def _save():
    addgvar(_KEY, json.dumps(_rules, ensure_ascii=False))


_load()


def _pick(rule: str) -> str:
    return random.choice(RANDOM_POOL) if rule == "random" else rule


@catub.on(events.NewMessage(incoming=True))
async def _autoreact_watcher(event):
    if not _rules or event.chat_id in _dead_chats:
        return
    rule = _rules.get(f"u:{event.sender_id}") or _rules.get(f"c:{event.chat_id}")
    if not rule:
        return
    now = time.monotonic()
    if now - _last_sent.get(event.chat_id, 0) < 2.5:
        return
    _last_sent[event.chat_id] = now
    await asyncio.sleep(random.uniform(0.6, 2.2))  # look human
    try:
        await event.client(
            functions.messages.SendReactionRequest(
                peer=await event.get_input_chat(),
                msg_id=event.id,
                reaction=[types.ReactionEmoji(emoticon=_pick(rule))],
            )
        )
    except FloodWaitError as e:
        _last_sent[event.chat_id] = now + e.seconds
    except RPCError as e:
        reason = getattr(e, "message", str(e))
        if reason in ("REACTION_INVALID", "CHAT_ADMIN_REQUIRED", "CHAT_WRITE_FORBIDDEN", "REACTIONS_TOO_MANY"):
            _dead_chats.add(event.chat_id)
            LOGS.info(f"autoreact disabled for chat {event.chat_id}: {reason}")
    except Exception as e:
        LOGS.debug(f"autoreact: {e}")


@catub.cat_cmd(
    pattern=r"autoreact(?:\s+(.+))?$",
    command=("autoreact", plugin_category),
    info={
        "header": "Automatically react to someone's messages.",
        "description": "Reply to a user to react to everything they send (in any chat). "
        "Use it without a reply to react to every incoming message in the current chat. "
        "Rules are saved in the database and survive restarts. "
        "Free accounts can only use the standard reactions the chat allows.",
        "options": {
            "<emoji>": "a standard reaction, e.g. 🔥 ❤️ 👍 😁 🤯 🏆",
            "random": "a random positive reaction each time",
            "off": "remove the rule for that user / this chat",
            "clear": "remove every rule",
            "list": "show the free reaction emojis",
        },
        "usage": ["{tr}autoreact <emoji | random> [reply]", "{tr}autoreact off [reply]", "{tr}autoreacts"],
        "examples": ["{tr}autoreact 🔥  (reply to your friend)", "{tr}autoreact random  (in a group)"],
    },
)
async def autoreact_cmd(event):
    "Set up auto reactions."
    arg = _norm(event.pattern_match.group(1) or "")
    if not arg:
        return await edit_delete(event, f"`Usage: {Config.COMMAND_HAND_LER}autoreact <emoji|random|off> [reply]`", 8)
    low = arg.lower()

    if low == "list":
        return await edit_or_reply(event, "**Free reactions:**\n" + " ".join(FREE_REACTIONS))
    if low == "clear":
        _rules.clear()
        _dead_chats.clear()
        _save()
        return await edit_delete(event, "🧹 All auto-react rules removed.", 6)

    reply = await event.get_reply_message()
    if reply and reply.sender_id and not reply.out:
        key, target = f"u:{reply.sender_id}", await reply.get_sender()
        where = f"everything **{name_of(target)}** sends"
    else:
        key, target = f"c:{event.chat_id}", await event.get_chat()
        where = f"every incoming message in **{name_of(target, 'this chat')}**"

    if low == "off":
        if _rules.pop(key, None) is None:
            return await edit_delete(event, "No rule here.", 5)
        _save()
        return await edit_delete(event, "🔕 Auto-react removed.", 5)

    if low != "random" and arg not in FREE_REACTIONS:
        return await edit_delete(
            event,
            f"`{arg}` isn't a standard reaction. See `{Config.COMMAND_HAND_LER}autoreact list`.",
            8,
        )
    _rules[key] = "random" if low == "random" else arg
    _dead_chats.discard(event.chat_id)
    _save()
    shown = "🎲 random" if low == "random" else arg
    await edit_delete(event, f"✅ Reacting {shown} to {where}.", 8)


@catub.cat_cmd(
    pattern=r"autoreacts$",
    command=("autoreacts", plugin_category),
    info={"header": "List your auto-react rules.", "usage": "{tr}autoreacts"},
)
async def autoreacts_cmd(event):
    "List auto-react rules."
    if not _rules:
        return await edit_delete(event, "No auto-react rules yet.", 6)
    lines = ["⚡ <b>Auto-react rules</b>\n"]
    for key, emoji in _rules.items():
        kind, _, ident = key.partition(":")
        try:
            ent = await event.client.get_entity(int(ident))
            label = esc(name_of(ent))
        except Exception:
            label = f"id {ident}"
        icon = "👤" if kind == "u" else "💬"
        dead = " <i>(not allowed there)</i>" if kind == "c" and int(ident) in _dead_chats else ""
        lines.append(f"{icon} {label} → {'🎲' if emoji == 'random' else emoji}{dead}")
    await edit_or_reply(event, "\n".join(lines), parse_mode="html")
