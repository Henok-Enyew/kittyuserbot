# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~# CatUserBot #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
# Copyright (C) 2020-2023 by TgCatUB@Github.

# This file is part of: https://github.com/TgCatUB/catuserbot
# and is released under the "GNU v3.0 License Agreement".

# Please see: https://github.com/TgCatUB/catuserbot/blob/master/LICENSE
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

import asyncio
import json
import math
import os
import random
import re
import time
from pathlib import Path

from telethon import Button, types
from telethon.errors.rpcerrorlist import QueryIdInvalidError
from telethon.events import CallbackQuery, InlineQuery

from userbot import catub

from ..assistant.inlinefm import get_manager
from ..assistant.whisper_store import put_whisper
from ..Config import Config
from ..helpers.functions import rand_key
from ..helpers.functions.utube import (
    _fast_download_buttons,
    get_yt_video_id,
    get_ytthumb,
    result_formatter,
    videos_search,
    ytsearch_data,
)
from ..plugins import mention
from ..sql_helper.globals import gvarstatus
from . import CMD_INFO, GRP_INFO, PLG_INFO, check_owner
from .cmdinfo import cmdinfo, get_key, getkey, plugininfo
from .logger import logging

LOGS = logging.getLogger(__name__)
tr = Config.COMMAND_HAND_LER


def get_thumb(name=None, url=None):
    if url is None:
        url = f"https://github.com/TgCatUB/CatUserbot-Resources/blob/master/Resources/Inline/{name}?raw=true"
    return types.InputWebDocument(
        url=url, size=0, mime_type="image/jpeg", attributes=[]
    )


def main_menu():
    text = f"𝗖𝗮𝘁𝗨𝘀𝗲𝗿𝗯𝗼𝘁 𝗛𝗲𝗹𝗽𝗲𝗿\
        \n𝗣𝗿𝗼𝘃𝗶𝗱𝗲𝗱 𝗯𝘆 {mention}"
    buttons = [
        (Button.inline("ℹ️ Info", data="check"),),
        (
            Button.inline(f"👮‍♂️ Admin ({len(GRP_INFO['admin'])})", data="admin_menu"),
            Button.inline(f"🤖 Bot ({len(GRP_INFO['bot'])})", data="bot_menu"),
        ),
        (
            Button.inline(f"🎨 Fun ({len(GRP_INFO['fun'])})", data="fun_menu"),
            Button.inline(f"🧩 Misc ({len(GRP_INFO['misc'])})", data="misc_menu"),
        ),
        (
            Button.inline(f"🧰 Tools ({len(GRP_INFO['tools'])})", data="tools_menu"),
            Button.inline(f"🗂 Utils ({len(GRP_INFO['utils'])})", data="utils_menu"),
        ),
        (
            Button.inline(f"➕ Extra ({len(GRP_INFO['extra'])})", data="extra_menu"),
            Button.inline("🔒 Close Menu", data="close"),
        ),
    ]
    if Config.BADCAT:
        switch_button = [
            (
                Button.inline(f"➕ Extra ({len(GRP_INFO['extra'])})", data="extra_menu"),
                Button.inline(
                    f"⚰️ Useless ({len(GRP_INFO['useless'])})", data="useless_menu"
                ),
            ),
            (Button.inline("🔒 Close Menu", data="close"),),
        ]
        buttons = buttons[:-1] + switch_button

    return text, buttons


async def build_article(
    event,
    media=None,
    title=None,
    text=None,
    description=None,
    buttons=None,
    thumbnail=None,
    parse_mode="md",
    link_preview=False,
):
    builder = event.builder
    photo_document = None
    if media:
        if not media.endswith((".jpg", ".jpeg", ".png")):
            # Return a document object with the provided media URL
            return builder.document(
                media,
                title=title,
                description=description,
                text=text,
                buttons=buttons,
            )
        # Create an InputWebDocument object for the media file
        photo_document = get_thumb(url=media)
    if thumbnail and isinstance(thumbnail, str):
        thumbnail = get_thumb(url=thumbnail)
    # Return an article object with the provided properties
    return builder.article(
        title=title,
        description=description,
        type="photo" if photo_document else "article",
        file=media,
        thumb=thumbnail or photo_document,
        content=photo_document,
        text=text,
        buttons=buttons,
        link_preview=link_preview,
        parse_mode=parse_mode,
    )


