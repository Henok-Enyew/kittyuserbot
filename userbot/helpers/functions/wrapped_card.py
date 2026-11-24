# "Chat Wrapped" — stats collection + card rendering (pure; no Telegram calls).

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import timedelta

from PIL import Image, ImageDraw

from .kittycard import FONT_BOLD, FONT_LIGHT, fit, font, gradient, printable, text_width

URL_RE = re.compile(r"https?://\S+|www\.\S+|t\.me/\S+", re.I)
WORD_RE = re.compile(r"[^\W\d_]{3,}", re.U)
EMOJI_RE = re.compile(
    "[\U0001F300-\U0001F5FF\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\U0001F900-\U0001F9FF"
    "\U0001FA70-\U0001FAFF☀-⛿✀-➿❤\U0001F1E6-\U0001F1FF]"
)
STOPWORDS = set(
    """
the and for are but not you all any can had her was one our out has him his how its may new now old see two
who boy did get got let put say she too use that with have this will your from they know want been good much
some time very when come here just like long make many more only over such take than them then well were what
there their would about which could other into also back after first even because these those where while being
does doing done dont didnt im ive its thats yeah yes okay ok lol haha hahaha hmm umm ill youre theyre cant wont
isnt arent wasnt sure really still think going gonna wanna gotta need why who whom whats should shouldnt
""".split()
)
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


