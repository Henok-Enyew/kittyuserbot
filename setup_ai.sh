#!/bin/bash

# AI Assistant Setup Script for CatUserbot
# This script helps configure the AI assistant

echo "🤖 AI Assistant Setup for CatUserbot"
echo "===================================="
echo ""

# Check if running in virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: Not running in a virtual environment"
    echo "   It's recommended to use a virtual environment"
    echo ""
fi

# Function to set environment variable
set_env_var() {
    local var_name=$1
    local var_value=$2
    
    # Check if .env file exists
    if [ -f .env ]; then
        # Update existing or add new
        if grep -q "^${var_name}=" .env; then
            sed -i "s|^${var_name}=.*|${var_name}=${var_value}|" .env
        else
            echo "${var_name}=${var_value}" >> .env
        fi
    else
        # Create new .env file
        echo "${var_name}=${var_value}" > .env
    fi
}

# Get API Key
echo "📝 Configuration"
echo ""
read -p "Enter your Mistral AI API Key: " api_key

if [ -z "$api_key" ]; then
    echo "❌ API key is required!"
    exit 1
fi

# Get user name
read -p "Enter your name (default: Henok): " user_name
user_name=${user_name:-Henok}

# Get provider
echo ""
echo "Select AI Provider:"
echo "1) Mistral AI (recommended)"
echo "2) NVIDIA AI"
read -p "Choice (1 or 2): " provider_choice

case $provider_choice in
    1)
        provider="mistral"
        ;;
    2)
        provider="nvidia"
        ;;
    *)
        provider="mistral"
        echo "Invalid choice, using Mistral AI"
        ;;
esac

# Set environment variables
echo ""
echo "💾 Saving configuration..."
set_env_var "AI_API_KEY" "$api_key"
set_env_var "AI_PROVIDER" "$provider"
set_env_var "ALIVE_NAME" "$user_name"

# Export for current session
export AI_API_KEY="$api_key"
export AI_PROVIDER="$provider"
export ALIVE_NAME="$user_name"

echo "✅ Configuration saved to .env file"
echo ""

# Show configuration
echo "📋 Current Configuration:"
echo "   AI Provider: $provider"
echo "   User Name: $user_name"
echo "   API Key: ${api_key:0:10}..."
echo ""

# Check if userbot is running
if pgrep -f "python.*__main__.py" > /dev/null; then
    echo "⚠️  Userbot is currently running"
    read -p "Do you want to restart it? (y/n): " restart
    if [ "$restart" = "y" ]; then
        echo "🔄 Restarting userbot..."
        pkill -f "python.*__main__.py"
        sleep 2
        nohup python3 -m userbot > userbot.log 2>&1 &
        echo "✅ Userbot restarted"
    fi
else
    echo "ℹ️  Userbot is not running"
    read -p "Do you want to start it? (y/n): " start
    if [ "$start" = "y" ]; then
        echo "🚀 Starting userbot..."
        nohup python3 -m userbot > userbot.log 2>&1 &
        echo "✅ Userbot started"
    fi
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📖 Quick Start:"
echo "   .ai on          - Enable AI globally"
echo "   .ai enable      - Enable AI for current chat"
echo "   .ai status      - Check AI status"
echo ""
echo "📚 Read AI_ASSISTANT_README.md for full documentation"
