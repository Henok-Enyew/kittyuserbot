# AI PM Permit — Smart AI-powered private message gatekeeper
# Completely separate from the existing pmpermit plugin.
# Reuses the existing AI provider and conversation engine.

import asyncio

from telethon import events
from telethon.tl.types import User

from userbot import catub
from userbot.core.logger import logging
from userbot.core.managers import edit_delete, edit_or_reply
from userbot.ai_assistant.state import ai_state

# Reuse the same provider/engine from ai_assistant.py
# Import lazily to avoid circular issues at load time
def _get_ai():
    from userbot.plugins.ai_assistant import get_ai_components
    return get_ai_components()


plugin_category = "utils"
LOGS = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# COMMANDS
# ══════════════════════════════════════════════════════════════════════════════

@catub.cat_cmd(
    pattern=r"aipmpermit (on|off)$",
    command=("aipmpermit", plugin_category),
    info={
        "header": "AI-powered PM permit",
        "description": (
            "Replaces the standard PM block with an AI assistant that handles "
            "unknown users professionally until you approve them."
        ),
        "usage": [
            "{tr}aipmpermit on",
            "{tr}aipmpermit off",
        ],
        "examples": [
            "{tr}aipmpermit on",
            "{tr}aipmpermit off",
        ],
        "note": (
            "Does NOT interfere with the existing pmpermit system. "
            "Use .aia or .aiapprove to approve a user, .aid or .aidisapprove to remove approval."
        ),
    },
)
async def aipmpermit_toggle(event):
    "Enable or disable AI PM permit."
    arg = event.pattern_match.group(1).strip().lower()
    if arg == "on":
        ai_state.enable_aipmpermit()
        await edit_delete(
            event,
            "🤖 **AI PM Permit enabled.**\n"
            "Unknown users will be handled by the AI until you approve them.\n"
            "Use `.aia` to approve, `.aid` to disapprove.",
            6,
        )
    else:
        ai_state.disable_aipmpermit()
        await edit_delete(event, "❌ AI PM Permit disabled.", 5)


@catub.cat_cmd(
    pattern=r"(?:aia|aiapprove)$",
    command=("aia", plugin_category),
    info={
        "header": "Approve user for AI PM Permit",
        "description": "Approves the user in the current private chat — AI gating stops for them.",
        "usage": "{tr}aia",
        "examples": "{tr}aia",
    },
)
async def ai_approve(event):
    "Approve the current chat user through AI PM Permit."
    if not event.is_private:
        return await edit_delete(event, "`This command only works in private chats.`", 5)

    sender = await event.get_sender()
    if not sender:
        return await edit_delete(event, "`Could not identify the user.`", 5)

    first_name = getattr(sender, "first_name", None)
    username = getattr(sender, "username", None)
    ai_state.approve_user(sender.id, first_name, username)
    
    name = first_name or str(sender.id)
    await edit_delete(event, f"✅ **{name}** approved. AI gating removed for this user.", 5)


@catub.cat_cmd(
    pattern=r"(?:aid|aidisapprove)$",
    command=("aid", plugin_category),
    info={
        "header": "Disapprove user for AI PM Permit",
        "description": "Removes approval — AI will gate this user again.",
        "usage": "{tr}aid",
        "examples": "{tr}aid",
    },
)
async def ai_disapprove(event):
    "Disapprove the current chat user — AI gating resumes."
    if not event.is_private:
        return await edit_delete(event, "`This command only works in private chats.`", 5)

    sender = await event.get_sender()
    if not sender:
        return await edit_delete(event, "`Could not identify the user.`", 5)

    ai_state.disapprove_user(sender.id)
    name = getattr(sender, "first_name", str(sender.id))
    await edit_delete(event, f"🚫 **{name}** disapproved. AI will gate this user again.", 5)


