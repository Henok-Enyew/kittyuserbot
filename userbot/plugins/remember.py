# Owner personal notes — .remember / .recall / .rememberlist

from userbot import catub
from userbot.ai_assistant.state import ai_state
from userbot.core.managers import edit_delete, edit_or_reply
from userbot.sql_helper import owner_notes_sql as notes_sql

plugin_category = "utils"


@catub.cat_cmd(
    pattern=r"rememberlist$",
    command=("rememberlist", plugin_category),
    info={
        "header": "List saved personal notes",
        "description": "Shows up to 20 owner notes stored in Postgres for AI recall.",
        "usage": "{tr}rememberlist",
    },
)
async def remember_list(event):
    "List owner notes."
    notes = notes_sql.list_notes(limit=20)
    if not notes:
        return await edit_delete(event, "**No notes saved yet.**")
    lines = ["**Saved notes:**\n"]
    for i, note in enumerate(notes, 1):
        lines.append(f"{i}. **{note['topic']}** — {note['content'][:120]}")
    await edit_or_reply(event, "\n".join(lines))


@catub.cat_cmd(
    pattern=r"remember delete(?:\s+(.+))?$",
    command=("remember", plugin_category),
    info={
        "header": "Delete a saved note",
        "description": "Removes a note by topic key. Also refreshes AI owner-notes cache.",
        "usage": "{tr}remember delete <topic>",
        "examples": "{tr}remember delete John",
    },
)
async def remember_delete(event):
    "Delete an owner note."
    topic = event.pattern_match.group(1)
    if not topic:
        return await edit_delete(event, "**Usage:** `.remember delete <topic>`")
    if ai_state.delete_owner_note(topic.strip()):
        return await edit_delete(event, f"**Deleted note:** `{topic.strip()}`", 5)
    await edit_delete(event, f"**No note found for:** `{topic.strip()}`")


@catub.cat_cmd(
    pattern=r"recall(?:\s+(.+))?$",
    command=("recall", plugin_category),
    info={
        "header": "Recall a saved personal note",
        "description": "Fuzzy-match a topic and return the stored note content.",
        "usage": "{tr}recall <topic>",
        "examples": ["{tr}recall John", "{tr}recall whatsapp"],
    },
)
async def recall_cmd(event):
    "Recall a saved note."
    topic = event.pattern_match.group(1)
    if not topic:
        return await edit_delete(event, "**Usage:** `.recall <topic>`")
    found = ai_state.recall_owner_note(topic.strip())
    if not found:
        return await edit_delete(event, f"**Nothing found for:** `{topic.strip()}`")
    await edit_or_reply(
        event,
        f"**{found['topic']}**\n\n{found['content']}",
    )


@catub.cat_cmd(
    pattern=r"remember(?:\s+(.+))?$",
    command=("remember", plugin_category),
    info={
        "header": "Save a personal note for AI and recall",
        "description": (
            "Stores a note in Postgres and injects it into .ask, .reply, "
            "auto-reply, and PM permit when relevant."
        ),
        "usage": "{tr}remember <topic> <note>",
        "examples": "{tr}remember John prefers WhatsApp not calls",
    },
)
async def remember_cmd(event):
    "Save a personal note."
    raw = event.pattern_match.group(1)
    if not raw or " " not in raw.strip():
        return await edit_delete(
            event,
            "**Usage:** `.remember <topic> <note>`\n"
            "**Example:** `.remember John prefers WhatsApp not calls`",
        )
    parts = raw.strip().split(None, 1)
    topic, content = parts[0], parts[1]
    ai_state.add_owner_note(topic, content)
    ai_state.reload_owner_notes()
    await edit_delete(event, f"**Saved:** `{topic}` → {content[:200]}", 6)
