# 🤖 AI Assistant for CatUserbot

A modular, provider-independent AI assistant integrated into your Telegram userbot. Responds naturally on your behalf, learns your communication style, and integrates seamlessly with AFK mode.

---

## 🎯 Features

### Core Capabilities
- ✅ **Auto-respond** to messages on your behalf
- ✅ **Global & per-chat** toggle controls
- ✅ **New chat detection** with automatic greetings
- ✅ **AFK integration** - AI-aware responses when you're away
- ✅ **Style learning** - Mimics your communication patterns
- ✅ **Anti-spam** - Cooldown timers and smart response logic
- ✅ **Human-like behavior** - Typing delays, natural responses

### Provider Independence
- 🔄 **Mistral AI** (primary)
- 🔄 **NVIDIA AI** (future support)
- 🔧 Switch providers with **one config change**

---

## 🏗️ Architecture

```
userbot/
├── ai_assistant/
│   ├── __init__.py              # Module exports
│   ├── providers/
│   │   ├── __init__.py          # Provider factory
│   │   ├── base.py              # Abstract interface
│   │   ├── mistral.py           # Mistral AI implementation
│   │   └── nvidia.py            # NVIDIA AI implementation
│   ├── conversation.py          # Prompt building & context
│   └── state.py                 # State management
└── plugins/
    └── ai_assistant.py          # Main plugin (commands & handlers)
```

### Layer Separation

1. **AI Provider Layer** (`providers/`)
   - Abstract interface for all AI services
   - Easy to add new providers
   - Business logic never touches provider details

2. **Conversation Engine** (`conversation.py`)
   - Builds prompts dynamically
   - Injects context (AFK, new chat, style)
   - Manages conversation flow

3. **State Management** (`state.py`)
   - Tracks enabled chats
   - Conversation history
   - Cooldown timers
   - User style examples

4. **Plugin Layer** (`plugins/ai_assistant.py`)
   - Command handlers
   - Message interceptors
   - Integration with userbot

---

## 🚀 Setup & Installation

### 1. Set Environment Variables

Add these to your environment (Heroku, Railway, or `.env` file):

```bash
# Required
AI_API_KEY=your_mistral_api_key_here

# Optional
AI_PROVIDER=mistral          # or 'nvidia'
ALIVE_NAME=Henok             # Your name (for AI personality)
```

### 2. Get Mistral AI API Key

