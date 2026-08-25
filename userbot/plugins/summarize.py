# Text / chat summarizer via AI
# .summarize / .sum — DM + group aware

import os

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
MAX_INPUT = 6000
MAX_RANGE = 100


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
        lines.append(f"{name}: {m.message or m.text}")
    return "\n".join(lines)


async def _summarize_text(event, text: str):
    if len(text) > MAX_INPUT:
        text = text[:MAX_INPUT] + "\n\n...(truncated for length)"
    thinking = await edit_or_reply(event, "**Summarizing...**")
    try:
        provider, conv_engine = get_ai_components()
    except Exception as e:
        return await thinking.edit(f"**AI not configured:** {e}")
    try:
        messages = conv_engine.build_messages(
            current_message=f"Summarize this:\n\n{text}",
            is_owner_direct=True,
            owner_notes=ai_state.get_owner_notes(limit=5),
            summarize_mode=True,
        )
        response = await provider.generate_response(
            messages=messages, temperature=0.4, max_tokens=500
        )
        if not response:
            return await thinking.edit("**Empty summary. Try again.**")
        out = f"**Summary:**\n\n{response}"
        if len(out) > 4000:
            out = out[:3900] + "\n...(truncated)"
        await thinking.edit(out)
    except Exception as e:
        LOGS.error(f"summarize error: {e}")
        await thinking.edit(f"**Error:** {e}")


async def _summarize_voice(event, reply):
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
    return await _summarize_text(event, text)


async def _summarize_last_n(event, n: int):
    """Last N messages in current chat (DM or group)."""
    n = max(1, min(n, MAX_RANGE))
    msgs = await event.client.get_messages(event.chat_id, limit=n)
    # Exclude the command message itself
    rows = [m for m in reversed(msgs) if m.id != event.id]
    text = await _format_messages(rows)
    if not text:
        return await edit_delete(event, "**No text messages to summarize.**")
    return await _summarize_text(event, text)


async def _summarize_after_reply(event, reply):
    """All text messages after the replied message up to (not including) the command."""
    msgs = await event.client.get_messages(
        event.chat_id,
        min_id=reply.id,
        max_id=event.id,
        limit=MAX_RANGE,
    )
    # Telethon returns newest-first; chronological for the model
    rows = list(reversed(msgs))
    text = await _format_messages(rows)
    if not text:
        return await edit_delete(
            event,
            "**No text messages after that.** Reply to an earlier message, "
            "or use `.summarize this` for just that one.",
        )
    return await _summarize_text(event, text)


async def _summarize_single_reply(event, reply):
    mediatype = await media_type(reply)
    if mediatype in ["Voice", "Audio"]:
        return await _summarize_voice(event, reply)
    text = reply.message or reply.text
    if not text:
        return await edit_delete(event, "**Nothing to summarize in that message.**")
    return await _summarize_text(event, text)


async def _run_summarize(event, arg: str | None):
    """
    Semantics:
      .summarize / .sum <N>           → last N msgs (DM or group)
      .summarize this (reply)         → only the replied message
      .summarize (reply)              → all texts AFTER the replied message
      .summarize (reply to voice)     → STT then summarize that voice
    """
    arg = (arg or "").strip().lower()
    reply = await event.get_reply_message()

    if arg == "this":
        if not reply:
            return await edit_delete(
                event, "**Reply** to a message with `.summarize this`"
            )
        return await _summarize_single_reply(event, reply)

    if arg.isdigit():
        return await _summarize_last_n(event, int(arg))

    if arg and not reply:
        return await edit_delete(
            event,
            "**Usage:**\n"
            "`.summarize` / `.sum` (reply) — texts after that message\n"
            "`.summarize this` — just the replied message\n"
            "`.summarize 50` — last 50 in this chat (DM or group)",
        )

    if reply:
        mediatype = await media_type(reply)
        # Voice/audio without "this" still summarizes that clip
        if mediatype in ["Voice", "Audio"]:
            return await _summarize_single_reply(event, reply)
        return await _summarize_after_reply(event, reply)

    return await edit_delete(
        event,
        "**Usage:**\n"
        "`.summarize` / `.sum` (reply) — texts after that message\n"
        "`.summarize this` — just the replied message\n"
        "`.summarize 50` — last 50 in this chat (DM or group)",
    )


_USAGE_INFO = {
    "header": "Summarize text, voice, or chat ranges",
    "description": (
        "Works in DMs and groups. Reply to summarize everything after that message; "
        "use 'this' for only the replied message; pass a number for last N messages."
    ),
    "usage": [
        "{tr}summarize (reply) — all texts after that message",
        "{tr}summarize this (reply) — only that message",
        "{tr}summarize 50 — last 50 in DM or group",
        "{tr}sum … — short alias",
    ],
    "examples": [
        "{tr}summarize",
        "{tr}summarize this",
        "{tr}summarize 30",
        "{tr}sum this",
    ],
}


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
