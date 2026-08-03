#!/usr/bin/env bash
# Tatvik local feature verification — tests all services and endpoints.
set -u

API=http://localhost:8000
LLAMA=http://localhost:11434
HERMES=http://localhost:8101
WEB=http://localhost:3000
MODEL=/home/heet18/Documents/Why-Not-Our-Own-Data/models/qwen2.5-coder-3b-instruct-q4_k_m.gguf

PASS=0; FAIL=0
ok()   { echo "  ✓ $1"; PASS=$((PASS+1)); }
fail() { echo "  ✗ $1"; FAIL=$((FAIL+1)); }
check() { # check <name> <curl args...> <expect>
  local name="$1"; shift
  local expect="$1"; shift
  local out; out=$(curl -s -o /tmp/tv.out -w '%{http_code}' "$@" 2>/dev/null)
  if [ "$out" = "$expect" ]; then ok "$name (HTTP $out)"; else fail "$name (got HTTP $out, want $expect)"; fi
}

echo "=== Service liveness ==="
check "llama-server :11434" 200 "$LLAMA/v1/models"
check "Tatvik API   :8000"  200 "$API/system/health"
check "Hermes       :8101"  200 "$HERMES/health"
check "Frontend     :3000"  200 "$WEB/chat"

echo
echo "=== Chat & system prompt ==="
REPLY=$(curl -s -X POST "$API/models/chat" -H 'Content-Type: application/json' \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"system\",\"content\":\"You are Tatvik, built by Heet Mehta at Autodevs.\"},{\"role\":\"user\",\"content\":\"Who built you?\"}],\"stream\":false}" \
  | python3 -c "import sys,json;print(json.load(sys.stdin).get('message',{}).get('content',''))" 2>/dev/null)
if echo "$REPLY" | grep -qi "heet\|tatvik\|autodev"; then ok "System prompt identity: '$REPLY'"; else fail "System prompt identity (got: '$REPLY')"; fi

echo
echo "=== Streaming (SSE) ==="
if curl -s -N -X POST "$API/models/chat/stream" -H 'Content-Type: application/json' \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"say hi\"}],\"stream\":true}" \
  | grep -q "data: "; then ok "Streaming emits data: chunks"; else fail "Streaming"; fi

echo
echo "=== RAG context search ==="
if curl -s -X POST "$API/models/context" -H 'Content-Type: application/json' \
  -d '{"query":"gpu monitor","max_results":2}' | python3 -c "import sys,json;d=json.load(sys.stdin);sys.exit(0 if len(d.get('snippets',[]))>0 else 1)" 2>/dev/null; then
  ok "Codebase context search returns snippets"; else fail "Context search"; fi

echo
echo "=== Web search ==="
if curl -s -X POST "$API/models/websearch" -H 'Content-Type: application/json' \
  -d '{"query":"python programming","max_results":2,"fetch_content":false}' | python3 -c "import sys,json;d=json.load(sys.stdin);sys.exit(0 if len(d.get('results',[]))>0 else 1)" 2>/dev/null; then
  ok "Web search returns results"; else fail "Web search"; fi

echo
echo "=== Sahapatha training ==="
STATUS=$(curl -s "$API/sahapatha/status")
echo "  status: $(echo "$STATUS" | python3 -c "import sys,json;d=json.load(sys.stdin);print('buffer=%s versions=%s latest=v%s'%(d['buffer_size'],d['total_versions'],d['latest_version']))" 2>/dev/null)"
if curl -s -X POST "$API/sahapatha/chat" -H 'Content-Type: application/json' \
  -d '{"prompt":"Write a lambda to add two numbers","max_new_tokens":80}' \
  | grep -q '"status":"ok"'; then ok "Trained model chat (v4 adapter) responds"; else fail "Trained model chat"; fi

echo
echo "=== Kronos forecast ==="
check "Forecast tickers" 200 "$API/forecast/tickers"
if curl -s -X POST "$API/forecast/predict" -H 'Content-Type: application/json' \
  -d '{"ticker":"RELIANCE.NS","steps":3}' | python3 -c "import sys,json;d=json.load(sys.stdin);sys.exit(0 if d.get('actual_close') and d.get('predicted_close') else 1)" 2>/dev/null; then
  ok "Forecast predict returns data"; else fail "Forecast predict"; fi

echo
echo "=== Hermes agents ==="
if curl -s "$HERMES/status" | python3 -c "import sys,json;d=json.load(sys.stdin);sys.exit(0 if len(d.get('agents',[]))==8 else 1)" 2>/dev/null; then
  ok "Hermes: 8 agents registered"; else fail "Hermes agents"; fi
if curl -s -X POST "$HERMES/agents/run" -H 'Content-Type: application/json' \
  -d '{"agent_id":"quality-1"}' | grep -q '"status":"completed"'; then
  ok "Hermes: quality-1 agent executes"; else fail "Hermes agent run"; fi

echo
echo "=== GPU monitor ==="
curl -s "$API/system/gpu" | python3 -c "import sys,json;d=json.load(sys.stdin);g=d['gpus'][0];print(f'  {g[\"name\"]} | {d[\"avg_memory_mb\"]:.0f}/{d[\"total_memory_mb\"]} MB | {g[\"temperature_c\"]}C')" 2>/dev/null

echo
echo "=== RESULTS: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ] && echo "All features operational ✓" || echo "Fix the failures above."