async def help_article(event):
    help_info = main_menu()
    return await build_article(
        event,
        title="Help Menu",
        description="Help menu for CatUserbot.",
        thumbnail=get_thumb("help.png"),
        text=help_info[0],
        buttons=help_info[1],
    )


async def filemanager_article(event):
    try:
        _, path_ = (event.text).split(" ", 1)
        path = Path(path_) if path_ else os.getcwd()
    except Exception:
        path = os.getcwd()
    if not os.path.exists(path):
        return
    query, buttons = get_manager(path, 1)
    return await build_article(
        event,
        title="File Manager",
        description=f"Inline file manager\nSyntax: ls (path optional)\nPath:  {path}",
        thumbnail=get_thumb("filemanager.jpg"),
        media="https://github.com/TgCatUB/CatUserbot-Resources/raw/master/Resources/Inline/filemanager.jpg",
        text=query,
        buttons=buttons,
    )


KITTY_REPO = "https://github.com/Henok-Enyew/kittyuserbot"


async def deploy_article(event):
    buttons = [
        (
            Button.url("Source code", KITTY_REPO),
            Button.url("GitHub", KITTY_REPO),
        )
    ]
    return await build_article(
        event,
        title="KittyUserbot",
        description="Get the source on GitHub.",
        media="https://github.com/TgCatUB/CatUserbot-Resources/raw/master/Resources/Inline/catlogo.png",
        text="𝗗𝗲𝗽𝗹𝗼𝘆 𝘆𝗼𝘂𝗿 𝗼𝘄𝗻 𝗞𝗶𝘁𝘁𝘆𝗨𝘀𝗲𝗿𝗯𝗼𝘁.\n\n"
        f"[Henok-Enyew/kittyuserbot]({KITTY_REPO})",
        buttons=buttons,
    )


async def pmpermit_article(event):
    buttons = [Button.inline(text="Show Options.", data="show_pmpermit_options")]
    query = gvarstatus("PM_TEXT")
    media = None
    if PM_PIC := gvarstatus("PM_PIC"):
        CAT = list(PM_PIC.split())
        PIC = list(CAT)
        media = random.choice(PIC)
    return await build_article(
        event,
        media=media,
        text=query,
        buttons=buttons,
    )


async def age_verification_article(event):
    buttons = [
        Button.inline(text="Yes I'm 18+", data="age_verification_true"),
        Button.inline(text="No I'm Not", data="age_verification_false"),
    ]
    return await build_article(
        event,
        title="Age verification",
        text="**ARE YOU OLD ENOUGH FOR THIS ?**",
        buttons=buttons,
        media="https://i.imgur.com/Zg58iXc.jpg",
    )


async def vcplayer_article(event):
    try:
        from catvc.helper.function import vc_player
        from catvc.helper.inlinevc import buttons, vcimg

        text = "** | VC Menu | **"
        buttons = buttons[0]
        if play := vc_player.PLAYING:
            vcimg = play["img"]
            text = f"**🎧 Playing:** [{play['title']}]({play['url']})\n"
            text += f"**⏳ Duration:** `{play['duration']}`\n"
            text += f"**💭 Chat:** `{vc_player.CHAT_NAME}`"
            buttons = buttons[1]

        return await build_article(
            event,
            title="CatVc Player",
            media=vcimg,
            text=text,
            description="Manange Vc Stream.",
            buttons=buttons,
            thumbnail="https://github.com/TgCatUB/CatUserbot-Resources/raw/master/Resources/Inline/vcplayer.jpg",
        )
    except Exception:
        return None


