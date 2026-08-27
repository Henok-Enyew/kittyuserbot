# Multi-day weather — Open-Meteo (no key) + OpenWeatherMap forecast.
from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import httpx

from ...Config import Config

METEO_GEO = "https://geocoding-api.open-meteo.com/v1/search"
METEO_FORECAST = "https://api.open-meteo.com/v1/forecast"
OWM_GEO = "https://api.openweathermap.org/geo/1.0/direct"
HTTP_HEADERS = {"User-Agent": "CatUserBot/weather-forecast"}
OWM_FORECAST = "https://api.openweathermap.org/data/2.5/forecast"
OWM_CURRENT = "https://api.openweathermap.org/data/2.5/weather"

_CACHE: Dict[str, Tuple[float, Any]] = {}


@dataclass
class Location:
    name: str
    lat: float
    lon: float
    country: str = ""
    timezone: str = "auto"


@dataclass
class DailyForecast:
    day: date
    label: str
    temp_min: float
    temp_max: float
    precip_mm: float
    wind_kmh: float
    weather: str
    emoji: str


@dataclass
class HourlyForecast:
    when: datetime
    temp_c: float
    weather: str
    emoji: str
    precip_mm: float = 0.0


@dataclass
class WeatherQuery:
    mode: str = "forecast"  # forecast, today, tomorrow, hourly
    city: str = ""
    days: int = 7
    hours: int = 24
    imperial: bool = False


def _cache_get(key: str) -> Any:
    item = _CACHE.get(key)
    if not item or time.time() > item[0]:
        return None
    return item[1]


def _cache_set(key: str, value: Any, ttl: int) -> None:
    _CACHE[key] = (time.time() + ttl, value)


def _owm_key() -> Optional[str]:
    for source in (
        os.environ.get("OPEN_WEATHER_MAP_APPID"),
        getattr(Config, "OPEN_WEATHER_MAP_APPID", None),
    ):
        if source and str(source).strip().lower() not in {"", "none", "null"}:
            return str(source).strip()
    return None


def _location_today(tz_name: str) -> date:
    try:
        tz_name = tz_name if tz_name and tz_name != "auto" else "UTC"
        return datetime.now(ZoneInfo(tz_name)).date()
    except Exception:
        return date.today()


def _day_label(day: date, local_today: date) -> str:
    if day == local_today:
        return "Today"
    if day == local_today + timedelta(days=1):
        return "Tomorrow"
    return day.strftime("%a")


def _default_days(gvars: dict) -> int:
    try:
        return int(
            gvars.get("METEO_DAYS")
            or getattr(Config, "METEO_DEFAULT_DAYS", None)
            or 7
        )
    except (TypeError, ValueError):
        return 7


def _imperial_default(gvars: dict) -> bool:
    u = (gvars.get("METEO_UNITS") or "").lower()
    return u in {"imperial", "f", "us"}


def wmo_label(code: int) -> Tuple[str, str]:
    table = {
        0: ("Clear", "☀️"),
        1: ("Mainly clear", "🌤"),
        2: ("Partly cloudy", "⛅"),
        3: ("Overcast", "☁️"),
        45: ("Fog", "🌫"),
        48: ("Fog", "🌫"),
        51: ("Drizzle", "🌦"),
        53: ("Drizzle", "🌦"),
        55: ("Drizzle", "🌦"),
        61: ("Rain", "🌧"),
        63: ("Rain", "🌧"),
        65: ("Heavy rain", "🌧"),
        71: ("Snow", "🌨"),
        73: ("Snow", "🌨"),
        75: ("Heavy snow", "🌨"),
        80: ("Showers", "🌦"),
        81: ("Showers", "🌦"),
        82: ("Heavy showers", "🌦"),
        95: ("Thunderstorm", "⛈"),
        96: ("Thunderstorm", "⛈"),
        99: ("Thunderstorm", "⛈"),
    }
    return table.get(code, ("Weather", "🌡"))


