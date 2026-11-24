# Declutter — find the dead weight in your chat list and tidy it (reversibly).
#
#   .declutter            scan: channels you never read, dead groups, deleted accounts, old bots
#   .declutter archive    move everything flagged to the Archive folder (undo: unarchive in the app)
#   .declutter read       mark everything flagged as read
#
# Nothing is ever left, deleted or blocked.

import asyncio
from datetime import timedelta

from telethon.errors import FloodWaitError, RPCError
from telethon.tl import types

from userbot import catub

from ..Config import Config
from ..core.managers import edit_or_reply
from ..helpers.functions.kittychat import esc
from ..helpers.functions.kittytime import now_utc

plugin_category = "utils"

UNREAD_CHANNEL = 100  # a channel with this many unread posts = you don't read it
DEAD_GROUP_DAYS = 90
OLD_BOT_DAYS = 180
_last = {}

CATEGORIES = [
    ("channels", "📢 Channels you never read", f"{UNREAD_CHANNEL}+ unread posts"),
    ("groups", "🪦 Dead groups", f"no messages for {DEAD_GROUP_DAYS}+ days"),
    ("deleted", "👻 Deleted accounts", "chats with deleted users"),
    ("bots", "🤖 Bots you stopped using", f"untouched for {OLD_BOT_DAYS}+ days"),
]


async def _scan(client):
    now = now_utc()
    found = {k: [] for k, *_ in CATEGORIES}
    total = 0
    async for d in client.iter_dialogs(archived=False):
        total += 1
        if d.pinned or d.dialog.folder_id:
            continue
        e, last = d.entity, d.date
        age = (now - last).days if last else 9999
        if isinstance(e, types.Channel) and e.broadcast:
            if d.unread_count >= UNREAD_CHANNEL:
                found["channels"].append((d, f"{d.unread_count} unread"))
        elif isinstance(e, types.Chat) or (isinstance(e, types.Channel) and e.megagroup):
            if age >= DEAD_GROUP_DAYS:
                found["groups"].append((d, f"quiet {age}d"))
        elif isinstance(e, types.User):
            if e.deleted:
                found["deleted"].append((d, ""))
            elif e.bot and age >= OLD_BOT_DAYS:
                found["bots"].append((d, f"{age}d ago"))
    return found, total


def _report(found, total) -> str:
    lines = [f"🧹 <b>Declutter report</b> — {total} chats scanned\n"]
    flagged = 0
    for key, title, why in CATEGORIES:
        items = found[key]
        flagged += len(items)
        lines.append(f"{title}: <b>{len(items)}</b> <i>({why})</i>")
        for d, info in sorted(items, key=lambda x: x[0].date or now_utc() - timedelta(days=99999))[:6]:
            lines.append(f"   • {esc(d.name or 'Deleted Account')}{' — ' + info if info else ''}")
        if len(items) > 6:
            lines.append(f"   …and {len(items) - 6} more")
    if flagged:
        p = Config.COMMAND_HAND_LER
        lines.append(
            f"\n<code>{p}declutter archive</code> → move all {flagged} to Archive (reversible)\n"
            f"<code>{p}declutter read</code> → mark them all as read"
        )
    else:
        lines.append("\n✨ Your chat list is already clean.")
    return "\n".join(lines)


@catub.cat_cmd(
    pattern=r"declutter(?:\s+(archive|read))?$",
    command=("declutter", plugin_category),
    info={
        "header": "Find and tidy dead chats: unread channels, dead groups, deleted accounts, old bots.",
        "description": "Scan first, then archive or mark-as-read everything flagged. Pinned and already "
        "archived chats are skipped. Nothing is ever left or deleted, and archiving can be undone.",
        "usage": ["{tr}declutter", "{tr}declutter archive", "{tr}declutter read"],
    },
)
async def declutter_cmd(event):
    "Declutter chat list."
    action = event.pattern_match.group(1)
    status = await edit_or_reply(event, "`Scanning your chats…`")
    found, total = await _scan(event.client)
    _last.update(found=found, total=total)
    if not action:
        return await status.edit(_report(found, total), parse_mode="html")

    items = [d for key, *_ in CATEGORIES for d, _ in found[key]]
    if not items:
        return await status.edit("✨ Nothing flagged, nothing to do.")
    done = failed = 0
    for i, d in enumerate(items, 1):
        try:
            if action == "archive":
                await event.client.edit_folder(d.entity, 1)
            else:
                await event.client.send_read_acknowledge(d.entity, clear_mentions=True)
            done += 1
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds + 1)
            failed += 1
        except RPCError:
            failed += 1
        if i % 20 == 0:
            await status.edit(f"`{action.title()}… {i}/{len(items)}`")
            await asyncio.sleep(1)
    verb = "Archived" if action == "archive" else "Marked as read"
    extra = f" ({failed} failed)" if failed else ""
    await status.edit(f"🧹 {verb} <b>{done}</b> chats{extra}.", parse_mode="html")
