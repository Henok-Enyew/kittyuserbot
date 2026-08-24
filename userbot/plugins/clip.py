# Unified media download — .clip

import os
import re

from userbot import Convert, catub
from userbot.core.managers import edit_delete, edit_or_reply
from userbot.helpers.functions.clip_router import clip_download, extract_url
from userbot.helpers.utils import reply_id

plugin_category = "misc"


def _parse_clip_args(raw: str):
    """Returns (mode, url, gif_duration, gif_width). mode: video|audio|gif"""
    text = (raw or "").strip()
    if not text:
        return "video", None, 10, 480
    if text.lower().startswith("audio "):
        return "audio", extract_url(text[6:]), 10, 480
    if text.lower().startswith("gif "):
        rest = text[4:].strip()
        m = re.match(r"^(\d+)(?:\s+(\d+))?\s+(.+)$", rest)
        if m:
            return "gif", extract_url(m.group(3)), int(m.group(1)), int(m.group(2) or 480)
        return "gif", extract_url(rest), 10, 480
    return "video", extract_url(text), 10, 480


@catub.cat_cmd(
    pattern=r"clip(?:\s+(.+))?$",
    command=("clip", plugin_category),
    info={
        "header": "Unified media downloader",
        "description": "Auto-detect platform and download. Flags: audio, gif.",
        "usage": [
            "{tr}clip <url>",
            "{tr}clip audio <url>",
            "{tr}clip gif <url>",
            "{tr}clip gif 5 320 <url>",
        ],
        "examples": [
            "{tr}clip https://instagram.com/reel/...",
            "{tr}clip audio https://youtu.be/...",
        ],
    },
)
async def clip_cmd(event):
    "Download media from URL — native first, bot fallback."
    raw = event.pattern_match.group(1)
    reply = await event.get_reply_message()
    if not raw and reply:
        raw = reply.text or reply.message
    mode, url, gif_dur, gif_w = _parse_clip_args(raw)
    if not url:
        return await edit_delete(
            event,
            "**Usage:** `.clip <url>` | `.clip audio <url>` | `.clip gif <url>`",
        )
    catevent = await edit_or_reply(event, f"**Fetching media...** (`{mode}`)")
    reply_to = await reply_id(event)
    result = await clip_download(event, catevent, url, audio=(mode == "audio"))
    if not result:
        return await edit_delete(catevent, "**Could not download this URL.**")
    if result["type"] == "bot":
        return
    path = result["path"]
    meta = result.get("meta") or {}
    title = meta.get("title", "Media")
    thumb = meta.get("thumb")
    cleanup = [path, thumb]

    if mode == "gif":
        gif_path = os.path.join("./temp", "clip_output.gif")
        gif_w = max(240, min(gif_w, 720))
        gif_dur = max(1, min(gif_dur, 30))
        converted = await Convert.to_vgif_from_path(
            path, gif_path, max_duration=gif_dur, max_width=gif_w
        )
        if not converted:
            return await edit_delete(catevent, "**GIF conversion failed.**")
        path = converted
        cleanup.append(gif_path)

    try:
        await event.client.send_file(
            event.chat_id,
            path,
            caption=f"**{title}**",
            thumb=thumb if thumb and os.path.exists(thumb) else None,
            supports_streaming=(mode != "gif"),
            reply_to=reply_to,
        )
        await catevent.delete()
    finally:
        for f in cleanup:
            if f and os.path.exists(f):
                os.remove(f)