def parse_weather_args(raw: str, gvars: dict, default_city: str) -> WeatherQuery:
    text = (raw or "").strip()
    imperial = _imperial_default(gvars)
    days = max(1, min(_default_days(gvars), 16))

    if not text:
        return WeatherQuery(mode="forecast", city=default_city, days=days, imperial=imperial)

    if text.lower() in {"f", "imperial", "us"}:
        return WeatherQuery(mode="forecast", city=default_city, days=days, imperial=True)

    parts = text.split()
    mode = parts[0].lower()

    if mode == "today":
        city = " ".join(parts[1:]) or default_city
        return WeatherQuery(mode="today", city=city, imperial=imperial)

    if mode == "tomorrow":
        city = " ".join(parts[1:]) or default_city
        return WeatherQuery(mode="tomorrow", city=city, imperial=imperial)

    if mode == "hourly":
        hours = 24
        rest = parts[1:]
        if rest and rest[0].isdigit():
            hours = max(1, min(int(rest[0]), 48))
            rest = rest[1:]
        city = " ".join(rest) or default_city
        return WeatherQuery(mode="hourly", city=city, hours=hours, imperial=imperial)

    # leading number = days
    if parts[0].isdigit():
        days = max(1, min(int(parts[0]), 16))
        city = " ".join(parts[1:]) or default_city
        return WeatherQuery(mode="forecast", city=city, days=days, imperial=imperial)

    if mode in {"f", "imperial"}:
        city = " ".join(parts[1:]) or default_city
        return WeatherQuery(mode="forecast", city=city, days=days, imperial=True)

    return WeatherQuery(
        mode="forecast", city=text or default_city, days=days, imperial=imperial
    )


def _c_to_f(c: float) -> float:
    return c * 9 / 5 + 32


def _kmh_to_mph(k: float) -> float:
    return k * 0.621371


def format_temp(c: float, imperial: bool) -> str:
    if imperial:
        return f"{_c_to_f(c):.0f}°F"
    return f"{c:.0f}°C"


def format_wind(kmh: float, imperial: bool) -> str:
    if imperial:
        return f"{_kmh_to_mph(kmh):.0f} mph"
    return f"{kmh:.0f} km/h"


def format_daily_report(
    loc: Location,
    days: List[DailyForecast],
    provider: str,
    imperial: bool,
) -> str:
    if not days:
        return f"**Weather — {loc.name}**\n_No forecast data._"
    unit = "°F" if imperial else "°C"
    lines = [
        f"**Weather — {loc.name}**",
        f"_Provider: {provider}_ · _Units: {'imperial' if imperial else 'metric'}_",
        "",
    ]
    for d in days:
        tmin = _c_to_f(d.temp_min) if imperial else d.temp_min
        tmax = _c_to_f(d.temp_max) if imperial else d.temp_max
        wind = format_wind(d.wind_kmh, imperial)
        lines.append(
            f"{d.emoji} **{d.label}** ({d.day.strftime('%a %d %b')})\n"
            f"   {tmin:.0f}{unit} – {tmax:.0f}{unit} · {d.weather}\n"
            f"   🌧 {d.precip_mm:.1f} mm · 💨 {wind}"
        )
    return "\n".join(lines)


def format_hourly_report(
    loc: Location,
    hours: List[HourlyForecast],
    provider: str,
    imperial: bool,
) -> str:
    lines = [
        f"**Hourly — {loc.name}**",
        f"_Provider: {provider}_",
        "",
    ]
    for h in hours[:24]:
        t = _c_to_f(h.temp_c) if imperial else h.temp_c
        unit = "°F" if imperial else "°C"
        lines.append(
            f"{h.emoji} `{h.when.strftime('%a %H:%M')}` — {t:.0f}{unit} · {h.weather}"
        )
    return "\n".join(lines)


async def geocode_openmeteo(city: str) -> Location:
    cache_key = f"geocode:meteo:{city.lower()}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    params = {"name": city, "count": 5, "language": "en", "format": "json"}
    async with httpx.AsyncClient(timeout=20, headers=HTTP_HEADERS) as client:
        r = await client.get(METEO_GEO, params=params)
        if r.status_code != 200:
            raise RuntimeError(f"Open-Meteo geocoding HTTP {r.status_code}")
        data = r.json()

    results = data.get("results") or []
    if not results:
        raise ValueError(f"Location not found: {city}")

    best = results[0]
    loc = Location(
        name=best.get("name") or city,
        lat=float(best["latitude"]),
        lon=float(best["longitude"]),
        country=best.get("country") or "",
        timezone=best.get("timezone") or "auto",
    )
    if loc.country:
        loc.name = f"{loc.name}, {loc.country}"
    _cache_set(cache_key, loc, 86400)
    return loc


async def geocode_owm(city: str) -> Location:
    key = _owm_key()
    if not key:
        raise ValueError(
            "OPEN_WEATHER_MAP_APPID is not set. Get a key at https://openweathermap.org/api"
        )
    cache_key = f"geocode:owm:{city.lower()}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    params = {"q": city, "limit": 1, "appid": key}
    async with httpx.AsyncClient(timeout=20, headers=HTTP_HEADERS) as client:
        r = await client.get(OWM_GEO, params=params)
        if r.status_code != 200:
            raise RuntimeError(f"OpenWeatherMap geocoding HTTP {r.status_code}")
        data = r.json()

    if not isinstance(data, list) or not data:
        raise ValueError(f"Location not found: {city}")

    item = data[0]
    loc = Location(
        name=f"{item.get('name')}, {item.get('country', '')}".strip(", "),
        lat=float(item["lat"]),
        lon=float(item["lon"]),
        country=item.get("country") or "",
    )
    _cache_set(cache_key, loc, 86400)
    return loc


