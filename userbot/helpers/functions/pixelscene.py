# Pixel-art renderer for Kitty and the living profile photo.
#
# Everything is drawn on a tiny 80x80 canvas and scaled up with nearest-neighbour,
# so it stays crisp pixel art at any size (640x640 for a profile photo). Pure
# Pillow, no assets: sprites are the string grids below.
#
#   render_scene(state, "city" | "kitty" | "both")  -> PIL.Image (640x640)
#   render_card(kitty, signals, state)              -> PIL.Image (960x540) for .kitty
#   scene_signature(state, scene)                   -> str, changes only when the picture would
#
# Telegram shows profile photos as circles, so the important parts (your tower,
# Kitty) stay in the middle.
from __future__ import annotations

import hashlib
import math
import os
import random
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Iterable, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

RGB = Tuple[int, int, int]
BASE = 80  # logical canvas size
PFP_SIZE = 640

_FONTS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts")
PIXEL_FONT = os.path.join(_FONTS, "pressstart.ttf")


# --------------------------------------------------------------------------- #
# Scene description
# --------------------------------------------------------------------------- #


@dataclass
class SceneState:
    phase: str = "night"  # night | dawn | day | dusk
    weather: str = "clear"  # clear | cloudy | fog | drizzle | rain | storm
    awake: bool = True
    solved: int = 0  # problems solved today -> lit windows in your tower
    streak: int = 0
    moon: float = 0.5  # 0 new .. 0.5 full .. 1
    kitty_mood: Optional[str] = None  # None = no cat in the scene
    kitty_stage: str = "kitten"
    kitty_coat: str = "orange"
    seed: int = 7  # skyline layout; stable per account


def scene_signature(state: SceneState, scene: str) -> str:
    """Only the things that change the picture. Used to skip identical uploads."""
    moon_step = int(state.moon * 8 + 0.5) % 8 if state.phase == "night" else -1
    parts = (scene, state.phase, state.weather, state.awake, min(state.solved, TOWER_WINDOWS + 1),
             _streak_bucket(state.streak), moon_step, state.kitty_mood if scene != "city" else None,
             state.kitty_stage if scene != "city" else None, state.kitty_coat if scene != "city" else None,
             state.seed)
    return hashlib.sha1(repr(parts).encode()).hexdigest()[:16]


def _streak_bucket(streak: int) -> int:
    return streak if streak < 1000 else 1000


# --------------------------------------------------------------------------- #
# Kitty sprites
#   . clear  o outline  f fur  d dark fur/stripes  w white  p pink (ears)
#   n nose   e eye      h eye highlight
# --------------------------------------------------------------------------- #

SIT = (
    "..o.......o.....",
    ".opo.....opo....",
    ".opfooooofpo....",
    "offfffdfffffo...",
    "offffdfdffffo...",
    "ofhefffffhefo...",
    "ofeefffffeefo...",
    "offffwnwffffo...",
    ".offwowowffo....",
    "..oowwwwwoo.....",
    "..ofwwwwwfo..oo.",
    ".odfwwwwwfdo.ofo",
    ".offwwwwwffoofo.",
    ".odffwwwffdofo..",
    ".owwfffffwwoo...",
    "..ooooooooooo...",
)
SIT_EYES = ((5, 2), (5, 3), (5, 9), (5, 10), (6, 2), (6, 3), (6, 9), (6, 10))
SIT_CHEEKS = ((7, 1), (7, 11))
SIT_MOUTH = (8, 6)

KITTEN = (
    ".o........o...",
    "opo......opo..",
    "opfoooooofpo..",
    "offffdffffffo.",
    "offfdfdfffffo.",
    "ofhefffffhefo.",
    "ofeefffffeefo.",
    "offffwnwffffo.",
    ".offwwwwwffo..",
    "..oowwwwwoo...",
    "..ofwwwwwfo.o.",
    "..owwfffwwoofo",
    "...ooooooooo..",
)
KITTEN_EYES = ((5, 2), (5, 3), (5, 9), (5, 10), (6, 2), (6, 3), (6, 9), (6, 10))
KITTEN_CHEEKS = ((7, 1), (7, 11))

