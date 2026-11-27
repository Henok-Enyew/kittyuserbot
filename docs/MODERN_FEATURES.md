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
| `.stories @user [-p \| list \| n \| a-b]` | Someone's active / profile stories, or one by number (newest = 1), without calling the "mark viewed" API. Their expired unpinned stories aren't available from Telegram | `stories.py` |
| `.mystories [list \| n \| a-b \| all] [-v]` | Your stories incl. the full archive: browse, download by number (newest = 1), viewer list | `stories.py` |
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
| `.ethdate [date]` | Today in the Ethiopian calendar (Amharic + English + Ge'ez numerals), Ethiopian time, next holiday | `habesha.py` |
| `.ethconv <date>` | Convert Gregorian ⇄ Ethiopian (`2026-11-24`, `15 hidar 2019`, `ኅዳር 15 2019`) | `habesha.py` |
| `.holidays [n]` | Upcoming Ethiopian public holidays; Fasika computed yearly, Muslim holidays ≈ | `habesha.py` |
| `.birr [amount] [cur]` | ETB exchange rates, keyless (open.er-api.com, daily official rate) | `habesha.py` |
| `.countdown <holiday\|date\|2h> [\| title]` | Live self-updating countdown message, survives restarts; `.countdowns`, `.countdown stop` | `countdown.py` |
| `.kw add\|del\|list\|ignore\|on\|off` | Keyword alerts: Saved Messages ping when your words appear in any group | `kw.py` |
| `.biz on\|hours\|away\|greet\|test` | Free "Telegram Business": away messages outside working hours + greetings | `biz.py` |
| `.vfx <effect>` (reply) | Voice changer via ffmpeg: chipmunk, deep, robot, alien, echo, radio, 8d, reverse… | `voicefx.py` |
| `.antidelete on\|off` | Logs deleted / edited private messages to Saved Messages (opt-in, in-memory) | `antidelete.py` |
| `.raffle [n]` | Giveaway: animated draw among people who reacted/replied (or recent members) | `groupfun.py` |
| `.top [24h\|7d\|30d]` | Leaderboard of who talks the most | `groupfun.py` |
| `.declutter [archive\|read]` | Find never-read channels, dead groups, deleted accounts, old bots; archive or mark read | `declutter.py` |
| `.capsule <when> <text>` | Time-capsule message delivered to this chat up to a year later | `remind.py` |
| `.kitty [on\|off\|pet\|treat\|name\|coat\|public\|notify\|stats\|reset]` | Pixel cat that follows your life: eats LeetCode problems, sulks when the streak breaks, sleeps on your keyboard at 2-5 AM, grows kitten → legend | `kitty.py` |
| `.livepfp [on\|off\|scene\|preview\|now\|every\|shuffle]` | Living profile photo: pixel city with a lit window per problem solved today, streak beacon, real Addis sky/moon/weather, sleeps when you're offline, Kitty on the roof | `livepfp.py` |

Times are parsed and shown in Africa/Addis_Ababa time (`10m`, `1h30m`, `18:30`,
`6pm`, `tomorrow 9am`).

Shared helpers live in `userbot/helpers/functions/`: `kittytime.py` (time
parsing), `ethiocal.py` (Ethiopian calendar, Ge'ez numerals, holidays), `kittychat.py` (names, links, message labels), `kittycard.py` and
`wrapped_card.py` (Pillow rendering), `kittylife.py` (live signals: online status,
Open-Meteo weather, LeetCode solves and streak), `kittypet.py` (Kitty's simulation,
no Telegram code), `pixelscene.py` (80x80 pixel-art city, sprites, status card) and
`kittystore.py` (glue between them).

Settings are stored in the `globals` table: `AUTOREACT_RULES`, `BDWISH_MODE`,
`BDWISH_MSG`, `BDWISH_SENT`, `BDWISH_LAST`, `BDAY_CACHE`, `COUNTDOWNS`,
`KW_STATE`, `BIZ_STATE`, `ANTIDELETE`. Kitty and the living photo keep their state in
`kitty_kv` (`KITTY_PET`, `LIVEPFP`). Both are off until you turn them on.
