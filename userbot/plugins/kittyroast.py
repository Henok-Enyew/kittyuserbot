import asyncio

from ..helpers.functions import kittyfun_banks as kf
from . import ALIVE_NAME, catub, edit_or_reply

plugin_category = "fun"


async def _who(event):
    reply = await event.get_reply_message()
    if reply and reply.sender:
        return reply.sender.first_name or ALIVE_NAME
    arg = (event.pattern_match.group(1) or "").strip()
    return kf.clean_name(arg, ALIVE_NAME or "someone")


def _tier(score: int):
    if score < 34:
        return "low"
    if score < 67:
        return "mid"
    return "high"


def _meter_block(title, name, score, comments):
    tier = _tier(score)
    return (
        f"**{title} — {name}**\n"
        f"`[{kf.bar(score)}]` **{score}%**\n"
        f"{kf.pick(comments[tier])}"
    )


@catub.cat_cmd(
    pattern="roast(?:\s|$)([\s\S]*)",
    command=("roast", plugin_category),
    info={
        "header": "Serve a roast (mild → brutal).",
        "usage": ["{tr}roast", "{tr}roast <name>", "{tr}roast <reply>"],
    },
)
async def roast(event):
    "Roast generator."
    name = await _who(event)
    catevent = await edit_or_reply(event, "`preheating the burners…`")
    await asyncio.sleep(0.4)
    line = kf.pick(kf.ROAST_MILD + kf.ROAST_MID + kf.ROAST_BRUTAL)
    await catevent.edit(kf.fill(line, name=name))


@catub.cat_cmd(
    pattern="burn(?:\s|$)([\s\S]*)",
    command=("burn", plugin_category),
    info={
        "header": "Escalating roast animation.",
        "usage": ["{tr}burn", "{tr}burn <name>", "{tr}burn <reply>"],
    },
)
async def burn(event):
    "Escalating burn animation."
    name = await _who(event)
    catevent = await edit_or_reply(event, "`lighting match…`")
    frames = [
        kf.fill(kf.pick(kf.ROAST_MILD), name=name),
        kf.fill(kf.pick(kf.ROAST_MID), name=name),
        kf.fill(kf.pick(kf.ROAST_BRUTAL), name=name),
        f"🔥 {kf.pick(kf.DISS_LINES)}",
    ]
    for frame in frames:
        await asyncio.sleep(0.7)
        await catevent.edit(frame)


@catub.cat_cmd(
    pattern="diss(?:\s|$)([\s\S]*)",
    command=("diss", plugin_category),
    info={
        "header": "Short diss track energy.",
        "usage": ["{tr}diss", "{tr}diss <name>", "{tr}diss <reply>"],
    },
)
async def diss(event):
    "Diss line."
    name = await _who(event)
    await edit_or_reply(
        event,
        f"**DISS — {name}**\n{kf.fill(kf.pick(kf.ROAST_BRUTAL), name=name)}\n_{kf.pick(kf.DISS_LINES)}_",
    )


@catub.cat_cmd(
    pattern="rate(?:\s|$)([\s\S]*)",
    command=("rate", plugin_category),
    info={
        "header": "Rate anything 0–100 with commentary.",
        "usage": ["{tr}rate <thing>", "{tr}rate <reply>"],
        "examples": "{tr}rate my fit",
    },
)
async def rate(event):
    "Rate meter."
    subject = event.pattern_match.group(1).strip()
    if not subject:
        reply = await event.get_reply_message()
        subject = (reply.text if reply else "") or (await _who(event))
    subject = subject[:80]
    score = kf.meter(subject, "rate")
    await edit_or_reply(event, _meter_block("RATE", subject, score, kf.RATE_COMMENTS))