async def openmeteo_forecast(loc: Location, days: int) -> List[DailyForecast]:
    cache_key = f"meteo:fc:{loc.lat}:{loc.lon}:{days}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    params = {
        "latitude": loc.lat,
        "longitude": loc.lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode,windspeed_10m_max",
        "forecast_days": max(1, min(days, 16)),
        "timezone": loc.timezone or "auto",
    }
    async with httpx.AsyncClient(timeout=25, headers=HTTP_HEADERS) as client:
        r = await client.get(METEO_FORECAST, params=params)
        if r.status_code != 200:
            raise RuntimeError(f"Open-Meteo forecast HTTP {r.status_code}")
        data = r.json()

    if data.get("error"):
        raise RuntimeError(f"Open-Meteo error: {data.get('reason', data['error'])}")

    daily = data.get("daily") or {}
    dates = daily.get("time") or []
    if not dates:
        raise RuntimeError(
            "Open-Meteo returned no daily forecast. Try again or use `.owf`."
        )

    out: List[DailyForecast] = []
    local_today = _location_today(loc.timezone)

    for i, ds in enumerate(dates):
        d = date.fromisoformat(ds)
        code = int((daily.get("weathercode") or [0])[i])
        wmo_name, emoji = wmo_label(code)
        label = _day_label(d, local_today)

        out.append(
            DailyForecast(
                day=d,
                label=label,
                temp_min=float((daily.get("temperature_2m_min") or [0])[i]),
                temp_max=float((daily.get("temperature_2m_max") or [0])[i]),
                precip_mm=float((daily.get("precipitation_sum") or [0])[i]),
                wind_kmh=float((daily.get("windspeed_10m_max") or [0])[i]),
                weather=wmo_name,
                emoji=emoji,
            )
        )

    _cache_set(cache_key, out, 1800)
    return out


