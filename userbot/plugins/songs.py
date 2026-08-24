# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~# CatUserBot #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
# Copyright (C) 2020-2023 by TgCatUB@Github.

# This file is part of: https://github.com/TgCatUB/catuserbot
# and is released under the "GNU v3.0 License Agreement".

# Please see: https://github.com/TgCatUB/catuserbot/blob/master/LICENSE
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

import os
import uuid

from ShazamAPI import Shazam
from validators.url import url

from ..Config import Config
from ..core.logger import logging
from ..core.managers import edit_delete, edit_or_reply
from ..helpers.functions import yt_search
from ..helpers.tools import media_type
from ..helpers.utils import reply_id
from . import catub, song_download

plugin_category = "utils"
LOGS = logging.getLogger(__name__)

SONG_SEARCH_STRING = "<code>wi8..! I am finding your song....</code>"
SONG_NOT_FOUND = "<code>Sorry !I am unable to find any song like that</code>"


def _resolve_query(event, text_group: int, reply):
    query = event.pattern_match.group(text_group)
    if query:
        return str(query).strip()
    if reply and reply.message:
        return str(reply.message).strip()
    return None


async def _send_native_song(event, query, quality="128k", video=False):
    reply_to_id = await reply_id(event)
    catevent = await edit_or_reply(event, "`wi8..! I am finding your song....`")
    video_link = await yt_search(query)
    if not url(video_link):
        await catevent.edit(
            f"Sorry!. I can't find any related video/audio for `{query}`"
        )
        return

    result = await song_download(
        video_link, catevent, quality=quality, video=video
    )
    if not isinstance(result, tuple) or len(result) != 3:
        return

    media_file, catthumb, title = result
    if not media_file or not os.path.exists(media_file):
        return

    await event.client.send_file(
        event.chat_id,
        media_file,
        force_document=False,
        caption=f"**Title:** `{title}`",
        thumb=catthumb if catthumb and os.path.exists(catthumb) else None,
        supports_streaming=True,
        reply_to=reply_to_id,
    )
    await catevent.delete()
    for file_path in (catthumb, media_file):
        if file_path and os.path.exists(file_path):
            os.remove(file_path)


@catub.cat_cmd(
    pattern="song(320)?(?:\s|$)([\s\S]*)",
    command=("song", plugin_category),
    info={
        "header": "To get songs from youtube.",
        "description": "Basically this command searches youtube and send the first video as audio file.",
        "flags": {
            "320": "if you use song320 then you get 320k quality else 128k quality",
        },
        "usage": "{tr}song <song name>",
        "examples": "{tr}song memories song",
    },
)
async def song(event):
    "To search songs"
    reply = await event.get_reply_message()
    query = _resolve_query(event, 2, reply)
    if not query:
        return await edit_or_reply(event, "`What I am Supposed to find `")
    quality = "320k" if event.pattern_match.group(1) == "320" else "128k"
    await _send_native_song(event, query, quality=quality, video=False)


@catub.cat_cmd(
    pattern="vsong(?:\s|$)([\s\S]*)",
    command=("vsong", plugin_category),
    info={
        "header": "To get video songs from youtube.",
        "description": "Basically this command searches youtube and sends the first video",
        "usage": "{tr}vsong <song name>",
        "examples": "{tr}vsong memories song",
    },
)
async def vsong(event):
    "To search video songs"
    reply = await event.get_reply_message()
    query = _resolve_query(event, 1, reply)
    if not query:
        return await edit_or_reply(event, "`What I am Supposed to find`")
    await _send_native_song(event, query, video=True)


