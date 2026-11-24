#!/data/data/com.termux/files/usr/bin/bash
# // GREEN PHONE EDIT
# v3: uses the named Cloudflare tunnel "greenscreen" at a fixed address.
# The address comes from GS_HOST in greenscreen.env.
cd ~/greenscreen || exit 1
set -a; . ./greenscreen.env; set +a
if [ -z "$GS_HOST" ]; then echo "GS_HOST is missing from greenscreen.env"; exit 1; fi
termux-wake-lock
pkill -f greenscreen_v
pkill -f "cloudflared tunnel"
sleep 1
nohup python greenscreen_v2_2026-11-24.py > server.log 2>&1 &
nohup cloudflared tunnel --no-autoupdate run --url 127.0.0.1:8765 greenscreen > tunnel.log 2>&1 &
echo ""
echo "Crock Pot address: $GS_HOST/$GS_TOKEN/"
