# Bot command catalog for .askme — built from live CMD_INFO / PLG_INFO / GRP_INFO.
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from ...Config import Config
from ...core.cmdinfo import get_key, getkey

_CATALOG_CACHE: Optional[str] = None
_INDEX_CACHE: Optional[str] = None
_CACHE_CMD_COUNT = 0

CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "bot_command_catalog.md"

# Curated quick answers (synced with common user questions + recent plugins)
QUICK_TOPICS: Dict[str, List[str]] = {
    "gif": ["vtogif", "gif", "gifs", "klipy", "kgifs"],
    "video": ["vtogif", "gif", "circle", "spin", "split", "trim"],
    "sticker": ["mkstcr", "makestcr", "stoi", "kang", "vas", "mtoi", "stcr"],
    "background": ["mkstcr", "makestcr", "rembg", "removebg"],
    "summarize": ["sum", "summarize", "osum", "osummarize", "sumthis"],
    "weather": ["meteo", "owf", "climate", "weather"],
    "football": ["fball", "fdata", "afball", "ffdata", "fballset"],
    "soccer": ["fball", "fdata", "afball", "ffdata", "fballset"],
    "premier": ["fball", "fdata", "afball", "ffdata"],
    "laliga": ["fball", "fdata", "afball", "ffdata"],
    "champions": ["fball", "fdata", "afball", "ffdata"],
    "ucl": ["fball", "fdata", "afball", "ffdata"],
    "scores": ["fball", "fdata", "afball", "ffdata", "score", "cric"],
    "live": ["fball", "fdata", "afball", "ffdata"],
    "image": ["img", "dimg", "rembg", "ocr"],
    "ai": [
        "ai",
        "ai on",
        "ai off",
        "ai enable",
        "ai disable",
        "ai status",
        "ai provider",
        "ai clear",
        "aiswitch",
        "askme",
        "botask",
        "aireply",
        "digest",
        "ask",
        "aiafk",
        "gpt",
        "dalle",
    ],
    "provider": ["aiswitch", "ai provider", "ai status"],
    "nvidia": ["aiswitch", "ai provider"],
    "mistral": ["aiswitch", "ai provider"],
    "groq": ["aiswitch", "ai provider"],
    "openrouter": ["aiswitch", "ai provider"],
    "help": ["help", "cmds", "s", "askme", "botask"],
    "digest": ["digest"],
    "portfolio": ["portfolio", "resume"],
    "leetcode": ["lcstatus", "lcremind", "leetcode"],
    "love": [
        "love",
        "lovemorning",
        "lovenight",
        "lovepoem",
        "lovehaiku",
        "loveletter",
        "lovestcr",
        "dirtytalk",
        "reallydirty",
        "desire",
        "crushmeter",
        "heartburst",
        "lovekiss",
    ],
    "romance": ["soulmate", "foreverlove", "weddingpoem", "loverose", "lovespell"],
}

# Extra query synonyms → topic keys in QUICK_TOPICS (or command-name hints)
QUERY_SYNONYMS: Dict[str, List[str]] = {
    "epl": ["premier", "football"],
    "pl": ["premier", "football"],
    "liga": ["laliga", "football"],
    "spain": ["laliga", "football"],
    "england": ["premier", "football"],
    "match": ["football", "scores"],
    "fixture": ["football", "scores"],
    "fixtures": ["football", "scores"],
    "result": ["football", "scores"],
    "results": ["football", "scores"],
    "llm": ["ai", "provider"],
    "chatgpt": ["ai", "gpt"],
    "switch": ["provider", "aiswitch"],
    "forecast": ["weather"],
    "temperature": ["weather"],
    "stickerpack": ["sticker"],
    "meme": ["sticker", "gif"],
}


def _prefix() -> str:
    return getattr(Config, "COMMAND_HAND_LER", ".") or "."


def _cmd_meta(cmd: str) -> Tuple[str, str, str]:
    """Return (plugin, category, intro_text)."""
    from ...core import CMD_INFO

    plugin = get_key(cmd) or "unknown"
    category = getkey(plugin) or "misc"
    intro = ""
    if cmd in CMD_INFO and CMD_INFO[cmd]:
        intro = str(CMD_INFO[cmd][0] or "")
    return plugin, category, intro


