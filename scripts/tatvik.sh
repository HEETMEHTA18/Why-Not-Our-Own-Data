#!/usr/bin/env bash
# Tatvik platform control — manage all five services via systemd user units.
#
# Usage:
#   ./scripts/tatvik.sh up         — full one-shot: install units, ensure .env, build frontend, start all
#   ./scripts/tatvik.sh status     — show service + port status
#   ./scripts/tatvik.sh start      — start all services
#   ./scripts/tatvik.sh stop       — stop all services
#   ./scripts/tatvik.sh restart    — restart all services
#   ./scripts/tatvik.sh logs       — tail logs for all services
#   ./scripts/tatvik.sh build      — rebuild the Next.js frontend and restart it
#   ./scripts/tatvik.sh verify     — run scripts/verify.sh end-to-end check
set -u

REPO="$(cd "$(dirname "$0")/.." && pwd)"
UNIT_DIR="$HOME/.config/systemd/user"
SERVICES=(tatvik-llama.service tatvik-api.service governor.service hermes.service tatvik-front.service)
PORTS=(11434 8000 8100 8101 3000)
PATHS=(/health /system/health /health /health /chat)
NAMES=("llama-server" "Tatvik API" "Governor" "Hermes" "Frontend")
VENV="$REPO/.venv"
PY="$VENV/bin/python"
NODE="$(command -v node || echo /usr/bin/node)"
NPM="$(command -v npm || echo /usr/bin/npm)"
LLAMA_BIN="$(command -v llama-server || echo "$HOME/cuda-12.8/llama-server")"
CUDA_LIB="$HOME/cuda-12.8"
MODEL="$REPO/models/qwen2.5-coder-3b-instruct-q4_k_m.gguf"

log() { echo -e "\033[1;32m[tatvik]\033[0m $*"; }
err() { echo -e "\033[1;31m[tatvik]\033[0m $*"; }

write_units() {
  mkdir -p "$UNIT_DIR"
  local cuda_libs
  cuda_libs="$CUDA_LIB:$VENV/lib/python3.12/site-packages/nvidia/cuda_runtime/lib"
  for d in cublas cudnn curand cusolver cusparse nccl nvjitlink; do
    [ -d "$VENV/lib/python3.12/site-packages/nvidia/$d/lib" ] && cuda_libs="$cuda_libs:$VENV/lib/python3.12/site-packages/nvidia/$d/lib"
  done

  cat > "$UNIT_DIR/tatvik-llama.service" <<EOF
[Unit]
Description=Tatvik llama-server
After=network.target

[Service]
Type=simple
WorkingDirectory=$REPO
Environment="LD_LIBRARY_PATH=$cuda_libs"
ExecStart=$LLAMA_BIN -m $MODEL --host 0.0.0.0 --port 11434 -ngl 99 -c 4096
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
EOF

  cat > "$UNIT_DIR/tatvik-api.service" <<EOF
[Unit]
Description=Tatvik AI Runtime API
After=network.target tatvik-llama.service

[Service]
Type=simple
WorkingDirectory=$REPO
Environment="PATH=$VENV/bin:/usr/bin:/bin"
ExecStart=$PY tatvik/run.py
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
EOF

  cat > "$UNIT_DIR/governor.service" <<EOF
[Unit]
Description=Tatvik Governor (data intelligence, agents, KG)
After=network.target tatvik-api.service

[Service]
Type=simple
WorkingDirectory=$REPO
Environment="PATH=$VENV/bin:/usr/bin:/bin"
ExecStart=$PY -m uvicorn governor.main:app --host 0.0.0.0 --port 8100 --log-level warning
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
EOF

  cat > "$UNIT_DIR/hermes.service" <<EOF
[Unit]
Description=Hermes Multi-Agent Orchestrator
After=network.target

[Service]
Type=simple
WorkingDirectory=$REPO
Environment="PATH=$VENV/bin:/usr/bin:/bin"
ExecStart=$PY -m hermes start
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF

  cat > "$UNIT_DIR/tatvik-front.service" <<EOF
[Unit]
Description=Tatvik Next.js Frontend
After=network.target tatvik-api.service

[Service]
Type=simple
WorkingDirectory=$REPO
Environment="PATH=$(dirname "$NODE"):/usr/bin:/bin"
Environment="PORT=3000"
ExecStart=$NPM run start
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
EOF

  systemctl --user daemon-reload
  log "installed 5 systemd units in $UNIT_DIR"
}

up() {
  log "bootstrapping Tatvik ($REPO)..."
  [ -x "$PY" ] || { err "venv missing at $VENV — create it and install deps first"; exit 1; }
  [ -f "$MODEL" ] || { err "model missing at $MODEL — download qwen2.5-coder-3b-instruct-q4_k_m.gguf first"; exit 1; }
  [ -f "$REPO/.env" ] || { log ".env missing — copying from .env.example (fill in real keys after)"; cp "$REPO/.env.example" "$REPO/.env"; }

  write_units

  if [ ! -d "$REPO/node_modules/.bin" ]; then
    log "installing frontend deps..."
    npm install || { err "npm install failed"; exit 1; }
  fi
  if [ ! -d "$REPO/.next" ]; then
    build
  fi

  systemctl --user enable --now tatvik-llama.service tatvik-api.service governor.service hermes.service tatvik-front.service
  log "waiting for llama-server to load model (~20s)..."
  sleep 20
  for s in "${SERVICES[@]}"; do
    systemctl --user is-active "$s" >/dev/null || err "WARNING: $s not active"
  done
  status
}

status() {
  log "service status:"
  for s in "${SERVICES[@]}"; do
    printf "  %-24s %s\n" "$s" "$(systemctl --user is-active "$s" 2>/dev/null || echo missing)"
  done
  log "port liveness:"
  for i in "${!PORTS[@]}"; do
    code=$(curl -s -o /dev/null -w "%{http_code}" -m 2 "http://localhost:${PORTS[$i]}${PATHS[$i]}" 2>/dev/null)
    printf "  %-18s :%-6s HTTP %s\n" "${NAMES[$i]}" "${PORTS[$i]}" "${code:-down}"
  done
}

start() {
  log "starting all services..."
  systemctl --user daemon-reload
  for s in "${SERVICES[@]}"; do
    systemctl --user start "$s" && log "started $s"
  done
}

stop() {
  log "stopping all services..."
  for s in "${SERVICES[@]}"; do
    systemctl --user stop "$s" && log "stopped $s"
  done
}

restart() {
  log "restarting all services..."
  systemctl --user daemon-reload
  for s in "${SERVICES[@]}"; do
    systemctl --user restart "$s" && log "restarted $s"
  done
  log "waiting for llama-server to reload the model..."
  sleep 20
  status
}

logs() {
  log "tailing logs (Ctrl-C to stop)..."
  journalctl --user -f -u tatvik-llama.service -u tatvik-api.service -u governor.service -u hermes.service -u tatvik-front.service
}

build() {
  log "building frontend..."
  npm run build || { err "build failed"; exit 1; }
  systemctl --user restart tatvik-front.service && log "frontend restarted"
}

verify() {
  bash scripts/verify.sh
}

case "${1:-status}" in
  up)     up ;;
  status) status ;;
  start)  start ;;
  stop)   stop ;;
  restart) restart ;;
  logs)   logs ;;
  build)  build ;;
  verify) verify ;;
  *) echo "usage: $0 {up|status|start|stop|restart|logs|build|verify}" >&2; exit 1 ;;
esac