@dataclass
class ChatStats:
    title: str = ""
    total: int = 0
    words_total: int = 0
    chars_total: int = 0
    links: int = 0
    first: object = None
    last: object = None
    senders: Counter = field(default_factory=Counter)
    names: dict = field(default_factory=dict)
    hours: list = field(default_factory=lambda: [0] * 24)
    weekdays: list = field(default_factory=lambda: [0] * 7)
    days: Counter = field(default_factory=Counter)
    words: Counter = field(default_factory=Counter)
    emojis: Counter = field(default_factory=Counter)
    media: Counter = field(default_factory=Counter)
    reply_times: dict = field(default_factory=lambda: defaultdict(list))
    longest: tuple = (0, None)
    _prev: tuple = (None, None)  # (sender_id, local datetime) of previous message (chronological)

    def add(self, sender_id, sender_name, local_dt, text, kind):
        """Feed messages in chronological order."""
        self.total += 1
        self.senders[sender_id] += 1
        self.names.setdefault(sender_id, sender_name)
        self.hours[local_dt.hour] += 1
        self.weekdays[local_dt.weekday()] += 1
        self.days[local_dt.date()] += 1
        self.first = self.first or local_dt
        self.last = local_dt
        if kind and kind != "link":
            self.media[kind] += 1
        if text:
            self.links += len(URL_RE.findall(text))
            clean = URL_RE.sub(" ", text)
            self.chars_total += len(clean)
            toks = WORD_RE.findall(clean.lower())
            self.words_total += len(clean.split())
            self.words.update(t for t in toks if t not in STOPWORDS)
            self.emojis.update(EMOJI_RE.findall(text))
            if len(clean) > self.longest[0]:
                self.longest = (len(clean), sender_id)
        prev_id, prev_dt = self._prev
        if prev_id is not None and prev_id != sender_id:
            gap = (local_dt - prev_dt).total_seconds()
            if 0 <= gap <= 6 * 3600:
                self.reply_times[sender_id].append(gap)
        self._prev = (sender_id, local_dt)

    # derived ---------------------------------------------------------
    def streak(self) -> int:
        best = cur = 0
        prev = None
        for d in sorted(self.days):
            cur = cur + 1 if prev and d - prev == timedelta(days=1) else 1
            best = max(best, cur)
            prev = d
        return best

    def busiest_hour(self) -> int:
        return max(range(24), key=lambda h: self.hours[h])

    def busiest_day(self):
        return self.days.most_common(1)[0] if self.days else (None, 0)

    def night_share(self) -> float:
        return sum(self.hours[0:5]) / self.total if self.total else 0

    def median_reply(self):
        """{sender_id: median seconds} for people with >= 5 replies."""
        out = {}
        for sid, gaps in self.reply_times.items():
            if len(gaps) >= 5:
                g = sorted(gaps)
                out[sid] = g[len(g) // 2]
        return out


def fmt_secs(s: float) -> str:
    s = int(s)
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m"
    return f"{s // 3600}h {s % 3600 // 60}m"


def compact(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 10_000:
        return f"{n / 1000:.0f}K"
    if n >= 1000:
        return f"{n / 1000:.1f}K"
    return str(n)


# ─────────────────────────────── render ───────────────────────────────

W = 1080
PAD = 60
ACCENTS = [(255, 107, 129), (255, 184, 76), (94, 234, 212), (129, 140, 248), (244, 114, 182), (163, 230, 53)]
WHITE = (255, 255, 255)
DIM = (190, 196, 230)


class _Canvas:
    def __init__(self, h):
        self.img = gradient((W, h), (20, 18, 48), (88, 28, 135)).convert("RGBA")
        self.draw = ImageDraw.Draw(self.img)

    def panel(self, box, alpha=34, radius=28):
        layer = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        ImageDraw.Draw(layer).rounded_rectangle(box, radius=radius, fill=(255, 255, 255, alpha))
        self.img = Image.alpha_composite(self.img, layer)
        self.draw = ImageDraw.Draw(self.img)

    def text(self, xy, txt, size, bold=True, fill=WHITE, anchor="la", max_w=None):
        path = FONT_BOLD if bold else FONT_LIGHT
        fnt = font(path, size)
        txt = printable(txt, path)
        if max_w:
            txt = fit(self.draw, txt, fnt, max_w)
        self.draw.text(xy, txt, font=fnt, fill=fill, anchor=anchor)
        return txt


def _label(sid, stats) -> str:
    name = printable(stats.names.get(sid, ""), FONT_BOLD).strip()
    return name or f"User {str(sid)[-4:]}"


def render(stats: ChatStats, out_path: str, subtitle: str = "") -> str:
    H = 2600  # generous canvas, cropped to content at the end
    c = _Canvas(H)
    y = PAD

    c.text((PAD, y), "CHAT WRAPPED", 34, fill=(255, 184, 76))
    y += 52
    title = printable(stats.title, FONT_BOLD) or "This chat"
    c.text((PAD, y), title, 72, max_w=W - 2 * PAD)
    y += 92
    span = f"{stats.first:%d %b %Y} – {stats.last:%d %b %Y}" if stats.first else ""
    c.text((PAD, y), f"{span}   {subtitle}".strip(), 30, bold=False, fill=DIM, max_w=W - 2 * PAD)
    y += 70

    # tiles ------------------------------------------------------------
    bh, bd = stats.busiest_hour(), stats.busiest_day()
    tiles = [
        (compact(stats.total), "messages"),
        (compact(stats.words_total), "words"),
        (str(len(stats.days)), "active days"),
        (f"{stats.streak()}d", "longest streak"),
        (f"{bh:02d}:00", "peak hour"),
        (f"{bd[0]:%d %b}" if bd[0] else "-", f"busiest day · {bd[1]}"),
    ]
    tw, th, gap = (W - 2 * PAD - 2 * 24) // 3, 170, 24
    for i, (big, small) in enumerate(tiles):
        col, row = i % 3, i // 3
        x0, y0 = PAD + col * (tw + gap), y + row * (th + gap)
        c.panel((x0, y0, x0 + tw, y0 + th))
        c.text((x0 + 28, y0 + 30), big, 62, fill=ACCENTS[i % len(ACCENTS)], max_w=tw - 40)
        c.text((x0 + 28, y0 + 112), small, 28, bold=False, fill=DIM, max_w=tw - 40)
    y += 2 * th + gap + 50

    # top talkers ------------------------------------------------------
    top = stats.senders.most_common(5)
    box_h = 90 + 78 * max(1, len(top))
    c.panel((PAD, y, W - PAD, y + box_h))
    c.text((PAD + 32, y + 28), "Top talkers", 38)
    yy = y + 92
    peak = top[0][1] if top else 1
    for i, (sid, n) in enumerate(top):
        pct = n * 100 / stats.total
        bar_w = int((W - 2 * PAD - 64) * n / peak)
        c.draw.rounded_rectangle((PAD + 32, yy + 40, PAD + 32 + max(bar_w, 14), yy + 58), radius=9, fill=ACCENTS[i])
        c.text((PAD + 32, yy), _label(sid, stats), 32, max_w=W - 2 * PAD - 300)
        c.text((W - PAD - 32, yy), f"{compact(n)} · {pct:.0f}%", 30, bold=False, fill=DIM, anchor="ra")
        yy += 78
    y += box_h + 36

    # hourly activity --------------------------------------------------
    c.panel((PAD, y, W - PAD, y + 300))
    c.text((PAD + 32, y + 28), "When you talk", 38)
    chart_top, chart_bot = y + 100, y + 250
    peak_h = max(stats.hours) or 1
    slot = (W - 2 * PAD - 64) / 24
    for h in range(24):
        v = stats.hours[h]
        x0 = PAD + 32 + h * slot
        bh_px = int((chart_bot - chart_top) * v / peak_h)
        color = ACCENTS[1] if h == bh else (129, 140, 248)
        c.draw.rounded_rectangle((x0 + 3, chart_bot - max(bh_px, 4), x0 + slot - 3, chart_bot), radius=5, fill=color)
        if h % 6 == 0:
            c.text((x0 + slot / 2, chart_bot + 10), f"{h:02d}", 22, bold=False, fill=DIM, anchor="ma")
    y += 336

    # weekdays + top words ---------------------------------------------
    half = (W - 2 * PAD - 24) // 2
    c.panel((PAD, y, PAD + half, y + 330))
    c.text((PAD + 32, y + 28), "Week", 38)
    peak_w = max(stats.weekdays) or 1
    busiest_wd = max(range(7), key=lambda d: stats.weekdays[d])
    for d in range(7):
        yy = y + 96 + d * 32
        c.text((PAD + 32, yy), WEEKDAYS[d], 24, bold=False, fill=DIM)
        bw = int((half - 140) * stats.weekdays[d] / peak_w)
        c.draw.rounded_rectangle(
            (PAD + 100, yy + 6, PAD + 100 + max(bw, 8), yy + 24),
            radius=8,
            fill=ACCENTS[0] if d == busiest_wd else (94, 234, 212),
        )

    x1 = PAD + half + 24
    c.panel((x1, y, W - PAD, y + 330))
    c.text((x1 + 32, y + 28), "Top words", 38)
    yy, xx = y + 100, x1 + 32
    for i, (word, n) in enumerate([(w, n) for w, n in stats.words.most_common(60) if printable(w) == w][:9]):
        fnt = font(FONT_BOLD, 28)
        wpx = text_width(c.draw, word, fnt) + 36
        if xx + wpx > W - PAD - 24:
            xx, yy = x1 + 32, yy + 58
            if yy > y + 280:
                break
        c.draw.rounded_rectangle((xx, yy, xx + wpx, yy + 46), radius=23, fill=ACCENTS[i % len(ACCENTS)])
        c.draw.text((xx + 18, yy + 8), word, font=fnt, fill=(20, 18, 48))
        xx += wpx + 12
    y += 366

    # fun facts ----------------------------------------------------------
    facts = []
    night = stats.night_share()
    if night >= 0.08:
        facts.append(f"Night owls: {night * 100:.0f}% of messages sent 00:00-05:00")
    replies = stats.median_reply()
    if len(replies) >= 2:
        fast = min(replies, key=replies.get)
        facts.append(f"Fastest replier: {_label(fast, stats)} (median {fmt_secs(replies[fast])})")
    if stats.media:
        kind, n = stats.media.most_common(1)[0]
        facts.append(f"Favourite media: {kind} x{n}")
    if stats.longest[1] is not None:
        facts.append(f"Longest message: {compact(stats.longest[0])} chars by {_label(stats.longest[1], stats)}")
    if stats.links:
        facts.append(f"Links shared: {stats.links}")
    facts = facts[:4]
    if facts:
        c.panel((PAD, y, W - PAD, y + 70 + 52 * len(facts)))
        yy = y + 30
        for i, f in enumerate(facts):
            c.draw.ellipse((PAD + 34, yy + 12, PAD + 50, yy + 28), fill=ACCENTS[i])
            c.text((PAD + 68, yy), f, 30, bold=False, max_w=W - 2 * PAD - 100)
            yy += 52
        y += 70 + 52 * len(facts) + 30

    c.text((W // 2, min(y + 10, H - 60)), "made with KittyUserbot", 26, bold=False, fill=DIM, anchor="ma")
    final_h = min(H, y + 70)
    c.img.crop((0, 0, W, final_h)).convert("RGB").save(out_path, "JPEG", quality=93)
    return out_path