async def openmeteo_hourly(loc: Location, hours: int) -> List[HourlyForecast]:
    params = {
        "latitude": loc.lat,
        "longitude": loc.lon,
        "hourly": "temperature_2m,weathercode,precipitation",
        "forecast_days": min(3, (hours // 24) + 1),
        "timezone": loc.timezone or "auto",
    }
    async with httpx.AsyncClient(timeout=25, headers=HTTP_HEADERS) as client:
        r = await client.get(METEO_FORECAST, params=params)
        if r.status_code != 200:
            raise RuntimeError(f"Open-Meteo hourly HTTP {r.status_code}")
        data = r.json()

    hourly = data.get("hourly") or {}
    times = hourly.get("time") or []
    out: List[HourlyForecast] = []
    now = datetime.now(ZoneInfo(loc.timezone if loc.timezone != "auto" else "UTC"))

    for i, ts in enumerate(times):
        when = datetime.fromisoformat(ts)
        if when.tzinfo is None:
            when = when.replace(tzinfo=ZoneInfo("UTC"))
        if when < now.replace(minute=0, second=0, microsecond=0):
            continue
        code = int((hourly.get("weathercode") or [0])[i])
        w, em = wmo_label(code)
        out.append(
            HourlyForecast(
                when=when,
                temp_c=float((hourly.get("temperature_2m") or [0])[i]),
                weather=w,
                emoji=em,
                precip_mm=float((hourly.get("precipitation") or [0])[i]),
            )
        )
        if len(out) >= hours:
            break
    return out


def _owm_weather_emoji(main: str) -> str:
    m = (main or "").lower()
    return {
        "clear": "☀️",
        "clouds": "☁️",
        "rain": "🌧",
        "drizzle": "🌦",
        "thunderstorm": "⛈",
        "snow": "🌨",
        "mist": "🌫",
        "fog": "🌫",
    }.get(m, "🌡")


async def owm_forecast_daily(loc: Location, days: int) -> List[DailyForecast]:
    key = _owm_key()
    if not key:
        raise ValueError("OPEN_WEATHER_MAP_APPID is not set.")

    params = {"lat": loc.lat, "lon": loc.lon, "appid": key, "units": "metric"}
    async with httpx.AsyncClient(timeout=25, headers=HTTP_HEADERS) as client:
        r = await client.get(OWM_FORECAST, params=params)
        if r.status_code != 200:
            raise RuntimeError(f"OpenWeatherMap forecast HTTP {r.status_code}")
        data = r.json()

    if str(data.get("cod")) not in {"200", "200.0"}:
        raise RuntimeError(f"OpenWeatherMap error: {data.get('message', data)}")

    by_day: Dict[date, dict] = {}
    for item in data.get("list") or []:
        dt = datetime.fromtimestamp(item["dt"], tz=ZoneInfo("UTC"))
        d = dt.date()
        main = item.get("main") or {}
        temp = main.get("temp")
        if d not in by_day:
            by_day[d] = {
                "min": temp,
                "max": temp,
                "precip": 0.0,
                "wind": (item.get("wind") or {}).get("speed", 0) * 3.6,
                "weather": (item.get("weather") or [{}])[0].get("main", ""),
            }
        else:
            by_day[d]["min"] = min(by_day[d]["min"], temp)
            by_day[d]["max"] = max(by_day[d]["max"], temp)
            by_day[d]["wind"] = max(
                by_day[d]["wind"], (item.get("wind") or {}).get("speed", 0) * 3.6
            )
        rain = (item.get("rain") or {}).get("3h") or 0
        by_day[d]["precip"] += float(rain)

    today = _location_today(loc.timezone or "UTC")
    out: List[DailyForecast] = []
    for d in sorted(by_day.keys())[: min(days, 8)]:
        row = by_day[d]
        label = _day_label(d, today)
        emoji = _owm_weather_emoji(row["weather"])
        out.append(
            DailyForecast(
                day=d,
                label=label,
                temp_min=float(row["min"]),
                temp_max=float(row["max"]),
                precip_mm=float(row["precip"]),
                wind_kmh=float(row["wind"]),
                weather=row["weather"],
                emoji=emoji,
            )
        )
    if not out:
        raise RuntimeError(
            "OpenWeatherMap returned no forecast data for this location."
        )
    return out
    key = _owm_key()
    if not key:
        raise ValueError("OPEN_WEATHER_MAP_APPID is not set.")

    params = {"lat": loc.lat, "lon": loc.lon, "appid": key, "units": "metric"}
    async with httpx.AsyncClient(timeout=25, headers=HTTP_HEADERS) as client:
        r = await client.get(OWM_FORECAST, params=params)
        if r.status_code != 200:
            raise RuntimeError(f"OpenWeatherMap forecast HTTP {r.status_code}")
        data = r.json()

    if str(data.get("cod")) not in {"200", "200.0"}:
        raise RuntimeError(f"OpenWeatherMap error: {data.get('message', data)}")

    out: List[HourlyForecast] = []
    now = datetime.now(ZoneInfo("UTC"))
    for item in data.get("list") or []:
        when = datetime.fromtimestamp(item["dt"], tz=ZoneInfo("UTC"))
        if when < now:
            continue
        wobj = (item.get("weather") or [{}])[0]
        main = wobj.get("main", "")
        out.append(
            HourlyForecast(
                when=when,
                temp_c=float((item.get("main") or {}).get("temp", 0)),
                weather=main,
                emoji=_owm_weather_emoji(main),
                precip_mm=float((item.get("rain") or {}).get("3h") or 0),
            )
        )
        if len(out) >= hours:
            break
    return out


async def run_weather_query(provider: str, query: WeatherQuery) -> str:
    if provider in {"openmeteo", "meteo"}:
        loc = await geocode_openmeteo(query.city)
        today_local = _location_today(loc.timezone)
        if query.mode == "hourly":
            hours = await openmeteo_hourly(loc, query.hours)
            return format_hourly_report(loc, hours, "Open-Meteo", query.imperial)
        fetch_days = query.days
        if query.mode == "today":
            fetch_days = 3
        elif query.mode == "tomorrow":
            fetch_days = 3
        daily = await openmeteo_forecast(loc, fetch_days)
        if query.mode == "today":
            daily = [d for d in daily if d.day == today_local] or daily[:1]
        elif query.mode == "tomorrow":
            tomorrow = today_local + timedelta(days=1)
            daily = [d for d in daily if d.day == tomorrow] or daily[1:2]
        else:
            daily = daily[: query.days]
        return format_daily_report(loc, daily, "Open-Meteo", query.imperial)

    # OpenWeatherMap (.owf / .wowf)
    loc = await geocode_owm(query.city)
    today_local = _location_today(loc.timezone or "UTC")
    if query.mode == "hourly":
        hours = await owm_hourly(loc, query.hours)
        return format_hourly_report(loc, hours, "OpenWeatherMap", query.imperial)
    days_n = query.days
    if query.mode in {"today", "tomorrow"}:
        days_n = 3
    daily = await owm_forecast_daily(loc, days_n)
    if query.mode == "today":
        daily = [d for d in daily if d.day == today_local] or daily[:1]
    elif query.mode == "tomorrow":
        tomorrow = today_local + timedelta(days=1)
        daily = [d for d in daily if d.day == tomorrow] or daily[1:2]
    else:
        daily = daily[: query.days]
    return format_daily_report(loc, daily, "OpenWeatherMap", query.imperial)
