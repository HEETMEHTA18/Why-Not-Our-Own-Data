import uuid
import numpy as np
from datetime import datetime, timezone
from typing import Optional, List
from ..database.sqlite import SQLiteStore
from ..dataset.models import InstructionExample
from ..dataset.builder import DatasetBuilder
from ..config import settings
from .models import QualityScore


class QualityScorer:
    def __init__(self, db: Optional[SQLiteStore] = None):
        self.db = db or SQLiteStore()
        self.builder = DatasetBuilder(self.db)

    def score_example(self, example: InstructionExample) -> QualityScore:
        coherence = self._score_coherence(example)
        correctness = self._score_correctness(example)
        completeness = self._score_completeness(example)
        novelty = self._score_novelty(example)
        confidence = self._score_confidence(example)
        importance = self._score_importance(example)
        consistency = self._score_consistency(example)
        difficulty = self._score_difficulty(example)

        overall = (
            0.22 * coherence
            + 0.22 * correctness
            + 0.16 * completeness
            + 0.08 * novelty
            + 0.08 * confidence
            + 0.10 * importance
            + 0.06 * consistency
            + 0.08 * difficulty
        )

        score = QualityScore(
            id=str(uuid.uuid4()),
            example_id=example.id,
            overall=round(min(1.0, max(0.0, overall)), 4),
            coherence=round(coherence, 4),
            correctness=round(correctness, 4),
            completeness=round(completeness, 4),
            novelty=round(novelty, 4),
            confidence=round(confidence, 4),
            importance=round(importance, 4),
            consistency=round(consistency, 4),
            difficulty=round(difficulty, 4),
            scored_at=datetime.now(timezone.utc).isoformat(),
        )
        self._persist(score)
        self.db.execute(
            "UPDATE dataset_examples SET quality_score = ? WHERE id = ?",
            (score.overall, example.id),
        )
        return score

    def score_all(self, valid_only: bool = True) -> List[QualityScore]:
        examples = self.builder.list_examples(valid_only=valid_only, limit=10000, offset=0)
        return [self.score_example(ex) for ex in examples]

    def score_external(self, instruction: str, output: str, source: str = "external",
                       metadata: Optional[dict] = None) -> QualityScore:
        import uuid as _uuid
        conv_id = str(_uuid.uuid4())
        ex_id = str(_uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        self.db.execute(
            "INSERT OR IGNORE INTO conversations (id, session_id, prompt, response, model, latency_ms, timestamp, rating, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (conv_id, "external", instruction, output, "external", 0, now, 0, "{}"),
        )
        example = InstructionExample(
            id=ex_id,
            conversation_id=conv_id,
            instruction=instruction,
            input="",
            output=output,
            source=source,
            created_at=now,
            quality_score=0.0,
            is_valid=True,
            metadata=metadata or {},
        )
        self.builder._save_example(example)
        return self.score_example(example)

    def _score_coherence(self, ex: InstructionExample) -> float:
        score = 0.7
        instr_words = len(ex.instruction.split())
        out_words = len(ex.output.split())
        if instr_words < 3:
            score -= 0.3
        elif instr_words > 50:
            score += 0.1
        if out_words < 5:
            score -= 0.3
        elif out_words > 200:
            score += 0.1
        if ex.instruction.strip().endswith("?"):
            score += 0.1
        return max(0.1, min(1.0, score))

    def _score_correctness(self, ex: InstructionExample) -> float:
        score = 0.7
        if ex.source == "correction":
            score += 0.2
        rating = ex.metadata.get("rating", 0) if isinstance(ex.metadata, dict) else 0
        if rating >= 4:
            score += 0.1
        if "crawled_" in ex.source:
            score += 0.1
        return min(1.0, score)

    def _score_completeness(self, ex: InstructionExample) -> float:
        score = 0.6
        if len(ex.output) > 100:
            score += 0.15
        if len(ex.output) > 300:
            score += 0.15
        if len(ex.output) > 1000:
            score += 0.1
        return min(1.0, score)

    def _score_novelty(self, ex: InstructionExample) -> float:
        similar = self.db.fetchall(
            "SELECT quality_score FROM dataset_examples WHERE id != ? AND instruction = ?",
            (ex.id, ex.instruction),
        )
        if not similar:
            return 1.0
        avg_sim = np.mean([s["quality_score"] for s in similar]) if similar else 0
        return max(0.1, 1.0 - avg_sim)

    def _score_confidence(self, ex: InstructionExample) -> float:
        score = 0.8
        if ex.source == "correction":
            score += 0.1
        if isinstance(ex.metadata, dict) and ex.metadata.get("rating", 0) > 0:
            score += 0.1
        if len(ex.output) < 20:
            score -= 0.2
        if "crawled_api" in ex.source or "crawled_security" in ex.source:
            score += 0.05
        return max(0.1, min(1.0, score))

    def _score_importance(self, ex: InstructionExample) -> float:
        score = 0.6
        text = (ex.instruction + " " + ex.output).lower()
        important_topics = [
            "security", "vulnerability", "cve", "breaking change", "deprecation",
            "critical", "urgent", "important", "must", "required", "fix",
            "api change", "migration", "upgrade", "downtime",
        ]
        matches = sum(1 for t in important_topics if t in text)
        score += min(0.4, matches * 0.1)
        if isinstance(ex.metadata, dict) and ex.metadata.get("knowledge_type") in ("security", "api_update", "deprecation"):
            score += 0.2
        return min(1.0, score)

    def _score_consistency(self, ex: InstructionExample) -> float:
        score = 0.7
        similar = self.db.fetchall(
            "SELECT output FROM dataset_examples WHERE instruction = ? AND id != ? LIMIT 5",
            (ex.instruction, ex.id),
        )
        if not similar:
            return 0.8

        current_lower = ex.output.lower()
        consistent = 0
        for row in similar:
            other = row["output"].lower()
            if abs(len(current_lower) - len(other)) / max(len(current_lower), len(other), 1) < 0.3:
                consistent += 1
        consistency_ratio = consistent / len(similar) if similar else 1.0
        score *= consistency_ratio
        return max(0.2, score)

    def _score_difficulty(self, ex: InstructionExample) -> float:
        score = 0.5
        instr = ex.instruction
        output = ex.output
        instr_len = len(instr)
        out_len = len(output)

        if instr_len > 100:
            score += 0.15
        if out_len > 500:
            score += 0.15
        if out_len > 1000:
            score += 0.1

        technical_terms = [
            "algorithm", "complexity", "recursive", "asynchronous", "concurrent",
            "distributed", "encryption", "optimization", "polymorphism", "metaclass",
            "decorator", "generator", "coroutine", "reflection", "inference",
        ]
        text = (instr + " " + output).lower()
        terms_found = sum(1 for t in technical_terms if t in text)
        score += min(0.2, terms_found * 0.04)

        if "```" in output or "{" in output or "(" in output:
            score += 0.1

        return min(1.0, score)

    def _persist(self, score: QualityScore):
        self.db.execute(
            """INSERT OR REPLACE INTO quality_scores
               (id, example_id, overall, coherence, correctness, completeness,
                novelty, confidence, importance, consistency, difficulty, scored_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (score.id, score.example_id, score.overall, score.coherence, score.correctness,
             score.completeness, score.novelty, score.confidence, score.importance,
             score.consistency, score.difficulty, score.scored_at),
        )

    def get_scores(self, example_id: str) -> List[QualityScore]:
        rows = self.db.fetchall(
            "SELECT * FROM quality_scores WHERE example_id = ? ORDER BY scored_at DESC", (example_id,)
        )
        return [QualityScore(**r) for r in rows]

    def get_all_scores(self) -> List[QualityScore]:
        rows = self.db.fetchall("SELECT * FROM quality_scores ORDER BY scored_at DESC")
        return [QualityScore(**r) for r in rows]