async def article_builder(event, method):
    media = thumb = None
    title = "Cat Userbot"
    description = "Button menu for CatUserbot"
    if method == "ialive":
        buttons = [
            (
                Button.inline("Stats", data="stats"),
                Button.url("Repo", "https://github.com/Henok-Enyew/kittyuserbot"),
            )
        ]
        try:
            from userbot.plugins.alive import catalive_text

            query = catalive_text()
        except Exception:
            return None
        title = "Cat Alive"
        thumb = get_thumb("alive.png")
        description = "Alive menu for CatUserbot."
        ALIVE_PIC = gvarstatus("ALIVE_PIC")
        IALIVE_PIC = gvarstatus("IALIVE_PIC")
        if IALIVE_PIC:
            CAT = list(IALIVE_PIC.split())
            PIC = list(CAT)
            media = random.choice(PIC)
        if not IALIVE_PIC and ALIVE_PIC:
            CAT = list(ALIVE_PIC.split())
            PIC = list(CAT)
            media = random.choice(PIC)

    elif method == "spotify":
        try:
            from userbot.plugins.spotify import spotify_inline_article

            (
                query,
                buttons,
                media,
                thumb,
                title,
                description,
            ) = await spotify_inline_article()
        except Exception:
            return None

    elif method.startswith("Inline buttons"):
        from userbot.plugins.button import inline_button_aricle

        query, buttons, media = inline_button_aricle(method)

    return await build_article(
        event,
        title=title,
        text=query,
        buttons=buttons,
        description=description,
        media=media,
        thumbnail=thumb,
    )


def command_in_category(cname):
    cmds = 0
    for i in GRP_INFO[cname]:
        for _ in PLG_INFO[i]:
            cmds += 1
    return cmds


def paginate_help(
    page_number,
    loaded_plugins,
    prefix,
    plugins=True,
    category_plugins=None,
    category_pgno=0,
):  # sourcery no-metrics  # sourcery skip: low-code-quality
    try:
        number_of_rows = int(gvarstatus("NO_OF_ROWS_IN_HELP") or 5)
    except (ValueError, TypeError):
        number_of_rows = 5
    try:
        number_of_cols = int(gvarstatus("NO_OF_COLUMNS_IN_HELP") or 2)
    except (ValueError, TypeError):
        number_of_cols = 2
    HELP_EMOJI = gvarstatus("HELP_EMOJI") or " "
    helpable_plugins = [p for p in loaded_plugins if not p.startswith("_")]
    helpable_plugins = sorted(helpable_plugins)
    if len(HELP_EMOJI) == 2:
        if plugins:
            modules = [
                Button.inline(
                    f"{HELP_EMOJI[0]} {x} {HELP_EMOJI[1]}",
                    data=f"{x}_prev(1)_command_{prefix}_{page_number}",
                )
                for x in helpable_plugins
            ]
        else:
            modules = [
                Button.inline(
                    f"{HELP_EMOJI[0]} {x} {HELP_EMOJI[1]}",
                    data=f"{x}_cmdhelp_{prefix}_{page_number}_{category_plugins}_{category_pgno}",
                )
                for x in helpable_plugins
            ]
    elif plugins:
        modules = [
            Button.inline(
                f"{HELP_EMOJI} {x} {HELP_EMOJI}",
                data=f"{x}_prev(1)_command_{prefix}_{page_number}",
            )
            for x in helpable_plugins
        ]
    else:
        modules = [
            Button.inline(
                f"{HELP_EMOJI} {x} {HELP_EMOJI}",
                data=f"{x}_cmdhelp_{prefix}_{page_number}_{category_plugins}_{category_pgno}",
            )
            for x in helpable_plugins
        ]
    if number_of_cols == 1:
        pairs = list(zip(modules[::number_of_cols]))
    elif number_of_cols == 2:
        pairs = list(zip(modules[::number_of_cols], modules[1::number_of_cols]))
    else:
        pairs = list(
            zip(
                modules[::number_of_cols],
                modules[1::number_of_cols],
                modules[2::number_of_cols],
            )
        )
    if len(modules) % number_of_cols == 1:
        pairs.append((modules[-1],))
    elif len(modules) % number_of_cols == 2:
        pairs.append((modules[-2], modules[-1]))
    max_num_pages = math.ceil(len(pairs) / number_of_rows)
    modulo_page = page_number % max_num_pages
    if plugins:
        if len(pairs) > number_of_rows:
            pairs = pairs[
                modulo_page * number_of_rows : number_of_rows * (modulo_page + 1)
            ] + [
                (
                    Button.inline("⌫", data=f"{prefix}_prev({modulo_page})_plugin"),
                    Button.inline("⚙️ Main Menu", data="mainmenu"),
                    Button.inline("⌦", data=f"{prefix}_next({modulo_page})_plugin"),
                )
            ]
        else:
            pairs = pairs + [(Button.inline("⚙️ Main Menu", data="mainmenu"),)]
    elif len(pairs) > number_of_rows:
        if category_pgno < 0:
            category_pgno = len(pairs) + category_pgno
        pairs = pairs[
            modulo_page * number_of_rows : number_of_rows * (modulo_page + 1)
        ] + [
            (
                Button.inline(
                    "⌫",
                    data=f"{prefix}_prev({modulo_page})_command_{category_plugins}_{category_pgno}",
                ),
                Button.inline(
                    "⬅️ Back ",
                    data=f"back_plugin_{category_plugins}_{category_pgno}",
                ),
                Button.inline(
                    "⌦",
                    data=f"{prefix}_next({modulo_page})_command_{category_plugins}_{category_pgno}",
                ),
            )
        ]
    else:
        if category_pgno < 0:
            category_pgno = len(pairs) + category_pgno
        pairs = pairs + [
            (
                Button.inline(
                    "⬅️ Back ",
                    data=f"back_plugin_{category_plugins}_{category_pgno}",
                ),
            )
        ]
    return pairs


