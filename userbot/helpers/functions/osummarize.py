# Silent cross-chat summarizer helpers for .osum / .osummarize
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from telethon.tl.types import User

from ...Config import Config

MAX_INPUT = 6000

RE_TME_PUBLIC = re.compile(
    r"(https?://(?:www\.)?t\.me/([^/\s?]+)/(\d+)(?:\?([^\s]*))?)",
    re.I,
)
RE_TME_PRIVATE = re.compile(
    r"(https?://(?:www\.)?t\.me/c/(\d+)/(\d+)(?:\?([^\s]*))?)",
    re.I,
)
RE_TG_OPEN = re.compile(
    r"(tg://openmessage\?user_id=(\d+)&message_id=(\d+))",
    re.I,
)
RE_CHAT_AT = re.compile(r"^@([A-Za-z0-9_]{3,})$")
RE_CHAT_URL = re.compile(r"^https?://(?:www\.)?t\.me/([^/\s?]+)\s*$", re.I)


def _max_osum() -> int:
    try:
        return int(
            os.environ.get("OSUM_MAX_MESSAGES")
            or getattr(Config, "OSUM_MAX_MESSAGES", None)
            or 100
        )
    except (TypeError, ValueError):
        return 100


@dataclass
class ParsedMessageLink:
    url: str
    chat_ref: Any  # username str, int peer id, or entity id from private link
    msg_id: int
    thread_id: Optional[int] = None
    is_private_link: bool = False


@dataclass
class OsumQuery:
    mode: str  # count | range | from | to
    count: Optional[int] = None
    chat_ref: Optional[Any] = None
    focus: Optional[str] = None
    start: Optional[ParsedMessageLink] = None
    end: Optional[ParsedMessageLink] = None
    truncated_note: str = ""


def _thread_from_query(qs: Optional[str]) -> Optional[int]:
    if not qs:
        return None
    m = re.search(r"(?:^|&)thread=(\d+)", qs)
    return int(m.group(1)) if m else None


def parse_message_link(url: str) -> Optional[ParsedMessageLink]:
    url = (url or "").strip()
    m = RE_TME_PRIVATE.search(url)
    if m:
        full, cid, mid, qs = m.group(1), m.group(2), int(m.group(3)), m.group(4)
        return ParsedMessageLink(
            url=full,
            chat_ref=private_link_chat_id(cid),
            msg_id=mid,
            thread_id=_thread_from_query(qs),
            is_private_link=True,
        )
    m = RE_TME_PUBLIC.search(url)
    if m:
        full, username, mid, qs = m.group(1), m.group(2), int(m.group(3)), m.group(4)
        if username.lower() == "c":
            return None
        return ParsedMessageLink(
            url=full,
            chat_ref=username,
            msg_id=mid,
            thread_id=_thread_from_query(qs),
            is_private_link=False,
        )
    m = RE_TG_OPEN.search(url)
    if m:
        full, uid, mid = m.group(1), int(m.group(2)), int(m.group(3))
        return ParsedMessageLink(
            url=full,
            chat_ref=uid,
            msg_id=mid,
            is_private_link=False,
        )
    return None


def private_link_chat_id(raw: str) -> int:
    cid = int(raw)
    if cid > 0:
        return int(f"-100{cid}")
    return cid


def _strip_chat_id_for_link(chat_id: int) -> str:
    s = str(chat_id)
    if s.startswith("-100"):
        return s[4:]
    if s.startswith("-"):
        return s[1:]
    return s


def build_message_link(chat: Any, msg_id: int) -> str:
    if isinstance(chat, User):
        return f"tg://openmessage?user_id={chat.id}&message_id={msg_id}"
    username = getattr(chat, "username", None)
    if username:
        return f"https://t.me/{username}/{msg_id}"
    cid = getattr(chat, "id", chat)
    return f"https://t.me/c/{_strip_chat_id_for_link(int(cid))}/{msg_id}"


def _extract_links(text: str) -> List[str]:
    found: List[str] = []
    for pattern in (RE_TME_PRIVATE, RE_TME_PUBLIC, RE_TG_OPEN):
        for m in pattern.finditer(text):
            found.append(m.group(1))
    return found


def _split_chat_and_focus(rest: str) -> Tuple[Optional[str], Optional[str]]:
    rest = (rest or "").strip()
    if not rest:
        return None, None

    links = _extract_links(rest)
    if links:
        chat_part = links[0]
        focus = rest.replace(links[0], "", 1).strip()
        return chat_part, focus or None

    m = RE_CHAT_AT.match(rest.split()[0])
    if m:
        chat = f"@{m.group(1)}"
        focus = rest[len(rest.split()[0]):].strip() or None
        return chat, focus

    first = rest.split()[0]
    if first.lstrip("-").isdigit():
        focus = rest[len(first):].strip() or None
        return first, focus

    m = RE_CHAT_URL.match(first)
    if m:
        chat = f"https://t.me/{m.group(1)}"
        focus = rest[len(first):].strip() or None
        return chat, focus

    return rest, None