1. Go to [Mistral AI Console](https://console.mistral.ai/)
2. Sign up / Log in
3. Navigate to **API Keys**
4. Create a new API key
5. Copy and set as `AI_API_KEY`

### 3. Deploy

The AI assistant will automatically load when your userbot starts.

---

## 📖 Commands

### Global Controls

| Command | Description |
|---------|-------------|
| `.ai on` | Enable AI assistant globally (all chats) |
| `.ai off` | Disable AI assistant globally |

### Per-Chat Controls

| Command | Description |
|---------|-------------|
| `.ai enable` | Enable AI for current chat only |
| `.ai disable` | Disable AI for current chat |

### Management

| Command | Description |
|---------|-------------|
| `.ai status` | Show AI configuration and status |
| `.ai clear` | Clear conversation history for current chat |

---

## 🎭 How It Works

### Message Flow

```
Incoming Message
    ↓
Is AI enabled? → No → Ignore
    ↓ Yes
Is sender a bot? → Yes → Ignore
    ↓ No
Should respond? (group/mention logic) → No → Ignore
    ↓ Yes
Cooldown check → Not ready → Ignore
    ↓ Ready
Build context (history, AFK, style)
    ↓
Call AI provider
    ↓
Send response
    ↓
Update state (history, cooldown)
```

### Smart Response Logic

**Private Chats:**
- Always responds when AI is enabled

**Group Chats:**
- Only responds when mentioned/tagged
- Prevents spam in busy groups

**Anti-Spam:**
- 5-second cooldown between responses
- Ignores very short messages
- Simulates human typing delay

### Style Learning

The AI learns from your outgoing messages:
- Captures your tone and personality
- Mimics message length patterns
- Adapts emoji usage
- Keeps last 20 messages as examples

### AFK Integration

When you're AFK (`.afk` command):
- AI detects AFK status automatically
- Responds with AFK-aware messages
- Mentions your AFK reason
- Tells people you'll get back to them

### New Chat Greeting

First message in a new chat:
- AI introduces itself
- Explains it's your assistant
- Sets expectations naturally

---

## 🔧 Configuration

### Cooldown Settings

Edit `userbot/ai_assistant/state.py`:

```python
self.cooldown_seconds = 5        # Time between responses
self.max_history_per_chat = 10   # Messages to remember
self.max_style_examples = 20     # Style examples to keep
```

### AI Parameters

Edit `userbot/plugins/ai_assistant.py`:

```python
response = await provider.generate_response(
    messages=messages,
    temperature=0.8,    # Creativity (0.0-1.0)
    max_tokens=300      # Response length
)
```

### System Prompt

Edit `userbot/ai_assistant/conversation.py` → `_build_system_prompt()`

Customize the AI's personality, behavior rules, and response style.

---

## 🔄 Switching AI Providers

### From Mistral to NVIDIA

1. Get NVIDIA API key from [NVIDIA AI](https://build.nvidia.com/)
2. Update environment variable:
   ```bash
   AI_PROVIDER=nvidia
   AI_API_KEY=your_nvidia_api_key
   ```
3. Restart userbot

**That's it!** No code changes needed.

### Adding New Providers

1. Create `userbot/ai_assistant/providers/your_provider.py`
2. Inherit from `AIProvider` base class
3. Implement `generate_response()` method
4. Register in `providers/__init__.py`

Example:

```python
from .base import AIProvider

class YourProvider(AIProvider):
    def get_provider_name(self) -> str:
        return "Your Provider"
    
    async def generate_response(self, messages, temperature, max_tokens):
        # Your implementation
        return "response"
```

---

## 🧪 Testing

### Test AI Response

1. Enable AI: `.ai on`
2. Send yourself a message from another account
3. AI should respond automatically

### Test Per-Chat

1. In a specific chat: `.ai enable`
2. Send a message
3. AI responds only in that chat

### Test AFK Integration

1. Set AFK: `.afk Testing AI`
2. Get a message
3. AI responds with AFK-aware message

### Test Style Learning

1. Send several messages with your style
2. Check status: `.ai status`
3. AI will mimic your patterns

---

## 🛡️ Safety Features

### Anti-Detection
- Human-like typing delays
- Cooldown between responses
- Natural conversation flow
- Doesn't respond to every message

### Privacy
- No data sent to external servers (except AI provider)
- Conversation history stored locally
- Style examples kept in memory only

### Error Handling
- Graceful API failure handling
- Silent errors (no user-facing crashes)
- Automatic retry logic

---

## 🐛 Troubleshooting

### AI Not Responding

1. Check if enabled: `.ai status`
2. Verify API key is set: `echo $AI_API_KEY`
3. Check logs for errors
4. Ensure cooldown has passed (5 seconds)

### Wrong Provider

```bash
# Check current provider
.ai status

# Switch provider
export AI_PROVIDER=mistral  # or nvidia
```

### API Errors

- **401 Unauthorized**: Invalid API key
- **429 Rate Limit**: Too many requests, wait
- **500 Server Error**: Provider issue, try again

### Style Not Learning

- AI learns from outgoing messages
- Avoid commands (starting with `.`)
- Send at least 5-10 messages
- Check: `.ai status` → Style Examples count

---

## 📊 Performance

### Resource Usage
- **Memory**: ~50MB (conversation history)
- **API Calls**: 1 per response
- **Latency**: 1-3 seconds per response

### Optimization Tips
- Reduce `max_history_per_chat` for less memory
- Increase `cooldown_seconds` for fewer API calls
- Lower `max_tokens` for faster responses

---

## 🎨 Customization Examples

### Make AI More Casual

Edit `conversation.py`:

```python
system_content += "\n\nTONE: Be super casual, use slang, lots of emojis 😎"
```

### Make AI More Professional

```python
system_content += "\n\nTONE: Professional and formal. No emojis."
```

### Add Custom Behavior

```python
if "urgent" in current_message.lower():
    system_content += "\n\nThis is URGENT. Respond immediately and seriously."
```

---

## 🤝 Contributing

Want to add a new AI provider?

1. Fork the repo
2. Create `providers/your_provider.py`
3. Implement `AIProvider` interface
4. Test thoroughly
5. Submit PR

---

## 📝 License

Same as CatUserbot - GNU Affero General Public License v3.0

---

## 🙏 Credits

- **CatUserbot** - Base userbot framework
- **Mistral AI** - Primary AI provider
- **NVIDIA** - Future AI provider support

---

## 💡 Tips

1. **Start with per-chat**: Test in one chat before going global
2. **Monitor style learning**: Check `.ai status` regularly
3. **Adjust temperature**: Higher = more creative, Lower = more focused
4. **Use AFK integration**: Let AI handle messages when you're away
5. **Clear history**: Use `.ai clear` if conversation goes off-track

---

**Built with ❤️ for natural, human-like AI assistance**
