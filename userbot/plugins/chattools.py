# Chat power tools.
#
#   .snooze 2h | tomorrow 8am | forever | off     mute this chat for a while
#   .find <words> [-n 30]                         search all your chats at once
#   .export [n] [txt]                             export this chat to a pretty HTML file

import io
import os
import tempfile
from datetime import datetime, timezone

from telethon.errors import RPCError
from telethon.tl import functions, types

from userbot import catub

from ..Config import Config
from ..core.managers import edit_delete, edit_or_reply
from ..helpers.functions.kittychat import describe, esc, media_kind, message_link, name_of, resolve_chat
from ..helpers.functions.kittytime import fmt_local, human_delta, now_utc, split_when, to_local

plugin_category = "utils"

FOREVER = datetime(2038, 1, 1, tzinfo=timezone.utc)


# ────────────────────────────── .snooze ───────────────────────────────


@catub.cat_cmd(
    pattern=r"snooze(?:\s+([\s\S]+))?$",
    command=("snooze", plugin_category),
    info={
        "header": "Mute a noisy chat until a given time.",
        "description": "Notifications come back automatically when the time is up. Telegram does that "
        "server-side, so it works even if the bot restarts.",
        "usage": ["{tr}snooze <2h | 30m | 18:00 | tomorrow 8am | forever>", "{tr}snooze off", "{tr}snooze 3h @chat"],
        "examples": ["{tr}snooze 2h", "{tr}snooze tomorrow 7am", "{tr}snooze off"],
    },
)
async def snooze_cmd(event):
    "Mute this chat for a while."
    raw = (event.pattern_match.group(1) or "").strip()
    if not raw:
        return await edit_delete(event, f"`Usage: {Config.COMMAND_HAND_LER}snooze 2h | forever | off`", 6)

    chat = None
    words = raw.split()
    if len(words) > 1 and (words[-1].startswith("@") or words[-1].lstrip("-").isdigit() and len(words[-1]) > 5):
        chat = await resolve_chat(event.client, words[-1])
        raw = " ".join(words[:-1])
    chat = chat or await event.get_chat()

    low = raw.lower()
    if low in ("off", "unmute", "wake"):
        until = datetime(1970, 1, 1, tzinfo=timezone.utc)
    elif low in ("forever", "always", "inf"):
        until = FOREVER
    else:
        until, rest = split_when(raw)
        if until is None or rest:
            return await edit_delete(event, "`Couldn't read that time. Try 2h, 45m, 18:00, tomorrow 8am.`", 6)

    peer = types.InputNotifyPeer(peer=await event.client.get_input_entity(chat))
    try:
        await event.client(
            functions.account.UpdateNotifySettingsRequest(
                peer=peer, settings=types.InputPeerNotifySettings(mute_until=until)
            )
        )
    except RPCError as e:
        return await edit_delete(event, f"Couldn't change notifications: `{e}`", 8)

    title = name_of(chat, "this chat")
    if until.year == 1970:
        msg = f"🔔 **{title}** notifications are back on."
    elif until is FOREVER:
        msg = f"🔕 **{title}** muted forever."
    else:
        msg = f"😴 **{title}** snoozed until **{fmt_local(until)}** ({human_delta(until - now_utc())})."
    await edit_delete(event, msg, 8)


# ─────────────────────────────── .find ────────────────────────────────


@catub.cat_cmd(
    pattern=r"find(?:\s+([\s\S]+))?$",
    command=("find", plugin_category),
    info={
        "header": "Search for words across all your chats at once.",
        "description": "Uses Telegram's global search, the same as the search bar, but the results "
        "come back as a list with links you can tap.",
        "flags": {"-n <num>": "number of results (default 25, max 100)"},
        "usage": "{tr}find <words> [-n 50]",
        "examples": ["{tr}find meeting link", "{tr}find invoice -n 50"],
    },
)
async def find_cmd(event):
    "Global search."
    raw = (event.pattern_match.group(1) or "").strip()
    limit = 25
    words = raw.split()
    if "-n" in words:
        i = words.index("-n")
        if i + 1 < len(words) and words[i + 1].isdigit():
            limit = max(1, min(int(words[i + 1]), 100))
            del words[i : i + 2]
    query = " ".join(words)
    if not query:
        return await edit_delete(event, "`What should I search for?`", 6)

    status = await edit_or_reply(event, f"`Searching all chats for “{query}”…`")
    results = []
    try:
        async for m in event.client.iter_messages(None, search=query, limit=limit):
            results.append(m)
    except RPCError as e:
        return await status.edit(f"Search failed: <code>{esc(e)}</code>", parse_mode="html")
    if not results:
        return await status.edit(f"🔍 Nothing found for <b>{esc(query)}</b>.", parse_mode="html")

    lines = [f"🔍 <b>{len(results)} results</b> for “{esc(query)}”\n"]
    for m in results:
        chat = m.chat
        link = message_link(chat, m.id)
        who = "You" if m.out else name_of(m.sender, "")
        title = esc(name_of(chat))
        title = f'<a href="{link}">{title}</a>' if link else f"<b>{title}</b>"
        snippet = esc(describe(m, 110))
        sender = f"{esc(who)}: " if who and not isinstance(chat, types.User) else ""
        lines.append(f"• {title} · <i>{fmt_local(m.date)}</i>\n   {sender}{snippet}")
    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:3990].rsplit("\n•", 1)[0] + "\n…"
    await status.edit(text, parse_mode="html", link_preview=False)


# ────────────────────────────── .export ───────────────────────────────

