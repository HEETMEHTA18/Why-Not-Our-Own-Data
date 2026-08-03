import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict
from ..database.sqlite import SQLiteStore
from ..collector.storage import CollectorStorage
from ..collector.models import ConversationFilter
from .models import InstructionExample


class DatasetBuilder:
    def __init__(self, db: Optional[SQLiteStore] = None):
        self.db = db or SQLiteStore()
        self.collector = CollectorStorage(self.db)

    def build_from_corrections(self, conversation_ids: Optional[List[str]] = None) -> List[InstructionExample]:
        if conversation_ids:
            conversations = []
            for cid in conversation_ids:
                c = self.collector.get_conversation(cid)
                if c:
                    conversations.append(c)
        else:
            conversations = self.collector.list_conversations(
                ConversationFilter(has_correction=True, limit=1000, offset=0)
            )

        examples = []
        for conv in conversations:
            if not conv.corrected_response:
                continue
            ex = self._to_instruction(conv)
            self._save_example(ex)
            examples.append(ex)
        return examples

    def build_from_ratings(self, min_rating: int = 4) -> List[InstructionExample]:
        conversations = self.collector.list_conversations(
            ConversationFilter(min_rating=min_rating, has_correction=None, limit=1000, offset=0)
        )
        examples = []
        for conv in conversations:
            ex = self._to_instruction(conv)
            self._save_example(ex)
            examples.append(ex)
        return examples

    def _to_instruction(self, conv) -> InstructionExample:
        output = conv.corrected_response or conv.response
        return InstructionExample(
            id=str(uuid.uuid4()),
            conversation_id=conv.id,
            instruction=conv.prompt,
            input="",
            output=output,
            source="correction" if conv.corrected_response else "raw",
            created_at=datetime.now(timezone.utc).isoformat(),
            quality_score=0.0,
            is_valid=True,
            metadata={"model": conv.model, "rating": conv.rating},
        )

    def _save_example(self, example: InstructionExample):
        self.db.execute(
            """INSERT OR REPLACE INTO dataset_examples
               (id, conversation_id, instruction, input, output, source, created_at, quality_score, is_valid, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (example.id, example.conversation_id, example.instruction, example.input,
             example.output, example.source, example.created_at,
             example.quality_score, int(example.is_valid), str(example.metadata)),
        )

    def get_example(self, example_id: str) -> Optional[InstructionExample]:
        row = self.db.fetchone("SELECT * FROM dataset_examples WHERE id = ?", (example_id,))
        if row:
            row["metadata"] = eval(row["metadata"]) if isinstance(row.get("metadata"), str) else {}
            row["is_valid"] = bool(row["is_valid"])
            return InstructionExample(**row)
        return None

    def list_examples(self, valid_only: bool = True, limit: int = 100, offset: int = 0) -> List[InstructionExample]:
        condition = "is_valid = 1" if valid_only else "1=1"
        rows = self.db.fetchall(
            f"SELECT * FROM dataset_examples WHERE {condition} ORDER BY quality_score DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        for r in rows:
            r["metadata"] = eval(r["metadata"]) if isinstance(r.get("metadata"), str) else {}
            r["is_valid"] = bool(r["is_valid"])
        return [InstructionExample(**r) for r in rows]

    def export_alpaca(self, valid_only: bool = True) -> List[Dict]:
        examples = self.list_examples(valid_only=valid_only, limit=10000, offset=0)
        return [
            {"instruction": e.instruction, "input": e.input, "output": e.output}
            for e in examples
        ]

    def stats(self) -> dict:
        total = self.db.fetchone("SELECT COUNT(*) as c FROM dataset_examples")["c"]
        valid = self.db.fetchone("SELECT COUNT(*) as c FROM dataset_examples WHERE is_valid = 1")["c"]
        invalid = self.db.fetchone("SELECT COUNT(*) as c FROM dataset_examples WHERE is_valid = 0")["c"]
        avg_q = self.db.fetchone("SELECT COALESCE(AVG(quality_score), 0) as a FROM dataset_examples WHERE is_valid = 1")["a"]
        return {
            "total_examples": total,
            "valid_examples": valid,
            "invalid_examples": invalid,
            "avg_quality": round(avg_q, 4),
        }