LOAF = (
    "...o....o.........",
    "..opo..opo........",
    ".ofpfoofpfo.......",
    "offffffffffoooooo.",
    "offffdfffffffffffo",
    "offfffffffffdfdffo",
    "ofooffffooffdfdffo",
    "offffwnwfffffffffo",
    "owwwwffffffffffffo",
    "oddddddfffffffffo.",
    ".ooooooooooooooo..",
)

COAT_PALETTES: Dict[str, Dict[str, RGB]] = {
    "orange": {"f": (238, 150, 62), "d": (196, 102, 34), "w": (255, 240, 222), "o": (66, 38, 24), "e": (44, 32, 30)},
    "black": {"f": (48, 46, 58), "d": (32, 30, 40), "w": (232, 232, 238), "o": (14, 14, 20), "e": (236, 204, 70)},
    "white": {"f": (246, 244, 238), "d": (222, 220, 212), "w": (255, 255, 255), "o": (92, 92, 104), "e": (70, 140, 210)},
    "gray": {"f": (152, 158, 170), "d": (112, 118, 132), "w": (228, 228, 234), "o": (48, 50, 60), "e": (120, 190, 90)},
    "calico": {"f": (250, 244, 232), "d": (226, 136, 56), "w": (255, 255, 255), "o": (70, 50, 40), "e": (60, 44, 36)},
    "siamese": {"f": (240, 226, 200), "d": (96, 66, 50), "w": (250, 242, 228), "o": (58, 40, 30), "e": (64, 120, 214)},
}
SHARED = {"p": (242, 152, 164), "n": (226, 104, 128), "h": (255, 255, 255), "t": (120, 190, 255),
          "r": (214, 52, 64), "y": (255, 214, 64), "c": (255, 150, 170)}


def _palette(coat: str) -> Dict[str, RGB]:
    pal = dict(SHARED)
    pal.update(COAT_PALETTES.get(coat, COAT_PALETTES["orange"]))
    return pal


def _face(grid: Tuple[str, ...], eyes, cheeks, mood: str, kitten: bool) -> list:
    """Apply a facial expression to a sprite grid."""
    rows = [list(r) for r in grid]
    top = eyes[:4]
    bottom = eyes[4:]
    if mood in ("happy", "party", "content", "rainy"):
        # ^ ^ eyes: top row dark, bottom row fur
        if mood in ("happy", "party"):
            for r, c in top:
                rows[r][c] = "o"
            for r, c in bottom:
                rows[r][c] = "f"
            for r, c in cheeks:
                rows[r][c] = "c"
    elif mood in ("asleep", "keyboard"):
        for r, c in top:
            rows[r][c] = "f"
        for r, c in bottom:
            rows[r][c] = "o"
    elif mood in ("sulking", "bored"):
        for r, c in top:
            rows[r][c] = "d"  # heavy lids
        for r, c in bottom:
            rows[r][c] = "e"
    elif mood in ("hungry", "starving"):
        r, c = SIT_MOUTH if not kitten else (8, 6)
        rows[r][c] = "p"  # tongue out
        if mood == "starving":
            r, c = bottom[0]
            rows[r + 1][c] = "t"  # a tear
    return rows


# --------------------------------------------------------------------------- #
# Tiny drawing helpers on the 80x80 canvas
# --------------------------------------------------------------------------- #


def _blend(a: RGB, b: RGB, t: float) -> RGB:
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _put(img: Image.Image, x: int, y: int, color: RGB, alpha: float = 1.0):
    if 0 <= x < img.width and 0 <= y < img.height:
        if alpha >= 1:
            img.putpixel((x, y), color)
        else:
            img.putpixel((x, y), _blend(img.getpixel((x, y)), color, alpha))


def _rect(img, x0, y0, x1, y1, color, alpha=1.0):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            _put(img, x, y, color, alpha)


def _sprite(img, rows, x0, y0, pal, scale=1, flip=False):
    for r, row in enumerate(rows):
        row = row[::-1] if flip else row
        for c, ch in enumerate(row):
            if ch == ".":
                continue
            color = pal.get(ch)
            if color is None:
                continue
            for dy in range(scale):
                for dx in range(scale):
                    _put(img, x0 + c * scale + dx, y0 + r * scale + dy, color)


