# API Keys Configuration Guide

## 🔑 Environment Variables Setup

### Option 1: Separate Keys (Recommended)

Use separate API keys for each provider:

```bash
# In your .env file:

# Mistral AI API Key
MISTRAL_API_KEY="ISTHgYweaLuaLNBpjdXzvN*****"

# NVIDIA AI API Key
NVIDIA_API_KEY="nvapi-your-nvidia-key-here"

# Optional: Set default provider
AI_PROVIDER="mistral"
```

**Benefits:**
- ✅ Each provider has its own key
- ✅ Can use different accounts/credits
- ✅ More secure (if one leaks, other is safe)
- ✅ Clear and organized

---

### Option 2: Single Key (Backward Compatible)

Use one key for both providers (if they share the same key):

```bash
# In your .env file:

# Single API Key (used for both providers)
AI_API_KEY="your-shared-api-key-here"

# Optional: Set default provider
AI_PROVIDER="mistral"
```

**Benefits:**
- ✅ Simpler setup
- ✅ Backward compatible
- ✅ Works if both providers use same key

---

### Option 3: Mixed (Flexible)

Use separate keys but with fallback:

```bash
# In your .env file:

# Provider-specific keys
MISTRAL_API_KEY="your-mistral-key"
NVIDIA_API_KEY="your-nvidia-key"

# Fallback key (optional)
AI_API_KEY="fallback-key"

# Default provider
AI_PROVIDER="mistral"
```

**How it works:**
1. System tries `MISTRAL_API_KEY` for Mistral
2. If not found, falls back to `AI_API_KEY`
3. Same for NVIDIA: tries `NVIDIA_API_KEY`, then `AI_API_KEY`

---

## 📋 Priority Order

The system checks for API keys in this order:

### For Mistral AI:
1. `MISTRAL_API_KEY` (provider-specific)
2. `AI_API_KEY` (fallback)

### For NVIDIA AI:
1. `NVIDIA_API_KEY` (provider-specific)
2. `AI_API_KEY` (fallback)

---

## 🚀 Quick Setup

### Step 1: Get Your API Keys

**Mistral AI:**
1. Go to https://console.mistral.ai
2. Sign up / Log in
3. Navigate to API Keys
4. Create new key
5. Copy the key

**NVIDIA AI:**
1. Go to https://build.nvidia.com
2. Sign up / Log in
3. Navigate to API Keys
4. Create new key
5. Copy the key

### Step 2: Add to .env File

```bash
# Open your .env file
nano .env

# Add these lines:
MISTRAL_API_KEY="your-mistral-key-here"
NVIDIA_API_KEY="your-nvidia-key-here"
AI_PROVIDER="mistral"

# Save and exit (Ctrl+X, Y, Enter)
```

### Step 3: Verify Setup

```bash
# Check environment variables
echo $MISTRAL_API_KEY
echo $NVIDIA_API_KEY

# Or check in bot
.ai status
```

---

## 🔧 Configuration Examples

### Example 1: Both Providers with Separate Keys

```bash
# .env file
MISTRAL_API_KEY="mistral_key_abc123"
NVIDIA_API_KEY="nvapi_key_xyz789"
AI_PROVIDER="mistral"
ALIVE_NAME="Henok"
```

**Usage:**
```bash
.aiswitch mistral    # Uses MISTRAL_API_KEY
.aiswitch nvidia     # Uses NVIDIA_API_KEY
```

---

### Example 2: Only Mistral (Single Provider)

```bash
# .env file
MISTRAL_API_KEY="mistral_key_abc123"
AI_PROVIDER="mistral"
ALIVE_NAME="Henok"
```

**Usage:**
```bash
.ai on               # Uses Mistral
.ask hello           # Uses Mistral
.aiswitch nvidia     # Will fail (no NVIDIA key)
```

---

### Example 3: Backward Compatible (Old Setup)

```bash
# .env file (old format still works)
AI_API_KEY="shared_key_abc123"
AI_PROVIDER="mistral"
ALIVE_NAME="Henok"
```

**Usage:**
```bash
.aiswitch mistral    # Uses AI_API_KEY
.aiswitch nvidia     # Uses AI_API_KEY (same key)
```

---

## ⚠️ Important Notes

### Security
- ✅ Never commit `.env` file to git
- ✅ Add `.env` to `.gitignore`
- ✅ Keep keys secret
- ✅ Rotate keys periodically

