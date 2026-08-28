# Text / chat summarizer via AI
# .summarize / .sum — DM + group aware, optional focus prompt

import os
import re
from typing import Optional

import requests
from telethon.tl.types import User

from userbot import catub
from userbot.Config import Config
from userbot.ai_assistant.state import ai_state
from userbot.core.logger import logging
from userbot.core.managers import edit_delete, edit_or_reply
from userbot.helpers.tools import media_type
from userbot.plugins.ai_assistant import get_ai_components

plugin_category = "utils"
LOGS = logging.getLogger(__name__)
MAX_INPUT = 8000


def _max_summarize_range() -> int:
    try:
        return int(
            os.environ.get("SUM_MAX_RANGE")
            or getattr(Config, "SUM_MAX_RANGE", None)
            or 150
        )
    except (TypeError, ValueError):
        return 150

_USAGE_HINT = (
    "**Usage:**\n"
    "`.summarize` / `.sum` (reply) — texts after that message\n"
    "`.sum tell me where he told me to meet` (reply) — focused summary\n"
    "`.summarizethis` / `.sumthis` — just the replied message\n"
    "`.summarize 50` — last 50 in this chat\n"
    "`.summarize 30 key deadlines only` — last 30 with focus\n"
    "`.sum job roles` — last 80 messages with focus (no reply)",
)


def _parse_summarize_arg(raw: str | None) -> tuple[str, str | None, int | None]:
    """
    Returns (mode, focus, count).
    mode: empty | count | focus | count_focus

    Anything after a space is a focus prompt — use .sumthis for one message only.
    """
    text = (raw or "").strip()
    if not text:
        return "empty", None, None
    if text.isdigit():
        return "count", None, int(text)
    m = re.match(r"^(\d+)\s+(.+)$", text)
    if m:
        return "count_focus", m.group(2).strip(), int(m.group(1))
    return "focus", text, None


async def _stt_from_file(path: str, mime: str) -> str:
    if not getattr(Config, "IBM_WATSON_CRED_URL", None) or not getattr(
        Config, "IBM_WATSON_CRED_PASSWORD", None
    ):
        return ""
    with open(path, "rb") as f:
        data = f.read()
    resp = requests.post(
        f"{Config.IBM_WATSON_CRED_URL}/v1/recognize",
        headers={"Content-Type": mime},
        data=data,
        auth=("apikey", Config.IBM_WATSON_CRED_PASSWORD),
        timeout=60,
    )
    if not resp.ok:
        return ""
    results = resp.json().get("results", [])
    if not results:
        return ""
    alts = results[0].get("alternatives", [])
    return alts[0].get("transcript", "") if alts else ""


async def _sender_name(msg) -> str:
    try:
        sender = await msg.get_sender()
        if isinstance(sender, User):
            return getattr(sender, "first_name", None) or "Unknown"
        if sender and getattr(sender, "title", None):
            return sender.title
    except Exception:
        pass
    return "Unknown"


async def _format_messages(msgs) -> str:
    lines = []
    for m in msgs:
        if not m or not (m.message or m.text):
            continue
        name = await _sender_name(m)
        lines.append(f"[#{m.id}] {name}: {m.message or m.text}")
    return "\n".join(lines)


def _reply_to_kw(msg) -> Optional[int]:
    """Forum topic / thread id when summarizing inside a topic."""
    rt = getattr(msg, "reply_to", None)
    if not rt:
        return None
    return getattr(rt, "reply_to_top_id", None) or getattr(rt, "reply_to_msg_id", None)


async def _collect_range_messages(event, min_id: int, max_id: int, anchor_msg=None):
    """Fetch text messages in id range (chronological), up to configured cap."""
    cap = max(1, min(_max_summarize_range(), 300))
    kwargs: dict = {
        "entity": event.chat_id,
        "min_id": min_id,
        "max_id": max_id,
    }
    topic = _reply_to_kw(anchor_msg) if anchor_msg else None
    if topic:
        kwargs["reply_to"] = topic

    rows = []
    async for m in event.client.iter_messages(limit=cap, **kwargs):
        if m.id == event.id:
            continue
        if m.message or m.text:
            rows.append(m)
    return list(reversed(rows))


