# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~# CatUserBot #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
# Copyright (C) 2020-2023 by TgCatUB@Github.

# This file is part of: https://github.com/TgCatUB/catuserbot
# and is released under the "GNU v3.0 License Agreement".

# Please see: https://github.com/TgCatUB/catuserbot/blob/master/LICENSE
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

import os
import re
import urllib.request
from collections import defaultdict

import requests
import ujson
import yt_dlp
from telethon import Button
from yt_dlp.utils import DownloadError, ExtractorError, GeoRestrictedError

from ...Config import Config
from ...core import pool
from ...core.logger import logging
from ..aiohttp_helper import AioHttp
from ..progress import humanbytes
from .functions import sublists

LOGS = logging.getLogger(__name__)
BASE_YT_URL = "https://www.youtube.com/watch?v="
YOUTUBE_REGEX = re.compile(
    r"(?:youtube\.com|youtu\.be)/(?:[\w-]+\?v=|embed/|v/|shorts/)?([\w-]{11})"
)
PATH = "./userbot/cache/ytsearch.json"

_YT_EXTRACTOR_ARGS = '--extractor-args "youtube:player_client=android,mweb,web"'

song_dl = (
    "yt-dlp --force-ipv4 --retries 3 --fragment-retries 3 "
    f"{_YT_EXTRACTOR_ARGS} "
    "--write-thumbnail --add-metadata --embed-thumbnail "
    "-o './temp/%(title)s.%(ext)s' --extract-audio --audio-format mp3 "
    "--audio-quality {QUALITY} {video_link}"
)

thumb_dl = (
    "yt-dlp --force-ipv4 "
    f"{_YT_EXTRACTOR_ARGS} "
    "-o './temp/%(title)s.%(ext)s' --write-thumbnail --skip-download {video_link}"
)
video_dl = (
    "yt-dlp --force-ipv4 --retries 3 "
    f"{_YT_EXTRACTOR_ARGS} "
    "--write-thumbnail --add-metadata --embed-thumbnail "
    "-o './temp/%(title)s.%(ext)s' -f 'best[height<=480]/best' {video_link}"
)
name_dl = (
    "yt-dlp --force-ipv4 "
    f"{_YT_EXTRACTOR_ARGS} "
    "--get-filename -o './temp/%(title)s.%(ext)s' {video_link}"
)

# Public search APIs (no key) — used when yt-dlp ytsearch SSL fails on HF
PIPED_INSTANCES = [
    "https://api.piped.private.coffee",
    "https://api.piped.yt",
    "https://pipedapi.kavin.rocks",
    "https://pipedapi-libre.kavin.rocks",
    "https://pipedapi.darkness.services",
    "https://pipedapi.leptons.xyz",
]
INVIDIOUS_INSTANCES = [
    "https://inv.nadeko.net",
    "https://invidious.nerdvpn.de",
    "https://yewtu.be",
    "https://invidious.fdn.fr",
    "https://vid.puffyan.us",
]


def _format_duration(seconds):
    if seconds in (None, 0):
        return "N/A"
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return "N/A"
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def _format_view_count_short(count):
    if not count:
        return "N/A"
    try:
        count = int(count)
    except (TypeError, ValueError):
        return "N/A"
    if count >= 1_000_000_000:
        val = count / 1_000_000_000
        return f"{val:.1f}B".replace(".0B", "B")
    if count >= 1_000_000:
        val = count / 1_000_000
        return f"{val:.1f}M".replace(".0M", "M")
    if count >= 1_000:
        val = count / 1_000
        return f"{val:.1f}K".replace(".0K", "K")
    return str(count)


def _format_upload_date(upload_date):
    if not upload_date or len(str(upload_date)) != 8:
        return "Unknown"
    s = str(upload_date)
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}"


