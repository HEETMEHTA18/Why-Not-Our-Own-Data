"""
Multi-adapter routing + data lineage.

routing:  classifies an incoming prompt by task domain and returns the best
          adapter (by benchmark score) for that domain, plus the fallback.
lineage:  traces any adapter/dataset/example back to its governed knowledge
          item and source URL — full provenance for trust and audit.
"""

import uuid
import structlog
from datetime import datetime, timezone
from typing import Optional, List, Dict

from .database.sqlite import SQLiteStore
from .eventbus.bus import get_bus
from .eventbus.models import EventType, EventPriority

logger = structlog.get_logger()

DOMAIN_KEYWORDS = {
    "python": ["python", "def ", "import ", "list comprehension", "pip"],
    "fastapi": ["fastapi", "api endpoint", "app.get", "pydantic", "openapi"],
    "react": ["react", "component", "usestate", "useeffect", "jsx", "props"],
    "docker": ["docker", "container", "image", "dockerfile", "compose"],
    "kubernetes": ["kubernetes", "k8s", "pod", "deployment", "cluster", "helm"],
    "sql": ["sql", "select", "query", "join", "database", "postgres"],
    "security": ["security", "cve", "vulnerability", "oauth", "jwt", "auth"],
    "git": ["git", "commit", "branch", "merge", "rebase"],
    "linux": ["linux", "bash", "shell", "grep", "systemd"],
    "javascript": ["javascript", "typescript", "async", "promise", "node"],
}


