# KittyUserBot creative fun string banks (API-free).
import hashlib
import random
import re

ZALGO_UP = list("̍̎̄̅̿̑̆̐͒͗͑̇̈̉̊̋̌̍̎̏̐̑̒̓̔̽̾̿̀́͂̓̈́͆͊͋͌͐͑͒͗͛ͣͤͥͦͧͨͩͪͫͬͭͮͯ")
ZALGO_MID = list("̴̵̶̷̸̡̢̧̨̛̹̺̻̼͇͈͎͍͎̀́̕͘ͅ")
ZALGO_DOWN = list("̖̗̘̙̜̝̞̟̠̣̤̥̦̩̪̫̬̭̮̯̰̱̲̳̹̺̻̼͇͈͉͍͎́̏̑̒̓̔̽̾̿͂͆͊͋͌͐͑͒͗͛ͣͤͥͦͧͨͩͪͫͬͭͮͯͅ")


def pick(items):
    return random.choice(items)


def meter(seed_text: str, salt: str = "") -> int:
    """Stable 0-100 score from text (same inputs => same score)."""
    raw = f"{salt}|{(seed_text or '').strip().lower()}"
    digest = hashlib.md5(raw.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 101


def fill(template: str, **kwargs) -> str:
    class _Safe(dict):
        def __missing__(self, key):
            return "{" + key + "}"

    return template.format_map(_Safe(**{k: (v if v is not None else "") for k, v in kwargs.items()}))


def bar(score: int, width: int = 10) -> str:
    score = max(0, min(100, int(score)))
    filled = round(score / 100 * width)
    return "█" * filled + "░" * (width - filled)


def ship_name(a: str, b: str) -> str:
    a, b = (a or "A").strip(), (b or "B").strip()
    if not a:
        a = "A"
    if not b:
        b = "B"
    left = a[: max(2, len(a) // 2)]
    right = b[len(b) // 2 :]
    return (left + right).title().replace(" ", "")


def zalgo(text: str, intensity: int = 2) -> str:
    out = []
    for ch in text:
        out.append(ch)
        if ch.isspace():
            continue
        for _ in range(intensity):
            out.append(pick(ZALGO_UP))
            out.append(pick(ZALGO_MID))
            out.append(pick(ZALGO_DOWN))
    return "".join(out)


def clean_name(text: str, fallback: str = "someone") -> str:
    text = (text or "").strip()
    text = re.sub(r"^@+", "", text)
    return text or fallback


# ─── Roasts ───────────────────────────────────────────────────────────────────
ROAST_MILD = [
    "{name}'s personality is buffering at 2%.",
    "{name} is the human equivalent of a participation trophy.",
    "If common sense was Wi‑Fi, {name} would be out of range.",
    "{name} brings the vibe of a wet sock in a luxury hotel.",
    "{name} is proof that NPC dialogue can walk and talk.",
]

ROAST_MID = [
    "{name}'s brain has more unfinished tabs than Chrome.",
    "I'd agree with {name}, but then we'd both be wrong.",
    "{name} peaked in a group chat and never recovered.",
    "Somewhere a village is missing its idiot. {name} has roaming enabled.",
    "{name}'s aura is 'left on read by destiny'.",
]

ROAST_BRUTAL = [
    "{name} is so mid that average filed a restraining order.",
    "Evolution looked at {name} and hit undo.",
    "{name}'s confidence is unpaid overtime for their incompetence.",
    "If embarrassment was currency, {name} would be a billionaire.",
    "{name} is the plot hole in everyone else's day.",
]

DISS_LINES = [
    "Not roasted — lightly air‑fried at 220° until golden and wrong.",
    "That wasn't a burn. That was a controlled demolition.",
    "Chef's kiss… to the dumpster fire that is this take.",
]

RATE_COMMENTS = {
    "low": [
        "Scientists classified this as a cry for help.",
        "Even the void said 'no thanks'.",
        "This scored lower than a potato in a spelling bee.",
    ],
    "mid": [
        "Aggressively average. Weaponized beige.",
        "Not bad. Not good. Just… vibing incorrectly.",
        "The definition of 'could be a person'.",
    ],
    "high": [
        "Main character energy with DLC installed.",
        "The algorithm bows. The timeline trembles.",
        "Certified legendary. Frame this.",
    ],
}

RIZZ_LINES = [
    "Are you Wi‑Fi? Because I'm feeling a connection… and also insecurity.",
    "Do you have a map? I keep getting lost in your bad decisions.",
    "Is your name Google? Because you have everything I'm searching for… badly.",
    "If looks could kill, yours would still need a permit and a lawyer.",
]

# ─── Shipping ─────────────────────────────────────────────────────────────────
SHIP_VERDICTS = {
    "low": [
        "Chemistry: expired yogurt.",
        "OTP status: Opposed To Partnership.",
        "The universe filed a noise complaint.",
    ],
    "mid": [
        "Situationship with extra steps.",
        "Fanfic writers are sweating.",
        "Could work if both ignore red flags (they won't).",
    ],
    "high": [
        "Canon. Don't argue with the prophecy.",
        "The timeline repaired itself for this ship.",
        "Wedding playlist already downloading.",
    ],
}

EX_ROASTS = [
    "{name} wasn't an ex — they were a limited‑time event nobody asked for.",
    "Blocking {name} raised the national IQ by 0.3.",
    "{name} still lives rent‑free… in the trash folder.",
    "Relationship with {name}: 2 stars. Would not recommend. Shipping delayed.",
]

# ─── Oracle ───────────────────────────────────────────────────────────────────
FORTUNES = [
    "You will touch grass. Reluctantly. It will judge you.",
    "A great opportunity approaches: the opportunity to mind your business.",
    "Today your enemies will underestimate you. Correctly.",
    "Beware of free advice and free Wi‑Fi.",
    "Someone is thinking of you. They're wrong, but committed.",
    "Your future holds snacks. Prioritize accordingly.",
    "The stars say 'maybe'. The moon says 'absolutely not'.",
    "You will win an argument you shouldn't have started.",
]

ZODIAC = [
    ("Aries", "Pick a fight with a vending machine. Lose with dignity."),
    ("Taurus", "Nap strategically. Productivity is a scam today."),
    ("Gemini", "Say two contradictory things before noon. Stay mysterious."),
    ("Cancer", "Cry, then weaponize the tears into motivation."),
    ("Leo", "Main character day. Tip: other people exist."),
    ("Virgo", "Reorganize something nobody asked you to. Feel power."),
    ("Libra", "Can't decide? Flip a coin, then ignore it."),
    ("Scorpio", "Plot in silence. Smile like a tax audit."),
    ("Sagittarius", "Book a trip you can't afford emotionally."),
    ("Capricorn", "Grind. Then grind the grind. Then rest never."),
    ("Aquarius", "Be weird on purpose. Accidental weird is Tuesday."),
    ("Pisces", "Daydream so hard reality sends a cease‑and‑desist."),
]

EIGHTBALL = [
    "Yes.",
    "No.",
    "Ask again when sober.",
    "The spirits say 'lmao'.",
    "Absolutely. Catastrophically.",
    "Outlook hazy — like your search history.",
    "Signs point to chaos.",
    "Don't. Just… don't.",
    "It is certain (source: vibes).",
    "Better not tell you now. Or ever.",
]

JOKES = [
    "I told my Wi‑Fi we needed space. Now it won't connect.",
    "My therapist says I have a preoccupation with vengeance. We'll see about that.",
    "I have a joke about construction… but I'm still working on it.",
    "Parallel lines have so much in common. It's a shame they'll never meet.",
]

DIRTY_JOKES = [
    "I like my relationships like my coffee: hot, bitter, and likely to keep me up.",
    "My bed and I have a great relationship — we see each other every night and do nothing productive.",
    "I'm not saying I'm addicted to attention… but if you leave me on read I experience withdrawal.",
    "Sex education taught me biology. Group chats taught me regret.",
]

PUNS = [
    "I'm reading a book on anti‑gravity. It's impossible to put down.",
    "I used to be a banker but I lost interest.",
    "The past, present, and future walked into a bar. It was tense.",
]

DAD_JOKES = [
    "Why don't eggs tell jokes? They'd crack each other up.",
    "I'm afraid for the calendar. Its days are numbered.",
    "What do you call fake spaghetti? An impasta.",
]

TAROT = [
    "The Fool (but make it fashion)",
    "The Tower, but it's your group chat",
    "Ace of Snacks",
    "Nine of Unread Messages",
    "The Lovers… arguing about pizza",
    "Death (metaphorical; chill)",
    "Wheel of Unfortunate Timing",
    "The Magician's unpaid internship",
    "Queen of Side‑Eye",
    "Knight of Oversharing",
]

PROPHECIES = [
    "Hear me, {name}: before the next full moon, you will reply 'lol' to something tragic.",
    "The ancient scrolls name {name} as Bringer of Awkward Silences.",
    "A crow lands. It owes {name} money. The debt is emotional.",
    "When the clocks blink 3:33, {name} will remember an old cringe and perish a little.",
]

VIBE_DIAG = [
    "Diagnosis: chronically online with acute main‑character fever.",
    "Diagnosis: soft launch energy, hard launch consequences.",
    "Diagnosis: running on spite and iced coffee.",
    "Diagnosis: mysterious. Suspiciously empty behind the eyes.",
    "Diagnosis: golden retriever in a trench coat.",
]

# ─── Spicy ────────────────────────────────────────────────────────────────────
FLIRTS = [
    "If beauty was a crime, {name} would still get community service for that attitude.",
    "Are you a parking ticket? Because you've got 'fine' written all over you… and unpaid drama.",
    "I'd say Godzilla, but you're the king of… never mind, that joke got weird.",
    "{name}, you're the reason 'airplane mode' was invented — people need a break from the heat.",
]

PICKUPS = [
    "Hey {name}, my bed is broken — can I sleep in yours? Asking for a friend (the friend is me).",
    "Do you believe in love at first sight, or should I walk by again looking hotter?",
    "Is your dad a thief? Because he stole the stars and put them in your eyes. Also maybe Wi‑Fi.",
    "I'm not a photographer, but I can picture us… arguing about snacks at 2am.",
]

THIRST = [
    "Hydration check failed. Someone get {name} a glass of water and a cold shower.",
    "Thirst level: camel crossing the Sahara with a dating app.",
    "Down bad? {name} invented a new basement.",
]

BEDROOM_FRAMES = [
    "Dim the lights…",
    "Cue the soft playlist…",
    "Pull the curtains…",
    "Light a candle…",
    "The candle tips over.",
    "False alarm. Ordering pizza instead.",
    "Mood: cheese‑stuffed crust. Still kinda sexy.",
]

MOAN_FRAMES = [
    "ahh",
    "ahh~",
    "ahh~~",
    "oh no not like that",
    "I stubbed my toe",
    "AHHHHHHHHH (pain)",
    "…anyway",
]

NUDE_SWITCH = [
    "Sending nudes…",
    "Compressing…",
    "Uploading… 12%",
    "Uploading… 69%",
    "Uploading… 99%",
    "Delivered:\n🐱 a blurry cat photo\n📄 your personality tax return\nlasagna recipe (grandma's)",
]

ONLYFANS_PITCH = [
    "Unlock {name}'s premium content: exclusive sighs, rationed eye contact, and one (1) soft launch.",
    "Subscribe to {name}: $4.99/month for vibes, $9.99 for intentional spelling.",
    "Fan tip jar for {name} currently accepts: ego, attention, and unread essays.",
]

DIRTY_DARES = [
    "Send a voice note that says 'hello' like it's illegal.",
    "Compliment someone so hard they get suspicious.",
    "Change your status to something unhinged for 10 minutes.",
    "Reply to the next message with only emoji that look suggestive (keep it chat‑safe).",
    "Write a fake dating bio for the replied user.",
]

AFTERCARE = [
    "**Aftercare card for {name}**\n• Water\n• Snacks\n• Emotional support meme\n• Permission to pretend that never happened",
    "**Post‑chaos protocol**\nHydrate. Stretch. Blame Mercury. Soft‑block if needed.",
]

# ─── Dark ─────────────────────────────────────────────────────────────────────
OBITUARIES = [
    "Here lies {name}.\nCause of death: chronic cringe exposure.\nSurvived by: unread notifications.",
    "In loving memory of {name}'s dignity (2019–today).",
    "{name} — gone too soon from this conversation.\nDonations to: the bit.",
]

TOMBSTONES = [
    "```\n  _______\n /       \\\n|  R.I.P. |\n| {name} |\n|  mid    |\n \\_______/\n```",
]

HAUNTED = [
    "The lights flicker…",
    "Something breathes near {name}…",
    "A cold draft of unread tea…",
    "The ghost of their search history appears…",
    "It speaks: 'we need to talk.'",
    "{name} has been possessed by main‑character syndrome.",
]

CURSED = [
    "Cursed thought: {name} has a favorite Windows error sound.",
    "Cursed comment: this message will be screenshotted in hell's group chat.",
    "Cursed vibe: smiling in a way that suggests unpaid invoices.",
]

LAST_WORDS = [
    "Tell my Wi‑Fi… I loved it.",
    "I leave my unfinished playlists to nobody.",
    "Bury me with my charger.",
    "One last thing— wait, never mind.",
]

GHOSTED = [
    "{name} left the chat… spiritually.",
    "Last online: emotionally unavailable.",
    "Typing… then silence. A haunting.",
    "The paranormal activity was just them ignoring you.",
]

THERAPY = [
    "Therapist: how does that make you feel?\nYou: bad.\nTherapist: interesting. $150.",
    "Therapist: have you tried not doing that?\nYou: …\nTherapist: groundbreaking.",
    "Therapist: let's unpack that.\n*opens empty suitcase*",
]

VOID_LINES = [
    "You stare into the void.",
    "The void stares back.",
    "The void checks your mutuals.",
    "The void soft‑launches disappointment.",
    "The void says: 'skill issue.'",
]

YIKES_ESCALATION = [
    "yikes",
    "yikes.",
    "y i k e s",
    "secondhand embarrassment entering the chat",
    "calling a priest",
    "calling a publicist",
    "autopsy complete: cause of death = this message",
]

# ─── Chaos / story ────────────────────────────────────────────────────────────
STORY_BEATS = [
    "Act I — {hero} wakes up wrong on purpose.",
    "Act II — A mysterious quest appears: touch grass.",
    "Act III — {hero} meets {other}, a walking red flag with good hair.",
    "Act IV — Betrayal! The snacks were a lie.",
    "Act V — Final boss: group chat politics.",
    "Epilogue — {hero} wins. Nobody asked. Credits roll on a loop.",
]

KARAOKE = [
    "Never gonna give you up~",
    "Never gonna let you down~",
    "Never gonna run around and desert you~",
    "♪ (audience is one person eating chips) ♪",
]

DEBATE_A = [
    "FOR: because vibes.",
    "FOR: my uncle's friend's cousin agrees.",
    "FOR: I saw a TikTok.",
]
DEBATE_B = [
    "AGAINST: because counter‑vibes.",
    "AGAINST: science (citation needed).",
    "AGAINST: the council of me said no.",
]

COURT_FRAMES = [
    "Court is now in session.",
    "The accused: {name}",
    "Charge: crimes against the vibe.",
    "Evidence: screenshots (fabricated with love).",
    "Jury: twelve raccoons in ties.",
    "Verdict: GUILTY of being iconic anyway.",
    "Sentence: community service in this chat.",
]

PODCAST = [
    "**[INTRO STING]** Welcome to *Unsolicited Opinions*…",
    "Today's guest: {name}, expert in nothing and everything.",
    "Host: So… thoughts?\n{name}: It's giving… situation.",
    "Host: Deep. Sponsor later. Trauma now.",
    "**[OUTRO]** Like, subscribe, emotionally detach.",
]

RECAP = [
    "Previously on this chat…",
    "Someone said something.",
    "Someone else said 'same'.",
    "A meme was deployed. Casualties: context.",
    "And then {name} entered… forever changing the lore.",
]

NPCS = [
    "A bard named Greg who only sings Windows startup sounds.",
    "A mysterious stranger selling 'authentic' Wi‑Fi.",
    "An owl accountant demanding your browser history.",
    "A sentient vending machine named Debts.",
    "Your evil twin, but they hydrate.",
]

QUEST_FRAMES = [
    "You enter the Dungeon of Mild Inconvenience.",
    "A goblin offers you a side quest: reply to that text.",
    "You choose violence (politely).",
    "Boss fight: Capcha of Destiny.",
    "Victory! Loot: +3 charisma, −1 dignity, a lukewarm soda.",
]

ADS = [
    "**AD BREAK**\nThis chaos brought to you by Hydrate™ — water, but make it branded.",
    "**SPONSOR**\nNordVPN can't save your group chat. We tried.",
    "**AD**\nRaid… your snack drawer. Use code: KITTY.",
]

PLOT_ARMOR = [
    "The building explodes—",
    "Cut to: {name} behind a conveniently placed fruit cart.",
    "Bullet time. Hair perfect.",
    "They walk away in slow motion.",
    "Credits: 'No vibes were harmed (much).'",
]

LOOT_REWARDS = [
    "a legendary sock (unmatched)",
    "the Sword of Mild Sass +2",
    "3 unused apology drafts",
    "a coupon for one free ego death",
    "Plot Armor (cracked, still works)",
    "the Helm of Leaving on Read",
]

BUFFER_TIPS = [
    "Pro tip: if it's buffering, so is your life.",
    "Loading personality… 14%",
    "Downloading charm pack… corrupted",
    "Please insert coin to continue existing",
    "Reconnecting to main character server…",
]
