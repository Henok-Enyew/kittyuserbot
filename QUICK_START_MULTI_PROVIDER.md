# Quick Start: Multi-Provider AI System

## 🚀 Get Started in 3 Steps

### Step 1: Verify Configuration
```bash
# Check your API key is set
echo $AI_API_KEY

# If not set, add to .env
echo "AI_API_KEY=your_key_here" >> .env
```

### Step 2: Test Current Provider
```bash
# Check which provider is active
.ai provider

# Test with a question
.ask hello
```

### Step 3: Try Switching
```bash
# Switch to NVIDIA
.aiswitch nvidia

# Test again
.ask hello

# Switch back to Mistral
.aiswitch mistral
```

---

## 📋 New Commands

```bash
# Provider Management
.aiswitch mistral    # Switch to Mistral AI (default)
.aiswitch nvidia     # Switch to NVIDIA AI
.aiswitch            # Show available providers
.ai provider         # Show current provider

# Everything else works the same!
.ai on               # Enable AI
.ask <question>      # Ask AI anything
.aiafk               # AI AFK mode
.aipmpermit on       # AI PM permit
```

---

## 🎯 Common Use Cases

### Use Case 1: Quick Test
```bash
# Test both providers
.aiswitch mistral
.ask what is 2+2?

.aiswitch nvidia
.ask what is 2+2?

# Compare responses
```

### Use Case 2: Best for Task
```bash
# Fast general chat - use Mistral
.aiswitch mistral
.ai on

# Technical queries - use NVIDIA
.aiswitch nvidia
.ask explain this code [reply to code]
```

### Use Case 3: Handling Failures
```bash
# If one provider is slow/failing
.aiswitch mistral    # or nvidia

# System auto-retries and falls back
# You just switch manually if needed
```

---

## ✅ Verify Everything Works

### Test 1: Provider Switching
```bash
.ai provider
# Should show: Mistral AI

.aiswitch nvidia
# Should show: ✅ Switched to NVIDIA AI

.ai provider
# Should show: NVIDIA AI
```

### Test 2: AI Features
```bash
# Test auto-reply
.ai on
[Wait for someone to message]

# Test direct query
.ask what is my portfolio?

# Test AI AFK
.aiafk testing
[Wait for message]
.aiafk off
```

### Test 3: Error Handling
```bash
# Try invalid provider
.aiswitch invalid
# Should show error with available providers

# Try with no API key (don't actually do this)
# System will show clear error message
```

---

## 🔧 Troubleshooting

### Problem: "AI_API_KEY is not set"
**Solution:**
```bash
# Add to .env file
echo "AI_API_KEY=your_key_here" >> .env

# Or export in shell
export AI_API_KEY="your_key_here"

# Restart bot
```

### Problem: "Invalid provider: xyz"
**Solution:**
```bash
# Check spelling (must be lowercase)
.aiswitch mistral    # ✅ Correct
.aiswitch Mistral    # ❌ Wrong (uppercase)

# Show available providers
.aiswitch
```

### Problem: Slow responses
**Solution:**
```bash
# Try switching providers
.aiswitch mistral    # Usually faster

# Check status
.ai status

# Check logs
tail -f catub.log | grep "AI"
```

### Problem: Provider initialization failed
**Solution:**
```bash
# System auto-falls back to Mistral
# Check API key is valid
echo $AI_API_KEY

# Try switching manually
.aiswitch mistral
```

---

## 📊 What Changed?

### New Features ✨
- ✅ Multi-provider support (Mistral + NVIDIA)
- ✅ Runtime switching (no restart)
- ✅ Better error handling (auto-retry)
- ✅ Phone number sharing (when asked)
- ✅ No auto-read (chats stay unread)

### What Stayed the Same ✓
- ✅ All existing commands work
- ✅ Conversation history preserved
- ✅ Style learning works
- ✅ PM permit works
- ✅ AI AFK works
- ✅ Everything else unchanged

---

## 🎓 Pro Tips

### Tip 1: Choose Provider by Task
- **General chat:** Mistral (faster)
- **Code help:** NVIDIA (more technical)
- **Quick answers:** Mistral
- **Deep analysis:** NVIDIA

### Tip 2: Monitor Performance
```bash
# Check current setup
.ai status

# Shows:
# - Current provider
# - Global AI status
# - Chat-specific status
# - Statistics
```

### Tip 3: Use Fallback
```bash
# If provider fails, system auto-falls back
# You can also switch manually:
.aiswitch mistral    # Safe default
```

### Tip 4: Test Before Important Use
```bash
# Before important conversation
.ask test
# Verify provider responds

# Then enable AI
.ai on
```

---

## 📞 Need Help?

### Check Status
```bash
.ai status           # Full AI status
.ai provider         # Current provider
.aipmpermit status   # PM permit status
```

### View Logs
```bash
# In terminal
tail -f catub.log | grep "AI provider"

# Look for:
# "AI provider initialized: Mistral AI"
# "Switched to NVIDIA AI"
# "Falling back to Mistral provider"
```

### Common Commands
```bash
# Reset to default
.aiswitch mistral
.ai off
.ai clear

# Test everything
.ai provider
.ask hello
.ai status
```

---

## 🎉 You're Ready!

The multi-provider AI system is now active. Key points:

1. **Default provider:** Mistral AI
2. **Switch anytime:** `.aiswitch <provider>`
3. **No restart needed:** Instant switching
4. **Auto-retry:** System handles failures
5. **All features work:** No changes to existing commands

**Start using it:**
```bash
.ai provider         # Check current
.ask what is my portfolio?    # Test it
.aiswitch nvidia     # Try switching
.ask hello           # Test again
```

Enjoy your enhanced AI assistant! 🚀