def _expand_query_words(words: Set[str]) -> Set[str]:
    expanded = set(words)
    for w in list(words):
        for syn in QUERY_SYNONYMS.get(w, []):
            expanded.add(syn)
    return expanded


def _score_cmd(cmd: str, intro: str, plugin: str, category: str, words: set[str]) -> int:
    blob = f"{cmd} {plugin} {category} {intro}".lower()
    score = 0
    for w in words:
        if len(w) < 2:
            continue
        if w == cmd.lower():
            score += 8
        if w in cmd.lower():
            score += 5
        if w in blob:
            score += 2
    for topic, cmds in QUICK_TOPICS.items():
        if topic in words and cmd in cmds:
            score += 10
    return score


def search_commands(query: str, limit: int = 30) -> List[str]:
    from ...core import CMD_INFO

    words = _expand_query_words(set(re.findall(r"[a-z0-9_]+", (query or "").lower())))
    if not words:
        return []

    scored: List[Tuple[int, str]] = []
    for cmd in CMD_INFO:
        plugin, category, intro = _cmd_meta(cmd)
        s = _score_cmd(cmd, intro, plugin, category, words)
        if s > 0:
            scored.append((s, cmd))

    scored.sort(key=lambda x: (-x[0], x[1]))
    return [c for _, c in scored[:limit]]


def _format_cmd_block(cmd: str, compact: bool = False) -> str:
    plugin, category, intro = _cmd_meta(cmd)
    p = _prefix()
    if compact:
        header = ""
        if intro:
            m = re.search(r"__([^_]+)__", intro)
            header = m.group(1) if m else ""
            if not header:
                # Fall back to first non-empty plain line from info description
                for line in intro.splitlines():
                    clean = re.sub(r"[*_`]", "", line).strip()
                    if clean and not clean.startswith("{"):
                        header = clean[:100]
                        break
        line = f"`{p}{cmd}` [{category}/{plugin}]"
        if header:
            line += f" — {header}"
        usages = re.findall(r"`" + re.escape(p) + r"([^`]+)`", intro)
        if not usages:
            usages = re.findall(r"\{tr\}([^\s`|,]+)", intro)
        if usages:
            line += f" | try: `{p}{usages[0].strip()}`"
        return line

    block = [f"### {p}{cmd} (plugin: {plugin}, category: {category})"]
    if intro:
        block.append(intro.replace("{tr}", p))
    else:
        block.append("_No detailed help text — use `.help -c " + cmd + "`._")
    return "\n".join(block)


def build_category_index() -> str:
    from ...core import GRP_INFO, PLG_INFO

    lines = ["## Command index by category"]
    p = _prefix()
    # Prefer known order, then any extra categories present at runtime
    preferred = ("admin", "bot", "fun", "misc", "tools", "utils", "extra")
    cats = list(preferred)
    for cat in sorted(GRP_INFO.keys()):
        if cat not in cats and cat.lower() not in {c.lower() for c in cats}:
            cats.append(cat)

    for cat in cats:
        plugins = GRP_INFO.get(cat) or GRP_INFO.get(cat.lower()) or []
        cmds: List[str] = []
        for plg in plugins:
            cmds.extend(PLG_INFO.get(plg, []))
        uniq = sorted(set(cmds))
        if uniq:
            lines.append(
                f"\n**{cat}** ({len(uniq)}): "
                + ", ".join(f"`{p}{c}`" for c in uniq)
            )
    return "\n".join(lines)


def build_full_catalog(compact: bool = True) -> str:
    from ...core import CMD_INFO

    p = _prefix()
    lines = [
        f"# Bot command catalog ({len(CMD_INFO)} commands)",
        f"Prefix: `{p}`",
        "",
        "## Meta / navigation",
        f"- `{p}help <plugin|command>` — structured help",
        f"- `{p}help -c <command>` — single command help",
        f"- `{p}cmds` — all commands list",
        f"- `{p}s <keyword>` — search command names",
        f"- `{p}askme <question>` — ask in plain English (alias: `{p}botask`)",
        f"- `{p}aiswitch <mistral|nvidia|groq|openrouter>` — switch AI provider",
        "",
        "## All commands (compact)",
    ]
    for cmd in sorted(CMD_INFO.keys()):
        lines.append(_format_cmd_block(cmd, compact=compact))
    return "\n".join(lines)


