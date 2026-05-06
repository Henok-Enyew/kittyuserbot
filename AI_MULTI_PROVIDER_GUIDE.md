# AI Multi-Provider System Guide

## Overview

The AI assistant now supports multiple AI providers with runtime switching capabilities. You can seamlessly switch between providers without restarting the bot.

---

## Supported Providers

### 1. Mistral AI (Default)
- **Model:** mistral-small-latest
- **Strengths:** Fast, reliable, good for general conversations
- **API:** https://api.mistral.ai

### 2. NVIDIA AI
- **Model:** meta/llama-3.1-8b-instruct
- **Strengths:** Open-source model, good for technical queries
- **API:** https://integrate.api.nvidia.com

---

## Configuration

### Environment Variables

You need to set your API key in the environment:

```bash
# In .env file or environment
AI_API_KEY=your_api_key_here
```

**Note:** The same API key is used for both providers. Make sure your key is valid for the provider you're using.

---

## Commands

### Switch Provider

```bash
# Switch to Mistral AI
.aiswitch mistral

# Switch to NVIDIA AI
.aiswitch nvidia

# Show available providers
.aiswitch
```

### Check Current Provider

```bash
# Show which provider is active
.ai provider

# Full status including provider
.ai status
```

---

## How It Works

### Architecture

```
┌─────────────────────────────────────┐
│     AI Assistant Commands           │
│  (.ai, .ask, .aiafk, .aipmpermit)  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│    Conversation Engine               │
│  (Builds prompts & context)         │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      Provider Abstraction            │
│    (get_ai_components)              │
└──────────────┬──────────────────────┘
               │
        ┌──────┴──────┐
        ▼             ▼
┌──────────────┐ ┌──────────────┐
│   Mistral    │ │    NVIDIA    │
│   Provider   │ │   Provider   │
└──────────────┘ └──────────────┘
```

### Provider Switching Flow

1. User runs `.aiswitch nvidia`
2. State updates `current_provider = "nvidia"`
3. Current provider instance is cleared
4. Next AI request initializes NVIDIA provider
5. All subsequent requests use NVIDIA

**Key Points:**
- Switching is instant (no bot restart needed)
- Affects ALL AI features immediately
- Provider is initialized lazily on first use
- Fallback to Mistral if initialization fails

---

## Error Handling

### Automatic Retry

Both providers implement automatic retry logic:
- **Max retries:** 2 attempts
- **Retry on:** Network errors, empty responses, API errors
- **Timeout:** 30 seconds per request

### Fallback Mechanism

If the current provider fails to initialize:
1. System logs the error
2. Automatically falls back to Mistral (if not already using it)
3. User is notified of the fallback

### Empty Response Handling

If a provider returns an empty response:
1. Automatically retries once
2. If still empty, raises an error
3. User sees a friendly error message

---

## Use Cases

### Scenario 1: Testing Different Models

```bash
# Try Mistral for a question
.aiswitch mistral
.ask explain quantum computing

# Try NVIDIA for comparison
.aiswitch nvidia
.ask explain quantum computing
```

### Scenario 2: Provider-Specific Features

```bash
# Use Mistral for general chat (faster)
.aiswitch mistral
.ai on

# Switch to NVIDIA for technical discussions
.aiswitch nvidia
.ask explain this code [reply to code]
```

### Scenario 3: Handling API Limits

```bash
# If Mistral hits rate limit
.aiswitch nvidia

# Continue using AI features normally
.ask what is my portfolio?
```

---

## Features Affected by Provider Switch

All AI features use the current provider:

✅ **Auto-Reply** (`.ai on/off`)
- Responds to incoming messages
- Uses current provider for all responses

✅ **AI AFK** (`.aiafk`)
- Away message responses
- Uses current provider

✅ **AI PM Permit** (`.aipmpermit on`)
- Gatekeeper responses
- Uses current provider

✅ **Direct Queries** (`.ask`)
- On-demand questions
- Uses current provider

---

## Performance Comparison

| Feature | Mistral AI | NVIDIA AI |
|---------|-----------|-----------|
| Response Speed | Fast (~2-3s) | Medium (~3-5s) |
| Context Understanding | Excellent | Very Good |
| Technical Accuracy | Very Good | Excellent |
| Conversation Flow | Natural | Natural |
| Rate Limits | Generous | Generous |

---

## Troubleshooting

### Provider Won't Switch

**Problem:** `.aiswitch nvidia` doesn't work

**Solutions:**
1. Check provider name spelling (must be lowercase)
2. Verify API key is set: `echo $AI_API_KEY`
3. Check logs for initialization errors

