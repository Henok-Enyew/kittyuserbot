# Stories — download anyone's stories, inspect your own viewers, post new ones.
#
#   .stories [@user|reply] [-p]   download active (or -p pinned/profile) stories
#   .mystories [n]                your active stories with views; n = full viewer list
#   .poststory [text] [-c|-cf]    post replied photo/video, or a generated text story

import os
import random
import shutil
import tempfile

from telethon.errors import RPCError
from telethon.tl import functions, types

from userbot import catub

from ..Config import Config
from ..core.managers import edit_delete, edit_or_reply
from ..helpers.functions.kittycard import STORY_THEMES, text_story_image
from ..helpers.functions.kittychat import esc, mention_html, name_of, resolve_chat
from ..helpers.functions.kittytime import ago, fmt_local

plugin_category = "utils"


def _reaction(r) -> str:
    if isinstance(r, types.ReactionEmoji):
        return r.emoticon
    if isinstance(r, types.ReactionCustomEmoji):
        return "🧩"
    return ""


async def _full_items(client, peer, items):
    """Replace StoryItemSkipped (no media) with full StoryItems, drop deleted."""
    skipped = [s.id for s in items if isinstance(s, types.StoryItemSkipped)]
    full = {s.id: s for s in items if isinstance(s, types.StoryItem)}
    if skipped:
        res = await client(functions.stories.GetStoriesByIDRequest(peer=peer, id=skipped))
        full.update({s.id: s for s in res.stories if isinstance(s, types.StoryItem)})
    return [full[i] for i in sorted(full)]


# ────────────────────────────── .stories ──────────────────────────────


@catub.cat_cmd(
    pattern=r"stories(?:\s+([\s\S]+))?$",
    command=("stories", plugin_category),
    info={
        "header": "Download someone's stories.",
        "description": "Fetches the user's (or channel's) active stories and sends the photos/videos here. "
        "The bot never calls Telegram's 'mark story as viewed' API, so you don't show up in their viewer list.",
        "flags": {"-p": "profile (pinned) stories instead of the last 24h"},
        "usage": ["{tr}stories <@user / id / reply>", "{tr}stories <@user> -p"],
        "examples": ["{tr}stories @telegram", "{tr}stories -p  (in reply)"],
    },
)
async def stories_cmd(event):
    "Download stories."
    arg = (event.pattern_match.group(1) or "").strip()
    pinned = False
    if "-p" in arg.split():
        pinned = True
        arg = " ".join(w for w in arg.split() if w != "-p")

    reply = await event.get_reply_message()
    if arg:
        target = await resolve_chat(event.client, arg)
    elif reply and reply.sender_id:
        target = await reply.get_sender()
    elif event.is_private:
        target = await event.get_chat()
    else:
        return await edit_delete(event, "`Give a @username, id or reply to someone.`", 6)
    if target is None:
        return await edit_delete(event, "`Couldn't find that user/channel.`", 6)

    status = await edit_or_reply(event, f"`Looking for {'profile ' if pinned else ''}stories…`")
    peer = await event.client.get_input_entity(target)
    try:
        if pinned:
            res = await event.client(functions.stories.GetPinnedStoriesRequest(peer=peer, offset_id=0, limit=30))
            items = res.stories
        else:
            res = await event.client(functions.stories.GetPeerStoriesRequest(peer=peer))
            items = res.stories.stories
        items = await _full_items(event.client, peer, items)
    except RPCError as e:
        return await status.edit(f"Telegram refused: <code>{esc(e)}</code>", parse_mode="html")

    who = name_of(target)
    if not items:
        kind = "profile stories" if pinned else "active stories (last 24h)"
        tip = "" if pinned else f" Try <code>{Config.COMMAND_HAND_LER}stories … -p</code> for profile stories."
        return await status.edit(f"📭 {esc(who)} has no {kind}.{tip}", parse_mode="html")

    await status.edit(f"`Downloading {len(items)} stor{'y' if len(items) == 1 else 'ies'}…`")
    tmp = tempfile.mkdtemp(dir=Config.TMP_DOWNLOAD_DIRECTORY)
    files, captions = [], []
    try:
        for i, s in enumerate(items, 1):
            if s.media is None:
                continue
            path = await event.client.download_media(s.media, file=os.path.join(tmp, f"{s.id}"))
            if not path:
                continue
            views = f" · 👁 {s.views.views_count}" if s.views and s.views.views_count is not None else ""
            cap = f"📖 {who} · {i}/{len(items)} · {fmt_local(s.date)} ({ago(s.date)}){views}"
            if s.caption:
                cap += f"\n\n{s.caption}"
            files.append(path)
            captions.append(cap[:1000])

        if not files:
            return await status.edit("No downloadable media in those stories.")
        for start in range(0, len(files), 10):
            chunk, caps = files[start : start + 10], captions[start : start + 10]
            await event.client.send_file(
                event.chat_id,
                chunk if len(chunk) > 1 else chunk[0],
                caption=caps if len(caps) > 1 else caps[0],
                reply_to=event.reply_to_msg_id,
                parse_mode=None,
                supports_streaming=True,
            )
        await status.delete()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ───────────────────────────── .mystories ─────────────────────────────


