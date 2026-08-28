# Love, romance, passion & spicy commands — texts, animations, stickers.
import asyncio
import random
import textwrap
from collections import deque
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

from ..helpers.functions import kittyfun_banks as kf
from ..helpers.functions import kittylove_banks as kl
from ..helpers.functions import deEmojify
from ..helpers.utils import reply_id
from . import ALIVE_NAME, catub, edit_delete, edit_or_reply

plugin_category = "fun"

_LOVE_RGB = [
    (255, 105, 180),
    (220, 20, 60),
    (255, 182, 193),
    (199, 21, 133),
    (255, 20, 147),
]
_FALLBACK_FONT = (
    "https://github.com/TgCatUB/CatUserbot-Resources/blob/master/"
    "Resources/Spotify/ArialUnicodeMS.ttf?raw=true"
)


async def _who(event, group: int = 1, fallback: str | None = None) -> str:
    reply = await event.get_reply_message()
    if reply and reply.sender:
        return reply.sender.first_name or ALIVE_NAME
    arg = (event.pattern_match.group(group) or "").strip()
    fb = fallback or ALIVE_NAME or "love"
    return kf.clean_name(arg, fb)


async def _two_names(event):
    raw = (event.pattern_match.group(1) or "").strip()
    reply = await event.get_reply_message()
    reply_name = reply.sender.first_name if reply and reply.sender else None
    if raw:
        parts = raw.replace("|", " ").replace("&", " ").split()
        if len(parts) >= 2:
            return kf.clean_name(parts[0]), kf.clean_name(parts[1])
        if reply_name:
            return reply_name, kf.clean_name(parts[0])
        return kf.clean_name(parts[0]), ALIVE_NAME or "You"
    if reply_name:
        return reply_name, ALIVE_NAME or "You"
    return ALIVE_NAME or "You", "Destiny"


async def _animate(event, frames: list[str], delay: float = 0.45, first: str = "`…`"):
    catevent = await edit_or_reply(event, first)
    for frame in frames:
        await asyncio.sleep(delay)
        await catevent.edit(frame)


