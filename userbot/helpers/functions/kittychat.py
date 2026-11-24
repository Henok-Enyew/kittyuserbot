# Shared chat helpers for the "modern" plugins: names, links, message labels.

import html

from telethon import utils
from telethon.tl import types

MEDIA_ICONS = {
    "photo": "🖼",
    "video": "🎬",
    "round": "⏺",
    "voice": "🎙",
    "audio": "🎵",
    "sticker": "🎟",
    "gif": "🎞",
    "document": "📎",
    "poll": "📊",
    "location": "📍",
    "contact": "👤",
    "dice": "🎲",
    "game": "🎮",
    "story": "📖",
    "link": "🔗",
    "giveaway": "🎁",
}


def esc(text) -> str:
    return html.escape(str(text or ""), quote=False)


def name_of(entity, fallback="Unknown") -> str:
    if entity is None:
        return fallback
    if isinstance(entity, types.User) and entity.deleted:
        return "Deleted Account"
    return utils.get_display_name(entity) or fallback


def mention_html(entity, fallback="Unknown") -> str:
    name = esc(name_of(entity, fallback))
    if isinstance(entity, types.User):
        return f'<a href="tg://user?id={entity.id}">{name}</a>'
    username = getattr(entity, "username", None)
    if username:
        return f'<a href="https://t.me/{username}">{name}</a>'
    return name


def message_link(chat, msg_id: int):
    """Public/private t.me link for a message, or None for PMs & basic groups."""
    if isinstance(chat, types.Channel):
        if chat.username:
            return f"https://t.me/{chat.username}/{msg_id}"
        return f"https://t.me/c/{chat.id}/{msg_id}"
    return None


def media_kind(msg) -> str | None:
    """Short media kind for a message ('photo', 'voice', ...) or None."""
    media = getattr(msg, "media", None)
    if media is None:
        return None
    if isinstance(media, types.MessageMediaPhoto):
        return "photo"
    if isinstance(media, types.MessageMediaDocument):
        if msg.sticker:
            return "sticker"
        if msg.gif:
            return "gif"
        if msg.video_note:
            return "round"
        if msg.video:
            return "video"
        if msg.voice:
            return "voice"
        if msg.audio:
            return "audio"
        return "document"
    if isinstance(media, types.MessageMediaPoll):
        return "poll"
    if isinstance(media, (types.MessageMediaGeo, types.MessageMediaGeoLive, types.MessageMediaVenue)):
        return "location"
    if isinstance(media, types.MessageMediaContact):
        return "contact"
    if isinstance(media, types.MessageMediaDice):
        return "dice"
    if isinstance(media, types.MessageMediaGame):
        return "game"
    if isinstance(media, types.MessageMediaStory):
        return "story"
    if isinstance(media, types.MessageMediaWebPage):
        return "link"
    if isinstance(media, (types.MessageMediaGiveaway, types.MessageMediaGiveawayResults)):
        return "giveaway"
    return None


def describe(msg, limit: int = 300) -> str:
    """Plain-text one-liner for any message, e.g. '🎙 voice 0:12' or the text."""
    if isinstance(msg, types.MessageService) or getattr(msg, "action", None):
        return f"⚙️ {type(msg.action).__name__.replace('MessageAction', '')}"

    kind = media_kind(msg)
    text = (msg.message or "").strip()
    label = ""
    if kind and kind != "link":
        label = MEDIA_ICONS.get(kind, "📎") + " " + kind
        if kind == "sticker":
            alt = next(
                (a.alt for a in msg.document.attributes if isinstance(a, types.DocumentAttributeSticker)),
                "",
            )
            label = f"🎟 sticker {alt}".rstrip()
        elif kind in ("voice", "audio", "video", "round") and msg.file and msg.file.duration:
            d = int(msg.file.duration)
            label += f" {d // 60}:{d % 60:02d}"
        elif kind == "document" and msg.file and msg.file.name:
            label += f" {msg.file.name}"
        elif kind == "poll":
            q = msg.media.poll.question
            label += f" {getattr(q, 'text', q)}"
        elif kind == "dice":
            label = f"{msg.media.emoticon} {msg.media.value}"
    out = f"{label} · {text}" if label and text else (label or text)
    out = " ".join(out.split())
    if len(out) > limit:
        out = out[: limit - 1] + "…"
    return out or "(empty)"


async def resolve_chat(client, ref: str):
    """Resolve '@user', 'me', numeric id, t.me link or a dialog title fragment."""
    ref = (ref or "").strip()
    if not ref:
        return None
    if ref.lower() in ("me", "self", "saved"):
        return await client.get_entity("me")
    if "t.me/" in ref:
        ref = ref.split("t.me/", 1)[1].split("/")[0]
        if ref == "c":
            return None
    if ref.lstrip("-").isdigit():
        try:
            return await client.get_entity(int(ref))
        except Exception:
            pass
    try:
        return await client.get_entity(ref)
    except Exception:
        pass
    needle = ref.lower().lstrip("@")
    async for dialog in client.iter_dialogs(limit=300):
        if needle in (dialog.name or "").lower():
            return dialog.entity
    return None