@catub.tgbot.on(InlineQuery)
async def inline_handler(event):
    builder = event.builder
    result = None
    query = event.text
    string = query.lower()
    query.split(" ", 2)
    str_y = query.split(" ", 1)
    string.split()
    query_user_id = event.query.user_id
    if query_user_id == Config.OWNER_ID or query_user_id in Config.SUDO_USERS:
        hmm = re.compile("troll (.*) (.*)")
        match = re.findall(hmm, query)
        inf = re.compile("secret (.*) (.*)")
        match2 = re.findall(inf, query)
        hid = re.compile("hide (.*)")
        match3 = re.findall(hid, query)
        if string == "ialive":
            result = await article_builder(event, string)
            await event.answer([result] if result else None)
        elif str_y[0].lower() == "ls":
            result = await filemanager_article(event)
            await event.answer([result] if result else None)
        elif query.startswith("Inline buttons"):
            result = await article_builder(event, query)
            await event.answer([result] if result else None)
        elif match or match2 or match3:
            packed = await hide_toll_secret(event, query, match, match3)
            if not packed:
                result = await build_article(
                    event,
                    title="Invalid whisper",
                    description="Could not resolve user / bad syntax.",
                    text=(
                        "**Could not create whisper.**\n\n"
                        "Use: `secret @username text`\n"
                        "Or: `secret @user1 @user2 | text`\n"
                        "Hide: `hide text`"
                    ),
                )
                await event.answer([result] if result else None)
            else:
                result, old_msg, jsondata, new_msg = packed
                await event.answer([result] if result else None)
                if result and new_msg is not None:
                    try:
                        os.makedirs(os.path.dirname(old_msg) or ".", exist_ok=True)
                        if jsondata:
                            jsondata.update(new_msg)
                            json.dump(jsondata, open(old_msg, "w"))
                        else:
                            json.dump(new_msg, open(old_msg, "w"))
                    except Exception as e:
                        LOGS.error(f"Failed to persist whisper: {e}")
        elif string == "help":
            result = await help_article(event)
            await event.answer([result] if result else None)
        elif string == "spotify":
            result = await article_builder(event, string)
            await event.answer([result] if result else None)
        elif string == "vcplayer":
            result = await vcplayer_article(event)
            await event.answer([result] if result else None)
        elif str_y[0].lower() == "s" and len(str_y) == 2:
            result = await inline_search(event, str_y[1].strip())
            await event.answer(result or None)
        elif str_y[0].lower() == "ytdl" and len(str_y) == 2:
            try:
                result = await asyncio.wait_for(
                    youtube_data_article(event, str_y), timeout=4.5
                )
            except asyncio.TimeoutError:
                LOGS.warning("Inline ytdl search timed out — tip article")
                result = await build_article(
                    event,
                    title="Timed out — use .iytdl",
                    description="Inline search took too long",
                    text=(
                        "**Inline ytdl timed out.**\n\n"
                        "Use `.iytdl <query>` instead — it searches first, "
                        "then opens the download buttons."
                    ),
                )
            except Exception as e:
                LOGS.error(f"Inline ytdl failed: {e}")
                result = await build_article(
                    event,
                    title="ytdl error — try .iytdl",
                    description="Inline search failed",
                    text=(
                        f"**Inline ytdl error:** `{e}`\n\n"
                        "Try `.iytdl <query>` instead."
                    ),
                )
            try:
                await event.answer([result] if result else None)
            except QueryIdInvalidError:
                LOGS.warning(
                    "Inline ytdl query expired before answer (search too slow)"
                )
        elif string == "age_verification_alert":
            result = await age_verification_article(event)
            await event.answer([result] if result else None)
        elif string == "pmpermit":
            result = await pmpermit_article(event)
            await event.answer([result] if result else None)
        elif string == "":
            results = await inline_popup_info(event, builder)
            await event.answer(results)
    else:
        result = await deploy_article(event)
        await event.answer([result] if result else None)


