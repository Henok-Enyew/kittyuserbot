# 🏗️ AI Assistant Architecture

Complete system architecture and design documentation.

---

## 📐 System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        TELEGRAM                                  │
│                    (User Messages)                               │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   CATUSERBOT CORE                                │
│              (Telethon Event System)                             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  AI ASSISTANT PLUGIN                             │
│           userbot/plugins/ai_assistant.py                        │
│                                                                   │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │ Command Handler │  │ Message Handler  │  │ Style Learner  │ │
│  │  .ai on/off     │  │ Auto-respond     │  │ Outgoing msgs  │ │
│  │  .ai enable     │  │ Incoming msgs    │  │ Pattern learn  │ │
│  └─────────────────┘  └──────────────────┘  └────────────────┘ │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  CONVERSATION ENGINE                             │
│          userbot/ai_assistant/conversation.py                    │
│                                                                   │
│  • Build prompts dynamically                                     │
│  • Inject context (AFK, new chat, style)                         │
│  • Manage conversation flow                                      │
│  • Response decision logic                                       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   STATE MANAGEMENT                               │
│            userbot/ai_assistant/state.py                         │
│                                                                   │
│  • Global/per-chat toggles                                       │
│  • Conversation history                                          │
│  • Cooldown tracking                                             │
│  • Style examples                                                │
│  • Known chats                                                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   AI PROVIDER LAYER                              │
│          userbot/ai_assistant/providers/                         │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Base (ABC)   │  │ Mistral AI   │  │ NVIDIA AI    │          │
│  │ Interface    │  │ Provider     │  │ Provider     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   EXTERNAL AI APIs                               │
│         (Mistral AI / NVIDIA / Future Providers)                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Message Flow

### Incoming Message Flow

```
1. Telegram Message Arrives
   │
   ▼
2. Telethon Event System
   │
   ▼
3. AI Plugin: ai_auto_respond()
   │
   ├─► Check: Is AI enabled? ──────────► NO ──► Ignore
   │                                     YES
   ▼                                      │
4. Check: Is sender a bot? ──────────► YES ──► Ignore
   │                                     NO
   ▼                                      │
5. Conversation Engine: should_respond()
   │
   ├─► Private chat? ──────────────────► YES ──► Continue
   │                                     NO
   ├─► Group + mentioned? ─────────────► YES ──► Continue
   │                                     NO
   └─► Ignore                            │
                                         ▼
6. State: can_respond() (cooldown check)
   │
   ├─► Cooldown active? ───────────────► YES ──► Ignore
   │                                     NO
   ▼                                      │
7. Build Context
   │
   ├─► Get conversation history
   ├─► Check if new chat
   ├─► Check AFK status
   └─► Get style examples
   │
   ▼
8. Conversation Engine: build_messages()
   │
   ├─► System prompt
   ├─► Context injection
   ├─► History
   └─► Current message
   │
   ▼
9. AI Provider: generate_response()
   │
   ├─► Format for provider
   ├─► Make API call
   └─► Parse response
   │
   ▼
10. Send Response to Telegram
    │
    ▼
11. Update State
    │
    ├─► Add to history
    ├─► Mark response time
    └─► Mark chat as known
```

### Outgoing Message Flow (Style Learning)

```
1. User Sends Message
   │
   ▼
2. Telethon Event System
   │
   ▼
3. AI Plugin: learn_user_style()
   │
   ├─► Is command? (.ai, .afk, etc.) ──► YES ──► Ignore
   │                                     NO
   ▼                                      │
4. State: add_user_style_example()
   │
   ├─► Add to examples list
   └─► Keep last N examples
```

---

## 🧩 Component Details

### 1. AI Provider Layer

**Purpose**: Abstract interface for AI services

**Files**:
- `providers/base.py` - Abstract base class
- `providers/mistral.py` - Mistral AI implementation
- `providers/nvidia.py` - NVIDIA AI implementation
- `providers/__init__.py` - Factory function

**Key Methods**:
```python
class AIProvider(ABC):
    async def generate_response(messages, temperature, max_tokens) -> str
    def get_provider_name() -> str
```

**Design Pattern**: Abstract Factory + Strategy

