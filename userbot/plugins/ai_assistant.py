# AI Assistant Plugin for CatUserbot
# Modular AI-powered assistant with provider independence

import asyncio
import os
from telethon import events
from telethon.tl.types import User

from userbot import catub
from userbot.core.logger import logging
from userbot.core.managers import edit_delete, edit_or_reply
from userbot.ai_assistant import get_ai_provider, ConversationEngine, AIState
from userbot.ai_assistant.state import ai_state
from userbot import ISAFK, AFKREASON

plugin_category = "ai"
LOGS = logging.getLogger(__name__)

# Initialize AI components
AI_PROVIDER_NAME = os.environ.get("AI_PROVIDER", "mistral")
AI_API_KEY = os.environ.get("AI_API_KEY", None)
AI_USER_NAME = os.environ.get("ALIVE_NAME", "Henok")

# Lazy initialization
ai_provider = None
conversation_engine = None


def get_ai_components():
    """Lazy initialization of AI components"""
    global ai_provider, conversation_engine
    
    if not AI_API_KEY:
        raise ValueError("AI_API_KEY not configured. Set it in environment variables.")
    
    if ai_provider is None:
        ai_provider = get_ai_provider(AI_PROVIDER_NAME, AI_API_KEY)
        LOGS.info(f"Initialized AI provider: {ai_provider.get_provider_name()}")
    
    if conversation_engine is None:
        conversation_engine = ConversationEngine(user_name=AI_USER_NAME)
        LOGS.info(f"Initialized conversation engine for {AI_USER_NAME}")
    
    return ai_provider, conversation_engine


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
    """Enable AI assistant globally"""
    ai_state.enable_global()
    await edit_delete(
        event,
        "✅ **AI Assistant enabled globally**\n\nI'll now respond to messages in all chats.",
        5
    )


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
    """Disable AI assistant globally"""
    ai_state.disable_global()
    await edit_delete(
        event,
        "❌ **AI Assistant disabled globally**\n\nI'll stop responding automatically.",
        5
    )


@catub.cat_cmd(
    pattern="ai enable$",
    command=("ai enable", plugin_category),
    info={
        "header": "Enable AI assistant for current chat",
        "description": "Enables AI assistant for this specific chat only",
        "usage": "{tr}ai enable",
    },
)
async def ai_chat_enable(event):
    """Enable AI assistant for current chat"""
    chat_id = event.chat_id
    ai_state.enable_chat(chat_id)
    await edit_delete(
        event,
        "✅ **AI Assistant enabled for this chat**\n\nI'll respond to messages here.",
        5
    )


@catub.cat_cmd(
    pattern="ai disable$",
    command=("ai disable", plugin_category),
    info={
        "header": "Disable AI assistant for current chat",
        "description": "Disables AI assistant for this specific chat",
        "usage": "{tr}ai disable",
    },
)
async def ai_chat_disable(event):
    """Disable AI assistant for current chat"""
    chat_id = event.chat_id
    ai_state.disable_chat(chat_id)
    await edit_delete(
        event,
        "❌ **AI Assistant disabled for this chat**\n\nI'll stop responding here.",
        5
    )


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
    """Show AI assistant status"""
    try:
        provider, _ = get_ai_components()
        provider_name = provider.get_provider_name()
    except Exception as e:
        provider_name = f"Not configured ({str(e)})"
    
    global_status = "✅ Enabled" if ai_state.global_enabled else "❌ Disabled"
    chat_id = event.chat_id
    chat_status = "✅ Enabled" if chat_id in ai_state.enabled_chats else "❌ Disabled"
    
    status_msg = f"""**🤖 AI Assistant Status**

**Provider:** {provider_name}
**Global Status:** {global_status}
**This Chat:** {chat_status}

**Enabled Chats:** {len(ai_state.enabled_chats)}
**Known Chats:** {len(ai_state.known_chats)}
**Style Examples:** {len(ai_state.user_style_examples)}

**User:** {AI_USER_NAME}
"""
    
    await edit_or_reply(event, status_msg)


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
    """Clear conversation history for current chat"""
    chat_id = event.chat_id
    ai_state.clear_history(chat_id)
    await edit_delete(
        event,
        "🗑️ **Conversation history cleared**\n\nStarting fresh!",
        5
    )


# ==================== MESSAGE HANDLER ====================

@catub.cat_cmd(incoming=True, func=lambda e: bool(e.mentioned or e.is_private), edited=False)
async def ai_auto_respond(event):
    """Automatically respond to incoming messages using AI"""
    
    # Check if AI is enabled
    chat_id = event.chat_id
    if not ai_state.is_enabled(chat_id):
        return
    
    # Don't respond to bots
    sender = await event.get_sender()
    if not sender or (isinstance(sender, User) and sender.bot):
        return
    
    # Get message text
    message_text = event.message.message
    if not message_text:
        return
    
    # Check if we should respond
    is_group = event.is_group
    is_mentioned = event.mentioned
    
    try:
        provider, conv_engine = get_ai_components()
    except Exception as e:
        LOGS.error(f"AI components not initialized: {e}")
        return
    
    # Decide if we should respond
    if not conv_engine.should_respond(message_text, is_group, is_mentioned):
        return
    
    # Check cooldown (anti-spam)
    if not ai_state.can_respond(chat_id):
        return
    
    # Check if new chat
    is_new_chat = ai_state.is_new_chat(chat_id)
    
    # Check AFK status
    is_afk = ISAFK
    afk_reason = AFKREASON if is_afk else None
    
    try:
        # Simulate typing (human-like behavior)
        await event.client.send_read_acknowledge(event.chat_id, event.message)
        
        # Add small delay to simulate thinking
        await asyncio.sleep(1.5)
        
        # Get conversation history
        chat_history = ai_state.get_history(chat_id)
        
        # Get style examples
        style_examples = ai_state.get_style_examples(limit=3)
        
        # Build messages for AI
        messages = conv_engine.build_messages(
            current_message=message_text,
            chat_history=chat_history,
            is_new_chat=is_new_chat,
            is_afk=is_afk,
            afk_reason=afk_reason,
            style_examples=style_examples
        )
        
        # Generate AI response
        response = await provider.generate_response(
            messages=messages,
            temperature=0.8,
            max_tokens=300
        )
        
        # Send response
        await event.reply(response)
        
        # Update state
        ai_state.add_to_history(chat_id, "user", message_text)
        ai_state.add_to_history(chat_id, "assistant", response)
        ai_state.mark_response(chat_id)
        ai_state.mark_chat_known(chat_id)
        
        LOGS.info(f"AI responded in chat {chat_id}")
        
    except Exception as e:
        LOGS.error(f"AI response error: {e}")
        # Silently fail - don't expose errors to users


# ==================== OUTGOING MESSAGE HANDLER ====================

@catub.cat_cmd(outgoing=True, edited=False)
async def learn_user_style(event):
    """Learn from user's outgoing messages to mimic style"""
    
    # Don't learn from commands
    message_text = event.message.message
    if not message_text or message_text.startswith("."):
        return
    
    # Add to style examples
    ai_state.add_user_style_example(message_text)