@catub.cat_cmd(
    pattern=r"aipmpermit status$",
    command=("aipmpermit status", plugin_category),
    info={
        "header": "AI PM Permit status",
        "description": "Shows whether AI PM Permit is active and how many users are approved.",
        "usage": "{tr}aipmpermit status",
    },
)
async def aipmpermit_status(event):
    "Show AI PM Permit status."
    status = "✅ Enabled" if ai_state.aipmpermit_enabled else "❌ Disabled"
    msg = (
        f"**🤖 AI PM Permit Status**\n\n"
        f"**Status:** {status}\n"
        f"**Approved users:** {len(ai_state.approved_users)}\n"
        f"**Pending (in AI conversation):** {len(ai_state.pending_users)}"
    )
    await edit_or_reply(event, msg)


@catub.cat_cmd(
    pattern=r"(?:aialist|aiapproved)$",
    command=("aialist", plugin_category),
    info={
        "header": "List approved users",
        "description": "Shows all users approved through AI PM Permit.",
        "usage": "{tr}aialist",
        "examples": "{tr}aialist",
    },
)
async def ai_approved_list(event):
    "List all approved users for AI PM Permit."
    try:
        from userbot.sql_helper.ai_pmpermit_sql import get_all_ai_approved
        approved = get_all_ai_approved()
        
        if not approved:
            return await edit_or_reply(event, "**No approved users yet.**")
        
        msg = "**✅ Approved Users for AI PM Permit:**\n\n"
        for user in approved:
            name = user.first_name or "Unknown"
            username = f"@{user.username}" if user.username else "No username"
            msg += f"• **{name}** ({username}) - ID: `{user.user_id}`\n"
        
        await edit_or_reply(event, msg)
    except Exception as e:
        await edit_or_reply(event, f"**Error:** {str(e)}")


# ══════════════════════════════════════════════════════════════════════════════
# INCOMING PRIVATE MESSAGE HANDLER
# ══════════════════════════════════════════════════════════════════════════════

@catub.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def aipmpermit_handler(event):
    """
    Gate incoming private messages through AI when aipmpermit is enabled
    and the sender is not yet approved.

    Priority:
      1. aipmpermit OFF          → skip (let other handlers deal with it)
      2. Sender is a bot         → skip
      3. Sender is approved      → skip (normal AI/no-AI flow applies)
      4. AI AFK is active        → AFK takes priority, skip pmpermit
      5. Unapproved sender       → AI gatekeeper responds
    """
    # 1. Feature must be on
    if not ai_state.aipmpermit_enabled:
        return

    sender = await event.get_sender()
    if not sender:
        return

    # 2. Ignore bots
    if isinstance(sender, User) and sender.bot:
        return

    user_id = sender.id

    # 3. Already approved — let the normal AI handler deal with it
    if ai_state.is_approved(user_id):
        return

    # 4. AI AFK takes priority — its handler will respond instead
    if ai_state.aiafk_enabled:
        return

    message_text = (event.message.message or "").strip()
    if not message_text:
        return

    chat_id = event.chat_id

    # Anti-spam cooldown (shared with main AI handler)
    if not ai_state.can_respond(chat_id):
        return

    try:
        provider, conv_engine = _get_ai()
    except Exception as e:
        LOGS.error(f"AI PM Permit — AI not ready: {e}")
        return

    # Mark as pending so we can track the conversation
    ai_state.mark_pending(user_id)

    is_new = ai_state.is_new_chat(chat_id)

    try:
        await event.client.send_read_acknowledge(chat_id, event.message)
        await asyncio.sleep(1.2)

        messages = conv_engine.build_messages(
            current_message=message_text,
            chat_history=ai_state.get_history(chat_id),
            is_new_chat=is_new,
            is_afk=False,
            afk_reason=None,
            style_examples=None,   # no style mimicry in gatekeeper mode
            is_pmpermit=True,      # inject gatekeeper context
        )

        response = await provider.generate_response(
            messages=messages,
            temperature=0.75,
            max_tokens=350,
        )

        await event.reply(response)

        ai_state.add_to_history(chat_id, "user", message_text)
        ai_state.add_to_history(chat_id, "assistant", response)
        ai_state.mark_response(chat_id)
        ai_state.mark_chat_known(chat_id)

        LOGS.info(f"AI PM Permit replied to unapproved user {user_id}")

    except Exception as e:
        LOGS.error(f"AI PM Permit response error for user {user_id}: {e}")
