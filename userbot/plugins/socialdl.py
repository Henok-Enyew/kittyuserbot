# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~# CatUserBot #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
# Social Media Downloader Plugin
# .yta  - YouTube audio  via @YtbAudioBot
# .ttv  - TikTok video   via @ttsavebot
# .tta  - TikTok audio   via @ttsavebot
# .inv  - Instagram video via @ttsavebot
# .ina  - Instagram audio via @ttsavebot
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


async def _get_url(event):
    """Extract URL from event message or reply."""
    msg = event.pattern_match.group(1).strip()
    if not msg and event.is_reply:
        reply = await event.get_reply_message()
        msg = reply.text or ""
    urls = extractor.find_urls(msg)
    return urls[0] if urls else None


async def _talk_to_bot(event, catevent, reply_to_id, bot_username, url,
                       send_start=True, ack_after_url=True,
                       first_timeout=90, more_timeout=5):
    """
    Open a conversation with bot_username, optionally send /start,
    send the URL, collect all media responses, forward them to the user.
    Returns True on success, False on failure.
    """
    media_list = []

    try:
        async with event.client.conversation(bot_username, timeout=first_timeout) as conv:
            # Send /start inside the conversation
            try:
                start_msg = await conv.send_message("/start")
            except YouBlockedUserError:
                await catub(unblock(bot_username))
                start_msg = await conv.send_message("/start")

            if send_start:
                # Consume the /start reply
                try:
                    await conv.get_response(timeout=15)
                    await event.client.send_read_acknowledge(conv.chat_id)
                except asyncio.TimeoutError:
                    pass

            # Send the URL
            await conv.send_message(url)
            await event.client.send_read_acknowledge(conv.chat_id)

            # Some bots send an immediate ack/processing message before the media
            if ack_after_url:
                try:
                    ack = await conv.get_response(timeout=20)
                    await event.client.send_read_acknowledge(conv.chat_id)
                    # If the ack itself has media, keep it
                    if ack.media:
                        media_list.append(ack)
                except asyncio.TimeoutError:
                    pass

            # Collect actual media responses
            while True:
                try:
                    msg = await conv.get_response(timeout=more_timeout)
                    await event.client.send_read_acknowledge(conv.chat_id)
                    media_list.append(msg)
                except asyncio.TimeoutError:
                    break

        if not media_list:
            await catevent.edit(
                f"`@{bot_username} did not respond. Link may be private or unsupported.`"
            )
            return False

        # Separate media from text-only error messages
        media_msgs = [m for m in media_list if m.media]
        if not media_msgs:
            err = media_list[-1].text if media_list else "No media received."
            await catevent.edit(f"`{err[:300]}`")
            return False

        # Forward all media to user's chat
        await catevent.delete()
        await event.client.send_file(
            event.chat_id,
            media_msgs,
            reply_to=reply_to_id,
        )
        await delete_conv(event, bot_username, start_msg)
        return True

    except asyncio.TimeoutError:
        await catevent.edit(f"`Timed out waiting for @{bot_username}. Try again later.`")
        return False
    except Exception as e:
        await catevent.edit(f"**Error:** `{e}`")
        return False


# ---------------------------------------------------------------------------
# .yta — YouTube audio via @YtbAudioBot
# ---------------------------------------------------------------------------
@catub.cat_cmd(
    pattern="yta(?:\s|$)([\s\S]*)",
    command=("yta", plugin_category),
    info={
        "header": "Download YouTube audio.",
        "description": "Downloads audio from YouTube via @YtbAudioBot.",
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
    catevent = await edit_or_reply(event, "`Fetching YouTube audio...`")
    reply_to_id = await reply_id(event)
    await _talk_to_bot(
        event, catevent, reply_to_id,
        YTB_AUDIO_BOT, url,
        send_start=True, ack_after_url=True,
        first_timeout=120, more_timeout=10,
    )


# ---------------------------------------------------------------------------
# .ttv — TikTok video via @ttsavebot
# ---------------------------------------------------------------------------
@catub.cat_cmd(
    pattern="ttv(?:\s|$)([\s\S]*)",
    command=("ttv", plugin_category),
    info={
        "header": "Download TikTok video.",
        "description": "Downloads a TikTok video via @ttsavebot.",
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
    await _talk_to_bot(
        event, catevent, reply_to_id,
        TT_SAVE_BOT, url,
        send_start=True, ack_after_url=False,
        first_timeout=90, more_timeout=5,
    )


# ---------------------------------------------------------------------------
# .tta — TikTok audio via @ttsavebot
# ---------------------------------------------------------------------------
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
    await _talk_to_bot(
        event, catevent, reply_to_id,
        TT_SAVE_BOT, url,
        send_start=True, ack_after_url=False,
        first_timeout=90, more_timeout=5,
    )


# ---------------------------------------------------------------------------
# .inv — Instagram video via @ttsavebot
# ---------------------------------------------------------------------------
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
    await _talk_to_bot(
        event, catevent, reply_to_id,
        TT_SAVE_BOT, url,
        send_start=True, ack_after_url=False,
        first_timeout=90, more_timeout=5,
    )


# ---------------------------------------------------------------------------
# .ina — Instagram audio via @ttsavebot
# ---------------------------------------------------------------------------
@catub.cat_cmd(
    pattern="ina(?:\s|$)([\s\S]*)",
    command=("ina", plugin_category),
    info={
        "header": "Download Instagram audio.",
        "description": "Downloads the audio from an Instagram reel/post via @ttsavebot.",
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
    await _talk_to_bot(
        event, catevent, reply_to_id,
        TT_SAVE_BOT, url,
        send_start=True, ack_after_url=False,
        first_timeout=90, more_timeout=5,
    )