@catub.cat_cmd(
    pattern=r"mystories(?:\s+(\d+))?$",
    command=("mystories", plugin_category),
    info={
        "header": "Your active stories, views and who watched.",
        "usage": ["{tr}mystories", "{tr}mystories <n>  (full viewer list of story n)"],
    },
)
async def mystories_cmd(event):
    "Your story stats."
    pick = event.pattern_match.group(1)
    status = await edit_or_reply(event, "`Fetching your stories…`")
    me = types.InputPeerSelf()
    try:
        res = await event.client(functions.stories.GetPeerStoriesRequest(peer=me))
        items = await _full_items(event.client, me, res.stories.stories)
    except RPCError as e:
        return await status.edit(f"Telegram refused: <code>{esc(e)}</code>", parse_mode="html")
    if not items:
        return await status.edit(
            f"📭 No active stories. Post one with <code>{Config.COMMAND_HAND_LER}poststory</code>.",
            parse_mode="html",
        )

    if pick:
        idx = int(pick)
        if not 1 <= idx <= len(items):
            return await status.edit(f"Pick 1–{len(items)}.")
        story = items[idx - 1]
        try:
            views = await event.client(
                functions.stories.GetStoryViewsListRequest(peer=me, id=story.id, offset="", limit=100)
            )
        except RPCError as e:
            return await status.edit(f"Couldn't load viewers: <code>{esc(e)}</code>", parse_mode="html")
        users = {u.id: u for u in views.users}
        lines = [
            f"📖 <b>Story {idx}</b> · posted {fmt_local(story.date)}\n"
            f"👁 {views.views_count} views · ❤️ {views.reactions_count} reactions · ↗️ {views.forwards_count} shares\n"
        ]
        for v in views.views:
            if isinstance(v, types.StoryView):
                react = f" {_reaction(v.reaction)}" if v.reaction else ""
                lines.append(f"• {mention_html(users.get(v.user_id), str(v.user_id))}{react} — <i>{ago(v.date)}</i>")
        if views.views_count > len(views.views):
            lines.append(f"…and {views.views_count - len(views.views)} more")
        return await status.edit("\n".join(lines)[:4090], parse_mode="html")

    total_views = 0
    lines = ["📚 <b>Your active stories</b>\n"]
    for i, s in enumerate(items, 1):
        v = s.views
        views = v.views_count if v else 0
        total_views += views or 0
        reacts = v.reactions_count if v and v.reactions_count else 0
        privacy = "🌍"
        if s.close_friends:
            privacy = "💚"
        elif s.contacts:
            privacy = "👥"
        elif s.selected_contacts:
            privacy = "🎯"
        kind = "🎬" if isinstance(s.media, types.MessageMediaDocument) else "🖼"
        expires = f"expires {fmt_local(s.expire_date, with_date=False)}" if s.expire_date else ""
        cap = f" — {esc(s.caption[:40])}" if s.caption else ""
        lines.append(f"<code>{i}</code> {kind}{privacy} 👁 <b>{views}</b> ❤️ {reacts} · {expires}{cap}")
    lines.append(f"\nTotal views: <b>{total_views}</b> · <code>{Config.COMMAND_HAND_LER}mystories 1</code> for viewers")
    await status.edit("\n".join(lines), parse_mode="html")


