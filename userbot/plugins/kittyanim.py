import asyncio

from ..helpers.functions import kittyfun_banks as kf
from . import ALIVE_NAME, catub, edit_or_reply

plugin_category = "fun"


async def _target(event, fallback=None):
    fallback = fallback or ALIVE_NAME or "someone"
    reply = await event.get_reply_message()
    if reply and reply.sender:
        return reply.sender.first_name or fallback
    arg = (event.pattern_match.group(1) or "").strip() if event.pattern_match.lastindex else ""
    return kf.clean_name(arg, fallback)


@catub.cat_cmd(
    pattern="glitchtxt(?:\s|$)([\s\S]*)",
    command=("glitchtxt", plugin_category),
    info={
        "header": "Corrupt text into cursed zalgo frames.",
        "usage": ["{tr}glitchtxt <text>", "{tr}glitchtxt <reply>"],
        "examples": "{tr}glitchtxt hello",
    },
)
async def glitchtxt(event):
    "Text corruption animation."
    text = event.pattern_match.group(1).strip()
    if not text:
        reply = await event.get_reply_message()
        text = (reply.text if reply else "") or "ERROR"
    catevent = await edit_or_reply(event, "`corrupting…`")
    for i in range(1, 6):
        await asyncio.sleep(0.45)
        await catevent.edit(kf.zalgo(text[:120], intensity=i))
    await asyncio.sleep(0.4)
    await catevent.edit(f"`stable again:`\n{text[:200]}")


@catub.cat_cmd(
    pattern="matrix$",
    command=("matrix", plugin_category),
    info={"header": "Fake matrix rain then punchline.", "usage": "{tr}matrix"},
)
async def matrix_cmd(event):
    "Matrix rain animation."
    catevent = await edit_or_reply(event, "`wake up, neo…`")
    frames = [
        "010010\n101101\n010110",
        "1 0 1 0 1\n0 1 0 1 0\n1 0 1 0 1",
        "▓▓░▓▓░\n░▓▓░▓▓\n▓▓░▓▓░",
        "`FOLLOW THE WHITE RABBIT`",
        f"`jk it's just {ALIVE_NAME} refreshing memes`",
    ]
    for frame in frames:
        await asyncio.sleep(0.55)
        await catevent.edit(frame)


@catub.cat_cmd(
    pattern="radar(?:\s|$)([\s\S]*)",
    command=("radar", plugin_category),
    info={
        "header": "Scan and acquire a target.",
        "usage": ["{tr}radar", "{tr}radar <name>", "{tr}radar <reply>"],
    },
)
async def radar(event):
    "Radar scan animation."
    name = await _target(event)
    catevent = await edit_or_reply(event, "`initializing radar…`")
    frames = [
        "📡 [·····]",
        "📡 [•····]",
        "📡 [··•··]",
        "📡 [····•]",
        f"**TARGET ACQUIRED:** {name}\nThreat level: chaotic neutral",
    ]
    for frame in frames:
        await asyncio.sleep(0.4)
        await catevent.edit(frame)


@catub.cat_cmd(
    pattern="nuke$",
    command=("nuke", plugin_category),
    info={
        "header": "Cartoon nuke countdown (joke only).",
        "usage": "{tr}nuke",
        "note": "Pure comedy animation. Not real.",
    },
)
async def nuke(event):
    "Cartoon nuke animation."
    catevent = await edit_or_reply(event, "`arming comedy warhead…`")
    for n in ("3", "2", "1"):
        await asyncio.sleep(0.6)
        await catevent.edit(f"**{n}**")
    await asyncio.sleep(0.5)
    await catevent.edit("```\n    _.-^^---....,,--\n _--                  --_\n<                        >)\n|                         |\n \\._                   _./\n    ``` --. . , ; .--'''\n          `  .`.\nBOOM (confetti edition)\n```")
    await asyncio.sleep(0.8)
    await catevent.edit("`Everyone is fine. It was glitter.`")


@catub.cat_cmd(
    pattern="portal$",
    command=("portal", plugin_category),
    info={"header": "Open a dimensional rift animation.", "usage": "{tr}portal"},
)
async def portal(event):
    "Portal animation."
    catevent = await edit_or_reply(event, "`ripping spacetime…`")
    frames = [
        "·",
        "◦ ○ ◦",
        "(( ○ ))",
        "((( 🌀 )))",
        "🌀 *whoosh*",
        f"You fell out next to {ALIVE_NAME}'s snack drawer.",
    ]
    for frame in frames:
        await asyncio.sleep(0.45)
        await catevent.edit(frame)