def parse_osum_args(raw: Optional[str], reply_msg: Any = None) -> OsumQuery:
    text = (raw or "").strip()
    lower = text.lower()

    if lower.startswith("range "):
        rest = text[6:].strip()
        links = _extract_links(rest)
        if len(links) < 2:
            raise ValueError(
                "Usage: `.osum range <start_link> <end_link> [focus]`"
            )
        focus = rest
        for link in links:
            focus = focus.replace(link, "", 1)
        focus = focus.strip() or None
        start = parse_message_link(links[0])
        end = parse_message_link(links[1])
        if not start or not end:
            raise ValueError("Could not parse one of the message links.")
        return OsumQuery(mode="range", start=start, end=end, focus=focus)

    if lower.startswith("from ") and reply_msg:
        rest = text[5:].strip()
        links = _extract_links(rest)
        if not links:
            raise ValueError(
                "Reply to the **bottom** message and use: "
                "`.osum from <start_link> [focus]`"
            )
        focus = rest.replace(links[0], "", 1).strip() or None
        start = parse_message_link(links[0])
        if not start:
            raise ValueError("Could not parse the start message link.")
        end = ParsedMessageLink(
            url="",
            chat_ref=start.chat_ref,
            msg_id=reply_msg.id,
            thread_id=start.thread_id,
            is_private_link=start.is_private_link,
        )
        return OsumQuery(mode="from", start=start, end=end, focus=focus)

    if lower.startswith("to ") and reply_msg:
        rest = text[3:].strip()
        links = _extract_links(rest)
        if not links:
            raise ValueError(
                "Reply to the **top** message and use: "
                "`.osum to <end_link> [focus]`"
            )
        focus = rest.replace(links[0], "", 1).strip() or None
        end = parse_message_link(links[0])
        if not end:
            raise ValueError("Could not parse the end message link.")
        start = ParsedMessageLink(
            url="",
            chat_ref=end.chat_ref,
            msg_id=reply_msg.id,
            thread_id=end.thread_id,
            is_private_link=end.is_private_link,
        )
        return OsumQuery(mode="to", start=start, end=end, focus=focus)

    m = re.match(r"^(\d+)\s+(.+)$", text)
    if m:
        count = max(1, min(int(m.group(1)), _max_osum()))
        chat_ref, focus = _split_chat_and_focus(m.group(2).strip())
        if not chat_ref:
            raise ValueError(
                "Usage: `.osum <count> @chat [focus]` — e.g. `.osum 100 @codenight job roles`"
            )
        return OsumQuery(
            mode="count",
            count=count,
            chat_ref=chat_ref,
            focus=focus,
        )

    if text:
        raise ValueError(
            "Usage: `.osum <count> @chat [focus]` | "
            "`.osum range <start_link> <end_link> [focus]` | "
            "reply + `.osum from <start_link>` or `.osum to <end_link>`"
        )

    raise ValueError(
        "Usage: `.osum 100 @codenight check for job posts`"
    )


async def resolve_chat(client, chat_ref: Any) -> Any:
    if isinstance(chat_ref, int):
        return await client.get_entity(chat_ref)

    ref = str(chat_ref).strip()
    link = parse_message_link(ref)
    if link:
        return await client.get_entity(link.chat_ref)

    if ref.startswith("@"):
        return await client.get_entity(ref)

    if ref.lstrip("-").isdigit():
        return await client.get_entity(int(ref))

    m = RE_CHAT_URL.match(ref)
    if m:
        return await client.get_entity(m.group(1))

    if "t.me/" in ref:
        return await client.get_entity(ref)

    return await client.get_entity(ref)


def _same_chat(a: ParsedMessageLink, b: ParsedMessageLink) -> bool:
    return str(a.chat_ref) == str(b.chat_ref)


async def _sender_name(client, msg) -> str:
    try:
        sender = await msg.get_sender()
        if isinstance(sender, User):
            return getattr(sender, "first_name", None) or "Unknown"
        if sender and getattr(sender, "title", None):
            return sender.title
    except Exception:
        pass
    return "Unknown"


async def fetch_last_n(
    client,
    entity: Any,
    n: int,
    topic_id: Optional[int] = None,
) -> Tuple[List[Any], str]:
    limit = max(1, min(n, _max_osum()))
    kwargs: dict = {"entity": entity, "limit": limit}
    if topic_id:
        kwargs["reply_to"] = topic_id
    msgs = await client.get_messages(**kwargs)
    rows = [m for m in reversed(msgs) if m and (m.message or m.text)]
    truncated = ""
    if len(rows) >= limit:
        truncated = f"_Scanned last {limit} text messages (cap)._"
    return rows, truncated


