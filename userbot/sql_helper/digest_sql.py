# Digest PM log — ring buffer while owner is AFK

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, UnicodeText

from . import BASE, SESSION

MAX_PM_LOG = 50


class DigestPmLog(BASE):
    __tablename__ = "digest_pm_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(32), nullable=False)
    name = Column(UnicodeText, nullable=False)
    snippet = Column(UnicodeText, nullable=False)
    logged_at = Column(DateTime, default=datetime.utcnow)


try:
    DigestPmLog.__table__.create(checkfirst=True)
except Exception:
    pass


def log_pm(user_id, name: str, snippet: str):
    try:
        SESSION.add(
            DigestPmLog(
                str(user_id),
                (name or "Unknown")[:128],
                (snippet or "")[:500],
            )
        )
        SESSION.commit()
        count = SESSION.query(DigestPmLog).count()
        if count > MAX_PM_LOG:
            oldest = (
                SESSION.query(DigestPmLog)
                .order_by(DigestPmLog.id.asc())
                .limit(count - MAX_PM_LOG)
                .all()
            )
            for row in oldest:
                SESSION.delete(row)
            SESSION.commit()
    except Exception:
        pass
    finally:
        SESSION.close()


def get_pm_log_since(clear_after: bool = False) -> list:
    try:
        rows = (
            SESSION.query(DigestPmLog)
            .order_by(DigestPmLog.id.desc())
            .limit(MAX_PM_LOG)
            .all()
        )
        result = [
            {
                "user_id": r.user_id,
                "name": r.name,
                "snippet": r.snippet,
                "logged_at": r.logged_at,
            }
            for r in reversed(rows)
        ]
        if clear_after and rows:
            SESSION.query(DigestPmLog).delete()
            SESSION.commit()
        return result
    except Exception:
        return []
    finally:
        SESSION.close()


def pm_log_count() -> int:
    try:
        return SESSION.query(DigestPmLog).count()
    except Exception:
        return 0
    finally:
        SESSION.close()
