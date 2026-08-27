import asyncio

from ..helpers.functions import kittyfun_banks as kf
from . import ALIVE_NAME, catub, edit_or_reply

plugin_category = "fun"


async def _who(event):
    reply = await event.get_reply_message()
    if reply and reply.sender:
        return reply.sender.first_name or ALIVE_NAME
    arg = (event.pattern_match.group(1) or "").strip()
    return kf.clean_name(arg, ALIVE_NAME or "seeker")


@catub.cat_cmd(
    pattern="fortune$",
    command=("fortune", plugin_category),
    info={"header": "Crack a chaotic fortune cookie.", "usage": "{tr}fortune"},
)
async def fortune(event):
    "Fortune cookie."
    catevent = await edit_or_reply(event, "`cracking cookie…`")
    await asyncio.sleep(0.45)
    await catevent.edit(f"🥠 **Fortune**\n{kf.pick(kf.FORTUNES)}")


@catub.cat_cmd(
    pattern="cookie$",
    command=("cookie", plugin_category),
    info={"header": "Alias of fortune cookie.", "usage": "{tr}cookie"},
)
async def cookie(event):
    "Fortune cookie alias."
    await edit_or_reply(event, f"🥠 {kf.pick(kf.FORTUNES)}")


@catub.cat_cmd(
    pattern="horoscope(?:\s|$)([\s\S]*)",
    command=("horoscope", plugin_category),
    info={
        "header": "Chaotic fake daily horoscope.",
        "usage": ["{tr}horoscope", "{tr}horoscope <sign>"],
        "examples": "{tr}horoscope leo",
    },
)
async def horoscope(event):
    "Fake horoscope."
    arg = (event.pattern_match.group(1) or "").strip().lower()
    signs = {s.lower(): (s, t) for s, t in kf.ZODIAC}
    if arg and arg in signs:
        sign, tip = signs[arg]
    else:
        sign, tip = kf.pick(kf.ZODIAC)
    await edit_or_reply(
        event,
        f"✨ **{sign}**\n{tip}\n_Not financial, medical, or romantic advice._",
    )


@catub.cat_cmd(
    pattern="zodiac(?:\s|$)([\s\S]*)",
    command=("zodiac", plugin_category),
    info={
        "header": "Alias of horoscope.",
        "usage": ["{tr}zodiac", "{tr}zodiac <sign>"],
    },
)
async def zodiac(event):
    "Zodiac alias."
    return await horoscope(event)


@catub.cat_cmd(
    pattern="8ball(?:\s|$)([\s\S]*)",
    command=("8ball", plugin_category),
    info={
        "header": "Magic 8-ball answers.",
        "usage": ["{tr}8ball <question>", "{tr}8ball <reply>"],
        "examples": "{tr}8ball will I cook today",
    },
)
async def eightball(event):
    "Magic 8-ball."
    q = event.pattern_match.group(1).strip()
    if not q:
        reply = await event.get_reply_message()
        q = (reply.text if reply else "") or "???"
    catevent = await edit_or_reply(event, "`shaking…`")
    await asyncio.sleep(0.5)
    await catevent.edit(f"🎱 **Q:** {q[:120]}\n**A:** {kf.pick(kf.EIGHTBALL)}")


@catub.cat_cmd(
    pattern="joke$",
    command=("joke", plugin_category),
    info={
        "header": "Random joke (sometimes dirty).",
        "usage": "{tr}joke",
        "note": "May include dirty humor.",
    },
)
async def joke(event):
    "Joke bank."
    pool = kf.JOKES + kf.DIRTY_JOKES
    await edit_or_reply(event, f"😂 {kf.pick(pool)}")


@catub.cat_cmd(
    pattern="pun$",
    command=("pun", plugin_category),
    info={"header": "Painful pun delivery.", "usage": "{tr}pun"},
)
async def pun(event):
    "Pun bank."
    await edit_or_reply(event, f"🤓 {kf.pick(kf.PUNS)}")


@catub.cat_cmd(
    pattern="dadjoke$",
    command=("dadjoke", plugin_category),
    info={"header": "Dad joke. Groan optional.", "usage": "{tr}dadjoke"},
)
async def dadjoke(event):
    "Dad joke bank."
    await edit_or_reply(event, f"👨 {kf.pick(kf.DAD_JOKES)}")


@catub.cat_cmd(
    pattern="tarot$",
    command=("tarot", plugin_category),
    info={"header": "Absurd 3-card tarot spread.", "usage": "{tr}tarot"},
)
async def tarot(event):
    "Tarot spread."
    catevent = await edit_or_reply(event, "`shuffling chaos…`")
    await asyncio.sleep(0.45)
    cards = [kf.pick(kf.TAROT) for _ in range(3)]
    # unique-ish
    cards = list(dict.fromkeys(cards))
    while len(cards) < 3:
        cards.append(kf.pick(kf.TAROT))
    await catevent.edit(
        "**TAROT SPREAD**\n"
        f"Past: {cards[0]}\n"
        f"Present: {cards[1]}\n"
        f"Future: {cards[2]}\n"
        "_Interpretation: skill issue / main character arc._"
    )


@catub.cat_cmd(
    pattern="prophecy(?:\s|$)([\s\S]*)",
    command=("prophecy", plugin_category),
    info={
        "header": "Dramatic doom prophecy about a target.",
        "usage": ["{tr}prophecy", "{tr}prophecy <name>", "{tr}prophecy <reply>"],
    },
)
async def prophecy(event):
    "Prophecy."
    name = await _who(event)
    catevent = await edit_or_reply(event, "`the oracle convulsing…`")
    await asyncio.sleep(0.5)
    await catevent.edit(f"📜 {kf.fill(kf.pick(kf.PROPHECIES), name=name)}")


@catub.cat_cmd(
    pattern="vibecheck(?:\s|$)([\s\S]*)",
    command=("vibecheck", plugin_category),
    info={
        "header": "Vibe diagnosis animation.",
        "usage": ["{tr}vibecheck", "{tr}vibecheck <name>", "{tr}vibecheck <reply>"],
    },
)
async def vibecheck(event):
    "Vibe check animation."
    name = await _who(event)
    catevent = await edit_or_reply(event, f"`scanning {name}'s vibe…`")
    frames = [
        "📡 aura…",
        "📡 posture…",
        "📡 browser history (redacted)…",
        f"**VIBECHECK — {name}**\n{kf.pick(kf.VIBE_DIAG)}",
    ]
    for frame in frames:
        await asyncio.sleep(0.45)
        await catevent.edit(frame)
