import pytest
from ..crawler.engine import CrawlerEngine
from ..crawler.models import CrawlRequest, SourceType, CrawledItem


@pytest.fixture
def engine():
    from ..database.sqlite import SQLiteStore
    db = SQLiteStore(db_path=":memory:")
    return CrawlerEngine(db=db)


class TestCrawlerEngine:
    def test_init_creates_table(self, engine):
        row = engine.db.fetchone(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='crawled_items'"
        )
        assert row is not None

    def test_save_and_list(self, engine):
        from datetime import datetime, timezone
        item = CrawledItem(
            id="test-1",
            source=SourceType.GITHUB_RELEASE,
            title="Test Release v1.0",
            url="https://github.com/test/repo/releases/v1.0",
            content="This is a test release with important changes",
            summary="Test release summary",
            crawled_at=datetime.now(timezone.utc).isoformat(),
            tags=["test", "release"],
            metadata={"repo": "test/repo"},
        )
        engine._save(item)
        items = engine.list_items()
        assert len(items) == 1
        assert items[0].title == "Test Release v1.0"
        assert items[0].source == SourceType.GITHUB_RELEASE

    def test_list_with_source_filter(self, engine):
        from datetime import datetime, timezone
        items_data = [
            CrawledItem(id="t1", source=SourceType.GITHUB_RELEASE, title="R1", url="https://a.com",
                        content="c", summary="s", crawled_at=datetime.now(timezone.utc).isoformat()),
            CrawledItem(id="t2", source=SourceType.OFFICIAL_DOCS, title="D1", url="https://b.com",
                        content="c", summary="s", crawled_at=datetime.now(timezone.utc).isoformat()),
        ]
        for item in items_data:
            engine._save(item)
        gh_items = engine.list_items(source="github_release")
        assert len(gh_items) == 1
        assert gh_items[0].id == "t1"

    def test_stats(self, engine):
        from datetime import datetime, timezone
        items_data = [
            CrawledItem(id="s1", source=SourceType.GITHUB_RELEASE, title="R1", url="https://a.com",
                        content="c", summary="s", crawled_at=datetime.now(timezone.utc).isoformat()),
            CrawledItem(id="s2", source=SourceType.GITHUB_RELEASE, title="R2", url="https://b.com",
                        content="c", summary="s", crawled_at=datetime.now(timezone.utc).isoformat()),
        ]
        for item in items_data:
            engine._save(item)
        stats = engine.stats()
        assert stats["total_crawled"] == 2
        assert stats["by_source"]["github_release"] == 2

    def test_mark_extracted(self, engine):
        from datetime import datetime, timezone
        item = CrawledItem(id="ext-1", source=SourceType.OFFICIAL_DOCS, title="Doc",
                           url="https://doc.com", content="doc content", summary="s",
                           crawled_at=datetime.now(timezone.utc).isoformat())
        engine._save(item)
        assert len(engine.get_unextracted()) == 1
        engine.mark_extracted("ext-1")
        assert len(engine.get_unextracted()) == 0
