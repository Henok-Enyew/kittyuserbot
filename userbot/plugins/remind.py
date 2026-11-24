# Reminders that survive restarts.
#
# Each reminder is a Telegram *scheduled message* in your Saved Messages, so
# Telegram's servers deliver it (with a notification) even if the bot is down
# or the Hugging Face container restarted. No database, no scheduler thread.
#
#   .remind 10m stretch            .remind 18:30 call mom       .remind tomorrow 9am standup
#   .remind 2h  (reply)            -> reminds you about the replied message, with a link
#   .reminders                     .unremind 2 | all

from datetime import timedelta

from telethon.errors import RPCError
from telethon.tl import functions, types

from userbot import catub

from ..Config import Config
from ..core.managers import edit_delete, edit_or_reply
from ..helpers.functions.kittychat import describe, esc, message_link, name_of
from ..helpers.functions.kittytime import fmt_local, human_delta, now_utc, split_when

plugin_category = "utils"
MARK = "⏰"


async def _scheduled(client):
    res = await client(functions.messages.GetScheduledHistoryRequest(peer=types.InputPeerSelf(), hash=0))
    msgs = [m for m in getattr(res, "messages", []) if (m.message or "").startswith(MARK)]
    return sorted(msgs, key=lambda m: m.date)


@catub.cat_cmd(
    pattern=r"remind(?:\s+([\s\S]+))?$",
    command=("remind", plugin_category),
    info={
        "header": "Set a reminder. Telegram delivers it to your Saved Messages, even if the bot is offline.",
        "description": "Time formats: 10m, 1h30m, 2d, 18:30, 6pm, 'tomorrow 9am'. Times are Addis Ababa time. "
        "Reply to a message to be reminded about it (with a link back to it).",
        "usage": ["{tr}remind <when> <text>", "{tr}remind <when>  (reply)"],
        "examples": [
            "{tr}remind 25m take the pizza out",
            "{tr}remind 18:30 call mom",
            "{tr}remind tomorrow 8am gym 💪",
            "{tr}remind 3h  (reply to a message)",
        ],
    },
)
async def remind_cmd(event):
    "Set a reminder."
    raw = (event.pattern_match.group(1) or "").strip()
    when, text = split_when(raw)
    if when is None:
        return await edit_delete(
            event,
            f"`Couldn't read the time. Try {Config.COMMAND_HAND_LER}remind 30m text, 18:30 text or tomorrow 9am text`",
            10,
        )
    delta = when - now_utc()
    if delta < timedelta(seconds=30):
        return await edit_delete(event, "`Pick a time at least 30 seconds from now.`", 6)
    if delta > timedelta(days=365):
        return await edit_delete(event, "`Telegram schedules up to 365 days ahead.`", 6)

    reply = await event.get_reply_message()
    if not text and not reply:
        return await edit_delete(event, "`What should I remind you about?`", 6)

    body = f"{MARK} <b>Reminder</b>\n{esc(text)}" if text else f"{MARK} <b>Reminder</b>"
    if reply:
        chat = await event.get_chat()
        link = message_link(chat, reply.id)
        sender = "you" if reply.out else name_of(await reply.get_sender(), "someone")
        where = f'<a href="{link}">open message</a>' if link else f"in {esc(name_of(chat))}"
        body += f"\n\n↪️ <i>{esc(sender)}: {esc(describe(reply, 200))}</i>\n{where}"
    elif not event.is_private or (await event.get_chat()).id != (await event.client.get_me()).id:
        body += f"\n\n<i>set in {esc(name_of(await event.get_chat()))}</i>"

    try:
        await event.client.send_message("me", body, parse_mode="html", schedule=when, link_preview=False)
    except RPCError as e:
        return await edit_delete(event, f"Couldn't schedule: `{e}`", 8)
    await edit_delete(event, f"⏰ Got it, I'll remind you **{fmt_local(when)}** (in {human_delta(delta)}).", 8)


@catub.cat_cmd(
    pattern=r"reminders$",
    command=("reminders", plugin_category),
    info={"header": "List pending reminders.", "usage": "{tr}reminders"},
)
async def reminders_cmd(event):
    "List reminders."
    msgs = await _scheduled(event.client)
    if not msgs:
        return await edit_delete(event, f"No reminders. Set one with `{Config.COMMAND_HAND_LER}remind 1h text`.", 8)
    lines = ["⏰ <b>Pending reminders</b>\n"]
    for i, m in enumerate(msgs, 1):
        preview = (m.message or "").replace(MARK, "", 1).replace("Reminder", "", 1).strip().split("\n")
        preview = next((p for p in preview if p.strip()), "(replied message)")
        lines.append(f"<code>{i}</code> <b>{fmt_local(m.date)}</b> — {esc(preview[:70])}")
    lines.append(f"\n<code>{Config.COMMAND_HAND_LER}unremind &lt;n|all&gt;</code> to cancel")
    await edit_or_reply(event, "\n".join(lines), parse_mode="html")


@catub.cat_cmd(
    pattern=r"unremind(?:\s+(\S+))?$",
    command=("unremind", plugin_category),
    info={"header": "Cancel a reminder.", "usage": ["{tr}unremind <n>", "{tr}unremind all"]},
)
async def unremind_cmd(event):
    "Cancel reminders."
    arg = (event.pattern_match.group(1) or "").lower()
    msgs = await _scheduled(event.client)
    if arg == "all":
        ids = [m.id for m in msgs]
    elif arg.isdigit() and 1 <= int(arg) <= len(msgs):
        ids = [msgs[int(arg) - 1].id]
    else:
        return await edit_delete(event, f"`Give a number from {Config.COMMAND_HAND_LER}reminders, or all.`", 6)
    if not ids:
        return await edit_delete(event, "Nothing to cancel.", 5)
    await event.client(functions.messages.DeleteScheduledMessagesRequest(peer=types.InputPeerSelf(), id=ids))
    await edit_delete(event, f"🗑 Cancelled {len(ids)} reminder{'s' if len(ids) != 1 else ''}.", 6)
