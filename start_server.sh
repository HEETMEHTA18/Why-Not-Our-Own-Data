#!/bin/bash
cd /home/heet18/Documents/Why-Not-Our-Own-Data

# Kill any existing processes
pkill -f "llama-server" 2>/dev/null || true
pkill -f "uvicorn" 2>/dev/null || true
sleep 1

# Start llama-server with the GGUF model for inference
nohup /home/heet18/.hyperspace/bin/llama-server \
  -m /tmp/qwen-coder.gguf \
  --port 11434 \
  -c 4096 \
  --n-gpu-layers 99 \
  --no-webui \
  --host 0.0.0.0 \
  > /tmp/llama-server.log 2>&1 &
echo "llama-server starting on :11434 ..."
sleep 2

# Start Tatvik API server (proxies to llama-server, hosts Sahapatha)
source .venv/bin/activate
# Run from tatvik/ directory so imports like 'from api.deps' resolve
cd tatvik
PYTHONPATH="..:$PYTHONPATH" nohup python3 -m uvicorn api.app:app --host 0.0.0.0 --port 8000 > /tmp/tatvik.log 2>&1 &
echo "Tatvik API starting on :8000 ..."
cd ..
sleep 2

# Start Next.js frontend
nohup npx next dev -p 3000 > /tmp/frontend.log 2>&1 &
echo "Frontend starting on :3000 ..."
sleep 2

# Start Governor API server (data intelligence, agents, knowledge graph)
cd /home/heet18/Documents/Why-Not-Our-Own-Data
source .venv/bin/activate
nohup python3 -m uvicorn governor.main:app --host 0.0.0.0 --port 8100 > /tmp/governor.log 2>&1 &
echo "Governor API starting on :8100 ..."
sleep 2

# Start Hermes orchestrator (multi-agent pipelines)
nohup python3 -m uvicorn hermes.api:app --host 0.0.0.0 --port 8101 > /tmp/hermes.log 2>&1 &
echo "Hermes Orchestrator starting on :8101 ..."

echo ""
echo "=== Tatvik Platform ==="
echo "llama-server (inference): http://localhost:11434"
echo "Tatvik API:              http://localhost:8000"
echo "Sahapatha UI:            http://localhost:8000/sahapatha/ui"
echo "Governor API:            http://localhost:8100"
echo "Hermes Orchestrator:     http://localhost:8101"
echo "Frontend:                http://localhost:3000"
