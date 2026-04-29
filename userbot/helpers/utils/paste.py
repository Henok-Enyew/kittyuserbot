# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~# CatUserBot #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
# Copyright (C) 2020-2023 by TgCatUB@Github.

# This file is part of: https://github.com/TgCatUB/catuserbot
# and is released under the "GNU v3.0 License Agreement".

# Please see: https://github.com/TgCatUB/catuserbot/blob/master/LICENSE
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

import json

import requests

from ...Config import Config
from ...core.logger import logging

LOGS = logging.getLogger("CatUserbot")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.104 Safari/537.36",
    "content-type": "application/json",
}


async def p_paste(message, extension=None):
    """
    To Paste the given message/text/code to paste.rs
    """
    try:
        response = requests.post(
            "https://paste.rs/",
            data=message.encode("utf-8"),
            headers={"Content-Type": "text/plain; charset=utf-8"},
            timeout=10,
        )
    except Exception as e:
        return {"error": str(e)}
    if response.status_code == 201:
        purl = response.text.strip()
        return {
            "url": purl,
            "raw": purl,
            "bin": "paste.rs",
        }
    return {"error": f"paste.rs returned {response.status_code}"}


async def s_paste(message, extension="txt"):
    """
    To Paste the given message/text/code to dpaste.com
    """
    try:
        response = requests.post(
            "https://dpaste.com/api/v2/",
            data={"content": message, "syntax": "text", "expiry_days": 7},
            timeout=10,
        )
    except Exception as e:
        return {"error": str(e)}
    if response.status_code == 201:
        purl = response.text.strip().strip('"')
        return {
            "url": purl,
            "raw": purl + ".txt",
            "bin": "dpaste",
        }
    return {"error": f"dpaste returned {response.status_code}"}


def spaste(message, extension="txt"):
    """
    To Paste the given message/text/code to dpaste.com (sync version)
    """
    try:
        response = requests.post(
            "https://dpaste.com/api/v2/",
            data={"content": message, "syntax": "text", "expiry_days": 7},
            timeout=10,
        )
    except Exception as e:
        return {"error": str(e)}
    if response.status_code == 201:
        purl = response.text.strip().strip('"')
        return {
            "url": purl,
            "raw": purl + ".txt",
            "bin": "dpaste",
        }
    return {"error": f"dpaste returned {response.status_code}"}


async def n_paste(message, extension=None):
    """
    To Paste the given message/text/code to paste.rs (fallback)
    """
    return await p_paste(message, extension)


async def d_paste(message, extension=None):
    """
    To Paste the given message/text/code to dpaste.com
    """
    return await s_paste(message, extension)


async def pastetext(text_to_print, pastetype=None, extension=None):
    response = {"error": "something went wrong"}
    if pastetype is not None:
        if pastetype == "p":
            response = await p_paste(text_to_print, extension)
        elif pastetype == "s" and extension:
            response = await s_paste(text_to_print, extension)
        elif pastetype == "s":
            response = await s_paste(text_to_print)
        elif pastetype == "d":
            response = await d_paste(text_to_print, extension)
        elif pastetype == "n":
            response = await n_paste(text_to_print, extension)
    if "error" in response:
        response = await p_paste(text_to_print, extension)
    if "error" in response:
        response = await n_paste(text_to_print, extension)
    if "error" in response:
        if extension:
            response = await s_paste(text_to_print, extension)
        else:
            response = await s_paste(text_to_print)
    if "error" in response:
        response = await d_paste(text_to_print, extension)
    return response
