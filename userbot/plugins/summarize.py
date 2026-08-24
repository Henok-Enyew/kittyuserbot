# Text / chat summarizer via AI

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


@catub.cat_cmd(
    pattern=r"summarize(?:\s+(\d+))?$",
    command=("summarize", plugin_category),
    info={
        "header": "Summarize text, voice, or recent chat messages",
        "usage": [
            "{tr}summarize (reply to text/voice)",
            "{tr}summarize 50 (last 50 messages in group)",
        ],
    },
)
async def summarize_cmd(event):
    "Summarize replied content or last N group messages."
    count = event.pattern_match.group(1)
    reply = await event.get_reply_message()

    if count and not reply:
        try:
            n = max(1, min(int(count), 100))
        except ValueError:
            return await edit_delete(event, "**Usage:** `.summarize 50` in a group")
        if not event.is_group:
            return await edit_delete(event, "**Use in a group** or reply to a message.")
        msgs = await event.client.get_messages(event.chat_id, limit=n)
        lines = []
        for m in reversed(msgs):
            if not m.message:
                continue
            sender = await m.get_sender()
            name = "Unknown"
            if isinstance(sender, User):
                name = getattr(sender, "first_name", "Unknown")
            lines.append(f"{name}: {m.message}")
        if not lines:
            return await edit_delete(event, "**No text messages to summarize.**")
        return await _summarize_text(event, "\n".join(lines))

    if not reply:
        return await edit_delete(
            event,
            "**Reply** to text/voice or use `.summarize 50` in a group.",
        )

    mediatype = await media_type(reply)
    if mediatype in ["Voice", "Audio"]:
        if not getattr(Config, "IBM_WATSON_CRED_URL", None):
            return await edit_delete(
                event, "**Voice summarize needs IBM Watson STT configured.**"
            )
        catevent = await edit_or_reply(event, "**Transcribing...**")
        os.makedirs(Config.TEMP_DIR, exist_ok=True)
        path = await event.client.download_media(reply, Config.TEMP_DIR)
        mime = getattr(reply.document, "mime_type", "audio/ogg")
        text = await _stt_from_file(path, mime)
        if os.path.exists(path):
            os.remove(path)
        if not text:
            return await edit_delete(catevent, "**Could not transcribe audio.**")
        await catevent.delete()
        return await _summarize_text(event, text)

    text = reply.message or reply.text
    if not text:
        return await edit_delete(event, "**Nothing to summarize in that message.**")
    await _summarize_text(event, text)
