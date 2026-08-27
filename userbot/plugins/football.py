# Football scores — API-Football + football-data.org
from ..helpers.functions.football_api import (
    build_fball_help,
    build_fballset_help,
    parse_football_args,
    run_football_query,
)
from ..sql_helper.globals import addgvar, gvarstatus
from . import catub, edit_delete, edit_or_reply

plugin_category = "extra"


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
    info=build_fball_help("apisports"),
)
async def fball_cmd(event):
    """API-Football scores (.fball)."""
    await _football_handler(event, "apisports")


@catub.cat_cmd(
    pattern=r"afball(?:\s|$)([\s\S]*)",
    command=("afball", plugin_category),
    info=build_fball_help(
        "apisports",
        header="Alias of fball (API-Football)",
        note="Same as {tr}fball — uses API_FOOTBALL_KEY. See {tr}help fball for full guide.",
    ),
)
async def afball_cmd(event):
    """Alias of .fball."""
    await _football_handler(event, "apisports")


@catub.cat_cmd(
    pattern=r"fdata(?:\s|$)([\s\S]*)",
    command=("fdata", plugin_category),
    info=build_fball_help("fdata"),
)
async def fdata_cmd(event):
    """football-data.org scores (.fdata)."""
    await _football_handler(event, "fdata")


@catub.cat_cmd(
    pattern=r"ffdata(?:\s|$)([\s\S]*)",
    command=("ffdata", plugin_category),
    info=build_fball_help(
        "fdata",
        header="Alias of fdata (football-data.org)",
        note="Same as {tr}fdata — uses FOOTBALL_DATA_API_KEY. See {tr}help fdata for full guide.",
    ),
)
async def ffdata_cmd(event):
    """Alias of .fdata."""
    await _football_handler(event, "fdata")


@catub.cat_cmd(
    pattern=r"fballset(?:\s|$)([\s\S]*)",
    command=("fballset", plugin_category),
    info=build_fballset_help(),
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
