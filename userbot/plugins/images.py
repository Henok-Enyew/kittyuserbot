# Image search — .img (Pexels/Unsplash) + .dimg (DuckDuckGo)

import contextlib
import os
import re
import tempfile
from io import BytesIO
from typing import List, Tuple

import httpx
from PIL import Image
from telethon.errors.rpcerrorlist import MediaEmptyError, MediaInvalidError

from userbot import catub
from userbot.Config import Config
from userbot.core import pool

from ..core.logger import logging
from ..core.managers import edit_or_reply
from ..helpers.utils import reply_id

plugin_category = "misc"
LOGS = logging.getLogger(__name__)

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
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


def _dedupe_urls(urls: List[str], limit: int) -> List[str]:
    out: List[str] = []
    seen = set()
    for url in urls:
        if not url or not url.startswith("http"):
            continue
        if url in seen:
            continue
        seen.add(url)
        out.append(url)
        if len(out) >= limit:
            break
    return out


async def pexels_search(query: str, limit: int = 3) -> List[str]:
    key = getattr(Config, "PEXELS_API_KEY", None)
    if not key:
        return []
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        r = await client.get(
            "https://api.pexels.com/v1/search",
            params={"query": query, "per_page": min(limit, 15), "page": 1},
            headers={"Authorization": key},
        )
        if r.status_code != 200:
            LOGS.warning(f"Pexels search HTTP {r.status_code}: {r.text[:200]}")
            return []
        photos = (r.json() or {}).get("photos") or []
        urls = []
        for p in photos:
            src = p.get("src") or {}
            url = src.get("large") or src.get("large2x") or src.get("medium")
            if url:
                urls.append(url)
        return _dedupe_urls(urls, limit)


async def unsplash_search(query: str, limit: int = 3) -> List[str]:
    key = getattr(Config, "UNSPLASH_ACCESS_KEY", None)
    if not key:
        return []
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        r = await client.get(
            "https://api.unsplash.com/search/photos",
            params={"query": query, "per_page": min(limit, 15), "page": 1},
            headers={"Authorization": f"Client-ID {key}"},
        )
        if r.status_code != 200:
            LOGS.warning(f"Unsplash search HTTP {r.status_code}: {r.text[:200]}")
            return []
        results = (r.json() or {}).get("results") or []
        urls = []
        for item in results:
            u = (item.get("urls") or {}).get("regular") or (item.get("urls") or {}).get(
                "small"
            )
            if u:
                urls.append(u)
            # Unsplash guideline: ping download_location when downloading
            dl = (item.get("links") or {}).get("download_location")
            if dl:
                with contextlib.suppress(Exception):
                    await client.get(
                        dl, headers={"Authorization": f"Client-ID {key}"}
                    )
        return _dedupe_urls(urls, limit)


async def stock_image_search(query: str, limit: int = 3) -> List[str]:
    """Pexels primary, Unsplash fills remaining slots."""
    urls = await pexels_search(query, limit)
    if len(urls) < limit:
        extra = await unsplash_search(query, limit - len(urls) + 2)
        for u in extra:
            if u not in urls:
                urls.append(u)
            if len(urls) >= limit:
                break
    return urls[:limit]


@pool.run_in_thread
def ddg_image_search(query: str, limit: int = 3) -> List[str]:
    """DuckDuckGo Images (runs in thread pool)."""
    try:
        from duckduckgo_search import DDGS
    except ImportError as e:
        raise RuntimeError(
            "duckduckgo-search is not installed. Redeploy / pip install it."
        ) from e

    # Over-fetch; some URLs fail download
    want = max(limit * 2, limit + 3)
    ddgs = DDGS()
    results = ddgs.images(
        query,
        max_results=want,
        safesearch="moderate",
    )
    urls = [r.get("image") for r in (results or []) if r.get("image")]
    return _dedupe_urls(urls, want)


async def urls_to_jpeg_files(urls: List[str], limit: int) -> List[str]:
    """Download URLs and re-encode as JPEG so Telegram sends photos with captions."""
    paths: List[str] = []
    async with httpx.AsyncClient(
        headers={"User-Agent": _UA},
        follow_redirects=True,
        timeout=25,
    ) as client:
        for url in urls:
            if len(paths) >= limit:
                break
            try:
                r = await client.get(url)
                if r.status_code != 200 or len(r.content) < 1000:
                    continue
                ct = (r.headers.get("content-type") or "").lower()
                if ct and not ct.startswith("image/") and "octet-stream" not in ct:
                    continue
                img = Image.open(BytesIO(r.content)).convert("RGB")
                img.thumbnail(
                    (1280, 1280), getattr(Image, "Resampling", Image).LANCZOS
                )
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                img.save(tmp.name, format="JPEG", quality=85, optimize=True)
                tmp.close()
                paths.append(tmp.name)
            except Exception as e:
                LOGS.debug(f"img download skip: {e}")
                continue
    return paths


