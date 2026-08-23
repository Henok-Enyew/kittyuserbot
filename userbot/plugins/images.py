# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~# CatUserBot #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
# Copyright (C) 2020-2023 by TgCatUB@Github.

# This file is part of: https://github.com/TgCatUB/catuserbot
# and is released under the "GNU v3.0 License Agreement".

# Please see: https://github.com/TgCatUB/catuserbot/blob/master/LICENSE
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

import contextlib
import html
import os
import re
import tempfile
from typing import List, Tuple
from urllib.parse import unquote

import httpx
from telethon.errors.rpcerrorlist import MediaEmptyError, MediaInvalidError

from userbot import catub

from ..core.managers import edit_or_reply
from ..helpers.utils import reply_id

plugin_category = "misc"

BING_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Bing CDN thumbnails — not full-size images
_THUMB_HOST_RE = re.compile(r"(\.bing\.net/th|ts\d\.mm\.bing\.net/th)", re.I)

# Structured tile: murl (full image) + t (title) from each result block
_TILE_RE = re.compile(
    r"&quot;murl&quot;:&quot;(https?://[^&]+?)&quot;"
    r".*?"
    r"&quot;t&quot;:&quot;((?:\\.|[^&])*)?&quot;",
    re.DOTALL,
)


def _parse_img_args(raw: str) -> Tuple[int, str]:
    """Parse optional leading count and search query from command text."""
    text = (raw or "").strip()
    if not text:
        return 3, ""
    m = re.match(r"^(\d{1,2})\s+(.+)$", text)
    if m:
        return max(1, min(int(m.group(1)), 10)), m.group(2).strip()
    return 3, text


def _decode_bing_text(value: str) -> str:
    if not value:
        return ""
    return html.unescape(value.replace("\\'", "'").replace('\\"', '"'))


def _normalize_image_url(url: str) -> str:
    url = _decode_bing_text(url.strip())
    url = unquote(url)
    return url.replace("&amp;", "&")


def _relevance_score(query: str, title: str) -> int:
    """Higher score = more likely relevant to the search query."""
    q_terms = {w for w in re.findall(r"[a-z0-9]+", query.lower()) if len(w) > 1}
    if not q_terms:
        return 0
    title_l = title.lower()
    title_terms = set(re.findall(r"[a-z0-9]+", title_l))
    overlap = len(q_terms & title_terms)
    # Bonus when full query phrase appears in title
    phrase_bonus = 2 if query.lower() in title_l else 0
    return overlap * 3 + phrase_bonus


def _extract_bing_tiles(page_html: str) -> List[Tuple[str, str, int]]:
    """Return [(url, title, score), ...] from Bing image result tiles."""
    seen = set()
    ranked: List[Tuple[str, str, int]] = []

    for murl_raw, title_raw in _TILE_RE.findall(page_html):
        url = _normalize_image_url(murl_raw)
        title = _decode_bing_text(title_raw)

        if not url.startswith("http"):
            continue
        if _THUMB_HOST_RE.search(url):
            continue
        if url in seen:
            continue
        seen.add(url)
        ranked.append((url, title, 0))

    return ranked


def _rank_tiles(query: str, tiles: List[Tuple[str, str, int]]) -> List[str]:
    """Sort tiles by title/query relevance and return image URLs."""
    q = query.strip()
    scored = [(_relevance_score(q, title), url) for url, title, _ in tiles]
    scored.sort(key=lambda x: x[0], reverse=True)

    urls = []
    seen = set()
    for _score, url in scored:
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


async def bing_image_search(query: str, limit: int = 3) -> list:
    """Search Bing Images and return up to `limit` relevant image URLs."""
    query = query.strip()
    if not query:
        return []

    fetch_count = min(max(limit * 4, 20), 35)
    params = {
        "q": query,
        "first": 0,
        "count": fetch_count,
        "adlt": "moderate",
        # Prefer actual photos over clipart/icons for better accuracy
        "qft": "+filterui:photo-photo",
    }

    async with httpx.AsyncClient(
        headers=BING_HEADERS, follow_redirects=True, timeout=20
    ) as client:
        r = await client.get("https://www.bing.com/images/async", params=params)
        r.raise_for_status()
        page_html = r.text

    tiles = _extract_bing_tiles(page_html)
    urls = _rank_tiles(query, tiles)

    # Fallback: legacy regex if tile parser finds nothing (Bing markup change)
    if not urls:
        legacy = re.findall(
            r"&quot;murl&quot;:&quot;(https?://[^&]+?)&quot;", page_html
        )
        for raw in legacy:
            url = _normalize_image_url(raw)
            if url.startswith("http") and not _THUMB_HOST_RE.search(url):
                if url not in urls:
                    urls.append(url)

    return urls[:limit]


async def download_images(urls: list) -> list:
    """Download image URLs to temp files, return list of file paths."""
    paths = []
    async with httpx.AsyncClient(
        headers={**BING_HEADERS, "Referer": "https://www.bing.com/"},
        follow_redirects=True,
        timeout=25,
    ) as client:
        for url in urls:
            try:
                r = await client.get(url)
                if r.status_code != 200:
                    continue
                ct = (r.headers.get("content-type") or "").lower()
                if ct and not ct.startswith("image/") and "octet-stream" not in ct:
                    continue
                if len(r.content) < 1000:
                    continue
                ext = (
                    ".png"
                    if "png" in ct
                    else ".gif"
                    if "gif" in ct
                    else ".webp"
                    if "webp" in ct
                    else ".jpg"
                )
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                tmp.write(r.content)
                tmp.close()
                paths.append(tmp.name)
            except Exception:
                continue
    return paths


@catub.cat_cmd(
    pattern=r"img(?: |$)([\s\S]*)",
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
    raw = str(event.pattern_match.group(1) or "")

    if event.is_reply and not raw.strip():
        reply_msg = await event.get_reply_message()
        query = str(reply_msg.message or "").strip()
        lim = 3
    else:
        lim, query = _parse_img_args(raw)

    if not query:
        return await edit_or_reply(
            event, "Reply to a message or pass a query to search!"
        )

    cat = await edit_or_reply(event, "`Searching images...`")

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

    gifs = []
    images = []

    for p in paths:
        if p.lower().endswith(".gif"):
            gifs.append(p)
        else:
            images.append(p)

    try:
        for gif in gifs:
            try:
                await event.client.send_file(event.chat_id, gif, reply_to=reply_to_id)
            except (MediaEmptyError, MediaInvalidError):
                pass

        if images:
            try:
                await event.client.send_file(
                    event.chat_id, images, reply_to=reply_to_id
                )
            except MediaInvalidError:
                for img in images:
                    try:
                        await event.client.send_file(
                            event.chat_id, img, reply_to=reply_to_id
                        )
                    except (MediaEmptyError, MediaInvalidError):
                        pass
            except MediaEmptyError:
                for img in images:
                    with contextlib.suppress(MediaEmptyError, MediaInvalidError):
                        await event.client.send_file(
                            event.chat_id, img, reply_to=reply_to_id
                        )
    finally:
        for p in paths:
            with contextlib.suppress(Exception):
                os.unlink(p)

    await cat.delete()
