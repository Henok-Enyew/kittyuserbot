# Pillow helpers for generated cards (chat recap, text stories).
#
# Only the fonts shipped in userbot/helpers/styles are used, so rendering is the
# same on every host. Those fonts cover Latin/Cyrillic/Greek but not emoji or
# Ethiopic, so text is filtered through `printable()` before drawing; the full
# text always goes into the Telegram caption instead.

import os
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

_STYLES = os.path.join(os.path.dirname(os.path.dirname(__file__)), "styles")
FONT_BOLD = os.path.join(_STYLES, "ProductSans-BoldItalic.ttf")
FONT_LIGHT = os.path.join(_STYLES, "ProductSans-Light.ttf")


@lru_cache(maxsize=64)
def font(path: str, size: int):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


@lru_cache(maxsize=8)
def _cmap(path: str) -> frozenset:
    try:
        from fontTools.ttLib import TTFont

        return frozenset(TTFont(path).getBestCmap().keys())
    except Exception:
        return frozenset(range(32, 0x250))  # assume basic Latin + Latin-ext


def printable(text: str, path: str = FONT_BOLD) -> str:
    """Drop characters the font can't draw (emoji, Ethiopic...), tidy spaces."""
    cmap = _cmap(path)
    out = "".join(ch for ch in str(text or "") if ch in "\n " or ord(ch) in cmap)
    return " ".join(out.split()) if "\n" not in out else "\n".join(" ".join(l.split()) for l in out.split("\n"))


def text_width(draw: ImageDraw.ImageDraw, text: str, fnt) -> int:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0]


def fit(draw, text: str, fnt, max_width: int) -> str:
    """Truncate a single line with an ellipsis so it fits max_width."""
    if text_width(draw, text, fnt) <= max_width:
        return text
    while text and text_width(draw, text + "…", fnt) > max_width:
        text = text[:-1]
    return text + "…"


def wrap(draw, text: str, fnt, max_width: int) -> list:
    lines = []
    for para in str(text).split("\n"):
        words, cur = para.split(), ""
        if not words:
            lines.append("")
            continue
        for w in words:
            trial = f"{cur} {w}".strip()
            if text_width(draw, trial, fnt) <= max_width:
                cur = trial
                continue
            if cur:
                lines.append(cur)
            while text_width(draw, w, fnt) > max_width and len(w) > 1:  # very long word
                cut = len(w)
                while cut > 1 and text_width(draw, w[:cut], fnt) > max_width:
                    cut -= 1
                lines.append(w[:cut])
                w = w[cut:]
            cur = w
        lines.append(cur)
    return lines


def gradient(size, top, bottom, diagonal=True) -> Image.Image:
    w, h = size
    base = Image.new("RGB", size, top)
    steps = 256
    band = Image.new("RGB", (1, steps))
    for i in range(steps):
        t = i / (steps - 1)
        band.putpixel((0, i), tuple(int(top[c] + (bottom[c] - top[c]) * t) for c in range(3)))
    if diagonal:
        big = band.resize((max(w, h) * 2, max(w, h) * 2))
        big = big.rotate(35, resample=Image.BICUBIC)
        cx, cy = big.width // 2, big.height // 2
        base.paste(big.crop((cx - w // 2, cy - h // 2, cx - w // 2 + w, cy - h // 2 + h)))
    else:
        base.paste(band.resize((w, h)))
    return base


STORY_THEMES = [
    ((255, 94, 98), (255, 153, 102)),  # sunset
    ((67, 97, 238), (114, 9, 183)),  # indigo → purple
    ((17, 153, 142), (56, 239, 125)),  # mint
    ((15, 32, 39), (44, 83, 100)),  # deep sea
    ((238, 9, 121), (255, 106, 0)),  # neon
    ((20, 20, 20), (60, 60, 60)),  # graphite
]


def text_story_image(text: str, theme: int, out_path: str, footer: str = "") -> str:
    """1080x1920 gradient card with centered text, for `.poststory <text>`."""
    W, H = 1080, 1920
    top, bottom = STORY_THEMES[theme % len(STORY_THEMES)]
    img = gradient((W, H), top, bottom)
    draw = ImageDraw.Draw(img)
    text = printable(text, FONT_BOLD) or "…"

    size = 120
    while size > 44:
        fnt = font(FONT_BOLD, size)
        lines = wrap(draw, text, fnt, W - 180)
        line_h = int(size * 1.25)
        if line_h * len(lines) <= H - 600:
            break
        size -= 8
    fnt = font(FONT_BOLD, size)
    lines = wrap(draw, text, fnt, W - 180)
    line_h = int(size * 1.25)
    y = (H - line_h * len(lines)) // 2
    for line in lines:
        x = (W - text_width(draw, line, fnt)) // 2
        draw.text((x + 4, y + 5), line, font=fnt, fill=(0, 0, 0, 90))
        draw.text((x, y), line, font=fnt, fill=(255, 255, 255))
        y += line_h
    if footer:
        f2 = font(FONT_LIGHT, 40)
        footer = printable(footer, FONT_LIGHT)
        draw.text(((W - text_width(draw, footer, f2)) // 2, H - 200), footer, font=f2, fill=(255, 255, 255))
    img.save(out_path, "JPEG", quality=92)
    return out_path
