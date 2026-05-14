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
                       first_timeout=90, more_timeout=5):
    """
    1. Send /start outside conversation (fire and forget, just to wake the bot)
    2. Wait briefly for bot to process
    3. Open fresh conversation, send URL only, collect only media responses (skip promotional text)
    """
    media_list = []

    try:
        # Step 1: wake the bot with /start outside any conversation
        try:
            start_msg = await event.client.send_message(bot_username, "/start")
        except YouBlockedUserError:
            await catub(unblock(bot_username))
            start_msg = await event.client.send_message(bot_username, "/start")
        except Exception:
            start_msg = None

        # Step 2: give bot time to process /start before we open conversation
        await asyncio.sleep(3)

        # Step 3: open fresh conversation and send URL only
        async with event.client.conversation(bot_username, timeout=first_timeout) as conv:
            await conv.send_message(url)
            await event.client.send_read_acknowledge(conv.chat_id)

            # Collect all responses until timeout
            all_messages = []
            while True:
                try:
                    msg = await conv.get_response(timeout=more_timeout)
                    await event.client.send_read_acknowledge(conv.chat_id)
                    all_messages.append(msg)
                except asyncio.TimeoutError:
                    break

        if not all_messages:
            await catevent.edit(
                f"`@{bot_username} did not respond. Link may be private or unsupported.`"
            )
            return False

        # Filter: only keep messages with actual media (video, audio, document, photo)
        # Skip stickers, GIFs, and text-only promotional messages
        for msg in all_messages:
            if msg.media:
                # Check for actual downloadable media (not stickers/animated emojis)
                if msg.video or msg.audio or msg.document or msg.photo:
                    # Additional check: skip GIFs (they're documents with video mime type)
                    if msg.document:
                        # Skip if it's an animated sticker or GIF
                        mime = getattr(msg.document, 'mime_type', '')
                        if 'image/gif' in mime or msg.document.attributes:
                            # Check if it's a sticker
                            is_sticker = any(
                                hasattr(attr, 'stickerset') 
                                for attr in msg.document.attributes
                            )
                            if is_sticker:
                                continue  # Skip stickers
                    media_list.append(msg)

        if not media_list:
            # Check if there's an error message in text responses
            text_messages = [m.text for m in all_messages if m.text and not m.media]
            if text_messages:
                # Look for error indicators
                error_text = text_messages[-1]
                if any(word in error_text.lower() for word in ['error', 'invalid', 'failed', 'not found', 'unsupported']):
                    await catevent.edit("`Invalid link or unsupported source.`")
                    return False
            
            await catevent.edit("`Couldn't get the media, try again.`")
            return False

        # Forward media to user's chat
        await catevent.delete()
        for media_msg in media_list:
            await event.client.forward_messages(
                event.chat_id,
                media_msg,
                from_peer=bot_username
            )
        
        if start_msg:
            await delete_conv(event, bot_username, start_msg)
        return True

    except asyncio.TimeoutError:
        await catevent.edit("`Couldn't get the media, try again.`")
        return False
    except Exception as e:
        await catevent.edit(f"**Error:** `{str(e)[:200]}`")
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
        first_timeout=90, more_timeout=5,
    )
