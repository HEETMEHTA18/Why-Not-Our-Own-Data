import uuid
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Tuple
from collections import deque

from ..database.sqlite import SQLiteStore
from ..eventbus.bus import get_bus
from ..eventbus.models import EventType, EventPriority
from .models import (
    KnowledgeNode, KnowledgeEdge, KnowledgeEdge as Edge,
    NodeType, EdgeType, KG_SEED_NODES, KG_SEED_EDGES,
    GraphPath, GraphQuery,
)

import structlog
logger = structlog.get_logger()


class KnowledgeGraph:
    def __init__(self, db: Optional[SQLiteStore] = None):
        self.db = db or SQLiteStore()
        self._init_tables()
        self._seed()

    def _init_tables(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS kg_nodes (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                node_type TEXT NOT NULL,
                description TEXT DEFAULT '',
                aliases TEXT DEFAULT '[]',
                tags TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            )
        """)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS kg_edges (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                edge_type TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                FOREIGN KEY (source_id) REFERENCES kg_nodes(id),
                FOREIGN KEY (target_id) REFERENCES kg_nodes(id)
            )
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_kg_edge_source ON kg_edges(source_id)
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_kg_edge_target ON kg_edges(target_id)
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_kg_node_type ON kg_nodes(node_type)
        """)

    def _seed(self):
        existing = self.db.fetchone("SELECT COUNT(*) as c FROM kg_nodes")["c"]
        if existing > 0:
            return
        now = datetime.now(timezone.utc).isoformat()
        name_to_id = {}
        for ndata in KG_SEED_NODES:
            nid = str(uuid.uuid4())
            name_to_id[ndata["name"]] = nid
            self.db.execute(
                """INSERT OR REPLACE INTO kg_nodes
                   (id, name, node_type, description, aliases, tags, metadata, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (nid, ndata["name"], ndata["node_type"].value if isinstance(ndata["node_type"], NodeType) else ndata["node_type"],
                 ndata.get("description", ""), str(ndata.get("aliases", [])),
                 str(ndata.get("tags", [])), str(ndata.get("metadata", {})), now),
            )
        for src_name, tgt_name, edge_type in KG_SEED_EDGES:
            src_id = name_to_id.get(src_name)
            tgt_id = name_to_id.get(tgt_name)
            if src_id and tgt_id:
                eid = str(uuid.uuid4())
                et = edge_type.value if isinstance(edge_type, EdgeType) else edge_type
                self.db.execute(
                    """INSERT OR REPLACE INTO kg_edges
                       (id, source_id, target_id, edge_type, weight, metadata, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (eid, src_id, tgt_id, et, 1.0, "{}", now),
                )
        logger.info("knowledge_graph_seeded", nodes=len(KG_SEED_NODES), edges=len(KG_SEED_EDGES))

    def add_node(self, name: str, node_type: NodeType, description: str = "",
                  aliases: list = None, tags: list = None) -> KnowledgeNode:
        existing = self.db.fetchone("SELECT * FROM kg_nodes WHERE name = ?", (name,))
        if existing:
            return self._row_to_node(existing)
        nid = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        self.db.execute(
            """INSERT INTO kg_nodes
               (id, name, node_type, description, aliases, tags, metadata, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (nid, name, node_type.value, description, str(aliases or []),
             str(tags or []), "{}", now),
        )
        row = self.db.fetchone("SELECT * FROM kg_nodes WHERE id = ?", (nid,))
        return self._row_to_node(row)

    def add_edge(self, source_name: str, target_name: str, edge_type: EdgeType,
                  weight: float = 1.0) -> Optional[KnowledgeEdge]:
        src = self.db.fetchone("SELECT id FROM kg_nodes WHERE name = ?", (source_name,))
        tgt = self.db.fetchone("SELECT id FROM kg_nodes WHERE name = ?", (target_name,))
        if not src or not tgt:
            return None
        existing = self.db.fetchone(
            "SELECT * FROM kg_edges WHERE source_id = ? AND target_id = ? AND edge_type = ?",
            (src["id"], tgt["id"], edge_type.value),
        )
        if existing:
            return self._row_to_edge(existing)
        eid = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        self.db.execute(
            """INSERT INTO kg_edges
               (id, source_id, target_id, edge_type, weight, metadata, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (eid, src["id"], tgt["id"], edge_type.value, weight, "{}", now),
        )
        row = self.db.fetchone("SELECT * FROM kg_edges WHERE id = ?", (eid,))
        return self._row_to_edge(row)

    def query(self, q: GraphQuery) -> GraphPath:
        if q.source_name:
            start = self.db.fetchone(
                "SELECT id FROM kg_nodes WHERE name = ?", (q.source_name,)
            )
            if not start:
                return GraphPath(nodes=[], edges=[])
            return self._traverse(start["id"], q.max_depth, q.limit)

        if q.node_type:
            nodes = self.db.fetchall(
                "SELECT * FROM kg_nodes WHERE node_type = ? LIMIT ?",
                (q.node_type.value, q.limit),
            )
            return GraphPath(
                nodes=[self._row_to_node(r) for r in nodes],
                edges=[],
            )

        nodes = self.db.fetchall("SELECT * FROM kg_nodes LIMIT ?", (q.limit,))
        return GraphPath(
            nodes=[self._row_to_node(r) for r in nodes],
            edges=[],
        )

    def _traverse(self, start_id: str, max_depth: int, limit: int) -> GraphPath:
        visited_nodes = set()
        visited_edges = set()
        queue = deque([(start_id, 0)])
        nodes_map = {}
        edges_list = []

        while queue and len(visited_nodes) < limit:
            node_id, depth = queue.popleft()
            if node_id in visited_nodes or depth > max_depth:
                continue
            visited_nodes.add(node_id)
            row = self.db.fetchone("SELECT * FROM kg_nodes WHERE id = ?", (node_id,))
            if row:
                nodes_map[node_id] = self._row_to_node(row)

            if depth < max_depth:
                for direction in ["source_id", "target_id"]:
                    other_col = "target_id" if direction == "source_id" else "source_id"
                    edges = self.db.fetchall(
                        f"SELECT * FROM kg_edges WHERE {direction} = ? LIMIT {limit}",
                        (node_id,),
                    )
                    for edge in edges:
                        eid = edge["id"]
                        if eid in visited_edges:
                            continue
                        visited_edges.add(eid)
                        other_id = edge[other_col]
                        edges_list.append(self._row_to_edge(edge))
                        queue.append((other_id, depth + 1))

        return GraphPath(nodes=list(nodes_map.values()), edges=edges_list)

    def find_path(self, source_name: str, target_name: str, max_depth: int = 4) -> Optional[GraphPath]:
        src = self.db.fetchone("SELECT id FROM kg_nodes WHERE name = ?", (source_name,))
        tgt = self.db.fetchone("SELECT id FROM kg_nodes WHERE name = ?", (target_name,))
        if not src or not tgt:
            return None

        parent = {src["id"]: None}
        edge_to_parent = {}
        queue = deque([(src["id"], 0)])

        while queue:
            node_id, depth = queue.popleft()
            if node_id == tgt["id"]:
                break
            if depth >= max_depth:
                continue
            for direction in ["source_id", "target_id"]:
                other_col = "target_id" if direction == "source_id" else "source_id"
                edges = self.db.fetchall(
                    f"SELECT * FROM kg_edges WHERE {direction} = ?", (node_id,)
                )
                for edge in edges:
                    other_id = edge[other_col]
                    if other_id not in parent:
                        parent[other_id] = node_id
                        edge_to_parent[other_id] = edge
                        queue.append((other_id, depth + 1))

        if tgt["id"] not in parent:
            return None

        path_nodes = []
        path_edges = []
        current = tgt["id"]
        while current is not None:
            row = self.db.fetchone("SELECT * FROM kg_nodes WHERE id = ?", (current,))
            if row:
                path_nodes.append(self._row_to_node(row))
            if current in edge_to_parent:
                path_edges.append(self._row_to_edge(edge_to_parent[current]))
            current = parent.get(current)
        path_nodes.reverse()
        path_edges.reverse()

        return GraphPath(nodes=path_nodes, edges=path_edges, total_distance=len(path_edges))

    def search(self, query: str, node_type: Optional[NodeType] = None, limit: int = 20) -> List[KnowledgeNode]:
        q = f"%{query}%"
        if node_type:
            rows = self.db.fetchall(
                "SELECT * FROM kg_nodes WHERE (name LIKE ? OR description LIKE ?) AND node_type = ? LIMIT ?",
                (q, q, node_type.value, limit),
            )
        else:
            rows = self.db.fetchall(
                "SELECT * FROM kg_nodes WHERE name LIKE ? OR description LIKE ? LIMIT ?",
                (q, q, limit),
            )
        return [self._row_to_node(r) for r in rows]

    def get_node(self, name: str) -> Optional[KnowledgeNode]:
        row = self.db.fetchone("SELECT * FROM kg_nodes WHERE name = ?", (name,))
        return self._row_to_node(row) if row else None

    def get_node_by_id(self, node_id: str) -> Optional[KnowledgeNode]:
        row = self.db.fetchone("SELECT * FROM kg_nodes WHERE id = ?", (node_id,))
        return self._row_to_node(row) if row else None

    def get_connections(self, node_name: str, edge_type: Optional[EdgeType] = None) -> List[dict]:
        node = self.db.fetchone("SELECT id FROM kg_nodes WHERE name = ?", (node_name,))
        if not node:
            return []
        node_id = node["id"]
        if edge_type:
            edges = self.db.fetchall(
                """SELECT e.*, n.name as connected_name, n.node_type as connected_type
                   FROM kg_edges e JOIN kg_nodes n ON
                     (n.id = CASE WHEN e.source_id = ? THEN e.target_id ELSE e.source_id END)
                   WHERE (e.source_id = ? OR e.target_id = ?) AND e.edge_type = ?""",
                (node_id, node_id, node_id, edge_type.value),
            )
        else:
            edges = self.db.fetchall(
                """SELECT e.*, n.name as connected_name, n.node_type as connected_type
                   FROM kg_edges e JOIN kg_nodes n ON
                     (n.id = CASE WHEN e.source_id = ? THEN e.target_id ELSE e.source_id END)
                   WHERE e.source_id = ? OR e.target_id = ?""",
                (node_id, node_id, node_id),
            )
        result = []
        for e in edges:
            result.append({
                "edge_type": e["edge_type"],
                "weight": e["weight"],
                "connected_to": e["connected_name"],
                "connected_type": e["connected_type"],
                "direction": "outgoing" if e["source_id"] == node_id else "incoming",
            })
        return result

    def get_stats(self) -> dict:
        total_nodes = self.db.fetchone("SELECT COUNT(*) as c FROM kg_nodes")["c"]
        total_edges = self.db.fetchone("SELECT COUNT(*) as c FROM kg_edges")["c"]
        by_type = self.db.fetchall(
            "SELECT node_type, COUNT(*) as cnt FROM kg_nodes GROUP BY node_type"
        )
        by_edge = self.db.fetchall(
            "SELECT edge_type, COUNT(*) as cnt FROM kg_edges GROUP BY edge_type"
        )
        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "nodes_by_type": {r["node_type"]: r["cnt"] for r in by_type},
            "edges_by_type": {r["edge_type"]: r["cnt"] for r in by_edge},
        }

    # --- Dynamic ingestion -------------------------------------------------

    _DOMAIN_TERMS = {
        NodeType.LANGUAGE: ["python", "javascript", "typescript", "rust", "go", "java", "c++", "sql"],
        NodeType.FRAMEWORK: ["fastapi", "django", "react", "next.js", "flask", "vue", "spring"],
        NodeType.LIBRARY: ["pytorch", "peft", "unsloth", "langchain", "sqlalchemy", "pydantic", "tensorflow"],
        NodeType.TOOL: ["docker", "git", "github", "ollama", "kubectl", "nginx", "redis-cli"],
        NodeType.DATABASE: ["postgresql", "sqlite", "redis", "duckdb", "mysql", "mongodb"],
        NodeType.SECURITY: ["jwt", "oauth2", "cve", "tls", "https", "security"],
    }

    def ingest_knowledge(self, text: str, title: str = "", knowledge_type: str = "",
                         source: str = "") -> Dict[str, int]:
        """Auto-create KG nodes/edges from governed knowledge text.

        Extracts domain terms from the text, ensures each is a node, and
        links them (KNOWLEDGE_ABOUT edges from the primary topic).
        """
        lower = (title + " " + text).lower()
        found: Dict[NodeType, str] = {}
        for ntype, terms in self._DOMAIN_TERMS.items():
            for term in terms:
                if term in lower:
                    found[ntype] = term
                    break

        if not found:
            return {"nodes_created": 0, "edges_created": 0}

        primary_type = NodeType.SECURITY if knowledge_type in ("security", "bug_fix") else list(found.keys())[0]
        primary_name = found.get(primary_type) or list(found.values())[0]

        nodes_created = 0
        edges_created = 0
        primary = self.add_node(primary_name.title(), primary_type,
                                description=f"Auto-ingested from knowledge item ({source or 'governor'})",
                                tags=[knowledge_type])
        nodes_created += 1

        for ntype, term in found.items():
            if term == primary_name:
                continue
            node = self.add_node(term.title(), ntype,
                                 description=f"Auto-ingested from knowledge item ({source or 'governor'})",
                                 tags=[knowledge_type])
            nodes_created += 1
            edge = self.add_edge(primary.name, node.name, EdgeType.KNOWLEDGE_ABOUT, weight=0.8)
            if edge:
                edges_created += 1

        bus = get_bus()
        import asyncio
        try:
            asyncio.create_task(bus.publish_sync(
                EventType.KNOWLEDGE_INGESTED_KG, "knowledge_graph",
                payload={"primary": primary_name, "nodes_created": nodes_created,
                         "edges_created": edges_created},
                priority=EventPriority.LOW,
            ))
        except RuntimeError:
            pass

        logger.info("kg_ingested", primary=primary_name,
                    nodes=nodes_created, edges=edges_created)
        return {"nodes_created": nodes_created, "edges_created": edges_created}

    def communities(self) -> List[dict]:
        """Label-propagation community detection (LPA) over the node graph."""
        nodes = self.db.fetchall("SELECT id, name, node_type FROM kg_nodes")
        edges = self.db.fetchall("SELECT source_id, target_id FROM kg_edges")
        if not nodes:
            return []

        labels = {n["id"]: n["name"] for n in nodes}
        adjacency = {n["id"]: [] for n in nodes}
        for e in edges:
            adjacency.setdefault(e["source_id"], []).append(e["target_id"])
            adjacency.setdefault(e["target_id"], []).append(e["source_id"])

        # Small LPA - a few iterations to be fast on ~50 nodes
        for _ in range(5):
            changed = False
            for nid in list(adjacency.keys()):
                neighbors = adjacency[nid]
                if not neighbors:
                    continue
                from collections import Counter
                counts = Counter(labels[nb] for nb in neighbors if nb in labels)
                if not counts:
                    continue
                best_label = counts.most_common(1)[0][0]
                if best_label != labels[nid]:
                    labels[nid] = best_label
                    changed = True
            if not changed:
                break

        groups: Dict[str, dict] = {}
        for n in nodes:
            label = labels.get(n["id"], n["name"])
            if label not in groups:
                groups[label] = {"label": label, "members": [], "types": {}}
            groups[label]["members"].append({
                "id": n["id"], "name": n["name"], "node_type": n["node_type"],
            })
            t = n["node_type"]
            groups[label]["types"][t] = groups[label]["types"].get(t, 0) + 1

        result = sorted(
            ({"label": g["label"], "size": len(g["members"]),
              "members": g["members"], "types": g["types"]}
             for g in groups.values()),
            key=lambda x: x["size"], reverse=True,
        )
        return result

    def emerging_topics(self, limit: int = 10) -> List[dict]:
        """Newest auto-ingested nodes — potential emerging topics."""
        rows = self.db.fetchall(
            "SELECT * FROM kg_nodes WHERE metadata LIKE '%auto-ingest%' "
            "ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        result = []
        for r in rows:
            node = self._row_to_node(r)
            result.append({
                "id": node.id,
                "name": node.name,
                "node_type": node.node_type.value,
                "tags": node.tags,
                "created_at": node.created_at,
            })
        return result


    def _row_to_node(self, r: dict) -> KnowledgeNode:
        return KnowledgeNode(
            id=r["id"],
            name=r["name"],
            node_type=NodeType(r["node_type"]),
            description=r.get("description", ""),
            aliases=eval(r.get("aliases", "[]")),
            tags=eval(r.get("tags", "[]")),
            metadata=eval(r.get("metadata", "{}")),
            created_at=r.get("created_at", ""),
        )

    def _row_to_edge(self, r: dict) -> KnowledgeEdge:
        return KnowledgeEdge(
            id=r["id"],
            source_id=r["source_id"],
            target_id=r["target_id"],
            edge_type=EdgeType(r["edge_type"]),
            weight=r.get("weight", 1.0),
            metadata=eval(r.get("metadata", "{}")),
            created_at=r.get("created_at", ""),
        )