async def _summarize_text(event, text: str, focus: str | None = None, truncated: bool = False):
    was_truncated = truncated
    if len(text) > MAX_INPUT:
        text = text[:MAX_INPUT] + "\n\n...(truncated for length)"
        was_truncated = True
    thinking = await edit_or_reply(event, "**Summarizing...**")
    try:
        provider, conv_engine = get_ai_components()
    except Exception as e:
        return await thinking.edit(f"**AI not configured:** {e}")
    try:
        trunc_note = ""
        if was_truncated:
            trunc_note = (
                "\n(Note: message history was truncated — say if matches might be "
                "outside the scanned text.)\n"
            )
        if focus:
            user_msg = (
                f"Find and summarize everything related to this focus: {focus}\n"
                f"{trunc_note}\nMessages:\n{text}"
            )
        else:
            user_msg = f"Summarize this:\n\n{text}"
        messages = conv_engine.build_messages(
            current_message=user_msg,
            is_owner_direct=True,
            owner_notes=ai_state.get_owner_notes(limit=5),
            summarize_mode=True,
            summarize_focus=focus,
        )
        max_tokens = 800 if focus else 500
        response = await provider.generate_response(
            messages=messages, temperature=0.35, max_tokens=max_tokens
        )
        if not response:
            return await thinking.edit("**Empty summary. Try again.**")
        header = "**Focused summary:**" if focus else "**Summary:**"
        out = f"{header}\n\n{response}"
        if len(out) > 4000:
            out = out[:3900] + "\n...(truncated)"
        await thinking.edit(out)
    except Exception as e:
        LOGS.error(f"summarize error: {e}")
        await thinking.edit(f"**Error:** {e}")


async def _summarize_voice(event, reply, focus: str | None = None):
    if not getattr(Config, "IBM_WATSON_CRED_URL", None):
        return await edit_delete(
            event, "**Voice summarize needs IBM Watson STT configured.**"
        )
    catevent = await edit_or_reply(event, "**Transcribing...**")
    os.makedirs(Config.TEMP_DIR, exist_ok=True)
    path = await event.client.download_media(reply, Config.TEMP_DIR)
    mime = getattr(reply.document, "mime_type", "audio/ogg")
    text = await _stt_from_file(path, mime)
    if path and os.path.exists(path):
        os.remove(path)
    if not text:
        return await edit_delete(catevent, "**Could not transcribe audio.**")
    await catevent.delete()
    return await _summarize_text(event, text, focus=focus)


async def _summarize_last_n(event, n: int, focus: str | None = None):
    """Last N messages in current chat (DM or group)."""
    cap = _max_summarize_range()
    n = max(1, min(n, cap))
    kwargs: dict = {"entity": event.chat_id, "limit": n + 1}
    topic = _reply_to_kw(await event.get_reply_message()) or _reply_to_kw(event)
    if topic:
        kwargs["reply_to"] = topic
    msgs = await event.client.get_messages(**kwargs)
    rows = [m for m in reversed(msgs) if m.id != event.id and (m.message or m.text)]
    truncated = len(rows) >= n
    text = await _format_messages(rows)
    if not text:
        return await edit_delete(event, "**No text messages to summarize.**")
    return await _summarize_text(event, text, focus=focus, truncated=truncated)


async def _summarize_after_reply(event, reply, focus: str | None = None):
    """Messages from replied anchor through this command (inclusive of reply when focused)."""
    min_id = reply.id - 1 if focus else reply.id
    rows = await _collect_range_messages(
        event, min_id=min_id, max_id=event.id, anchor_msg=reply
    )
    truncated = len(rows) >= _max_summarize_range()
    text = await _format_messages(rows)
    if not text:
        return await edit_delete(
            event,
            "**No text messages in that range.** Reply to an earlier message, "
            "or use `.summarize 50 <focus>` for the last 50 messages.",
        )
    return await _summarize_text(event, text, focus=focus, truncated=truncated)


async def _summarize_single_reply(event, reply, focus: str | None = None):
    mediatype = await media_type(reply)
    if mediatype in ["Voice", "Audio"]:
        return await _summarize_voice(event, reply, focus=focus)
    text = reply.message or reply.text
    if not text:
        return await edit_delete(event, "**Nothing to summarize in that message.**")
    return await _summarize_text(event, text, focus=focus)


