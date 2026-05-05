#!/bin/bash
source venv/bin/activate
set -a
source .env
set +a
exec python3 -m userbot