DIGITS = {  # 3x5 pixel digits for the streak billboard
    "0": ("111", "101", "101", "101", "111"), "1": ("010", "110", "010", "010", "111"),
    "2": ("111", "001", "111", "100", "111"), "3": ("111", "001", "111", "001", "111"),
    "4": ("101", "101", "111", "001", "001"), "5": ("111", "100", "111", "001", "111"),
    "6": ("111", "100", "111", "101", "111"), "7": ("111", "001", "010", "010", "010"),
    "8": ("111", "101", "111", "101", "111"), "9": ("111", "101", "111", "001", "111"),
}


def _digits(img, text, x, y, color):
    for ch in text:
        glyph = DIGITS.get(ch)
        if glyph:
            for r, row in enumerate(glyph):
                for c, bit in enumerate(row):
                    if bit == "1":
                        _put(img, x + c, y + r, color)
        x += 4
    return x


# --------------------------------------------------------------------------- #
# Sky
# --------------------------------------------------------------------------- #

SKIES = {  # top -> horizon
    "night": [(10, 12, 34), (16, 20, 52), (26, 30, 70), (40, 40, 88), (58, 50, 98)],
    "dawn": [(44, 52, 110), (110, 90, 150), (220, 130, 130), (250, 170, 120), (255, 206, 140)],
    "day": [(70, 140, 222), (96, 162, 232), (124, 184, 240), (156, 204, 244), (190, 224, 248)],
    "dusk": [(36, 32, 84), (98, 58, 120), (196, 88, 110), (240, 130, 90), (255, 176, 96)],
}
GREY_SKIES = {
    "night": [(16, 18, 26), (22, 24, 34), (30, 32, 42), (38, 40, 50), (46, 48, 58)],
    "dawn": [(70, 72, 90), (96, 96, 112), (128, 122, 130), (150, 140, 140), (170, 160, 150)],
    "day": [(110, 120, 136), (126, 136, 150), (142, 150, 162), (158, 166, 176), (176, 182, 190)],
    "dusk": [(58, 52, 70), (88, 72, 88), (120, 92, 100), (146, 112, 108), (170, 134, 116)],
}


