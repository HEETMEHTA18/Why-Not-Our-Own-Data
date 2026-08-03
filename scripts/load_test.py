#!/usr/bin/env python3
"""
Hermes + Governance Load Test Harness

Exercises the full stack under concurrent load:
  1. Governance decisions  — N concurrent POST /governor/govern (varied item mix)
  2. Agent concurrency     — multiple Hermes agents running side-by-side
  3. Pipeline concurrency  — multiple pipelines running at once
  4. Mixed workload        — everything simultaneously
  5. Event bus pressure    — total events before/after, queue depth, failures

Usage:
  python3 scripts/load_test.py --governance 200 --workers 16
  python3 scripts/load_test.py --agents 4 --pipelines 2 --quick
  python3 scripts/load_test.py --all --report /tmp/load_report.json
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

GOVERNOR_URL = "http://localhost:8100"
HERMES_URL = "http://localhost:8101"

# --- Sample knowledge items that exercise all four governance actions ---
SECURITY_ITEMS = [
    ("CVE-2026-1182", "Critical vulnerability in FastAPI's WebSocket handshake allowing RCE via crafted origin headers. Patch in v0.115.3.", "FastAPI security patch", "security", 0.98),
    ("JWT algorithm confusion", "If 'alg' header is not pinned to HS256/RS256, attackers can sign tokens with 'none' or HMAC keys.", "JWT hardening", "security", 0.95),
    ("SQL injection via f-strings", "Never interpolate user input into SQL strings; use parameterized queries.", "SQL injection prevention", "security", 0.92),
    ("Docker privilege escalation", "Running containers with --privileged allows host kernel escape. Use seccomp and read-only rootfs.", "Docker security", "security", 0.9),
]

API_ITEMS = [
    ("FastAPI 0.115 breaking change", "Deprecated `app.router.add_api_route` in favor of `app.add_api_route`. Old signature logs deprecation warning and will be removed in 0.120.", "FastAPI API update", "api_update", 0.9),
    ("React 19 use() hook", "`use()` can now be called inside loops and conditionals. Resources suspend the component tree.", "React API update", "api_update", 0.85),
    ("Next.js 15 caching defaults", "fetch requests are no longer cached by default. Opt-in with `next: { revalidate: 60 }`.", "Next.js deprecation", "deprecation", 0.88),
    ("Docker Compose v2 command", "`docker-compose` is deprecated; use `docker compose` subcommand.", "Docker deprecation", "deprecation", 0.95),
]

NOVEL_ITEMS = [
    ("Zero-copy tensor slicing", "Novel LoRA pattern: slice adapter weights zero-copy via memoryview for 3x faster gradient checkpointing with Unsloth on consumer GPUs.", "LoRA optimization framework", "framework", 0.8),
    ("KV-cache reuse across turns", "Emerging pattern: reuse KV cache between multi-turn training samples cuts epoch time 40% when sequences share a prefix.", "Training optimization framework", "framework", 0.75),
    ("Weight dequantized on-the-fly", "Dequantize LoRA base weights on the fly during inference to fit 70B on 24GB VRAM with 2% latency penalty.", "Inference optimization framework", "framework", 0.78),
]

GENERIC_ITEMS = [
    ("Basic git workflow", "git add, commit, push. Standard stuff.", "Git basics", "general", 0.4),
    ("What is Kubernetes", "Kubernetes is a container orchestration platform. It manages deployments, services, and scaling.", "K8s intro", "general", 0.5),
    ("Python list comprehension", "Comprehensions build lists in one line: [x*2 for x in range(10)].", "Python basics", "general", 0.3),
    ("Vague note about servers", "Some servers exist somewhere and do things. Not sure what though.", "Unclear note", "general", 0.2),
]

ALL_ITEMS = SECURITY_ITEMS + API_ITEMS + NOVEL_ITEMS + GENERIC_ITEMS


@dataclass
class RequestStats:
    total: int = 0
    success: int = 0
    failed: int = 0
    latencies: List[float] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def record(self, success: bool, latency_ms: float, error: str = ""):
        self.total += 1
        self.latencies.append(latency_ms)
        if success:
            self.success += 1
        else:
            self.failed += 1
            if error:
                self.errors.append(error)

    def summarize(self) -> Dict:
        ls = sorted(self.latencies) if self.latencies else []
        return {
            "total": self.total,
            "success": self.success,
            "failed": self.failed,
            "success_rate": f"{100 * self.success / self.total:.1f}%" if self.total else "n/a",
            "avg_ms": f"{statistics.mean(ls):.1f}" if ls else "n/a",
            "p50_ms": f"{ls[len(ls) // 2]:.1f}" if ls else "n/a",
            "p95_ms": f"{ls[int(len(ls) * 0.95)]:.1f}" if ls else "n/a",
            "max_ms": f"{max(ls):.1f}" if ls else "n/a",
            "throughput_rps": f"{len(ls) / (sum(ls) / 1000):.1f}" if sum(ls) > 0 else "n/a",
        }


def http_request(url: str, method: str = "GET", body: Optional[dict] = None,
                 timeout: float = 15) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {"ok": True, "status": resp.status, "body": json.loads(resp.read())}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "error": str(e), "body": None}
    except Exception as e:
        return {"ok": False, "status": 0, "error": str(e), "body": None}


def bench(name: str, fn: Callable, count: int, workers: int,
          stats: RequestStats, per_call: Optional[Callable] = None) -> RequestStats:
    print(f"\n--- {name} ---")
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(fn, i) for i in range(count)]
        for fut in as_completed(futures):
            result = fut.result()
            stats.record(result["ok"], result["latency_ms"], result.get("error", ""))
            if per_call and result["ok"]:
                per_call(result["body"])
    elapsed = time.perf_counter() - t0
    s = stats.summarize()
    s["wall_s"] = f"{elapsed:.1f}"
    print(json.dumps(s, indent=2))
    return stats


def run_governance_load(count: int, workers: int, items: List[tuple]) -> RequestStats:
    stats = RequestStats()
    action_dist: Dict[str, int] = {}

    def one(i: int) -> dict:
        kid, text, title, ktype, conf = items[i % len(items)]
        body = {
            "knowledge_id": f"load-{i}",
            "text": text,
            "title": title,
            "knowledge_type": ktype,
            "confidence": conf,
        }
        t0 = time.perf_counter()
        resp = http_request(f"{GOVERNOR_URL}/governor/govern", "POST", body, timeout=10)
        latency = (time.perf_counter() - t0) * 1000
        return {"ok": resp["ok"], "latency_ms": latency,
                "error": resp.get("error", ""), "body": resp.get("body")}

    def track(body: dict):
        action = body.get("action", "unknown")
        action_dist[action] = action_dist.get(action, 0) + 1

    bench("Governance decisions (concurrent /governor/govern)", one, count, workers, stats, track)
    print(f"  Decision distribution: {json.dumps(action_dist)}")
    stats.result_extra = {"decision_distribution": action_dist}  # type: ignore
    return stats


def run_agent_concurrency(agent_ids: List[str], rounds: int) -> RequestStats:
    stats = RequestStats()

    def one(i: int) -> dict:
        agent_id = agent_ids[i % len(agent_ids)]
        body = {"agent_id": agent_id}
        t0 = time.perf_counter()
        resp = http_request(f"{HERMES_URL}/agents/run", "POST", body, timeout=60)
        latency = (time.perf_counter() - t0) * 1000
        result = resp.get("body") or {}
        status = result.get("status", "")
        err = result.get("error") or ""
        return {"ok": resp["ok"] and status in ("completed",), "latency_ms": latency,
                "error": resp.get("error", "") or err[:120] if err else "",
                "body": result}

    bench(f"Agent concurrency (agents={agent_ids}, rounds={rounds})", one, len(agent_ids) * rounds,
          min(len(agent_ids), 4), stats)
    return stats


def run_pipeline_concurrency(pipelines: List[str], rounds: int) -> RequestStats:
    stats = RequestStats()

    def one(i: int) -> dict:
        pipeline = pipelines[i % len(pipelines)]
        body = {"pipeline_name": pipeline}
        t0 = time.perf_counter()
        resp = http_request(f"{HERMES_URL}/pipelines/run", "POST", body, timeout=90)
        latency = (time.perf_counter() - t0) * 1000
        result = resp.get("body") or {}
        return {"ok": resp["ok"], "latency_ms": latency,
                "error": resp.get("error", "") or str(result)[:120], "body": result}

    bench(f"Pipeline concurrency (pipelines={pipelines}, rounds={rounds})",
          one, len(pipelines) * rounds, min(len(pipelines), 3), stats)
    return stats


def run_read_mix(count: int, workers: int) -> RequestStats:
    read_endpoints = [
        (f"{GOVERNOR_URL}/kg/stats", "GET"),
        (f"{GOVERNOR_URL}/benchmarks/stats", "GET"),
        (f"{GOVERNOR_URL}/governor/stats", "GET"),
        (f"{GOVERNOR_URL}/scheduler/jobs", "GET"),
        (f"{HERMES_URL}/status", "GET"),
        (f"{HERMES_URL}/runs?limit=5", "GET"),
    ]
    stats = RequestStats()

    def one(i: int) -> dict:
        url, method = read_endpoints[i % len(read_endpoints)]
        t0 = time.perf_counter()
        resp = http_request(url, method, timeout=10)
        latency = (time.perf_counter() - t0) * 1000
        return {"ok": resp["ok"], "latency_ms": latency,
                "error": resp.get("error", ""), "body": resp.get("body")}

    bench(f"Read workload (mixed GETs x{count})", one, count, workers, stats)
    return stats


def run_mixed_workload(count: int, workers: int) -> RequestStats:
    jobs: List[Callable[[int], dict]] = [
        lambda i: governance_job(i),
        lambda i: read_job(i),
    ]

    def governance_job(i: int) -> dict:
        kid, text, title, ktype, conf = ALL_ITEMS[i % len(ALL_ITEMS)]
        t0 = time.perf_counter()
        resp = http_request(f"{GOVERNOR_URL}/governor/govern", "POST",
                            {"knowledge_id": f"mixed-{i}", "text": text, "title": title,
                             "knowledge_type": ktype, "confidence": conf}, timeout=10)
        return {"ok": resp["ok"], "latency_ms": (time.perf_counter() - t0) * 1000,
                "error": resp.get("error", ""), "body": resp.get("body")}

    read_endpoints = [
        f"{GOVERNOR_URL}/kg/stats", f"{GOVERNOR_URL}/benchmarks/stats",
        f"{HERMES_URL}/status", f"{HERMES_URL}/events/stats",
    ]

    def read_job(i: int) -> dict:
        url = read_endpoints[i % len(read_endpoints)]
        t0 = time.perf_counter()
        resp = http_request(url, timeout=10)
        return {"ok": resp["ok"], "latency_ms": (time.perf_counter() - t0) * 1000,
                "error": resp.get("error", ""), "body": resp.get("body")}

    stats = RequestStats()

    def one(i: int) -> dict:
        return jobs[i % len(jobs)](i)

    bench(f"Mixed workload (govern + reads x{count})", one, count, workers, stats)
    return stats


def snapshot_event_bus(base_url: str) -> dict:
    resp = http_request(f"{base_url}/events/stats")
    return resp.get("body", {}) if resp["ok"] else {}


def print_section(title: str):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def main():
    ap = argparse.ArgumentParser(description="Hermes + Governance load test")
    ap.add_argument("--governance", type=int, default=0, help="Number of governance decisions")
    ap.add_argument("--workers", type=int, default=16, help="Concurrent workers")
    ap.add_argument("--agents", type=int, default=0, help="Number of concurrent agent runs (rounds)")
    ap.add_argument("--agent-list", type=str, default="research-1,doc-1,quality-1,dataset-1",
                    help="Comma-separated agent IDs to run concurrently")
    ap.add_argument("--pipelines", type=int, default=0, help="Number of pipeline runs (rounds)")
    ap.add_argument("--pipeline-list", type=str, default="daily-research,training-cycle",
                    help="Comma-separated pipelines to run concurrently")
    ap.add_argument("--reads", type=int, default=0, help="Number of read requests")
    ap.add_argument("--mixed", type=int, default=0, help="Mixed governance+read requests")
    ap.add_argument("--quick", action="store_true", help="Run all scenarios with small counts")
    ap.add_argument("--all", action="store_true", help="Run full suite")
    ap.add_argument("--report", type=str, default=None, help="Write JSON report to path")
    args = ap.parse_args()

    if args.quick:
        args.governance = args.governance or 50
        args.agents = args.agents or 2
        args.pipelines = args.pipelines or 1
        args.reads = args.reads or 30
        args.mixed = args.mixed or 30
    if args.all:
        args.governance = args.governance or 200
        args.agents = args.agents or 3
        args.pipelines = args.pipelines or 2
        args.reads = args.reads or 100
        args.mixed = args.mixed or 100

    if not any([args.governance, args.agents, args.pipelines, args.reads, args.mixed]):
        print("Nothing to run. Use --governance N, --agents N, --pipelines N, --reads N, --mixed N, --quick, or --all")
        sys.exit(1)

    print_section("Pre-flight")
    for name, url in [("Governor", f"{GOVERNOR_URL}/health"), ("Hermes", f"{HERMES_URL}/health")]:
        resp = http_request(url)
        print(f"  {name}: {'UP' if resp['ok'] else 'DOWN ' + resp.get('error', '')}")

    bus_before_gov = snapshot_event_bus(GOVERNOR_URL)
    bus_before_her = snapshot_event_bus(HERMES_URL)
    print(f"  Event bus (governor) before: {bus_before_gov.get('total_events', 0)} events")
    print(f"  Event bus (hermes)   before: {bus_before_her.get('total_events', 0)} events")

    report: Dict = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config": vars(args),
        "scenarios": {},
    }

    if args.governance:
        report["scenarios"]["governance"] = run_governance_load(
            args.governance, args.workers, ALL_ITEMS).summarize()

    if args.agents:
        agent_ids = [a.strip() for a in args.agent_list.split(",") if a.strip()]
        report["scenarios"]["agents"] = run_agent_concurrency(agent_ids, args.agents).summarize()

    if args.pipelines:
        pipelines = [p.strip() for p in args.pipeline_list.split(",") if p.strip()]
        report["scenarios"]["pipelines"] = run_pipeline_concurrency(pipelines, args.pipelines).summarize()

    if args.reads:
        report["scenarios"]["reads"] = run_read_mix(args.reads, args.workers).summarize()

    if args.mixed:
        report["scenarios"]["mixed"] = run_mixed_workload(args.mixed, args.workers).summarize()

    print_section("Post-load event bus")
    bus_after_gov = snapshot_event_bus(GOVERNOR_URL)
    bus_after_her = snapshot_event_bus(HERMES_URL)
    report["event_bus"] = {
        "governor": {"before": bus_before_gov.get("total_events", 0),
                     "after": bus_after_gov.get("total_events", 0),
                     "delta": bus_after_gov.get("total_events", 0) - bus_before_gov.get("total_events", 0),
                     "failed": bus_after_gov.get("failed_events", 0)},
        "hermes": {"before": bus_before_her.get("total_events", 0),
                   "after": bus_after_her.get("total_events", 0),
                   "delta": bus_after_her.get("total_events", 0) - bus_before_her.get("total_events", 0),
                   "failed": bus_after_her.get("failed_events", 0)},
    }
    print(json.dumps(report["event_bus"], indent=2))

    if args.report:
        with open(args.report, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport written to {args.report}")

    print_section("Done")


if __name__ == "__main__":
    main()
