# Silent cross-chat summarizer — .osum / .osummarize
from userbot import catub
from userbot.ai_assistant.state import ai_state
from userbot.core.logger import logging
from userbot.core.managers import edit_delete, edit_or_reply
from userbot.helpers.functions.osummarize import (
    MAX_INPUT,
    _link_map_block,
    build_osum_help,
    parse_osum_args,
    resolve_osum_messages,
    sanitize_osum_html,
)
from userbot.plugins.ai_assistant import get_ai_components

plugin_category = "utils"
LOGS = logging.getLogger(__name__)


async def _run_osum(event, raw: str | None):
    reply = await event.get_reply_message()
    try:
        query = parse_osum_args(raw, reply_msg=reply)
    except ValueError as e:
        return await edit_delete(event, str(e), 12)

    catevent = await edit_or_reply(event, "**Scanning other chat (silent)...**")
    try:
        text, entity, link_map, truncated = await resolve_osum_messages(
            event.client, query
        )
    except Exception as e:
        LOGS.error(f"osum fetch error: {e}")
        return await edit_delete(catevent, f"**Could not read target chat:**\n`{e}`", 12)

    if not text:
        return await edit_delete(
            catevent,
            "**No text messages to summarize** in that range (media/voice skipped).",
            10,
        )

    if len(text) > MAX_INPUT:
        text = text[:MAX_INPUT] + "\n\n...(truncated for length)"

    chat_label = getattr(entity, "title", None) or getattr(entity, "first_name", "chat")
    link_block = _link_map_block(link_map)
    focus = query.focus

    if focus:
        user_msg = (
            f"Summarize this chat ({chat_label}) with focus: {focus}\n\n"
            f"{link_block}\n\nMessages:\n{text}"
        )
    else:
        user_msg = (
            f"Summarize this chat ({chat_label}):\n\n"
            f"{link_block}\n\nMessages:\n{text}"
        )

    await catevent.edit("**Summarizing other chat...**")
    try:
        provider, conv_engine = get_ai_components()
    except Exception as e:
        return await catevent.edit(f"**AI not configured:** {e}")

    try:
        messages = conv_engine.build_messages(
            current_message=user_msg,
            is_owner_direct=True,
            owner_notes=ai_state.get_owner_notes(limit=5),
            summarize_mode=True,
            summarize_focus=focus,
            summarize_link_mode=True,
        )
        response = await provider.generate_response(
            messages=messages, temperature=0.4, max_tokens=700
        )
        if not response:
            return await catevent.edit("**Empty summary. Try again.**")

        header = "**Other-chat summary"
        if focus:
            header += f" (focus: {focus})"
        header += ":**"
        out = header + "\n\n" + sanitize_osum_html(response, link_map)
        if truncated:
            out += f"\n\n_{truncated}_"
        if len(out) > 4000:
            out = out[:3900] + "\n...(truncated)"
        await catevent.edit(out, parse_mode="html", link_preview=False)
    except Exception as e:
        LOGS.error(f"osum summarize error: {e}")
        await catevent.edit(f"**Error:** {e}")


@catub.cat_cmd(
    pattern=r"osummarize(?:\s+([\s\S]*))?$",
    command=("osummarize", plugin_category),
    info=build_osum_help(),
)
async def osummarize_cmd(event):
    """Summarize another chat silently (.osummarize)."""
    await _run_osum(event, event.pattern_match.group(1))


@catub.cat_cmd(
    pattern=r"osum(?:\s+([\s\S]*))?$",
    command=("osum", plugin_category),
    info=build_osum_help(
        header="Short alias — other-chat summarize (.osummarize)",
        note="Same as {tr}osummarize. See {tr}help osummarize for full guide.",
    ),
)
async def osum_cmd(event):
    """Short alias for .osummarize."""
    await _run_osum(event, event.pattern_match.group(1))
