import pytest
from ..research.engine import ResearchEngine
from ..research.models import ResearchStatus, FeasibilityVerdict


@pytest.fixture
def engine():
    from ..database.sqlite import SQLiteStore
    db = SQLiteStore(db_path=":memory:")
    return ResearchEngine(db=db)


class TestResearchEngine:
    def test_init_creates_tables(self, engine):
        for table in ["research_topics", "paper_summaries", "feasibility_studies", "method_comparisons"]:
            row = engine.db.fetchone(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
            )
            assert row is not None, f"Table {table} not created"

    def test_seed_topics(self, engine):
        count = engine.seed_topics()
        assert count > 0
        count2 = engine.seed_topics()
        assert count2 == 0

    def test_list_topics(self, engine):
        engine.seed_topics()
        topics = engine.list_topics()
        assert len(topics) >= 6
        assert topics[0]["status"] == "planned"

    def test_get_topic(self, engine):
        engine.seed_topics()
        topics = engine.list_topics()
        topic = engine.get_topic(topics[0]["id"])
        assert topic is not None
        assert topic["id"] == topics[0]["id"]

    def test_update_topic(self, engine):
        engine.seed_topics()
        topics = engine.list_topics()
        tid = topics[0]["id"]
        success = engine.update_topic(tid, status=ResearchStatus.IN_PROGRESS, findings="Initial results look promising")
        assert success
        topic = engine.get_topic(tid)
        assert topic["status"] == "in_progress"
        assert topic["findings"] == "Initial results look promising"

    def test_add_paper(self, engine):
        paper = engine.add_paper(
            title="LoRA: Low-Rank Adaptation of Large Language Models",
            authors=["Edward Hu", "Yelong Shen"],
            year=2021,
            url="https://arxiv.org/abs/2106.09685",
            abstract="We propose LoRA...",
            key_findings="LoRA achieves comparable performance to full fine-tuning with far fewer parameters",
            tags=["lora", "fine-tuning", "efficiency"],
        )
        assert paper.title == "LoRA: Low-Rank Adaptation of Large Language Models"
        assert len(paper.authors) == 2

    def test_feasibility_study(self, engine):
        engine.seed_topics()
        topics = engine.list_topics()
        study = engine.feasibility_study(
            topic_id=topics[0]["id"],
            verdict=FeasibilityVerdict.FEASIBLE,
            rationale="Well-understood technique with existing implementations",
            risks=["High GPU memory requirement"],
            prerequisites=["Access to A100 GPU"],
            estimated_effort="2 weeks",
            recommendations=["Start with rank 16", "Use QLoRA for memory efficiency"],
        )
        assert study.verdict == FeasibilityVerdict.FEASIBLE
        assert "High GPU memory requirement" in study.risks

    def test_stats(self, engine):
        engine.seed_topics()
        stats = engine.stats()
        assert stats["total_topics"] >= 6
        assert stats["total_papers"] == 0
        assert "planned" in stats["by_status"]
