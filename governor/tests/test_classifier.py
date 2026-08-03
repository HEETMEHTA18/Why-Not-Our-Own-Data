import pytest
from ..classifier.engine import KnowledgeClassifier, SIGNAL_PATTERNS
from ..classifier.models import KnowledgeCategory


@pytest.fixture
def classifier():
    from ..database.sqlite import SQLiteStore
    db = SQLiteStore(db_path=":memory:")
    return KnowledgeClassifier(db=db)


class TestKnowledgeClassifier:
    def test_init_creates_table(self, classifier):
        row = classifier.db.fetchone(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='classification_verdicts'"
        )
        assert row is not None

    def test_classify_text_api(self, classifier):
        results = classifier.classify_text("New API endpoint for user authentication", "API Update")
        categories = [c.value for c, _, _ in results]
        assert KnowledgeCategory.API_UPDATE.value in categories

    def test_classify_text_security(self, classifier):
        results = classifier.classify_text("CVE-2024-1234 vulnerability in auth module")
        categories = [c.value for c, _, _ in results]
        assert KnowledgeCategory.SECURITY.value in categories

    def test_classify_text_bug(self, classifier):
        results = classifier.classify_text("Fixed bug #456 where app would crash on null input")
        categories = [c.value for c, _, _ in results]
        assert KnowledgeCategory.BUG_FIX.value in categories

    def test_classify_text_performance(self, classifier):
        results = classifier.classify_text("Performance optimization: reduced latency by 50%")
        categories = [c.value for c, _, _ in results]
        assert KnowledgeCategory.PERFORMANCE.value in categories

    def test_classify_text_deprecation(self, classifier):
        results = classifier.classify_text("This API is deprecated and will be removed in v3")
        categories = [c.value for c, _, _ in results]
        assert KnowledgeCategory.DEPRECATION.value in categories

    def test_classify_item_stores_verdict(self, classifier):
        verdict = classifier.classify_item(
            item_id="item-1",
            text="Fixed security vulnerability in authentication",
            item_type="crawled",
            title="Security Fix",
        )
        assert verdict.item_id == "item-1"
        assert verdict.category == KnowledgeCategory.SECURITY
        assert verdict.confidence > 0

    def test_classify_item_with_code(self, classifier):
        verdict = classifier.classify_item(
            item_id="item-2",
            text="New React hook for state management",
            item_type="crawled",
            title="React Hook",
            code_snippets=["import { useState } from 'react'"],
        )
        assert verdict.category == KnowledgeCategory.FRAMEWORK

    def test_stats(self, classifier):
        classifier.classify_item("s1", "security vulnerability CVE exploit", "crawled")
        classifier.classify_item("s2", "new API function added support", "crawled")
        stats = classifier.stats()
        assert stats["total_classified"] >= 2
        assert len(stats["categories"]) == len(KnowledgeCategory)

    def test_get_verdicts(self, classifier):
        classifier.classify_item("gv-1", "bug fix crash", "crawled", title="Bug")
        verdicts = classifier.get_verdicts(limit=10)
        assert len(verdicts) >= 1
        assert verdicts[0]["item_id"] == "gv-1"

    def test_all_categories_have_patterns(self):
        for cat in KnowledgeCategory:
            assert cat in SIGNAL_PATTERNS, f"Missing patterns for {cat}"
            assert len(SIGNAL_PATTERNS[cat]) > 0, f"Empty patterns for {cat}"
