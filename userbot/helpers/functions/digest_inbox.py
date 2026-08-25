# Efficient unread DM + group-mention collector for digest

from __future__ import annotations

from telethon.tl.types import Channel, Chat, User

try:
    from telethon.tl.types import InputMessagesFilterMentions
except ImportError:
    InputMessagesFilterMentions = None

from userbot.core.logger import logging

LOGS = logging.getLogger(__name__)

# Soft caps — keeps digest fast on HF / large accounts
MAX_DM_CHATS = 12
MAX_MENTION_CHATS = 10
MSGS_PER_CHAT = 3
SNIPPET_LEN = 120


def _snip(text: str) -> str:
    text = (text or "").replace("\n", " ").strip()
    if len(text) > SNIPPET_LEN:
        return text[: SNIPPET_LEN - 1] + "…"
    return text or "(media/no text)"


def _entity_name(entity) -> str:
    if isinstance(entity, User):
        return getattr(entity, "first_name", None) or "Unknown"
    return getattr(entity, "title", None) or "Chat"


async def collect_unread_inbox(
    client,
    max_dm_chats: int = MAX_DM_CHATS,
    max_mention_chats: int = MAX_MENTION_CHATS,
    msgs_per_chat: int = MSGS_PER_CHAT,
) -> dict:
    """
    Scan dialogs for unread private messages and group mentions only.
    Skips bots/channels without mentions. Soft-fails to empty inbox.
    """
    dms = []
    mentions = []
    try:
        async for dialog in client.iter_dialogs():
            if len(dms) >= max_dm_chats and len(mentions) >= max_mention_chats:
                break

            entity = dialog.entity
            unread = int(dialog.unread_count or 0)
            unread_mentions = int(dialog.unread_mentions_count or 0)

            # Private chats with unread (non-bot)
            if (
                dialog.is_user
                and unread > 0
                and len(dms) < max_dm_chats
                and isinstance(entity, User)
                and not getattr(entity, "bot", False)
                and not getattr(entity, "is_self", False)
            ):
                limit = min(unread, msgs_per_chat)
                try:
                    msgs = await client.get_messages(dialog.id, limit=limit)
                except Exception:
                    msgs = []
                message_rows = []
                for m in reversed(msgs or []):
                    if m.out:
                        continue
                    message_rows.append(
                        {
                            "name": _entity_name(entity),
                            "text": _snip(m.message or ""),
                        }
                    )
                dms.append(
                    {
                        "name": _entity_name(entity),
                        "chat_title": _entity_name(entity),
                        "unread": unread,
                        "messages": message_rows[:msgs_per_chat],
                        "extra": max(0, unread - len(message_rows)),
                    }
                )
                continue

            # Groups / megagroups with unread mentions
            is_group = dialog.is_group or (
                isinstance(entity, Channel) and getattr(entity, "megagroup", False)
            ) or isinstance(entity, Chat)
            if (
                is_group
                and unread_mentions > 0
                and len(mentions) < max_mention_chats
            ):
                limit = min(unread_mentions, msgs_per_chat)
                try:
                    if InputMessagesFilterMentions is not None:
                        msgs = await client.get_messages(
                            dialog.id,
                            limit=limit,
                            filter=InputMessagesFilterMentions(),
                        )
                    else:
                        msgs = await client.get_messages(dialog.id, limit=limit)
                except Exception:
                    try:
                        msgs = await client.get_messages(dialog.id, limit=limit)
                    except Exception:
                        msgs = []
                message_rows = []
                for m in reversed(msgs or []):
                    if m.out:
                        continue
                    sender = None
                    try:
                        sender = await m.get_sender()
                    except Exception:
                        pass
                    who = _entity_name(sender) if sender else "Someone"
                    message_rows.append(
                        {
                            "name": who,
                            "text": _snip(m.message or ""),
                        }
                    )
                mentions.append(
                    {
                        "chat_title": _entity_name(entity),
                        "unread": unread_mentions,
                        "messages": message_rows[:msgs_per_chat],
                        "extra": max(0, unread_mentions - len(message_rows)),
                    }
                )
    except Exception as e:
        LOGS.error(f"collect_unread_inbox failed: {e}")
        return {"dms": [], "mentions": []}

    return {"dms": dms, "mentions": mentions}
