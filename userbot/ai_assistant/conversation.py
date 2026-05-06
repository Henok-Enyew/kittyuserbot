# Conversation Engine - Prompt building and context management
from typing import List, Dict, Optional


class ConversationEngine:
    """
    Manages conversation context and prompt building.
    Injects system behavior, chat state, and user style.
    """
    
    def __init__(self, user_name: str = "Henok"):
        self.user_name = user_name
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build the core system prompt"""
        return f"""You are {self.user_name}'s personal AI assistant integrated into their Telegram account.

CORE IDENTITY:
- You respond on behalf of {self.user_name}
- You are helpful, concise, and natural
- You sound like a real human, not a bot
- You adapt to {self.user_name}'s communication style

BEHAVIOR RULES:
1. Be concise by default - expand only when necessary
2. Use natural, conversational language
3. Avoid robotic phrases like "How can I assist you today?"
4. Ask follow-up questions when context is unclear
5. Show personality - be warm but professional
6. Never reveal you are an AI unless directly asked

RESPONSE GUIDELINES:
- Short messages deserve short replies
- Match the tone and energy of the conversation
- Use emojis sparingly and naturally
- Avoid over-explaining simple things
- Be direct and honest

SAFETY:
- Never share sensitive information
- Decline inappropriate requests politely
- Stay respectful and professional

Remember: You ARE {self.user_name}'s assistant, not a separate entity. Respond as if you're helping {self.user_name} communicate."""
    
    def build_messages(
        self,
        current_message: str,
        chat_history: List[Dict[str, str]] = None,
        is_new_chat: bool = False,
        is_afk: bool = False,
        afk_reason: str = None,
        style_examples: List[str] = None
    ) -> List[Dict[str, str]]:
        """
        Build complete message list for AI provider.
        
        Args:
            current_message: The message to respond to
            chat_history: Recent conversation history
            is_new_chat: Is this the first message in this chat?
            is_afk: Is user in AFK mode?
            afk_reason: AFK reason if applicable
            style_examples: Examples of user's writing style
            
        Returns:
            List of messages formatted for AI provider
        """
        messages = []
        
        # System prompt with context
        system_content = self.system_prompt
        
        # Add AFK context
        if is_afk:
            afk_context = f"\n\nCURRENT STATUS: {self.user_name} is currently AFK (Away From Keyboard)."
            if afk_reason:
                afk_context += f"\nReason: {afk_reason}"
            afk_context += f"\nRespond briefly acknowledging {self.user_name} is away and will get back to them."
            system_content += afk_context
        
        # Add new chat context
        if is_new_chat:
            new_chat_context = f"\n\nNEW CHAT DETECTED: This is the first interaction in this chat. Introduce yourself briefly as {self.user_name}'s assistant."
            system_content += new_chat_context
        
        # Add style examples
        if style_examples:
            style_context = f"\n\nCOMMUNICATION STYLE EXAMPLES from {self.user_name}:\n"
            for i, example in enumerate(style_examples, 1):
                style_context += f"{i}. \"{example}\"\n"
            style_context += f"\nMimic this style in your responses - match the tone, length, and personality."
            system_content += style_context
        
        messages.append({
            "role": "system",
            "content": system_content
        })
        
        # Add conversation history
        if chat_history:
            messages.extend(chat_history)
        
        # Add current message
        messages.append({
            "role": "user",
            "content": current_message
        })
        
        return messages
    
    def should_respond(
        self,
        message_text: str,
        is_group: bool = False,
        is_mentioned: bool = False
    ) -> bool:
        """
        Decide if we should respond to this message.
        
        Args:
            message_text: The message content
            is_group: Is this a group chat?
            is_mentioned: Were we mentioned/tagged?
            
        Returns:
            True if we should respond
        """
        # Ignore very short or empty messages
        if not message_text or len(message_text.strip()) < 2:
            return False
        
        # In groups, only respond if mentioned
        if is_group and not is_mentioned:
            return False
        
        # In private chats, always respond
        if not is_group:
            return True
        
        # In groups with mention, respond
        if is_mentioned:
            return True
        
        return False
    
    def extract_greeting_message(self, is_group: bool = False) -> str:
        """Generate a greeting message for new chats"""
        if is_group:
            return f"Hey! I'm {self.user_name}'s AI assistant. I help manage messages when they're busy. Feel free to reach out!"
        else:
            return f"Hi! I'm {self.user_name}'s assistant. I'm here to help while they're away. What can I do for you?"