### Key Format
- Mistral keys usually start with: `IST...` or similar
- NVIDIA keys usually start with: `nvapi-...`
- Keys are case-sensitive

### Validation
```bash
# Test Mistral key
.aiswitch mistral
.ask test

# Test NVIDIA key
.aiswitch nvidia
.ask test

# If error, check:
# 1. Key is correct
# 2. Key is active
# 3. Account has credits
```

---

## 🐛 Troubleshooting

### Error: "API key not set for mistral"

**Problem:** `MISTRAL_API_KEY` not found

**Solution:**
```bash
# Add to .env
echo 'MISTRAL_API_KEY="your-key-here"' >> .env

# Or use fallback
echo 'AI_API_KEY="your-key-here"' >> .env
```

---

### Error: "API key not set for nvidia"

**Problem:** `NVIDIA_API_KEY` not found

**Solution:**
```bash
# Add to .env
echo 'NVIDIA_API_KEY="your-key-here"' >> .env

# Or use fallback
echo 'AI_API_KEY="your-key-here"' >> .env
```

---

### Error: "Mistral API error (401)"

**Problem:** Invalid or expired key

**Solution:**
1. Check key is correct (no extra spaces)
2. Verify key is active in console
3. Check account has credits
4. Generate new key if needed

---

### Error: "NVIDIA API error (401)"

**Problem:** Invalid or expired key

**Solution:**
1. Check key is correct (no extra spaces)
2. Verify key is active in console
3. Check account has credits
4. Generate new key if needed

---

## 📊 Migration Guide

### From Old Setup to New Setup

**Old .env:**
```bash
AI_API_KEY="shared_key"
AI_PROVIDER="mistral"
```

**New .env (Recommended):**
```bash
# Keep old key as fallback
AI_API_KEY="shared_key"

# Add provider-specific keys
MISTRAL_API_KEY="mistral_specific_key"
NVIDIA_API_KEY="nvidia_specific_key"

# Keep provider setting
AI_PROVIDER="mistral"
```

**Migration Steps:**
1. Keep existing `AI_API_KEY` (backward compatible)
2. Add `MISTRAL_API_KEY` with Mistral-specific key
3. Add `NVIDIA_API_KEY` with NVIDIA-specific key
4. Test both providers
5. Optionally remove `AI_API_KEY` once confirmed working

---

## ✅ Verification Checklist

After setup, verify:

- [ ] `.env` file exists
- [ ] `MISTRAL_API_KEY` is set (or `AI_API_KEY`)
- [ ] `NVIDIA_API_KEY` is set (or `AI_API_KEY`)
- [ ] Keys have no extra spaces
- [ ] Keys are quoted properly
- [ ] `.env` is in `.gitignore`
- [ ] Bot can read environment variables
- [ ] `.ai status` shows provider
- [ ] `.aiswitch mistral` works
- [ ] `.aiswitch nvidia` works
- [ ] `.ask test` responds

---

## 🎯 Recommended Setup

For best results, use this configuration:

```bash
# .env file

# Provider-specific API keys
MISTRAL_API_KEY="your-mistral-key-here"
NVIDIA_API_KEY="your-nvidia-key-here"

# Default provider (optional, defaults to "mistral")
AI_PROVIDER="mistral"

# User name (optional, defaults to "Henok")
ALIVE_NAME="Henok"

# Other bot settings...
```

This gives you:
- ✅ Separate keys for each provider
- ✅ Clear organization
- ✅ Easy to manage
- ✅ Secure and flexible

---

## 📞 Need Help?

### Check Current Configuration
```bash
# Show environment variables (keys hidden)
env | grep API_KEY

# Check bot status
.ai status
.ai provider
```

### Test Configuration
```bash
# Test Mistral
.aiswitch mistral
.ask hello

# Test NVIDIA
.aiswitch nvidia
.ask hello
```

### View Logs
```bash
# Check for API key errors
tail -f catub.log | grep "API key"

# Check provider initialization
tail -f catub.log | grep "AI provider"
```

---

## 🎉 Summary

**Recommended Variable Names:**
```bash
MISTRAL_API_KEY="your-mistral-key"
NVIDIA_API_KEY="your-nvidia-key"
AI_PROVIDER="mistral"
```

**Fallback (Backward Compatible):**
```bash
AI_API_KEY="shared-key"
```

**Priority:**
- Mistral: `MISTRAL_API_KEY` → `AI_API_KEY`
- NVIDIA: `NVIDIA_API_KEY` → `AI_API_KEY`

Use separate keys for better security and organization! 🔐