**Why This Design**:
- Business logic never depends on specific provider
- Easy to add new providers
- Switch providers with config change only
- Testable in isolation

---

### 2. Conversation Engine

**Purpose**: Prompt building and conversation management

**File**: `conversation.py`

**Key Methods**:
```python
class ConversationEngine:
    def build_messages(current_message, chat_history, is_new_chat, 
                      is_afk, afk_reason, style_examples) -> List[Dict]
    def should_respond(message_text, is_group, is_mentioned) -> bool
    def extract_greeting_message(is_group) -> str
```

**Responsibilities**:
- Build system prompts
- Inject context dynamically
- Manage conversation flow
- Decide when to respond

**Design Pattern**: Builder + Strategy

---

### 3. State Management

**Purpose**: Track AI state across chats

**File**: `state.py`

**Key Data**:
```python
class AIState:
    global_enabled: bool
    enabled_chats: Set[int]
    known_chats: Set[int]
    last_response_time: Dict[int, float]
    conversation_history: Dict[int, list]
    user_style_examples: list
```

**Key Methods**:
```python
is_enabled(chat_id) -> bool
enable_global() / disable_global()
enable_chat(chat_id) / disable_chat(chat_id)
is_new_chat(chat_id) -> bool
can_respond(chat_id) -> bool
add_to_history(chat_id, role, content)
add_user_style_example(message)
```

**Design Pattern**: Singleton + Repository

---

### 4. Plugin Layer

**Purpose**: Integration with userbot

**File**: `plugins/ai_assistant.py`

**Components**:

1. **Command Handlers**:
   - `.ai on` / `.ai off` - Global toggle
   - `.ai enable` / `.ai disable` - Per-chat toggle
   - `.ai status` - Show configuration
   - `.ai clear` - Clear history

2. **Message Handlers**:
   - `ai_auto_respond()` - Incoming messages
   - `learn_user_style()` - Outgoing messages

**Design Pattern**: Command + Observer

---

## 🎯 Design Principles

### 1. Separation of Concerns

Each layer has a single responsibility:
- **Plugin**: User interaction
- **Conversation**: Business logic
- **State**: Data management
- **Provider**: External API

### 2. Provider Independence

```python
# Business logic NEVER does this:
from mistral import MistralClient  # ❌ BAD

# Instead:
from providers import get_ai_provider  # ✅ GOOD
provider = get_ai_provider(config.provider, config.api_key)
```

### 3. Dependency Injection

```python
# Components receive dependencies:
def __init__(self, provider: AIProvider):
    self.provider = provider  # ✅ Testable

# Not:
def __init__(self):
    self.provider = MistralProvider()  # ❌ Hard-coded
```

### 4. Interface Segregation

```python
# Small, focused interfaces:
class AIProvider(ABC):
    async def generate_response(...) -> str  # One job
    def get_provider_name() -> str           # One job
```

---

## 🔌 Extension Points

### Adding New AI Provider

1. Create `providers/your_provider.py`:
```python
from .base import AIProvider

class YourProvider(AIProvider):
    API_URL = "https://api.yourprovider.com/v1/chat"
    
    def get_provider_name(self) -> str:
        return "Your Provider"
    
    async def generate_response(self, messages, temperature, max_tokens):
        # Implementation
        pass
```

2. Register in `providers/__init__.py`:
```python
PROVIDERS = {
    "mistral": MistralProvider,
    "nvidia": NVIDIAProvider,
    "your_provider": YourProvider,  # Add here
}
```

3. Use it:
```bash
export AI_PROVIDER=your_provider
export AI_API_KEY=your_key
```

### Adding New Commands

Edit `plugins/ai_assistant.py`:
```python
@catub.cat_cmd(
    pattern="ai custom$",
    command=("ai custom", plugin_category),
    info={...}
)
async def ai_custom_command(event):
    # Your implementation
    pass
```

### Adding Custom Context

Edit `conversation.py`:
```python
def build_messages(self, ...):
    # Add custom context
    if some_condition:
        system_content += "\n\nCUSTOM CONTEXT: ..."
```

---

## 🧪 Testing Strategy

### Unit Tests

