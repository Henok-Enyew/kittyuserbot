# Insight — read receipts, reaction breakdowns, who's online, and silent reading.
#
#   .seen       who read your message (groups) / when it was read (PMs)
#   .whoreact   who reacted with what
#   .online     who is online right now in this group (or a user's last seen)
#   .peek       read a chat without sending read receipts

from collections import OrderedDict
from datetime import timedelta

from telethon.errors import RPCError
from telethon.tl import functions, types

from userbot import catub

from ..core.managers import edit_delete, edit_or_reply
from ..helpers.functions.kittychat import (
    describe,
    esc,
    mention_html,
    name_of,
    resolve_chat,
)
from ..helpers.functions.kittytime import ago, fmt_local, now_utc

plugin_category = "utils"

_LAST_INBOX = []  # dialogs listed by the last bare `.peek`, for `.peek 3`


def _reaction_label(reaction) -> str:
    if isinstance(reaction, types.ReactionEmoji):
        return reaction.emoticon
    if isinstance(reaction, types.ReactionCustomEmoji):
        return "🧩"
    if isinstance(reaction, types.ReactionPaid):
        return "⭐"
    return "❔"


def _rpc_reason(err: Exception) -> str:
    return getattr(err, "message", None) or str(err)


# ─────────────────────────────── .seen ────────────────────────────────


@catub.cat_cmd(
    pattern=r"seen$",
    command=("seen", plugin_category),
    info={
        "header": "See who read your message, and when.",
        "description": "Reply to one of your own messages.\n"
        "• Groups: lists every member who read it with the time (Telegram allows this for "
        "groups up to 100 members and messages under 7 days old).\n"
        "• Private chats: shows the exact read time, or just read/unread if they hide it.",
        "usage": "{tr}seen <reply to your message>",
    },
)
async def seen_cmd(event):
    "Read receipts for your message."
    reply = await event.get_reply_message()
    if not reply:
        return await edit_delete(event, "`Reply to one of your messages.`", 6)
    if not reply.out:
        return await edit_delete(event, "`Telegram only shows read receipts for your own messages.`", 6)
    status = await edit_or_reply(event, "`Checking read receipts…`")
    peer = await event.get_input_chat()

    if event.is_private:
        try:
            res = await event.client(functions.messages.GetOutboxReadDateRequest(peer=peer, msg_id=reply.id))
            return await status.edit(
                f"👁 <b>Read</b> {fmt_local(res.date)} ({ago(res.date)})",
                parse_mode="html",
            )
        except RPCError as e:
            reason = _rpc_reason(e)
        dialogs = await event.client(
            functions.messages.GetPeerDialogsRequest(peers=[types.InputDialogPeer(peer)])
        )
        read = dialogs.dialogs and dialogs.dialogs[0].read_outbox_max_id >= reply.id
        if not read:
            return await status.edit("⏳ <b>Not read yet.</b>", parse_mode="html")
        why = {
            "USER_PRIVACY_RESTRICTED": "they hide their read time",
            "YOUR_PRIVACY_RESTRICTED": "you hide your own read time (Settings → Privacy → Last Seen)",
            "MESSAGE_TOO_OLD": "the message is older than 7 days",
        }.get(reason, reason)
        return await status.edit(f"✅ <b>Read</b> — exact time unavailable: {esc(why)}.", parse_mode="html")

    try:
        readers = await event.client(functions.messages.GetMessageReadParticipantsRequest(peer=peer, msg_id=reply.id))
    except RPCError as e:
        reason = _rpc_reason(e)
        hint = {
            "CHAT_TOO_BIG": "this group has more than 100 members",
            "MSG_TOO_OLD": "the message is older than 7 days",
        }.get(reason, reason)
        return await status.edit(f"🙈 Read receipts unavailable: {esc(hint)}.", parse_mode="html")

    if not readers:
        return await status.edit("⏳ <b>Nobody has read it yet.</b>", parse_mode="html")

    users = {}
    try:
        for u in await event.client.get_participants(peer, limit=200):
            users[u.id] = u
    except Exception:
        pass
    readers = sorted(readers, key=lambda r: r.date or now_utc())
    lines = [f"👁 <b>Read by {len(readers)}</b>" + (f" of {len(users) - 1}" if users else "") + "\n"]
    for r in readers[:60]:
        who = mention_html(users.get(r.user_id), f"id {r.user_id}")
        lines.append(f"• {who} — <i>{fmt_local(r.date) if r.date else '?'}</i>")
    if len(readers) > 60:
        lines.append(f"…and {len(readers) - 60} more")
    if users:
        unread = [u for uid, u in users.items() if uid not in {r.user_id for r in readers} and not u.bot and not u.is_self]
        if unread:
            names = ", ".join(mention_html(u) for u in unread[:25])
            more = f" +{len(unread) - 25}" if len(unread) > 25 else ""
            lines.append(f"\n⏳ <b>Not yet:</b> {names}{more}")
    await status.edit("\n".join(lines), parse_mode="html")