def _normalize_ytdlp_entry(entry):
    video_id = entry.get("id")
    title = entry.get("title") or "Unknown"
    link = (
        entry.get("url")
        or entry.get("webpage_url")
        or (f"{BASE_YT_URL}{video_id}" if video_id else None)
    )
    duration = _format_duration(entry.get("duration"))
    description = (entry.get("description") or "").strip()
    description_snippet = [{"text": description}] if description else None
    channel_url = entry.get("channel_url")
    channel_id = entry.get("channel_id")
    if not channel_url and channel_id:
        channel_url = f"https://www.youtube.com/channel/{channel_id}"
    channel_name = entry.get("uploader") or entry.get("channel") or "Unknown"

    return {
        "id": video_id,
        "title": title,
        "link": link,
        "duration": duration,
        "descriptionSnippet": description_snippet,
        "viewCount": {"short": _format_view_count_short(entry.get("view_count"))},
        "accessibility": {"duration": duration, "title": title},
        "publishedTime": _format_upload_date(entry.get("upload_date")),
        "channel": {"link": channel_url, "name": channel_name} if channel_url else None,
    }


def _result_from_fields(
    video_id,
    title,
    duration_seconds=None,
    view_count=None,
    description=None,
    channel_name=None,
    channel_url=None,
    published=None,
):
    if not video_id:
        return None
    duration = _format_duration(duration_seconds)
    description = (description or "").strip()
    description_snippet = [{"text": description}] if description else None
    return {
        "id": video_id,
        "title": title or "Unknown",
        "link": f"{BASE_YT_URL}{video_id}",
        "duration": duration,
        "descriptionSnippet": description_snippet,
        "viewCount": {"short": _format_view_count_short(view_count)},
        "accessibility": {"duration": duration, "title": title or "Unknown"},
        "publishedTime": published or "Unknown",
        "channel": (
            {"link": channel_url, "name": channel_name or "Unknown"}
            if channel_url or channel_name
            else None
        ),
    }


def _search_ytdlp(query, limit):
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": "in_playlist",
        "force_ipv4": True,
        "retries": 2,
        "socket_timeout": 20,
        "nocheckcertificate": True,
        "extractor_args": {
            "youtube": {"player_client": ["android", "mweb", "web"]}
        },
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"ytsearch{int(limit)}:{query}", download=False)
    entries = info.get("entries") if info else None
    if not entries:
        return []
    results = []
    for entry in entries:
        if not entry:
            continue
        normalized = _normalize_ytdlp_entry(entry)
        if normalized.get("id"):
            results.append(normalized)
    return results


def _search_piped(query, limit):
    results = []
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    for base in PIPED_INSTANCES:
        try:
            resp = requests.get(
                f"{base}/search",
                params={"q": query, "filter": "videos"},
                timeout=12,
                headers=headers,
            )
            if not resp.ok:
                continue
            items = resp.json().get("items") or []
            for item in items:
                itype = item.get("type")
                if itype and itype not in ("stream", "video"):
                    continue
                raw_url = item.get("url") or item.get("id") or ""
                video_id = None
                if "/watch?v=" in str(raw_url):
                    video_id = str(raw_url).split("/watch?v=")[-1].split("&")[0]
                elif "youtu" in str(raw_url):
                    m = YOUTUBE_REGEX.search(str(raw_url))
                    video_id = m.group(1) if m else None
                elif re.fullmatch(r"[\w-]{11}", str(raw_url).strip("/")):
                    video_id = str(raw_url).strip("/")
                if not video_id:
                    continue
                up = item.get("uploaderUrl") or ""
                channel_url = None
                if isinstance(up, str) and up:
                    channel_url = up if up.startswith("http") else f"https://youtube.com{up}"
                row = _result_from_fields(
                    video_id=video_id,
                    title=item.get("title"),
                    duration_seconds=item.get("duration"),
                    view_count=item.get("views"),
                    description=item.get("shortDescription") or item.get("description"),
                    channel_name=item.get("uploader"),
                    channel_url=channel_url,
                    published=item.get("uploadedDate") or "Unknown",
                )
                if row:
                    results.append(row)
                if len(results) >= limit:
                    return results
            if results:
                return results
        except Exception as e:
            LOGS.debug(f"Piped search via {base} failed: {e}")
            continue
    return results


