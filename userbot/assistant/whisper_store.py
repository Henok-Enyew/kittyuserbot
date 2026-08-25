# Shared in-memory + file store for secret / hide / troll whispers

import json
import os

_WHISPER_CACHE: dict[str, dict] = {"secret": {}, "hide": {}, "troll": {}}


def put_whisper(kind: str, timestamp, data: dict) -> None:
    _WHISPER_CACHE.setdefault(kind, {})[str(timestamp)] = data


def get_whisper(kind: str, timestamp: str):
    cached = _WHISPER_CACHE.get(kind, {}).get(str(timestamp))
    if cached:
        return cached
    path = os.path.join("./userbot", f"{kind}.txt")
    if not os.path.exists(path):
        return None
    try:
        data = json.load(open(path))
        return data.get(str(timestamp))
    except Exception:
        return None
