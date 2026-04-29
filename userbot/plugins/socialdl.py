# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~# CatUserBot #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
# Social Media Downloader Plugin
# .yta  - YouTube audio (via @YtbAudioBot)
# .ttv  - TikTok video (via @ttsavebot)
# .tta  - TikTok audio (via @ttsavebot)
# .inv  - Instagram video (via @ttsavebot)
# .ina  - Instagram audio (via @ttsavebot)
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

import asyncio

from telethon.errors.rpcerrorlist import YouBlockedUserError
from telethon.tl.functions.contacts import UnblockRequest as unblock
from urlextract import URLExtract

from userbot import catub

from ..core.managers import edit_delete, edit_or_reply
from ..helpers.functions import delete_conv
from ..helpers.utils import reply_id

plugin_category = "misc"
extractor = URLExtract()

YTB_AUDIO_BOT = "YtbAudioBot"
TT_SAVE_BOT = "ttsavebot"


async def _unblock_and_start(client, bot_username):
    """Unblock bot if needed and send /start, return the start message."""
    try:
        msg = await client.send_message(bot_username, "/start")
    except YouBlockedUserError:
        await client(unblock(bot_username))
        msg = await client.send_message(bot_username, "/start")
    return msg


async def _collect_media(conv, timeout_first=60, timeout_more=5):
    """Collect all media messages from conversation until timeout."""
    media_list = []
    try:
        msg = await conv.get_response(timeout=timeout_first)
        while True:
            if msg.media:
                media_list.append(msg)
            elif msg.text and not msg.media:
                # text-only could be an error message
                if not media_list:  # only matters if we have nothing yet
                    media_list.append(msg)
            try:
                msg = await conv.get_response(timeout=timeout_more)
            except asyncio.TimeoutError:
                break
    except asyncio.TimeoutError:
        pass
    return media_list


async def _get_url(event):
    """Extract URL from event message or reply."""
    msg = event.pattern_match.group(1).strip()
    if not msg and event.is_reply:
        reply = await event.get_reply_message()
        msg = reply.text or ""
    urls = extractor.find_urls(msg)
    return urls[0] if urls else None


# ─────────────────────────────────────────────────────────────────────────────
# .yta  — YouTube audio via @YtbAudioBot
# ─────────────────────────────────────────────────────────────────────────────
@catub.cat_cmd(
    pattern="yta(?:\s|$)([\s\S]*)",
    command=("yta", plugin_category),
    info={
        "header": "Download YouTube audio.",
        "description": "Downloads audio from a YouTube link via @YtbAudioBot.",
        "usage": "{tr}yta <youtube link>",
        "examples": "{tr}yta https://youtu.be/dQw4w9WgXcQ",
    },
)
async def yta_cmd(event):
    "Download YouTube audio via @YtbAudioBot."
    url = await _get_url(event)
    if not url:
        return await edit_delete(event, "`Give me a YouTube link.`")
    if "youtu" not in url:
        return await edit_delete(event, "`That doesn't look like a YouTube URL.`")

    catevent = await edit_or_reply(event, "`Fetching audio from YouTube...`")
    reply_to_id = await reply_id(event)

    try:
        start_msg = await _unblock_and_start(event.client, YTB_AUDIO_BOT)
        async with event.client.conversation(YTB_AUDIO_BOT, timeout=120) as conv:
            await conv.get_response(timeout=10)  # consume /start reply
            await conv.send_message(url)
            msgs = await _collect_media(conv, timeout_first=90, timeout_more=5)

        if not msgs:
            return await catevent.edit("`@YtbAudioBot didn't respond. Try again later.`")

        result = msgs[-1]  # last message is usually the audio file
        if not result.media:
            return await catevent.edit(f"`Bot said: {result.text[:200]}`")

        await event.client.send_file(
            event.chat_id,
            result.media,
            caption=result.text or "",
            reply_to=reply_to_id,
        )
        await delete_conv(event, YTB_AUDIO_BOT, start_msg)
    except asyncio.TimeoutError:
        return await catevent.edit("`Timed out waiting for @YtbAudioBot.`")
    except Exception as e:
        return await catevent.edit(f"**Error:** `{e}`")

    await catevent.delete()


# ─────────────────────────────────────────────────────────────────────────────
# .ttv  — TikTok video via @ttsavebot
# ─────────────────────────────────────────────────────────────────────────────
@catub.cat_cmd(
    pattern="ttv(?:\s|$)([\s\S]*)",
    command=("ttv", plugin_category),
    info={
        "header": "Download TikTok video.",
        "description": "Downloads a TikTok video without watermark via @ttsavebot.",
        "usage": "{tr}ttv <tiktok link>",
        "examples": "{tr}ttv https://vm.tiktok.com/xxxxx",
    },
)
async def ttv_cmd(event):
    "Download TikTok video via @ttsavebot."
    url = await _get_url(event)
    if not url:
        return await edit_delete(event, "`Give me a TikTok link.`")
    if "tiktok.com" not in url:
        return await edit_delete(event, "`That doesn't look like a TikTok URL.`")

    catevent = await edit_or_reply(event, "`Fetching TikTok video...`")
    reply_to_id = await reply_id(event)
    await _forward_from_bot(event, catevent, reply_to_id, TT_SAVE_BOT, url, want="video")