async def youtube_data_article(event, str_y):
    link = get_yt_video_id(str_y[1].strip())
    found_ = True
    if link is None:
        resp = (await videos_search(str_y[1].strip(), limit=5)).get("result") or []
        if not resp:
            found_ = False
        else:
            outdata = await result_formatter(resp)
            if not outdata:
                found_ = False
            else:
                key_ = rand_key()
                ytsearch_data.store_(key_, outdata)
                buttons = [
                    Button.inline(
                        f"1 / {len(outdata)}",
                        data=f"ytdl_next_{key_}_1",
                    ),
                    Button.inline(
                        "📜  List all",
                        data=f"ytdl_listall_{key_}_1",
                    ),
                    Button.inline(
                        "⬇️  Download",
                        data=f'ytdl_download_{outdata[1]["video_id"]}_0',
                    ),
                ]
                caption = outdata[1]["message"]
                photo = outdata[1]["thumb"]
    else:
        # Fast path: skip yt-dlp extract so inline answers before Telegram times out
        photo = await get_ytthumb(link)
        caption = f'<a href=https://www.youtube.com/watch?v={link}><b>[{link}]</b></a>'
        buttons = _fast_download_buttons(link)
    if found_:
        result = await build_article(
            event,
            title=link or str_y[1][:40],
            description="⬇️ Click to Download",
            thumbnail=photo,
            media=photo,
            text=caption,
            buttons=buttons,
            parse_mode="html",
        )
    else:
        result = await build_article(
            event,
            title="Not Found",
            text=f"No Results found for `{str_y[1]}`",
            description="INVALID",
        )
    return result


async def hide_toll_secret(event, query, match, match3):
    user_list = []
    if match3:
        sandy = "Chat"
        query = query[5:]
        info_type = ["hide", "can't", "Read Message "]
    else:
        sandy = ""
        if match:
            query = query[6:]
            info_type = ["troll", "can't", "show message 🔐"]
        else:
            query = query[7:]
            info_type = ["secret", "can", "show message 🔐"]
        if "|" in query:
            iris, query = query.replace(" |", "|").replace("| ", "|").split("|", 1)
            users = [u for u in iris.split(" ") if u]
        else:
            parts = query.split(" ", 1)
            if len(parts) < 2 or not parts[1].strip():
                return None
            user, query = parts
            users = [user]
        for user in users:
            user = user.strip()
            if not user:
                continue
            if user.startswith("@"):
                user = user[1:]
            usr = int(user) if user.isdigit() else user
            try:
                # Resolve via userbot — bots often cannot resolve strangers
                u = await catub.get_entity(usr)
            except Exception:
                try:
                    u = await event.client.get_entity(usr)
                except Exception:
                    return None
            if getattr(u, "username", None):
                sandy += f"@{u.username}"
            else:
                sandy += f"[{getattr(u, 'first_name', None) or 'User'}](tg://user?id={u.id})"
            user_list.append(u.id)
            sandy += " "
        sandy = sandy[:-1]
        if not user_list:
            return None
    old_msg = os.path.join("./userbot", f"{info_type[0]}.txt")
    try:
        jsondata = json.load(open(old_msg))
    except Exception:
        jsondata = False
    timestamp = int(time.time() * 2)
    payload = (
        {"text": query}
        if match3
        else {"userid": user_list, "text": query}
    )
    new_msg = {str(timestamp): payload}
    put_whisper(info_type[0], timestamp, payload)
    buttons = [Button.inline(info_type[2], data=f"{info_type[0]}_{timestamp}")]

    result = await build_article(
        event,
        title=f"{info_type[0].title()} message  to {sandy}.",
        description="Send hidden text in chat."
        if match3
        else f"Only he/she/they {info_type[1]} open it.",
        thumbnail=get_thumb(f"{info_type[0]}.png"),
        text="✖✖✖"
        if match3
        else f"🔒 A whisper message to {sandy}, Only he/she can open it.",
        buttons=buttons,
    )
    return result, old_msg, jsondata, new_msg


