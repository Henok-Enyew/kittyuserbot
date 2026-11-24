# LeetCode submission checker — GraphQL recentAcSubmissionList
from __future__ import annotations

import time
from datetime import datetime
from typing import List, Optional, Tuple

import requests

from ...Config import Config
from .digest_builder import ADDIS_TZ, addis_now

LC_GRAPHQL_URL = "https://leetcode.com/graphql"
LC_HEADERS = {
    "Content-Type": "application/json",
    "Referer": "https://leetcode.com",
    "User-Agent": "Mozilla/5.0 (compatible; KittyUserBot/1.0)",
}

_SUBMISSIONS_QUERY = """
query recentAcSubmissions($username: String!, $limit: Int!) {
  recentAcSubmissionList(username: $username, limit: $limit) {
    id
    title
    titleSlug
    timestamp
  }
}
"""

_CACHE: dict = {}
_CACHE_TTL = 300  # 5 minutes


def _leetcode_username() -> str:
    return (
        getattr(Config, "LEETCODE_USERNAME", None)
        or "Enoch90s"
    ).strip()


def fetch_recent_submissions(
    username: Optional[str] = None,
    limit: int = 20,
    use_cache: bool = True,
) -> List[dict]:
    """Fetch recent accepted submissions from LeetCode GraphQL."""
    username = (username or _leetcode_username()).strip()
    limit = max(1, min(limit, 20))
    cache_key = f"{username}:{limit}"

    if use_cache and cache_key in _CACHE:
        cached_at, data = _CACHE[cache_key]
        if time.time() - cached_at < _CACHE_TTL:
            return data

    payload = {
        "operationName": "recentAcSubmissions",
        "query": _SUBMISSIONS_QUERY,
        "variables": {"username": username, "limit": limit},
    }
    try:
        resp = requests.post(
            LC_GRAPHQL_URL,
            json=payload,
            headers=LC_HEADERS,
            timeout=20,
        )
        resp.raise_for_status()
        body = resp.json()
    except Exception as e:
        raise RuntimeError(f"LeetCode API request failed: {e}") from e

    if body.get("errors"):
        raise RuntimeError(f"LeetCode GraphQL error: {body['errors']}")

    data = body.get("data") or {}
    submissions = data.get("recentAcSubmissionList") or []
    if use_cache:
        _CACHE[cache_key] = (time.time(), submissions)
    return submissions


def submissions_on_date(
    submissions: List[dict],
    target_date: datetime.date,
) -> List[str]:
    """Return titles of submissions accepted on target_date (local date per ts)."""
    titles: List[str] = []
    for item in submissions:
        ts = item.get("timestamp")
        if ts is None:
            continue
        try:
            ts_int = int(ts)
        except (TypeError, ValueError):
            continue
        sub_date = datetime.fromtimestamp(ts_int, tz=ADDIS_TZ).date()
        if sub_date == target_date:
            title = item.get("title") or item.get("titleSlug") or "Unknown"
            titles.append(str(title))
    return titles


def solved_today(username: Optional[str] = None) -> Tuple[bool, List[str]]:
    """
    Check if user solved at least one problem today (Africa/Addis_Ababa calendar day).
    Returns (solved_flag, list_of_titles_today).
    """
    username = (username or _leetcode_username()).strip()
    today = addis_now().date()
    submissions = fetch_recent_submissions(username=username, limit=20)
    titles = submissions_on_date(submissions, today)
    return bool(titles), titles


def today_status_text(username: Optional[str] = None) -> str:
    """Human-readable status for .lcstatus."""
    username = (username or _leetcode_username()).strip()
    today = addis_now()
    try:
        solved, titles = solved_today(username)
    except Exception as e:
        return f"**LeetCode check failed:** `{e}`"

    date_str = today.strftime("%Y-%m-%d")
    tz_label = "Africa/Addis_Ababa (UTC+3)"
    header = f"**LeetCode — {username}**\n**Date:** `{date_str}` ({tz_label})"

    if not solved:
        return (
            f"{header}\n\n"
            "**Status:** No accepted solves today yet.\n"
            f"Profile: https://leetcode.com/u/{username}/"
        )

    lines = [header, "", f"**Status:** **{len(titles)}** solve(s) today", "", "**Problems:**"]
    for t in titles:
        lines.append(f"• {t}")
    return "\n".join(lines)
