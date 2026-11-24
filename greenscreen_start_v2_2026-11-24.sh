#!/data/data/com.termux/files/usr/bin/bash
# // GREEN PHONE EDIT
cd ~/greenscreen || exit 1
set -a; . ./greenscreen.env; set +a
termux-wake-lock
pkill -f greenscreen_v
pkill -f "cloudflared tunnel"
sleep 1
nohup python greenscreen_v2_2026-11-24.py > server.log 2>&1 &
rm -f tunnel.log
nohup cloudflared tunnel --no-autoupdate --url 127.0.0.1:8765 > tunnel.log 2>&1 &
HOST=""
for i in $(seq 1 60); do
  HOST=$(grep -o '[a-z0-9-]*\.trycloudflare\.com' tunnel.log | head -n1)
  [ -n "$HOST" ] && break
  sleep 1
done
if [ -z "$HOST" ]; then echo "Tunnel did not come up. Run this script again."; exit 1; fi
echo ""
echo "SAVE THIS (give to Crock Pot): $HOST/$GS_TOKEN/"
