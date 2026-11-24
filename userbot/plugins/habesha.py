# Habesha toolkit — Ethiopian calendar, time, holidays and birr rates. No API keys.
#
#   .ethdate [YYYY-MM-DD]        today (or a date) in the Ethiopian calendar + Ethiopian time
#   .ethconv <date>              convert either way: 2026-11-24  |  15 hidar 2019  |  ኅዳር 15 2019
#   .holidays [n]                upcoming Ethiopian public holidays with countdown
#   .birr [amount] [currency]    ETB exchange rates (official rate, updated daily)

import re
import time
from datetime import date, datetime

import aiohttp

from userbot import catub

from ..Config import Config
from ..core.managers import edit_delete, edit_or_reply
from ..helpers.functions.ethiocal import (
    MONTHS_AM,
    MONTHS_EN,
    eth_time,
    format_eth,
    geez,
    holidays_between,
    parse_month,
    to_ethiopian,
    to_gregorian,
)
from ..helpers.functions.kittytime import now_local

plugin_category = "utils"

_DATE_ISO = re.compile(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$")
_DATE_DMY = re.compile(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})$")


def _parse_gregorian(text: str):
    t = text.strip()
    m = _DATE_ISO.match(t)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = _DATE_DMY.match(t)
    if m:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    return None


def _parse_ethiopian(text: str):
    """'15 hidar 2019', 'ኅዳር 15 2019', 'hidar 15, 2019', '2019-03-15 ec' -> (y, m, d) or None."""
    t = text.replace(",", " ").replace("ዓ.ም", " ").strip()
    low = t.lower()
    if low.endswith(" ec") or low.endswith(" e.c.") or low.endswith(" eth"):
        core = t.rsplit(" ", 1)[0].strip()
        m = _DATE_ISO.match(core)
        if m:
            return int(m.group(1)), int(m.group(2)), int(m.group(3))
        m = _DATE_DMY.match(core)
        if m:
            return int(m.group(3)), int(m.group(2)), int(m.group(1))
    month, nums = None, []
    for tok in t.split():
        if tok.isdigit():
            nums.append(int(tok))
        elif month is None:
            month = parse_month(tok)
            if month is None:
                return None
        else:
            return None
    if month is None or not nums:
        return None
    day = next((n for n in nums if n <= 30), None)
    year = next((n for n in nums if n > 30), None) or to_ethiopian(now_local().date())[0]
    if day is None:
        return None
    return year, month, day


def _eth_block(d: date) -> str:
    y, m, day = to_ethiopian(d)
    return (
        f"🇪🇹 <b>{format_eth(d)}</b>\n"
        f"    {format_eth(d, amharic=False)}\n"
        f"    ግዕዝ: {geez(day)} {MONTHS_AM[m - 1]} {geez(y)}"
    )


@catub.cat_cmd(
    pattern=r"ethdate(?:\s+(.+))?$",
    command=("ethdate", plugin_category),
    info={
        "header": "Today in the Ethiopian calendar, with Ethiopian time and Ge'ez numerals.",
        "usage": ["{tr}ethdate", "{tr}ethdate 2027-01-07"],
    },
)
async def ethdate_cmd(event):
    "Ethiopian date & time."
    arg = (event.pattern_match.group(1) or "").strip()
    now = now_local()
    d = now.date()
    if arg:
        try:
            d = _parse_gregorian(arg)
        except ValueError:
            d = None
        if d is None:
            return await edit_delete(event, "`Use YYYY-MM-DD or DD/MM/YYYY.`", 6)
    lines = [f"📅 <b>{d:%A, %d %B %Y}</b>", _eth_block(d)]
    if not arg:
        h, mi, am, en = eth_time(now.hour, now.minute)
        lines.append(f"\n🕰 <b>{h}:{mi:02d} {am}</b> ({h}:{mi:02d} in the {en}) · {now:%H:%M} Addis")
        upcoming = holidays_between(d, d.replace(year=d.year + 1))
        if upcoming:
            hd, _, en_name, am_name, approx = upcoming[0]
            days = (hd - d).days
            when = "today 🎉" if days == 0 else f"in {days} day{'s' if days != 1 else ''}"
            lines.append(f"🎊 Next holiday: <b>{am_name}</b> / {en_name}{' ≈' if approx else ''} — {when}")
    await edit_or_reply(event, "\n".join(lines), parse_mode="html")


@catub.cat_cmd(
    pattern=r"ethconv(?:\s+(.+))?$",
    command=("ethconv", plugin_category),
    info={
        "header": "Convert dates between the Gregorian and Ethiopian calendars.",
        "description": "Gregorian → Ethiopian: 2026-11-24 or 24/11/2026.\n"
        "Ethiopian → Gregorian: '15 hidar 2019', 'ኅዳር 15 2019' or '2019-03-15 ec'. "
        "Month names work in Amharic or English (first 3 letters are enough).",
        "usage": "{tr}ethconv <date>",
        "examples": ["{tr}ethconv 2027-01-07", "{tr}ethconv 1 meskerem 2020", "{tr}ethconv መስከረም 17 2019"],
    },
)
async def ethconv_cmd(event):
    "Calendar converter."
    arg = (event.pattern_match.group(1) or "").strip()
    if not arg:
        return await edit_delete(event, f"`Usage: {Config.COMMAND_HAND_LER}ethconv 2026-11-24 | 15 hidar 2019`", 8)
    try:
        g = _parse_gregorian(arg)
    except ValueError as e:
        return await edit_delete(event, f"`{e}`", 6)
    if g:
        return await edit_or_reply(event, f"📅 {g:%A, %d %B %Y} =\n{_eth_block(g)}", parse_mode="html")
    eth = _parse_ethiopian(arg)
    if not eth:
        return await edit_delete(event, "`Couldn't read that date. Try 2026-11-24 or 15 hidar 2019.`", 8)
    try:
        g = to_gregorian(*eth)
    except ValueError as e:
        return await edit_delete(event, f"`{e}`", 6)
    y, m, d = eth
    await edit_or_reply(
        event,
        f"🇪🇹 {MONTHS_AM[m - 1]} {d} ቀን {y} ዓ.ም ({MONTHS_EN[m - 1]} {d}, {y}) =\n📅 <b>{g:%A, %d %B %Y}</b>",
        parse_mode="html",
    )


