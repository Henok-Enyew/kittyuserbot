# Message effects & expandable quotes — newer Telegram message features.
#
#   .fx 🔥 text     send text with a full-screen message effect (private chats)
#   .fx list        effects you can use (free ones marked)
#   .cq text        send text as a collapsed (expandable) quote; reply = re-post that message collapsed

from telethon.errors import RPCError
from telethon.tl import functions, types

from userbot import catub

from ..Config import Config
from ..core.managers import edit_delete, edit_or_reply

plugin_category = "tools"

_EFFECTS = {}  # emoticon -> AvailableEffect

ALIASES = {
    "fire": "🔥",
    "like": "👍",
    "thumbs": "👍",
    "dislike": "👎",
    "heart": "❤",
    "love": "❤",
    "party": "🎉",
    "confetti": "🎉",
    "tada": "🎉",
    "poop": "💩",
    "poo": "💩",
}


def _norm(e: str) -> str:
    return e.replace("️", "")


async def _effects(client):
    if not _EFFECTS:
        res = await client(functions.messages.GetAvailableEffectsRequest(hash=0))
        for eff in getattr(res, "effects", []):
            _EFFECTS[_norm(eff.emoticon)] = eff
    return _EFFECTS


def _utf16_len(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


@catub.cat_cmd(
    pattern=r"fx(?:\s+([\s\S]+))?$",
    command=("fx", plugin_category),
    info={
        "header": "Send a message with a full-screen animated effect.",
        "description": "Message effects play an animation when the other person opens the chat. "
        "Telegram only allows them in private chats. Free accounts get the free effects "
        "(usually 👍 👎 ❤️ 🔥 🎉 💩); the rest need Premium. Markdown formatting works.",
        "usage": ["{tr}fx <emoji | name> <text>", "{tr}fx list"],
        "examples": ["{tr}fx 🎉 Happy birthday!!", "{tr}fx fire we shipped it", "{tr}fx heart miss you"],
    },
)
async def fx_cmd(event):
    "Send with a message effect."
    raw = (event.pattern_match.group(1) or "").strip()
    try:
        effects = await _effects(event.client)
    except RPCError as e:
        return await edit_delete(event, f"Couldn't load effects: `{e}`", 8)

    if not raw or raw.lower() == "list":
        free = [e for e in effects.values() if not e.premium_required]
        paid = [e for e in effects.values() if e.premium_required]
        names = {v: k for k, v in ALIASES.items()}
        text = "✨ **Message effects**\n\n**Free:** " + "  ".join(
            f"{e.emoticon}`{names.get(_norm(e.emoticon), '')}`" for e in free
        )
        if paid:
            text += "\n\n**Premium:** " + " ".join(e.emoticon for e in paid)
        text += f"\n\n`{Config.COMMAND_HAND_LER}fx 🔥 your message` — private chats only."
        return await edit_or_reply(event, text)

    head, _, text = raw.partition(" ")
    key = _norm(ALIASES.get(head.lower(), head))
    effect = effects.get(key)
    if effect is None:
        return await edit_delete(event, f"`{head}` isn't an effect. Try `{Config.COMMAND_HAND_LER}fx list`.", 8)
    if not text.strip():
        return await edit_delete(event, "`Give some text to send.`", 6)
    if not event.is_private:
        return await edit_delete(event, "`Telegram only allows message effects in private chats.`", 6)
    if effect.premium_required and not (await event.client.get_me()).premium:
        free = " ".join(e.emoticon for e in effects.values() if not e.premium_required)
        return await edit_delete(event, f"{effect.emoticon} needs Telegram Premium. Free ones: {free}", 8)

    message, entities = await event.client._parse_message_text(text.strip(), "md")
    reply_to = types.InputReplyToMessage(reply_to_msg_id=event.reply_to_msg_id) if event.reply_to_msg_id else None
    peer = await event.get_input_chat()
    try:
        await event.client(
            functions.messages.SendMessageRequest(
                peer=peer,
                message=message,
                entities=entities or None,
                reply_to=reply_to,
                no_webpage=True,
                effect=effect.id,
            )
        )
    except RPCError as e:
        reason = getattr(e, "message", str(e))
        if "PREMIUM" in reason:
            return await edit_delete(event, f"{effect.emoticon} needs Telegram Premium. Free: 👍 👎 ❤️ 🔥 🎉 💩", 8)
        return await edit_delete(event, f"Effect failed: `{reason}`", 8)
    await event.delete()


@catub.cat_cmd(
    pattern=r"cq(?:\s+([\s\S]+))?$",
    command=("cq", plugin_category),
    info={
        "header": "Send long text as a collapsed, expandable quote.",
        "description": "The quote shows a few lines and expands when tapped, so long texts, "
        "lyrics, logs or spoilers don't flood the chat. "
        "Use 'Title | text' to keep a visible title line above the quote. "
        "Reply to a long message to re-post it collapsed.",
        "usage": ["{tr}cq <text>", "{tr}cq <title> | <text>", "{tr}cq <reply>"],
        "examples": ["{tr}cq Lyrics | Never gonna give you up...", "{tr}cq (reply to a long message)"],
    },
)
async def cq_cmd(event):
    "Expandable quote."
    raw = (event.pattern_match.group(1) or "").strip()
    reply = await event.get_reply_message()
    if not raw and reply and reply.message:
        raw = reply.message
    if not raw:
        return await edit_delete(event, "`Give text or reply to a message.`", 6)

    title, body = "", raw
    if " | " in raw.split("\n", 1)[0]:
        title, body = (p.strip() for p in raw.split(" | ", 1))

    text = f"{title}\n{body}" if title else body
    q_off = _utf16_len(title) + 1 if title else 0
    entities = [types.MessageEntityBlockquote(offset=q_off, length=_utf16_len(body), collapsed=True)]
    if title:
        entities.insert(0, types.MessageEntityBold(offset=0, length=_utf16_len(title)))
    if _utf16_len(text) > 4096:
        return await edit_delete(event, "`Too long for one message (4096 max).`", 6)

    await event.client.send_message(
        event.chat_id,
        text,
        formatting_entities=entities,
        reply_to=event.reply_to_msg_id,
        link_preview=False,
    )
    if event.out:
        await event.delete()