async def send_photo_album(client, chat_id, paths: List[str], reply_to=None) -> int:
    """Send JPEGs as photos; return how many were sent."""
    if not paths:
        return 0
    sent = 0
    try:
        await client.send_file(
            chat_id,
            paths if len(paths) > 1 else paths[0],
            reply_to=reply_to,
            force_document=False,
            allow_cache=False,
        )
        return len(paths)
    except (MediaInvalidError, MediaEmptyError, Exception) as e:
        LOGS.debug(f"album send failed, falling back one-by-one: {e}")

    for path in paths:
        try:
            await client.send_file(
                chat_id,
                path,
                reply_to=reply_to,
                force_document=False,
                allow_cache=False,
            )
            sent += 1
        except (MediaEmptyError, MediaInvalidError, Exception):
            continue
    return sent


def _cleanup(paths: List[str]) -> None:
    for p in paths:
        with contextlib.suppress(Exception):
            os.unlink(p)


async def _run_image_cmd(event, *, web: bool):
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

    label = "DuckDuckGo" if web else "Pexels/Unsplash"
    cat = await edit_or_reply(event, f"`Searching {label} for '{query}'...`")

    try:
        if web:
            urls = await ddg_image_search(query, lim)
        else:
            has_key = bool(
                getattr(Config, "PEXELS_API_KEY", None)
                or getattr(Config, "UNSPLASH_ACCESS_KEY", None)
            )
            if not has_key:
                return await cat.edit(
                    "**No stock API key set.**\n\n"
                    "Add `PEXELS_API_KEY` (free: https://www.pexels.com/api/) "
                    "or use `.dimg` for DuckDuckGo web search."
                )
            urls = await stock_image_search(query, lim)
    except Exception as e:
        LOGS.error(f"image search failed: {e}")
        tip = (
            " DuckDuckGo may be blocked from this host — try `.img`."
            if web
            else " Or try `.dimg` for web search."
        )
        return await cat.edit(f"**Search failed:** `{e}`{tip}")

    if not urls:
        tip = (
            " Try `.img` for stock photos."
            if web
            else " Set `PEXELS_API_KEY` or try `.dimg`."
        )
        return await cat.edit(f"No images found for that query.{tip}")

    await cat.edit(f"`Downloading {min(len(urls), lim)} images...`")
    paths = await urls_to_jpeg_files(urls, lim)

    if not paths:
        return await cat.edit(
            "Found URLs but failed to download any images. Try again or another query."
        )

    await cat.edit(f"`Sending {len(paths)}/{lim}...`")
    try:
        sent = await send_photo_album(
            event.client, event.chat_id, paths, reply_to=reply_to_id
        )
    finally:
        _cleanup(paths)

    if sent == 0:
        return await cat.edit("Downloaded images but Telegram refused to send them.")

    await cat.delete()


@catub.cat_cmd(
    pattern=r"img(?: |$)([\s\S]*)",
    command=("img", plugin_category),
    info={
        "header": "Stock photo search (Pexels / Unsplash)",
        "description": (
            "Searches curated stock photos via Pexels (primary) and Unsplash (optional fill). "
            "Sends 1–10 JPEG photos (default 3). Needs PEXELS_API_KEY. "
            "For web/meme search use .dimg."
        ),
        "usage": ["{tr}img <1-10> <query>", "{tr}img <query>"],
        "examples": [
            "{tr}img cat",
            "{tr}img 10 cat",
            "{tr}img 5 ethiopian coffee",
        ],
    },
)
async def img_stock(event):
    "Stock photos via Pexels/Unsplash."
    await _run_image_cmd(event, web=False)


@catub.cat_cmd(
    pattern=r"dimg(?: |$)([\s\S]*)",
    command=("dimg", plugin_category),
    info={
        "header": "Web image search (DuckDuckGo)",
        "description": (
            "Searches the web via DuckDuckGo Images (no API key). "
            "Sends 1–10 JPEG photos (default 3). Good for memes / specific people. "
            "For polished stock photos use .img."
        ),
        "usage": ["{tr}dimg <1-10> <query>", "{tr}dimg <query>"],
        "examples": [
            "{tr}dimg cat meme",
            "{tr}dimg 8 ethiopian models",
            "{tr}dimg 5 never gonna give you up",
        ],
    },
)
async def img_ddg(event):
    "Web images via DuckDuckGo."
    await _run_image_cmd(event, web=True)
