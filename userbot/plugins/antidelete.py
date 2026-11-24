# Anti-delete for private chats — see what people deleted or edited. Opt-in.
#
#   .antidelete on | off        (status without args)
#
# Incoming private messages are kept in a small in-memory cache (last 3000). When one is
# deleted or edited, the original is posted to your Saved Messages. Media is re-sent when
# Telegram still allows it, otherwise it's described. The cache is emptied on restart.

from collections import OrderedDict

from telethon import events
from telethon.errors import RPCError

from userbot import catub

from ..core.logger import logging
from ..core.managers import edit_delete, edit_or_reply
from ..helpers.functions.kittychat import describe, esc, media_kind, name_of
from ..helpers.functions.kittytime import fmt_local
from ..sql_helper.kitty_kv_sql import kv_get, kv_set

plugin_category = "utils"
LOGS = logging.getLogger(__name__)

CACHE_SIZE = 3000
BULK = 20  # more deletions than this at once = a cleared chat; summarise instead
_cache = OrderedDict()  # msg_id -> dict


def _on() -> bool:
    return (kv_get("ANTIDELETE") or "off") == "on"


@catub.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def _ad_store(event):
    if not _on():
        return
    sender = await event.get_sender()
    if not sender or getattr(sender, "bot", False) or sender.id == 777000:
        return
    _cache[event.id] = {
        "chat": event.chat_id,
        "who": name_of(sender),
        "uid": sender.id,
        "text": event.raw_text or "",
        "label": describe(event.message, 200),
        "kind": media_kind(event.message),
        "media": event.message.media,
        "date": event.date,
    }
    if len(_cache) > CACHE_SIZE:
        _cache.popitem(last=False)


def _header(entry, verb):
    who = f'<a href="tg://user?id={entry["uid"]}">{esc(entry["who"])}</a>'
    return f"{verb} {who} · sent {fmt_local(entry['date'])}"


@catub.on(events.MessageDeleted())
async def _ad_deleted(event):
    if not _on() or event.chat_id is not None and not event.is_private:
        return
    hits = [(i, _cache.pop(i)) for i in event.deleted_ids if i in _cache]
    if not hits:
        return
    client = event.client
    if len(hits) > BULK:
        people = sorted({h["who"] for _, h in hits})
        await client.send_message(
            "me", f"🗑 <b>{len(hits)} messages deleted at once</b> (chat cleared?) from {esc(', '.join(people))}", parse_mode="html"
        )
        return
    for _, entry in hits:
        head = _header(entry, "🗑 <b>Deleted</b> by")
        body = f"\n<blockquote>{esc(entry['text'])}</blockquote>" if entry["text"] else ""
        kind = entry["kind"]
        if kind and kind not in ("link", "poll", "dice", "game", "story", "giveaway"):
            try:
                await client.send_file("me", entry["media"], caption=head + body, parse_mode="html")
                continue
            except (RPCError, TypeError, ValueError) as e:
                LOGS.debug(f"antidelete media resend failed: {e}")
                body += f"\n<i>[{esc(entry['label'])} — media no longer available]</i>"
        elif kind:
            body += f"\n<i>[{esc(entry['label'])}]</i>"
        try:
            await client.send_message("me", head + body, parse_mode="html", link_preview=False)
        except Exception as e:
            LOGS.debug(f"antidelete log failed: {e}")


@catub.on(events.MessageEdited(incoming=True, func=lambda e: e.is_private))
async def _ad_edited(event):
    if not _on():
        return
    entry = _cache.get(event.id)
    new = event.raw_text or ""
    if not entry or entry["text"] == new:
        return
    old = entry["text"]
    entry["text"] = new
    await event.client.send_message(
        "me",
        f"{_header(entry, '✏️ <b>Edited</b> by')}\n"
        f"<b>Before:</b><blockquote>{esc(old) or '(no text)'}</blockquote>\n"
        f"<b>After:</b><blockquote>{esc(new) or '(no text)'}</blockquote>",
        parse_mode="html",
        link_preview=False,
    )


@catub.cat_cmd(
    pattern=r"antidelete(?:\s+(on|off))?$",
    command=("antidelete", plugin_category),
    info={
        "header": "See messages people delete or edit in your private chats.",
        "description": "When on, incoming private messages are cached in memory. If the sender deletes "
        "or edits one, the original goes to your Saved Messages (media re-sent when still possible). "
        "Only messages received while it's on are covered, and the cache resets on restart. "
        "Note: deleting a message yourself ('delete for me') also shows up.",
        "usage": ["{tr}antidelete on", "{tr}antidelete off", "{tr}antidelete"],
    },
)
async def antidelete_cmd(event):
    "Anti-delete switch."
    arg = event.pattern_match.group(1)
    if arg:
        kv_set("ANTIDELETE", arg)
        if arg == "off":
            _cache.clear()
        return await edit_delete(event, f"🗑 Anti-delete **{arg}**.", 5)
    await edit_or_reply(
        event,
        f"🗑 **Anti-delete** is **{'on' if _on() else 'off'}** · {len(_cache)} private messages cached",
    )
