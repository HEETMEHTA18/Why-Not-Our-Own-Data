import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from ..database.sqlite import SQLiteStore
from ..config import settings
from .models import ConversationCreate, CorrectionCreate, Conversation, ConversationFilter


class CollectorStorage:
    def __init__(self, db: Optional[SQLiteStore] = None):
        self.db = db or SQLiteStore()

    def store_conversation(self, data: ConversationCreate) -> Conversation:
        cid = str(uuid.uuid4())
        ts = datetime.now(timezone.utc).isoformat()
        self.db.execute(
            """INSERT INTO conversations (id, session_id, prompt, response, model, latency_ms, timestamp, rating, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (cid, data.session_id, data.prompt, data.response, data.model,
             data.latency_ms, ts, data.rating, str(data.metadata)),
        )
        return self.get_conversation(cid)

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        row = self.db.fetchone("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
        if row:
            row["metadata"] = json.loads(row["metadata"]) if isinstance(row.get("metadata"), str) else {}
            return Conversation(**row)
        return None

    def list_conversations(self, f: Optional[ConversationFilter] = None) -> List[Conversation]:
        f = f or ConversationFilter()
        conditions = []
        params = []
        if getattr(f, 'session_id', None):
            conditions.append("session_id = ?")
            params.append(f.session_id)
        if getattr(f, 'min_rating', None) is not None:
            conditions.append("rating >= ?")
            params.append(f.min_rating)
        if f.has_correction is True:
            conditions.append("corrected_response IS NOT NULL")
        elif f.has_correction is False:
            conditions.append("corrected_response IS NULL")
        if getattr(f, 'start_date', None):
            conditions.append("timestamp >= ?")
            params.append(f.start_date)
        if getattr(f, 'end_date', None):
            conditions.append("timestamp <= ?")
            params.append(f.end_date)

        where = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT * FROM conversations WHERE {where} ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([f.limit, f.offset])
        rows = self.db.fetchall(sql, tuple(params))
        for r in rows:
            r["metadata"] = json.loads(r["metadata"]) if isinstance(r.get("metadata"), str) else {}
        return [Conversation(**r) for r in rows]

    def apply_correction(self, data: CorrectionCreate) -> Optional[Conversation]:
        ts = datetime.now(timezone.utc).isoformat()
        self.db.execute(
            "UPDATE conversations SET corrected_response = ?, correction_timestamp = ? WHERE id = ?",
            (data.corrected_response, ts, data.conversation_id),
        )
        return self.get_conversation(data.conversation_id)

    def rate_conversation(self, conversation_id: str, rating: int) -> Optional[Conversation]:
        self.db.execute(
            "UPDATE conversations SET rating = ? WHERE id = ?",
            (rating, conversation_id),
        )
        return self.get_conversation(conversation_id)

    def count(self, has_correction: Optional[bool] = None) -> int:
        if has_correction is True:
            return self.db.fetchone("SELECT COUNT(*) as c FROM conversations WHERE corrected_response IS NOT NULL")["c"]
        elif has_correction is False:
            return self.db.fetchone("SELECT COUNT(*) as c FROM conversations WHERE corrected_response IS NULL")["c"]
        return self.db.fetchone("SELECT COUNT(*) as c FROM conversations")["c"]
