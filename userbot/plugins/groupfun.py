# Group fun — giveaways/raffles with an animated draw, and activity leaderboards.
#
#   .raffle [n]        reply to a post: winners among people who reacted or replied
#                      no reply: winners among people active in the last 500 messages
#   .top [24h|7d|30d]  who talks the most

import asyncio
import random
from collections import Counter
from datetime import timedelta

from telethon.errors import RPCError
from telethon.tl import functions, types

from userbot import catub

from ..core.managers import edit_or_reply
from ..helpers.functions.kittychat import esc, mention_html, name_of
from ..helpers.functions.kittytime import now_utc

plugin_category = "fun"
MEDALS = ["🥇", "🥈", "🥉"]


async def _reactors(client, peer, msg_id):
    users, offset = {}, None
    for _ in range(10):
        res = await client(functions.messages.GetMessageReactionsListRequest(peer=peer, id=msg_id, limit=100, offset=offset))
        by_id = {u.id: u for u in res.users}
        for r in res.reactions:
            uid = getattr(r.peer_id, "user_id", None)
            if uid in by_id:
                users[uid] = by_id[uid]
        offset = res.next_offset
        if not offset:
            break
    return users


@catub.cat_cmd(
    pattern=r"raffle(?:\s+(\d+))?$",
    command=("raffle", plugin_category),
    info={
        "header": "Run a giveaway: pick random winners with an animated draw.",
        "description": "Reply to a post to draw from everyone who reacted to it or replied to it. "
        "Without a reply, draws from people active in the last 500 messages. Bots and you are excluded.",
        "usage": ["{tr}raffle [winners]  (reply to the giveaway post)", "{tr}raffle [winners]"],
        "examples": ["{tr}raffle", "{tr}raffle 3"],
    },
)
async def raffle_cmd(event):
    "Giveaway draw."
    n = max(1, min(int(event.pattern_match.group(1) or 1), 10))
    reply = await event.get_reply_message()
    peer = await event.get_input_chat()
    me = await event.client.get_me()
    status = await edit_or_reply(event, "🎟 `Collecting entries…`")
    pool, source = {}, ""

    if reply:
        try:
            pool.update(await _reactors(event.client, peer, reply.id))
        except RPCError:
            pass
        try:
            async for m in event.client.iter_messages(event.chat_id, reply_to=reply.id, limit=1000):
                if m.sender:
                    pool[m.sender_id] = m.sender
        except RPCError:
            pass
        try:
            async for m in event.client.iter_messages(event.chat_id, limit=1500, min_id=reply.id):
                if m.reply_to and m.reply_to.reply_to_msg_id == reply.id and m.sender:
                    pool[m.sender_id] = m.sender
        except RPCError:
            pass
        source = "reacted or replied"
    else:
        async for m in event.client.iter_messages(event.chat_id, limit=500):
            if m.sender:
                pool[m.sender_id] = m.sender
        source = "were active recently"

    entrants = [u for uid, u in pool.items() if isinstance(u, types.User) and not u.bot and not u.deleted and uid != me.id]
    if reply and reply.sender_id in {u.id for u in entrants} and reply.sender_id != me.id and len(entrants) > n:
        entrants = [u for u in entrants if u.id != reply.sender_id]  # the host doesn't win their own giveaway
    if len(entrants) < 1:
        return await status.edit("Nobody to draw from yet 🤷")
    n = min(n, len(entrants))

    for i in range(7):
        sample = random.sample(entrants, min(3, len(entrants)))
        reel = "  ·  ".join(esc(name_of(u)) for u in sample)
        try:
            await status.edit(f"🎰 <b>Drawing…</b>\n\n{reel}", parse_mode="html")
        except RPCError:
            pass
        await asyncio.sleep(0.6 + i * 0.15)

    winners = random.sample(entrants, n)
    lines = [f"🎉 <b>{'Winner' if n == 1 else 'Winners'}</b> — out of {len(entrants)} people who {source}\n"]
    for i, u in enumerate(winners):
        lines.append(f"{MEDALS[i] if i < 3 else '🏅'} {mention_html(u)}")
    lines.append("\nCongratulations! 🥳")
    await status.edit("\n".join(lines), parse_mode="html")


@catub.cat_cmd(
    pattern=r"top(?:\s+(24h|7d|30d|day|week|month))?$",
    command=("top", plugin_category),
    info={
        "header": "Leaderboard: who talks the most in this chat.",
        "usage": "{tr}top [24h | 7d | 30d]",
        "examples": ["{tr}top", "{tr}top 7d"],
    },
)
async def top_cmd(event):
    "Activity leaderboard."
    span = (event.pattern_match.group(1) or "24h").lower()
    days = {"24h": 1, "day": 1, "7d": 7, "week": 7, "30d": 30, "month": 30}[span]
    cutoff = now_utc() - timedelta(days=days)
    status = await edit_or_reply(event, "`Counting…`")
    counts, words, names = Counter(), Counter(), {}
    scanned = 0
    async for m in event.client.iter_messages(event.chat_id, limit=20000):
        if m.date < cutoff:
            break
        scanned += 1
        if not m.sender_id or getattr(m, "action", None):
            continue
        counts[m.sender_id] += 1
        words[m.sender_id] += len((m.raw_text or "").split())
        names.setdefault(m.sender_id, m.sender)
    if not counts:
        return await status.edit("Silence… nobody talked in that period 🦗")
    total = sum(counts.values())
    peak = counts.most_common(1)[0][1]
    label = {1: "last 24 hours", 7: "last 7 days", 30: "last 30 days"}[days]
    lines = [f"🏆 <b>Top talkers</b> — {label}\n{total:,} messages from {len(counts)} people\n"]
    for i, (uid, c) in enumerate(counts.most_common(10)):
        bar = "▰" * max(1, round(8 * c / peak)) + "▱" * (8 - max(1, round(8 * c / peak)))
        rank = MEDALS[i] if i < 3 else f"<code>{i + 1:>2}</code>"
        lines.append(f"{rank} {mention_html(names.get(uid), str(uid))}\n     {bar} {c} msgs · {words[uid]:,} words")
    if scanned >= 20000:
        lines.append("\n<i>(stopped at 20,000 messages)</i>")
    await status.edit("\n".join(lines), parse_mode="html")
