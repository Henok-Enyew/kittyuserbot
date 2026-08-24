# State Management for AI Assistant
import time
from typing import Set, Dict, Optional, List
from collections import defaultdict


class AIState:
    """
    Manages AI assistant state across chats.
    Tracks enabled chats, known chats, cooldowns, and user style.
    Chat history, style examples, and friends persist to Postgres when available.
    """

    def __init__(self):
        # Global AI toggle
        self.global_enabled: bool = False

        # Per-chat AI toggles
        self.enabled_chats: Set[int] = set()   # explicitly ON
        self.disabled_chats: Set[int] = set()  # explicitly OFF (overrides global)

        # Track known chats (for first-time greeting)
        self.known_chats: Set[int] = set()

        # Cooldown tracking (chat_id -> last_response_time)
        self.last_response_time: Dict[int, float] = {}

        # Conversation context (chat_id -> list of recent messages)
        self.conversation_history: Dict[int, list] = defaultdict(list)

        # User style examples (recent messages sent by user)
        self.user_style_examples: list = []

        # Friend memory: list of {"name", "note"}
        self.friends: List[Dict[str, str]] = []
        self.max_friends: int = 30

        # Owner personal notes: list of {"topic", "content"}
        self.owner_notes: List[Dict[str, str]] = []
        self.max_owner_notes: int = 100

        # ── AI AFK state (separate from the built-in .afk system) ──────────
        self.aiafk_enabled: bool = False
        self.aiafk_reason: Optional[str] = None

        # ── AI PM Permit state ───────────────────────────────────────────────
        self.aipmpermit_enabled: bool = False
        self.approved_users: Set[int] = set()   # users allowed through normally
        self.pending_users: Set[int] = set()    # users currently in AI-gated conversation
        self._load_approved_users()  # Load from database on init
        # ────────────────────────────────────────────────────────────────────

        # ── AI Provider Management ───────────────────────────────────────────
        self.current_provider: str = "mistral"  # default provider
        # ────────────────────────────────────────────────────────────────────

        # Configuration
        self.cooldown_seconds: int = 5   # Minimum seconds between responses
        self.max_history_per_chat: int = 10
        self.max_style_examples: int = 20

        # Persistable memory (soft-fail if DB unavailable)
        self._load_persisted_memory()

    def _load_approved_users(self):
        """Load approved users from database on startup."""
        try:
            from userbot.sql_helper.ai_pmpermit_sql import get_all_ai_approved
            approved = get_all_ai_approved()
            if approved:
                self.approved_users = {int(user.user_id) for user in approved}
        except Exception:
            # Database might not be available yet or table doesn't exist
            pass

    def _load_persisted_memory(self):
        """Load chat history, style examples, and friends from Postgres."""
        try:
            from userbot.sql_helper import ai_memory_sql as mem

            history = mem.load_all_history(self.max_history_per_chat)
            if history:
                for chat_id, msgs in history.items():
                    self.conversation_history[chat_id] = list(msgs)
                    self.known_chats.add(chat_id)

            styles = mem.load_style_examples(self.max_style_examples)
            if styles:
                self.user_style_examples = list(styles)

            friends = mem.load_friends(self.max_friends)
            if friends:
                self.friends = list(friends)

            from userbot.sql_helper import owner_notes_sql as notes_sql

            notes = notes_sql.load_owner_notes(self.max_owner_notes)
            if notes:
                self.owner_notes = list(notes)
        except Exception:
            pass

    # ── Global / per-chat toggles ──────────────────────────────────────────

    def is_enabled(self, chat_id: int) -> bool:
        """
        Priority (highest → lowest):
          1. Chat explicitly disabled  → OFF
          2. Chat explicitly enabled   → ON
          3. Global AI on              → ON
          4. AI AFK on                 → ON
          5. Default                   → OFF
        """
        if chat_id in self.disabled_chats:
            return False
        if chat_id in self.enabled_chats:
            return True
        if self.global_enabled:
            return True
        if self.aiafk_enabled:
            return True
        return False

    def enable_global(self):
        self.global_enabled = True

    def disable_global(self):
        self.global_enabled = False

    def enable_chat(self, chat_id: int):
        """Explicitly enable a chat (removes any explicit disable)."""
        self.disabled_chats.discard(chat_id)
        self.enabled_chats.add(chat_id)

    def disable_chat(self, chat_id: int):
        """Explicitly disable a chat (overrides global and per-chat enable)."""
        self.enabled_chats.discard(chat_id)
        self.disabled_chats.add(chat_id)

    # ── AI AFK ────────────────────────────────────────────────────────────

    def enable_aiafk(self, reason: Optional[str] = None):
        """Enable AI AFK mode with an optional reason."""
        self.aiafk_enabled = True
        self.aiafk_reason = reason or None

    def disable_aiafk(self):
        """Disable AI AFK mode and clear the reason."""
        self.aiafk_enabled = False
        self.aiafk_reason = None

    # ── AI PM Permit ──────────────────────────────────────────────────────

    def enable_aipmpermit(self):
        self.aipmpermit_enabled = True

    def disable_aipmpermit(self):
        self.aipmpermit_enabled = False

    def is_approved(self, user_id: int) -> bool:
        return user_id in self.approved_users

    def approve_user(self, user_id: int, first_name: str = None, username: str = None):
        """Approve a user and save to database."""
        self.approved_users.add(user_id)
        self.pending_users.discard(user_id)
        # Persist to database
        try:
            from userbot.sql_helper.ai_pmpermit_sql import ai_approve
            ai_approve(user_id, first_name, username)
        except Exception:
            pass  # Non-critical if database fails

    def disapprove_user(self, user_id: int):
        """Remove approval and delete from database."""
        self.approved_users.discard(user_id)
        # Remove from database
        try:
            from userbot.sql_helper.ai_pmpermit_sql import ai_disapprove
            ai_disapprove(user_id)
        except Exception:
            pass  # Non-critical if database fails

    def mark_pending(self, user_id: int):
        self.pending_users.add(user_id)

    def is_pending(self, user_id: int) -> bool:
        return user_id in self.pending_users

    # ── Known chats ───────────────────────────────────────────────────────

    def is_new_chat(self, chat_id: int) -> bool:
        return chat_id not in self.known_chats

    def mark_chat_known(self, chat_id: int):
        self.known_chats.add(chat_id)

    # ── Cooldown ──────────────────────────────────────────────────────────

    def can_respond(self, chat_id: int) -> bool:
        if chat_id not in self.last_response_time:
            return True
        return (time.time() - self.last_response_time[chat_id]) >= self.cooldown_seconds

    def mark_response(self, chat_id: int):
        self.last_response_time[chat_id] = time.time()

    # ── Conversation history ──────────────────────────────────────────────

    def add_to_history(self, chat_id: int, role: str, content: str):
        self.conversation_history[chat_id].append({"role": role, "content": content})
        if len(self.conversation_history[chat_id]) > self.max_history_per_chat:
            self.conversation_history[chat_id] = (
                self.conversation_history[chat_id][-self.max_history_per_chat:]
            )
        try:
            from userbot.sql_helper.ai_memory_sql import append_history
            append_history(chat_id, role, content, self.max_history_per_chat)
        except Exception:
            pass

    def get_history(self, chat_id: int) -> list:
        return self.conversation_history[chat_id]

    def clear_history(self, chat_id: int):
        self.conversation_history.pop(chat_id, None)
        try:
            from userbot.sql_helper.ai_memory_sql import clear_history_db
            clear_history_db(chat_id)
        except Exception:
            pass

    # ── Style learning ────────────────────────────────────────────────────

    def add_user_style_example(self, message: str):
        if message and len(message.strip()) > 5:
            self.user_style_examples.append(message)
            if len(self.user_style_examples) > self.max_style_examples:
                self.user_style_examples = self.user_style_examples[-self.max_style_examples:]
            try:
                from userbot.sql_helper.ai_memory_sql import append_style_example
                append_style_example(message, self.max_style_examples)
            except Exception:
                pass

    def get_style_examples(self, limit: int = 5) -> list:
        return self.user_style_examples[-limit:] if self.user_style_examples else []

    # ── Friend memory ─────────────────────────────────────────────────────

    def add_friend(self, name: str, note: str = "") -> bool:
        """Remember a friend name (RAM + DB)."""
        if not name or not name.strip():
            return False
        display = name.strip()
        key = display.lower()
        for f in self.friends:
            if f.get("name", "").lower() == key:
                if note:
                    f["note"] = note
                try:
                    from userbot.sql_helper.ai_memory_sql import upsert_friend
                    upsert_friend(display, note or f.get("note", ""), self.max_friends)
                except Exception:
                    pass
                return True
        self.friends.append({"name": display, "note": note or ""})
        if len(self.friends) > self.max_friends:
            self.friends = self.friends[-self.max_friends:]
        try:
            from userbot.sql_helper.ai_memory_sql import upsert_friend
            upsert_friend(display, note or "", self.max_friends)
        except Exception:
            pass
        return True

    def get_friends(self) -> List[Dict[str, str]]:
        return list(self.friends)

    def forget_friend(self, name: str) -> bool:
        if not name:
            return False
        key = name.strip().lower()
        before = len(self.friends)
        self.friends = [f for f in self.friends if f.get("name", "").lower() != key]
        try:
            from userbot.sql_helper.ai_memory_sql import delete_friend
            delete_friend(name)
        except Exception:
            pass
        return len(self.friends) < before

    # ── Owner notes (.remember) ───────────────────────────────────────────

    def add_owner_note(self, topic: str, content: str) -> bool:
        if not topic or not content:
            return False
        key = topic.strip().lower()
        for note in self.owner_notes:
            if note.get("topic", "").lower() == key:
                note["content"] = content.strip()
                note["topic"] = topic.strip()
                self._persist_owner_note(topic, content)
                return True
        self.owner_notes.append({"topic": topic.strip(), "content": content.strip()})
        if len(self.owner_notes) > self.max_owner_notes:
            self.owner_notes = self.owner_notes[-self.max_owner_notes :]
        self._persist_owner_note(topic, content)
        return True

    def _persist_owner_note(self, topic: str, content: str):
        try:
            from userbot.sql_helper.owner_notes_sql import upsert_note

            upsert_note(topic, content, self.max_owner_notes)
        except Exception:
            pass

    def get_owner_notes(self, limit: int = 15) -> List[Dict[str, str]]:
        return self.owner_notes[-limit:] if self.owner_notes else []

    def recall_owner_note(self, topic: str) -> Optional[Dict[str, str]]:
        try:
            from userbot.sql_helper.owner_notes_sql import find_note

            found = find_note(topic)
            if found:
                return found
        except Exception:
            pass
        key = (topic or "").strip().lower()
        for note in self.owner_notes:
            if key in note.get("topic", "").lower():
                return note
        return None

    def delete_owner_note(self, topic: str) -> bool:
        key = (topic or "").strip().lower()
        before = len(self.owner_notes)
        self.owner_notes = [
            n for n in self.owner_notes if n.get("topic", "").lower() != key
        ]
        try:
            from userbot.sql_helper.owner_notes_sql import delete_note

            delete_note(topic)
        except Exception:
            pass
        return len(self.owner_notes) < before

    def reload_owner_notes(self):
        try:
            from userbot.sql_helper import owner_notes_sql as notes_sql

            notes = notes_sql.load_owner_notes(self.max_owner_notes)
            if notes:
                self.owner_notes = list(notes)
        except Exception:
            pass

    # ── AI Provider Management ────────────────────────────────────────────

    def set_provider(self, provider_name: str) -> bool:
        """Set the current AI provider."""
        provider_name = provider_name.lower()
        valid_providers = ["mistral", "nvidia"]
        if provider_name not in valid_providers:
            return False
        self.current_provider = provider_name
        return True

    def get_provider(self) -> str:
        """Get the current AI provider name."""
        return self.current_provider


# Global singleton
ai_state = AIState()
