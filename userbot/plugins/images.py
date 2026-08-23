# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~# CatUserBot #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
# Copyright (C) 2020-2023 by TgCatUB@Github.

# This file is part of: https://github.com/TgCatUB/catuserbot
# and is released under the "GNU v3.0 License Agreement".

# Please see: https://github.com/TgCatUB/catuserbot/blob/master/LICENSE
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

import contextlib
import html
import json
import os
import re
import tempfile
from typing import Dict, List, Tuple
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

_THUMB_HOST_RE = re.compile(r"(\.bing\.net/th|ts\d+\.mm\.bing\.net/th)", re.I)

# When user means people/models, penalize landscape/architecture false positives
_LANDSCAPE_TERMS = {
    "mountain", "mountains", "landscape", "scenery", "simien", "lalibela",
    "terrain", "valley", "peak", "summit", "volcano", "waterfall", "nature",
    "national park", "highlands", "plateau", "church", "monastery", "castle",
    "map", "satellite", "aerial view", "panorama", "wildlife", "elephant",
}

_PERSON_TERMS = {
    "model", "models", "portrait", "woman", "women", "man", "men", "girl",
    "boy", "face", "person", "people", "beauty", "fashion", "runway",
    "actress", "actor", "selfie", "headshot",
}

_AMBIGUOUS_MODEL_RE = re.compile(
    r"\bmodels?\b", re.I
)
_MODEL_CONTEXT_RE = re.compile(
    r"\b(fashion|portrait|runway|3d|car|architect|scale|role\s+model|"
    r"ai\s+model|llm|anatomy|scientific|mathematical|data\s+model)\b",
    re.I,
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
    cleaned = html.unescape(value.replace("\\'", "'").replace('\\"', '"'))
    # Bing highlights query terms with private-use chars — strip them
    return re.sub(r"[\ue000-\uf8ff]", "", cleaned).strip()


def _normalize_image_url(url: str) -> str:
    url = _decode_bing_text(url.strip())
    url = unquote(url)
    return url.replace("&amp;", "&")


def _refine_query(query: str) -> str:
    """
    Reduce ambiguous Bing results.
    'ethiopian models' often returns landscapes/3D/architecture — bias toward portraits.
    """
    q = query.strip()
    if not q:
        return q
    if _AMBIGUOUS_MODEL_RE.search(q) and not _MODEL_CONTEXT_RE.search(q):
        return f"{q} portrait fashion"
    return q


def _query_wants_people(query: str) -> bool:
    lower = query.lower()
    if _AMBIGUOUS_MODEL_RE.search(lower):
        return True
    return any(term in lower for term in ("portrait", "woman", "man", "face", "selfie", "beauty"))


def _relevance_score(query: str, title: str, desc: str = "", page_url: str = "") -> int:
    """Score how well a result matches the query."""
    blob = " ".join([title, desc, page_url]).lower()
    q_lower = query.lower()

    q_terms = {w for w in re.findall(r"[a-z0-9]+", q_lower) if len(w) > 1}
    if not q_terms:
        return 0

    blob_terms = set(re.findall(r"[a-z0-9]+", blob))
    overlap = len(q_terms & blob_terms)
    score = overlap * 4

    # Phrase / partial phrase bonuses
    if q_lower in blob:
        score += 8
    else:
        for term in q_terms:
            if len(term) >= 4 and term in blob:
                score += 1

    # Person-query boosts & landscape penalties
    if _query_wants_people(query):
        if any(t in blob for t in _PERSON_TERMS):
            score += 6
        if any(t in blob for t in _LANDSCAPE_TERMS):
            score -= 12

    return score


def _extract_bing_tiles(page_html: str) -> List[Dict[str, str]]:
    """
    Parse Bing image tiles from m="..." JSON attributes.
    Keeps murl + title + desc paired correctly (unlike loose regex).
    """
    results: List[Dict[str, str]] = []
    seen_urls = set()

    for match in re.finditer(r'\sm="\{&quot;', page_html):
        start = match.start() + 4  # after m="
        end = page_html.find('}"', start)
        if end == -1:
            continue
        raw_json = page_html[start : end + 1]
        try:
            obj = json.loads(html.unescape(raw_json.replace("&quot;", '"')))
        except json.JSONDecodeError:
            continue

        url = _normalize_image_url(obj.get("murl") or "")
        if not url.startswith("http"):
            continue
        if _THUMB_HOST_RE.search(url):
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)

        results.append(
            {
                "url": url,
                "title": _decode_bing_text(obj.get("t") or ""),
                "desc": _decode_bing_text(obj.get("desc") or ""),
                "page": _decode_bing_text(obj.get("purl") or ""),
            }
        )

    return results


def _rank_tiles(query: str, tiles: List[Dict[str, str]]) -> List[str]:
    """Sort tiles by relevance; drop obvious junk when better matches exist."""
    scored = []
    for tile in tiles:
        s = _relevance_score(
            query,
            tile.get("title", ""),
            tile.get("desc", ""),
            tile.get("page", ""),
        )
        scored.append((s, tile["url"]))

    scored.sort(key=lambda x: x[0], reverse=True)

    if scored and scored[0][0] > 0:
        # Drop clearly irrelevant results when we have good matches
        top = scored[0][0]
        min_keep = max(0, top - 8)
        scored = [(s, u) for s, u in scored if s >= min_keep]

    urls: List[str] = []
    seen = set()
    for _score, url in scored:
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


async def _fetch_bing_html(client: httpx.AsyncClient, query: str, *, face_bias: bool = False) -> str:
    params = {
        "q": query,
        "first": 0,
        "count": 35,
        "adlt": "moderate",
        "setlang": "en",
        "mkt": "en-US",
        "qft": "+filterui:photo-photo",
    }
    if face_bias:
        params["qft"] = "+filterui:photo-photo+filterui:face-face"

    r = await client.get("https://www.bing.com/images/async", params=params)
    r.raise_for_status()
    return r.text


async def bing_image_search(query: str, limit: int = 3) -> list:
    """Search Bing Images and return up to `limit` relevant image URLs."""
    original_query = query.strip()
    if not original_query:
        return []

    search_query = _refine_query(original_query)
    face_bias = _query_wants_people(original_query)

    async with httpx.AsyncClient(
        headers=BING_HEADERS, follow_redirects=True, timeout=20
    ) as client:
        page_html = await _fetch_bing_html(client, search_query, face_bias=face_bias)
        tiles = _extract_bing_tiles(page_html)
        urls = _rank_tiles(original_query, tiles)

        # Retry without face filter if too few results
        if len(urls) < limit and face_bias:
            page_html = await _fetch_bing_html(client, search_query, face_bias=False)
            tiles = _extract_bing_tiles(page_html)
            urls = _rank_tiles(original_query, tiles)

        # Retry original query without refinement
        if len(urls) < limit and search_query != original_query:
            page_html = await _fetch_bing_html(client, original_query, face_bias=False)
            tiles = _extract_bing_tiles(page_html)
            extra = _rank_tiles(original_query, tiles)
            for url in extra:
                if url not in urls:
                    urls.append(url)

        # Last resort: main search page
        if len(urls) < limit:
            r = await client.get(
                "https://www.bing.com/images/search",
                params={
                    "q": search_query,
                    "form": "HDRSC2",
                    "first": 1,
                    "count": 35,
                    "adlt": "moderate",
                    "qft": "+filterui:photo-photo",
                },
            )
            tiles = _extract_bing_tiles(r.text)
            extra = _rank_tiles(original_query, tiles)
            for url in extra:
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
            "{tr}img ethiopian fashion models",
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
