# Portfolio / hire-me business card

import contextlib
import os
import re

import requests
from telethon import Button, events
from telethon.tl.types import User

from userbot import catub
from userbot.Config import Config
from userbot.core.logger import logging

from ..core.managers import edit_delete, edit_or_reply
from ..helpers.functions.portfolio_data import PORTFOLIO, build_portfolio_html
from ..helpers.utils import reply_id
from ..sql_helper.globals import addgvar, gvarstatus

plugin_category = "utils"
LOGS = logging.getLogger(__name__)


def _hire_open() -> bool:
    val = gvarstatus("HIREME_OPEN") or "false"
    return str(val).lower() in ("true", "1", "yes", "on")


def _resume_url() -> str | None:
    return getattr(Config, "PORTFOLIO_RESUME_URL", None) or None


def _portfolio_buttons():
    row = [
        Button.url("Portfolio", PORTFOLIO["links"]["Portfolio"]),
        Button.url("GitHub", PORTFOLIO["links"]["GitHub"]),
        Button.url("LinkedIn", PORTFOLIO["links"]["LinkedIn"]),
    ]
    resume = _resume_url()
    if resume:
        row.append(Button.url("Resume", resume))
    return row


def _extract_gdrive_id(url: str) -> str | None:
    match = re.search(r"/file/d/([^/]+)", url)
    if match:
        return match.group(1)
    match = re.search(r"[?&]id=([^&]+)", url)
    return match.group(1) if match else None


def _download_resume(url: str, out_dir: str = "./temp") -> str | None:
    """Download resume from Google Drive or direct URL. Returns local path or None."""
    os.makedirs(out_dir, exist_ok=True)
    session = requests.Session()
    try:
        file_id = _extract_gdrive_id(url)
        if file_id:
            base = f"https://drive.google.com/uc?export=download&id={file_id}"
            resp = session.get(base, stream=True, timeout=30)
            for key, value in resp.cookies.items():
                if key.startswith("download_warning"):
                    resp = session.get(
                        f"{base}&confirm={value}",
                        stream=True,
                        timeout=60,
                    )
                    break
        else:
            resp = session.get(url, stream=True, timeout=30, allow_redirects=True)

        if not resp.ok:
            return None

        ctype = resp.headers.get("Content-Disposition", "")
        ext = ".pdf"
        fn_match = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)', ctype)
        if fn_match:
            fname = fn_match.group(1).strip()
            _, ext_part = os.path.splitext(fname)
            if ext_part:
                ext = ext_part

        out_path = os.path.join(out_dir, f"resume{ext}")
        with open(out_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            return out_path
    except Exception as e:
        LOGS.debug(f"resume download failed: {e}")
    return None


async def _fetch_og_image(url: str):
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if not resp.ok:
            return None
        match = re.search(
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',
            resp.text,
            re.I,
        )
        if not match:
            match = re.search(
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image',
                resp.text,
                re.I,
            )
        return match.group(1) if match else None
    except Exception:
        return None


async def _send_card(
    client,
    chat_id,
    show_hire_status: bool = False,
    reply_to=None,
):
    """Send polished portfolio card; attach resume document when downloadable."""
    resume_url = _resume_url()
    text = build_portfolio_html(
        hire_open=_hire_open(),
        show_hire_status=show_hire_status,
        resume_url=resume_url,
    )
    buttons = _portfolio_buttons()
    resume_path = None
    cleanup = []

    if resume_url:
        resume_path = _download_resume(resume_url)
        if resume_path:
            cleanup.append(resume_path)

    try:
        if resume_path:
            await client.send_file(
                chat_id,
                resume_path,
                caption=text,
                parse_mode="html",
                buttons=buttons,
                reply_to=reply_to,
            )
            return

        thumb = await _fetch_og_image(PORTFOLIO["portfolio_url"])
        if thumb:
            with contextlib.suppress(Exception):
                await client.send_file(
                    chat_id,
                    thumb,
                    caption=text,
                    parse_mode="html",
                    buttons=buttons,
                    reply_to=reply_to,
                    link_preview=False,
                )
                return

        await client.send_message(
            chat_id,
            text,
            parse_mode="html",
            buttons=buttons,
            reply_to=reply_to,
            link_preview=False,
        )
    finally:
        for path in cleanup:
            if path and os.path.exists(path):
                os.remove(path)


async def _send_card_event(event, show_hire_status: bool = False):
    reply_to = await reply_id(event)
    await _send_card(
        event.client,
        event.chat_id,
        show_hire_status=show_hire_status,
        reply_to=reply_to,
    )


async def _is_brand_new_pm(event) -> bool:
    """True only when chat history is exactly this one incoming message."""
    try:
        msgs = await event.client.get_messages(event.chat_id, limit=2)
    except Exception:
        return False
    if len(msgs) != 1:
        return False
    return msgs[0].id == event.message.id


@catub.on(events.NewMessage(incoming=True))
async def portfolio_auto_greet(event):
    """Send portfolio card to brand-new PM strangers (zero prior chat history)."""
    if not getattr(Config, "PORTFOLIO_AUTO_GREET", False):
        return
    if not event.is_private:
        return
    sender = await event.get_sender()
    if not sender or not isinstance(sender, User) or sender.bot:
        return
    if getattr(sender, "is_self", False):
        return
    text = (event.message.message or "").strip()
    if not text:
        return
    if not await _is_brand_new_pm(event):
        return
    try:
        await _send_card(event.client, event.chat_id, show_hire_status=True)
        LOGS.info(f"Portfolio auto-greet sent to user {sender.id}")
    except Exception as e:
        LOGS.error(f"Portfolio auto-greet failed: {e}")


@catub.cat_cmd(
    pattern=r"portfolio$",
    command=("portfolio", plugin_category),
    info={
        "header": "Share Henok's portfolio card",
        "description": (
            "Sends a polished HTML business card with project links and inline buttons."
            + " Set PORTFOLIO_RESUME_URL to attach or link a resume."
        ),
        "usage": "{tr}portfolio",
        "examples": "{tr}portfolio",
    },
)
async def portfolio_cmd(event):
    "Send portfolio business card."
    await edit_or_reply(event, "**Loading portfolio...**")
    await _send_card_event(event, show_hire_status=False)
    with contextlib.suppress(Exception):
        await event.delete()


@catub.cat_cmd(
    pattern=r"hireme(?:\s+(on|off))?$",
    command=("hireme", plugin_category),
    info={
        "header": "Portfolio card with hire-me status",
        "description": (
            "Shows portfolio card with open/closed hire status."
            + " Use on/off to toggle. Resume attached when PORTFOLIO_RESUME_URL is set."
        ),
        "usage": ["{tr}hireme", "{tr}hireme on", "{tr}hireme off"],
        "examples": ["{tr}hireme", "{tr}hireme on"],
    },
)
async def hireme_cmd(event):
    "Portfolio card with optional hire-me toggle."
    arg = (event.pattern_match.group(1) or "").strip().lower()
    if arg == "on":
        addgvar("HIREME_OPEN", "true")
        return await edit_delete(event, "**Hire-me status:** Open to opportunities", 5)
    if arg == "off":
        addgvar("HIREME_OPEN", "false")
        return await edit_delete(event, "**Hire-me status:** Not actively looking", 5)
    await edit_or_reply(event, "**Loading card...**")
    await _send_card_event(event, show_hire_status=True)
    with contextlib.suppress(Exception):
        await event.delete()
