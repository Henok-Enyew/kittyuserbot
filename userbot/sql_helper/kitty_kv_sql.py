# Key-value store for plugin state that can grow large (JSON blobs, caches).
#
# The legacy `globals` table uses (variable, value) as its PRIMARY KEY, so Postgres
# indexes every value and rejects anything over ~2.7 KB ("index row size exceeds
# btree maximum"). Here only the key is indexed, so values can be any size.

import json

from sqlalchemy import Column, String, UnicodeText

from . import BASE, SESSION
from .globals import gvarstatus


class KittyKV(BASE):
    __tablename__ = "kitty_kv"
    variable = Column(String, primary_key=True, nullable=False)
    value = Column(UnicodeText, nullable=True)

    def __init__(self, variable, value):
        self.variable = str(variable)
        self.value = value


KittyKV.__table__.create(checkfirst=True)

_MISSING = object()


def kv_get(key: str, default=None):
    """Raw string value; falls back to the old `globals` table for values saved before."""
    try:
        row = SESSION.query(KittyKV).get(str(key))
        if row is not None:
            return row.value
    except Exception:
        SESSION.rollback()
    finally:
        SESSION.close()
    legacy = gvarstatus(key)
    return default if legacy is None else legacy


def kv_set(key: str, value: str):
    try:
        row = SESSION.query(KittyKV).get(str(key))
        if row is None:
            SESSION.add(KittyKV(str(key), value))
        else:
            row.value = value
        SESSION.commit()
    except Exception:
        SESSION.rollback()
        raise
    finally:
        SESSION.close()


def kv_del(key: str):
    try:
        SESSION.query(KittyKV).filter(KittyKV.variable == str(key)).delete(synchronize_session=False)
        SESSION.commit()
    except Exception:
        SESSION.rollback()
        raise
    finally:
        SESSION.close()


def kv_get_json(key: str, default=None):
    raw = kv_get(key, _MISSING)
    if raw is _MISSING or raw is None:
        return default
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return default


def kv_set_json(key: str, obj):
    kv_set(key, json.dumps(obj, ensure_ascii=False, separators=(",", ":")))
