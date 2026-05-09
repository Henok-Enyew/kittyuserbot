#!/usr/bin/env python3
"""
Test script for AI Assistant module
Verifies that all components are properly configured
"""

import sys
import os
import asyncio

# Add userbot to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("🧪 Testing AI Assistant Module")
print("=" * 50)
print()

# Test 1: Import modules
print("Test 1: Importing modules...")
try:
    from userbot.ai_assistant import get_ai_provider, ConversationEngine, AIState
    from userbot.ai_assistant.state import ai_state
    print("✅ All modules imported successfully")
except Exception as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

print()

# Test 2: Check environment variables
print("Test 2: Checking environment variables...")
AI_API_KEY = os.environ.get("AI_API_KEY")
AI_PROVIDER = os.environ.get("AI_PROVIDER", "mistral")
AI_USER_NAME = os.environ.get("ALIVE_NAME", "Henok")

if not AI_API_KEY:
    print("❌ AI_API_KEY not set!")
    print("   Set it with: export AI_API_KEY='your_key_here'")
    sys.exit(1)

print(f"✅ AI_API_KEY: {AI_API_KEY[:10]}...")
print(f"✅ AI_PROVIDER: {AI_PROVIDER}")
print(f"✅ ALIVE_NAME: {AI_USER_NAME}")
print()

# Test 3: Initialize provider
print("Test 3: Initializing AI provider...")
try:
    provider = get_ai_provider(AI_PROVIDER, AI_API_KEY)
    print(f"✅ Provider initialized: {provider.get_provider_name()}")
except Exception as e:
    print(f"❌ Provider initialization failed: {e}")
    sys.exit(1)

print()

# Test 4: Initialize conversation engine
print("Test 4: Initializing conversation engine...")
try:
    conv_engine = ConversationEngine(user_name=AI_USER_NAME)
    print(f"✅ Conversation engine initialized for {AI_USER_NAME}")
except Exception as e:
    print(f"❌ Conversation engine initialization failed: {e}")
    sys.exit(1)

print()

# Test 5: Test state management
print("Test 5: Testing state management...")
try:
    # Test global enable/disable
    ai_state.enable_global()
    assert ai_state.global_enabled == True
    ai_state.disable_global()
    assert ai_state.global_enabled == False
    
    # Test per-chat enable/disable
    test_chat_id = 12345
    ai_state.enable_chat(test_chat_id)
    assert test_chat_id in ai_state.enabled_chats
    ai_state.disable_chat(test_chat_id)
    assert test_chat_id not in ai_state.enabled_chats
    
    # Test new chat detection
    assert ai_state.is_new_chat(test_chat_id) == True
    ai_state.mark_chat_known(test_chat_id)
    assert ai_state.is_new_chat(test_chat_id) == False
    
    # Test cooldown
    assert ai_state.can_respond(test_chat_id) == True
    ai_state.mark_response(test_chat_id)
    assert ai_state.can_respond(test_chat_id) == False
    
    print("✅ State management working correctly")
except Exception as e:
    print(f"❌ State management test failed: {e}")
    sys.exit(1)

print()

# Test 6: Test conversation building
print("Test 6: Testing conversation building...")
try:
    messages = conv_engine.build_messages(
        current_message="Hello, how are you?",
        chat_history=[],
        is_new_chat=True,
        is_afk=False,
        style_examples=["Hey!", "What's up?"]
    )
    
    assert len(messages) >= 2  # System + user message
    assert messages[0]["role"] == "system"
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == "Hello, how are you?"
    
    print(f"✅ Built {len(messages)} messages correctly")
except Exception as e:
    print(f"❌ Conversation building test failed: {e}")
    sys.exit(1)

print()

# Test 7: Test AI API call (optional - requires valid API key)
print("Test 7: Testing AI API call...")
print("   (This will make a real API call)")

async def test_api_call():
    try:
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Hello World' and nothing else."}
        ]
        
        response = await provider.generate_response(
            messages=messages,
            temperature=0.7,
            max_tokens=50
        )
        
        print(f"✅ API call successful!")
        print(f"   Response: {response[:100]}...")
        return True
    except Exception as e:
        print(f"❌ API call failed: {e}")
        return False

# Run async test
try:
    result = asyncio.run(test_api_call())
    if not result:
        print("   Note: API call failed, but module structure is OK")
except Exception as e:
    print(f"   Note: Could not test API call: {e}")

print()
print("=" * 50)
print("🎉 All tests completed!")
print()
print("✅ AI Assistant module is ready to use")
print()
print("Next steps:")
print("1. Configure your userbot (config.py)")
print("2. Run: ./run_with_ai.sh")
print("3. In Telegram, use: .ai on")
print()
