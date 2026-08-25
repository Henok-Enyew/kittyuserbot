# Fun aura reactions — .fu (gorilla) + .fuck (ASCII)

import contextlib

from userbot import catub

from ..core.managers import edit_delete
from ..helpers.functions.aura_fun import (
    FU_IMAGE_PATH,
    build_fuck_message,
    fu_image_exists,
    random_fu_caption,
    resolve_fu_target,
)

plugin_category = "fun"


@catub.cat_cmd(
    pattern=r"fu$",
    command=("fu", plugin_category),
    info={
        "header": "Send the legendary gorilla reaction",
        "description": (
            "Deletes your command and drops the .fu image with a short "
            "creative caption. Replies to the message you replied to."
        ),
        "usage": ["{tr}fu", "{tr}fu (reply)"],
        "examples": ["{tr}fu"],
    },
)
async def fu_cmd(event):
    "Gorilla reaction image."
    if not fu_image_exists():
        return await edit_delete(
            event, "**Missing fu.png** — redeploy with bundled resources."
        )
    reply_to = await resolve_fu_target(event)
    caption = random_fu_caption()
    with contextlib.suppress(Exception):
        await event.delete()
    await event.client.send_file(
        event.chat_id,
        FU_IMAGE_PATH,
        caption=caption,
        reply_to=reply_to,
    )


@catub.cat_cmd(
    pattern=r"fuck$",
    command=("fuck", plugin_category),
    info={
        "header": "Send middle-finger ASCII art",
        "description": (
            "Deletes your command and sends monospace finger art. "
            "Replies to the message you replied to."
        ),
        "usage": ["{tr}fuck", "{tr}fuck (reply)"],
        "examples": ["{tr}fuck"],
    },
)
async def fuck_cmd(event):
    "ASCII finger art (aura farming)."
    reply_to = await resolve_fu_target(event)
    text = build_fuck_message()
    with contextlib.suppress(Exception):
        await event.delete()
    await event.client.send_message(
        event.chat_id,
        text,
        parse_mode="html",
        link_preview=False,
        reply_to=reply_to,
    )
