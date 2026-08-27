import asyncio

from ..helpers.functions import kittyfun_banks as kf
from . import ALIVE_NAME, catub, edit_or_reply

plugin_category = "fun"


async def _who(event):
    reply = await event.get_reply_message()
    if reply and reply.sender:
        return reply.sender.first_name or ALIVE_NAME
    arg = (event.pattern_match.group(1) or "").strip()
    return kf.clean_name(arg, ALIVE_NAME or "You")


@catub.cat_cmd(
    pattern="story(?:\s|$)([\s\S]*)",
    command=("story", plugin_category),
    info={
        "header": "Six-beat micro story starring you / reply.",
        "usage": ["{tr}story", "{tr}story <name>", "{tr}story <reply>"],
    },
)
async def story(event):
    "Micro story animation."
    other = await _who(event)
    hero = ALIVE_NAME or "Hero"
    catevent = await edit_or_reply(event, "`writing…`")
    for beat in kf.STORY_BEATS:
        await asyncio.sleep(0.65)
        await catevent.edit(kf.fill(beat, hero=hero, other=other))


@catub.cat_cmd(
    pattern="karaoke$",
    command=("karaoke", plugin_category),
    info={"header": "Karaoke lyric bounce animation.", "usage": "{tr}karaoke"},
)
async def karaoke(event):
    "Karaoke animation."
    catevent = await edit_or_reply(event, "`mic check…`")
    for line in kf.KARAOKE:
        await asyncio.sleep(0.55)
        await catevent.edit(f"🎤 {line}")


@catub.cat_cmd(
    pattern="debate(?:\s|$)([\s\S]*)",
    command=("debate", plugin_category),
    info={
        "header": "Two-sided argument animation about a topic.",
        "usage": ["{tr}debate <topic>", "{tr}debate <reply>"],
        "examples": "{tr}debate pineapple pizza",
    },
)
async def debate(event):
    "Debate animation."
    topic = event.pattern_match.group(1).strip()
    if not topic:
        reply = await event.get_reply_message()
        topic = (reply.text if reply else "") or "the bit"
    topic = topic[:80]
    catevent = await edit_or_reply(event, f"**DEBATE:** {topic}")
    frames = [
        f"**FOR:** {kf.pick(kf.DEBATE_A)}",
        f"**AGAINST:** {kf.pick(kf.DEBATE_B)}",
        f"**FOR:** {kf.pick(kf.DEBATE_A)}",
        f"**AGAINST:** {kf.pick(kf.DEBATE_B)}",
        f"**MODERATOR ({ALIVE_NAME}):** both of you are wrong. Next topic.",
    ]
    for frame in frames:
        await asyncio.sleep(0.6)
        await catevent.edit(f"**DEBATE:** {topic}\n\n{frame}")


@catub.cat_cmd(
    pattern="court(?:\s|$)([\s\S]*)",
    command=("court", plugin_category),
    info={
        "header": "Fake trial; verdict on target.",
        "usage": ["{tr}court", "{tr}court <name>", "{tr}court <reply>"],
    },
)
async def court(event):
    "Court animation."
    name = await _who(event)
    catevent = await edit_or_reply(event, "`all rise…`")
    for frame in kf.COURT_FRAMES:
        await asyncio.sleep(0.55)
        await catevent.edit(kf.fill(frame, name=name))


@catub.cat_cmd(
    pattern="podcast(?:\s|$)([\s\S]*)",
    command=("podcast", plugin_category),
    info={
        "header": "Fake podcast transcript drops.",
        "usage": ["{tr}podcast", "{tr}podcast <guest>", "{tr}podcast <reply>"],
    },
)
async def podcast(event):
    "Podcast transcript animation."
    name = await _who(event)
    catevent = await edit_or_reply(event, "`recording…`")
    for frame in kf.PODCAST:
        await asyncio.sleep(0.6)
        await catevent.edit(kf.fill(frame, name=name))


@catub.cat_cmd(
    pattern="recap(?:\s|$)([\s\S]*)",
    command=("recap", plugin_category),
    info={
        "header": "Previously on this chat… absurd recap.",
        "usage": ["{tr}recap", "{tr}recap <name>", "{tr}recap <reply>"],
    },
)
async def recap(event):
    "Chat recap animation."
    name = await _who(event)
    catevent = await edit_or_reply(event, "`previously…`")
    for frame in kf.RECAP:
        await asyncio.sleep(0.5)
        await catevent.edit(kf.fill(frame, name=name))


@catub.cat_cmd(
    pattern="npc$",
    command=("npc", plugin_category),
    info={"header": "Spawn a cursed NPC into the chat.", "usage": "{tr}npc"},
)
async def npc(event):
    "NPC generator."
    catevent = await edit_or_reply(event, "`rolling NPC…`")
    await asyncio.sleep(0.4)
    await catevent.edit(
        f"**NPC ENTERS THE CHAT**\n{kf.pick(kf.NPCS)}\nThey sit down. They will not leave."
    )


@catub.cat_cmd(
    pattern="quest$",
    command=("quest", plugin_category),
    info={"header": "Mini text RPG encounter → loot.", "usage": "{tr}quest"},
)
async def quest(event):
    "Mini quest animation."
    catevent = await edit_or_reply(event, "`entering dungeon…`")
    for frame in kf.QUEST_FRAMES:
        await asyncio.sleep(0.55)
        await catevent.edit(frame)


@catub.cat_cmd(
    pattern="adbreak$",
    command=("adbreak", plugin_category),
    info={"header": "Fake sponsor read mid-chat.", "usage": "{tr}adbreak"},
)
async def adbreak(event):
    "Ad break."
    await edit_or_reply(event, kf.pick(kf.ADS))


@catub.cat_cmd(
    pattern="plotarmor(?:\s|$)([\s\S]*)",
    command=("plotarmor", plugin_category),
    info={
        "header": "Cinematic save-from-death tropes.",
        "usage": ["{tr}plotarmor", "{tr}plotarmor <name>", "{tr}plotarmor <reply>"],
    },
)
async def plotarmor(event):
    "Plot armor animation."
    name = await _who(event)
    catevent = await edit_or_reply(event, "`roll cameras…`")
    for frame in kf.PLOT_ARMOR:
        await asyncio.sleep(0.55)
        await catevent.edit(kf.fill(frame, name=name))