# ───────────────────────────── .whoreact ──────────────────────────────


@catub.cat_cmd(
    pattern=r"whoreact$",
    command=("whoreact", plugin_category),
    info={
        "header": "Show who reacted to a message, grouped by reaction.",
        "description": "Works in private chats and groups. In channels and big groups Telegram hides "
        "who reacted, so only the totals are shown.",
        "usage": "{tr}whoreact <reply>",
    },
)
async def whoreact_cmd(event):
    "Reaction breakdown for a message."
    reply = await event.get_reply_message()
    if not reply:
        return await edit_delete(event, "`Reply to a message.`", 6)
    if not reply.reactions or not reply.reactions.results:
        return await edit_delete(event, "`No reactions on that message.`", 6)
    status = await edit_or_reply(event, "`Collecting reactions…`")
    peer = await event.get_input_chat()

    groups = OrderedDict()
    for rc in sorted(reply.reactions.results, key=lambda r: -r.count):
        groups[_reaction_label(rc.reaction)] = {"count": rc.count, "who": []}

    hidden = None
    offset, fetched = None, 0
    try:
        while fetched < 500:
            res = await event.client(
                functions.messages.GetMessageReactionsListRequest(peer=peer, id=reply.id, limit=100, offset=offset)
            )
            ents = {u.id: u for u in res.users}
            ents.update({c.id: c for c in res.chats})
            for pr in res.reactions:
                label = _reaction_label(pr.reaction)
                pid = getattr(pr.peer_id, "user_id", None) or getattr(pr.peer_id, "channel_id", None) or getattr(pr.peer_id, "chat_id", None)
                groups.setdefault(label, {"count": 0, "who": []})["who"].append(ents.get(pid))
            fetched += len(res.reactions)
            offset = res.next_offset
            if not offset or not res.reactions:
                break
    except RPCError as e:
        hidden = _rpc_reason(e)

    total = sum(g["count"] for g in groups.values())
    lines = [f"💬 <b>{total} reaction{'s' if total != 1 else ''}</b>\n"]
    for label, g in groups.items():
        names = ", ".join(mention_html(w) for w in g["who"][:30] if w is not None)
        extra = g["count"] - min(len(g["who"]), 30)
        tail = f" +{extra}" if names and extra > 0 else ""
        lines.append(f"{label} <b>{g['count']}</b>" + (f" — {names}{tail}" if names else ""))
    if hidden:
        lines.append(f"\n<i>Telegram hides who reacted here ({esc(hidden)}).</i>")
    await status.edit("\n".join(lines), parse_mode="html")


# ────────────────────────────── .online ───────────────────────────────


def _status_rank(user):
    st = user.status
    if isinstance(st, types.UserStatusOnline):
        return 0, None
    if isinstance(st, types.UserStatusOffline) and st.was_online:
        if now_utc() - st.was_online <= timedelta(minutes=15):
            return 1, st.was_online
        return 3, st.was_online
    if isinstance(st, types.UserStatusRecently):
        return 2, None
    return 4, None


def _last_seen_text(user) -> str:
    st = user.status
    if isinstance(st, types.UserStatusOnline):
        return "🟢 online now"
    if isinstance(st, types.UserStatusOffline):
        return f"⚪ last seen {fmt_local(st.was_online)} ({ago(st.was_online)})"
    if isinstance(st, types.UserStatusRecently):
        return "🟡 last seen recently (exact time hidden)"
    if isinstance(st, types.UserStatusLastWeek):
        return "🟠 last seen within a week"
    if isinstance(st, types.UserStatusLastMonth):
        return "🔴 last seen within a month"
    return "⚫ last seen a long time ago / hidden"


@catub.cat_cmd(
    pattern=r"online(?:\s+(.+))?$",
    command=("online", plugin_category),
    info={
        "header": "Who's online right now?",
        "description": "In a group: lists members online now and those active in the last 15 minutes.\n"
        "With a user (reply / @username / in a PM): shows their last seen.",
        "usage": ["{tr}online", "{tr}online <@user / reply>", "{tr}online 2000  (scan up to N members)"],
    },
)
async def online_cmd(event):
    "Online members / last seen."
    arg = (event.pattern_match.group(1) or "").strip()
    reply = await event.get_reply_message()

    target = None
    if reply and reply.sender_id and not event.is_private:
        target = await reply.get_sender()
    elif arg and not arg.isdigit():
        target = await resolve_chat(event.client, arg)
    elif event.is_private:
        target = await event.get_chat()
    if target is not None:
        if not isinstance(target, types.User):
            return await edit_delete(event, "`That's not a user.`", 6)
        full = await event.client.get_entity(target.id)
        return await edit_or_reply(event, f"{mention_html(full)}\n{_last_seen_text(full)}", parse_mode="html")

    limit = min(int(arg), 10000) if arg.isdigit() else 3000
    status = await edit_or_reply(event, "`Scanning members…`")
    buckets = {0: [], 1: [], 2: []}
    scanned = 0
    try:
        async for u in event.client.iter_participants(event.chat_id, limit=limit):
            scanned += 1
            if u.bot or u.deleted or u.is_self:
                continue
            rank, when = _status_rank(u)
            if rank in buckets:
                buckets[rank].append((u, when))
    except RPCError as e:
        return await status.edit(f"Couldn't list members: {esc(_rpc_reason(e))}", parse_mode="html")

    lines = [f"📡 <b>Presence</b> — scanned {scanned} members\n"]
    lines.append(f"🟢 <b>Online now ({len(buckets[0])})</b>")
    lines += [f"• {mention_html(u)}" for u, _ in buckets[0][:40]] or ["<i>nobody</i>"]
    if buckets[1]:
        lines.append(f"\n🟡 <b>Active in the last 15 min ({len(buckets[1])})</b>")
        for u, when in sorted(buckets[1], key=lambda x: x[1], reverse=True)[:25]:
            lines.append(f"• {mention_html(u)} — {ago(when)}")
    lines.append(f"\n🫥 Hidden \"recently\": {len(buckets[2])}")
    await status.edit("\n".join(lines), parse_mode="html")