# ───────────────────────────── .poststory ─────────────────────────────


@catub.cat_cmd(
    pattern=r"poststory(?:\s+([\s\S]+))?$",
    command=("poststory", plugin_category),
    info={
        "header": "Post a story from the bot.",
        "description": "Reply to a photo/video (video ≤ 60s) to post it as a story, with optional caption.\n"
        "Without a reply, the text is rendered as a colourful text story.\n"
        "Free accounts get a few stories per day and 24h duration only.",
        "flags": {
            "-c": "contacts only",
            "-cf": "close friends only",
            "-t<n>": f"text story colour theme 1-{len(STORY_THEMES)} (default random)",
        },
        "usage": ["{tr}poststory [caption] <reply to media>", "{tr}poststory <text> [-t3]"],
        "examples": ["{tr}poststory good morning ☀️ -cf", "{tr}poststory Shipping features today -t2"],
    },
)
async def poststory_cmd(event):
    "Post a story."
    raw = (event.pattern_match.group(1) or "").strip()
    words, privacy, theme = [], "all", None
    for w in raw.split(" "):
        lw = w.lower()
        if lw == "-cf":
            privacy = "cf"
        elif lw == "-c":
            privacy = "contacts"
        elif lw.startswith("-t") and lw[2:].isdigit():
            theme = int(lw[2:]) - 1
        else:
            words.append(w)
    text = " ".join(words).strip()
    reply = await event.get_reply_message()
    has_media = reply and isinstance(reply.media, (types.MessageMediaPhoto, types.MessageMediaDocument)) and (
        reply.photo or reply.video or (reply.document and (reply.file.mime_type or "").startswith("image/"))
    )
    if not has_media and not text:
        return await edit_delete(event, "`Reply to a photo/video, or give some text for a text story.`", 8)

    status = await edit_or_reply(event, "`Preparing story…`")
    tmp = tempfile.mkdtemp(dir=Config.TMP_DOWNLOAD_DIRECTORY)
    try:
        if has_media:
            if reply.video and reply.file.duration and reply.file.duration > 60:
                return await status.edit("Stories can be at most 60 seconds. Trim it first (`.vtrim`).")
            path = await event.client.download_media(reply.media, file=tmp + os.sep)
            if not path:
                return await status.edit("Couldn't download that media.")
            caption = text
        else:
            path = text_story_image(
                text,
                theme if theme is not None else random.randrange(len(STORY_THEMES)),
                os.path.join(tmp, "story.jpg"),
            )
            caption = ""

        await status.edit("`Uploading…`")
        _, media, _ = await event.client._file_to_media(path, supports_streaming=True)
        message, entities = await event.client._parse_message_text(caption, "md")
        rules = {
            "all": [types.InputPrivacyValueAllowAll()],
            "contacts": [types.InputPrivacyValueAllowContacts()],
            "cf": [types.InputPrivacyValueAllowCloseFriends()],
        }[privacy]
        await event.client(
            functions.stories.SendStoryRequest(
                peer=types.InputPeerSelf(),
                media=media,
                privacy_rules=rules,
                caption=message or None,
                entities=entities or None,
                period=86400,
            )
        )
    except RPCError as e:
        reason = getattr(e, "message", str(e))
        friendly = {
            "STORIES_TOO_MUCH": "you hit today's story limit for free accounts",
            "PREMIUM_ACCOUNT_REQUIRED": "Telegram wants Premium for this (daily limit reached?)",
            "STORY_PERIOD_INVALID": "free accounts can only post 24h stories",
            "MEDIA_FILE_INVALID": "Telegram didn't accept that file as story media",
        }.get(reason, reason)
        return await status.edit(f"❌ Story not posted: {esc(friendly)}", parse_mode="html")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    who = {"all": "everyone", "contacts": "contacts", "cf": "close friends"}[privacy]
    await edit_delete(status, f"✅ Story posted for **{who}**. Check it with `{Config.COMMAND_HAND_LER}mystories`.", 10)
