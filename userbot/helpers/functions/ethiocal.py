# Ethiopian calendar, Ethiopian time, Ge'ez numerals and Ethiopian holidays (pure math).

from datetime import date, timedelta

ETH_EPOCH = 1723856  # JDN offset used by the Beyene-Kudlek conversion
_ORD_TO_JDN = 1721425  # date.toordinal() + this = Julian Day Number

MONTHS_AM = ["መስከረም", "ጥቅምት", "ኅዳር", "ታኅሣሥ", "ጥር", "የካቲት", "መጋቢት", "ሚያዝያ", "ግንቦት", "ሰኔ", "ሐምሌ", "ነሐሴ", "ጳጉሜን"]
MONTHS_EN = ["Meskerem", "Tikimt", "Hidar", "Tahsas", "Tir", "Yekatit", "Megabit", "Miyazya", "Ginbot", "Sene", "Hamle", "Nehase", "Pagume"]
WEEKDAYS_AM = ["ሰኞ", "ማክሰኞ", "ረቡዕ", "ሐሙስ", "ዓርብ", "ቅዳሜ", "እሑድ"]
WEEKDAYS_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

_GEEZ_ONES = "፩፪፫፬፭፮፯፰፱"
_GEEZ_TENS = "፲፳፴፵፶፷፸፹፺"


def _jdn(d: date) -> int:
    return d.toordinal() + _ORD_TO_JDN


def _from_jdn(jdn: int) -> date:
    return date.fromordinal(jdn - _ORD_TO_JDN)


