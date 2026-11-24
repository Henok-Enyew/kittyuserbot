# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~# CatUserBot #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
# Copyright (C) 2020-2023 by TgCatUB@Github.

# This file is part of: https://github.com/TgCatUB/catuserbot
# and is released under the "GNU v3.0 License Agreement".

# Please see: https://github.com/TgCatUB/catuserbot/blob/master/LICENSE
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

import sys
import time

from telethon.errors import (
    AccessTokenExpiredError,
    AccessTokenInvalidError,
    RpcCallFailError,
)
from telethon.network.connection.tcpabridged import ConnectionTcpAbridged
from telethon.sessions import StringSession

from ..Config import Config
from .client import CatUserBotClient

__version__ = "3.3.0"

loop = None

if Config.STRING_SESSION:
    session = StringSession(str(Config.STRING_SESSION))
else:
    session = "catuserbot"

try:
    catub = CatUserBotClient(
        session=session,
        api_id=Config.APP_ID,
        api_hash=Config.API_HASH,
        loop=loop,
        app_version=__version__,
        connection=ConnectionTcpAbridged,
        auto_reconnect=True,
        connection_retries=None,
    )
except Exception as e:
    print(f"STRING_SESSION - {e}")
    sys.exit()


catub.tgbot = tgbot = CatUserBotClient(
    session="CatTgbot",
    api_id=Config.APP_ID,
    api_hash=Config.API_HASH,
    loop=loop,
    app_version=__version__,
    connection=ConnectionTcpAbridged,
    auto_reconnect=True,
    connection_retries=None,
)


def _start_assistant_bot(client, token, attempts=8):
    """Log the assistant bot in, waiting out Telegram-side hiccups.

    Telethon gives up after 6 quick retries when Telegram answers
    ``RpcCallFailError`` ("Telegram is having internal issues"). On a host that
    restarts the container on every crash (Hugging Face, Heroku...) that turns
    into a restart loop of fresh logins, which makes Telegram even less willing
    to accept the token. Back off instead, and stop for good when the token is
    actually invalid.
    """
    delay = 30
    for attempt in range(1, attempts + 1):
        try:
            return client.start(bot_token=token)
        except (AccessTokenInvalidError, AccessTokenExpiredError) as e:
            print(
                f"TG_BOT_TOKEN rejected by Telegram ({e.__class__.__name__}). "
                "Get a fresh token from @BotFather and update the config."
            )
            sys.exit(1)
        except (ValueError, RpcCallFailError, ConnectionError, OSError) as e:
            if attempt == attempts:
                raise
            print(
                f"Assistant bot login failed ({e}); retry {attempt}/{attempts - 1} "
                f"in {delay}s..."
            )
            time.sleep(delay)
            delay = min(delay * 2, 300)


_start_assistant_bot(tgbot, Config.TG_BOT_TOKEN)
