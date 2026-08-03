import pytest
from ..quality.scorer import QualityScorer
from ..dataset.models import InstructionExample


@pytest.fixture
def scorer():
    from ..database.sqlite import SQLiteStore
    db = SQLiteStore(db_path=":memory:")
    return QualityScorer(db=db)


def _save(scorer, ex):
    import uuid
    from datetime import datetime, timezone
    scorer.db.execute(
        "INSERT OR IGNORE INTO conversations (id, session_id, prompt, response, model, latency_ms, timestamp, rating, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (ex.conversation_id, "test-session", ex.instruction, ex.output, "test", 0, datetime.now(timezone.utc).isoformat(), 0, "{}"),
    )
    scorer.builder._save_example(ex)
    return ex


class TestQualityScorerExtended:
    def test_importance_security_topic(self, scorer):
        ex = _save(scorer, InstructionExample(
            id="imp-1", conversation_id="c1",
            instruction="How do I fix a SQL injection vulnerability?",
            input="", output="Use parameterized queries instead of string concatenation.",
            source="correction", created_at="2024-01-01", quality_score=0.0, is_valid=True,
            metadata={"knowledge_type": "security"},
        ))
        score = scorer.score_example(ex)
        assert score.importance > 0.6

    def test_importance_generic_topic(self, scorer):
        ex = _save(scorer, InstructionExample(
            id="imp-2", conversation_id="c2",
            instruction="What is Python?",
            input="", output="Python is a programming language.",
            source="raw", created_at="2024-01-01", quality_score=0.0, is_valid=True,
            metadata={},
        ))
        score = scorer.score_example(ex)
        assert score.importance < 0.7

    def test_consistency_matching(self, scorer):
        ex1 = _save(scorer, InstructionExample(
            id="con-1", conversation_id="c1",
            instruction="What is the capital of France?",
            input="", output="The capital of France is Paris.",
            source="crawled", created_at="2024-01-01", quality_score=0.0, is_valid=True,
            metadata={},
        ))
        ex2 = _save(scorer, InstructionExample(
            id="con-2", conversation_id="c2",
            instruction="What is the capital of France?",
            input="", output="Paris is the capital city of France.",
            source="crawled", created_at="2024-01-01", quality_score=0.0, is_valid=True,
            metadata={},
        ))
        score = scorer.score_example(ex1)
        assert score.consistency > 0.3

    def test_difficulty_technical(self, scorer):
        ex = _save(scorer, InstructionExample(
            id="diff-1", conversation_id="c1",
            instruction="Implement a concurrent distributed caching algorithm",
            input="", output="```python\nimport asyncio\nfrom hashlib import sha256\n\nclass DistributedCache:\n    def __init__(self, nodes):\n        self.nodes = nodes\n        self.ring = sorted([self._hash(n) for n in nodes])\n```",
            source="raw", created_at="2024-01-01", quality_score=0.0, is_valid=True,
            metadata={},
        ))
        score = scorer.score_example(ex)
        assert score.difficulty > 0.5

    def test_difficulty_simple(self, scorer):
        ex = _save(scorer, InstructionExample(
            id="diff-2", conversation_id="c2",
            instruction="What is 2+2?",
            input="", output="4",
            source="raw", created_at="2024-01-01", quality_score=0.0, is_valid=True,
            metadata={},
        ))
        score = scorer.score_example(ex)
        assert score.difficulty < 0.6

    def test_score_external(self, scorer):
        score = scorer.score_external(
            instruction="How to use async/await in Python?",
            output="Use 'async def' to define a coroutine and 'await' to call it.",
            source="external_api",
        )
        assert score.overall > 0
        assert score.importance >= 0
        assert score.consistency >= 0
        assert score.difficulty >= 0

    def test_overall_weights(self, scorer):
        ex = _save(scorer, InstructionExample(
            id="weight-1", conversation_id="c1",
            instruction="Explain RSA encryption",
            input="", output="RSA uses a public-private key pair. The public key encrypts, the private key decrypts.",
            source="crawled_security", created_at="2024-01-01", quality_score=0.0, is_valid=True,
            metadata={},
        ))
        score = scorer.score_example(ex)
        assert 0 <= score.overall <= 1
        assert 0 <= score.coherence <= 1
        assert 0 <= score.correctness <= 1
        assert 0 <= score.completeness <= 1
        assert 0 <= score.novelty <= 1
        assert 0 <= score.confidence <= 1
        assert 0 <= score.importance <= 1
        assert 0 <= score.consistency <= 1
        assert 0 <= score.difficulty <= 1