_HTML_HEAD = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>
:root{{--bg:#0e1621;--card:#182533;--me:#2b5278;--txt:#e9eef3;--dim:#7f91a4;--acc:#64b5ef}}
@media (prefers-color-scheme:light){{:root{{--bg:#e6ebee;--card:#fff;--me:#effdde;--txt:#000;--dim:#6d7f8f;--acc:#168acd}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--txt);font:15px/1.45 -apple-system,Segoe UI,Roboto,sans-serif}}
header{{position:sticky;top:0;background:var(--card);padding:14px 18px;box-shadow:0 1px 4px #0004;z-index:2}}
header h1{{margin:0;font-size:18px}}header p{{margin:2px 0 0;color:var(--dim);font-size:13px}}
main{{max-width:760px;margin:0 auto;padding:12px}}
.day{{text-align:center;margin:16px 0 8px}}.day span{{background:#0006;color:#fff;padding:3px 10px;border-radius:12px;font-size:13px}}
.m{{display:flex;margin:3px 0}}.m.out{{justify-content:flex-end}}
.b{{max-width:78%;background:var(--card);padding:6px 10px 4px;border-radius:12px;white-space:pre-wrap;word-wrap:break-word}}
.out .b{{background:var(--me)}}.n{{color:var(--acc);font-weight:600;font-size:13px}}
.t{{color:var(--dim);font-size:11px;text-align:right;margin-top:2px}}.md{{color:var(--dim);font-style:italic}}
.r{{border-left:2px solid var(--acc);padding-left:6px;color:var(--dim);font-size:13px;margin-bottom:3px}}
.sv{{text-align:center;color:var(--dim);font-size:13px;margin:6px 0}}
</style></head><body><header><h1>{title}</h1><p>{sub}</p></header><main>
"""


def _render_html(chat, msgs, by_id) -> str:
    title = esc(name_of(chat, "Chat"))
    first, last = to_local(msgs[0].date), to_local(msgs[-1].date)
    sub = f"{len(msgs)} messages · {first:%d %b %Y} – {last:%d %b %Y} · exported {to_local(now_utc()):%d %b %Y %H:%M}"
    out = io.StringIO()
    out.write(_HTML_HEAD.format(title=title, sub=sub))
    day = None
    for m in msgs:
        d = to_local(m.date)
        if d.date() != day:
            day = d.date()
            out.write(f'<div class="day"><span>{d:%A, %d %B %Y}</span></div>')
        if isinstance(m, types.MessageService) or getattr(m, "action", None):
            out.write(f'<div class="sv">{esc(describe(m))}</div>')
            continue
        cls = "m out" if m.out else "m"
        name = "" if m.out or isinstance(chat, types.User) else f'<div class="n">{esc(name_of(m.sender, "?"))}</div>'
        quote = ""
        if m.reply_to and m.reply_to.reply_to_msg_id in by_id:
            q = by_id[m.reply_to.reply_to_msg_id]
            quote = f'<div class="r">{esc(name_of(q.sender, "?") if not q.out else "You")}: {esc(describe(q, 90))}</div>'
        kind = media_kind(m)
        media = f'<div class="md">[{esc(describe(m, 120).split(" · ")[0])}]</div>' if kind and kind != "link" else ""
        body = esc(m.message or "")
        edited = " · edited" if m.edit_date else ""
        out.write(
            f'<div class="{cls}"><div class="b">{name}{quote}{media}{body}'
            f'<div class="t">{d:%H:%M}{edited}</div></div></div>'
        )
    out.write("</main></body></html>")
    return out.getvalue()


@catub.cat_cmd(
    pattern=r"export(?:\s+([\s\S]+))?$",
    command=("export", plugin_category),
    info={
        "header": "Export this chat to a file.",
        "description": "Builds a self-contained HTML page styled like Telegram (dark/light) with "
        "date separators, replies and media placeholders. Add 'txt' for plain text. "
        "The file is sent to your Saved Messages.",
        "usage": ["{tr}export [count]", "{tr}export [count] txt"],
        "examples": ["{tr}export", "{tr}export 5000", "{tr}export 300 txt"],
    },
)
async def export_cmd(event):
    "Export chat history."
    args = (event.pattern_match.group(1) or "").lower().split()
    as_txt = "txt" in args
    count = next((int(a) for a in args if a.isdigit()), 1000)
    count = max(10, min(count, 20000))
    chat = await event.get_chat()

    status = await edit_or_reply(event, f"`Exporting up to {count} messages…`")
    msgs = []
    async for m in event.client.iter_messages(chat, limit=count):
        if m.id != event.id:
            msgs.append(m)
    if not msgs:
        return await status.edit("Nothing to export.")
    msgs.reverse()
    by_id = {m.id: m for m in msgs}
    safe = "".join(c for c in name_of(chat, "chat") if c.isalnum() or c in " -_").strip()[:40] or "chat"

    tmp = tempfile.mkdtemp(dir=Config.TMP_DOWNLOAD_DIRECTORY)
    path = os.path.join(tmp, f"{safe} {to_local(now_utc()):%Y-%m-%d}.{'txt' if as_txt else 'html'}")
    if as_txt:
        with open(path, "w", encoding="utf-8") as f:
            for m in msgs:
                who = "You" if m.out else name_of(m.sender, "?")
                f.write(f"[{to_local(m.date):%Y-%m-%d %H:%M}] {who}: {describe(m, 100000)}\n")
    else:
        with open(path, "w", encoding="utf-8") as f:
            f.write(_render_html(chat, msgs, by_id))

    try:
        await event.client.send_file(
            "me",
            path,
            caption=f"📦 Export of **{name_of(chat)}** — {len(msgs)} messages",
            force_document=True,
        )
    finally:
        try:
            os.remove(path)
            os.rmdir(tmp)
        except OSError:
            pass
    await edit_delete(status, "📦 Export sent to your Saved Messages.", 6)
