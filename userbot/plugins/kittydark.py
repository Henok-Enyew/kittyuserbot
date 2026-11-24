import asyncio

from ..helpers.functions import kittyfun_banks as kf
from . import ALIVE_NAME, catub, edit_or_reply

plugin_category = "fun"


async def _who(event):
    reply = await event.get_reply_message()
    if reply and reply.sender:
        return reply.sender.first_name or ALIVE_NAME
    arg = (event.pattern_match.group(1) or "").strip()
    return kf.clean_name(arg, ALIVE_NAME or "the departed")


@catub.cat_cmd(
    pattern="obituary(?:\s|$)([\s\S]*)",
    command=("obituary", plugin_category),
    info={
        "header": "Dark humor — fake obituary.",
        "usage": ["{tr}obituary", "{tr}obituary <name>", "{tr}obituary <reply>"],
        "note": "Fictional joke epitaph only.",
    },
)
async def obituary(event):
    "Fake obituary."
    name = await _who(event)
    await edit_or_reply(event, kf.fill(kf.pick(kf.OBITUARIES), name=name))


@catub.cat_cmd(
    pattern="tombstone(?:\s|$)([\s\S]*)",
    command=("tombstone", plugin_category),
    info={
        "header": "Dark humor — ASCII tombstone.",
        "usage": ["{tr}tombstone", "{tr}tombstone <name>", "{tr}tombstone <reply>"],
    },
)
async def tombstone(event):
    "ASCII tombstone."
    name = await _who(event)
    label = (name[:10] + "..") if len(name) > 12 else name
    art = f"```\n  _______\n /       \\\n|  R.I.P. |\n| {label:^7} |\n|  mid    |\n \\_______/\n```"
    await edit_or_reply(event, art)


@catub.cat_cmd(
    pattern="haunted(?:\s|$)([\s\S]*)",
    command=("haunted", plugin_category),
    info={
        "header": "Dark humor — possession animation.",
        "usage": ["{tr}haunted", "{tr}haunted <name>", "{tr}haunted <reply>"],
    },
)
async def haunted(event):
    "Haunted animation."
    name = await _who(event)
    catevent = await edit_or_reply(event, "`…`")
    for frame in kf.HAUNTED:
        await asyncio.sleep(0.5)
        await catevent.edit(kf.fill(frame, name=name))


@catub.cat_cmd(
    pattern="cursed(?:\s|$)([\s\S]*)",
    command=("cursed", plugin_category),
    info={
        "header": "Dark humor — cursed comment generator.",
        "usage": ["{tr}cursed", "{tr}cursed <name>", "{tr}cursed <reply>"],
    },
)
async def cursed(event):
    "Cursed comment."
    name = await _who(event)
    await edit_or_reply(event, f"👁️ {kf.fill(kf.pick(kf.CURSED), name=name)}")


@catub.cat_cmd(
    pattern="lastwords(?:\s|$)([\s\S]*)",
    command=("lastwords", plugin_category),
    info={
        "header": "Dark humor — dramatic final words.",
        "usage": ["{tr}lastwords", "{tr}lastwords <name>", "{tr}lastwords <reply>"],
    },
)
async def lastwords(event):
    "Last words animation."
    name = await _who(event)
    catevent = await edit_or_reply(event, f"`{name} clears throat…`")
    await asyncio.sleep(0.5)
    await catevent.edit(f"**LAST WORDS — {name}**\n_{kf.pick(kf.LAST_WORDS)}_")


@catub.cat_cmd(
    pattern="ghosted(?:\s|$)([\s\S]*)",
    command=("ghosted", plugin_category),
    info={
        "header": "Dark humor — paranormal ghosting roast.",
        "usage": ["{tr}ghosted", "{tr}ghosted <name>", "{tr}ghosted <reply>"],
    },
)
async def ghosted(event):
    "Ghosted roast animation."
    name = await _who(event)
    catevent = await edit_or_reply(event, "`checking last seen…`")
    for frame in kf.GHOSTED:
        await asyncio.sleep(0.45)
        await catevent.edit(kf.fill(frame, name=name))


@catub.cat_cmd(
    pattern="midlife(?:\s|$)([\s\S]*)",
    command=("midlife", plugin_category),
    info={
        "header": "Dark humor — existential crisis meter.",
        "usage": ["{tr}midlife", "{tr}midlife <name>", "{tr}midlife <reply>"],
    },
)
async def midlife(event):
    "Midlife crisis meter."
    name = await _who(event)
    score = kf.meter(name, "midlife")
    await edit_or_reply(
        event,
        f"**MIDLIFE METER — {name}**\n`[{kf.bar(score)}]` **{score}%**\n"
        f"Symptoms: sports car fantasies, playlist spirals, sudden gym.",
    )


@catub.cat_cmd(
    pattern="therapy$",
    command=("therapy", plugin_category),
    info={
        "header": "Dark humor — useless therapist dialogue.",
        "usage": "{tr}therapy",
    },
)
async def therapy(event):
    "Therapy dialogue animation."
    catevent = await edit_or_reply(event, "`session starting…`")
    for frame in kf.THERAPY:
        await asyncio.sleep(0.7)
        await catevent.edit(frame)


@catub.cat_cmd(
    pattern="void$",
    command=("void", plugin_category),
    info={
        "header": "Dark humor — stare into the void.",
        "usage": "{tr}void",
    },
)
async def void_cmd(event):
    "Void stare animation."
    catevent = await edit_or_reply(event, "`…`")
    for frame in kf.VOID_LINES:
        await asyncio.sleep(0.5)
        await catevent.edit(frame)


@catub.cat_cmd(
    pattern="fakedie(?:\s|$)([\s\S]*)",
    command=("fakedie", plugin_category),
    info={
        "header": "Dark humor — cartoon chalk-outline gag.",
        "usage": ["{tr}fakedie", "{tr}fakedie <name>", "{tr}fakedie <reply>"],
        "note": "Cartoon joke only. Not real harm.",
    },
)
async def fakedie(event):
    "Cartoon chalk outline."
    name = await _who(event)
    catevent = await edit_or_reply(event, "`dramatic collapse…`")
    frames = [
        f"{name} has left the mortal group chat",
        "```\n  .---.\n /     \\\n|  X X  |\n \\  -  /\n  '---'\n chalk outline (washable)\n```",
        f"**FAKE OUT**\n{name} sits up. It was for the bit.\nAudience: unpaid.",
    ]
    for frame in frames:
        await asyncio.sleep(0.6)
        await catevent.edit(frame)


@catub.cat_cmd(
    pattern="yikes$",
    command=("yikes", plugin_category),
    info={
        "header": "Dark humor — cringe autopsy of a replied message.",
        "usage": "{tr}yikes (preferably reply)",
    },
)
async def yikes(event):
    "Yikes escalation."
    reply = await event.get_reply_message()
    snippet = ""
    if reply and reply.text:
        snippet = reply.text[:80].replace("\n", " ")
    catevent = await edit_or_reply(event, "`opening crime scene…`")
    for frame in kf.YIKES_ESCALATION:
        await asyncio.sleep(0.4)
        await catevent.edit(frame)
    if snippet:
        await catevent.edit(
            f"**CRINGE AUTOPSY**\nExhibit A: `{snippet}`\nVerdict: sealed in the vault of shame."
        )