@catub.cat_cmd(
    pattern="reboot$",
    command=("reboot", plugin_category),
    info={"header": "Fake OS kernel panic then kitty reboot.", "usage": "{tr}reboot"},
)
async def reboot(event):
    "Fake reboot animation."
    catevent = await edit_or_reply(event, "`kernel panic — not syncing`")
    frames = [
        "```\nBUG: soft lockup - CPU#0 stuck\n```",
        "`dumping stack…`",
        "`rebooting in 3…`",
        "`rebooting in 2…`",
        "`rebooting in 1…`",
        f"🐱 **KittyOS** booted\nWelcome back, {ALIVE_NAME}.\nUptime: emotional.",
    ]
    for frame in frames:
        await asyncio.sleep(0.5)
        await catevent.edit(frame)


@catub.cat_cmd(
    pattern="bossfight(?:\s|$)([\s\S]*)",
    command=("bossfight", plugin_category),
    info={
        "header": "RPG boss fight vs a user.",
        "usage": ["{tr}bossfight", "{tr}bossfight <name>", "{tr}bossfight <reply>"],
    },
)
async def bossfight(event):
    "Boss fight animation."
    name = await _target(event)
    catevent = await edit_or_reply(event, f"`engaging {name}…`")
    frames = [
        f"**BOSS:** {name}\nHP `[{kf.bar(100)}]` 100%",
        f"**BOSS:** {name}\nHP `[{kf.bar(72)}]` 72%\nYou used: Side‑Eye",
        f"**BOSS:** {name}\nHP `[{kf.bar(41)}]` 41%\nCritical hit: Receipts",
        f"**BOSS:** {name}\nHP `[{kf.bar(8)}]` 8%\n{name} is enraged!",
        f"**VICTORY**\n{name} dropped: {kf.pick(kf.LOOT_REWARDS)}",
    ]
    for frame in frames:
        await asyncio.sleep(0.65)
        await catevent.edit(frame)


@catub.cat_cmd(
    pattern="lootbox$",
    command=("lootbox", plugin_category),
    info={"header": "Spin a cursed lootbox.", "usage": "{tr}lootbox"},
)
async def lootbox(event):
    "Lootbox spin animation."
    catevent = await edit_or_reply(event, "`opening lootbox…`")
    rarities = ["Common", "Uncommon", "Rare", "Epic", "LEGENDARY", "Mythic (fake)"]
    for r in rarities:
        await asyncio.sleep(0.35)
        await catevent.edit(f"🎁 **{r}** ?")
    await asyncio.sleep(0.4)
    await catevent.edit(
        f"🎁 You won: **{kf.pick(kf.LOOT_REWARDS)}**\n(Pity system not included.)"
    )


@catub.cat_cmd(
    pattern="typewriter(?:\s|$)([\s\S]*)",
    command=("typewriter", plugin_category),
    info={
        "header": "Type text out letter by letter.",
        "usage": ["{tr}typewriter <text>", "{tr}typewriter <reply>"],
        "examples": "{tr}typewriter I have a confession",
    },
)
async def typewriter(event):
    "Typewriter animation."
    text = event.pattern_match.group(1).strip()
    if not text:
        reply = await event.get_reply_message()
        text = (reply.text if reply else "") or kf.pick(kf.ROAST_MILD).format(name=ALIVE_NAME)
    text = text[:120]
    catevent = await edit_or_reply(event, "` `")
    buf = ""
    for ch in text:
        buf += ch
        await catevent.edit(f"`{buf}▌`")
        await asyncio.sleep(0.05)
    await catevent.edit(f"`{buf}`")


@catub.cat_cmd(
    pattern="zoomin$",
    command=("zoomin", plugin_category),
    info={"header": "Emoji zoom-in panic animation.", "usage": "{tr}zoomin"},
)
async def zoomin(event):
    "Zoom panic animation."
    catevent = await edit_or_reply(event, "👀")
    frames = ["👀", "👁️", "👀👀", "👁️👁️👁️", "😱", "I SAW TOO MUCH"]
    for frame in frames:
        await asyncio.sleep(0.4)
        await catevent.edit(frame)


@catub.cat_cmd(
    pattern="buffering$",
    command=("buffering", plugin_category),
    info={"header": "Cursed loading tips animation.", "usage": "{tr}buffering"},
)
async def buffering(event):
    "Buffering tips animation."
    catevent = await edit_or_reply(event, "`loading…`")
    for tip in kf.BUFFER_TIPS:
        await asyncio.sleep(0.55)
        await catevent.edit(f"⏳ {tip}")
    await catevent.edit("`done. personality still pending.`")


@catub.cat_cmd(
    pattern="finale$",
    command=("finale", plugin_category),
    info={"header": "Over-the-top victory confetti.", "usage": "{tr}finale"},
)
async def finale(event):
    "Victory finale animation."
    catevent = await edit_or_reply(event, "`rolling credits…`")
    frames = [
        "✨",
        "✨🎉✨",
        "🎊✨🎉✨🎊",
        f"**FINALE**\n{ALIVE_NAME} wins at existing.",
        "👏👏👏\nEncore denied.",
    ]
    for frame in frames:
        await asyncio.sleep(0.45)
        await catevent.edit(frame)
