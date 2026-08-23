# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~# CatUserBot #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
# Copyright (C) 2020-2023 by TgCatUB@Github.

# This file is part of: https://github.com/TgCatUB/catuserbot
# and is released under the "GNU v3.0 License Agreement".

# Please see: https://github.com/TgCatUB/catuserbot/blob/master/LICENSE
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

import os
import re
from typing import List, Tuple

import httpx

from userbot import catub
from userbot.Config import Config

from ..core.managers import edit_delete, edit_or_reply
from ..helpers import reply_id, unsavegif

plugin_category = "Extra"

GIPHY_SEARCH_URL = "https://api.giphy.com/v1/gifs/search"
MAX_GIFS = 10


def _giphy_api_key() -> str | None:
    return (
        os.environ.get("GIPHY_API_KEY")
        or getattr(Config, "GIPHY_API_KEY", None)
        or None
    )


def _parse_gifs_args(raw: str) -> Tuple[int, str]:
    """
    Parse count + query.
    Supports:
      .gifs cat
      .gifs 5 cat
      .gifs cat ; 5   (legacy)
    """
    text = (raw or "").strip()
    if not text:
        return 1, ""

    # Legacy: query ; count
    if ";" in text:
        parts = [p.strip() for p in text.split(";", 1)]
        query = parts[0]
        try:
            count = int(parts[1]) if len(parts) > 1 and parts[1] else 1
        except ValueError:
            count = 1
        return max(1, min(count, MAX_GIFS)), query

    # Like .img: leading number
    m = re.match(r"^(\d{1,2})\s+(.+)$", text)
    if m:
        return max(1, min(int(m.group(1)), MAX_GIFS)), m.group(2).strip()

    return 1, text


def _best_gif_url(images: dict) -> str | None:
    """Prefer a Telegram-friendly size; fall back to original."""
    if not images:
        return None
    for key in ("downsized_medium", "downsized", "fixed_height", "original"):
        url = (images.get(key) or {}).get("url")
        if url:
            return url
    return None


async def giphy_search(query: str, limit: int = 1) -> List[str]:
    """Search Giphy and return up to `limit` GIF URLs (best-ranked first)."""
    api_key = _giphy_api_key()
    if not api_key:
        raise ValueError(
            "GIPHY_API_KEY is not set. Add it to your env / Dockerfile / HF secrets."
        )

    # Fetch a few extra so we can skip broken entries
    fetch_limit = min(max(limit * 2, 10), 50)
    params = {
        "api_key": api_key,
        "q": query,
        "limit": fetch_limit,
        "offset": 0,
        "rating": "pg-13",
        "lang": "en",
        "bundle": "messaging_non_clips",
    }

    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        r = await client.get(GIPHY_SEARCH_URL, params=params)
        data = r.json()

    meta = data.get("meta") or {}
    if r.status_code != 200 or meta.get("status") != 200:
        msg = meta.get("msg") or r.text[:200]
        raise RuntimeError(f"Giphy API error ({r.status_code}): {msg}")

    urls: List[str] = []
    seen = set()
    for item in data.get("data") or []:
        url = _best_gif_url(item.get("images") or {})
        if not url or url in seen:
            continue
        seen.add(url)
        urls.append(url)
        if len(urls) >= limit:
            break
    return urls


@catub.cat_cmd(
    pattern=r"gifs(?: |$)([\s\S]*)",
    command=("gifs", plugin_category),
    info={
        "header": "Search and send GIFs from Giphy",
        "description": (
            "Searches Giphy with your GIPHY_API_KEY and sends the top matching GIFs. "
            "Default 1 GIF; up to 10."
        ),
        "usage": [
            "{tr}gifs <query>",
            "{tr}gifs <1-10> <query>",
            "{tr}gifs <query> ; <1-10>",
        ],
        "examples": [
            "{tr}gifs cat",
            "{tr}gifs 5 cat looking weird",
            "{tr}gifs funny dog ; 3",
        ],
    },
)
async def some(event):
    """Search Giphy and send matching GIFs."""
    raw = event.pattern_match.group(1)
    reply_to_id = await reply_id(event)
    count, query = _parse_gifs_args(raw)

    if not query:
        return await edit_delete(
            event,
            "`Give a search query.`\n"
            "**Examples:** `.gifs cat` | `.gifs 5 cat looking weird`",
        )

    if not _giphy_api_key():
        return await edit_delete(
            event,
            "**GIPHY_API_KEY not set.**\n"
            "Add `GIPHY_API_KEY=your_key` to env / Dockerfile / HF secrets.",
            10,
        )

    catevent = await edit_or_reply(event, f"`Searching Giphy for` `{query}`...")

    try:
        urls = await giphy_search(query, count)
    except Exception as e:
        return await edit_delete(catevent, f"**GIF search failed:**\n`{e}`", 10)

    if not urls:
        return await edit_delete(catevent, f"`No GIFs found for` `{query}`", 6)

    await catevent.edit(f"`Sending {len(urls)} GIF(s)...`")

    for url in urls:
        try:
            nood = await event.client.send_file(
                event.chat_id,
                url,
                reply_to=reply_to_id,
            )
            await unsavegif(event, nood)
        except Exception:
            continue

    await catevent.delete()
