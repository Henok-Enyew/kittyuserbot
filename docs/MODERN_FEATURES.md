# Modern Telegram features (2024+ API)

Plugins built on newer Telegram features (API layer 186: stories, reactions,
read dates, message effects, expandable quotes, birthdays). None of them need an
AI key or Telegram Premium. Every command also shows up in `.help`.

| Command | What it does | Plugin |
|---|---|---|
| `.seen` (reply to your msg) | Who read it and when (groups up to 100 members); exact read time in PMs | `insight.py` |
| `.whoreact` (reply) | Who reacted with which emoji | `insight.py` |
| `.online [@user]` | Who's online now / active in the last 15 min; a user's last seen | `insight.py` |
| `.peek [n \| @chat] [count]` | Unread inbox, then read a chat **without** sending read receipts | `insight.py` |
| `.stories @user [-p]` | Download someone's active (or profile) stories without calling the "mark viewed" API | `stories.py` |
| `.mystories [n]` | Your active stories, views, reactions, viewer list | `stories.py` |
| `.poststory [text] [-c\|-cf] [-tN]` | Post the replied photo/video, or a generated gradient text story | `stories.py` |
| `.autoreact <emoji\|random\|off>` | Auto-react to a person (reply) or a whole chat; `.autoreacts` lists rules | `autoreact.py` |
| `.fx <emoji> <text>` | Send with a full-screen message effect (PMs; free: 👍 👎 ❤️ 🔥 🎉 💩) | `fx.py` |
| `.cq [title \|] <text>` | Expandable collapsed quote; reply to re-post a long message collapsed | `fx.py` |
| `.remind <when> <text>` | Reminder as a scheduled message in Saved Messages, so it survives restarts; `.reminders`, `.unremind` | `remind.py` |
| `.snooze <2h\|tomorrow 8am\|forever\|off>` | Mute a chat until a time (Telegram unmutes it itself) | `chattools.py` |
| `.find <words> [-n 50]` | Search all chats at once, results with tap-able links | `chattools.py` |
| `.export [count] [txt]` | Export the chat to a Telegram-styled HTML (or txt) file in Saved Messages | `chattools.py` |
| `.wrapped [count]` | "Chat Wrapped" recap image: top talkers, peak hours, streaks, top words, reply speed | `wrapped.py` |
| `.bdays [refresh]` | Upcoming birthdays of your contacts | `birthdays.py` |
| `.bdwish remind\|auto\|off\|send\|msg` | Daily 08:00 birthday check; `auto` wishes people with the 🎉 effect | `birthdays.py` |
| `.quiz [n] [category] [level]` | Native Telegram quiz polls from Open Trivia DB | `quiz.py` |

Times are parsed and shown in Africa/Addis_Ababa time (`10m`, `1h30m`, `18:30`,
`6pm`, `tomorrow 9am`).

Shared helpers live in `userbot/helpers/functions/`: `kittytime.py` (time
parsing), `kittychat.py` (names, links, message labels), `kittycard.py` and
`wrapped_card.py` (Pillow rendering).

Settings are stored in the `globals` table: `AUTOREACT_RULES`, `BDWISH_MODE`,
`BDWISH_MSG`, `BDWISH_SENT`, `BDWISH_LAST`, `BDAY_CACHE`.