def _search_invidious(query, limit):
    results = []
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    for base in INVIDIOUS_INSTANCES:
        try:
            resp = requests.get(
                f"{base}/api/v1/search",
                params={"q": query, "type": "video"},
                timeout=12,
                headers=headers,
            )
            if not resp.ok:
                continue
            payload = resp.json()
            items = payload if isinstance(payload, list) else []
            for item in items:
                if item.get("type") and item.get("type") != "video":
                    continue
                video_id = item.get("videoId")
                author_id = item.get("authorId")
                channel_url = (
                    f"https://www.youtube.com/channel/{author_id}" if author_id else None
                )
                row = _result_from_fields(
                    video_id=video_id,
                    title=item.get("title"),
                    duration_seconds=item.get("lengthSeconds"),
                    view_count=item.get("viewCount"),
                    description=item.get("description"),
                    channel_name=item.get("author"),
                    channel_url=channel_url,
                    published=item.get("publishedText") or "Unknown",
                )
                if row:
                    results.append(row)
                if len(results) >= limit:
                    return results
            if results:
                return results
        except Exception as e:
            LOGS.debug(f"Invidious search via {base} failed: {e}")
            continue
    return results


def _search_youtube_html(query, limit):
    """Last-resort scrape of YouTube results page for video IDs."""
    try:
        from urllib.parse import quote_plus

        resp = requests.get(
            f"https://www.youtube.com/results?search_query={quote_plus(query)}",
            timeout=15,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        if not resp.ok:
            return []
        # Prefer structured ytInitialData videoIds, fall back to watch?v=
        ids = re.findall(r'"videoId":"([\w-]{11})"', resp.text)
        if not ids:
            ids = re.findall(r"watch\?v=([\w-]{11})", resp.text)
        seen = set()
        results = []
        for vid in ids:
            if vid in seen:
                continue
            seen.add(vid)
            row = _result_from_fields(video_id=vid, title=f"YouTube video {vid}")
            if row:
                # Try to pick nearby title from JSON blob
                title_m = re.search(
                    rf'"videoId":"{re.escape(vid)}".*?"title":\{{"runs":\[\{{"text":"(.*?)"\}}',
                    resp.text,
                )
                if not title_m:
                    title_m = re.search(
                        rf'"title":\{{"runs":\[\{{"text":"(.*?)"\}}\].*?"videoId":"{re.escape(vid)}"',
                        resp.text,
                    )
                if title_m:
                    row["title"] = (
                        title_m.group(1)
                        .encode("utf-8")
                        .decode("unicode_escape", errors="ignore")
                    )
                    row["accessibility"]["title"] = row["title"]
                results.append(row)
            if len(results) >= limit:
                break
        return results
    except Exception as e:
        LOGS.debug(f"YouTube HTML search failed: {e}")
        return []


def _videos_search_sync(query, limit=15):
    """Search YouTube: yt-dlp → Piped → Invidious → HTML scrape."""
    query = (query or "").strip()
    if not query:
        return {"result": []}
    limit = max(1, min(int(limit), 25))

    # 1) yt-dlp
    try:
        results = _search_ytdlp(query, limit)
        if results:
            return {"result": results[:limit]}
    except Exception as e:
        LOGS.warning(f"yt-dlp search failed for '{query}': {e}")

    # 2) Piped
    try:
        results = _search_piped(query, limit)
        if results:
            LOGS.info(f"YouTube search via Piped for '{query}' ({len(results)} hits)")
            return {"result": results[:limit]}
    except Exception as e:
        LOGS.warning(f"Piped search failed for '{query}': {e}")

    # 3) Invidious
    try:
        results = _search_invidious(query, limit)
        if results:
            LOGS.info(f"YouTube search via Invidious for '{query}' ({len(results)} hits)")
            return {"result": results[:limit]}
    except Exception as e:
        LOGS.warning(f"Invidious search failed for '{query}': {e}")

    # 4) YouTube HTML scrape
    try:
        results = _search_youtube_html(query, limit)
        if results:
            LOGS.info(f"YouTube search via HTML scrape for '{query}' ({len(results)} hits)")
            return {"result": results[:limit]}
    except Exception as e:
        LOGS.warning(f"HTML search failed for '{query}': {e}")

    LOGS.error(f"YouTube search exhausted all backends for '{query}'")
    return {"result": []}


@pool.run_in_thread
def videos_search(query, limit=15):
    return _videos_search_sync(query, limit)


async def yt_search(cat):
    """Return the first YouTube watch URL for a search query."""
    query = (cat or "").strip()
    if not query:
        return "Couldnt fetch results"
    try:
        results = (await videos_search(query, limit=1)).get("result") or []
        if not results:
            return "Couldnt fetch results"
        video_id = results[0].get("id")
        if video_id:
            return f"{BASE_YT_URL}{video_id}"
        link = results[0].get("link")
        if link:
            return link
    except Exception as e:
        LOGS.error(f"yt_search failed for '{query}': {e}")
    return "Couldnt fetch results"


async def ytsearch(query, limit):
    result = ""
    items = (await videos_search(query.lower(), limit=limit)).get("result") or []
    if not items:
        return "No results found."
    for v in items:
        textresult = f"[{v['title']}](https://www.youtube.com/watch?v={v['id']})\n"
        try:
            textresult += f"**Description : **`{v['descriptionSnippet'][-1]['text']}`\n"
        except Exception:
            textresult += "**Description : **`None`\n"
        textresult += f"**Duration : **__{v['duration']}__  **Views : **__{v['viewCount']['short']}__\n"
        result += f"☞ {textresult}\n"
    return result


class YT_Search_X:
    def __init__(self):
        if not os.path.exists(PATH):
            with open(PATH, "w") as f_x:
                ujson.dump({}, f_x)
        with open(PATH) as yt_db:
            self.db = ujson.load(yt_db)

    def store_(self, rnd_id: str, results: dict):
        self.db[rnd_id] = results
        self.save()

    def save(self):
        with open(PATH, "w") as outfile:
            ujson.dump(self.db, outfile, indent=4)


ytsearch_data = YT_Search_X()

"""
async def yt_data(cat):
    params = {"format": "json", "url": cat}
    url = "https://www.youtube.com/oembed"  # https://stackoverflow.com/questions/29069444/returning-the-urls-as-a-list-from-a-youtube-search-query
    query_string = urllib.parse.urlencode(params)
    url = f"{url}?{query_string}"
    with urllib.request.urlopen(url) as response:
        response_text = response.read()
        data = ujson.loads(response_text.decode())
    return data
"""


async def get_ytthumb(videoid: str):
    # Fast path for inline answers — probing every quality times out Telegram.
    if not videoid:
        return "https://i.imgur.com/4LwPLai.png"
    return f"https://i.ytimg.com/vi/{videoid}/hqdefault.jpg"


async def get_ytthumb_best(videoid: str):
    """Probe thumbnail qualities (slower — use outside inline query window)."""
    thumb_quality = [
        "maxresdefault.jpg",
        "hqdefault.jpg",
        "sddefault.jpg",
        "mqdefault.jpg",
        "default.jpg",
    ]
    thumb_link = "https://i.imgur.com/4LwPLai.png"
    for qualiy in thumb_quality:
        link = f"https://i.ytimg.com/vi/{videoid}/{qualiy}"
        if await AioHttp().get_status(link) == 200:
            thumb_link = link
            break
    return thumb_link


def get_yt_video_id(url: str):
    if match := YOUTUBE_REGEX.search(url):
        return match.group(1)


# Based on https://gist.github.com/AgentOak/34d47c65b1d28829bb17c24c04a0096f
def get_choice_by_id(choice_id, media_type: str):
    if choice_id == "mkv":
        # default format selection
        choice_str = "bestvideo+bestaudio/best"
        disp_str = "best(video+audio)"
    elif choice_id == "mp3":
        choice_str = "320"
        disp_str = "320 Kbps"
    elif choice_id == "mp4":
        # Download best Webm / Mp4 format available or any other best if no mp4
        # available
        choice_str = "bestvideo[ext=webm]+251/bestvideo[ext=mp4]+(258/256/140/bestaudio[ext=m4a])/bestvideo[ext=webm]+(250/249)/best"
        disp_str = "best(video+audio)[webm/mp4]"
    else:
        disp_str = str(choice_id)
        choice_str = (
            f"{disp_str}+(258/256/140/bestaudio[ext=m4a])/best"
            if media_type == "v"
            else disp_str
        )

    return choice_str, disp_str


async def result_formatter(results: list):
    output = {}
    for index, r in enumerate(results, start=1):
        v_deo_id = r.get("id")
        if not v_deo_id:
            continue
        thumb = await get_ytthumb(v_deo_id)
        upld = r.get("channel") or {}
        access = r.get("accessibility") or {}
        views = r.get("viewCount") or {}
        title = f'<a href={r.get("link")}><b>{r.get("title")}</b></a>\n'
        out = title
        if r.get("descriptionSnippet"):
            out += f'<code>{"".join(x.get("text") or "" for x in r.get("descriptionSnippet"))}</code>\n\n'
        out += f'<b>❯  Duration:</b> {access.get("duration") or r.get("duration") or "N/A"}\n'
        out += f'<b>❯  Views:</b> {views.get("short") or "N/A"}\n'
        out += f'<b>❯  Upload date:</b> {r.get("publishedTime") or "Unknown"}\n'
        if upld:
            out += "<b>❯  Uploader:</b> "
            out += f'<a href={upld.get("link") or "#"}>{upld.get("name") or "Unknown"}</a>'

        output[index] = dict(
            message=out,
            thumb=thumb,
            video_id=v_deo_id,
            list_view=(
                f'<img src={thumb}><b><a href={r.get("link")}>{index}. '
                f'{access.get("title") or r.get("title")}</a></b><br>'
            ),
        )

    return output


def yt_search_btns(
    data_key: str, page: int, vid: str, total: int, del_back: bool = False
):
    buttons = [
        [
            Button.inline(
                text="⬅️  Back",
                data=f"ytdl_back_{data_key}_{page}",
            ),
            Button.inline(
                text=f"{page} / {total}",
                data=f"ytdl_next_{data_key}_{page}",
            ),
        ],
        [
            Button.inline(
                text="📜  List all",
                data=f"ytdl_listall_{data_key}_{page}",
            ),
            Button.inline(
                text="⬇️  Download",
                data=f"ytdl_download_{vid}_0",
            ),
        ],
    ]
    if del_back:
        buttons[0].pop(0)
    return buttons


def _fast_download_buttons(vid: str):
    """Best-effort buttons without yt-dlp extract (keeps inline answers fast)."""
    return [
        [
            Button.inline("⭐️ BEST - 📹 MKV", data=f"ytdl_download_{vid}_mkv_v"),
            Button.inline(
                "⭐️ BEST - 📹 WebM/MP4",
                data=f"ytdl_download_{vid}_mp4_v",
            ),
        ],
        [Button.inline("⭐️ BEST - 🎵 320Kbps - MP3", data=f"ytdl_download_{vid}_mp3_a")],
    ]


@pool.run_in_thread
def download_button(vid: str, body: bool = False):  # sourcery no-metrics
    # sourcery skip: low-code-quality
    try:
        vid_data = yt_dlp.YoutubeDL(
            {
                "no-playlist": True,
                "quiet": True,
                "no_warnings": True,
                "socket_timeout": 15,
                "retries": 1,
                "extractor_args": {
                    "youtube": {"player_client": ["android", "mweb"]}
                },
            }
        ).extract_info(BASE_YT_URL + vid, download=False)
    except Exception:
        vid_data = {"formats": [], "webpage_url": BASE_YT_URL + vid, "title": vid}
    buttons = [
        [
            Button.inline("⭐️ BEST - 📹 MKV", data=f"ytdl_download_{vid}_mkv_v"),
            Button.inline(
                "⭐️ BEST - 📹 WebM/MP4",
                data=f"ytdl_download_{vid}_mp4_v",
            ),
        ]
    ]
    # ------------------------------------------------ #
    qual_dict = defaultdict(lambda: defaultdict(int))
    qual_list = ["144p", "240p", "360p", "480p", "720p", "1080p", "1440p"]
    audio_dict = {}
    # ------------------------------------------------ #
    for video in vid_data.get("formats") or []:
        if video.get("filesize"):
            fr_note = video.get("format_note")
            fr_id = int(video.get("format_id"))
            fr_size = video.get("filesize")
            if video.get("ext") == "mp4":
                for frmt_ in qual_list:
                    if fr_note in (frmt_, f"{frmt_}60"):
                        qual_dict[frmt_][fr_id] = fr_size
            if video.get("acodec") != "none":
                bitrrate = int(video.get("abr", 0))
                if bitrrate != 0:
                    audio_dict[
                        bitrrate
                    ] = f"🎵 {bitrrate}Kbps ({humanbytes(fr_size) or 'N/A'})"

    video_btns = []
    for frmt in qual_list:
        frmt_dict = qual_dict[frmt]
        if len(frmt_dict) != 0:
            frmt_id = sorted(list(frmt_dict))[-1]
            frmt_size = humanbytes(frmt_dict.get(frmt_id)) or "N/A"
            video_btns.append(
                Button.inline(
                    f"📹 {frmt} ({frmt_size})",
                    data=f"ytdl_download_{vid}_{frmt_id}_v",
                )
            )
    buttons += sublists(video_btns, width=2)
    buttons += [
        [Button.inline("⭐️ BEST - 🎵 320Kbps - MP3", data=f"ytdl_download_{vid}_mp3_a")]
    ]
    buttons += sublists(
        [
            Button.inline(audio_dict.get(key_), data=f"ytdl_download_{vid}_{key_}_a")
            for key_ in sorted(audio_dict.keys())
        ],
        width=2,
    )
    if body:
        title = vid_data.get("title") or vid
        url = vid_data.get("webpage_url") or (BASE_YT_URL + vid)
        vid_body = f"<a href={url}><b>[{title}]</b></a>"
        return vid_body, buttons
    return buttons


@pool.run_in_thread
def _tubeDl(url: str, starttime, uid: str):
    ydl_opts = {
        "addmetadata": True,
        "geo_bypass": True,
        "nocheckcertificate": True,
        "force_ipv4": True,
        "retries": 3,
        "outtmpl": os.path.join(
            Config.TEMP_DIR, str(starttime), "%(title)s-%(format)s.%(ext)s"
        ),
        "format": uid,
        "writethumbnail": True,
        "prefer_ffmpeg": True,
        "extractor_args": {
            "youtube": {"player_client": ["android", "mweb", "web"]}
        },
        "postprocessors": [
            {"key": "FFmpegMetadata"}
        ],
        "quiet": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            x = ydl.download([url])
    except DownloadError as e:
        LOGS.error(e)
    except GeoRestrictedError:
        LOGS.error(
            "ERROR: The uploader has not made this video available in your country"
        )
    else:
        return x


@pool.run_in_thread
def _mp3Dl(url: str, starttime, uid: str):
    _opts = {
        "outtmpl": os.path.join(Config.TEMP_DIR, str(starttime), "%(title)s.%(ext)s"),
        "writethumbnail": True,
        "prefer_ffmpeg": True,
        "format": "bestaudio/best",
        "geo_bypass": True,
        "nocheckcertificate": True,
        "force_ipv4": True,
        "retries": 3,
        "extractor_args": {
            "youtube": {"player_client": ["android", "mweb", "web"]}
        },
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": uid,
            },
            {"key": "FFmpegMetadata"},
        ],
        "quiet": True,
    }
    try:
        with yt_dlp.YoutubeDL(_opts) as ytdl:
            dloader = ytdl.download([url])
    except Exception as y_e:
        LOGS.exception(y_e)
        return y_e
    else:
        return dloader