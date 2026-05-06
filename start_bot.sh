#!/bin/bash
source venv/bin/activate
set -a
source .env
set +a
python3 -m userbot 2>&1 | tee userbot_live.log
