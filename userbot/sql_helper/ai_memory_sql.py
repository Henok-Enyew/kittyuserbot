# AI Memory SQL Helper
# Persists chat history, style examples, and friend memory across restarts.

from sqlalchemy import Column, Integer, String, UnicodeText

from . import BASE, SESSION


class AiChatHistory(BASE):
    __tablename__ = "ai_chat_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(String(32), nullable=False, index=True)
    role = Column(String(16), nullable=False)
    content = Column(UnicodeText, nullable=False)

    def __init__(self, chat_id, role, content):
        self.chat_id = str(chat_id)
        self.role = role
        self.content = content


class AiStyleExample(BASE):
    __tablename__ = "ai_style_examples"
    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(UnicodeText, nullable=False)

    def __init__(self, content):
        self.content = content


class AiFriendMemory(BASE):
    __tablename__ = "ai_friend_memory"
    name_key = Column(String(64), primary_key=True)
    name = Column(UnicodeText, nullable=False)
    note = Column(UnicodeText)

    def __init__(self, name_key, name, note=None):
        self.name_key = name_key
        self.name = name
        self.note = note or ""


try:
    AiChatHistory.__table__.create(checkfirst=True)
    AiStyleExample.__table__.create(checkfirst=True)
    AiFriendMemory.__table__.create(checkfirst=True)
except Exception:
    pass


# ── Chat history ─────────────────────────────────────────────────────────────


def load_all_history(max_per_chat: int = 10) -> dict:
    """Return {chat_id_int: [{"role", "content"}, ...]} limited per chat."""
    result = {}
    try:
        rows = (
            SESSION.query(AiChatHistory)
            .order_by(AiChatHistory.id.asc())
            .all()
        )
        by_chat = {}
        for row in rows:
            cid = str(row.chat_id)
            by_chat.setdefault(cid, []).append(
                {"role": row.role, "content": row.content}
            )
        for cid, msgs in by_chat.items():
            trimmed = msgs[-max_per_chat:]
            try:
                result[int(cid)] = trimmed
            except ValueError:
                result[cid] = trimmed
        return result
    except Exception:
        return {}
    finally:
        SESSION.close()


def append_history(chat_id, role: str, content: str, max_per_chat: int = 10):
    """Append one message and trim oldest rows for that chat."""
    try:
        SESSION.add(AiChatHistory(str(chat_id), role, content))
        SESSION.commit()
        rows = (
            SESSION.query(AiChatHistory)
            .filter(AiChatHistory.chat_id == str(chat_id))
            .order_by(AiChatHistory.id.asc())
            .all()
        )
        if len(rows) > max_per_chat:
            for old in rows[: len(rows) - max_per_chat]:
                SESSION.delete(old)
            SESSION.commit()
        return True
    except Exception:
        try:
            SESSION.rollback()
        except Exception:
            pass
        return False
    finally:
        SESSION.close()


def clear_history_db(chat_id) -> bool:
    try:
        SESSION.query(AiChatHistory).filter(
            AiChatHistory.chat_id == str(chat_id)
        ).delete(synchronize_session="fetch")
        SESSION.commit()
        return True
    except Exception:
        try:
            SESSION.rollback()
        except Exception:
            pass
        return False
    finally:
        SESSION.close()


# ── Style examples ───────────────────────────────────────────────────────────


def load_style_examples(limit: int = 20) -> list:
    try:
        rows = (
            SESSION.query(AiStyleExample)
            .order_by(AiStyleExample.id.asc())
            .all()
        )
        return [r.content for r in rows[-limit:]]
    except Exception:
        return []
    finally:
        SESSION.close()


def append_style_example(content: str, max_examples: int = 20) -> bool:
    try:
        SESSION.add(AiStyleExample(content))
        SESSION.commit()
        rows = (
            SESSION.query(AiStyleExample)
            .order_by(AiStyleExample.id.asc())
            .all()
        )
        if len(rows) > max_examples:
            for old in rows[: len(rows) - max_examples]:
                SESSION.delete(old)
            SESSION.commit()
        return True
    except Exception:
        try:
            SESSION.rollback()
        except Exception:
            pass
        return False
    finally:
        SESSION.close()


# ── Friend memory ────────────────────────────────────────────────────────────


def load_friends(limit: int = 30) -> list:
    """Return list of {"name", "note"} dicts."""
    try:
        rows = SESSION.query(AiFriendMemory).all()
        friends = [{"name": r.name, "note": r.note or ""} for r in rows]
        return friends[:limit]
    except Exception:
        return []
    finally:
        SESSION.close()


def upsert_friend(name: str, note: str = "", max_friends: int = 30) -> bool:
    if not name or not name.strip():
        return False
    key = name.strip().lower()
    display = name.strip().title() if name.strip().islower() else name.strip()
    try:
        existing = SESSION.query(AiFriendMemory).get(key)
        if existing:
            existing.name = display
            if note:
                existing.note = note
            SESSION.commit()
            return True
        count = SESSION.query(AiFriendMemory).count()
        if count >= max_friends:
            oldest = SESSION.query(AiFriendMemory).first()
            if oldest:
                SESSION.delete(oldest)
                SESSION.commit()
        SESSION.add(AiFriendMemory(key, display, note or ""))
        SESSION.commit()
        return True
    except Exception:
        try:
            SESSION.rollback()
        except Exception:
            pass
        return False
    finally:
        SESSION.close()


def delete_friend(name: str) -> bool:
    if not name:
        return False
    key = name.strip().lower()
    try:
        rem = SESSION.query(AiFriendMemory).get(key)
        if not rem:
            return False
        SESSION.delete(rem)
        SESSION.commit()
        return True
    except Exception:
        try:
            SESSION.rollback()
        except Exception:
            pass
        return False
    finally:
        SESSION.close()
