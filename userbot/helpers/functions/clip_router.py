# Unified media download router — native yt-dlp first, bot fallback

import asyncio
import os
import re
from pathlib import Path

from telethon.errors.rpcerrorlist import YouBlockedUserError
from telethon.tl.functions.contacts import UnblockRequest as unblock
from urlextract import URLExtract
from yt_dlp import YoutubeDL

from userbot import catub
from userbot.helpers.functions import delete_conv

extractor = URLExtract()

TT_SAVE_BOT = "ttsavebot"
YTB_AUDIO_BOT = "YtbAudioBot"


def extract_url(text: str) -> str | None:
    if not text:
        return None
    urls = extractor.find_urls(text)
    if not urls:
        return None
    url = urls[0]
    if "instagram.com" in url and "?" in url:
        url = url.split("?", 1)[0]
    return url.rstrip("/")


def detect_platform(url: str) -> str:
    u = url.lower()
    if "instagram.com" in u:
        return "instagram"
    if "tiktok.com" in u:
        return "tiktok"
    if "youtu" in u:
        return "youtube"
    if "twitter.com" in u or "x.com" in u:
        return "twitter"
    return "generic"


def _bot_for_platform(platform: str, audio: bool = False) -> str:
    if platform == "youtube" and audio:
        return YTB_AUDIO_BOT
    return TT_SAVE_BOT


async def native_download(url: str, audio: bool = False, out_dir: str = "./temp"):
    os.makedirs(out_dir, exist_ok=True)
    if audio:
        opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(out_dir, "clip_%(id)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "extractor_args": {"youtube": {"player_client": ["mweb", "web"]}},
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "320",
                }
            ],
        }
    else:
        opts = {
            "format": "best[height<=720]/best",
            "outtmpl": os.path.join(out_dir, "clip_%(id)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "extractor_args": {"youtube": {"player_client": ["mweb", "web"]}},
        }
    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                return None, None
            vid = info.get("id", "clip")
            if audio:
                path = os.path.join(out_dir, f"clip_{vid}.mp3")
                if not os.path.exists(path):
                    for f in os.listdir(out_dir):
                        if f.startswith(f"clip_{vid}") and f.endswith(".mp3"):
                            path = os.path.join(out_dir, f)
                            break
            else:
                ext = info.get("ext", "mp4")
                path = os.path.join(out_dir, f"clip_{vid}.{ext}")
                if not os.path.exists(path):
                    matches = list(Path(out_dir).glob(f"clip_{vid}.*"))
                    path = str(matches[0]) if matches else None
            title = info.get("title", "Media")
            if path and os.path.exists(path):
                thumb = None
                for ext in (".jpg", ".webp", ".png"):
                    candidate = os.path.splitext(path)[0] + ext
                    if os.path.exists(candidate):
                        thumb = candidate
                        break
                return path, {"title": title, "thumb": thumb}
    except Exception:
        pass
    return None, None


async def talk_to_bot(event, catevent, bot_username, url, first_timeout=90, more_timeout=5):
    """Download via third-party bot and forward media."""
    media_list = []
    start_msg = None
    try:
        try:
            start_msg = await event.client.send_message(bot_username, "/start")
        except YouBlockedUserError:
            await catub(unblock(bot_username))
            start_msg = await event.client.send_message(bot_username, "/start")
        except Exception:
            start_msg = None
        await asyncio.sleep(3)
        async with event.client.conversation(bot_username, timeout=first_timeout) as conv:
            await conv.send_message(url)
            await event.client.send_read_acknowledge(conv.chat_id)
            all_messages = []
            while True:
                try:
                    msg = await conv.get_response(timeout=more_timeout)
                    await event.client.send_read_acknowledge(conv.chat_id)
                    all_messages.append(msg)
                except asyncio.TimeoutError:
                    break
        if not all_messages:
            await catevent.edit(f"`@{bot_username} did not respond.`")
            return False
        for msg in all_messages:
            if msg.media and (msg.video or msg.audio or msg.document or msg.photo):
                if msg.document:
                    mime = getattr(msg.document, "mime_type", "") or ""
                    if any(
                        hasattr(a, "stickerset") for a in (msg.document.attributes or [])
                    ):
                        continue
                    if "image/gif" in mime:
                        continue
                media_list.append(msg)
        if not media_list:
            await catevent.edit("`Couldn't get media from bot.`")
            return False
        await catevent.delete()
        for media_msg in media_list:
            await event.client.forward_messages(
                event.chat_id, media_msg, from_peer=bot_username
            )
        if start_msg:
            await delete_conv(event, bot_username, start_msg)
        return True
    except asyncio.TimeoutError:
        await catevent.edit("`Bot timed out. Try again.`")
        return False
    except Exception as e:
        await catevent.edit(f"**Error:** `{str(e)[:200]}`")
        return False


async def clip_download(event, catevent, url: str, audio: bool = False):
    """Try native download; fall back to bot."""
    path, meta = await native_download(url, audio=audio)
    if path:
        return {"type": "native", "path": path, "meta": meta or {}}
    platform = detect_platform(url)
    bot = _bot_for_platform(platform, audio=audio)
    ok = await talk_to_bot(event, catevent, bot, url)
    if ok:
        return {"type": "bot", "path": None, "meta": {}}
    return None
