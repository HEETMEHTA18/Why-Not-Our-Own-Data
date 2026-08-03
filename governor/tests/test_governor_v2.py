import pytest
from ..database.sqlite import SQLiteStore
from ..governor.governor_v2 import KnowledgeGovernor


@pytest.fixture
def db():
    return SQLiteStore(db_path=":memory:")


@pytest.fixture
def gov(db):
    return KnowledgeGovernor(db)


class TestPolicyConstraints:
    def test_security_policy_respects_min_confidence(self, gov):
        item = gov.govern_knowledge_item(
            knowledge_id="sec-low-conf",
            text="CVE in dependency, security patch needed.",
            title="Low confidence security note",
            knowledge_type="security",
            confidence=0.1,
        )
        assert item.action.value != "recommend_lora"

    def test_security_policy_high_confidence_recommends_lora(self, gov):
        item = gov.govern_knowledge_item(
            knowledge_id="sec-high-conf",
            text="CVE in dependency, security patch needed urgently.",
            title="Security advisory",
            knowledge_type="security",
            confidence=0.95,
        )
        assert item.action.value == "recommend_lora"

    def test_low_quality_ignored(self, gov):
        item = gov.govern_knowledge_item(
            knowledge_id="generic-low",
            text="Some vague note.",
            title="Unclear note",
            knowledge_type="general",
            confidence=0.2,
        )
        assert item.action.value == "ignore"

    def test_api_update_goes_to_rag(self, gov):
        item = gov.govern_knowledge_item(
            knowledge_id="api-update",
            text="Function deprecated in next version, use new API instead.",
            title="API deprecation",
            knowledge_type="api_update",
            confidence=0.9,
        )
        assert item.action.value == "store_rag"

    def test_framework_goes_to_kg(self, gov):
        item = gov.govern_knowledge_item(
            knowledge_id="fw-pattern",
            text="Service layer architecture pattern for FastAPI applications.",
            title="Architecture best practice",
            knowledge_type="framework",
            confidence=0.8,
        )
        assert item.action.value == "store_kg"

    def test_all_four_actions_reachable(self, gov):
        actions = set()
        for kid, text, title, ktype, conf in [
            ("a", "CVE-2026 patch for critical RCE in websocket handshake.", "Security advisory", "security", 0.98),
            ("b", "Deprecated endpoint in v2, replaced by /api/v3.", "API deprecation", "api_update", 0.9),
            ("c", "Zero-copy tensor slicing pattern for LoRA.", "Framework pattern", "framework", 0.8),
            ("d", "Random vague note.", "Unclear", "general", 0.2),
        ]:
            actions.add(gov.govern_knowledge_item(
                knowledge_id=kid, text=text, title=title,
                knowledge_type=ktype, confidence=conf,
            ).action.value)
        assert actions == {"recommend_lora", "store_rag", "store_kg", "ignore"}

    def test_batch_governs_multiple(self, gov):
        items = [
            {"knowledge_id": f"b{i}", "text": "Some generic note.", "title": f"Note {i}",
             "knowledge_type": "general", "confidence": 0.5}
            for i in range(5)
        ]
        results = gov.govern_batch(items)
        assert len(results) == 5
