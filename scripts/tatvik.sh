#!/usr/bin/env bash
# Tatvik platform control — manage all five services via systemd user units.
#
# Usage:
#   ./scripts/tatvik.sh status     — show service + port status
#   ./scripts/tatvik.sh start      — start all services
#   ./scripts/tatvik.sh stop       — stop all services
#   ./scripts/tatvik.sh restart    — restart all services
#   ./scripts/tatvik.sh logs       — tail logs for all services
#   ./scripts/tatvik.sh build      — rebuild the Next.js frontend and restart it
#   ./scripts/tatvik.sh verify     — run scripts/verify.sh end-to-end check
set -u

UNIT_DIR="$HOME/.config/systemd/user"
SERVICES=(tatvik-llama.service tatvik-api.service governor.service hermes.service tatvik-front.service)
PORTS=(11434 8000 8100 8101 3000)
PATHS=(/health /system/health /health /health /chat)
NAMES=("llama-server" "Tatvik API" "Governor" "Hermes" "Frontend")

log() { echo -e "\033[1;32m[tatvik]\033[0m $*"; }
err() { echo -e "\033[1;31m[tatvik]\033[0m $*"; }

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
  status) status ;;
  start)  start ;;
  stop)   stop ;;
  restart) restart ;;
  logs)   logs ;;
  build)  build ;;
  verify) verify ;;
  *) echo "usage: $0 {status|start|stop|restart|logs|build|verify}" >&2; exit 1 ;;
esac