async def fetch_range(
    client,
    entity: Any,
    start_id: int,
    end_id: int,
    topic_id: Optional[int] = None,
) -> Tuple[List[Any], str]:
    low, high = min(start_id, end_id), max(start_id, end_id)
    limit = min(high - low + 1, _max_osum())
    kwargs: dict = {
        "entity": entity,
        "min_id": low - 1,
        "max_id": high,
        "limit": limit,
    }
    if topic_id:
        kwargs["reply_to"] = topic_id
    msgs = await client.get_messages(**kwargs)
    rows = list(reversed([m for m in msgs if m and (m.message or m.text)]))
    truncated = ""
    total = high - low + 1
    if total > _max_osum():
        truncated = f"_Range had {total} messages; truncated to {_max_osum()}._"
    return rows, truncated


async def format_messages_with_links(
    client,
    msgs: List[Any],
    chat: Any,
) -> Tuple[str, Dict[int, str]]:
    lines: List[str] = []
    link_map: Dict[int, str] = {}
    for m in msgs:
        text = m.message or m.text
        if not text:
            continue
        url = build_message_link(chat, m.id)
        link_map[m.id] = url
        name = await _sender_name(client, m)
        lines.append(f"[msg:{m.id}] {name}: {text}")
    return "\n".join(lines), link_map


def _link_map_block(link_map: Dict[int, str]) -> str:
    if not link_map:
        return ""
    lines = ["Message link map (use these exact URLs in HTML <a href> tags):"]
    for mid, url in sorted(link_map.items()):
        lines.append(f"  msg:{mid} -> {url}")
    return "\n".join(lines)


async def resolve_osum_messages(
    client,
    query: OsumQuery,
) -> Tuple[str, Any, Dict[int, str], str]:
    truncated = ""

    if query.mode == "count":
        entity = await resolve_chat(client, query.chat_ref)
        msgs, truncated = await fetch_last_n(client, entity, query.count or 10)
        text, link_map = await format_messages_with_links(client, msgs, entity)
        return text, entity, link_map, truncated

    if query.mode in {"range", "from", "to"}:
        start, end = query.start, query.end
        if not start or not end:
            raise ValueError("Invalid range query.")
        if not _same_chat(start, end):
            raise ValueError("Both message links must be from the **same chat**.")
        entity = await resolve_chat(client, start.chat_ref)
        topic_id = start.thread_id or end.thread_id
        msgs, truncated = await fetch_range(
            client, entity, start.msg_id, end.msg_id, topic_id=topic_id
        )
        text, link_map = await format_messages_with_links(client, msgs, entity)
        return text, entity, link_map, truncated

    raise ValueError(f"Unknown osum mode: {query.mode}")


def build_osum_help(**overrides) -> dict:
    max_n = _max_osum()
    info = {
        "header": "Summarize another chat silently (other-chat summarize)",
        "description": (
            "Read messages from a **different** group/channel/DM and post the summary "
            "only in the chat where you run the command (e.g. Saved Messages). "
            "Never writes to the target chat."
        ),
        "flags": {
            "count": f"Last N messages — `.osum {max_n} @chat [focus]`",
            "range": "Between two message links — `.osum range <start> <end> [focus]`",
            "from": "Reply to bottom msg + `.osum from <start_link> [focus]`",
            "to": "Reply to top msg + `.osum to <end_link> [focus]`",
        },
        "options": {
            "<count>": f"1–{max_n} messages to scan",
            "@chat / t.me link": "Target chat — username, link, or id",
            "focus": "Optional natural-language filter (multi-word OK)",
        },
        "usage": [
            "{tr}osum 100 @codenight any job role posted here",
            "{tr}osum 50 https://t.me/codenight",
            "{tr}osum range https://t.me/codenight/1200 https://t.me/codenight/1450 hiring roles",
            "(reply bottom) {tr}osum from https://t.me/codenight/1200 job posts",
            "(reply top) {tr}osum to https://t.me/codenight/1450 job posts",
        ],
        "examples": [
            "{tr}osummarize 80 @codenight remote backend jobs",
            "{tr}osum range https://t.me/c/1234567890/100 https://t.me/c/1234567890/250 deadlines",
            "{tr}osum 30 @mygroup who mentioned meeting",
        ],
        "requirements": {
            "AI": "Configured AI provider (same as {tr}summarize)",
            "OSUM_MAX_MESSAGES": f"Optional env — default {max_n}",
        },
        "note": (
            "Output uses HTML links to the original messages when matches are found. "
            "Voice/media-only ranges return no text. Does not modify {tr}sum / {tr}summarize."
        ),
    }
    info.update(overrides)
    return info
