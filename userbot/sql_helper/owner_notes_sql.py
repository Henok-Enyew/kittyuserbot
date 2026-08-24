# Owner personal notes — persisted for .remember / .recall and AI injection

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, UnicodeText

from . import BASE, SESSION


class OwnerNote(BASE):
    __tablename__ = "owner_notes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    topic_key = Column(String(128), nullable=False, index=True)
    topic = Column(UnicodeText, nullable=False)
    content = Column(UnicodeText, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __init__(self, topic_key, topic, content):
        self.topic_key = topic_key
        self.topic = topic
        self.content = content


try:
    OwnerNote.__table__.create(checkfirst=True)
except Exception:
    pass


def _normalize_key(topic: str) -> str:
    return (topic or "").strip().lower()


def upsert_note(topic: str, content: str, max_notes: int = 100) -> bool:
    key = _normalize_key(topic)
    if not key or not content:
        return False
    try:
        row = SESSION.query(OwnerNote).filter(OwnerNote.topic_key == key).first()
        if row:
            row.content = content
            row.topic = topic.strip()
        else:
            SESSION.add(OwnerNote(key, topic.strip(), content.strip()))
        SESSION.commit()
        _trim_notes(max_notes)
        return True
    except Exception:
        return False
    finally:
        SESSION.close()


def _trim_notes(max_notes: int):
    try:
        count = SESSION.query(OwnerNote).count()
        if count <= max_notes:
            return
        oldest = (
            SESSION.query(OwnerNote)
            .order_by(OwnerNote.id.asc())
            .limit(count - max_notes)
            .all()
        )
        for row in oldest:
            SESSION.delete(row)
        SESSION.commit()
    except Exception:
        pass
    finally:
        SESSION.close()


def delete_note(topic: str) -> bool:
    key = _normalize_key(topic)
    if not key:
        return False
    try:
        deleted = (
            SESSION.query(OwnerNote).filter(OwnerNote.topic_key == key).delete()
        )
        SESSION.commit()
        return deleted > 0
    except Exception:
        return False
    finally:
        SESSION.close()


def find_note(topic: str):
    key = _normalize_key(topic)
    if not key:
        return None
    try:
        row = SESSION.query(OwnerNote).filter(OwnerNote.topic_key == key).first()
        if row:
            return {"topic": row.topic, "content": row.content}
        rows = SESSION.query(OwnerNote).all()
        for row in rows:
            if key in row.topic_key or key in row.topic.lower():
                return {"topic": row.topic, "content": row.content}
        return None
    except Exception:
        return None
    finally:
        SESSION.close()


def list_notes(limit: int = 50) -> list:
    try:
        rows = (
            SESSION.query(OwnerNote)
            .order_by(OwnerNote.id.desc())
            .limit(limit)
            .all()
        )
        return [{"topic": r.topic, "content": r.content} for r in rows]
    except Exception:
        return []
    finally:
        SESSION.close()


def load_owner_notes(limit: int = 50) -> list:
    return list_notes(limit)