async def inline_popup_info(event, builder):
    results = []
    alive_menu = await article_builder(event, "ialive")
    results.append(alive_menu) if alive_menu else None
    help_menu = await help_article(event)
    results.append(help_menu) if help_menu else None
    spotify_menu = await article_builder(event, "spotify")
    results.append(spotify_menu) if spotify_menu else None
    vcplayer_menu = await vcplayer_article(event)
    results.append(vcplayer_menu) if vcplayer_menu else None
    file_manager = await filemanager_article(event)
    results.append(file_manager) if file_manager else None
    results.extend(
        (
            builder.article(
                title="Hide",
                description="Send hidden text in chat.\nSyntax: hide",
                text="__Send hidden message for spoilers/quote prevention.__",
                thumb=get_thumb("hide.png"),
                buttons=[
                    Button.switch_inline(
                        "Hidden Text",
                        query="hide Text",
                        same_peer=True,
                    )
                ],
            ),
            builder.article(
                title="Search",
                description="Search cmds & plugins\nSyntax: s",
                text="__Get help about a plugin or cmd.\n\nMixture of .help & .s__",
                thumb=get_thumb("search.jpg"),
                buttons=[
                    Button.switch_inline("Search Help", query="s al", same_peer=True)
                ],
            ),
            builder.article(
                title="Secret",
                description="Send secret message to your friends.\nSyntax: secret @usename",
                text="__Send **secret message** which only you & the reciever can see.\n\nFor multiple users give space to username & use **|** to seperate text.__",
                thumb=get_thumb("secret.png"),
                buttons=[
                    (
                        Button.switch_inline(
                            "Single",
                            query="secret @username Text",
                            same_peer=True,
                        ),
                        Button.switch_inline(
                            "Multiple",
                            query="secret @username @username2 | Text",
                            same_peer=True,
                        ),
                    )
                ],
            ),
            builder.article(
                title="Troll",
                description="Send troll message to your friends.\nSyntax: toll @usename",
                text="__Send **troll message** which everyone can see except the reciever.\n\nFor multiple users give space to username & use **|** to seperate text.__",
                thumb=get_thumb("troll.png"),
                buttons=[
                    (
                        Button.switch_inline(
                            "Single",
                            query="troll @username Text",
                            same_peer=True,
                        ),
                        Button.switch_inline(
                            "Multiple",
                            query="troll @username @username2 | Text",
                            same_peer=True,
                        ),
                    )
                ],
            ),
            builder.article(
                title="Youtube Download",
                description="Download videos/audios from YouTube.\nSyntax: ytdl",
                text="__Download videos or audios from YouTube with different options of resolutions/quality.__",
                thumb=get_thumb("youtube.png"),
                buttons=[
                    Button.switch_inline(
                        "Youtube-dl",
                        query="ytdl perfect",
                        same_peer=True,
                    )
                ],
            ),
        )
    )

    return results


@catub.tgbot.on(CallbackQuery(data=re.compile(b"close")))
@check_owner
async def on_plug_in_callback_query_handler(event):
    buttons = [
        (Button.inline("Open Menu", data="mainmenu"),),
    ]
    await event.edit("Menu Closed", buttons=buttons)


