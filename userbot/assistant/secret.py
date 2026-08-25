# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~# CatUserBot #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
# Copyright (C) 2020-2023 by TgCatUB@Github.

# This file is part of: https://github.com/TgCatUB/catuserbot
# and is released under the "GNU v3.0 License Agreement".

# Please see: https://github.com/TgCatUB/catuserbot/blob/master/LICENSE
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

import re

from telethon.events import CallbackQuery

from userbot import catub
from userbot.assistant.whisper_store import get_whisper

# Telegram callback alert hard limit
_ALERT_LIMIT = 200


def _fit_alert(text: str) -> str:
    text = text or ""
    if len(text) <= _ALERT_LIMIT:
        return text
    return text[: _ALERT_LIMIT - 1].rstrip() + "…"


@catub.tgbot.on(CallbackQuery(data=re.compile(b"secret_(.*)")))
async def on_plug_in_callback_query_handler(event):
    timestamp = event.pattern_match.group(1).decode("UTF-8")
    message = get_whisper("secret", timestamp)
    if not message:
        return await event.answer(
            "This message no longer exists", cache_time=0, alert=True
        )
    userid = message.get("userid") or []
    ids = list(userid) + [catub.uid]
    if event.query.user_id in ids:
        reply_pop_up_alert = _fit_alert(message.get("text") or "")
    else:
        reply_pop_up_alert = "This secret is not for you."
    await event.answer(reply_pop_up_alert, cache_time=0, alert=True)
