#!/bin/bash
# Restart governor + hermes backend services
cd /home/heet18/Documents/Why-Not-Our-Own-Data
source .venv/bin/activate

pkill -f "uvicorn governor.main" 2>/dev/null
pkill -f "uvicorn hermes.api" 2>/dev/null
sleep 2

mkdir -p /tmp/hermes_logs

setsid nohup python3 -m uvicorn governor.main:app --host 0.0.0.0 --port 8100 --log-level warning \
  > /tmp/hermes_logs/governor.log 2>&1 < /dev/null &
echo "governor PID: $!"

setsid nohup python3 -m uvicorn hermes.api:app --host 0.0.0.0 --port 8101 --log-level warning \
  > /tmp/hermes_logs/hermes.log 2>&1 < /dev/null &
echo "hermes PID: $!"

sleep 5
for p in 8100 8101; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$p/health")
  echo "port $p -> $code"
done