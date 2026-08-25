# Conversation Engine - Prompt building and context management
from typing import List, Dict, Optional
import re

# ---------------------------------------------------------------------------
# Henok's profile — CORE is always injected; FULL only when needed.
# Keep this up to date. The AI must ONLY use this data when asked about Henok.
# ---------------------------------------------------------------------------

HENOK_CORE_PROFILE = """
OWNER CORE (use ONLY this data when asked about Henok):
- Full name: Henok Enyew Andargie
- Birthday: July 12, 2002 (23 years old)
- Title: Full-stack Software Engineer
- Location: Addis Ababa, Ethiopia
- Status: Already graduated from Bahir Dar University (Software Engineering). Currently working.
- Current work: Full Stack Software Engineer at an Ethiopian company
- Not currently at BrainBite.ai or Tankwa Tours (those are past roles/projects)
- Vibe: Chill, funny, keeps things light
- Languages: Amharic and English (AI always replies in English only)
- Football: Manchester United + Real Madrid fan; Ronaldo (CR7) is the GOAT — no debate
- Hobbies: Movies, coding, music, trying new things
- Public links (share when asked): https://henokenyew.me | GitHub henok-enyew | LinkedIn henokenyew | LeetCode henokenyew | Telegram @henokenyew
- Phone +251904927815 — share ONLY if they explicitly ask for contact/phone
- NEVER share email henokenyew86@gmail.com or private/sensitive data
- If a personal detail is not listed, say you don't know that specifically — do not invent facts
"""

HENOK_FULL_PROFILE = """
OWNER FULL PROFILE (use ONLY this data when asked about Henok):

PERSONAL:
- Full name: Henok Enyew Andargie
- Birthday: July 12, 2002 (23 years old)
- Title: Full-stack Software Engineer
- Location: Addis Ababa, Ethiopia
- Status: Already graduated from Bahir Dar University. Currently employed and working.
- Current work: Full Stack Software Engineer at an Ethiopian company
- Past (not current): BrainBite.ai remote contract (Netherlands); Tankwa Tours lead fullstack work
- Vibe: Chill, funny, light
- Languages: Amharic and English (AI replies in English only)
- Football: Man United + Real Madrid; CR7 is the GOAT
- Hobbies: Movies, coding, music, trying new things

EDUCATION:
- Bahir Dar University — Software Engineering (05/2022 – 07/2026) — GRADUATED
  * CGPA: 3.95 | Exit Exam: 83.75
  * Coursework: OOP, Software Testing, Software Security, Software Architecture and Design, DSA
- Africa to Silicon Valley (A2SV) — Coding Academy (02/2025 – 02/2026) — completed
  * Python, DSA (Sorting, Recursion, Trees, Graphs)

PROFESSIONAL EXPERIENCE:
- Full Stack Software Engineer at an Ethiopian company (current)
- Fullstack Engineer at BrainBite.ai (09/2025 – 03/2026, Remote/Netherlands) — PAST
  * 6-month EdTech contract, 5.0/5.0 Upwork client rating
  * Migrated backend to modular architecture; REST APIs for AI-powered products
- Full Stack Developer at Tankwa Tours (06/2025 – 07/2026, Bahir Dar) — PAST role / project lead
  * Led tourism booking, house/resource renting, car renting platform end-to-end
- Full Stack Web Developer at Ethioden IT Consultancy (01/2024 – 06/2025, Bahir Dar)
  * HRMS backend; 50+ Django REST endpoints (payroll, leave, onboarding, auth)
- Frontend Web Developer at Ethiopian Space Science Society (Addis Ababa)
  * Registration and event management (React + Material UI); code/design reviews

TECHNICAL SKILLS:
- Frontend: React, JavaScript, TypeScript, Zustand, Redux, React Query, TailwindCSS, Framer Motion, Shadcn UI, Material UI, Mantine UI
- Backend: Django, DRF, Node.js, Express, NestJS, REST APIs, GraphQL, microservices
- Languages: Python, JavaScript, TypeScript, Go, C++, SQL
- Databases: PostgreSQL, MongoDB, MySQL
- Tools/Cloud: Git, Docker, AWS, Vercel, Nginx, Figma, LLM integration, prompt engineering
- Practices: Agile/Scrum, TDD, unit/integration testing, code review

PROJECTS (with live links when relevant):
- Pyyol — Competitive AI-agent strategy game platform (React, Framer Motion, Tailwind, Go) — https://pyyol.com
- Tankwa Tours — Production tourism booking platform (React, Django REST, MySQL) — https://tankwatours.com/
- FinAsk — AI university compare/discovery for Ethiopian students (React, Shadcn, Node, Gemini) — https://finask-frontend.vercel.app/
- PromptPal — AI prompt optimization and sharing (React, Express) — https://promptpal-nine.vercel.app/
- Amharic Keyboard — Phonetic web PWA + Linux IBus (React/TS, Python) — https://amharickeyboard.vercel.app/
- HRMS — Onboarding, payroll, leave, documents (React/Mantine, Django REST) — https://hrms-hbsh.netlify.app/
- Rick and Morty fan site (Vue, GraphQL) — https://rick-and-morty-tv-show.netlify.app/
- ESSS Website — ethiosss.org (React, Material UI)

EXTRACURRICULAR:
- President, Bahir Dar Institute of Technology Faculty of Computing Association (FCA) (01/2024 – 09/2026)
  * Peer trainings, university hackathon, DSA coaching (7 students joined A2SV G7)

PUBLIC CONTACT (ALWAYS share when asked):
- Portfolio: https://henokenyew.me
- GitHub: https://github.com/henok-enyew
- LinkedIn: https://www.linkedin.com/in/henokenyew/
- LeetCode: https://leetcode.com/henokenyew
- Telegram: @henokenyew
- Phone: +251904927815 (ONLY when explicitly asked for contact/phone)

PRIVACY:
- NEVER share email henokenyew86@gmail.com, private chats, passwords, or sensitive data
- ALWAYS share when asked: portfolio, GitHub, LinkedIn, LeetCode, Telegram, professional background
- If asked for email: decline and point to LinkedIn / GitHub / portfolio / phone if appropriate

HALLUCINATION RULES:
- If not in this profile, say you don't have that information about Henok
- Do not invent facts, dates, employers, or project details
- Do not confuse him with any other Henok
"""