def refresh_catalog_store() -> str:
    """Rebuild in-memory cache and write markdown catalog to disk."""
    global _CATALOG_CACHE, _INDEX_CACHE, _CACHE_CMD_COUNT
    from ...core import CMD_INFO

    _CATALOG_CACHE = build_full_catalog(compact=True)
    _INDEX_CACHE = build_category_index()
    _CACHE_CMD_COUNT = len(CMD_INFO)

    try:
        CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CATALOG_PATH.write_text(
            _CATALOG_CACHE + "\n\n" + _INDEX_CACHE, encoding="utf-8"
        )
    except OSError:
        pass

    return _CATALOG_CACHE


def _ensure_cache() -> None:
    from ...core import CMD_INFO

    if _CATALOG_CACHE is None or _CACHE_CMD_COUNT != len(CMD_INFO):
        refresh_catalog_store()


def build_askme_context(query: str) -> str:
    """Context block injected into the AI user message — includes FULL catalog."""
    _ensure_cache()
    p = _prefix()
    matches = search_commands(query, limit=30)

    # Boost with topic aliases (including synonym-expanded topics)
    qwords = _expand_query_words(set(re.findall(r"[a-z0-9_]+", query.lower())))
    for topic, cmds in QUICK_TOPICS.items():
        if topic in qwords:
            for c in cmds:
                if c not in matches:
                    matches.append(c)

    # Only keep matches that actually exist in CMD_INFO
    from ...core import CMD_INFO

    matches = [c for c in matches if c in CMD_INFO]

    lines = [
        f"USER QUESTION: {query.strip()}",
        f"COMMAND PREFIX: `{p}` (always show commands with this prefix)",
        f"TOTAL LOADED COMMANDS: {len(CMD_INFO)}",
        "",
        "## Best matching commands (prefer these)",
    ]
    if matches:
        for cmd in matches[:25]:
            lines.append(_format_cmd_block(cmd, compact=True))
    else:
        lines.append("_No strong name match — use the full catalog below._")

    lines.append("")
    lines.append(_INDEX_CACHE or build_category_index())
    lines.append("")
    # Full compact catalog so the model knows every command, including recent ones
    lines.append("## FULL COMMAND CATALOG (every loaded command)")
    lines.append(_CATALOG_CACHE or build_full_catalog(compact=True))
    lines.append("")
    lines.append(
        "## Rules for your answer\n"
        "- Only recommend commands that appear in the catalog above.\n"
        "- Prefer Best matching commands when relevant; otherwise search the FULL catalog.\n"
        "- Give 1–3 best commands with syntax, reply/media requirements, and examples.\n"
        "- Mention API keys / env vars only if relevant.\n"
        "- Include recent AI providers: mistral, nvidia, groq, openrouter via `.aiswitch`.\n"
        f"- For full detail: `{p}help -c <command>`.\n"
        f"- If unsure: suggest `{p}s <keyword>` or `{p}cmds <plugin>`."
    )
    return "\n".join(lines)


def build_askme_help() -> dict:
    p = "{tr}"
    return {
        "header": "AI bot help — ask anything about commands in plain English",
        "description": (
            "Natural-language guide for this userbot. Feeds the live full command catalog "
            "to the AI and explains which command to use, with examples. Catalog stored in "
            "userbot/data/bot_command_catalog.md (auto-updated)."
        ),
        "usage": [
            f"{p}askme sticker from image remove background",
            f"{p}askme what is the cmd to convert video to gifs",
            f"{p}askme command to generate stickers",
            f"{p}botask how do I summarize another chat silently",
            f"{p}askme football live scores",
            f"{p}askme switch to groq ai",
        ],
        "examples": [
            f"{p}askme search gifs online",
            f"{p}botask weather forecast without api key",
            f"{p}askme last 50 messages job posts",
            f"{p}askme premier league and laliga scores",
        ],
        "note": (
            "Requires AI provider (same as .ai). Alias: .botask. Does not run commands — "
            "only explains them. Uses the full live command catalog. "
            "Use .help -c <cmd> for official static help."
        ),
    }
