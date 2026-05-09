# 🚀 Quick Start - AI Assistant

Get your AI assistant running in 5 minutes!

---

## Option 1: Virtual Environment (Recommended)

### Step 1: Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows
```

### Step 2: Install Dependencies

```bash
# Install all requirements
pip install -r requirements.txt

# Verify installation
python3 -c "import aiohttp; print('✅ Dependencies OK')"
```

### Step 3: Configure AI

```bash
# Run setup script
./setup_ai.sh

# OR manually set environment variables
export AI_API_KEY="HI0kplM0ehgLKhjZ94TKfch2xrakwWVf"
export AI_PROVIDER="mistral"
export ALIVE_NAME="Henok"
```

### Step 4: Configure Userbot

If you haven't configured the userbot yet:

```bash
# Copy sample config
cp sample_config.py config.py

# Edit config.py and set:
# - APP_ID (from my.telegram.org)
# - API_HASH (from my.telegram.org)
# - STRING_SESSION (run: python3 stringsetup.py)
# - TG_BOT_TOKEN (from @BotFather)
# - DATABASE_URL (from elephantsql.com or heroku)
```

### Step 5: Run Userbot

```bash
# Start userbot
python3 -m userbot

# Check logs
tail -f userbot.log
```

### Step 6: Test AI

1. In any Telegram chat, send: `.ai on`
2. Message yourself from another account
3. AI should respond automatically! 🎉

---

## Option 2: Docker (Alternative)

### Step 1: Build Docker Image

```bash
# Build image
docker-compose build

# OR use Dockerfile directly
docker build -t catuserbot .
```

### Step 2: Set Environment Variables

Edit `docker-compose.yml` and add:

```yaml
environment:
  - AI_API_KEY=HI0kplM0ehgLKhjZ94TKfch2xrakwWVf
  - AI_PROVIDER=mistral
  - ALIVE_NAME=Henok
  # ... other vars
```

### Step 3: Run Container

```bash
# Start container
docker-compose up -d

# Check logs
docker-compose logs -f
```

---

## 🎯 Your API Key

You provided: `HI0kplM0ehgLKhjZ94TKfch2xrakwWVf`

This is already set in the examples above!

---

## ✅ Verification Checklist

- [ ] Virtual environment created and activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] AI_API_KEY environment variable set
- [ ] Userbot configured (APP_ID, API_HASH, STRING_SESSION, etc.)
- [ ] Userbot running without errors
- [ ] Tested `.ai on` command
- [ ] AI responds to messages

---

## 🐛 Common Issues

### "AI_API_KEY not configured"

```bash
# Set the environment variable
export AI_API_KEY="HI0kplM0ehgLKhjZ94TKfch2xrakwWVf"

# Verify it's set
echo $AI_API_KEY
```

### "Module 'aiohttp' not found"

```bash
# Install dependencies
pip install -r requirements.txt
```

### "Userbot won't start"

```bash
# Check if config.py exists
ls config.py

# If not, copy sample
cp sample_config.py config.py

# Edit and configure it
nano config.py
```

### "AI not responding"

1. Check if enabled: `.ai status`
2. Enable it: `.ai on`
3. Check logs: `tail -f userbot.log`
4. Verify API key is correct

---

## 📱 Commands Reference

```bash
.ai on          # Enable AI globally
.ai off         # Disable AI globally
.ai enable      # Enable for current chat
.ai disable     # Disable for current chat
.ai status      # Show configuration
.ai clear       # Clear conversation history
```

---

## 🎓 Next Steps

1. **Read full docs**: `AI_ASSISTANT_README.md`
2. **Customize behavior**: Edit `userbot/ai_assistant/conversation.py`
3. **Adjust settings**: Edit `userbot/ai_assistant/state.py`
4. **Test AFK integration**: Use `.afk` command
5. **Monitor style learning**: Check `.ai status` regularly

---

## 💬 Support

- **Userbot Issues**: https://t.me/catuserbot_support
- **AI Assistant Issues**: Check logs and documentation

---

**You're all set! Enjoy your AI assistant! 🤖✨**
