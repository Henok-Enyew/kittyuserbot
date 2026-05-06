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

# "utils" is a recognised GRP_INFO category; "ai" is not in the list
plugin_category = "utils"
LOGS = logging.getLogger(__name__)

# Lazy singletons — nothing initialised at import time
_ai_provider = None
_conv_engine = None


def _resolve_config(key, default=None):
    """Read from env first, then fall back to Config (class or instance)."""
    val = os.environ.get(key)
    if val:
        return val
    try:
        from userbot.Config import Config
        return getattr(Config, key, default)
    except Exception:
        return default


def get_ai_components():
    """Lazy-initialise and return (provider, conversation_engine)."""
    global _ai_provider, _conv_engine

    if _ai_provider is None:
        api_key = _resolve_config("AI_API_KEY")
        if not api_key:
            raise ValueError("AI_API_KEY is not set. Add it to your environment variables.")
        provider_name = _resolve_config("AI_PROVIDER", "mistral")
        _ai_provider = get_ai_provider(provider_name, api_key)
        LOGS.info(f"AI provider ready: {_ai_provider.get_provider_name()}")

    if _conv_engine is None:
        user_name = _resolve_config("ALIVE_NAME", "Henok")
        _conv_engine = ConversationEngine(user_name=user_name)
        LOGS.info(f"Conversation engine ready for {user_name}")

    return _ai_provider, _conv_engine


# ══════════════════════════════════════════════════════════════════════════════
# COMMAND HANDLERS
# ══════════════════════════════════════════════════════════════════════════════

@catub.cat_cmd(
    pattern="ai on$",
    command=("ai on", plugin_category),
    info={
        "header": "Enable AI assistant globally",
        "description": "Turns on AI auto-reply in all chats at once.",
        "usage": "{tr}ai on",
        "examples": "{tr}ai on",
    },
)
async def ai_global_on(event):
    "Enable AI assistant globally across all chats."
    ai_state.enable_global()
    await edit_delete(event, "✅ AI Assistant enabled globally.", 5)


@catub.cat_cmd(
    pattern="ai off$",
    command=("ai off", plugin_category),
    info={
        "header": "Disable AI assistant globally",
        "description": "Turns off AI auto-reply in all chats at once.",
        "usage": "{tr}ai off",
        "examples": "{tr}ai off",
    },
)
async def ai_global_off(event):
    "Disable AI assistant globally across all chats."
    ai_state.disable_global()
    await edit_delete(event, "❌ AI Assistant disabled globally.", 5)


@catub.cat_cmd(
    pattern="ai enable$",
    command=("ai enable", plugin_category),
    info={
        "header": "Enable AI for current chat",
        "description": "Turns on AI auto-reply only in this specific chat.",
        "usage": "{tr}ai enable",
        "examples": "{tr}ai enable",
    },
)
async def ai_chat_enable(event):
    "Enable AI assistant for this specific chat only."
    ai_state.enable_chat(event.chat_id)
    await edit_delete(event, "✅ AI Assistant enabled for this chat.", 5)


@catub.cat_cmd(
    pattern="ai disable$",
    command=("ai disable", plugin_category),
    info={
        "header": "Disable AI for current chat",
        "description": "Turns off AI auto-reply only in this specific chat.",
        "usage": "{tr}ai disable",
        "examples": "{tr}ai disable",
    },
)
async def ai_chat_disable(event):
    "Disable AI assistant for this specific chat only."
    ai_state.disable_chat(event.chat_id)
    await edit_delete(event, "❌ AI disabled for this chat (overrides global).", 5)


@catub.cat_cmd(
    pattern="ai status$",
    command=("ai status", plugin_category),
    info={
        "header": "Check AI assistant status",
        "description": "Shows provider, global toggle, per-chat toggle, AI AFK state, and stats.",
        "usage": "{tr}ai status",
        "examples": "{tr}ai status",
    },
)
async def ai_status(event):
    "Show current AI assistant configuration and stats."
    try:
        provider, _ = get_ai_components()
        provider_name = provider.get_provider_name()
    except Exception as e:
        provider_name = f"Not configured ({e})"

    chat_id = event.chat_id
    if chat_id in ai_state.disabled_chats:
        chat_status = "🚫 Explicitly OFF (overrides global)"
    elif chat_id in ai_state.enabled_chats:
        chat_status = "✅ Explicitly ON"
    elif ai_state.global_enabled:
        chat_status = "✅ ON (via global)"
    elif ai_state.aiafk_enabled:
        chat_status = "✅ ON (via AI AFK)"
    else:
        chat_status = "❌ OFF"
    user_name = _resolve_config("ALIVE_NAME", "Henok")
    afk_line = ""
    if ai_state.aiafk_enabled:
        reason = ai_state.aiafk_reason or "no reason set"
        afk_line = f"\n**AI AFK:** 🌙 On — _{reason}_"

    msg = (
        f"**🤖 AI Assistant Status**\n\n"
        f"**Provider:** {provider_name}\n"
        f"**Global:** {'✅ On' if ai_state.global_enabled else '❌ Off'}\n"
        f"**This chat:** {chat_status}"
        f"{afk_line}\n\n"
        f"**Enabled chats:** {len(ai_state.enabled_chats)}\n"
        f"**Disabled chats:** {len(ai_state.disabled_chats)}\n"
        f"**Known chats:** {len(ai_state.known_chats)}\n"
        f"**Style examples:** {len(ai_state.user_style_examples)}\n"
        f"**User:** {user_name}"
    )
    await edit_or_reply(event, msg)


