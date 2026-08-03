import pytest
from ..database.sqlite import SQLiteStore
from ..consensus import GovernanceCouncil
from ..feedback import FeedbackEngine, DEFAULT_THRESHOLDS
from ..rag.retrieval import RAGKnowledgeBase
from ..knowledge_graph.engine import KnowledgeGraph
from ..insights import AdapterRouter, LineageTracker
from ..ops import CostTelemetry, AlertEngine, LearningProfiler


@pytest.fixture
def db():
    return SQLiteStore(db_path=":memory:")


class TestConsensus:
    def test_council_all_members_vote(self, db):
        council = GovernanceCouncil(db)
        d = council.decide("c-1", "CVE-2026 critical RCE patch for FastAPI websocket handshake.",
                           "Security advisory", "security", 0.98)
        assert len(d.votes) == 4
        assert set(v["member"] for v in d.votes) == {"research", "doc", "dataset", "quality"}
        assert d.action in ("recommend_lora", "store_rag", "store_kg", "ignore")
        assert 0 <= d.consensus <= 1

    def test_council_disagreement_detected(self, db):
        council = GovernanceCouncil(db)
        d = council.decide("c-2", "Vague uncertain note with no clear signal.", "Unclear", "general", 0.15)
        assert 0 <= d.disagreement <= 1

    def test_council_persists(self, db):
        council = GovernanceCouncil(db)
        council.decide("c-3", "Docker compose v2 replaced docker-compose command.",
                       "Deprecation", "deprecation", 0.9)
        stats = council.get_stats()
        assert stats["total_decisions"] == 1


class TestFeedback:
    def test_no_regression_no_adjust(self, db):
        engine = FeedbackEngine(db)
        result = engine.record_regression("mmlu", 0.01)
        assert result["adjusted"] == 0

    def test_regression_tunes_thresholds(self, db):
        engine = FeedbackEngine(db)
        before = engine.get_current_thresholds()
        result = engine.record_regression("gsm8k", -0.08, knowledge_type="general")
        assert result["adjusted"] > 0
        after = engine.get_current_thresholds()
        assert after["high-novelty-train"]["novelty_min"] >= before["high-novelty-train"]["novelty_min"]

    def test_security_regression_tightens_security(self, db):
        engine = FeedbackEngine(db)
        before = engine.get_current_thresholds()
        engine.record_regression("security-bench", -0.05, knowledge_type="security")
        after = engine.get_current_thresholds()
        assert after["security-first"]["min_confidence"] <= before["security-first"]["min_confidence"]

    def test_reset_restores_defaults(self, db):
        engine = FeedbackEngine(db)
        engine.record_regression("gsm8k", -0.08)
        engine.reset_to_defaults()
        current = engine.get_current_thresholds()
        assert current["high-novelty-train"]["novelty_min"] == DEFAULT_THRESHOLDS["high-novelty-train"]["novelty_min"]


class TestRAG:
    def test_add_and_retrieve(self, db):
        kb = RAGKnowledgeBase(db)
        kb.add("r-1", "FastAPI 0.115 breaking change",
               "Deprecated app.router.add_api_route in favor of app.add_api_route.",
               "api_update", "changelog")
        ctx = kb.build_context("fastapi add_api_route deprecation", k=3)
        assert ctx["count"] == 1
        assert ctx["documents"][0]["knowledge_id"] == "r-1"

    def test_no_match_empty(self, db):
        kb = RAGKnowledgeBase(db)
        kb.add("r-2", "Docker compose", "docker compose v2 command", "api_update")
        ctx = kb.build_context("quantum physics entanglement", k=3)
        assert ctx["count"] == 0

    def test_ingest_governed_only_store_rag(self, db):
        kb = RAGKnowledgeBase(db)
        assert kb.ingest_governed("r-3", "recommend_lora", "some text", "t") is None
        doc_id = kb.ingest_governed("r-4", "store_rag", "api update text", "t", metadata={"source": "x"})
        assert doc_id is not None
        assert kb.stats()["total_documents"] == 1


class TestDynamicKG:
    def test_ingest_creates_nodes_and_edges(self, db):
        kg = KnowledgeGraph(db)
        result = kg.ingest_knowledge(
            "FastAPI uses pydantic for validation and Docker for deployment.",
            title="FastAPI stack", knowledge_type="framework")
        assert result["nodes_created"] >= 1
        assert result["edges_created"] >= 1
        stats = kg.get_stats()
        assert stats["total_nodes"] > 50
        assert stats["total_edges"] > 46

    def test_communities_detected(self, db):
        kg = KnowledgeGraph(db)
        kg.ingest_knowledge("FastAPI uses pydantic for validation.", knowledge_type="framework")
        communities = kg.communities()
        assert len(communities) >= 1
        assert any(c["size"] > 1 for c in communities)


class TestRouting:
    def test_classify_domain(self, db):
        router = AdapterRouter(db)
        assert router.classify("How do I create a FastAPI endpoint with pydantic?") == "fastapi"
        assert router.classify("Docker container deployment issue") == "docker"
        assert router.classify("hello world") == "general"

    def test_route_uses_best_adapter(self, db):
        router = AdapterRouter(db)
        router.register_adapter("adapter-fastapi", "fastapi", benchmark_score=0.85, baseline_score=0.7)
        result = router.route("build a fastapi api endpoint")
        assert result["domain"] == "fastapi"
        assert result["chosen_adapter"]["adapter_id"] == "adapter-fastapi"
        assert result["chosen_adapter"]["improvement"] == 0.15


class TestLineage:
    def test_trace_chain(self, db):
        tracker = LineageTracker(db)
        tracker.link("dataset", "ds-1", "adapter", "ad-1")
        tracker.link("governed", "g-1", "dataset", "ds-1")
        tracker.link("source", "url-1", "governed", "g-1")
        trace = tracker.trace("adapter", "ad-1")
        assert trace["length"] == 4
        types = [n["type"] for n in trace["chain"]]
        assert "dataset" in types and "governed" in types and "source" in types


class TestTelemetry:
    def test_stats_roi(self, db):
        telemetry = CostTelemetry(db)
        telemetry.record("ad-1", "training", 2.0, benchmark_delta=0.04)
        telemetry.record("ad-1", "training", 3.0, benchmark_delta=0.06)
        stats = telemetry.stats()
        assert stats["total_gpu_hours"] == 5.0
        assert stats["per_adapter"]["ad-1"]["runs"] == 2
        assert stats["per_adapter"]["ad-1"]["cost_per_point"] is not None


class TestAlerts:
    def test_notify_logs(self, db):
        alerts = AlertEngine(db)
        aid = alerts.notify("critical", "Benchmark regression detected", "gsm8k dropped")
        assert len(alerts.list_alerts()) == 1
        assert alerts.list_alerts()[0]["severity"] == "critical"


class TestProfiler:
    def test_dominant_stack(self, db):
        profiler = LearningProfiler(db)
        profiler.observe("How do I build a FastAPI endpoint with pydantic validation?")
        profiler.observe("Python list comprehension with pandas")
        profile = profiler.profile()
        assert profile["dominant_stack"] == "python"