```python
# Test provider interface
def test_provider():
    provider = MistralProvider(api_key="test")
    assert provider.get_provider_name() == "Mistral AI"

# Test state management
def test_state():
    state = AIState()
    state.enable_global()
    assert state.global_enabled == True

# Test conversation building
def test_conversation():
    conv = ConversationEngine("Test")
    messages = conv.build_messages("Hello", [], False, False, None, [])
    assert len(messages) >= 2
```

### Integration Tests

```python
# Test full flow
async def test_full_flow():
    provider = get_ai_provider("mistral", api_key)
    conv = ConversationEngine("Test")
    state = AIState()
    
    # Simulate message
    messages = conv.build_messages("Test", [], False, False, None, [])
    response = await provider.generate_response(messages)
    
    assert response is not None
```

---

## 📊 Performance Considerations

### Memory Usage

```
Component                Memory
─────────────────────────────────
Provider instance        ~1 MB
Conversation engine      ~1 MB
State (per chat):
  - History (10 msgs)    ~5 KB
  - Style examples       ~10 KB
Total (100 chats)        ~3.5 MB
```

### API Calls

```
Scenario                 API Calls
─────────────────────────────────
Per response             1 call
With cooldown (5s)       Max 12/min
Typical usage            ~50/hour
```

### Latency

```
Component                Time
─────────────────────────────────
State check              <1 ms
Prompt building          <10 ms
API call                 1-3 s
Total response time      1-3 s
```

---

## 🔒 Security Considerations

### API Key Storage

```python
# ✅ GOOD: Environment variable
api_key = os.environ.get("AI_API_KEY")

# ❌ BAD: Hard-coded
api_key = "sk-1234..."  # Never do this!
```

### Error Handling

```python
try:
    response = await provider.generate_response(...)
except Exception as e:
    LOGS.error(f"AI error: {e}")
    # Silently fail - don't expose to user
    return
```

### Input Validation

```python
# Validate message length
if len(message) > MAX_LENGTH:
    return

# Filter sensitive content
if contains_sensitive_data(message):
    return
```

---

## 🎨 Customization Guide

### Change AI Personality

Edit `conversation.py`:
```python
def _build_system_prompt(self):
    return f"""You are {self.user_name}'s assistant.
    
    PERSONALITY: [Your custom personality here]
    
    BEHAVIOR: [Your custom rules here]
    """
```

### Adjust Response Logic

Edit `conversation.py`:
```python
def should_respond(self, message_text, is_group, is_mentioned):
    # Custom logic
    if custom_condition:
        return True
    return False
```

### Add Custom State

Edit `state.py`:
```python
class AIState:
    def __init__(self):
        # ... existing state ...
        self.custom_state = {}  # Your custom state
```

---

## 📈 Scalability

### Current Limits

- **Chats**: Unlimited (memory-based)
- **History**: 10 messages per chat
- **Style examples**: 20 messages
- **Cooldown**: 5 seconds

### Scaling Up

For high-volume usage:

1. **Add persistent storage**:
```python
# Use Redis or database
import redis
r = redis.Redis()
r.set(f"history:{chat_id}", json.dumps(history))
```

2. **Add caching**:
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_cached_response(message_hash):
    # Cache similar messages
    pass
```

3. **Add rate limiting**:
```python
from ratelimit import limits

@limits(calls=10, period=60)
async def generate_response(...):
    # Rate limit API calls
    pass
```

---

## 🔄 Future Enhancements

### Planned Features

1. **Multi-language support**
2. **Conversation summarization**
3. **Sentiment analysis**
4. **Custom personality profiles**
5. **Voice message support**
6. **Image understanding**
7. **Persistent storage**
8. **Analytics dashboard**

### Provider Roadmap

- [x] Mistral AI
- [x] NVIDIA AI
- [ ] OpenAI GPT-4
- [ ] Anthropic Claude
- [ ] Google Gemini
- [ ] Local LLMs (Ollama)

---

## 📚 References

### Design Patterns Used

- **Abstract Factory**: Provider creation
- **Strategy**: Provider selection
- **Builder**: Message construction
- **Singleton**: State management
- **Observer**: Event handling
- **Command**: Command handlers
- **Repository**: State storage

### Best Practices

- SOLID principles
- Clean architecture
- Dependency injection
- Interface segregation
- Single responsibility

---

**Built with clean architecture principles for maintainability and extensibility**