@catub.tgbot.on(CallbackQuery(data=re.compile(b"check")))
async def on_plugin_callback_query_handler(event):
    text = f"𝙿𝚕𝚞𝚐𝚒𝚗𝚜: {len(PLG_INFO)}\
        \n𝙲𝚘𝚖𝚖𝚊𝚗𝚍𝚜: {len(CMD_INFO)}\
        \n\n{tr}𝚑𝚎𝚕𝚙 <𝚙𝚕𝚞𝚐𝚒𝚗> : 𝙵𝚘𝚛 𝚜𝚙𝚎𝚌𝚒𝚏𝚒𝚌 𝚙𝚕𝚞𝚐𝚒𝚗 𝚒𝚗𝚏𝚘.\
        \n{tr}𝚑𝚎𝚕𝚙 -𝚌 <𝚌𝚘𝚖𝚖𝚊𝚗𝚍> : 𝙵𝚘𝚛 𝚊𝚗𝚢 𝚌𝚘𝚖𝚖𝚊𝚗𝚍 𝚒𝚗𝚏𝚘.\
        \n{tr}𝚜 <𝚚𝚞𝚎𝚛𝚢> : 𝚃𝚘 𝚜𝚎𝚊𝚛𝚌𝚑 𝚊𝚗𝚢 𝚌𝚘𝚖𝚖𝚊𝚗𝚍𝚜.\
        "
    await event.answer(text, cache_time=0, alert=True)


@catub.tgbot.on(CallbackQuery(data=re.compile(b"(.*)_menu")))
@check_owner
async def on_plug_in_callback_query_handler(event):
    category = str(event.pattern_match.group(1).decode("UTF-8"))
    buttons = paginate_help(0, GRP_INFO[category], category)
    text = f"**Category: **{category}\
        \n**Total plugins :** {len(GRP_INFO[category])}\
        \n**Total Commands:** {command_in_category(category)}"
    await event.edit(text, buttons=buttons)


@catub.tgbot.on(
    CallbackQuery(
        data=re.compile(b"back_([a-z]+)_([a-z_1-9]+)_([0-9]+)_?([a-z1-9]+)?_?([0-9]+)?")
    )
)
@check_owner
async def on_plug_in_callback_query_handler(event):
    mtype = str(event.pattern_match.group(1).decode("UTF-8"))
    category = str(event.pattern_match.group(2).decode("UTF-8"))
    pgno = int(event.pattern_match.group(3).decode("UTF-8"))
    if mtype == "plugin":
        buttons = paginate_help(pgno, GRP_INFO[category], category)
        text = f"**Category: **`{category}`\
            \n**Total plugins :** __{len(GRP_INFO[category])}__\
            \n**Total Commands:** __{command_in_category(category)}__"
    else:
        category_plugins = str(event.pattern_match.group(4).decode("UTF-8"))
        category_pgno = int(event.pattern_match.group(5).decode("UTF-8"))
        buttons = paginate_help(
            pgno,
            PLG_INFO[category],
            category,
            plugins=False,
            category_plugins=category_plugins,
            category_pgno=category_pgno,
        )
        text = f"**Plugin: **`{category}`\
                \n**Category: **__{getkey(category)}__\
                \n**Total Commands:** __{len(PLG_INFO[category])}__"
    await event.edit(text, buttons=buttons)


@catub.tgbot.on(CallbackQuery(data=re.compile(rb"mainmenu")))
@check_owner
async def on_plug_in_callback_query_handler(event):
    _result = main_menu()
    await event.edit(_result[0], buttons=_result[1])


