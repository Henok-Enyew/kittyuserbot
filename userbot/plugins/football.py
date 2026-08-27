# Football scores — API-Football + football-data.org
from ..helpers.functions.football_api import parse_football_args, run_football_query
from ..sql_helper.globals import addgvar, gvarstatus
from . import catub, edit_delete, edit_or_reply

plugin_category = "extra"

_FBALL_HELP = {
    "header": "Football scores & fixtures",
    "description": (
        "Live scores, today, upcoming/past fixtures, team view, and league filter. "
        "`.fball`/`.afball` use API-Football; `.fdata`/`.ffdata` use football-data.org."
    ),
    "usage": [
        "{tr}fball live",
        "{tr}fball today",
        "{tr}fball up 7",
        "{tr}fball past 5",
        "{tr}fball team Arsenal 2024",
        "{tr}fball league PL",
    ],
    "examples": [
        "{tr}afball live",
        "{tr}ffdata up 5",
        "{tr}fdata team Real Madrid",
    ],
    "note": (
        "Requires API_FOOTBALL_KEY (.fball) or FOOTBALL_DATA_API_KEY (.fdata). "
        "Defaults: gvars FBALL_UP_DAYS, FBALL_PAST_DAYS, FBALL_LEAGUE — set via {tr}fballset."
    ),
}


def _gvars() -> dict:
    return {
        "FBALL_UP_DAYS": gvarstatus("FBALL_UP_DAYS"),
        "FBALL_PAST_DAYS": gvarstatus("FBALL_PAST_DAYS"),
        "FBALL_LEAGUE": gvarstatus("FBALL_LEAGUE"),
    }


async def _football_handler(event, provider: str):
    raw = (event.pattern_match.group(1) or "").strip()
    catevent = await edit_or_reply(event, "`Fetching football data…`")
    try:
        query = parse_football_args(raw, _gvars())
        text = await run_football_query(provider, query)
        await catevent.edit(text)
    except ValueError as e:
        await edit_delete(catevent, str(e), 10)
    except Exception as e:
        await edit_delete(catevent, f"**Football error:**\n`{e}`", 12)


@catub.cat_cmd(
    pattern=r"fball(?:\s|$)([\s\S]*)",
    command=("fball", plugin_category),
    info=_FBALL_HELP,
)
async def fball_cmd(event):
    """API-Football scores (.fball)."""
    await _football_handler(event, "apisports")


@catub.cat_cmd(
    pattern=r"afball(?:\s|$)([\s\S]*)",
    command=("afball", plugin_category),
    info={**_FBALL_HELP, "header": "Alias of fball (API-Football)"},
)
async def afball_cmd(event):
    """Alias of .fball."""
    await _football_handler(event, "apisports")


@catub.cat_cmd(
    pattern=r"fdata(?:\s|$)([\s\S]*)",
    command=("fdata", plugin_category),
    info={
        **_FBALL_HELP,
        "header": "Football scores via football-data.org",
        "note": "Requires FOOTBALL_DATA_API_KEY. Free tier: top competitions only.",
    },
)
async def fdata_cmd(event):
    """football-data.org scores (.fdata)."""
    await _football_handler(event, "fdata")


@catub.cat_cmd(
    pattern=r"ffdata(?:\s|$)([\s\S]*)",
    command=("ffdata", plugin_category),
    info={**_FBALL_HELP, "header": "Alias of fdata (football-data.org)"},
)
async def ffdata_cmd(event):
    """Alias of .fdata."""
    await _football_handler(event, "fdata")


@catub.cat_cmd(
    pattern=r"fballset(?:\s|$)([\s\S]*)",
    command=("fballset", plugin_category),
    info={
        "header": "Set football plugin defaults (gvars)",
        "usage": [
            "{tr}fballset up 7",
            "{tr}fballset past 5",
            "{tr}fballset league PL",
        ],
        "examples": "{tr}fballset league UCL",
    },
)
async def fballset(event):
    """Configure football defaults."""
    raw = (event.pattern_match.group(1) or "").strip()
    if not raw:
        return await edit_or_reply(
            event,
            "**Football defaults**\n"
            f"UP_DAYS: `{gvarstatus('FBALL_UP_DAYS') or '3'}`\n"
            f"PAST_DAYS: `{gvarstatus('FBALL_PAST_DAYS') or '3'}`\n"
            f"LEAGUE: `{gvarstatus('FBALL_LEAGUE') or '—'}`",
        )
    parts = raw.split(maxsplit=1)
    key = parts[0].lower()
    val = parts[1].strip() if len(parts) > 1 else ""
    if key in {"up", "upcoming"} and val.isdigit():
        addgvar("FBALL_UP_DAYS", val)
        return await edit_or_reply(event, f"`FBALL_UP_DAYS` set to **{val}**")
    if key in {"past", "results"} and val.isdigit():
        addgvar("FBALL_PAST_DAYS", val)
        return await edit_or_reply(event, f"`FBALL_PAST_DAYS` set to **{val}**")
    if key == "league" and val:
        addgvar("FBALL_LEAGUE", val.upper())
        return await edit_or_reply(event, f"`FBALL_LEAGUE` set to **{val.upper()}**")
    await edit_or_reply(
        event,
        "`Usage:` `.fballset up 7` | `.fballset past 5` | `.fballset league PL`",
    )