@catub.cat_cmd(
    pattern="ai clear$",
    command=("ai clear", plugin_category),
    info={
        "header": "Clear AI conversation history",
        "description": "Wipes the conversation memory for the current chat so AI starts fresh.",
        "usage": "{tr}ai clear",
        "examples": "{tr}ai clear",
    },
)
async def ai_clear_history(event):
    "Clear AI conversation history for the current chat."
    ai_state.clear_history(event.chat_id)
    await edit_delete(event, "🗑️ Conversation history cleared.", 5)


# ── AI AFK ────────────────────────────────────────────────────────────────────

@catub.cat_cmd(
    pattern=r"aiafk ?(.*)$",
    command=("aiafk", plugin_category),
    info={
        "header": "AI-powered AFK mode",
        "description": (
            "Enables a smart AFK mode where the AI replies to ALL incoming messages "
            "on your behalf. Automatically turns off the moment you send any message."
        ),
        "usage": [
            "{tr}aiafk",
            "{tr}aiafk <reason>",
            "{tr}aiafk off",
        ],
        "examples": [
            "{tr}aiafk eating lunch",
            "{tr}aiafk in a meeting",
            "{tr}aiafk off",
        ],
        "note": (
            "This is separate from the built-in .afk command. "
            "AI AFK responds to every private message and group mention, "
            "and disables itself automatically when you type anything."
        ),
    },
)
async def ai_afk_cmd(event):
    "Enable or disable AI-powered AFK mode."
    arg = (event.pattern_match.group(1) or "").strip()

    if arg.lower() == "off":
        ai_state.disable_aiafk()
        await edit_delete(event, "✅ AI AFK disabled. Welcome back!", 5)
        return

    ai_state.enable_aiafk(reason=arg or None)
    reason_text = f"\nReason: _{arg}_" if arg else ""
    await edit_delete(
        event,
        f"🌙 **AI AFK enabled.**{reason_text}\n"
        "I'll reply to messages for you.\n"
        "Send any message to turn it off automatically.",
        6,
    )


# ══════════════════════════════════════════════════════════════════════════════
# INCOMING MESSAGE HANDLER
# cat_cmd only fires on the owner's outgoing messages, so we use catub.on()
# for incoming messages from other people.
# ══════════════════════════════════════════════════════════════════════════════

@catub.on(events.NewMessage(incoming=True))
async def ai_auto_respond(event):
    """Respond to incoming messages when AI or AI AFK is active."""
    chat_id = event.chat_id
    is_private = event.is_private
    is_mentioned = event.mentioned

    # ── Decide whether to respond ──────────────────────────────────────────
    # AI AFK: respond to ALL private messages and group mentions
    # Regular AI: respond to private messages and group mentions only
    in_aiafk = ai_state.aiafk_enabled
    in_regular_ai = ai_state.is_enabled(chat_id)

    if not in_aiafk and not in_regular_ai:
        return

    # In groups: only respond when mentioned (both modes)
    if not is_private and not is_mentioned:
        return

    # Ignore bots
    sender = await event.get_sender()
    if not sender or (isinstance(sender, User) and sender.bot):
        return

    message_text = (event.message.message or "").strip()
    if not message_text:
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

    # AFK context: prefer AI AFK state, fall back to built-in .afk globals
    if in_aiafk:
        is_afk = True
        afk_reason = ai_state.aiafk_reason
    else:
        import userbot as _ub
        is_afk = getattr(_ub, "ISAFK", False)
        afk_reason = getattr(_ub, "AFKREASON", None) if is_afk else None

    try:
        await event.client.send_read_acknowledge(chat_id, event.message)
        await asyncio.sleep(1.5)  # simulate human typing delay

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

        LOGS.info(f"AI replied in chat {chat_id} (aiafk={in_aiafk})")

    except Exception as e:
        LOGS.error(f"AI response error in {chat_id}: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# OUTGOING MESSAGE HANDLER
# Two jobs:
#   1. Auto-disable AI AFK the moment Henok sends any message
#   2. Passively learn from Henok's writing style
# ══════════════════════════════════════════════════════════════════════════════

@catub.on(events.NewMessage(outgoing=True))
async def on_outgoing_message(event):
    """Auto-disable AI AFK on any outgoing message; learn style."""
    text = (event.message.message or "").strip()

    # ── Auto-disable AI AFK ────────────────────────────────────────────────
    if ai_state.aiafk_enabled:
        # Don't disable on the .aiafk command itself
        if not text.lower().startswith(".aiafk"):
            ai_state.disable_aiafk()
            LOGS.info("AI AFK auto-disabled — Henok sent a message.")
            # Send a quiet notification so Henok knows AFK turned off
            try:
                await event.client.send_message(
                    event.chat_id,
                    "_(AI AFK mode turned off — you're back online)_",
                )
            except Exception:
                pass  # Non-critical, never crash here

    # ── Style learning ─────────────────────────────────────────────────────
    # Skip commands and very short messages
    if text and not text.startswith(".") and len(text) >= 5:
        ai_state.add_user_style_example(text)