### Provider Initialization Failed

**Problem:** "Provider switched but initialization failed"

**Solutions:**
1. Check API key validity
2. Verify network connectivity
3. Check provider API status
4. System will auto-fallback to Mistral

### Responses Are Slow

**Problem:** AI takes too long to respond

**Solutions:**
1. Try switching providers: `.aiswitch mistral`
2. Check network connection
3. Reduce max_tokens in code if needed

### Empty Responses

**Problem:** AI returns empty or no response

**Solutions:**
1. System automatically retries once
2. If persists, switch providers
3. Check API key and credits

---

## Advanced Configuration

### Customizing Providers

Edit `userbot/ai_assistant/providers/mistral.py` or `nvidia.py`:

```python
# Change model
DEFAULT_MODEL = "your-preferred-model"

# Adjust timeout
timeout=aiohttp.ClientTimeout(total=60)  # 60 seconds

# Modify retry logic
max_retries = 3  # More retries
```

### Adding New Providers

1. Create new provider file: `userbot/ai_assistant/providers/newprovider.py`
2. Inherit from `AIProvider` base class
3. Implement `generate_response()` and `get_provider_name()`
4. Register in `providers/__init__.py`:

```python
from .newprovider import NewProvider

PROVIDERS = {
    "mistral": MistralProvider,
    "nvidia": NVIDIAProvider,
    "newprovider": NewProvider,  # Add here
}
```

5. Use with `.aiswitch newprovider`

---

## Best Practices

### 1. Choose Provider Based on Use Case
- **General chat:** Mistral (faster)
- **Technical queries:** NVIDIA (more accurate)
- **Code analysis:** NVIDIA
- **Quick responses:** Mistral

### 2. Monitor Performance
```bash
# Check current provider
.ai provider

# Check full status
.ai status
```

### 3. Handle Failures Gracefully
- System auto-retries failed requests
- Falls back to Mistral if needed
- Always check logs for errors

### 4. API Key Management
- Use environment variables
- Never hardcode API keys
- Rotate keys periodically
- Monitor usage/credits

---

## Privacy & Read Behavior

### Read Acknowledgments

**Important:** Read acknowledgments have been disabled to prevent marking chats as read automatically.

**What This Means:**
- Chats won't be marked as read when AI responds
- You can review messages later
- More natural user experience

**Technical Note:**
```python
# Disabled in code:
# await event.client.send_read_acknowledge(chat_id, event.message)
```

### Phone Number Sharing

The AI now shares your phone number **only when appropriate**:

✅ **Shares when:**
- User asks "how can I contact you?"
- User asks "what's your phone number?"
- User asks for contact information

❌ **Doesn't share when:**
- Casual conversation
- General questions
- Unnecessary contexts

---

## API Requirements

### Mistral AI
- Sign up: https://console.mistral.ai
- Get API key from dashboard
- Free tier available
- Pay-as-you-go pricing

### NVIDIA AI
- Sign up: https://build.nvidia.com
- Get API key from dashboard
- Free tier available
- Access to various models

---

## Monitoring & Logs

### Check Logs

```bash
# View bot logs
tail -f catub.log

# Look for provider messages
grep "AI provider" catub.log
grep "Switched to" catub.log
```

### Log Messages

```
✅ Success: "AI provider initialized: Mistral AI"
✅ Success: "Switched to NVIDIA AI"
⚠️ Warning: "Failed to initialize nvidia provider"
⚠️ Warning: "Falling back to Mistral provider"
❌ Error: "Mistral AI failed after retries"
```

---

## FAQ

**Q: Can I use different providers for different features?**
A: No, all features use the same provider. Switch globally with `.aiswitch`.

**Q: Does switching affect conversation history?**
A: No, conversation history is preserved across provider switches.

**Q: Which provider is better?**
A: Depends on use case. Mistral is faster, NVIDIA is more technical.

**Q: Can I add my own provider?**
A: Yes! Follow the "Adding New Providers" section above.

**Q: What happens if my API key is invalid?**
A: Initialization fails, and you'll see an error message.

**Q: Does provider switching restart the bot?**
A: No, switching is instant and doesn't require restart.

---

## Summary

The multi-provider system gives you:
- ✅ Flexibility to choose AI models
- ✅ Runtime switching without restart
- ✅ Automatic error handling and retries
- ✅ Fallback mechanisms for reliability
- ✅ Consistent behavior across all features
- ✅ Easy extensibility for new providers

Switch providers anytime with `.aiswitch <provider>` and enjoy seamless AI assistance!
