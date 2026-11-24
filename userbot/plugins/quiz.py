# Trivia quizzes as native Telegram quiz polls (Open Trivia DB — free, no key).
#
#   .quiz                      one random question
#   .quiz 5 science hard       5 hard science questions
#   .quiz list                 categories

import asyncio
import html
import random

import aiohttp
from telethon.errors import RPCError
from telethon.tl import types

from userbot import catub

from ..Config import Config
from ..core.managers import edit_delete, edit_or_reply

plugin_category = "fun"

API = "https://opentdb.com/api.php"
CATEGORIES = {
    "general": 9,
    "books": 10,
    "film": 11,
    "movies": 11,
    "music": 12,
    "musicals": 13,
    "tv": 14,
    "games": 15,
    "videogames": 15,
    "boardgames": 16,
    "science": 17,
    "nature": 17,
    "computers": 18,
    "tech": 18,
    "math": 19,
    "mythology": 20,
    "sports": 21,
    "football": 21,
    "geography": 22,
    "history": 23,
    "politics": 24,
    "art": 25,
    "celebrities": 26,
    "animals": 27,
    "vehicles": 28,
    "cars": 28,
    "comics": 29,
    "gadgets": 30,
    "anime": 31,
    "cartoons": 32,
}
LEVELS = ("easy", "medium", "hard")
EMOJI = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}


def _clip(text: str, n: int) -> str:
    return text if len(text) <= n else text[: n - 1] + "…"


async def _fetch(amount: int, category: int | None, level: str | None):
    params = {"amount": amount, "type": "multiple"}
    if category:
        params["category"] = category
    if level:
        params["difficulty"] = level
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as s:
        async with s.get(API, params=params) as r:
            data = await r.json(content_type=None)
    if data.get("response_code") == 5:
        await asyncio.sleep(5.5)  # API allows 1 request / 5s per IP
        return await _fetch(amount, category, level)
    return data.get("results", [])


def _poll_media(q: dict) -> types.InputMediaPoll:
    question = _clip(html.unescape(q["question"]), 255)
    correct = _clip(html.unescape(q["correct_answer"]), 100)
    options = [correct] + [_clip(html.unescape(a), 100) for a in q["incorrect_answers"]]
    random.shuffle(options)
    answers = [
        types.PollAnswer(text=types.TextWithEntities(text=opt, entities=[]), option=bytes([i]))
        for i, opt in enumerate(options)
    ]
    return types.InputMediaPoll(
        poll=types.Poll(
            id=random.getrandbits(62),
            question=types.TextWithEntities(text=question, entities=[]),
            answers=answers,
            quiz=True,
        ),
        correct_answers=[bytes([options.index(correct)])],
        solution=_clip(f"{EMOJI.get(q['difficulty'], '')} {html.unescape(q['category'])} · {q['difficulty']}", 200),
        solution_entities=[],
    )


@catub.cat_cmd(
    pattern=r"quiz(?:\s+(.+))?$",
    command=("quiz", plugin_category),
    info={
        "header": "Trivia quiz polls. Tap an answer to see if you're right.",
        "description": "Sends real Telegram quiz polls (the ones with confetti for the right answer) "
        "using questions from Open Trivia DB. Great for group chats.",
        "usage": ["{tr}quiz [count] [category] [easy|medium|hard]", "{tr}quiz list"],
        "examples": ["{tr}quiz", "{tr}quiz 5 science", "{tr}quiz anime hard", "{tr}quiz 3 football easy"],
    },
)
async def quiz_cmd(event):
    "Trivia quiz polls."
    args = (event.pattern_match.group(1) or "").lower().split()
    if args[:1] == ["list"]:
        cats = sorted({k for k in CATEGORIES})
        return await edit_or_reply(
            event,
            "🧠 **Quiz categories**\n" + ", ".join(f"`{c}`" for c in cats) + f"\n\nLevels: `{'`, `'.join(LEVELS)}`",
        )
    amount, category, level = 1, None, None
    for a in args:
        if a.isdigit():
            amount = max(1, min(int(a), 10))
        elif a in LEVELS:
            level = a
        elif a in CATEGORIES:
            category = CATEGORIES[a]
        else:
            return await edit_delete(event, f"Unknown option `{a}`. See `{Config.COMMAND_HAND_LER}quiz list`.", 8)

    status = await edit_or_reply(event, "`Picking questions…`")
    try:
        questions = await _fetch(amount, category, level)
    except Exception as e:
        return await edit_delete(status, f"Trivia API unavailable: `{e}`", 8)
    if not questions:
        return await edit_delete(status, "No questions for that combination, try another.", 8)
    await status.delete()
    for i, q in enumerate(questions):
        try:
            await event.client.send_message(event.chat_id, file=_poll_media(q))
        except RPCError as e:
            return await event.client.send_message(event.chat_id, f"Couldn't send the quiz: `{e}`")
        if i < len(questions) - 1:
            await asyncio.sleep(1.5)