def _sky(img, s: SceneState, rng: random.Random):
    bands = GREY_SKIES[s.phase] if s.weather in ("rain", "storm", "fog") else SKIES[s.phase]
    if s.weather in ("cloudy", "drizzle"):
        bands = [_blend(a, b, 0.45) for a, b in zip(SKIES[s.phase], GREY_SKIES[s.phase])]
    band_h = 66 // len(bands) + 1
    for y in range(BASE):
        i = min(y // band_h, len(bands) - 1)
        # dither the band edges for a retro gradient
        if i + 1 < len(bands) and y % band_h >= band_h - 2 and (y % 2):
            color = bands[i + 1]
        else:
            color = bands[i]
        for x in range(BASE):
            if i + 1 < len(bands) and y % band_h == band_h - 1 and (x + y) % 2:
                img.putpixel((x, y), bands[i + 1])
            else:
                img.putpixel((x, y), color)

    clear_night = s.phase == "night" and s.weather in ("clear", "cloudy")
    if clear_night or (s.phase in ("dawn", "dusk") and s.weather == "clear"):
        n = 34 if s.phase == "night" else 8
        for _ in range(n):
            x, y = rng.randrange(BASE), rng.randrange(40)
            twinkle = rng.random()
            _put(img, x, y, (255, 255, 230) if twinkle > 0.7 else (170, 170, 200))
            if twinkle > 0.93:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    _put(img, x + dx, y + dy, (150, 150, 190))

    if s.phase == "night" and s.weather not in ("rain", "storm", "fog"):
        _moon(img, 60, 11, 5, s.moon)
    elif s.phase == "day" and s.weather in ("clear", "cloudy"):
        _sun(img, 62, 12, 5)
    elif s.phase in ("dawn", "dusk") and s.weather in ("clear", "cloudy"):
        _sun(img, 16 if s.phase == "dawn" else 62, 44, 6, (255, 196, 110))


def _moon(img, cx, cy, r, phase):
    light, dark = (246, 240, 210), (60, 60, 92)
    # glow
    for y in range(cy - r - 3, cy + r + 4):
        for x in range(cx - r - 3, cx + r + 4):
            d = math.hypot(x - cx, y - cy)
            if r < d <= r + 3:
                _put(img, x, y, (120, 120, 170), 0.18)
    # lit part: phase 0..0.5 waxing (lit from the right), 0.5..1 waning (lit from the left)
    k = math.cos(phase * 2 * math.pi)  # 1 new .. -1 full
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            dx, dy = x - cx, y - cy
            if dx * dx + dy * dy > r * r + 1:
                continue
            half = math.sqrt(max(r * r - dy * dy, 0)) or 1
            pos = dx / half  # -1 left .. 1 right
            lit = pos > k if phase < 0.5 else pos < -k
            _put(img, x, y, light if lit else dark)
    if 0.35 < phase < 0.65:  # craters on a near-full moon
        for dx, dy in ((-2, -1), (1, 2), (2, -2)):
            _put(img, cx + dx, cy + dy, (214, 206, 176))


def _sun(img, cx, cy, r, color=(255, 230, 120)):
    for y in range(cy - r - 2, cy + r + 3):
        for x in range(cx - r - 2, cx + r + 3):
            d = math.hypot(x - cx, y - cy)
            if d <= r:
                _put(img, x, y, color)
            elif d <= r + 2:
                _put(img, x, y, color, 0.3)


def _cloud(img, x, y, w, color, alpha=1.0):
    shape = [(0, 2, w), (2, 1, w - 3), (4, 0, w - 8)]
    for dx, dy, length in shape:
        for i in range(max(length, 2)):
            _put(img, x + dx + i, y + dy, color, alpha)
    for i in range(w):
        _put(img, x + i, y + 3, _blend(color, (0, 0, 0), 0.15), alpha)


def _weather_top(img, s: SceneState, rng: random.Random):
    if s.weather in ("cloudy", "drizzle", "rain", "storm"):
        color = {"day": (236, 240, 246), "dawn": (240, 200, 190), "dusk": (200, 150, 160)}.get(s.phase, (70, 74, 96))
        if s.weather in ("rain", "storm"):
            color = _blend(color, (60, 62, 74), 0.55)
        count = 3 if s.weather == "cloudy" else 5
        for _ in range(count):
            _cloud(img, rng.randrange(-6, 70), rng.randrange(2, 26), rng.randrange(12, 22), color, 0.92)


def _weather_front(img, s: SceneState, rng: random.Random):
    if s.weather in ("drizzle", "rain", "storm"):
        drops = {"drizzle": 40, "rain": 90, "storm": 130}[s.weather]
        color = (170, 196, 236) if s.phase != "day" else (210, 226, 250)
        for _ in range(drops):
            x, y = rng.randrange(-4, BASE), rng.randrange(BASE)
            length = 2 if s.weather == "drizzle" else 3
            for i in range(length):
                _put(img, x + i // 2, y + i, color, 0.55)
        for x in range(0, BASE, 3):  # splashes on the road
            if rng.random() < 0.4:
                _put(img, x, 75 + rng.randrange(3), (190, 210, 240), 0.6)
    if s.weather == "storm":
        x, y = rng.randrange(8, 24), 4
        bolt = (255, 250, 200)
        for step in range(14):
            _put(img, x, y, bolt)
            _put(img, x + 1, y, bolt, 0.5)
            y += 1
            x += 1 if step % 4 < 2 else -1
    if s.weather == "fog":
        for y in range(30, BASE, 2):
            for x in range(BASE):
                _put(img, x, y, (190, 194, 204), 0.22 + 0.15 * ((x // 7 + y) % 2))


# --------------------------------------------------------------------------- #
# City
# --------------------------------------------------------------------------- #

TOWER = (31, 50)  # x range of your tower (centre of the circle)
TOWER_TOP = 34
TOWER_WINDOWS = 24  # 4 columns x 6 rows
WIN_LIT_SOLVE = (255, 226, 112)
WIN_LIT = [(232, 176, 82), (214, 150, 70), (130, 170, 236)]  # lamps + a TV glow


def _buildings(seed: int):
    """Skyline layout from the seed: [(x0, x1, top, color_index)] excluding your tower."""
    rng = random.Random(seed * 7919 + 3)
    out, x = [], -2
    while x < BASE:
        w = rng.randrange(7, 13)
        x1 = x + w
        if x1 > TOWER[0] - 1 and x < TOWER[1] + 1:  # leave room for the tower
            if x < TOWER[0]:
                out.append((x, TOWER[0] - 2, rng.randrange(40, 58), rng.randrange(3)))
            x = TOWER[1] + 2
            continue
        out.append((x, x1, rng.randrange(38, 60), rng.randrange(3)))
        x = x1 + rng.randrange(0, 3)
    return out


BUILDING_COLORS = {
    "night": [(34, 36, 62), (42, 40, 70), (30, 44, 66)],
    "dawn": [(74, 66, 104), (92, 76, 112), (70, 78, 108)],
    "day": [(104, 116, 150), (128, 120, 146), (96, 128, 150)],
    "dusk": [(66, 50, 86), (84, 58, 92), (60, 62, 92)],
}


def _city(img, s: SceneState, rng: random.Random):
    phase = s.phase
    dim = s.phase == "night" and not s.awake
    far = _blend(SKIES[phase][-1], (0, 0, 0), 0.45)
    frng = random.Random(s.seed)
    x = 0
    while x < BASE:  # far silhouette
        w, h = frng.randrange(4, 9), frng.randrange(46, 60)
        _rect(img, x, h, x + w, 72, far)
        x += w

    night = phase in ("night", "dusk")
    ambient = (0.30 if s.awake else 0.05) if night else (0.06 if s.awake else 0.02)
    for x0, x1, top, ci in _buildings(s.seed):
        body = BUILDING_COLORS[phase][ci]
        if dim:
            body = _blend(body, (0, 0, 0), 0.25)
        _rect(img, x0, top, x1, 72, body)
        _rect(img, x0, top, x1, top, _blend(body, (255, 255, 255), 0.15))  # roof edge
        for wy in range(top + 3, 70, 4):
            for wx in range(x0 + 2, x1 - 1, 3):
                lit = rng.random() < ambient
                color = rng.choice(WIN_LIT) if lit else (_blend(body, (150, 200, 240), 0.35) if phase == "day" else _blend(body, (0, 0, 0), 0.35))
                _rect(img, wx, wy, wx + 1, wy + 1, color)

    _tower(img, s)
    _street(img, s, rng)


def _tower(img, s: SceneState):
    x0, x1 = TOWER
    body = {"night": (52, 48, 86), "dawn": (100, 84, 124), "day": (140, 132, 168), "dusk": (88, 64, 104)}[s.phase]
    edge = _blend(body, (255, 255, 255), 0.18)
    _rect(img, x0, TOWER_TOP, x1, 72, body)
    _rect(img, x0, TOWER_TOP, x1, TOWER_TOP, edge)
    _rect(img, x0, TOWER_TOP, x0, 72, edge)
    # antenna + beacon: red, green from a 3-day streak, gold from 7
    ax = (x0 + x1) // 2
    _rect(img, ax, TOWER_TOP - 6, ax, TOWER_TOP - 1, (150, 150, 170))
    beacon = (255, 70, 70)
    if s.streak >= 7:
        beacon = (255, 214, 64)
    elif s.streak >= 3:
        beacon = (90, 230, 120)
    _put(img, ax, TOWER_TOP - 7, beacon)
    for dx, dy in ((1, 0), (-1, 0), (0, -1)):
        _put(img, ax + dx, TOWER_TOP - 7 + dy, beacon, 0.45)

    # your windows: one lights up per problem solved today, in a fixed scattered order
    slots = [(x0 + 3 + c * 4, TOWER_TOP + 5 + r * 5) for r in range(6) for c in range(4)]
    order = random.Random(s.seed + 99).sample(range(len(slots)), len(slots))
    lit = set(order[: min(s.solved, len(slots))])
    for i, (wx, wy) in enumerate(slots):
        if i in lit:
            _rect(img, wx, wy, wx + 2, wy + 2, WIN_LIT_SOLVE)
            if s.phase in ("night", "dusk"):
                for gx in range(wx - 1, wx + 4):
                    for gy in range(wy - 1, wy + 4):
                        if not (wx <= gx <= wx + 2 and wy <= gy <= wy + 2):
                            _put(img, gx, gy, WIN_LIT_SOLVE, 0.22)
        else:
            glass = (150, 196, 236) if s.phase == "day" else _blend(body, (0, 0, 0), 0.4)
            _rect(img, wx, wy, wx + 2, wy + 2, glass)

    # streak billboard on the tower's flank
    if s.streak > 0:
        text = str(min(s.streak, 999))
        w = len(text) * 4 + 6
        bx, by = x1 - w + 1, 66
        _rect(img, bx - 1, by - 1, bx + w, by + 5, (24, 22, 36))
        _flame(img, bx, by)
        _digits(img, text, bx + 5, by, (255, 214, 120))


def _flame(img, x, y):
    for px, py, col in ((1, 0, (255, 200, 80)), (0, 1, (255, 140, 50)), (1, 1, (255, 200, 80)), (2, 1, (255, 140, 50)),
                        (0, 2, (255, 120, 40)), (1, 2, (255, 230, 120)), (2, 2, (255, 120, 40)), (0, 3, (230, 80, 30)),
                        (1, 3, (255, 160, 60)), (2, 3, (230, 80, 30)), (1, 4, (200, 60, 30))):
        _put(img, x + px, y + py, col)


def _street(img, s: SceneState, rng: random.Random):
    wet = s.weather in ("drizzle", "rain", "storm")
    road = (34, 34, 44) if s.phase != "day" else (74, 76, 86)
    _rect(img, 0, 73, BASE - 1, BASE - 1, road)
    _rect(img, 0, 73, BASE - 1, 73, _blend(road, (255, 255, 255), 0.25))  # kerb
    for x in range(2, BASE, 8):
        _rect(img, x, 77, x + 3, 77, (210, 200, 120) if s.phase != "night" else (150, 140, 90))
    lamps_on = s.awake and s.phase in ("night", "dusk", "dawn")
    for lx in (8, 70):
        _rect(img, lx, 64, lx, 72, (90, 90, 110))
        _rect(img, lx, 64, lx + 2, 64, (90, 90, 110))
        if lamps_on:
            _put(img, lx + 2, 65, (255, 236, 160))
            _put(img, lx + 1, 65, (255, 236, 160), 0.6)
            for gy in range(66, 74):
                spread = (gy - 66) // 3
                for gx in range(lx + 1 - spread, lx + 4 + spread):
                    _put(img, gx, gy, (255, 214, 120), 0.10)
            for gx in range(lx - 3, lx + 8):  # pool of light on the pavement
                _put(img, gx, 73, (255, 214, 120), 0.45 if not wet else 0.6)
        else:
            _put(img, lx + 2, 65, (70, 70, 84))
    if s.awake:  # a car driving by
        cx = 16 + (s.seed * 13) % 40
        _rect(img, cx, 74, cx + 7, 75, (200, 60, 70))
        _rect(img, cx + 2, 73, cx + 5, 73, (220, 90, 96))
        _put(img, cx + 1, 76, (20, 20, 20))
        _put(img, cx + 6, 76, (20, 20, 20))
        if s.phase != "day":
            _put(img, cx + 7, 74, (255, 250, 200))
            for i in range(1, 5):
                _put(img, cx + 7 + i, 74, (255, 240, 180), 0.35 - i * 0.06)
    if wet:  # reflections of lit windows in the puddles
        for x in range(TOWER[0] + 3, TOWER[1] - 2, 4):
            if s.solved:
                _put(img, x, 79, WIN_LIT_SOLVE, 0.35)


# --------------------------------------------------------------------------- #
# Kitty in the scene
# --------------------------------------------------------------------------- #


def _accessories(img, mood, stage, x, y, w, scale):
    """Things drawn around the cat sprite at (x, y), sprite width w (in logical px)."""
    cx = x + (w * scale) // 2 - (2 if w == 16 else 1) * scale

    def px(dx, dy, color, a=1.0):
        for sy in range(scale):
            for sx in range(scale):
                _put(img, cx + dx * scale + sx, y + dy * scale + sy, color, a)

    if stage == "legend":
        for dx, dy in ((-2, -2), (0, -3), (2, -2), (-2, -1), (-1, -1), (0, -1), (1, -1), (2, -1), (0, -2)):
            px(dx, dy, (255, 210, 60))
        px(0, -2, (230, 60, 90))
    if mood == "party" and stage != "legend":
        for dy, span in ((-4, 0), (-3, 1), (-2, 1), (-1, 2)):
            for dx in range(-span, span + 1):
                px(dx, dy, (90, 200, 255) if (dx + dy) % 2 else (255, 100, 160))
        px(0, -5, (255, 230, 90))
    if mood in ("asleep", "keyboard"):
        zx = (w * scale) // 2 + 3
        for i, (dx, dy) in enumerate(((zx, -3), (zx + 4, -8))):
            size = 3 + i
            for k in range(size):
                for sy in range(scale):
                    for sx in range(scale):
                        _put(img, cx + (dx + k) * scale + sx, y + dy * scale + sy, (230, 236, 255))
                        _put(img, cx + (dx + k) * scale + sx, y + (dy + size - 1) * scale + sy, (230, 236, 255))
                        _put(img, cx + (dx + size - 1 - k) * scale + sx, y + (dy + k) * scale + sy, (230, 236, 255))
    if mood == "sulking":
        for dx in range(-3, 4):
            px(dx, -4, (120, 124, 140))
        for dx in range(-2, 3):
            px(dx, -5, (140, 144, 160))
        px(-1, -2, (120, 190, 255))
        px(1, -1, (120, 190, 255))
    if mood == "happy":
        hx = (w * scale) // 2 + 2
        for dx, dy in ((0, 0), (2, 0), (-1, 1), (0, 1), (1, 1), (2, 1), (3, 1), (0, 2), (1, 2), (2, 2), (1, 3)):
            for sy in range(scale):
                for sx in range(scale):
                    _put(img, cx + (hx + dx) * scale + sx, y + (dy - 4) * scale + sy, (255, 90, 130))
    if mood in ("hungry", "starving"):
        bx = (w * scale) // 2 + 2
        fish = ((0, 1), (1, 0), (1, 1), (1, 2), (2, 0), (2, 1), (2, 2), (3, 1), (4, 0), (4, 2))
        for dx, dy in fish:
            for sy in range(scale):
                for sx in range(scale):
                    _put(img, cx + (bx + dx) * scale + sx, y + (dy - 5) * scale + sy, (150, 200, 236))


def _keyboard(img, x, y, w):
    _rect(img, x, y, x + w, y + 3, (40, 42, 52))
    for kx in range(x + 1, x + w, 2):
        _put(img, kx, y + 1, (140, 146, 170))
        _put(img, kx + 1, y + 2, (140, 146, 170))


def _cat(img, mood, stage, coat, x, y, scale=1):
    """Draw the cat with its feet at y. Returns the sprite's top-left."""
    pal = _palette(coat)
    sleeping = mood in ("asleep", "keyboard")
    if sleeping and stage != "kitten":
        rows = [list(r) for r in LOAF]
        w, h = 18, len(LOAF)
    elif stage == "kitten":
        rows = _face(KITTEN, KITTEN_EYES, KITTEN_CHEEKS, mood, True)
        w, h = 12, len(KITTEN)
    else:
        rows = _face(SIT, SIT_EYES, SIT_CHEEKS, mood, False)
        w, h = 16, len(SIT)
        if stage in ("adult", "legend"):  # collar and bell
            for c in range(3, 10):
                if rows[9][c] != ".":
                    rows[9][c] = "r"
            rows[10][6] = "y"
    x0, y0 = x - (w * scale) // 2, y - h * scale
    if mood == "keyboard":
        _keyboard(img, x0 - scale, y - 2 * scale, w * scale + scale)
        y0 -= 2 * scale
    _sprite(img, ["".join(r) for r in rows], x0, y0, pal, scale)
    _accessories(img, mood, stage, x0, y0, w, scale)
    return x0, y0


# --------------------------------------------------------------------------- #
# Public renderers
# --------------------------------------------------------------------------- #


def _upscale(img: Image.Image, size: int) -> Image.Image:
    return img.resize((size, size), Image.NEAREST)


def render_scene(state: SceneState, scene: str = "both", size: int = PFP_SIZE) -> Image.Image:
    """scene: 'city' (city only), 'both' (Kitty on your rooftop), 'kitty' (Kitty at the window)."""
    rng = random.Random(f"{state.seed}-{state.phase}-{state.weather}-{state.awake}")
    img = Image.new("RGB", (BASE, BASE))
    _sky(img, state, rng)
    _weather_top(img, state, rng)
    _city(img, state, rng)
    cat = state.kitty_mood is not None
    if scene == "both" and cat:
        _cat(img, state.kitty_mood, state.kitty_stage, state.kitty_coat, (TOWER[0] + TOWER[1]) // 2 + 1, TOWER_TOP, 1)
    _weather_front(img, state, rng)
    if scene == "kitty" and cat:
        _window(img, state)
    return _upscale(img, size)


def _window(img, state: SceneState):
    """Kitty sitting on your windowsill, the city behind the glass."""
    frame, sill = (92, 64, 48), (128, 90, 64)
    for y in range(BASE):  # darken the outside slightly so Kitty pops
        for x in range(BASE):
            img.putpixel((x, y), _blend(img.getpixel((x, y)), (0, 0, 0), 0.25))
    _rect(img, 0, 0, BASE - 1, 3, frame)
    _rect(img, 0, 0, 3, BASE - 1, frame)
    _rect(img, BASE - 4, 0, BASE - 1, BASE - 1, frame)
    _rect(img, 38, 0, 41, 64, frame)
    _rect(img, 0, 63, BASE - 1, 65, frame)
    _rect(img, 0, 66, BASE - 1, BASE - 1, sill)
    _rect(img, 0, 66, BASE - 1, 66, _blend(sill, (255, 255, 255), 0.25))
    for x in range(0, BASE, 6):
        _rect(img, x, 70 + (x // 6) % 2 * 5, x + 3, 70 + (x // 6) % 2 * 5, _blend(sill, (0, 0, 0), 0.2))
    _cat(img, state.kitty_mood, state.kitty_stage, state.kitty_coat, 40, 76, 3)


@lru_cache(maxsize=8)
def _font(size: int):
    try:
        return ImageFont.truetype(PIXEL_FONT, size)
    except Exception:
        return ImageFont.load_default()


def _ascii(text: str) -> str:
    return "".join(ch for ch in str(text) if 32 <= ord(ch) < 127).strip()


def _wrap(text: str, width: int) -> Iterable[str]:
    line = ""
    for word in text.split():
        if len(line) + len(word) + 1 > width:
            yield line
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        yield line


def render_card(kitty, state: SceneState, mood_text: str, extra: Iterable[Tuple[str, str]] = ()) -> Image.Image:
    """The .kitty status card: Kitty at the window on the left, stats on the right."""
    W, H = 960, 540
    bg, panel, ink, muted = (20, 20, 34), (30, 30, 50), (240, 236, 255), (150, 146, 190)
    card = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(card)
    pic = render_scene(state, "kitty", 460)
    card.paste(pic, (40, 40))
    d.rectangle((36, 36, 503, 503), outline=(70, 66, 110), width=4)

    x, y = 540, 48
    d.text((x, y), _ascii(kitty.name)[:14] or "Kitty", font=_font(32), fill=ink)
    y += 50
    from .kittypet import xp_for_level

    lo, hi = xp_for_level(kitty.level), xp_for_level(kitty.level + 1)
    d.text((x, y), f"LV {kitty.level}  {kitty.stage.upper()}", font=_font(16), fill=(255, 210, 90))
    d.text((x + 380, y), f"{int(kitty.xp - lo)}/{hi - lo} XP", font=_font(16), fill=muted, anchor="ra")
    y += 28
    frac = (kitty.xp - lo) / max(hi - lo, 1)
    _pixel_bar(d, x, y, 380, 12, frac, (255, 210, 90), panel)
    y += 34
    for label, value, color in (("FOOD", kitty.food, (255, 150, 90)), ("JOY", kitty.joy, (255, 100, 150)),
                                ("ENERGY", kitty.energy, (110, 200, 255))):
        d.text((x, y), label, font=_font(16), fill=muted)
        d.text((x + 380, y), f"{int(value):>3}", font=_font(16), fill=ink, anchor="ra")
        y += 24
        _pixel_bar(d, x, y, 380, 16, value / 100, color, panel)
        y += 34
    y += 4
    for label, value in extra:
        d.text((x, y), _ascii(label), font=_font(16), fill=muted)
        d.text((x + 380, y), _ascii(value), font=_font(16), fill=ink, anchor="ra")
        y += 28
    y = max(y + 10, 420)
    for line in list(_wrap(_ascii(mood_text), 22))[:3]:
        d.text((x, y), line, font=_font(16), fill=(220, 214, 255))
        y += 26
    return card


def _pixel_bar(d: ImageDraw.ImageDraw, x, y, w, h, frac, color, track):
    frac = max(0.0, min(1.0, frac))
    d.rectangle((x, y, x + w, y + h), fill=track)
    seg = 12
    n = int(round(frac * (w // seg)))
    for i in range(n):
        d.rectangle((x + i * seg + 2, y + 2, x + i * seg + seg - 2, y + h - 2), fill=color)
