#!/usr/bin/env python3
import sys
import os

# Set environment
os.environ["AI_API_KEY"] = "HI0kplM0ehgLKhjZ94TKfch2xrakwWVf"
os.environ["AI_PROVIDER"] = "mistral"
os.environ["ALIVE_NAME"] = "Henok"

print("Testing AI module...")
from userbot.ai_assistant import get_ai_provider, ConversationEngine
from userbot.ai_assistant.state import ai_state

print("✅ Imports successful")

# Test provider
provider = get_ai_provider("mistral", os.environ["AI_API_KEY"])
print(f"✅ Provider: {provider.get_provider_name()}")

# Test conversation engine
conv = ConversationEngine("Henok")
print("✅ Conversation engine initialized")

# Test state
ai_state.enable_global()
print(f"✅ State management working")

print("\n🎉 All tests passed!")