# ─────────────────────────────────────────────────────────────────────────────
# .tta  — TikTok audio via @ttsavebot
# ─────────────────────────────────────────────────────────────────────────────
@catub.cat_cmd(
    pattern="tta(?:\s|$)([\s\S]*)",
    command=("tta", plugin_category),
    info={
        "header": "Download TikTok audio.",
        "description": "Downloads the audio track from a TikTok video via @ttsavebot.",
        "usage": "{tr}tta <tiktok link>",
        "examples": "{tr}tta https://vm.tiktok.com/xxxxx",
    },
)
async def tta_cmd(event):
    "Download TikTok audio via @ttsavebot."
    url = await _get_url(event)
    if not url:
        return await edit_delete(event, "`Give me a TikTok link.`")
    if "tiktok.com" not in url:
        return await edit_delete(event, "`That doesn't look like a TikTok URL.`")

    catevent = await edit_or_reply(event, "`Fetching TikTok audio...`")
    reply_to_id = await reply_id(event)
    await _forward_from_bot(event, catevent, reply_to_id, TT_SAVE_BOT, url, want="audio")


# ─────────────────────────────────────────────────────────────────────────────
# .inv  — Instagram video via @ttsavebot
# ─────────────────────────────────────────────────────────────────────────────
@catub.cat_cmd(
    pattern="inv(?:\s|$)([\s\S]*)",
    command=("inv", plugin_category),
    info={
        "header": "Download Instagram video.",
        "description": "Downloads a video from an Instagram reel/post via @ttsavebot.",
        "usage": "{tr}inv <instagram link>",
        "examples": "{tr}inv https://www.instagram.com/reel/xxxxx",
    },
)
async def inv_cmd(event):
    "Download Instagram video via @ttsavebot."
    url = await _get_url(event)
    if not url:
        return await edit_delete(event, "`Give me an Instagram link.`")
    if "instagram.com" not in url:
        return await edit_delete(event, "`That doesn't look like an Instagram URL.`")

    catevent = await edit_or_reply(event, "`Fetching Instagram video...`")
    reply_to_id = await reply_id(event)
    await _forward_from_bot(event, catevent, reply_to_id, TT_SAVE_BOT, url, want="video")


# ─────────────────────────────────────────────────────────────────────────────
# .ina  — Instagram audio via @ttsavebot
# ─────────────────────────────────────────────────────────────────────────────
@catub.cat_cmd(
    pattern="ina(?:\s|$)([\s\S]*)",
    command=("ina", plugin_category),
    info={
        "header": "Download Instagram audio.",
        "description": "Downloads the audio track from an Instagram reel/post via @ttsavebot.",
        "usage": "{tr}ina <instagram link>",
        "examples": "{tr}ina https://www.instagram.com/reel/xxxxx",
    },
)
async def ina_cmd(event):
    "Download Instagram audio via @ttsavebot."
    url = await _get_url(event)
    if not url:
        return await edit_delete(event, "`Give me an Instagram link.`")
    if "instagram.com" not in url:
        return await edit_delete(event, "`That doesn't look like an Instagram URL.`")

    catevent = await edit_or_reply(event, "`Fetching Instagram audio...`")
    reply_to_id = await reply_id(event)
    await _forward_from_bot(event, catevent, reply_to_id, TT_SAVE_BOT, url, want="audio")


# ─────────────────────────────────────────────────────────────────────────────
# Shared helper — talk to bot, collect result, forward to chat
# ─────────────────────────────────────────────────────────────────────────────
async def _forward_from_bot(event, catevent, reply_to_id, bot_username, url, want="video"):
    """
    Send URL to bot_username, collect media responses, forward the
    appropriate one (video or audio) back to the user's chat.
    """
    from telethon.tl.types import (
        MessageMediaDocument,
        MessageMediaPhoto,
    )
    from telethon.tl.types import DocumentAttributeAudio, DocumentAttributeVideo

    def _is_video(msg):
        if not msg.media:
            return False
        if isinstance(msg.media, MessageMediaPhoto):
            return False
        if isinstance(msg.media, MessageMediaDocument):
            for attr in msg.media.document.attributes:
                if isinstance(attr, DocumentAttributeVideo):
                    return True
        return False

    def _is_audio(msg):
        if not msg.media or not isinstance(msg.media, MessageMediaDocument):
            return False
        for attr in msg.media.document.attributes:
            if isinstance(attr, DocumentAttributeAudio):
                return True
        return False

    try:
        start_msg = await _unblock_and_start(event.client, bot_username)

        async with event.client.conversation(bot_username, timeout=120) as conv:
            # consume /start reply
            try:
                await conv.get_response(timeout=10)
            except asyncio.TimeoutError:
                pass
            await conv.send_message(url)
            await event.client.send_read_acknowledge(conv.chat_id)
            msgs = await _collect_media(conv, timeout_first=60, timeout_more=5)

        await event.client.send_read_acknowledge(bot_username)

        if not msgs:
            return await catevent.edit(
                f"`@{bot_username} didn't respond. The link may be private or unsupported.`"
            )

        # Filter for desired media type
        if want == "audio":
            picks = [m for m in msgs if _is_audio(m)]
            if not picks:
                # fall back to any media
                picks = [m for m in msgs if m.media]
        else:  # video
            picks = [m for m in msgs if _is_video(m)]
            if not picks:
                picks = [m for m in msgs if m.media]

        if not picks:
            # bot replied with text (error/not found)
            text_msgs = [m for m in msgs if m.text]
            err = text_msgs[-1].text if text_msgs else "No media received."
            return await catevent.edit(f"`{err[:300]}`")

        # Forward all matching media to the user's chat
        for msg in picks:
            await event.client.send_file(
                event.chat_id,
                msg.media,
                caption=msg.text or "",
                reply_to=reply_to_id,
            )

        await delete_conv(event, bot_username, start_msg)

    except asyncio.TimeoutError:
        return await catevent.edit(
            f"`Timed out waiting for @{bot_username}. Try again later.`"
        )
    except Exception as e:
        return await catevent.edit(f"**Error:** `{e}`")

    await catevent.delete()