async def _send_love_sticker(event, text: str):
    """Pink love-themed text sticker."""
    import os
    import requests

    sticktext = deEmojify(text or "love")
    sticktext = "\n".join(textwrap.wrap(sticktext, width=12))
    rgb = random.choice(_LOVE_RGB)
    image = Image.new("RGBA", (512, 512), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    fontsize = 200
    font_path = "./temp/ArialUnicodeMS.ttf"
    if not os.path.exists(font_path):
        try:
            resp = requests.get(_FALLBACK_FONT, timeout=15)
            os.makedirs("./temp", exist_ok=True)
            with open(font_path, "wb") as f:
                f.write(resp.content)
        except Exception:
            return await edit_delete(event, "`Could not load font for love sticker.`")
    font = ImageFont.truetype(font_path, size=fontsize)

    def _size(d, txt, f):
        bbox = d.textbbox((0, 0), txt, font=f)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    while _size(draw, sticktext, font)[0] > 480 or _size(draw, sticktext, font)[1] > 480:
        fontsize -= 3
        font = ImageFont.truetype(font_path, size=fontsize)
    w, h = _size(draw, sticktext, font)
    draw.multiline_text(((512 - w) / 2, (512 - h) / 2), sticktext, font=font, fill=rgb)
    stream = BytesIO()
    stream.name = "love.webp"
    image.save(stream, "WebP")
    stream.seek(0)
    reply_to = await reply_id(event)
    await event.delete()
    await event.client.send_file(event.chat_id, stream, reply_to=reply_to)


# ─── Sweet texts ──────────────────────────────────────────────────────────────

@catub.cat_cmd(
    pattern="love$",
    command=("love", plugin_category),
    info={
        "header": "Random romantic love line.",
        "usage": "{tr}love",
        "examples": "{tr}love",
    },
)
async def love_random(event):
    "Random love line."
    await edit_or_reply(event, f"💕 {kl.pick(kl.LOVE_RANDOM)}")


@catub.cat_cmd(
    pattern="lovemorning(?:\s|$)([\s\S]*)",
    command=("lovemorning", plugin_category),
    info={
        "header": "Morning love message for someone.",
        "usage": ["{tr}lovemorning", "{tr}lovemorning <name>", "{tr}lovemorning <reply>"],
        "examples": "{tr}lovemorning babe",
    },
)
async def love_morning(event):
    "Morning love text."
    name = await _who(event)
    await edit_or_reply(event, f"🌅 {kf.fill(kl.pick(kl.LOVE_MORNING), name=name)}")


@catub.cat_cmd(
    pattern="lovenight(?:\s|$)([\s\S]*)",
    command=("lovenight", plugin_category),
    info={
        "header": "Goodnight love message.",
        "usage": ["{tr}lovenight", "{tr}lovenight <name>", "{tr}lovenight <reply>"],
        "examples": "{tr}lovenight darling",
    },
)
async def love_night(event):
    "Goodnight love text."
    name = await _who(event)
    await edit_or_reply(event, f"🌙 {kf.fill(kl.pick(kl.LOVE_NIGHT), name=name)}")


@catub.cat_cmd(
    pattern="lovepoem(?:\s|$)([\s\S]*)",
    command=("lovepoem", plugin_category),
    info={
        "header": "Poetic love verse for someone.",
        "usage": ["{tr}lovepoem", "{tr}lovepoem <name>", "{tr}lovepoem <reply>"],
    },
)
async def love_poem(event):
    "Love poem."
    name = await _who(event)
    await edit_or_reply(event, kf.fill(kl.pick(kl.LOVE_POEMS), name=name))


@catub.cat_cmd(
    pattern="lovehaiku$",
    command=("lovehaiku", plugin_category),
    info={
        "header": "Random love haiku.",
        "usage": "{tr}lovehaiku",
    },
)
async def love_haiku(event):
    "Love haiku."
    await edit_or_reply(event, f"🍃 {kl.pick(kl.LOVE_HAIKU)}")


@catub.cat_cmd(
    pattern="soulmate(?:\s|$)([\s\S]*)",
    command=("soulmate", plugin_category),
    info={
        "header": "Soulmate declaration.",
        "usage": ["{tr}soulmate", "{tr}soulmate <name>", "{tr}soulmate <reply>"],
    },
)
async def soulmate(event):
    "Soulmate line."
    name = await _who(event)
    await edit_or_reply(event, f"✨ {kf.fill(kl.pick(kl.SOULMATE_LINES), name=name)}")


@catub.cat_cmd(
    pattern="foreverlove(?:\s|$)([\s\S]*)",
    command=("foreverlove", plugin_category),
    info={
        "header": "Forever / eternity love line.",
        "usage": ["{tr}foreverlove", "{tr}foreverlove <name>", "{tr}foreverlove <reply>"],
    },
)
async def forever_love(event):
    "Forever love."
    name = await _who(event)
    await edit_or_reply(event, f"♾️ {kf.fill(kl.pick(kl.FOREVER_LINES), name=name)}")


@catub.cat_cmd(
    pattern="weddingpoem(?:\s|$)([\s\S]*)",
    command=("weddingpoem", plugin_category),
    info={
        "header": "Chaotic wedding vow poem for two people.",
        "usage": ["{tr}weddingpoem <a> <b>", "{tr}weddingpoem <reply> <name>"],
        "examples": "{tr}weddingpoem Alice Bob",
    },
)
async def wedding_poem(event):
    "Wedding poem."
    a, b = await _two_names(event)
    await edit_or_reply(event, kf.fill(kl.pick(kl.WEDDING_VOWS), a=a, b=b))


@catub.cat_cmd(
    pattern="crushsay(?:\s|$)([\s\S]*)",
    command=("crushsay", plugin_category),
    info={
        "header": "Cute crush confession line.",
        "usage": ["{tr}crushsay", "{tr}crushsay <name>", "{tr}crushsay <reply>"],
    },
)
async def crush_say(event):
    "Crush confession."
    name = await _who(event)
    await edit_or_reply(event, f"💘 {kf.fill(kl.pick(kl.CRUSH_CONFESS), name=name)}")


@catub.cat_cmd(
    pattern="crushmeter(?:\s|$)([\s\S]*)",
    command=("crushmeter", plugin_category),
    info={
        "header": "How hard you're crushing on someone (%).",
        "usage": ["{tr}crushmeter", "{tr}crushmeter <name>", "{tr}crushmeter <reply>"],
    },
)
async def crush_meter(event):
    "Crush meter."
    name = await _who(event)
    score = kf.meter(f"crush|{name}", "heart")
    await edit_or_reply(
        event,
        f"💘 **CRUSHMETER — {name}**\n"
        f"`[{kf.bar(score)}]` **{score}%**\n"
        f"{kl.crush_meter_comment(score)}",
    )


@catub.cat_cmd(
    pattern="loverose(?:\s|$)([\s\S]*)",
    command=("loverose", plugin_category),
    info={
        "header": "ASCII rose + love quote for someone.",
        "usage": ["{tr}loverose", "{tr}loverose <name>", "{tr}loverose <reply>"],
    },
)
async def love_rose(event):
    "Rose art."
    name = await _who(event)
    quote = kl.pick(kl.LOVE_RANDOM)
    line = "—".join(name[:14]) if len(name) > 2 else "—love—"
    art = kf.fill(
        kl.ROSE_TEMPLATE,
        name=name,
        quote=quote,
        line=line.center(14, "—"),
    )
    await edit_or_reply(event, art)


# ─── Letters & dares ──────────────────────────────────────────────────────────

@catub.cat_cmd(
    pattern="loveletter(?:\s|$)([\s\S]*)",
    command=("loveletter", plugin_category),
    info={
        "header": "Full love letter (instant or animated with -a).",
        "usage": [
            "{tr}loveletter <name>",
            "{tr}loveletter -a <name>",
            "{tr}loveletter <reply>",
        ],
        "note": "Add `-a` for typewriter animation.",
    },
)
async def love_letter(event):
    "Love letter."
    raw = (event.pattern_match.group(1) or "").strip()
    animate = raw.startswith("-a")
    if animate:
        raw = raw[2:].strip()
    reply = await event.get_reply_message()
    if reply and reply.sender and not raw:
        name = reply.sender.first_name
    else:
        name = kf.clean_name(raw, "my love")
    sender = ALIVE_NAME or "Yours"
    letter = kf.fill(kl.pick(kl.LOVE_LETTERS), name=name, sender=sender)
    if animate:
        frames = [
            kf.fill(f, name=name, sender=sender)
            for f in kl.LOVE_LETTER_BUILD
        ]
        frames[-1] = letter
        await _animate(event, frames, delay=0.55, first="`writing…`")
    else:
        await edit_or_reply(event, letter)


@catub.cat_cmd(
    pattern="lovedare(?:\s|$)([\s\S]*)",
    command=("lovedare", plugin_category),
    info={
        "header": "Sweet romantic dare for your crush/partner.",
        "usage": ["{tr}lovedare", "{tr}lovedare <name>", "{tr}lovedare <reply>"],
    },
)
async def love_dare(event):
    "Sweet love dare."
    name = await _who(event)
    await edit_or_reply(event, f"🎲 **LOVE DARE**\n{kf.fill(kl.pick(kl.LOVE_DARES_SWEET), name=name)}")


# ─── Spicy / dirty texts ──────────────────────────────────────────────────────

@catub.cat_cmd(
    pattern="desire(?:\s|$)([\s\S]*)",
    command=("desire", plugin_category),
    info={
        "header": "Steamy desire line (sensual, not crude).",
        "usage": ["{tr}desire", "{tr}desire <name>", "{tr}desire <reply>"],
    },
)
async def desire(event):
    "Desire line."
    name = await _who(event)
    await edit_or_reply(event, f"🔥 {kf.fill(kl.pick(kl.DESIRE_LINES), name=name)}")


@catub.cat_cmd(
    pattern="dirtytalk(?:\s|$)([\s\S]*)",
    command=("dirtytalk", plugin_category),
    info={
        "header": "Explicit dirty talk line (adult).",
        "usage": ["{tr}dirtytalk", "{tr}dirtytalk <name>", "{tr}dirtytalk <reply>"],
        "note": "18+ explicit humor.",
    },
)
async def dirty_talk(event):
    "Dirty talk."
    name = await _who(event)
    await edit_or_reply(event, f"😈 {kf.fill(kl.pick(kl.DIRTY_TALK), name=name)}")


@catub.cat_cmd(
    pattern="(?:reallydirty|rdirty)(?:\s|$)([\s\S]*)",
    command=("reallydirty", plugin_category),
    info={
        "header": "Really explicit dirty line (18+).",
        "usage": [
            "{tr}reallydirty",
            "{tr}rdirty",
            "{tr}reallydirty <name>",
            "{tr}reallydirty <reply>",
        ],
        "note": "Maximum spice. Private chats only.",
    },
)
async def really_dirty(event):
    "Really dirty."
    name = await _who(event)
    await edit_or_reply(event, f"🫦 {kf.fill(kl.pick(kl.REALLY_DIRTY), name=name)}")


# ─── Animations ───────────────────────────────────────────────────────────────

@catub.cat_cmd(
    pattern="heartstorm$",
    command=("heartstorm", plugin_category),
    info={
        "header": "Heart rain animation.",
        "usage": "{tr}heartstorm",
    },
)
async def heart_storm(event):
    "Heart storm."
    await _animate(event, kl.HEARTSTORM_FRAMES, delay=0.35)


@catub.cat_cmd(
    pattern="heartbeat$",
    command=("heartbeat", plugin_category),
    info={
        "header": "Pulsing heartbeat animation.",
        "usage": "{tr}heartbeat",
    },
)
async def heart_beat(event):
    "Heartbeat."
    await _animate(event, kl.HEARTBEAT_FRAMES, delay=0.3)


@catub.cat_cmd(
    pattern="lovekiss(?:\s|$)([\s\S]*)",
    command=("lovekiss", plugin_category),
    info={
        "header": "Kiss delivery animation.",
        "usage": ["{tr}lovekiss", "{tr}lovekiss <name>", "{tr}lovekiss <reply>"],
    },
)
async def love_kiss(event):
    "Kiss animation."
    target = await _who(event, fallback="you")
    sender = ALIVE_NAME or "Me"
    frames = [kf.fill(f, name=target, target=target, sender=sender) for f in kl.KISS_FRAMES]
    await _animate(event, frames, delay=0.45)


@catub.cat_cmd(
    pattern="lovespell(?:\s|$)([\s\S]*)",
    command=("lovespell", plugin_category),
    info={
        "header": "Cast a love spell animation → romantic line.",
        "usage": ["{tr}lovespell", "{tr}lovespell <name>", "{tr}lovespell <reply>"],
    },
)
async def love_spell(event):
    "Love spell."
    name = await _who(event)
    line = kf.fill(kl.pick(kl.LOVE_RANDOM), name=name)
    frames = [kf.fill(f, line=line, name=name) for f in kl.LOVE_SPELL_FRAMES]
    await _animate(event, frames, delay=0.5, first="`casting…`")


@catub.cat_cmd(
    pattern="afterdark(?:\s|$)([\s\S]*)",
    command=("afterdark", plugin_category),
    info={
        "header": "After-dark seduction mood animation.",
        "usage": ["{tr}afterdark", "{tr}afterdark <name>", "{tr}afterdark <reply>"],
    },
)
async def after_dark(event):
    "After dark."
    name = await _who(event)
    line = kf.fill(kl.pick(kl.DESIRE_LINES), name=name)
    frames = [kf.fill(f, line=line, name=name) for f in kl.AFTERDARK_FRAMES]
    await _animate(event, frames, delay=0.5, first="`sunset…`")


@catub.cat_cmd(
    pattern="heartburst(?:\s|$)([\s\S]*)",
    command=("heartburst", plugin_category),
    info={
        "header": "Exploding hearts — I love you animation.",
        "usage": ["{tr}heartburst", "{tr}heartburst <name>", "{tr}heartburst <reply>"],
    },
)
async def heart_burst(event):
    "Heart burst ILU."
    target = await _who(event, fallback="you")
    frames = [kf.fill(f, target=target) for f in kl.HEART_BURST_FRAMES]
    await _animate(event, frames, delay=0.35)


@catub.cat_cmd(
    pattern="loveorbit$",
    command=("loveorbit", plugin_category),
    info={
        "header": "Rotating hearts orbit animation.",
        "usage": "{tr}loveorbit",
    },
)
async def love_orbit(event):
    "Hearts orbit."
    deq = deque(list("💗💕💖💘💝💓💗💕"))
    catevent = await edit_or_reply(event, "`orbiting…`")
    for _ in range(36):
        await asyncio.sleep(0.25)
        ring = "".join(deq)
        await catevent.edit(f"{ring}\n   💗\n{ring}")
        deq.rotate(1)
    await catevent.edit(f"💗 **LOVE ORBIT**\n{kl.HEART_SMALL}\nForever in motion.")


# ─── Sticker ──────────────────────────────────────────────────────────────────

@catub.cat_cmd(
    pattern="lovestcr(?:\s|$)([\s\S]*)",
    command=("lovestcr", plugin_category),
    info={
        "header": "Your love text as a pink sticker.",
        "usage": [
            "{tr}lovestcr <text>",
            "{tr}lovestcr <reply>",
            "{tr}lovestcr (empty = random love line)",
        ],
        "examples": "{tr}lovestcr I adore you",
    },
)
async def love_sticker(event):
    "Love text sticker."
    text = (event.pattern_match.group(1) or "").strip()
    reply = await event.get_reply_message()
    if not text and reply:
        text = reply.text or ""
    if not text:
        text = kl.pick(kl.LOVE_RANDOM)
    await _send_love_sticker(event, text)


@catub.cat_cmd(
    pattern="lovewall(?:\s|$)([\s\S]*)",
    command=("lovewall", plugin_category),
    info={
        "header": "Heart wall ASCII art + custom message.",
        "usage": "{tr}lovewall <message>",
        "examples": "{tr}lovewall you + me = forever",
    },
)
async def love_wall(event):
    "Heart wall art."
    msg = (event.pattern_match.group(1) or "").strip() or kl.pick(kl.LOVE_RANDOM)
    wall = (
        "♥♥♥♥♥♥♥♥♥♥♥♥♥♥♥\n"
        "♥♥♥♥♥♥♥♥♥♥♥♥♥♥♥\n"
        "♥♥♥♥♥♥♥♥♥♥♥♥♥♥♥\n"
        f"♥  {msg[:28]}  ♥\n"
        "♥♥♥♥♥♥♥♥♥♥♥♥♥♥♥\n"
        "♥♥♥♥♥♥♥♥♥♥♥♥♥♥♥\n"
        "♥♥♥♥♥♥♥♥♥♥♥♥♥♥♥"
    )
    await edit_or_reply(event, wall)
