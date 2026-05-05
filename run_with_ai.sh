#!/bin/bash

# Complete setup and run script for CatUserbot with AI Assistant
# This script handles everything: venv, dependencies, config, and running

set -e  # Exit on error

echo "🐱 CatUserbot with AI Assistant - Complete Setup"
echo "=================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# Check Python version
print_info "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed!"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
print_success "Python $PYTHON_VERSION found"
echo ""

# Step 1: Virtual Environment
print_info "Step 1: Setting up virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_info "Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate
print_success "Virtual environment activated"
echo ""

# Step 2: Install Dependencies
print_info "Step 2: Installing dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt
print_success "Dependencies installed"
echo ""

# Step 3: Configure AI
print_info "Step 3: AI Assistant Configuration"
echo ""

# Check if .env exists and has AI_API_KEY
if [ -f .env ] && grep -q "^AI_API_KEY=" .env; then
    print_info "AI configuration found in .env"
    source .env
else
    print_info "Setting up AI configuration..."
    
    # Use provided API key
    AI_API_KEY="HI0kplM0ehgLKhjZ94TKfch2xrakwWVf"
    AI_PROVIDER="mistral"
    ALIVE_NAME="Henok"
    
    # Create/update .env
    echo "AI_API_KEY=$AI_API_KEY" >> .env
    echo "AI_PROVIDER=$AI_PROVIDER" >> .env
    echo "ALIVE_NAME=$ALIVE_NAME" >> .env
    
    print_success "AI configuration saved"
fi

# Export variables
export AI_API_KEY="${AI_API_KEY:-HI0kplM0ehgLKhjZ94TKfch2xrakwWVf}"
export AI_PROVIDER="${AI_PROVIDER:-mistral}"
export ALIVE_NAME="${ALIVE_NAME:-Henok}"

echo ""
print_success "AI Provider: $AI_PROVIDER"
print_success "User Name: $ALIVE_NAME"
print_success "API Key: ${AI_API_KEY:0:10}..."
echo ""

# Step 4: Check Userbot Configuration
print_info "Step 4: Checking userbot configuration..."

if [ ! -f "config.py" ]; then
    print_error "config.py not found!"
    echo ""
    echo "Please create config.py with your Telegram credentials:"
    echo "1. Copy sample: cp sample_config.py config.py"
    echo "2. Get APP_ID and API_HASH from https://my.telegram.org"
    echo "3. Generate STRING_SESSION: python3 stringsetup.py"
    echo "4. Get TG_BOT_TOKEN from @BotFather"
    echo "5. Get DATABASE_URL from elephantsql.com"
    echo ""
    read -p "Do you want to copy sample_config.py now? (y/n): " copy_config
    if [ "$copy_config" = "y" ]; then
        cp sample_config.py config.py
        print_success "config.py created from sample"
        print_info "Please edit config.py and add your credentials, then run this script again"
        exit 0
    else
        exit 1
    fi
else
    print_success "config.py found"
fi
echo ""

# Step 5: Verify AI Module
print_info "Step 5: Verifying AI module..."
if [ -d "userbot/ai_assistant" ]; then
    print_success "AI assistant module found"
else
    print_error "AI assistant module not found!"
    exit 1
fi
echo ""

# Step 6: Run Userbot
print_info "Step 6: Starting userbot..."
echo ""
echo "=================================================="
echo "🚀 Launching CatUserbot with AI Assistant"
echo "=================================================="
echo ""
echo "📝 Quick Commands:"
echo "   .ai on       - Enable AI globally"
echo "   .ai enable   - Enable AI for current chat"
echo "   .ai status   - Check AI status"
echo ""
echo "📖 Full docs: AI_ASSISTANT_README.md"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Run userbot
python3 -m userbot
