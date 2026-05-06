# AI Assistant Plugin for CatUserbot
# Modular AI-powered assistant with provider independence

import asyncio
import os

from telethon import events
from telethon.tl.types import User

from userbot import catub
from userbot.core.logger import logging
from userbot.core.managers import edit_delete, edit_or_reply
from userbot.ai_assistant import get_ai_provider, ConversationEngine
from userbot.ai_assistant.state import ai_state

plugin_category = "ai"
LOGS = logging.getLogger(__name__)

# Lazy initialization — nothing runs at import time
_ai_provider = None
_conv_engine = None


def _resolve_config(key, default=None):
    """Read a value from env first, then Config class/instance fallback."""
    val = os.environ.get(key)
    if val:
        return val
    try:
        from userbot.Config import Config
        # Config may be a class or an instance depending on the environment
        return getattr(Config, key, default)
    except Exception:
        return default


def get_ai_components():
    """Lazy-initialize and return (provider, conversation_engine)."""
    global _ai_provider, _conv_engine

    if _ai_provider is None:
        api_key = _resolve_config("AI_API_KEY")
        if not api_key:
            raise ValueError(
                "AI_API_KEY is not set. Add it to your environment variables."
            )
        provider_name = _resolve_config("AI_PROVIDER", "mistral")
        _ai_provider = get_ai_provider(provider_name, api_key)
        LOGS.info(f"AI provider ready: {_ai_provider.get_provider_name()}")

    if _conv_engine is None:
        user_name = _resolve_config("ALIVE_NAME", "Henok")
        _conv_engine = ConversationEngine(user_name=user_name)
        LOGS.info(f"Conversation engine ready for {user_name}")

    return _ai_provider, _conv_engine


# ==================== COMMAND HANDLERS ====================

@catub.cat_cmd(
    pattern="ai on$",
    command=("ai on", plugin_category),
    info={
        "header": "Enable AI assistant globally",
        "description": "Enables AI assistant to respond in all chats",
        "usage": "{tr}ai on",
    },
)
async def ai_global_on(event):
    ai_state.enable_global()
    await edit_delete(event, "✅ AI Assistant enabled globally.", 5)


@catub.cat_cmd(
    pattern="ai off$",
    command=("ai off", plugin_category),
    info={
        "header": "Disable AI assistant globally",
        "description": "Disables AI assistant in all chats",
        "usage": "{tr}ai off",
    },
)
async def ai_global_off(event):
    ai_state.disable_global()
    await edit_delete(event, "❌ AI Assistant disabled globally.", 5)


@catub.cat_cmd(
    pattern="ai enable$",
    command=("ai enable", plugin_category),
    info={
        "header": "Enable AI for current chat",
        "description": "Enables AI assistant for this specific chat only",
        "usage": "{tr}ai enable",
    },
)
async def ai_chat_enable(event):
    ai_state.enable_chat(event.chat_id)
    await edit_delete(event, "✅ AI Assistant enabled for this chat.", 5)


@catub.cat_cmd(
    pattern="ai disable$",
    command=("ai disable", plugin_category),
    info={
        "header": "Disable AI for current chat",
        "description": "Disables AI assistant for this specific chat",
        "usage": "{tr}ai disable",
    },
)
async def ai_chat_disable(event):
    ai_state.disable_chat(event.chat_id)
    await edit_delete(event, "❌ AI Assistant disabled for this chat.", 5)


@catub.cat_cmd(
    pattern="ai status$",
    command=("ai status", plugin_category),
    info={
        "header": "Check AI assistant status",
        "description": "Shows current AI assistant configuration and status",
        "usage": "{tr}ai status",
    },
)
async def ai_status(event):
    try:
        provider, _ = get_ai_components()
        provider_name = provider.get_provider_name()
    except Exception as e:
        provider_name = f"Not configured ({e})"

    user_name = _resolve_config("ALIVE_NAME", "Henok")
    msg = (
        f"**🤖 AI Assistant Status**\n\n"
        f"**Provider:** {provider_name}\n"
        f"**Global:** {'✅ On' if ai_state.global_enabled else '❌ Off'}\n"
        f"**This chat:** {'✅ On' if event.chat_id in ai_state.enabled_chats else '❌ Off'}\n\n"
        f"**Enabled chats:** {len(ai_state.enabled_chats)}\n"
        f"**Known chats:** {len(ai_state.known_chats)}\n"
        f"**Style examples:** {len(ai_state.user_style_examples)}\n"
        f"**User:** {user_name}"
    )
    await edit_or_reply(event, msg)


@catub.cat_cmd(
    pattern="ai clear$",
    command=("ai clear", plugin_category),
    info={
        "header": "Clear conversation history",
        "description": "Clears AI conversation history for current chat",
        "usage": "{tr}ai clear",
    },
)
async def ai_clear_history(event):
    ai_state.clear_history(event.chat_id)
    await edit_delete(event, "🗑️ Conversation history cleared.", 5)


# ==================== INCOMING MESSAGE HANDLER ====================
# Uses catub.on() directly — cat_cmd only fires for the account owner's
# outgoing messages, so we need the raw event listener for incoming ones.

@catub.on(events.NewMessage(incoming=True, func=lambda e: e.is_private or e.mentioned))
async def ai_auto_respond(event):
    """Respond to incoming messages when AI is enabled for this chat."""
    chat_id = event.chat_id

    # Gate: AI must be enabled for this chat
    if not ai_state.is_enabled(chat_id):
        return

    # Ignore bots
    sender = await event.get_sender()
    if not sender or (isinstance(sender, User) and sender.bot):
        return

    message_text = (event.message.message or "").strip()
    if not message_text:
        return

    # In groups only respond when explicitly mentioned
    if event.is_group and not event.mentioned:
        return

    # Anti-spam cooldown
    if not ai_state.can_respond(chat_id):
        return

    try:
        provider, conv_engine = get_ai_components()
    except Exception as e:
        LOGS.error(f"AI not ready: {e}")
        return

    is_new_chat = ai_state.is_new_chat(chat_id)

    # Read AFK state at call time to avoid circular import at module load
    import userbot as _ub
    is_afk = getattr(_ub, "ISAFK", False)
    afk_reason = getattr(_ub, "AFKREASON", None) if is_afk else None

    try:
        await event.client.send_read_acknowledge(chat_id, event.message)
        await asyncio.sleep(1.5)  # human-like typing delay

        messages = conv_engine.build_messages(
            current_message=message_text,
            chat_history=ai_state.get_history(chat_id),
            is_new_chat=is_new_chat,
            is_afk=is_afk,
            afk_reason=afk_reason,
            style_examples=ai_state.get_style_examples(limit=3),
        )

        response = await provider.generate_response(
            messages=messages,
            temperature=0.8,
            max_tokens=300,
        )

        await event.reply(response)

        ai_state.add_to_history(chat_id, "user", message_text)
        ai_state.add_to_history(chat_id, "assistant", response)
        ai_state.mark_response(chat_id)
        ai_state.mark_chat_known(chat_id)

        LOGS.info(f"AI replied in chat {chat_id}")

    except Exception as e:
        LOGS.error(f"AI response error in {chat_id}: {e}")


# ==================== OUTGOING STYLE LEARNER ====================

@catub.on(events.NewMessage(outgoing=True))
async def learn_user_style(event):
    """Passively learn from the user's own messages to mimic style."""
    text = (event.message.message or "").strip()
    # Skip commands and very short messages
    if not text or text.startswith(".") or len(text) < 5:
        return
    ai_state.add_user_style_example(text)
