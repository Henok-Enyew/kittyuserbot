# State Management for AI Assistant
import time
from typing import Set, Dict, Optional
from collections import defaultdict


class AIState:
    """
    Manages AI assistant state across chats.
    Tracks enabled chats, known chats, cooldowns, and user style.
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

        # ── AI AFK state (separate from the built-in .afk system) ──────────
        self.aiafk_enabled: bool = False
        self.aiafk_reason: Optional[str] = None

        # ── AI PM Permit state ───────────────────────────────────────────────
        self.aipmpermit_enabled: bool = False
        self.approved_users: Set[int] = set()   # users allowed through normally
        self.pending_users: Set[int] = set()    # users currently in AI-gated conversation
        # ────────────────────────────────────────────────────────────────────

        # Configuration
        self.cooldown_seconds: int = 5   # Minimum seconds between responses
        self.max_history_per_chat: int = 10
        self.max_style_examples: int = 20

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

    def approve_user(self, user_id: int):
        self.approved_users.add(user_id)
        self.pending_users.discard(user_id)

    def disapprove_user(self, user_id: int):
        self.approved_users.discard(user_id)

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

    def get_history(self, chat_id: int) -> list:
        return self.conversation_history[chat_id]

    def clear_history(self, chat_id: int):
        self.conversation_history.pop(chat_id, None)

    # ── Style learning ────────────────────────────────────────────────────

    def add_user_style_example(self, message: str):
        if message and len(message.strip()) > 5:
            self.user_style_examples.append(message)
            if len(self.user_style_examples) > self.max_style_examples:
                self.user_style_examples = self.user_style_examples[-self.max_style_examples:]

    def get_style_examples(self, limit: int = 5) -> list:
        return self.user_style_examples[-limit:] if self.user_style_examples else []


# Global singleton
ai_state = AIState()
