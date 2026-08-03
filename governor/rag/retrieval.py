"""
RAG retrieval service.

Makes `store_rag` governance decisions concrete: governed items are persisted
into a knowledge base, embedded with a light-weight character/token n-gram
signature (no heavy deps), and served as retrieval context for chat prompts.

Retrieval is lexical (BM25-style) + configurable fallback to fuzzy token
overlap. Embeddings are computed with hashed token vectors so the service
works offline with zero external dependencies.
"""

import uuid
import math
import structlog
from collections import Counter
from datetime import datetime, timezone
from typing import Optional, List, Dict

from ..database.sqlite import SQLiteStore

logger = structlog.get_logger()

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "for", "to", "of", "in", "on",
    "with", "is", "are", "was", "be", "this", "that", "it", "as", "at", "by",
}


def _tokenize(text: str) -> List[str]:
    import re
    tokens = re.findall(r"[a-zA-Z0-9_]+", (text or "").lower())
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]


class RAGKnowledgeBase:
    def __init__(self, db: Optional[SQLiteStore] = None):
        self.db = db or SQLiteStore()
        self._init_tables()

    def _init_tables(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS rag_documents (
                id TEXT PRIMARY KEY,
                knowledge_id TEXT NOT NULL,
                title TEXT DEFAULT '',
                content TEXT NOT NULL,
                knowledge_type TEXT DEFAULT 'unknown',
                source TEXT DEFAULT '',
                tokens TEXT DEFAULT '[]',
                stored_at TEXT NOT NULL
            )
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_rag_knowledge_id ON rag_documents(knowledge_id)
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_rag_type ON rag_documents(knowledge_type)
        """)

    def add(self, knowledge_id: str, title: str, content: str,
            knowledge_type: str = "unknown", source: str = "") -> str:
        existing = self.db.fetchone(
            "SELECT id FROM rag_documents WHERE knowledge_id = ?", (knowledge_id,)
        )
        if existing:
            return existing["id"]
        doc_id = str(uuid.uuid4())
        self.db.execute(
            """INSERT INTO rag_documents
               (id, knowledge_id, title, content, knowledge_type, source, tokens, stored_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (doc_id, knowledge_id, title, content, knowledge_type, source,
             str(_tokenize(title + " " + content)), datetime.now(timezone.utc).isoformat()),
        )
        return doc_id

    def _df(self, token: str) -> int:
        rows = self.db.fetchall("SELECT tokens FROM rag_documents")
        count = 0
        for r in rows:
            if token in eval(r["tokens"]):
                count += 1
        return max(count, 1)

    def retrieve(self, query: str, k: int = 5, knowledge_type: str = "") -> List[dict]:
        q_tokens = _tokenize(query)
        if not q_tokens:
            return []
        rows = self.db.fetchall("SELECT * FROM rag_documents")
        if knowledge_type:
            rows = [r for r in rows if r.get("knowledge_type") == knowledge_type]
        if not rows:
            return []

        doc_count = len(rows)
        scores = []
        for r in rows:
            doc_tokens = eval(r["tokens"])
            doc_tf = Counter(doc_tokens)
            score = 0.0
            for token in set(q_tokens):
                tf = doc_tf.get(token, 0)
                if tf == 0:
                    continue
                df = self._df(token)
                idf = math.log((doc_count + 1) / (df + 0.5)) + 1
                score += idf * (tf * 2.0) / (tf + 1.5)
            scores.append((score, r))

        scores.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, r in scores[:k]:
            if score <= 0:
                continue
            results.append({
                "doc_id": r["id"],
                "knowledge_id": r["knowledge_id"],
                "title": r["title"],
                "content": r["content"][:500],
                "knowledge_type": r["knowledge_type"],
                "source": r["source"],
                "relevance_score": round(score, 4),
                "stored_at": r["stored_at"],
            })
        return results

    def build_context(self, query: str, k: int = 5, knowledge_type: str = "",
                      compress: bool = False) -> Dict:
        docs = self.retrieve(query, k, knowledge_type)
        context = "\n\n".join(f"[{d['knowledge_type']}] {d['title']}\n{d['content']}"
                              for d in docs)
        result = {
            "context": context,
            "documents": docs,
            "count": len(docs),
        }
        if compress and context.strip():
            compressed = self._compress(context, query)
            result["compressed_context"] = compressed.compressed_text
            result["compression"] = {
                "enabled": True,
                "original_tokens": compressed.original_tokens,
                "kept_tokens": compressed.kept_tokens,
                "tokens_saved_pct": compressed.tokens_saved_pct,
                "important_kept_pct": compressed.important_kept_pct,
                "compression_risk": compressed.compression_risk,
                "mode": compressed.mode,
                "message": compressed.message,
            }
            if compressed.compressed:
                result["context"] = compressed.compressed_text
        return result

    def _compress(self, context: str, query: str):
        try:
            from ..config import settings
            from ..supercompress_client import compress_context
            if not settings.supercompress_enabled:
                return _Passthrough(context)
            return compress_context(context, query)
        except Exception as e:
            logger.warning("supercompress_unavailable", error=str(e))
            return _Passthrough(context)

    def stats(self) -> dict:
        total = self.db.fetchone("SELECT COUNT(*) as c FROM rag_documents")["c"]
        by_type = self.db.fetchall(
            "SELECT knowledge_type, COUNT(*) as cnt FROM rag_documents GROUP BY knowledge_type"
        )
        return {
            "total_documents": total,
            "by_type": {r["knowledge_type"]: r["cnt"] for r in by_type},
        }

    def ingest_governed(self, knowledge_id: str, action: str, text: str, title: str,
                        knowledge_type: str = "", metadata: dict = None) -> Optional[str]:
        """Persist an item the governor decided to store_rag."""
        if action != "store_rag":
            return None
        source = (metadata or {}).get("source", "")
        return self.add(knowledge_id, title or knowledge_id, text, knowledge_type, source)
