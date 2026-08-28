# AI-powered bot self-help — .helpai
from userbot import catub
from userbot.Config import Config
from userbot.ai_assistant.state import ai_state
from userbot.core.logger import logging
from userbot.core.managers import edit_delete, edit_or_reply
from userbot.helpers.functions.bot_command_guide import (
    build_helpai_context,
    build_helpai_help,
    refresh_catalog_store,
)
from userbot.plugins.ai_assistant import get_ai_components

plugin_category = "tools"
LOGS = logging.getLogger(__name__)

_USAGE = (
    "**Ask me about any bot command in plain English.**\n\n"
    "Examples:\n"
    f"`{Config.COMMAND_HAND_LER}helpai what is the cmd to convert video to gifs`\n"
    f"`{Config.COMMAND_HAND_LER}helpai command to generate stickers`\n"
    f"`{Config.COMMAND_HAND_LER}helpai summarize another group without posting there`\n\n"
    f"Catalog: `userbot/data/bot_command_catalog.md` (auto-built from your loaded plugins).\n"
    f"Static help: `{Config.COMMAND_HAND_LER}help -c <command>`"
)


async def _run_helpai(event, question: str | None):
    q = (question or "").strip()
    if not q:
        return await edit_or_reply(event, _USAGE)

    thinking = await edit_or_reply(event, "**Searching bot commands…**")
    try:
        refresh_catalog_store()
        context = build_helpai_context(q)
    except Exception as e:
        LOGS.error(f"helpai catalog error: {e}")
        return await edit_delete(thinking, f"**Catalog error:** `{e}`", 10)

    await thinking.edit("**Thinking…**")
    try:
        provider, conv_engine = get_ai_components()
    except Exception as e:
        return await thinking.edit(f"**AI not configured:** {e}")

    try:
        user_msg = f"Help Henok use the userbot:\n\n{context}"
        messages = conv_engine.build_messages(
            current_message=user_msg,
            is_owner_direct=True,
            owner_notes=ai_state.get_owner_notes(limit=3),
            helpai_mode=True,
        )
        response = await provider.generate_response(
            messages=messages, temperature=0.25, max_tokens=600
        )
        if not response:
            return await thinking.edit("**No answer — try rephrasing or use `.s keyword`.**")

        out = f"**HelpAI** — _{q}_\n\n{response}"
        if len(out) > 4000:
            out = out[:3900] + "\n...(truncated — use `.help -c <cmd>` for full detail)"
        await thinking.edit(out)
    except Exception as e:
        LOGS.error(f"helpai error: {e}")
        await thinking.edit(f"**HelpAI error:** `{e}`")


@catub.cat_cmd(
    pattern=r"helpai(?:\s+([\s\S]*))?$",
    command=("helpai", plugin_category),
    info=build_helpai_help(),
)
async def helpai_cmd(event):
    """Natural-language bot command assistant."""
    await _run_helpai(event, event.pattern_match.group(1))
