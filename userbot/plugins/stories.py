# Stories — download anyone's stories (including your whole archive), inspect viewers, post new ones.
#
# Numbering is always newest → oldest: #1 is the latest story.
#
#   .mystories                    overview of your active stories + archive size
#   .mystories list [page]        numbered list of ALL your stories (active + archive)
#   .mystories 4 | 1-10 | all     download your 4th newest story / a range / everything
#   .mystories 4 -v               who viewed story #4
#
#   .stories @user                download their active stories (last 24h)
#   .stories @user -p             download their profile (pinned) stories
#   .stories @user list           numbered list of their active + profile stories
#   .stories @user 3 | 1-5        download by number
#
#   .poststory [text] [-c|-cf]    post replied photo/video, or a generated text story
#
# Telegram only exposes another person's active and profile (pinned) stories.
# Expired stories they didn't pin stay private to them; your own archive is complete.

import os
import random
import re
import shutil
import tempfile

from telethon.errors import RPCError
from telethon.tl import functions, types

from userbot import catub

from ..Config import Config
from ..core.managers import edit_delete, edit_or_reply
from ..helpers.functions.kittycard import STORY_THEMES, text_story_image
from ..helpers.functions.kittychat import esc, mention_html, name_of, resolve_chat
from ..helpers.functions.kittytime import ago, fmt_local, now_utc

plugin_category = "utils"

MAX_DOWNLOAD = 50  # stories per command
PAGE = 20  # rows per `list` page
_RANGE = re.compile(r"^(\d{1,4})(?:-(\d{1,4}))?$")


def _reaction(r) -> str:
    if isinstance(r, types.ReactionEmoji):
        return r.emoticon
    if isinstance(r, types.ReactionCustomEmoji):
        return "🧩"
    return ""


async def _full_items(client, peer, items):
    """Swap StoryItemSkipped (no media) for full StoryItems, drop deleted; keeps order."""
    skipped = [s.id for s in items if isinstance(s, types.StoryItemSkipped)]
    full = {s.id: s for s in items if isinstance(s, types.StoryItem)}
    for start in range(0, len(skipped), 100):
        res = await client(functions.stories.GetStoriesByIDRequest(peer=peer, id=skipped[start : start + 100]))
        full.update({s.id: s for s in res.stories if isinstance(s, types.StoryItem)})
    return [full[s.id] for s in items if s.id in full]


async def _collect(client, peer, own: bool, need: int | None = None, active=True, history=True):
    """Stories newest → oldest, plus the server's total count of archive/profile stories.

    own=True  : active + your full archive (stories.getStoriesArchive)
    own=False : active + their profile/pinned stories (stories.getPinnedStories)
    need      : stop paginating once this many stories are known
    """
    found = {}
    if active:
        res = await client(functions.stories.GetPeerStoriesRequest(peer=peer))
        for s in res.stories.stories:
            if not isinstance(s, types.StoryItemDeleted):
                found[s.id] = s
    total = 0
    if history:
        req = functions.stories.GetStoriesArchiveRequest if own else functions.stories.GetPinnedStoriesRequest
        offset = 0
        for _ in range(40):  # up to 4000 stories
            res = await client(req(peer=peer, offset_id=offset, limit=100))
            total = res.count
            batch = [s for s in res.stories if not isinstance(s, types.StoryItemDeleted)]
            if not res.stories:
                break
            for s in batch:
                if s.id not in found or isinstance(found[s.id], types.StoryItemSkipped):
                    found[s.id] = s
            offset = min(s.id for s in res.stories)
            if need and len(found) >= need:
                break
    return sorted(found.values(), key=lambda s: s.id, reverse=True), total


def _parse_pick(token: str):
    """'4' -> (4, 4); '1-10' -> (1, 10); 'all' -> (1, MAX_DOWNLOAD); else None."""
    if token == "all":
        return 1, MAX_DOWNLOAD
    m = _RANGE.match(token)
    if not m:
        return None
    a, b = int(m.group(1)), int(m.group(2) or m.group(1))
    if a < 1 or b < 1:
        return None
    return min(a, b), max(a, b)


