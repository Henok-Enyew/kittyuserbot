# Chat Wrapped — a Spotify-Wrapped-style recap card for any chat. No AI needed.
#
#   .wrapped            last 3000 messages of this chat
#   .wrapped 10000      bigger sample
#   .wrapped (reply)    one person's wrapped in this chat

import asyncio
import os
import shutil
import tempfile

from userbot import catub

from ..Config import Config
from ..core.managers import edit_delete, edit_or_reply
from ..helpers.functions.kittychat import esc, media_kind, name_of
from ..helpers.functions.kittytime import to_local
from ..helpers.functions.wrapped_card import ChatStats, compact, fmt_secs, render

plugin_category = "fun"


@catub.cat_cmd(
    pattern=r"wrapped(?:\s+(\d+))?$",
    command=("wrapped", plugin_category),
    info={
        "header": "Chat Wrapped: a recap card for this chat.",
        "description": "Reads the recent history and draws a recap image: top talkers, peak hours, busiest "
        "weekday, longest streak, top words, fastest replier, night-owl share and more. "
        "Reply to someone to get that person's wrapped. Everything is computed locally, no AI.",
        "usage": ["{tr}wrapped [messages]", "{tr}wrapped [messages]  (reply to a user)"],
        "examples": ["{tr}wrapped", "{tr}wrapped 10000"],
    },
)
async def wrapped_cmd(event):
    "Chat recap card."
    limit = int(event.pattern_match.group(1) or 3000)
    limit = max(100, min(limit, 30000))
    reply = await event.get_reply_message()
    person = await reply.get_sender() if reply and reply.sender_id else None
    chat = await event.get_chat()

    status = await edit_or_reply(event, f"`Reading up to {compact(limit)} messages…`")
    msgs = []
    async for m in event.client.iter_messages(chat, limit=limit, from_user=person):
        if m.id == event.id or getattr(m, "action", None):
            continue
        msgs.append(m)
        if len(msgs) % 2000 == 0:
            try:
                await status.edit(f"`Reading… {compact(len(msgs))} so far`")
            except Exception:
                pass
    if len(msgs) < 20:
        return await status.edit("Not enough messages for a recap (need at least 20).")

    await status.edit("`Crunching the numbers…`")
    stats = ChatStats(title=name_of(person) if person else name_of(chat, "Chat"))
    me = await event.client.get_me()
    sender_cache = {}
    for m in reversed(msgs):
        sid = m.sender_id or getattr(m.peer_id, "channel_id", 0)
        if sid not in sender_cache:
            sender_cache[sid] = "You" if sid == me.id else name_of(m.sender, f"User {sid}")
        stats.add(sid, sender_cache[sid], to_local(m.date), m.message or "", media_kind(m))

    subtitle = f"· {compact(stats.total)} msgs analysed"
    if person:
        subtitle += f" in {name_of(chat)}"
    tmp = tempfile.mkdtemp(dir=Config.TMP_DOWNLOAD_DIRECTORY)
    path = os.path.join(tmp, "wrapped.jpg")
    try:
        await asyncio.get_running_loop().run_in_executor(None, render, stats, path, subtitle)

        top = stats.senders.most_common(3)
        talkers = ", ".join(f"{esc(stats.names[s])} ({n})" for s, n in top)
        emojis = " ".join(e for e, _ in stats.emojis.most_common(8)) or "—"
        words = ", ".join(w for w, _ in stats.words.most_common(10)) or "—"
        bd, bd_n = stats.busiest_day()
        lines = [
            f"🎁 <b>{esc(stats.title)} — Wrapped</b>",
            f"💬 {stats.total:,} messages · {stats.words_total:,} words · {len(stats.days)} active days",
        ]
        if not person:
            lines.append(f"🏆 {talkers}")
        lines += [
            f"🔥 Streak: {stats.streak()} days · ⏰ peak {stats.busiest_hour():02d}:00"
            + (f" · 📅 {bd:%d %b} ({bd_n})" if bd else ""),
            f"😂 {emojis}",
            f"🔤 {esc(words)}",
        ]
        replies = stats.median_reply()
        if len(replies) >= 2:
            ranked = sorted(replies.items(), key=lambda kv: kv[1])[:3]
            lines.append("⚡ Reply speed: " + ", ".join(f"{esc(stats.names[s])} {fmt_secs(t)}" for s, t in ranked))
        await event.client.send_file(
            event.chat_id,
            path,
            caption="\n".join(lines)[:1020],
            parse_mode="html",
            reply_to=event.reply_to_msg_id,
        )
        await status.delete()
    except Exception as e:
        await edit_delete(status, f"Wrapped failed: `{e}`", 10)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
