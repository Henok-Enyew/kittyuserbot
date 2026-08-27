import asyncio

from ..helpers.functions import kittyfun_banks as kf
from . import ALIVE_NAME, catub, edit_or_reply

plugin_category = "fun"


async def _who(event):
    reply = await event.get_reply_message()
    if reply and reply.sender:
        return reply.sender.first_name or ALIVE_NAME
    arg = (event.pattern_match.group(1) or "").strip()
    return kf.clean_name(arg, ALIVE_NAME or "babe")


@catub.cat_cmd(
    pattern="flirt(?:\s|$)([\s\S]*)",
    command=("flirt", plugin_category),
    info={
        "header": "Dirty humor — flirt line.",
        "usage": ["{tr}flirt", "{tr}flirt <name>", "{tr}flirt <reply>"],
    },
)
async def flirt(event):
    "Flirt line."
    name = await _who(event)
    await edit_or_reply(event, f"😏 {kf.fill(kf.pick(kf.FLIRTS), name=name)}")


@catub.cat_cmd(
    pattern="pickup(?:\s|$)([\s\S]*)",
    command=("pickup", plugin_category),
    info={
        "header": "Dirty humor — pickup line.",
        "usage": ["{tr}pickup", "{tr}pickup <name>", "{tr}pickup <reply>"],
    },
)
async def pickup(event):
    "Pickup line."
    name = await _who(event)
    await edit_or_reply(event, f"💘 {kf.fill(kf.pick(kf.PICKUPS), name=name)}")


@catub.cat_cmd(
    pattern="thirst(?:\s|$)([\s\S]*)",
    command=("thirst", plugin_category),
    info={
        "header": "Dirty humor — call out the thirst.",
        "usage": ["{tr}thirst", "{tr}thirst <name>", "{tr}thirst <reply>"],
    },
)
async def thirst(event):
    "Thirst callout."
    name = await _who(event)
    await edit_or_reply(event, f"💧 {kf.fill(kf.pick(kf.THIRST), name=name)}")


@catub.cat_cmd(
    pattern="bedroom$",
    command=("bedroom", plugin_category),
    info={
        "header": "Dirty humor — mood lighting animation (suggestive comedy).",
        "usage": "{tr}bedroom",
    },
)
async def bedroom(event):
    "Bedroom mood animation."
    catevent = await edit_or_reply(event, "`setting the mood…`")
    for frame in kf.BEDROOM_FRAMES:
        await asyncio.sleep(0.5)
        await catevent.edit(frame)


@catub.cat_cmd(
    pattern="moan$",
    command=("moan", plugin_category),
    info={
        "header": "Dirty humor — cursed moan meme (bait-and-switch).",
        "usage": "{tr}moan",
    },
)
async def moan(event):
    "Moan meme animation."
    catevent = await edit_or_reply(event, "` `")
    for frame in kf.MOAN_FRAMES:
        await asyncio.sleep(0.4)
        await catevent.edit(frame)


@catub.cat_cmd(
    pattern="nudes$",
    command=("nudes", plugin_category),
    info={
        "header": "Dirty humor — fake 'sending nudes' bait-and-switch.",
        "usage": "{tr}nudes",
    },
)
async def nudes(event):
    "Fake nudes bait-and-switch."
    catevent = await edit_or_reply(event, kf.NUDE_SWITCH[0])
    for frame in kf.NUDE_SWITCH[1:]:
        await asyncio.sleep(0.45)
        await catevent.edit(frame)


@catub.cat_cmd(
    pattern="onlyfans(?:\s|$)([\s\S]*)",
    command=("onlyfans", plugin_category),
    info={
        "header": "Dirty humor — parody subscribe pitch.",
        "usage": ["{tr}onlyfans", "{tr}onlyfans <name>", "{tr}onlyfans <reply>"],
    },
)
async def onlyfans(event):
    "OnlyFans parody pitch."
    name = await _who(event)
    await edit_or_reply(event, kf.fill(kf.pick(kf.ONLYFANS_PITCH), name=name))


@catub.cat_cmd(
    pattern="kinkrate(?:\s|$)([\s\S]*)",
    command=("kinkrate", plugin_category),
    info={
        "header": "Dirty humor — joke kink meter.",
        "usage": ["{tr}kinkrate", "{tr}kinkrate <name>", "{tr}kinkrate <reply>"],
        "note": "Joke meter only.",
    },
)
async def kinkrate(event):
    "Kink rate meter."
    name = await _who(event)
    score = kf.meter(name, "kink")
    await edit_or_reply(
        event,
        f"**KINKRATE — {name}**\n`[{kf.bar(score)}]` **{score}%**\n"
        f"_Certified freak / certified bluffing — you decide._",
    )


@catub.cat_cmd(
    pattern="walkofshame$",
    command=("walkofshame", plugin_category),
    info={
        "header": "Dirty humor — morning-after comedy walk.",
        "usage": "{tr}walkofshame",
    },
)
async def walkofshame(event):
    "Walk of shame animation."
    catevent = await edit_or_reply(event, "`5:47am…`")
    frames = [
        "Sunglasses: ON",
        "Dignity: missing",
        "Uber: arriving",
        "Driver: knows",
        f"**WALK OF SHAME**\n{ALIVE_NAME} unlocks 'experienced' achievement.\n+1 lore, −3 sleep.",
    ]
    for frame in frames:
        await asyncio.sleep(0.5)
        await catevent.edit(frame)


@catub.cat_cmd(
    pattern="seduce(?:\s|$)([\s\S]*)",
    command=("seduce", plugin_category),
    info={
        "header": "Dirty humor — overacting seduction script.",
        "usage": ["{tr}seduce", "{tr}seduce <name>", "{tr}seduce <reply>"],
    },
)
async def seduce(event):
    "Seduction script animation."
    name = await _who(event)
    catevent = await edit_or_reply(event, "`method acting…`")
    frames = [
        f"*leans against wall near {name}*",
        "*wall was wet paint*",
        f"{ALIVE_NAME}: that was intentional",
        f"{name}: it was not",
        f"**SEDUCTION FAILED**\nFriendship ending unlocked. Try pizza.",
    ]
    for frame in frames:
        await asyncio.sleep(0.55)
        await catevent.edit(frame)


@catub.cat_cmd(
    pattern="dirtydice$",
    command=("dirtydice", plugin_category),
    info={
        "header": "Dirty humor — roll a filthy (chat-safe) dare.",
        "usage": "{tr}dirtydice",
    },
)
async def dirtydice(event):
    "Dirty dare dice."
    catevent = await edit_or_reply(event, "`rolling…`")
    await asyncio.sleep(0.4)
    await catevent.edit(f"🎲 **DIRTY DARE**\n{kf.pick(kf.DIRTY_DARES)}")


@catub.cat_cmd(
    pattern="aftercare(?:\s|$)([\s\S]*)",
    command=("aftercare", plugin_category),
    info={
        "header": "Dirty humor — sarcastic aftercare card.",
        "usage": ["{tr}aftercare", "{tr}aftercare <name>", "{tr}aftercare <reply>"],
    },
)
async def aftercare(event):
    "Aftercare card."
    name = await _who(event)
    await edit_or_reply(event, kf.fill(kf.pick(kf.AFTERCARE), name=name))