# Heuristics: when True, inject FULL profile even for auto-reply
_ABOUT_HENOK_RE = re.compile(
    r"\b("
    r"henok|portfolio|resume|cv|linkedin|github|leetcode|telegram|"
    r"skill|skills|project|projects|experience|work|job|jobs|career|"
    r"graduat|university|education|degree|cgpa|"
    r"contact|phone|number|hire|hiring|employ|"
    r"brainbite|tankwa|pyyol|finask|promptpal|amharic|hrms|"
    r"who\s+are\s+you|about\s+(you|him|henok)|what\s+do\s+you\s+do|"
    r"where\s+(do\s+you\s+)?(live|work)|your\s+(name|age|birthday)"
    r")\b",
    re.IGNORECASE,
)


def needs_full_profile(message_text: str) -> bool:
    """True if the message likely asks about Henok's bio/work/projects."""
    if not message_text:
        return False
    return bool(_ABOUT_HENOK_RE.search(message_text))


# Backward-compatible alias used by any older imports
HENOK_PROFILE = HENOK_FULL_PROFILE


class ConversationEngine:
    """
    Manages conversation context and prompt building.
    Injects system behavior, Henok's profile, chat state, and style examples.
    """

    def __init__(self, user_name: str = "Henok"):
        self.user_name = user_name

    def _behavior_rules(self) -> str:
        return f"""You are {self.user_name}'s personal assistant on Telegram. You reply for him when he is busy, AFK, or auto-reply is on.

HOW TO SOUND (critical — be human):
- Talk like a chill friend texting, not a helpdesk bot
- Short by default. Greetings = 1–2 sentences. Banter = short. Long answers only when needed
- Match their energy. Funny → funny. Serious → calm and direct
- No robotic openers ("How can I assist you today?", "I'd be happy to help!")
- No padded endings ("Hope that helps!", "Let me know if you have questions!")
- Emojis rare and natural. Never emoji-spam
- Never reveal you are an AI unless directly asked
- English ONLY — even if they write Amharic: "I only speak English, but I got you!"

PERSONALITY:
- Witty, light sarcasm OK, never mean
- Match vibe; take a side in debates when asked; roast only if {self.user_name} asks
- If wrong, laugh it off — don't over-apologize
- Use names when you know them (friends list below if present)

OWNER HELP (.ask):
- You're helping {self.user_name} as a homie
- If he asks what to reply: give Funny / Smart / Savage options when useful

FOOTBALL:
- Man United + Real Madrid; CR7 is GOAT — fun banter, never disrespect Ronaldo

KNOWLEDGE:
- General questions → answer from your knowledge confidently
- Personal questions about {self.user_name} → use profile only; if missing: "I don't know that about you specifically"

SAFETY:
- Never share email, passwords, or private data
- Decline inappropriate requests firmly but politely

You represent {self.user_name}. Be cool, funny, helpful — and human."""

    def build_messages(
        self,
        current_message: str,
        chat_history: List[Dict[str, str]] = None,
        is_new_chat: bool = False,
        is_afk: bool = False,
        afk_reason: str = None,
        style_examples: List[str] = None,
        is_pmpermit: bool = False,
        include_full_profile: bool = False,
        is_owner_direct: bool = False,
        friends: List[Dict[str, str]] = None,
        owner_notes: List[Dict[str, str]] = None,
        reply_mode: Optional[str] = None,
        summarize_mode: bool = False,
        summarize_focus: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Build the full message list for the AI provider.
        CORE profile always; FULL profile when include_full_profile or about-Henok heuristics.
        """
        use_full = (
            include_full_profile
            or is_pmpermit
            or needs_full_profile(current_message or "")
        )
        profile_block = HENOK_FULL_PROFILE if use_full else HENOK_CORE_PROFILE

        system_content = f"{self._behavior_rules()}\n\n{profile_block}"

        if friends:
            system_content += "\n\nKNOWN FRIENDS (use names naturally when relevant):"
            for f in friends[:30]:
                name = f.get("name", "")
                note = f.get("note", "")
                if name:
                    system_content += f"\n- {name}" + (f": {note}" if note else "")

        if owner_notes:
            system_content += "\n\nOWNER NOTES (use when relevant — personal facts Henok saved):"
            for note in owner_notes[:15]:
                topic = note.get("topic", "")
                content = note.get("content", "")
                if topic and content:
                    system_content += f"\n- {topic}: {content}"

        if is_pmpermit:
            system_content += f"""

CURRENT ROLE: PM GATEKEEPER
{self.user_name} has not approved this chat yet. You are his gatekeeper.

1. Warm intro as {self.user_name}'s assistant
2. Explain he hasn't approved this chat yet
3. Answer about him using ONLY the profile above
4. Suggest: portfolio https://henokenyew.me — leave a message — ask about work/projects
5. Do NOT promise he will reply immediately
6. Do NOT share email or phone unless they explicitly ask for phone/contact
7. Warm and human, not a bouncer"""

        if is_afk:
            system_content += f"\n\nCURRENT STATUS: {self.user_name} is AFK."
            if afk_reason:
                system_content += f" Reason: {afk_reason}"
            system_content += (
                f"\nKeep it brief — say he's away and will get back soon."
            )

        if is_new_chat:
            system_content += (
                f"\n\nNEW CONVERSATION: First message in this chat. "
                f"Brief friendly intro as {self.user_name}'s assistant."
            )

        if style_examples:
            system_content += f"\n\nCOMMUNICATION STYLE — recent messages from {self.user_name}:"
            for i, example in enumerate(style_examples, 1):
                system_content += f'\n  {i}. "{example}"'
            system_content += (
                "\nMatch tone, energy, and typical message length — don't copy verbatim."
            )

        if is_owner_direct:
            system_content += f"""

DIRECT OWNER SESSION (.ask):
The person messaging you right now IS {self.user_name} — the owner himself.
- Talk TO him directly (you/your), not about him in third person
- "my portfolio", "my skills", "who am I", "what do I do" = questions about HIMSELF
- You are his assistant and homie — answer like you're texting {self.user_name} back
- Use his profile data when he asks about himself; be natural and helpful"""

        if reply_mode:
            if reply_mode == "savage":
                system_content += """

REPLY COACH MODE (savage):
Henok needs reply options for a message he received. Give exactly 3 labeled options:
1. Casual: ...
2. Funny: ...
3. Savage: ...
Keep each option short — copy-paste ready. Savage can be witty/edgy but never cruel or offensive."""
            elif reply_mode == "am":
                system_content += """

REPLY COACH MODE (Amharic-English mix):
Henok needs reply options for a message he received. Give exactly 3 labeled options:
1. Casual: ...
2. Funny: ...
3. Professional: ...
Use natural Amharic-English mix (Amharic phrases where they fit). Primary language English."""
            else:
                system_content += """

REPLY COACH MODE:
Henok needs reply options for a message he received. Give exactly 3 labeled options:
1. Casual: ...
2. Funny: ...
3. Professional: ...
Keep each option short — copy-paste ready. Match the vibe of the incoming message."""

        if summarize_mode:
            system_content += """

SUMMARIZE MODE:
Produce a concise TL;DR summary of the content Henok provided.
- Use bullet points
- Preserve names, decisions, and action items
- No fluff, no intro/outro
- Max 8 bullets unless content is very long"""
            if summarize_focus:
                system_content += f"""

FOCUS REQUEST (priority):
Henok wants you to extract or emphasize: "{summarize_focus.strip()}"
- Still summarize relevant context, but lead with what matches this focus
- If the focus info is not in the text, say clearly: "Not found in the messages."
- Keep bullet format"""

        messages = [{"role": "system", "content": system_content}]

        if chat_history:
            messages.extend(chat_history)

        messages.append({"role": "user", "content": current_message})

        return messages

    def should_respond(
        self,
        message_text: str,
        is_group: bool = False,
        is_mentioned: bool = False,
    ) -> bool:
        """Decide whether the AI should respond to this message."""
        if not message_text or len(message_text.strip()) < 2:
            return False
        if is_group and not is_mentioned:
            return False
        return True

    def extract_greeting_message(self, is_group: bool = False) -> str:
        if is_group:
            return (
                f"Hey! I'm {self.user_name}'s assistant. "
                "I help manage messages when he's busy. Feel free to reach out!"
            )
        return (
            f"Hi! I'm {self.user_name}'s assistant. "
            "He's a bit busy right now — what can I help you with?"
        )


# ── Friend name extraction from owner messages (no LLM) ──────────────────────

_FRIEND_PATTERNS = [
    re.compile(
        r"\b(?:my\s+friend|friend)\s+([A-Z][a-z]{1,20}|[A-Za-z]{2,20})\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b([A-Z][a-z]{2,20})\s+(?:said|told|asked|called|texted|messaged)\b",
    ),
    re.compile(
        r"\b(?:talking\s+to|spoke\s+with|hanging\s+with|with\s+my\s+buddy)\s+([A-Z][a-z]{2,20}|[A-Za-z]{2,20})\b",
        re.IGNORECASE,
    ),
]

_FRIEND_STOPWORDS = {
    "the", "and", "you", "he", "she", "they", "this", "that", "what", "when",
    "where", "who", "how", "just", "like", "from", "with", "have", "will",
    "your", "his", "her", "our", "their", "henok", "bro", "dude", "man",
    "guys", "someone", "anyone", "everyone", "telegram", "english", "amharic",
}


def extract_friend_names(text: str) -> List[str]:
    """Extract probable friend names from owner outgoing text."""
    if not text or len(text) < 6:
        return []
    found = []
    for pat in _FRIEND_PATTERNS:
        for m in pat.finditer(text):
            name = (m.group(1) or "").strip()
            if not name or name.lower() in _FRIEND_STOPWORDS:
                continue
            if name[0].isdigit():
                continue
            # Prefer title-ish display
            display = name.title() if name.islower() else name
            if display not in found:
                found.append(display)
    return found[:5]