@catub.cat_cmd(
    pattern=r"holidays(?:\s+(\d+))?$",
    command=("holidays", plugin_category),
    info={
        "header": "Upcoming Ethiopian public holidays with countdown.",
        "description": "Fasika and Siklet are computed for each year. Muslim holidays (≈) use the arithmetic "
        "Hijri calendar and can shift a day or two with the moon sighting.",
        "usage": "{tr}holidays [count]",
    },
)
async def holidays_cmd(event):
    "Ethiopian holidays."
    count = min(int(event.pattern_match.group(1) or 8), 20)
    today = now_local().date()
    items = holidays_between(today, today.replace(year=today.year + 2))[:count]
    lines = ["🎊 <b>Upcoming holidays</b>\n"]
    for d, _, en, am, approx in items:
        days = (d - today).days
        when = "<b>today 🎉</b>" if days == 0 else ("tomorrow" if days == 1 else f"in {days} days")
        y, m, day = to_ethiopian(d)
        lines.append(
            f"• <b>{am}</b> — {en}{' ≈' if approx else ''}\n"
            f"   {d:%a %d %b %Y} · {MONTHS_AM[m - 1]} {day} · {when}"
        )
    lines.append(f"\n<code>{Config.COMMAND_HAND_LER}countdown genna</code> for a live countdown")
    await edit_or_reply(event, "\n".join(lines), parse_mode="html")


# ─────────────────────────────── .birr ────────────────────────────────

_RATES = {"at": 0, "data": None}
MAJORS = ["USD", "EUR", "GBP", "SAR", "AED", "CNY", "KES", "CAD", "TRY"]
FLAGS = {"USD": "🇺🇸", "EUR": "🇪🇺", "GBP": "🇬🇧", "SAR": "🇸🇦", "AED": "🇦🇪", "CNY": "🇨🇳", "KES": "🇰🇪", "CAD": "🇨🇦", "TRY": "🇹🇷", "ETB": "🇪🇹"}


async def _rates():
    if _RATES["data"] and time.time() - _RATES["at"] < 3600:
        return _RATES["data"]
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as s:
        async with s.get("https://open.er-api.com/v6/latest/USD") as r:
            data = await r.json(content_type=None)
    if data.get("result") != "success" or "ETB" not in data.get("rates", {}):
        raise RuntimeError(data.get("error-type", "rates unavailable"))
    _RATES.update(at=time.time(), data=data)
    return data


def _fmt(n: float) -> str:
    return f"{n:,.2f}" if n < 1e6 else f"{n:,.0f}"


@catub.cat_cmd(
    pattern=r"birr(?:\s+(.+))?$",
    command=("birr", plugin_category),
    info={
        "header": "Ethiopian birr exchange rates. No API key.",
        "description": "Official/market reference rates from ExchangeRate-API's open feed, updated once a day. "
        "Not the parallel (black) market rate.",
        "usage": ["{tr}birr", "{tr}birr <amount> <currency>  (→ ETB)", "{tr}birr <amount>  (ETB → majors)"],
        "examples": ["{tr}birr", "{tr}birr 100 usd", "{tr}birr 25000", "{tr}birr 50 sar"],
    },
)
async def birr_cmd(event):
    "Birr rates."
    args = (event.pattern_match.group(1) or "").upper().replace(",", "").split()
    try:
        data = await _rates()
    except Exception as e:
        return await edit_delete(event, f"Rates unavailable right now: `{e}`", 8)
    rates = data["rates"]
    etb_per = lambda cur: rates["ETB"] / rates[cur]  # noqa: E731
    updated = datetime.utcfromtimestamp(data.get("time_last_update_unix", time.time())).strftime("%d %b %Y")

    amount = None
    if args and re.fullmatch(r"\d+(\.\d+)?", args[0]):
        amount = float(args.pop(0))
    cur = args[0] if args else None
    if cur and cur not in rates:
        return await edit_delete(event, f"`Unknown currency {cur}.`", 6)

    if amount is not None and cur and cur != "ETB":
        val = amount * etb_per(cur)
        text = f"{FLAGS.get(cur, '💱')} <b>{_fmt(amount)} {cur}</b> = 🇪🇹 <b>{_fmt(val)} ETB</b>\n<i>1 {cur} = {etb_per(cur):,.4f} ETB</i>"
    elif amount is not None:
        lines = [f"🇪🇹 <b>{_fmt(amount)} ETB</b> =\n"]
        lines += [f"{FLAGS.get(c, '💱')} {_fmt(amount / etb_per(c))} {c}" for c in MAJORS if c in rates]
        text = "\n".join(lines)
    else:
        show = [cur] if cur else MAJORS
        lines = ["💱 <b>Birr rates</b>\n"]
        lines += [f"{FLAGS.get(c, '💱')} 1 {c} = <b>{etb_per(c):,.2f}</b> ETB" for c in show if c in rates]
        text = "\n".join(lines)
    await edit_or_reply(event, f"{text}\n\n<i>Updated {updated} · official rate, not parallel market</i>", parse_mode="html")
