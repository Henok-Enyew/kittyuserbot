# Portfolio card content — keep in sync with HENOK_FULL_PROFILE in conversation.py

import html
import unicodedata

PORTFOLIO = {
    "name": "👋 I am Henok Enyew Andargie",
    "title": "Full-stack Software Engineer",
    "location": "Addis Ababa, Ethiopia",
    "tagline": "Building products that ship — React, Django, Node, Golang AI integration.",
    "projects": [
        {
            "name": "Pyyol",
            "desc": "Competitive AI-agent strategy game platform",
            "url": "https://pyyol.com",
        },
        {
            "name": "Tankwa Tours",
            "desc": "Production tourism booking platform",
            "url": "https://tankwatours.com/",
        },
        {
            "name": "FinAsk",
            "desc": "AI university compare/discovery for Ethiopian students",
            "url": "https://finask-frontend.vercel.app/",
        },
    ],
    "skills": (
        "React, TypeScript, Django, Node.js, Golang, PostgreSQL, Docker, "
        "REST APIs, AI/LLM integration, TDD"
    ),
    "links": {
        "Portfolio": "https://henokenyew.me",
        "GitHub": "https://github.com/henok-enyew",
        "LinkedIn": "https://www.linkedin.com/in/henokenyew/",
        "LeetCode": "https://leetcode.com/henokenyew",
        "Telegram": "https://t.me/henokenyew",
    },
    "portfolio_url": "https://henokenyew.me",
}

_BORDER_TOP = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
_BORDER_BOT = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
_BOX_MIN_INNER = 31


def _display_width(text: str) -> int:
    """Terminal/monospace column width (emoji/CJK count as 2)."""
    width = 0
    for ch in text:
        if unicodedata.combining(ch) or unicodedata.category(ch) in ("Cf", "Mn", "Me"):
            continue
        if unicodedata.east_asian_width(ch) in ("F", "W"):
            width += 2
        else:
            width += 1
    return width


def _pad_display(text: str, width: int) -> str:
    return text + (" " * max(0, width - _display_width(text)))


def _ascii_box(lines: list[str], min_inner: int = _BOX_MIN_INNER) -> str:
    """Build a box whose right border aligns even when lines contain emoji."""
    inner = max(min_inner, max((_display_width(line) for line in lines), default=0))
    top = "┌" + "─" * (inner + 2) + "┐"
    mid = [f"│ {_pad_display(line, inner)} │" for line in lines]
    bot = "└" + "─" * (inner + 2) + "┘"
    return "\n".join([top, *mid, bot])


def _link_row(resume_url: str | None = None) -> str:
    """Top/bottom hyperlink bar."""
    items = [
        f'<a href="{PORTFOLIO["links"]["Portfolio"]}">Portfolio</a>',
        f'<a href="{PORTFOLIO["links"]["GitHub"]}">GitHub</a>',
        f'<a href="{PORTFOLIO["links"]["LinkedIn"]}">LinkedIn</a>',
    ]
    if resume_url:
        items.append(f'<a href="{html.escape(resume_url, quote=True)}">Resume</a>')
    return " | ".join(items)


def build_portfolio_html(
    hire_open: bool = False,
    show_hire_status: bool = False,
    resume_url: str | None = None,
) -> str:
    """Polished HTML card for Telegram."""
    p = PORTFOLIO
    name = html.escape(p["name"])
    title = html.escape(p["title"])
    location = html.escape(p["location"])
    tagline = html.escape(p["tagline"])
    skills = html.escape(p["skills"])

    pre_block = _ascii_box([name, title, location])

    lines = [
        _BORDER_TOP,
        _link_row(resume_url),
        "",
        f"<pre>{html.escape(pre_block)}</pre>",
        "",
        f"<i>{tagline}</i>",
        "",
        "<b>Top Projects</b>",
    ]
    for proj in p["projects"]:
        nm = html.escape(proj["name"])
        desc = html.escape(proj["desc"])
        url = html.escape(proj["url"], quote=True)
        lines.append(f"  🚀 <a href=\"{url}\">{nm}</a> — {desc}")

    lines += [
        "",
        "<b>Skills</b>",
        f"<code>{skills}</code>",
        "",
        "<b>Connect</b>",
    ]
    for label, url in p["links"].items():
        lines.append(
            f"  • <a href=\"{html.escape(url, quote=True)}\">{html.escape(label)}</a>"
        )

    if show_hire_status:
        if hire_open:
            lines += ["", "<b>Status:</b> 🟢 Open to opportunities"]
        else:
            lines += ["", "<b>Status:</b> ⚪ Not actively looking"]

    lines += ["", _link_row(resume_url), _BORDER_BOT]
    return "\n".join(lines)


def build_portfolio_text(hire_open: bool = False, show_hire_status: bool = False) -> str:
    """Legacy markdown builder (kept for compatibility)."""
    p = PORTFOLIO
    lines = [
        f"**{p['name']}**",
        f"_{p['title']}_ · {p['location']}",
        "",
        p["tagline"],
        "",
        "**Top Projects**",
    ]
    for proj in p["projects"]:
        lines.append(f"• [{proj['name']}]({proj['url']}) — {proj['desc']}")
    lines += [
        "",
        f"**Skills:** {p['skills']}",
        "",
        "**Links**",
    ]
    for label, url in p["links"].items():
        lines.append(f"• [{label}]({url})")
    if show_hire_status:
        status = "Open to opportunities" if hire_open else "Not actively looking"
        lines += ["", f"**Status:** {status}"]
    return "\n".join(lines)