@catub.tgbot.on(
    CallbackQuery(data=re.compile(rb"(.*)_prev\((.+?)\)_([a-z]+)_?([a-z]+)?_?(.*)?"))
)
@check_owner
async def on_plug_in_callback_query_handler(event):
    category = str(event.pattern_match.group(1).decode("UTF-8"))
    current_page_number = int(event.data_match.group(2).decode("UTF-8"))
    htype = str(event.pattern_match.group(3).decode("UTF-8"))
    if htype == "plugin":
        buttons = paginate_help(current_page_number - 1, GRP_INFO[category], category)
    else:
        category_plugins = str(event.pattern_match.group(4).decode("UTF-8"))
        category_pgno = int(event.pattern_match.group(5).decode("UTF-8"))
        buttons = paginate_help(
            current_page_number - 1,
            PLG_INFO[category],
            category,
            plugins=False,
            category_plugins=category_plugins,
            category_pgno=category_pgno,
        )
        text = f"**Plugin: **`{category}`\
                \n**Category: **__{getkey(category)}__\
                \n**Total Commands:** __{len(PLG_INFO[category])}__"
        try:
            return await event.edit(text, buttons=buttons)
        except Exception as e:
            LOGS.error(str(e))
    await event.edit(buttons=buttons)


@catub.tgbot.on(
    CallbackQuery(data=re.compile(rb"(.*)_next\((.+?)\)_([a-z]+)_?([a-z]+)?_?(.*)?"))
)
@check_owner
async def on_plug_in_callback_query_handler(event):
    category = str(event.pattern_match.group(1).decode("UTF-8"))
    current_page_number = int(event.data_match.group(2).decode("UTF-8"))
    htype = str(event.pattern_match.group(3).decode("UTF-8"))
    category_plugins = event.pattern_match.group(4)
    if category_plugins:
        category_plugins = str(category_plugins.decode("UTF-8"))
    category_pgno = event.pattern_match.group(5)
    if category_pgno:
        category_pgno = int(category_pgno.decode("UTF-8"))
    if htype == "plugin":
        buttons = paginate_help(current_page_number + 1, GRP_INFO[category], category)
    else:
        buttons = paginate_help(
            current_page_number + 1,
            PLG_INFO[category],
            category,
            plugins=False,
            category_plugins=category_plugins,
            category_pgno=category_pgno,
        )
    await event.edit(buttons=buttons)


@catub.tgbot.on(
    CallbackQuery(
        data=re.compile(b"(.*)_cmdhelp_([a-z_1-9]+)_([0-9]+)_([a-z]+)_([0-9]+)")
    )
)
@check_owner
async def on_plug_in_callback_query_handler(event):
    cmd = str(event.pattern_match.group(1).decode("UTF-8"))
    category = str(event.pattern_match.group(2).decode("UTF-8"))
    pgno = int(event.pattern_match.group(3).decode("UTF-8"))
    category_plugins = str(event.pattern_match.group(4).decode("UTF-8"))
    category_pgno = int(event.pattern_match.group(5).decode("UTF-8"))
    buttons = [
        (
            Button.inline(
                "⬅️ Back ",
                data=f"back_command_{category}_{pgno}_{category_plugins}_{category_pgno}",
            ),
            Button.inline("⚙️ Main Menu", data="mainmenu"),
        )
    ]
    text = f"**Command :** `{tr}{cmd}`\
        \n**Plugin :** `{category}`\
        \n**Category :** `{category_plugins}`\
        \n\n**✘ Intro :**\n{CMD_INFO[cmd][0]}"
    await event.edit(text, buttons=buttons)


async def inline_search(event, query):
    answers = []
    builder = event.builder
    if found := [i for i in sorted(list(CMD_INFO)) if query in i]:
        for cmd in found:
            title = f"Command:  {cmd}"
            plugin = get_key(cmd)
            try:
                info = CMD_INFO[cmd][1]
            except IndexError:
                info = "None"
            description = f"Plugin:  {plugin} \nCategory:  {getkey(plugin)}\n{info}"
            text = await cmdinfo(cmd, event)
            result = builder.article(
                title=title,
                description=description,
                thumb=get_thumb("plugin_cmd.jpg"),
                text=text,
            )
            answers.append(result)

    if found := [i for i in sorted(list(PLG_INFO.keys())) if query in i]:
        for plugin in found:
            count = len(PLG_INFO[plugin])
            if count > 1:
                title = f"Plugin:  {plugin}"
                text = await plugininfo(plugin, event, "-p")
                result = builder.article(
                    title=title,
                    description=f"Category:  {getkey(plugin)}\nTotal Cmd: {count}",
                    thumb=get_thumb("plugin.jpg"),
                    text=text,
                )
                answers.append(result)
    return answers
