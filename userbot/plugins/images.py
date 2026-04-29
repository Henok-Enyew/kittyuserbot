# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~# CatUserBot #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
# Copyright (C) 2020-2023 by TgCatUB@Github.

# This file is part of: https://github.com/TgCatUB/catuserbot
# and is released under the "GNU v3.0 License Agreement".

# Please see: https://github.com/TgCatUB/catuserbot/blob/master/LICENSE
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

import contextlib
import os
import re
import tempfile

import httpx
from telethon.errors.rpcerrorlist import MediaEmptyError

from userbot import catub

from ..core.managers import edit_or_reply
from ..helpers.utils import reply_id

plugin_category = "misc"

BING_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


async def bing_image_search(query: str, limit: int = 3) -> list:
    """Search Bing Images and return up to `limit` image URLs."""
    urls = []
    offset = 0
    async with httpx.AsyncClient(headers=BING_HEADERS, follow_redirects=True, timeout=20) as client:
        while len(urls) < limit:
            r = await client.get(
                "https://www.bing.com/images/async",
                params={
                    "q": query,
                    "first": offset,
                    "count": min(limit * 2, 20),
                    "adlt": "moderate",
                    "qft": "",
                },
            )
            found = re.findall(r'murl&quot;:&quot;(https?://[^&]+)&quot;', r.text)
            if not found:
                break
            urls.extend(found)
            offset += len(found)
            if offset > 50:
                break
    return list(dict.fromkeys(urls))[:limit]  # deduplicate, trim


async def download_images(urls: list) -> list:
    """Download image URLs to temp files, return list of file paths."""
    paths = []
    async with httpx.AsyncClient(headers=BING_HEADERS, follow_redirects=True, timeout=20) as client:
        for url in urls:
            try:
                r = await client.get(url)
                if r.status_code == 200 and len(r.content) > 1000:
                    ct = r.headers.get("content-type", "")
                    ext = ".png" if "png" in ct else ".gif" if "gif" in ct else ".webp" if "webp" in ct else ".jpg"
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                    tmp.write(r.content)
                    tmp.close()
                    paths.append(tmp.name)
            except Exception:
                continue
    return paths


@catub.cat_cmd(
    pattern="img(?: |$)(\d*)? ?([\s\S]*)",
    command=("img", plugin_category),
    info={
        "header": "Image search.",
        "description": "Search images via Bing. Sends up to 10 images (default 3).",
        "usage": ["{tr}img <1-10> <query>", "{tr}img <query>"],
        "examples": [
            "{tr}img 10 catuserbot",
            "{tr}img catuserbot",
            "{tr}img 7 cats",
        ],
    },
)
async def img_sampler(event):
    "Image search via Bing."
    reply_to_id = await reply_id(event)
    if event.is_reply and not event.pattern_match.group(2):
        reply_msg = await event.get_reply_message()
        query = str(reply_msg.message)
    else:
        query = str(event.pattern_match.group(2))
    if not query:
        return await edit_or_reply(event, "Reply to a message or pass a query to search!")

    cat = await edit_or_reply(event, "`Searching images...`")

    lim = 3
    if event.pattern_match.group(1):
        try:
            lim = max(1, min(int(event.pattern_match.group(1)), 10))
        except ValueError:
            pass

    try:
        urls = await bing_image_search(query, lim)
    except Exception as e:
        return await cat.edit(f"**Search failed:**\n`{e}`")

    if not urls:
        return await cat.edit("No images found for that query.")

    await cat.edit("`Downloading images...`")
    paths = await download_images(urls)

    if not paths:
        return await cat.edit("Found URLs but failed to download any images.")

    try:
        await event.client.send_file(event.chat_id, paths, reply_to=reply_to_id)
    except MediaEmptyError:
        for p in paths:
            with contextlib.suppress(MediaEmptyError):
                await event.client.send_file(event.chat_id, p, reply_to=reply_to_id)
    finally:
        for p in paths:
            with contextlib.suppress(Exception):
                os.unlink(p)

    await cat.delete()