class AdapterRouter:
    def __init__(self, db: Optional[SQLiteStore] = None):
        self.db = db or SQLiteStore()
        self._init_tables()

    def _init_tables(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS routing_log (
                id TEXT PRIMARY KEY,
                prompt TEXT NOT NULL,
                domain TEXT NOT NULL,
                chosen_adapter TEXT DEFAULT 'base',
                fallback TEXT DEFAULT 'base',
                reason TEXT DEFAULT '',
                routed_at TEXT NOT NULL
            )
        """)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS adapter_domains (
                adapter_id TEXT PRIMARY KEY,
                domain TEXT NOT NULL,
                benchmark_score REAL DEFAULT 0.0,
                baseline_score REAL DEFAULT 0.0,
                registered_at TEXT NOT NULL
            )
        """)

    def classify(self, prompt: str) -> str:
        lower = prompt.lower()
        best_domain = "general"
        best_count = 0
        for domain, keywords in DOMAIN_KEYWORDS.items():
            count = sum(1 for k in keywords if k in lower)
            if count > best_count:
                best_count = count
                best_domain = domain
        return best_domain

    def register_adapter(self, adapter_id: str, domain: str, benchmark_score: float = 0.0,
                         baseline_score: float = 0.0):
        self.db.execute(
            """INSERT OR REPLACE INTO adapter_domains
               (adapter_id, domain, benchmark_score, baseline_score, registered_at)
               VALUES (?, ?, ?, ?, ?)""",
            (adapter_id, domain, benchmark_score, baseline_score,
             datetime.now(timezone.utc).isoformat()),
        )

    def _best_adapter(self, domain: str) -> Dict:
        rows = self.db.fetchall(
            "SELECT * FROM adapter_domains WHERE domain = ? ORDER BY benchmark_score DESC LIMIT 1",
            (domain,),
        )
        if rows:
            row = rows[0]
            improvement = row["benchmark_score"] - row["baseline_score"]
            return {
                "adapter_id": row["adapter_id"],
                "benchmark_score": row["benchmark_score"],
                "baseline_score": row["baseline_score"],
                "improvement": round(improvement, 4),
            }
        return {"adapter_id": "base", "benchmark_score": 0.0, "baseline_score": 0.0,
                "improvement": 0.0}

    def route(self, prompt: str) -> Dict:
        domain = self.classify(prompt)
        chosen = self._best_adapter(domain)
        general = self._best_adapter("general") if domain != "general" else chosen
        fallback = general.get("adapter_id", "base") if chosen.get("adapter_id") != "base" else "base"

        self.db.execute(
            """INSERT INTO routing_log
               (id, prompt, domain, chosen_adapter, fallback, reason, routed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (str(uuid.uuid4()), prompt[:500], domain, chosen.get("adapter_id", "base"),
             fallback, f"best benchmark score for {domain}",
             datetime.now(timezone.utc).isoformat()),
        )

        bus = get_bus()
        import asyncio
        try:
            asyncio.create_task(bus.publish_sync(
                EventType.ROUTE_DECIDED, "adapter_router",
                payload={"domain": domain, "adapter": chosen.get("adapter_id"),
                         "improvement": chosen.get("improvement")},
                priority=EventPriority.LOW,
            ))
        except RuntimeError:
            pass

        return {"domain": domain, "chosen_adapter": chosen, "fallback": fallback}

    def routing_stats(self) -> dict:
        total = self.db.fetchone("SELECT COUNT(*) as c FROM routing_log")["c"]
        by_domain = self.db.fetchall(
            "SELECT domain, COUNT(*) as cnt FROM routing_log GROUP BY domain"
        )
        by_adapter = self.db.fetchall(
            "SELECT chosen_adapter, COUNT(*) as cnt FROM routing_log GROUP BY chosen_adapter"
        )
        return {
            "total_routes": total,
            "by_domain": {r["domain"]: r["cnt"] for r in by_domain},
            "by_adapter": {r["chosen_adapter"]: r["cnt"] for r in by_adapter},
        }

    def registered_adapters(self) -> List[dict]:
        return self.db.fetchall("SELECT * FROM adapter_domains ORDER BY benchmark_score DESC")


class LineageTracker:
    """Full provenance chain: adapter <- dataset <- governed items <- source URLs."""

    def __init__(self, db: Optional[SQLiteStore] = None):
        self.db = db or SQLiteStore()
        self._init_tables()

    def _init_tables(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS lineage_links (
                id TEXT PRIMARY KEY,
                source_type TEXT NOT NULL,
                source_id TEXT NOT NULL,
                target_type TEXT NOT NULL,
                target_id TEXT NOT NULL,
                link_type TEXT DEFAULT 'derived_from',
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            )
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_lineage_source ON lineage_links(source_type, source_id)
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_lineage_target ON lineage_links(target_type, target_id)
        """)

    def link(self, source_type: str, source_id: str, target_type: str,
             target_id: str, link_type: str = "derived_from", metadata: dict = None):
        existing = self.db.fetchone(
            "SELECT id FROM lineage_links WHERE source_type = ? AND source_id = ? "
            "AND target_type = ? AND target_id = ? AND link_type = ?",
            (source_type, source_id, target_type, target_id, link_type),
        )
        if existing:
            return existing["id"]
        lid = str(uuid.uuid4())
        self.db.execute(
            """INSERT INTO lineage_links
               (id, source_type, source_id, target_type, target_id, link_type, metadata, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (lid, source_type, source_id, target_type, target_id, link_type,
             str(metadata or {}), datetime.now(timezone.utc).isoformat()),
        )
        return lid

    def trace(self, target_type: str, target_id: str, max_depth: int = 3) -> Dict:
        """Follow derivation edges backward from a target (e.g. adapter)."""
        visited = set()
        nodes: List[dict] = []
        queue = [(target_type, target_id, 0)]
        while queue:
            t_type, t_id, depth = queue.pop(0)
            key = (t_type, t_id)
            if key in visited or depth > max_depth:
                continue
            visited.add(key)
            nodes.append({"type": t_type, "id": t_id, "depth": depth})
            if depth < max_depth:
                rows = self.db.fetchall(
                    "SELECT * FROM lineage_links WHERE target_type = ? AND target_id = ?",
                    (t_type, t_id),
                )
                for r in rows:
                    queue.append((r["source_type"], r["source_id"], depth + 1))
        return {
            "target": {"type": target_type, "id": target_id},
            "chain": nodes,
            "length": len(nodes),
        }