@catub.cat_cmd(
    pattern="rizz(?:\s|$)([\s\S]*)",
    command=("rizz", plugin_category),
    info={
        "header": "Rizz meter 0–100.",
        "usage": ["{tr}rizz", "{tr}rizz <name>", "{tr}rizz <reply>"],
    },
)
async def rizz(event):
    "Rizz meter."
    name = await _who(event)
    score = kf.meter(name, "rizz")
    await edit_or_reply(
        event,
        _meter_block("RIZZ", name, score, kf.RATE_COMMENTS)
        + f"\n💬 {kf.pick(kf.RIZZ_LINES)}",
    )


@catub.cat_cmd(
    pattern="rizzup(?:\s|$)([\s\S]*)",
    command=("rizzup", plugin_category),
    info={
        "header": "Deploy a pickup closer.",
        "usage": ["{tr}rizzup", "{tr}rizzup <name>", "{tr}rizzup <reply>"],
    },
)
async def rizzup(event):
    "Pickup closer."
    name = await _who(event)
    await edit_or_reply(event, f"💬 {kf.fill(kf.pick(kf.PICKUPS), name=name)}")


@catub.cat_cmd(
    pattern="aura(?:\s|$)([\s\S]*)",
    command=("aura", plugin_category),
    info={
        "header": "Aura score meter (joke).",
        "usage": ["{tr}aura", "{tr}aura <name>", "{tr}aura <reply>"],
        "note": "Different from {tr}fu reaction.",
    },
)
async def aura_meter(event):
    "Aura score meter."
    name = await _who(event)
    score = kf.meter(name, "aura")
    await edit_or_reply(event, _meter_block("AURA", name, score, kf.RATE_COMMENTS))


@catub.cat_cmd(
    pattern="based(?:\s|$)([\s\S]*)",
    command=("based", plugin_category),
    info={
        "header": "Based-o-meter.",
        "usage": ["{tr}based", "{tr}based <name>", "{tr}based <reply>"],
    },
)
async def based(event):
    "Based meter."
    name = await _who(event)
    score = kf.meter(name, "based")
    await edit_or_reply(event, _meter_block("BASED", name, score, kf.RATE_COMMENTS))


@catub.cat_cmd(
    pattern="cringe(?:\s|$)([\s\S]*)",
    command=("cringe", plugin_category),
    info={
        "header": "Cringe-o-meter.",
        "usage": ["{tr}cringe", "{tr}cringe <name>", "{tr}cringe <reply>"],
    },
)
async def cringe(event):
    "Cringe meter."
    name = await _who(event)
    score = kf.meter(name, "cringe")
    await edit_or_reply(event, _meter_block("CRINGE", name, score, kf.RATE_COMMENTS))


@catub.cat_cmd(
    pattern="gayrate(?:\s|$)([\s\S]*)",
    command=("gayrate", plugin_category),
    info={
        "header": "Joke gay-rate percentage meme.",
        "usage": ["{tr}gayrate", "{tr}gayrate <name>", "{tr}gayrate <reply>"],
        "note": "Pure joke meter. Not serious.",
    },
)
async def gayrate(event):
    "Joke gayrate meter."
    name = await _who(event)
    score = kf.meter(name, "gayrate")
    await edit_or_reply(
        event,
        f"**GAYRATE — {name}**\n`[{kf.bar(score)}]` **{score}%**\n_{kf.pick(kf.RATE_COMMENTS[_tier(score)])}_",
    )


@catub.cat_cmd(
    pattern="simprate(?:\s|$)([\s\S]*)",
    command=("simprate", plugin_category),
    info={
        "header": "Simp-o-meter joke percentage.",
        "usage": ["{tr}simprate", "{tr}simprate <name>", "{tr}simprate <reply>"],
    },
)
async def simprate(event):
    "Simp rate meter."
    name = await _who(event)
    score = kf.meter(name, "simprate")
    await edit_or_reply(
        event,
        f"**SIMPRATE — {name}**\n`[{kf.bar(score)}]` **{score}%**\n_{kf.pick(kf.RATE_COMMENTS[_tier(score)])}_",
    )