def to_ethiopian(d: date):
    """Gregorian date -> (year, month 1-13, day)."""
    jdn = _jdn(d)
    r = (jdn - ETH_EPOCH) % 1461
    n = r % 365 + 365 * (r // 1460)
    year = 4 * ((jdn - ETH_EPOCH) // 1461) + r // 365 - r // 1460
    return year, n // 30 + 1, n % 30 + 1


def is_eth_leap(year: int) -> bool:
    return year % 4 == 3


def to_gregorian(year: int, month: int, day: int) -> date:
    """Ethiopian date -> Gregorian date. Raises ValueError for impossible dates."""
    if not 1 <= month <= 13 or not 1 <= day <= 30:
        raise ValueError("month must be 1-13 and day 1-30")
    if month == 13 and day > (6 if is_eth_leap(year) else 5):
        raise ValueError(f"Pagume {year} has only {6 if is_eth_leap(year) else 5} days")
    jdn = (ETH_EPOCH + 365) + 365 * (year - 1) + year // 4 + 30 * month + day - 31
    return _from_jdn(jdn)


def geez(n: int) -> str:
    """Integer -> Ge'ez numerals, e.g. 2019 -> ፳፻፲፱."""
    if n <= 0:
        return str(n)
    s = str(n)
    if len(s) % 2:
        s = "0" + s
    pairs = [s[i : i + 2] for i in range(0, len(s), 2)]
    out = []
    for i, p in enumerate(pairs):
        pos = len(pairs) - 1 - i  # 0 = last pair
        t, o = int(p[0]), int(p[1])
        chunk = (_GEEZ_TENS[t - 1] if t else "") + (_GEEZ_ONES[o - 1] if o else "")
        if pos == 0:
            out.append(chunk)
            continue
        sep = "፻" if pos % 2 else "፼"
        if chunk == "፩" and i == 0:
            chunk = ""  # a leading one is implied: ፻ = 100, ፼ = 10000
        if chunk or sep == "፼" or i == 0:
            out.append(chunk + sep)
    return "".join(out)


def eth_time(hour: int, minute: int):
    """24h clock -> (Ethiopian hour 1-12, minute, Amharic period, English period)."""
    h = (hour - 6) % 12
    h = 12 if h == 0 else h
    if 6 <= hour < 12:
        period = ("ጠዋት", "morning")
    elif 12 <= hour < 18:
        period = ("ከሰዓት", "afternoon")
    elif 18 <= hour < 24:
        period = ("ማታ", "evening")
    else:
        period = ("ሌሊት", "night")
    return h, minute, period[0], period[1]


def format_eth(d: date, amharic=True) -> str:
    y, m, day = to_ethiopian(d)
    if amharic:
        return f"{WEEKDAYS_AM[d.weekday()]}፣ {MONTHS_AM[m - 1]} {day} ቀን {y} ዓ.ም"
    return f"{WEEKDAYS_EN[d.weekday()]}, {MONTHS_EN[m - 1]} {day}, {y} E.C."


def parse_month(token: str):
    t = token.strip().lower()
    for i, (am, en) in enumerate(zip(MONTHS_AM, MONTHS_EN), 1):
        if t in (am, en.lower()) or (len(t) >= 3 and en.lower().startswith(t)):
            return i
    if t.isdigit() and 1 <= int(t) <= 13:
        return int(t)
    return None


# ───────────────────────────── holidays ──────────────────────────────


def orthodox_easter(year: int) -> date:
    """Ethiopian/Eastern Orthodox Easter (Fasika), Gregorian date (valid 1900-2099)."""
    a, b, c = year % 4, year % 7, year % 19
    d = (19 * c + 15) % 30
    e = (2 * a + 4 * b - d + 34) % 7
    month = (d + e + 114) // 31
    day = (d + e + 114) % 31 + 1
    return date(year, month, day) + timedelta(days=13)


def _islamic_to_date(y: int, m: int, d: int) -> date:
    """Tabular (arithmetical) Islamic calendar; real dates depend on moon sighting (±1-2 days)."""
    jdn = d + int(29.5 * (m - 1) + 0.99999) + (y - 1) * 354 + (3 + 11 * y) // 30 + 1948439
    return _from_jdn(jdn)


def _islamic_year(d: date) -> int:
    return int((_jdn(d) - 1948439) * 30 / 10631) + 1


# (key, English, Amharic, ethiopian month, day)
_FIXED_ETH = [
    ("enkutatash", "Enkutatash (New Year)", "እንቁጣጣሽ", 1, 1),
    ("meskel", "Meskel", "መስቀል", 1, 17),
    ("timket", "Timket (Epiphany)", "ጥምቀት", 5, 11),
    ("adwa", "Adwa Victory Day", "የዓድዋ ድል", 6, 23),
    ("patriots", "Patriots' Victory Day", "የአርበኞች ቀን", 8, 27),
    ("derg", "Downfall of the Derg", "ግንቦት 20", 9, 20),
]


def holidays_between(start: date, end: date):
    """[(date, key, english, amharic, approx)] sorted, for start <= date <= end."""
    out = []
    for gy in range(start.year - 1, end.year + 2):
        ey = to_ethiopian(date(gy, 12, 31))[0]
        for key, en, am, m, d in _FIXED_ETH:
            for y in (ey - 1, ey):
                out.append((to_gregorian(y, m, d), key, en, am, False))
        # Genna is Tahsas 29, or Tahsas 28 after a leap year: always 7 January
        out.append((date(gy, 1, 7), "genna", "Genna (Christmas)", "ገና", False))
        out.append((date(gy, 5, 1), "labour", "International Labour Day", "የሠራተኞች ቀን", False))
        fasika = orthodox_easter(gy)
        out.append((fasika, "fasika", "Fasika (Easter)", "ፋሲካ", False))
        out.append((fasika - timedelta(days=2), "siklet", "Siklet (Good Friday)", "ስቅለት", False))
        hy = _islamic_year(date(gy, 6, 1))
        for y in (hy - 1, hy, hy + 1):
            out.append((_islamic_to_date(y, 10, 1), "eid-fitr", "Eid al-Fitr", "ኢድ አል ፈጥር", True))
            out.append((_islamic_to_date(y, 12, 10), "eid-adha", "Eid al-Adha (Arefa)", "ኢድ አል አድሃ (አረፋ)", True))
            out.append((_islamic_to_date(y, 3, 12), "mawlid", "Mawlid", "መውሊድ", True))
    seen, result = set(), []
    for h in sorted(out):
        if start <= h[0] <= end and (h[0], h[1]) not in seen:
            seen.add((h[0], h[1]))
            result.append(h)
    return result


def next_holiday(key: str, today: date):
    for h in holidays_between(today, today + timedelta(days=400)):
        if h[1] == key or key in h[2].lower():
            return h
    return None


HOLIDAY_KEYS = [k for k, *_ in _FIXED_ETH] + ["genna", "labour", "fasika", "siklet", "eid-fitr", "eid-adha", "mawlid"]
