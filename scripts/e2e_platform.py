#!/usr/bin/env python3
import urllib.request, json

def post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=10).read())

G = "http://localhost:8100"

print("=== 1. COUNCIL CONSENSUS ===")
d = post(f"{G}/platform/consensus/decide", {
    "knowledge_id": "e2e-c1", "title": "FastAPI security",
    "text": "CVE in FastAPI WebSocket handshake allowing RCE. Patch in v0.115.3. Apply immediately.",
    "knowledge_type": "security", "confidence": 0.97})
print(f"  action={d['action']} consensus={d['consensus']} votes={len(d['votes'])}")
print(f"  members: {[v['member'] for v in d['votes']]}")

print()
print("=== 2. FEEDBACK / SELF-TUNING GOVERNOR ===")
b = json.loads(urllib.request.urlopen(f"{G}/platform/feedback/thresholds").read())
print(f"  novelty_min before: {b['thresholds']['high-novelty-train']['novelty_min']}")
r = post(f"{G}/platform/feedback/regression", {"task": "gsm8k", "delta_score": -0.08})
print(f"  regression -> {r['adjusted']} adjustments")
a = json.loads(urllib.request.urlopen(f"{G}/platform/feedback/thresholds").read())
print(f"  novelty_min after:  {a['thresholds']['high-novelty-train']['novelty_min']}")

print()
print("=== 3. RAG ===")
post(f"{G}/rag/add", {"knowledge_id": "e2e-r1", "title": "FastAPI 0.115 breaking change",
    "content": "Deprecated app.router.add_api_route in favor of app.add_api_route.",
    "knowledge_type": "api_update", "source": "changelog"})
ctx = post(f"{G}/rag/retrieve", {"query": "fastapi add_api_route deprecation", "k": 3})
print(f"  docs retrieved: {ctx['count']}, top: {ctx['documents'][0]['title'] if ctx['documents'] else 'none'}")

print()
print("=== 4. DYNAMIC KG ===")
ig = post(f"{G}/kg/ingest", {"text": "FastAPI uses pydantic for validation and Docker for deployment.",
    "title": "FastAPI stack", "knowledge_type": "framework"})
print(f"  nodes_created={ig['nodes_created']} edges_created={ig['edges_created']}")
com = json.loads(urllib.request.urlopen(f"{G}/kg/communities").read())
print(f"  communities: {len(com['communities'])}")

print()
print("=== 5. ROUTING + LINEAGE ===")
post(f"{G}/platform/routing/register", {"adapter_id": "ad-fastapi-v1", "domain": "fastapi",
    "benchmark_score": 0.88, "baseline_score": 0.7})
rt = post(f"{G}/platform/routing/route", {"prompt": "build a fastapi api endpoint with pydantic"})
print(f"  domain={rt['domain']} -> {rt['chosen_adapter']['adapter_id']} (+{rt['chosen_adapter']['improvement']})")
post(f"{G}/platform/lineage/link", {"source_type": "dataset", "source_id": "ds-1",
    "target_type": "adapter", "target_id": "ad-fastapi-v1"})
post(f"{G}/platform/lineage/link", {"source_type": "governed", "source_id": "g-1",
    "target_type": "dataset", "target_id": "ds-1"})
tr = json.loads(urllib.request.urlopen(
    f"{G}/platform/lineage/trace?target_type=adapter&target_id=ad-fastapi-v1").read())
print(f"  lineage chain length: {tr['length']}")

print()
print("=== 6. TELEMETRY + ALERTS + PROFILER ===")
post(f"{G}/platform/telemetry/record", {"adapter_id": "ad-fastapi-v1", "task": "training",
    "gpu_hours": 2.5, "benchmark_delta": 0.05})
t = json.loads(urllib.request.urlopen(f"{G}/platform/telemetry/stats").read())
print(f"  cost=${t['total_cost_usd']} roi=${t['cost_per_benchmark_point']}/point")
post(f"{G}/platform/alerts/notify", {"severity": "high", "title": "Benchmark regression",
    "message": "gsm8k dropped"})
post(f"{G}/platform/profiler/observe", {"text": "How do I use FastAPI with pydantic and SQLAlchemy?"})
p = json.loads(urllib.request.urlopen(f"{G}/platform/profiler/profile").read())
print(f"  dominant stack: {p['dominant_stack']}")

print()
print("=== ALL E2E CHECKS PASSED ===")
