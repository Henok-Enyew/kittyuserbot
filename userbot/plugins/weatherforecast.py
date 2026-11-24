# Multi-day weather — Open-Meteo + OpenWeatherMap
import re

from ..helpers.functions.weather_forecast import (
    build_meteo_help,
    build_meteoset_help,
    parse_weather_args,
    run_weather_query,
)
from ..sql_helper.globals import addgvar, gvarstatus
from . import catub, edit_delete, edit_or_reply

plugin_category = "utils"


def _weather_gvars() -> dict:
    return {
        "METEO_DAYS": gvarstatus("METEO_DAYS"),
        "METEO_UNITS": gvarstatus("METEO_UNITS"),
    }


def _default_city() -> str:
    return gvarstatus("DEFCITY") or "Delhi"


def _strip_imperial(raw: str) -> tuple[str, bool]:
    imperial = bool(re.search(r"\b(imperial|f)\s*$", raw, re.I))
    if imperial:
        raw = re.sub(r"\s+(imperial|f)\s*$", "", raw, flags=re.I).strip()
    return raw, imperial


async def _weather_handler(event, provider: str):
    raw = (event.pattern_match.group(1) or "").strip()
    raw, imperial_flag = _strip_imperial(raw)
    query = parse_weather_args(raw, _weather_gvars(), _default_city())
    if imperial_flag:
        query.imperial = True

    if provider == "owm":
        from ..helpers.functions.weather_forecast import _owm_key

        if not _owm_key():
            return await edit_delete(
                event,
                "**OPEN_WEATHER_MAP_APPID is not set.**\n"
                "Add it to your Config / env (and do not overwrite it with `None` later in the same file).",
                12,
            )

    label = "Open-Meteo" if provider == "openmeteo" else "OpenWeatherMap"
    catevent = await edit_or_reply(event, f"`Fetching {label} forecast…`")
    try:
        text = await run_weather_query(provider, query)
        await catevent.edit(text)
    except ValueError as e:
        await edit_delete(catevent, str(e), 10)
    except Exception as e:
        await edit_delete(catevent, f"**Weather error:**\n`{e}`", 12)


@catub.cat_cmd(
    pattern=r"meteo(?:\s|$)([\s\S]*)",
    command=("meteo", plugin_category),
    info=build_meteo_help("openmeteo"),
)
async def meteo_cmd(event):
    """Open-Meteo forecast (.meteo)."""
    await _weather_handler(event, "openmeteo")


@catub.cat_cmd(
    pattern=r"wmeteo(?:\s|$)([\s\S]*)",
    command=("wmeteo", plugin_category),
    info=build_meteo_help(
        "openmeteo",
        header="Alias of meteo (Open-Meteo)",
        note="Same as {tr}meteo — no API key. See {tr}help meteo for full guide.",
    ),
)
async def wmeteo_cmd(event):
    """Alias of .meteo."""
    await _weather_handler(event, "openmeteo")


@catub.cat_cmd(
    pattern=r"owf(?:\s|$)([\s\S]*)",
    command=("owf", plugin_category),
    info=build_meteo_help("owm"),
)
async def owf_cmd(event):
    """OpenWeatherMap forecast (.owf)."""
    await _weather_handler(event, "owm")


@catub.cat_cmd(
    pattern=r"wowf(?:\s|$)([\s\S]*)",
    command=("wowf", plugin_category),
    info=build_meteo_help(
        "owm",
        header="Alias of owf (OpenWeatherMap)",
        note="Same as {tr}owf — needs OPEN_WEATHER_MAP_APPID. See {tr}help owf for full guide.",
    ),
)
async def wowf_cmd(event):
    """Alias of .owf."""
    await _weather_handler(event, "owm")


@catub.cat_cmd(
    pattern=r"meteoset(?:\s|$)([\s\S]*)",
    command=("meteoset", plugin_category),
    info=build_meteoset_help(),
)
async def meteoset(event):
    """Configure meteo defaults."""
    raw = (event.pattern_match.group(1) or "").strip()
    if not raw:
        return await edit_or_reply(
            event,
            "**Meteo defaults**\n"
            f"DAYS: `{gvarstatus('METEO_DAYS') or '7'}`\n"
            f"UNITS: `{gvarstatus('METEO_UNITS') or 'metric'}`",
        )
    parts = raw.split(maxsplit=1)
    key = parts[0].lower()
    val = (parts[1] if len(parts) > 1 else "").lower()
    if key == "days" and val.isdigit():
        addgvar("METEO_DAYS", val)
        return await edit_or_reply(event, f"`METEO_DAYS` set to **{val}**")
    if key == "units" and val in {"imperial", "metric", "f", "c"}:
        u = "imperial" if val in {"imperial", "f"} else "metric"
        addgvar("METEO_UNITS", u)
        return await edit_or_reply(event, f"`METEO_UNITS` set to **{u}**")
    await edit_or_reply(
        event,
        "`Usage:` `.meteoset days 7` | `.meteoset units imperial`",
    )