@catub.cat_cmd(
    pattern="(s(ha)?z(a)?m)(?:\s|$)([\s\S]*)",
    command=("shazam", plugin_category),
    info={
        "header": "To reverse search song.",
        "description": "Reverse search audio file using shazam api",
        "flags": {"s": "To download and send the matched song (320k MP3)"},
        "usage": [
            "{tr}shazam <reply to voice/audio>",
            "{tr}szm <reply to voice/audio>",
            "{tr}szm s <reply to voice/audio>",
        ],
    },
)
async def shazamcmd(event):
    "To reverse search song."
    reply = await event.get_reply_message()
    mediatype = await media_type(reply)
    flag = (event.pattern_match.group(4) or "").strip().lower()
    if not reply or not mediatype or mediatype not in ["Voice", "Audio"]:
        return await edit_delete(
            event, "__Reply to Voice clip or Audio clip to reverse search that song.__"
        )

    catevent = await edit_or_reply(event, "__Downloading the audio clip...__")
    temp_dir = getattr(Config, "TEMP_DIR", "./temp/")
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f"shazam_{uuid.uuid4().hex}.mp3")

    try:
        downloaded = await event.client.download_media(reply, file=temp_path)
        if not downloaded or not os.path.exists(downloaded):
            return await edit_delete(catevent, "__Could not download the audio clip.__")

        with open(downloaded, "rb") as audio_file:
            audio_bytes = audio_file.read()
        if not audio_bytes:
            return await edit_delete(catevent, "__Downloaded audio clip is empty.__")

        shazam = Shazam(audio_bytes)
        recognize_generator = shazam.recognizeSong()
        track = next(recognize_generator)[1]["track"]
    except StopIteration:
        return await edit_delete(
            catevent, "**No song match found for this audio clip.**"
        )
    except Exception as e:
        LOGS.error(f"shazam error: {e}")
        return await edit_delete(
            catevent, f"**Error while reverse searching song:**\n__{e}__"
        )
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    title = track.get("title") or "Unknown"
    artist = track.get("subtitle") or ""
    search_query = track.get("share", {}).get("subject") or f"{artist} {title}".strip()
    yt_link = await yt_search(search_query)
    yt_url = yt_link if url(yt_link) else None

    if flag == "s" and yt_url:
        reply_to_id = await reply_id(event)
        result = await song_download(yt_url, catevent, quality="320k", video=False)
        if isinstance(result, tuple) and len(result) == 3:
            song_file, catthumb, dl_title = result
            if song_file and os.path.exists(song_file):
                await event.client.send_file(
                    event.chat_id,
                    song_file,
                    force_document=False,
                    caption=(
                        f"<b>Song :</b> <code>{title}</code>\n"
                        f"<b>Artist :</b> <code>{artist}</code>\n"
                        f"<b>YouTube :</b> <a href='{yt_url}'>link</a>"
                    ),
                    thumb=catthumb if catthumb and os.path.exists(catthumb) else None,
                    supports_streaming=True,
                    reply_to=reply_to_id,
                    parse_mode="html",
                )
                await catevent.delete()
                for file_path in (catthumb, song_file):
                    if file_path and os.path.exists(file_path):
                        os.remove(file_path)
                return

    cover = track.get("images", {}).get("background")
    caption = (
        f"<b>Song :</b> <code>{title}</code>\n"
        f"<b>Artist :</b> <code>{artist}</code>\n"
    )
    if yt_url:
        caption += f"<b>YouTube :</b> <a href='{yt_url}'>link</a>"
    else:
        caption += "<b>YouTube :</b> not found"

    await event.client.send_file(
        event.chat_id,
        cover,
        caption=caption,
        reply_to=reply,
        parse_mode="html",
    )
    await catevent.delete()


@catub.cat_cmd(
    pattern="song2(?:\s|$)([\s\S]*)",
    command=("song2", plugin_category),
    info={
        "header": "To search songs and upload to telegram",
        "description": "Searches YouTube and uploads the first match as 320k MP3.",
        "usage": "{tr}song2 <song name>",
        "examples": "{tr}song2 memories",
    },
)
async def song2(event):
    "To search songs (320k native download)"
    reply = await event.get_reply_message()
    query = _resolve_query(event, 1, reply)
    if not query:
        return await edit_or_reply(event, SONG_NOT_FOUND, parse_mode="html")
    await _send_native_song(event, query, quality="320k", video=False)