# ─────────────────────────────── .peek ────────────────────────────────


@catub.cat_cmd(
    pattern=r"peek(?:\s+([\s\S]+))?$",
    command=("peek", plugin_category),
    info={
        "header": "Read chats without sending read receipts (ghost read).",
        "description": "Without arguments, lists your unread chats as a numbered inbox. Then peek one by "
        "number, @username, id or part of its name. The messages stay unread: no blue ticks for the sender.\n"
        "Tip: use it in Saved Messages.",
        "usage": ["{tr}peek", "{tr}peek <n | @user | name> [count]"],
        "examples": ["{tr}peek", "{tr}peek 2", "{tr}peek @durov 30", "{tr}peek mom 15"],
    },
)
async def peek_cmd(event):
    "Silent reading."
    global _LAST_INBOX
    arg = (event.pattern_match.group(1) or "").strip()

    if not arg:
        status = await edit_or_reply(event, "`Fetching unread chats…`")
        inbox = []
        async for d in event.client.iter_dialogs(limit=200):
            if d.unread_count and not d.archived:
                inbox.append(d)
            if len(inbox) >= 25:
                break
        if not inbox:
            return await status.edit("📭 <b>Inbox zero.</b> Nothing unread.", parse_mode="html")
        _LAST_INBOX = [d.entity for d in inbox]
        lines = ["📬 <b>Unread chats</b> — <code>.peek &lt;n&gt;</code> to read silently\n"]
        for i, d in enumerate(inbox, 1):
            ment = f" · @{d.unread_mentions_count}" if d.unread_mentions_count else ""
            muted = " 🔕" if d.dialog.notify_settings and d.dialog.notify_settings.mute_until else ""
            lines.append(f"<code>{i:>2}</code> {esc(d.name)} — <b>{d.unread_count}</b>{ment}{muted}")
        return await status.edit("\n".join(lines), parse_mode="html")

    parts = arg.rsplit(None, 1)
    count = None
    if len(parts) == 2 and parts[1].isdigit() and int(parts[1]) <= 100:
        arg, count = parts[0], int(parts[1])

    status = await edit_or_reply(event, "`Peeking…`")
    if arg.isdigit() and 1 <= int(arg) <= len(_LAST_INBOX):
        chat = _LAST_INBOX[int(arg) - 1]
    else:
        chat = await resolve_chat(event.client, arg)
    if chat is None:
        return await status.edit("Couldn't find that chat. Run <code>.peek</code> for your inbox.", parse_mode="html")

    unread, read_upto = 0, None
    try:
        dlg = await event.client(
            functions.messages.GetPeerDialogsRequest(
                peers=[types.InputDialogPeer(await event.client.get_input_entity(chat))]
            )
        )
        if dlg.dialogs:
            unread = dlg.dialogs[0].unread_count
            read_upto = dlg.dialogs[0].read_inbox_max_id
    except Exception:
        pass
    count = count or max(5, min(unread or 10, 40))

    msgs = await event.client.get_messages(chat, limit=count)
    if not msgs:
        return await status.edit("Empty chat.", parse_mode="html")
    is_group = not isinstance(chat, types.User)
    lines = [f"👻 <b>{esc(name_of(chat))}</b> — last {len(msgs)} · {unread} unread (still unread)\n"]
    for m in reversed(msgs):
        who = ""
        if is_group or m.out:
            sender = "You" if m.out else name_of(m.sender, "?")
            who = f"<b>{esc(sender)}:</b> "
        mark = "🔵 " if not m.out and read_upto is not None and m.id > read_upto else ""
        lines.append(f"<code>{fmt_local(m.date, with_date=False)}</code> {mark}{who}{esc(describe(m, 280))}")
    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:3990] + "…"
    await status.edit(text, parse_mode="html")