async def _run_summarize(event, arg: str | None):
    """
    Semantics:
      .summarize / .sum           → after-reply generic (with reply)
      .summarize / .sum <focus>   → after-reply + focus (with reply)
      .summarize <N>              → last N messages
      .summarize <N> <focus>      → last N + focus
      Single message only → .sumthis / .summarizethis (no space)
    """
    mode, focus, count = _parse_summarize_arg(arg)
    reply = await event.get_reply_message()

    if mode == "count":
        return await _summarize_last_n(event, count)

    if mode == "count_focus":
        return await _summarize_last_n(event, count, focus=focus)

    if mode == "focus" and not reply:
        # No reply: scan recent messages with focus (default 80)
        default_n = min(80, _max_summarize_range())
        return await _summarize_last_n(event, default_n, focus=focus)

    if mode == "focus" and reply:
        mediatype = await media_type(reply)
        if mediatype in ["Voice", "Audio"]:
            return await _summarize_single_reply(event, reply, focus=focus)
        return await _summarize_after_reply(event, reply, focus=focus)

    if mode == "empty" and reply:
        mediatype = await media_type(reply)
        if mediatype in ["Voice", "Audio"]:
            return await _summarize_single_reply(event, reply)
        return await _summarize_after_reply(event, reply)

    return await edit_delete(event, _USAGE_HINT)


_USAGE_INFO = {
    "header": "Summarize text, voice, or chat ranges",
    "description": (
        "Works in DMs and groups. Focus text scans semantically across up to 150 messages. "
        "Reply + `.sum` scans from that message forward. `.sum <focus>` without reply scans "
        "the last 80 messages. For one message only, use `.sumthis`."
    ),
    "usage": [
        "{tr}summarize (reply) — all texts after that message",
        "{tr}sum tell me where he told me to meet (reply) — focused",
        "{tr}summarizethis (reply) — only that message",
        "{tr}sumthis (reply) — short alias for single message",
        "{tr}summarize 50 — last 50 in DM or group",
        "{tr}summarize 30 key deadlines only — last 30 with focus",
        "{tr}sum any job role posted — last 80 with focus",
    ],
    "examples": [
        "{tr}summarize",
        "{tr}sum tell me where he told me to meet",
        "{tr}summarizethis",
        "{tr}summarize 100 job postings",
        "{tr}sum deadlines and meeting times",
    ],
}


@catub.cat_cmd(
    pattern=r"summarizethis$",
    command=("summarizethis", plugin_category),
    info={
        "header": "Summarize only the replied message",
        "description": "Reply to a text or voice message and summarize just that one.",
        "usage": "{tr}summarizethis (reply to message)",
        "examples": "{tr}summarizethis",
    },
)
async def summarizethis_cmd(event):
    "Summarize only the replied message."
    reply = await event.get_reply_message()
    if not reply:
        return await edit_delete(
            event, "**Reply** to a message with `.summarizethis`"
        )
    await _summarize_single_reply(event, reply)


@catub.cat_cmd(
    pattern=r"sumthis$",
    command=("sumthis", plugin_category),
    info={
        "header": "Short alias — summarize only the replied message",
        "usage": "{tr}sumthis (reply to message)",
        "examples": "{tr}sumthis",
    },
)
async def sumthis_cmd(event):
    "Summarize only the replied message (short alias)."
    reply = await event.get_reply_message()
    if not reply:
        return await edit_delete(event, "**Reply** to a message with `.sumthis`")
    await _summarize_single_reply(event, reply)


@catub.cat_cmd(
    pattern=r"summarize(?:\s+(.+))?$",
    command=("summarize", plugin_category),
    info=_USAGE_INFO,
)
async def summarize_cmd(event):
    "Summarize replied content, range after reply, or last N messages."
    await _run_summarize(event, event.pattern_match.group(1))


@catub.cat_cmd(
    pattern=r"sum(?:\s+(.+))?$",
    command=("sum", plugin_category),
    info={
        **_USAGE_INFO,
        "header": "Alias for .summarize",
    },
)
async def sum_cmd(event):
    "Short alias for .summarize."
    await _run_summarize(event, event.pattern_match.group(1))
