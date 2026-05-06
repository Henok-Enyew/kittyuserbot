# AI Assistant Quick Reference

## 🚀 Quick Start

### Enable AI PM Permit
```
.aipmpermit on
```

### Switch AI Provider
```
.aiswitch mistral    (default)
.aiswitch nvidia     (alternative)
.ai provider         (show current)
```

### Ask AI Anything
```
.ask what is my portfolio?
.ask explain quantum computing
```

### Approve/Disapprove Users
```
# In private chat
.aia          (approve)
.aid          (disapprove)

# Reply to any message
[Reply] .aia  (approve that user)
[Reply] .aid  (disapprove that user)
```

---

## 📋 Common Use Cases

### 1. Someone DMs You
```
Scenario: Unknown user messages you
→ AI PM Permit responds automatically
→ You review the conversation
→ Reply to their message: .aia
→ User is approved, AI stops gating them
```

### 2. Quick Information Lookup
```
You: .ask what are my technical skills?
AI: Your technical skills include Python, React, Django...

You: .ask what is my GitHub?
AI: Your GitHub is https://github.com/henok-enyew
```

### 3. Code Help in Groups
```
[Someone posts code in a group]
You: [Reply to code] .ask explain this
AI: [Provides detailed explanation]
```

### 4. Managing Approvals from Groups
```
[User messages in a group]
You: [Reply to their message] .aia
Bot: ✅ User approved
[They can now DM you without AI gating]
```

---

## 🎯 Command Cheat Sheet

### AI Provider Management
| Command | What It Does |
|---------|--------------|
| `.aiswitch mistral` | Switch to Mistral AI |
| `.aiswitch nvidia` | Switch to NVIDIA AI |
| `.ai provider` | Show current provider |

### PM Permit
| Command | What It Does |
|---------|--------------|
| `.aipmpermit on` | Turn on AI gatekeeper |
| `.aipmpermit off` | Turn off AI gatekeeper |
| `.aia` | Approve user (private or reply) |
| `.aid` | Disapprove user (private or reply) |
| `.aialist` | List all approved users |

### AI Assistant
| Command | What It Does |
|---------|--------------|
| `.ai on` | Enable AI everywhere |
| `.ai off` | Disable AI everywhere |
| `.ai enable` | Enable AI in this chat |
| `.ai disable` | Disable AI in this chat |
| `.ai status` | Check AI status |
| `.ai clear` | Clear chat history |

### Direct Queries
| Command | What It Does |
|---------|--------------|
| `.ask <question>` | Ask AI anything |
| `.ask` (reply) | Ask AI about replied message |

### AI AFK
| Command | What It Does |
|---------|--------------|
| `.aiafk [reason]` | AI responds while you're away |
| `.aiafk off` | Turn off AI AFK |

---

## 💡 Pro Tips

1. **Reply to Approve**: You can approve users from any chat by replying to their messages
2. **Ask About Yourself**: The AI knows your portfolio, skills, and experience
3. **No History in .ask**: Each `.ask` is independent (no conversation memory)
4. **Works Everywhere**: `.ask` works in private chats, groups, and channels
5. **Long Responses**: AI automatically splits long responses into chunks

---

## 🔧 Troubleshooting

### AI Not Responding?
```
.ai status          (check if AI is enabled)
.ai on              (enable globally)
```

### User Still Getting AI Responses After Approval?
```
.aialist            (verify they're approved)
.ai off             (disable AI if you don't want auto-replies)
```

### Want to Remove All Approvals?
```
.aialist            (see all approved users)
.aid                (disapprove individually by replying to their messages)
```

---

## 📊 Status Indicators

### AI Status
- ✅ = Enabled
- ❌ = Disabled
- 🌙 = AI AFK active

### User Status
- ✅ Approved = No AI gating
- 🚫 Disapproved = AI will gate again
- Pending = Currently in AI conversation

---

## 🎨 Example Workflows

### Workflow 1: New User Management
```
1. User DMs you
2. AI PM Permit responds
3. You check the conversation
4. Reply to their message: .aia
5. User is approved
6. They can now chat normally
```

### Workflow 2: Information Sharing
```
Friend: "What's your portfolio?"
You: .ask what is my portfolio?
AI: Your portfolio is at https://henokenyew.me...
[Share AI's response]
```

### Workflow 3: Code Review
```
1. Someone posts code
2. Reply to it: .ask review this code
3. AI provides analysis
4. Share insights with the team
```

---

## 🔐 Privacy & Security

**What AI Shares:**
- ✅ Portfolio URL
- ✅ GitHub, LinkedIn, LeetCode
- ✅ Telegram username
- ✅ Skills and experience
- ✅ Projects and education
- ✅ Phone number (ONLY when asked for contact info)

**What AI Never Shares:**
- ❌ Personal email
- ❌ Private conversations
- ❌ Passwords or sensitive data

**Phone Number Policy:**
- Shared only when users explicitly ask for contact information
- Not mentioned in casual conversations
- Appropriate for professional contact requests

---

## 📞 Your Public Links

The AI will share these when asked:
- Portfolio: https://henokenyew.me
- GitHub: https://github.com/henok-enyew
- LinkedIn: https://www.linkedin.com/in/henokenyew/
- LeetCode: https://leetcode.com/henokenyew
- Telegram: @henokenyew
- Phone: +251904927815 (when asked for contact)

---

## 🆘 Need Help?

Check status:
```
.ai status
.aipmpermit status
```

View approved users:
```
.aialist
```

Test AI:
```
.ask hello
```