def _split_args(raw: str):
    """Pull flags / list / pick out of the args; whatever is left is the target."""
    flags, pick, rest, page = set(), None, [], None
    words = raw.split()
    i = 0
    while i < len(words):
        w = words[i]
        lw = w.lower()
        if lw in ("-p", "-v"):
            flags.add(lw)
        elif lw == "list":
            flags.add("list")
            if i + 1 < len(words) and words[i + 1].isdigit() and len(words[i + 1]) <= 3:
                page = int(words[i + 1])
                i += 1
        elif pick is None and _parse_pick(lw):
            pick = _parse_pick(lw)
        else:
            rest.append(w)
        i += 1
    return flags, pick, " ".join(rest), page or 1


def _story_badges(s) -> str:
    kind = "🎬" if isinstance(s.media, types.MessageMediaDocument) else "🖼"
    privacy = "🌍"
    if s.close_friends:
        privacy = "💚"
    elif s.contacts:
        privacy = "👥"
    elif s.selected_contacts:
        privacy = "🎯"
    live = "🟢" if s.expire_date and s.expire_date > now_utc() else ""
    pin = "📌" if s.pinned else ""
    return f"{kind}{privacy}{live}{pin}"


def _views(s) -> int:
    return s.views.views_count if s.views and s.views.views_count is not None else 0


async def _send_stories(event, status, peer, picked, who):
    """picked: [(number or None, StoryItem-or-Skipped)] -> download and send as albums."""
    items = await _full_items(event.client, peer, [s for _, s in picked])
    numbers = {s.id: n for n, s in picked}
    if not items:
        return await status.edit("Those stories are gone (deleted).")
    await status.edit(f"`Downloading {len(items)} stor{'y' if len(items) == 1 else 'ies'}…`")
    tmp = tempfile.mkdtemp(dir=Config.TMP_DOWNLOAD_DIRECTORY)
    files, captions = [], []
    try:
        for s in items:
            if s.media is None:
                continue
            path = await event.client.download_media(s.media, file=os.path.join(tmp, f"{s.id}"))
            if not path:
                continue
            state = "active" if s.expire_date and s.expire_date > now_utc() else ("profile" if s.pinned else "archive")
            views = f" · 👁 {_views(s)}" if s.views else ""
            num = f" · #{numbers[s.id]}" if numbers.get(s.id) else ""
            cap = f"📖 {who}{num} · {fmt_local(s.date)} ({ago(s.date)}) · {state}{views}"
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


