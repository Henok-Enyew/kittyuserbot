# AI Assistant Features Update

## New Features Added

### 1. Enhanced `.aia` and `.aid` Commands (Reply Support)

**Previous Behavior:**
- Only worked in private chats
- Could only approve/disapprove the current chat user

**New Behavior:**
- Works in **any chat** (private or group)
- Can reply to any user's message and use `.aia` or `.aid`
- Detects the user from the replied message

**Usage Examples:**

```
# In a private chat (original way)
.aia          → Approves the current chat user
.aid          → Disapproves the current chat user

# Reply to any message (new way)
[Reply to user's message]
.aia          → Approves that user
.aid          → Disapproves that user
```

**Use Cases:**
- Approve users from group chats
- Approve users by replying to their forwarded messages
- Manage approvals without switching to private chat

---

### 2. New `.ask` Command (Direct AI Queries)

**Purpose:**
Ask the AI assistant anything directly in any chat, without needing auto-reply to be enabled.

**Features:**
- Works in **any chat** (private, group, channel)
- AI has access to your complete profile (portfolio, skills, experience)
- Can reply to messages and ask AI to explain them
- No conversation history (fresh context each time)
- Handles long responses by splitting into chunks

**Usage:**

```bash
# General questions
.ask what is quantum computing?
.ask explain blockchain technology
.ask what is the difference between REST and GraphQL?

# Questions about yourself
.ask what is my portfolio?
.ask what are my skills?
.ask tell me about my work experience
.ask what projects have I built?
.ask what is my GitHub?

# Reply to messages
[Reply to any message]
.ask explain this
.ask summarize this
.ask what does this mean?
.ask translate this to simple terms
```

**Response Format:**
```
🤔 Thinking...

🤖 AI Response:

[AI's answer here]
```

**Examples:**

1. **General Knowledge:**
   ```
   You: .ask what is theology?
   AI: Theology is the systematic study of the nature of the divine...
   ```

2. **About Yourself:**
   ```
   You: .ask what is my portfolio?
   AI: Your portfolio is at https://henokenyew.me. You're a Software Engineer...
   ```

3. **Code Explanation:**
   ```
   [Reply to code snippet]
   You: .ask explain this code
   AI: This code implements a binary search algorithm...
   ```

---

## Updated Commands Summary

### AI PM Permit Commands

| Command | Description | Usage |
|---------|-------------|-------|
| `.aipmpermit on` | Enable AI PM permit | In any chat |
| `.aipmpermit off` | Disable AI PM permit | In any chat |
| `.aia` or `.aiapprove` | Approve user | Private chat or reply to message |
| `.aid` or `.aidisapprove` | Disapprove user | Private chat or reply to message |
| `.aialist` or `.aiapproved` | List approved users | In any chat |
| `.aipmpermit status` | Show PM permit status | In any chat |

### AI Assistant Commands

| Command | Description | Usage |
|---------|-------------|-------|
| `.ai on` | Enable AI globally | In any chat |
| `.ai off` | Disable AI globally | In any chat |
| `.ai enable` | Enable AI for current chat | In any chat |
| `.ai disable` | Disable AI for current chat | In any chat |
| `.ai status` | Show AI status | In any chat |
| `.ai clear` | Clear conversation history | In any chat |
| `.ask <question>` | Ask AI directly | In any chat |
| `.aiafk [reason]` | Enable AI AFK mode | In any chat |
| `.aiafk off` | Disable AI AFK mode | In any chat |

---

## Technical Implementation

### Database Persistence
- Created `userbot/sql_helper/ai_pmpermit_sql.py`
- Approved users are stored in SQLite database
- Survives bot restarts
- Stores user ID, first name, and username

### State Management Updates
- `ai_state.approve_user()` now accepts first_name and username
- `_load_approved_users()` loads from database on startup
- Automatic database sync on approve/disapprove

### Logic Improvements
- Fixed approved users getting AI responses when AI is disabled
- Proper separation between PM permit gating and regular AI
- Reply detection for flexible user management

---

## Workflow Examples

### Scenario 1: Managing PM Permit from Groups

```
[Someone messages you in a group]
User: "Hey Henok, can you help me with my project?"

[You reply to their message]
You: .aia

Bot: ✅ John approved. AI gating removed for this user.

[Now John can message you privately without AI gating]
```

### Scenario 2: Using .ask for Quick Info

```
[In any chat]
You: .ask what is my LinkedIn?

AI: 🤖 AI Response:

Your LinkedIn profile is at https://www.linkedin.com/in/henokenyew/
```

### Scenario 3: Explaining Code

```
[Someone sends you code in a group]
User: [sends complex code snippet]

[You reply to it]
You: .ask explain this code in simple terms

AI: 🤖 AI Response:

This code implements a recursive function that...
[detailed explanation]
```

---

## Benefits

1. **Flexibility**: Manage approvals from anywhere, not just private chats
2. **Convenience**: Ask AI questions without enabling auto-reply
3. **Context-Aware**: AI knows your profile and can answer personal questions
4. **Persistent**: Approved users survive bot restarts
5. **User-Friendly**: Works with replies for intuitive user management

---

## Notes

- The `.ask` command uses fresh context (no conversation history)
- Approved users are treated as normal users (need AI enabled to get responses)
- The AI has access to your complete profile from `conversation.py`
- All commands work with the configured AI provider (Mistral/NVIDIA)
