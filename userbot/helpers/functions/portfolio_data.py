# Portfolio card content — keep in sync with HENOK_FULL_PROFILE in conversation.py

import html

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

    pre_block = (
        "┌─────────────────────────────────┐\n"
        f"│ {name:<31} │\n"
        f"│ {title:<31} │\n"
        f"│ {location:<31} │\n"
        "└─────────────────────────────────┘"
    )

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
