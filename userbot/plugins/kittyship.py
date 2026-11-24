import asyncio
import re

from ..helpers.functions import kittyfun_banks as kf
from . import ALIVE_NAME, catub, edit_or_reply

plugin_category = "fun"


def _tier(score: int):
    if score < 34:
        return "low"
    if score < 67:
        return "mid"
    return "high"


async def _two_names(event):
    """Resolve two names from args 'A B' / 'A|B' / 'A and B' or reply + arg."""
    raw = (event.pattern_match.group(1) or "").strip()
    reply = await event.get_reply_message()
    reply_name = None
    if reply and reply.sender:
        reply_name = reply.sender.first_name

    if raw:
        parts = re.split(r"\s+and\s+|\s*\|\s*|\s+&\s+|\s+", raw, maxsplit=1)
        if len(parts) >= 2 and parts[1].strip():
            return kf.clean_name(parts[0]), kf.clean_name(parts[1])
        if reply_name:
            return reply_name, kf.clean_name(parts[0])
        return kf.clean_name(parts[0]), ALIVE_NAME or "You"

    if reply_name:
        return reply_name, ALIVE_NAME or "You"
    return ALIVE_NAME or "You", "Destiny"


@catub.cat_cmd(
    pattern="ship(?:\s|$)([\s\S]*)",
    command=("ship", plugin_category),
    info={
        "header": "Ship two people with a compatibility %.",
        "usage": [
            "{tr}ship <name1> <name2>",
            "{tr}ship <name1>|<name2>",
            "{tr}ship <reply> <name>",
        ],
        "examples": "{tr}ship Alice Bob",
    },
)
async def ship(event):
    "Ship compatibility."
    a, b = await _two_names(event)
    score = kf.meter(f"{a}|{b}", "ship")
    sn = kf.ship_name(a, b)
    verdict = kf.pick(kf.SHIP_VERDICTS[_tier(score)])
    await edit_or_reply(
        event,
        f"💘 **{a}** × **{b}**\n"
        f"Ship name: **{sn}**\n"
        f"`[{kf.bar(score)}]` **{score}%**\n"
        f"{verdict}",
    )


@catub.cat_cmd(
    pattern="otp(?:\s|$)([\s\S]*)",
    command=("otp", plugin_category),
    info={
        "header": "OTP check (alias of ship with drama).",
        "usage": ["{tr}otp <name1> <name2>", "{tr}otp <reply> <name>"],
    },
)
async def otp(event):
    "OTP check."
    a, b = await _two_names(event)
    score = kf.meter(f"{a}|{b}", "otp")
    catevent = await edit_or_reply(event, "`consulting the fanfic council…`")
    await asyncio.sleep(0.5)
    await catevent.edit(
        f"✨ **OTP?** {a} × {b}\n"
        f"`[{kf.bar(score)}]` **{score}%**\n"
        f"{kf.pick(kf.SHIP_VERDICTS[_tier(score)])}"
    )


@catub.cat_cmd(
    pattern="compat(?:\s|$)([\s\S]*)",
    command=("compat", plugin_category),
    info={
        "header": "Compatibility dossier.",
        "usage": ["{tr}compat <name1> <name2>", "{tr}compat <reply> <name>"],
    },
)
async def compat(event):
    "Compatibility dossier."
    a, b = await _two_names(event)
    love = kf.meter(f"{a}|{b}", "love")
    chaos = kf.meter(f"{a}|{b}", "chaos")
    snacks = kf.meter(f"{a}|{b}", "snacks")
    await edit_or_reply(
        event,
        f"**COMPAT DOSSIER**\n{a} × {b}\n"
        f"Love `[{kf.bar(love)}]` {love}%\n"
        f"Chaos `[{kf.bar(chaos)}]` {chaos}%\n"
        f"Snack sync `[{kf.bar(snacks)}]` {snacks}%\n"
        f"Ship: **{kf.ship_name(a, b)}**",
    )