def _list_page(stories, page, who, cmd):
    pages = max(1, (len(stories) + PAGE - 1) // PAGE)
    page = min(max(page, 1), pages)
    start = (page - 1) * PAGE
    lines = [f"📚 <b>{esc(who)}</b> — {len(stories)} stories, newest first (page {page}/{pages})\n"]
    for n, s in enumerate(stories[start : start + PAGE], start + 1):
        date = s.date.strftime("%d %b %Y") if s.date else "?"
        cap = f" — {esc(s.caption[:30])}" if getattr(s, "caption", None) else ""
        if isinstance(s, types.StoryItem):
            lines.append(f"<code>{n:>3}</code> {_story_badges(s)} {date} · 👁 {_views(s)}{cap}")
        else:
            lines.append(f"<code>{n:>3}</code> {date}")
    nav = f"<code>{cmd} list {page + 1}</code> next · " if page < pages else ""
    lines.append(f"\n{nav}<code>{cmd} 3</code> or <code>{cmd} 1-10</code> to download")
    return "\n".join(lines)


# ────────────────────────────── .stories ──────────────────────────────


@catub.cat_cmd(
    pattern=r"stories(?:\s+([\s\S]+))?$",
    command=("stories", plugin_category),
    info={
        "header": "Download someone's stories: active, profile, or by number.",
        "description": "Numbers count newest → oldest across their active + profile (pinned) stories. "
        "Telegram doesn't expose expired stories they didn't pin to their profile. "
        "The bot never calls the 'mark story as viewed' API.",
        "flags": {"-p": "download all their profile (pinned) stories", "list": "numbered list"},
        "usage": [
            "{tr}stories <@user / id / reply>",
            "{tr}stories <@user> -p",
            "{tr}stories <@user> list",
            "{tr}stories <@user> <n | from-to>",
        ],
        "examples": ["{tr}stories @telegram", "{tr}stories @telegram 3", "{tr}stories @durov 1-5", "{tr}stories -p  (reply)"],
    },
)
async def stories_cmd(event):
    "Download stories."
    flags, pick, ref, page = _split_args(event.pattern_match.group(1) or "")
    reply = await event.get_reply_message()
    if ref:
        target = await resolve_chat(event.client, ref)
    elif reply and reply.sender_id:
        target = await reply.get_sender()
    elif event.is_private:
        target = await event.get_chat()
    else:
        return await edit_delete(event, "`Give a @username, id or reply to someone.`", 6)
    if target is None:
        return await edit_delete(event, "`Couldn't find that user/channel.`", 6)

    who = name_of(target)
    status = await edit_or_reply(event, "`Looking for stories…`")
    peer = await event.client.get_input_entity(target)
    cmd = f"{Config.COMMAND_HAND_LER}stories {ref}".rstrip()
    try:
        if pick or "list" in flags:
            need = None if "list" in flags else pick[1]
            stories, _ = await _collect(event.client, peer, own=False, need=need)
        elif "-p" in flags:
            stories, _ = await _collect(event.client, peer, own=False, active=False)
        else:
            stories, _ = await _collect(event.client, peer, own=False, history=False)
    except RPCError as e:
        return await status.edit(f"Telegram refused: <code>{esc(e)}</code>", parse_mode="html")

    if not stories:
        kind = "profile stories" if "-p" in flags else ("stories" if pick or "list" in flags else "active stories (last 24h)")
        tip = "" if pick or flags else f" Try <code>{cmd} -p</code> for profile stories."
        return await status.edit(f"📭 {esc(who)} has no {kind}.{tip}", parse_mode="html")

    if "list" in flags:
        return await status.edit(_list_page(await _full_items(event.client, peer, stories), page, who, cmd), parse_mode="html")

    if pick:
        a, b = pick
        if a > len(stories):
            return await status.edit(f"{esc(who)} only has {len(stories)} stories I can see.", parse_mode="html")
        numbered = list(enumerate(stories, 1))[a - 1 : min(b, a - 1 + MAX_DOWNLOAD)]
    else:
        # whole sets (active / profile) read best oldest → newest; numbers only mean
        # something in the combined numbering, so leave them off here
        numbered = [(None, s) for s in reversed(stories[:MAX_DOWNLOAD])]
    await _send_stories(event, status, peer, numbered, who)


# ───────────────────────────── .mystories ─────────────────────────────


async def _viewers(event, status, story, number):
    me = types.InputPeerSelf()
    try:
        views = await event.client(functions.stories.GetStoryViewsListRequest(peer=me, id=story.id, offset="", limit=100))
    except RPCError as e:
        return await status.edit(f"Couldn't load viewers: <code>{esc(e)}</code>", parse_mode="html")
    users = {u.id: u for u in views.users}
    lines = [
        f"📖 <b>Story #{number}</b> · posted {fmt_local(story.date)}\n"
        f"👁 {views.views_count} views · ❤️ {views.reactions_count} reactions · ↗️ {views.forwards_count} shares\n"
    ]
    for v in views.views:
        if isinstance(v, types.StoryView):
            react = f" {_reaction(v.reaction)}" if v.reaction else ""
            lines.append(f"• {mention_html(users.get(v.user_id), str(v.user_id))}{react} — <i>{ago(v.date)}</i>")
    if not views.views and (views.views_count or _views(story)):
        lines.append("<i>Telegram no longer shows who viewed this story (viewer lists expire after a while).</i>")
    elif views.views_count > len(views.views):
        lines.append(f"…and {views.views_count - len(views.views)} more")
    return await status.edit("\n".join(lines)[:4090], parse_mode="html")


@catub.cat_cmd(
    pattern=r"mystories(?:\s+([\s\S]+))?$",
    command=("mystories", plugin_category),
    info={
        "header": "Your stories: overview, full archive, downloads and viewers.",
        "description": "Numbers count newest → oldest over ALL your stories, active and archived, "
        "so #1 is your latest story ever. Downloads are capped at 50 per command.",
        "flags": {"list [page]": "numbered list of every story", "-v": "viewer list instead of downloading"},
        "usage": [
            "{tr}mystories",
            "{tr}mystories list [page]",
            "{tr}mystories <n | from-to | all>",
            "{tr}mystories <n> -v",
        ],
        "examples": ["{tr}mystories 4", "{tr}mystories 1-10", "{tr}mystories list 2", "{tr}mystories 1 -v"],
    },
)
async def mystories_cmd(event):
    "Your stories."
    flags, pick, _, page = _split_args(event.pattern_match.group(1) or "")
    me = types.InputPeerSelf()
    cmd = f"{Config.COMMAND_HAND_LER}mystories"
    status = await edit_or_reply(event, "`Fetching your stories…`")
    try:
        if pick or "list" in flags:
            need = None if "list" in flags else pick[1]
            stories, archive_total = await _collect(event.client, me, own=True, need=need)
        else:
            active, _ = await _collect(event.client, me, own=True, history=False)
            res = await event.client(functions.stories.GetStoriesArchiveRequest(peer=me, offset_id=0, limit=1))
            archive_total = res.count
            stories = await _full_items(event.client, me, active)
    except RPCError as e:
        return await status.edit(f"Telegram refused: <code>{esc(e)}</code>", parse_mode="html")

    if "list" in flags:
        if not stories:
            return await status.edit("📭 You haven't posted any stories yet.")
        return await status.edit(_list_page(await _full_items(event.client, me, stories), page, "Your stories", cmd), parse_mode="html")

    if pick:
        a, b = pick
        if not stories or a > len(stories):
            return await status.edit(f"You have {len(stories)} stories in total.")
        if "-v" in flags:
            story = (await _full_items(event.client, me, [stories[a - 1]]) or [None])[0]
            if story is None:
                return await status.edit("That story was deleted.")
            return await _viewers(event, status, story, a)
        numbered = list(enumerate(stories, 1))[a - 1 : min(b, a - 1 + MAX_DOWNLOAD)]
        return await _send_stories(event, status, me, numbered, "My story")

    # overview
    lines = ["📚 <b>Your active stories</b>\n"]
    if not stories:
        lines.append("<i>none right now</i>")
    total_views = 0
    for i, s in enumerate(stories, 1):
        v = s.views
        total_views += _views(s)
        reacts = v.reactions_count if v and v.reactions_count else 0
        expires = f"expires {fmt_local(s.expire_date, with_date=False)}" if s.expire_date else ""
        cap = f" — {esc(s.caption[:40])}" if s.caption else ""
        lines.append(f"<code>{i}</code> {_story_badges(s)} 👁 <b>{_views(s)}</b> ❤️ {reacts} · {expires}{cap}")
    if stories:
        lines.append(f"\nTotal views: <b>{total_views}</b>")
    lines.append(
        f"📦 Archive: <b>{archive_total}</b> stories all-time\n\n"
        f"<code>{cmd} list</code> browse all · <code>{cmd} 4</code> download #4 · "
        f"<code>{cmd} 1-10</code> range · <code>{cmd} 1 -v</code> viewers"
    )
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
