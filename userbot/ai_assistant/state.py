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
        
        # Per-chat AI toggle
        self.enabled_chats: Set[int] = set()
        
        # Track known chats (for first-time greeting)
        self.known_chats: Set[int] = set()
        
        # Cooldown tracking (chat_id -> last_response_time)
        self.last_response_time: Dict[int, float] = {}
        
        # Conversation context (chat_id -> list of recent messages)
        self.conversation_history: Dict[int, list] = defaultdict(list)
        
        # User style examples (recent messages sent by user)
        self.user_style_examples: list = []
        
        # Configuration
        self.cooldown_seconds: int = 5  # Minimum time between responses
        self.max_history_per_chat: int = 10  # Keep last N messages
        self.max_style_examples: int = 20  # Keep last N user messages
    
    def is_enabled(self, chat_id: int) -> bool:
        """Check if AI is enabled for a chat"""
        return self.global_enabled or chat_id in self.enabled_chats
    
    def enable_global(self):
        """Enable AI globally"""
        self.global_enabled = True
    
    def disable_global(self):
        """Disable AI globally"""
        self.global_enabled = False
    
    def enable_chat(self, chat_id: int):
        """Enable AI for specific chat"""
        self.enabled_chats.add(chat_id)
    
    def disable_chat(self, chat_id: int):
        """Disable AI for specific chat"""
        self.enabled_chats.discard(chat_id)
    
    def is_new_chat(self, chat_id: int) -> bool:
        """Check if this is a new chat (first interaction)"""
        return chat_id not in self.known_chats
    
    def mark_chat_known(self, chat_id: int):
        """Mark chat as known"""
        self.known_chats.add(chat_id)
    
    def can_respond(self, chat_id: int) -> bool:
        """Check if enough time has passed since last response (anti-spam)"""
        if chat_id not in self.last_response_time:
            return True
        
        elapsed = time.time() - self.last_response_time[chat_id]
        return elapsed >= self.cooldown_seconds
    
    def mark_response(self, chat_id: int):
        """Mark that we responded in this chat"""
        self.last_response_time[chat_id] = time.time()
    
    def add_to_history(self, chat_id: int, role: str, content: str):
        """Add message to conversation history"""
        self.conversation_history[chat_id].append({
            "role": role,
            "content": content
        })
        
        # Keep only recent messages
        if len(self.conversation_history[chat_id]) > self.max_history_per_chat:
            self.conversation_history[chat_id] = self.conversation_history[chat_id][-self.max_history_per_chat:]
    
    def get_history(self, chat_id: int) -> list:
        """Get conversation history for a chat"""
        return self.conversation_history[chat_id]
    
    def clear_history(self, chat_id: int):
        """Clear conversation history for a chat"""
        if chat_id in self.conversation_history:
            del self.conversation_history[chat_id]
    
    def add_user_style_example(self, message: str):
        """Add user's message as style example"""
        if message and len(message.strip()) > 5:  # Ignore very short messages
            self.user_style_examples.append(message)
            
            # Keep only recent examples
            if len(self.user_style_examples) > self.max_style_examples:
                self.user_style_examples = self.user_style_examples[-self.max_style_examples:]
    
    def get_style_examples(self, limit: int = 5) -> list:
        """Get recent user style examples"""
        return self.user_style_examples[-limit:] if self.user_style_examples else []


# Global state instance
ai_state = AIState()