@catub.cat_cmd(
    pattern="lovetriangle(?:\s|$)([\s\S]*)",
    command=("lovetriangle", plugin_category),
    info={
        "header": "Three-name love triangle drama.",
        "usage": "{tr}lovetriangle <a> <b> <c>",
        "examples": "{tr}lovetriangle Amy Bea Cat",
    },
)
async def lovetriangle(event):
    "Love triangle animation."
    raw = (event.pattern_match.group(1) or "").strip()
    parts = raw.split()
    if len(parts) < 3:
        return await edit_or_reply(event, "`need 3 names: .lovetriangle A B C`")
    a, b, c = [kf.clean_name(p) for p in parts[:3]]
    catevent = await edit_or_reply(event, "`assembling drama…`")
    frames = [
        f"{a} ❤️ {b}",
        f"{b} 😳 {c}",
        f"{a} 😡 {c}",
        f"{a} 💔 {b} 💔 {c}",
        f"**TRIANGLE COMPLETE**\n{a} / {b} / {c}\nNobody wins. The plot does.",
    ]
    for frame in frames:
        await asyncio.sleep(0.55)
        await catevent.edit(frame)


@catub.cat_cmd(
    pattern="breakup(?:\s|$)([\s\S]*)",
    command=("breakup", plugin_category),
    info={
        "header": "Soap-opera breakup animation.",
        "usage": ["{tr}breakup", "{tr}breakup <name>", "{tr}breakup <reply>"],
    },
)
async def breakup(event):
    "Breakup soap opera."
    a, b = await _two_names(event)
    catevent = await edit_or_reply(event, "`cue dramatic music…`")
    frames = [
        f"{a}: we need to talk",
        f"{b}: is this about the snacks",
        f"{a}: it's about everything",
        f"{b}: …including the snacks",
        f"**BREAKUP**\n{a} × {b} — cancelled like a bad reboot.\nShared playlist: disputed.",
    ]
    for frame in frames:
        await asyncio.sleep(0.6)
        await catevent.edit(frame)


@catub.cat_cmd(
    pattern="wedding(?:\s|$)([\s\S]*)",
    command=("wedding", plugin_category),
    info={
        "header": "Chaotic shotgun wedding animation.",
        "usage": ["{tr}wedding <name1> <name2>", "{tr}wedding <reply> <name>"],
    },
)
async def wedding(event):
    "Wedding animation."
    a, b = await _two_names(event)
    catevent = await edit_or_reply(event, "`assembling a courtroom… wait, chapel`")
    frames = [
        "💒 doors open",
        f"Bride/groom energy: **{a}**",
        f"Also bride/groom energy: **{b}**",
        "Officiant: a raccoon with a clipboard",
        f"**I NOW PRONOUNCE YOU**\n{kf.ship_name(a, b)}\nYou may roast the bride.",
    ]
    for frame in frames:
        await asyncio.sleep(0.55)
        await catevent.edit(frame)


@catub.cat_cmd(
    pattern="stalk(?:\s|$)([\s\S]*)",
    command=("stalk", plugin_category),
    info={
        "header": "Fake relationship intel dossier (parody).",
        "usage": ["{tr}stalk", "{tr}stalk <name>", "{tr}stalk <reply>"],
        "note": "Obviously fake joke dossier.",
    },
)
async def stalk(event):
    "Fake intel dossier."
    raw = (event.pattern_match.group(1) or "").strip()
    reply = await event.get_reply_message()
    name = (
        reply.sender.first_name
        if reply and reply.sender
        else kf.clean_name(raw, ALIVE_NAME or "Target")
    )
    catevent = await edit_or_reply(event, "`accessing public vibes…`")
    await asyncio.sleep(0.5)
    await catevent.edit(
        f"**INTEL DOSSIER (FAKE)**\n"
        f"Subject: **{name}**\n"
        f"Status: online emotionally, offline responsibly\n"
        f"Risk: {kf.meter(name, 'risk')}%\n"
        f"Known associates: snacks, unread mail\n"
        f"Conclusion: iconic, slightly illegal in 3 timelines\n"
        f"_This is parody. Touch grass._"
    )


@catub.cat_cmd(
    pattern="ex(?:\s|$)([\s\S]*)",
    command=("ex", plugin_category),
    info={
        "header": "Roast-your-ex generator.",
        "usage": ["{tr}ex", "{tr}ex <name>", "{tr}ex <reply>"],
    },
)
async def ex_roast(event):
    "Ex roast."
    raw = (event.pattern_match.group(1) or "").strip()
    reply = await event.get_reply_message()
    name = (
        reply.sender.first_name
        if reply and reply.sender
        else kf.clean_name(raw, "the ex")
    )
    await edit_or_reply(event, kf.fill(kf.pick(kf.EX_ROASTS), name=name))
