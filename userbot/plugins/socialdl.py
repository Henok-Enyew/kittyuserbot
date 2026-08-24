# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~# CatUserBot #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
# Social Media Downloader Plugin
# .yta  - YouTube audio  via @YtbAudioBot
# .ttv  - TikTok video   via @ttsavebot
# .tta  - TikTok audio   via @ttsavebot
# .inv  - Instagram video via @ttsavebot
# .ina  - Instagram audio via @ttsavebot
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

from urlextract import URLExtract

from userbot import catub

from ..core.managers import edit_delete, edit_or_reply
from ..helpers.functions.clip_router import (
    TT_SAVE_BOT,
    YTB_AUDIO_BOT,
    extract_url,
    talk_to_bot,
)
from ..helpers.utils import reply_id

plugin_category = "misc"
extractor = URLExtract()


async def _get_url(event):
    """Extract URL from event message or reply."""
    msg = event.pattern_match.group(1).strip()
    if not msg and event.is_reply:
        reply = await event.get_reply_message()
        msg = reply.text or ""
    return extract_url(msg)


# ---------------------------------------------------------------------------
# .yta — YouTube audio via @YtbAudioBot
# ---------------------------------------------------------------------------
@catub.cat_cmd(
    pattern=r"yta(?:\s|$)([\s\S]*)",
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
    await talk_to_bot(
        event, catevent, YTB_AUDIO_BOT, url,
        first_timeout=120, more_timeout=10,
    )


# ---------------------------------------------------------------------------
# .ttv — TikTok video via @ttsavebot
# ---------------------------------------------------------------------------
@catub.cat_cmd(
    pattern=r"ttv(?:\s|$)([\s\S]*)",
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
    await talk_to_bot(
        event, catevent, TT_SAVE_BOT, url,
        first_timeout=90, more_timeout=5,
    )


# ---------------------------------------------------------------------------
# .tta — TikTok audio via @ttsavebot
# ---------------------------------------------------------------------------
@catub.cat_cmd(
    pattern=r"tta(?:\s|$)([\s\S]*)",
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
    await talk_to_bot(
        event, catevent, TT_SAVE_BOT, url,
        first_timeout=90, more_timeout=5,
    )


# ---------------------------------------------------------------------------
# .inv — Instagram video via @ttsavebot
# ---------------------------------------------------------------------------
@catub.cat_cmd(
    pattern=r"inv(?:\s|$)([\s\S]*)",
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
    await talk_to_bot(
        event, catevent, TT_SAVE_BOT, url,
        first_timeout=90, more_timeout=5,
    )


# ---------------------------------------------------------------------------
# .ina — Instagram audio via @ttsavebot
# ---------------------------------------------------------------------------
@catub.cat_cmd(
    pattern=r"ina(?:\s|$)([\s\S]*)",
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
    await talk_to_bot(
        event, catevent, TT_SAVE_BOT, url,
        first_timeout=90, more_timeout=5,
    )
