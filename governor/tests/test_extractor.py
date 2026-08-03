import pytest
from ..extractor.engine import ExtractionEngine
from ..extractor.models import KnowledgeType
from ..crawler.models import CrawledItem, SourceType
from ..extractor.parser import HTMLParser


@pytest.fixture
def engine():
    from ..database.sqlite import SQLiteStore
    db = SQLiteStore(db_path=":memory:")
    return ExtractionEngine(db=db)


class TestHTMLParser:
    def test_extract_text(self):
        html = "<html><head><title>Test Page</title></head><body><p>" + "A" * 100 + "</p></body></html>"
        result = HTMLParser.extract(html, "https://example.com")
        assert result["title"] == "Test Page"
        assert "AAA" in result["content"]

    def test_extract_code_blocks(self):
        text = "Here's how:\n```python\nprint('hello')\n```"
        blocks = HTMLParser.extract_code_blocks(text)
        assert len(blocks) == 1
        assert blocks[0]["language"] == "python"
        assert blocks[0]["code"] == "print('hello')"

    def test_guess_language(self):
        assert HTMLParser.guess_language("def foo():\n    return 1") == "python"
        assert HTMLParser.guess_language("function foo() { return 1; }") == "javascript"
        assert HTMLParser.guess_language("fn foo() -> i32 { 1 }") == "rust"
        assert HTMLParser.guess_language("func foo() int { return 1 }") == "go"
        assert HTMLParser.guess_language("no code here") is None


class TestExtractionEngine:
    def test_init_creates_table(self, engine):
        row = engine.db.fetchone(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='extracted_knowledge'"
        )
        assert row is not None

    def test_extract_with_code(self, engine):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        item = CrawledItem(
            id="ext-test-1",
            source=SourceType.GITHUB_RELEASE,
            title="New Python API v2.0",
            url="https://github.com/python/cpython/releases/v2.0",
            content="We added a new function:\n```python\ndef new_api():\n    return 'hello'\n```",
            summary="New API release",
            crawled_at=now,
        )
        result = engine.extract(item)
        assert result is not None
        assert result.knowledge_type == KnowledgeType.API_UPDATE
        assert len(result.code_snippets) > 0
        assert result.confidence > 0.5

    def test_extract_security_item(self, engine):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        item = CrawledItem(
            id="ext-test-2",
            source=SourceType.GITHUB_RELEASE,
            title="CVE-2024-1234: Security Fix",
            url="https://github.com/test/repo/security",
            content="A vulnerability was found in the authentication module...",
            summary="Security fix",
            crawled_at=now,
        )
        result = engine.extract(item)
        assert result is not None
        assert result.knowledge_type == KnowledgeType.SECURITY

    def test_extract_short_content_returns_none(self, engine):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        item = CrawledItem(
            id="ext-test-3",
            source=SourceType.GITHUB_RELEASE,
            title="Short",
            url="https://github.com",
            content="Hi",  # Too short
            summary="Hi",
            crawled_at=now,
        )
        result = engine.extract(item)
        assert result is None

    def test_extract_many(self, engine):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        items = [
            CrawledItem(id=f"em-{i}", source=SourceType.GITHUB_RELEASE, title=f"Title {i}",
                        url=f"https://example.com/{i}",
                        content="Some content that is long enough to extract " * 5,
                        summary=f"Summary {i}", crawled_at=now)
            for i in range(3)
        ]
        results = engine.extract_many(items)
        assert len(results) == 3

    def test_stats(self, engine):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        item = CrawledItem(id="stats-test", source=SourceType.GITHUB_RELEASE,
                           title="Stats Test", url="https://example.com",
                           content="Test content for stats " * 10, summary="s", crawled_at=now)
        engine.extract(item)
        stats = engine.stats()
        assert stats["total_extracted"] >= 1

    def test_classify_knowledge_types(self, engine):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        test_cases = [
            (SourceType.GITHUB_RELEASE, "Bug fix: crash on null input", KnowledgeType.BUG_FIX),
            (SourceType.GITHUB_RELEASE, "New API: added support for async", KnowledgeType.API_UPDATE),
            (SourceType.GITHUB_RELEASE, "Performance optimization: faster sorting", KnowledgeType.PERFORMANCE),
        ]
        for src, title, expected_ktype in test_cases:
            item = CrawledItem(
                id=f"kt-{expected_ktype.value}", source=src, title=title,
                url="https://example.com",
                content=f"Content about: {title}. This has enough words to be meaningful.",
                summary=title[:50], crawled_at=now,
            )
            result = engine.extract(item)
            assert result is not None, f"Failed for {title}"
            assert result.knowledge_type == expected_ktype, f"Expected {expected_ktype}, got {result.knowledge_type} for {title}"
