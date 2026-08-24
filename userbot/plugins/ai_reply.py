# AI Reply Coach — structured reply suggestions for owner

from userbot import catub
from userbot.ai_assistant import get_ai_provider, ConversationEngine
from userbot.ai_assistant.state import ai_state
from userbot.core.logger import logging
from userbot.core.managers import edit_delete, edit_or_reply
from userbot.plugins.ai_assistant import get_ai_components

plugin_category = "utils"
LOGS = logging.getLogger(__name__)


def _parse_reply_mode(raw: str) -> str:
    mode = (raw or "").strip().lower()
    if mode in ("savage", "am"):
        return mode
    return "default"


@catub.cat_cmd(
    pattern=r"reply(?:\s+(savage|am))?(?:\s|$)",
    command=("reply", plugin_category),
    info={
        "header": "AI reply coach",
        "description": (
            "Reply to a message to get copy-paste reply options. "
            "Modes: default (casual/funny/pro), savage, am (Amharic-English mix)."
        ),
        "usage": [
            "{tr}reply (reply to a message)",
            "{tr}reply savage (reply to a message)",
            "{tr}reply am (reply to a message)",
        ],
        "examples": [
            "{tr}reply",
            "{tr}reply savage",
            "{tr}reply am",
        ],
    },
)
async def reply_coach(event):
    "Give structured reply options for a message Henok received."
    reply = await event.get_reply_message()
    if not reply or not (reply.message or reply.text):
        return await edit_delete(
            event,
            "**Usage:** Reply to a message with `.reply`, `.reply savage`, or `.reply am`",
            8,
        )

    mode = _parse_reply_mode(event.pattern_match.group(1))
    replied_text = reply.message or reply.text
    sender_info = ""
    try:
        sender = await reply.get_sender()
        if sender:
            sender_info = f" from {getattr(sender, 'first_name', 'Someone')}"
    except Exception:
        pass

    prompt = (
        f'Incoming message{sender_info}: "{replied_text}"\n\n'
        "Give me reply options I can copy-paste."
    )

    thinking_msg = await edit_or_reply(event, "**Drafting replies...**")
    try:
        provider, conv_engine = get_ai_components()
    except Exception as e:
        return await thinking_msg.edit(f"**AI not configured:** {e}")

    try:
        messages = conv_engine.build_messages(
            current_message=prompt,
            chat_history=None,
            is_new_chat=False,
            is_afk=False,
            afk_reason=None,
            style_examples=ai_state.get_style_examples(limit=3),
            is_pmpermit=False,
            include_full_profile=False,
            is_owner_direct=True,
            friends=ai_state.get_friends(),
            owner_notes=ai_state.get_owner_notes(limit=10),
            reply_mode=mode,
        )
        response = await provider.generate_response(
            messages=messages,
            temperature=0.85,
            max_tokens=400,
        )
        if not response or not response.strip():
            return await thinking_msg.edit("**AI returned an empty response. Try again.**")
        formatted = f"**Reply options:**\n\n{response}"
        if len(formatted) > 4000:
            formatted = formatted[:3900] + "\n\n... _(truncated)_"
        await thinking_msg.edit(formatted)
    except Exception as e:
        LOGS.error(f"reply coach error: {e}")
        await thinking_msg.edit(f"**Error:** {e}")
