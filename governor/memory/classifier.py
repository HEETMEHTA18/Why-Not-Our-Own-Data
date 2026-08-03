import uuid
from datetime import datetime, timezone
from typing import Optional, List
from ..database.sqlite import SQLiteStore
from ..collector.storage import CollectorStorage
from .models import MemoryClass, ClassificationResult


class MemoryClassifier:
    def __init__(self, db: Optional[SQLiteStore] = None):
        self.db = db or SQLiteStore()
        self.collector = CollectorStorage(self.db)

    def classify(self, conversation_id: str) -> ClassificationResult:
        conv = self.collector.get_conversation(conversation_id)
        if not conv:
            raise ValueError(f"Conversation {conversation_id} not found")

        text = f"{conv.prompt} {conv.response}{conv.corrected_response or ''}"
        rating = conv.rating
        has_correction = conv.corrected_response is not None

        if not has_correction and rating <= 1:
            return self._result(conv.id, MemoryClass.IGNORED, 0.7,
                                "Low rating and no correction — low value")

        if has_correction and rating >= 3:
            return self._result(conv.id, MemoryClass.TRAINING_DATA, 0.85,
                                "Corrected response with good rating — high training value")

        if has_correction and rating < 3:
            return self._result(conv.id, MemoryClass.LONG_TERM_MEMORY, 0.65,
                                "Corrected but low rating — store as reference")

        if rating >= 4:
            return self._result(conv.id, MemoryClass.TRAINING_DATA, 0.70,
                                "High rating — potentially useful for training")

        if len(conv.prompt) > 50 and len(conv.response) > 100:
            return self._result(conv.id, MemoryClass.LONG_TERM_MEMORY, 0.60,
                                "Substantial conversation — store as memory")

        return self._result(conv.id, MemoryClass.TEMPORARY_CONTEXT, 0.50,
                            "Short/generic — keep as temporary context")

    def classify_many(self, conversation_ids: List[str]) -> List[ClassificationResult]:
        return [self.classify(cid) for cid in conversation_ids]

    def _result(self, conv_id: str, cls: MemoryClass, confidence: float, reason: str) -> ClassificationResult:
        result = ClassificationResult(
            conversation_id=conv_id,
            classification=cls,
            confidence=confidence,
            reason=reason,
            should_store=cls != MemoryClass.IGNORED,
        )
        self._log(result)
        return result

    def _log(self, result: ClassificationResult):
        self.db.execute(
            """INSERT INTO classification_log
               (id, conversation_id, classification, confidence, reason, classified_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (str(uuid.uuid4()), result.conversation_id, result.classification.value,
             result.confidence, result.reason, datetime.now(timezone.utc).isoformat()),
        )

    def get_classification(self, conversation_id: str) -> Optional[ClassificationResult]:
        row = self.db.fetchone(
            "SELECT * FROM classification_log WHERE conversation_id = ? ORDER BY classified_at DESC",
            (conversation_id,),
        )
        if not row:
            return None
        return ClassificationResult(
            conversation_id=row["conversation_id"],
            classification=MemoryClass(row["classification"]),
            confidence=row["confidence"],
            reason=row["reason"],
            should_store=True,
        )

    def stats(self) -> dict:
        rows = self.db.fetchall(
            "SELECT classification, COUNT(*) as cnt FROM classification_log GROUP BY classification"
        )
        return {r["classification"]: r["cnt"] for r in rows} if rows else {}
