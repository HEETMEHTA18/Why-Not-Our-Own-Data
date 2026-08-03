import uuid
from datetime import datetime, timezone
from typing import List, Optional
from ..database.sqlite import SQLiteStore
from .models import CrawledItem, CrawlRequest, SourceType
from .github import GitHubCrawler
from .web import WebCrawler


DEFAULT_REPOS = [
    "python/cpython",
    "rust-lang/rust",
    "golang/go",
    "nodejs/node",
    "typescript-eslint/typescript-eslint",
    "microsoft/TypeScript",
    "reactjs/react.dev",
    "vercel/next.js",
    "langchain-ai/langchain",
    "huggingface/transformers",
    "unslothai/unsloth",
    "vllm-project/vllm",
    "ollama/ollama",
    "openai/openai-python",
]

DEFAULT_DOCS = [
    "https://docs.python.org/3/whatsnew/changelog.html",
    "https://react.dev/blog",
    "https://nodejs.org/en/blog",
    "https://kubernetes.io/docs/concepts/",
]

STACK_OVERFLOW_TAGS = ["python", "javascript", "typescript", "rust", "reactjs", "next.js", "api-design"]


class CrawlerEngine:
    def __init__(self, db: Optional[SQLiteStore] = None):
        self.db = db or SQLiteStore()
        self.github = GitHubCrawler()
        self.web = WebCrawler()
        self._init_table()

    def _init_table(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS crawled_items (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                content TEXT,
                summary TEXT,
                published TEXT,
                crawled_at TEXT NOT NULL,
                author TEXT,
                tags TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}',
                extracted INTEGER DEFAULT 0
            )
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_crawled_source ON crawled_items(source)
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_crawled_published ON crawled_items(published)
        """)

    def _save(self, item: CrawledItem):
        self.db.execute(
            """INSERT OR REPLACE INTO crawled_items
               (id, source, title, url, content, summary, published, crawled_at, author, tags, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (item.id, item.source.value, item.title, item.url, item.content, item.summary,
             item.published, item.crawled_at, item.author, str(item.tags), str(item.metadata)),
        )

    async def crawl(self, request: CrawlRequest) -> List[CrawledItem]:
        if request.source == SourceType.GITHUB_RELEASE:
            repos = request.urls or DEFAULT_REPOS
            items = []
            for repo in repos:
                items.extend(await self.github.fetch_releases(repo, request.since_days))
                items.extend(await self.github.fetch_commits(repo, since_days=request.since_days))
            for item in items[:request.max_items]:
                self._save(item)
            return items[:request.max_items]

        elif request.source == SourceType.OFFICIAL_DOCS:
            urls = request.urls or DEFAULT_DOCS
            items = []
            for url in urls:
                items.extend(await self.web.fetch_docs(url, max_pages=5))
            for item in items[:request.max_items]:
                self._save(item)
            return items[:request.max_items]

        elif request.source == SourceType.HUGGING_FACE:
            models = request.urls or ["unsloth/unsloth", "huggingface/transformers", "meta-llama/Llama-2"]
            items = []
            for m in models:
                items.extend(await self.web.fetch_hf(m, request.since_days))
            for item in items[:request.max_items]:
                self._save(item)
            return items[:request.max_items]

        elif request.source == SourceType.ARXIV_PAPER:
            items = await self._fetch_arxiv(request)
            for item in items[:request.max_items]:
                self._save(item)
            return items[:request.max_items]

        elif request.source == SourceType.CHANGELOG:
            urls = request.urls or [
                "https://github.com/python/cpython/commits/main",
                "https://github.com/nodejs/node/commits/main",
            ]
            items = []
            for url in urls:
                page = await self.web.fetch_page(url, SourceType.CHANGELOG)
                if page:
                    items.append(page)
            for item in items[:request.max_items]:
                self._save(item)
            return items[:request.max_items]

        else:
            urls = request.urls or []
            items = []
            for url in urls:
                page = await self.web.fetch_page(url, request.source)
                if page:
                    items.append(page)
            for item in items[:request.max_items]:
                self._save(item)
            return items[:request.max_items]

    async def _fetch_arxiv(self, request: CrawlRequest) -> List[CrawledItem]:
        from datetime import datetime, timezone, timedelta
        max_results = min(request.max_items, 50)
        query = "+".join(request.urls) if request.urls else "cat:cs.LG+OR+cat:cs.CL+OR+cat:cs.SE"
        url = f"http://export.arxiv.org/api/query?search_query={query}&sortBy=submittedDate&sortOrder=descending&max_results={max_results}"

        import httpx
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                r = await client.get(url)
                if r.status_code != 200:
                    return []
                import xml.etree.ElementTree as ET
                root = ET.fromstring(r.text)
                ns = {"a": "http://www.w3.org/2005/Atom"}
                items = []
                for entry in root.findall("a:entry", ns):
                    title = entry.find("a:title", ns)
                    summary = entry.find("a:summary", ns)
                    published = entry.find("a:published", ns)
                    link = entry.find("a:id", ns)
                    authors = [a.find("a:name", ns).text for a in entry.findall("a:author", ns) if a.find("a:name", ns) is not None]
                    items.append(CrawledItem(
                        id=f"arxiv-{abs(hash(link.text)):x}" if link is not None else str(uuid.uuid4()),
                        source=SourceType.ARXIV_PAPER,
                        title=(title.text or "").replace("\n", " ").strip() if title is not None else "",
                        url=link.text if link is not None else "",
                        content=(summary.text or "").replace("\n", " ").strip()[:5000] if summary is not None else "",
                        summary=(summary.text or "").replace("\n", " ").strip()[:300] if summary is not None else "",
                        published=published.text if published is not None else None,
                        crawled_at=datetime.now(timezone.utc).isoformat(),
                        author=", ".join(authors),
                        tags=["research", "paper"],
                        metadata={"source": "arxiv"},
                    ))
                return items
            except Exception:
                return []

    async def crawl_all_sources(self, max_per_source: int = 5) -> List[CrawledItem]:
        all_items = []
        for source in SourceType:
            req = CrawlRequest(source=source, max_items=max_per_source, since_days=7)
            items = await self.crawl(req)
            all_items.extend(items)
        return all_items

    def list_items(self, source: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[CrawledItem]:
        if source:
            rows = self.db.fetchall(
                "SELECT * FROM crawled_items WHERE source = ? ORDER BY crawled_at DESC LIMIT ? OFFSET ?",
                (source, limit, offset),
            )
        else:
            rows = self.db.fetchall(
                "SELECT * FROM crawled_items ORDER BY crawled_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
        return [self._row_to_item(r) for r in rows]

    def _row_to_item(self, r: dict) -> CrawledItem:
        return CrawledItem(
            id=r["id"],
            source=SourceType(r["source"]),
            title=r["title"],
            url=r["url"],
            content=r.get("content") or "",
            summary=r.get("summary") or "",
            published=r.get("published"),
            crawled_at=r["crawled_at"],
            author=r.get("author"),
            tags=eval(r.get("tags", "[]")),
            metadata=eval(r.get("metadata", "{}")),
        )

    def stats(self) -> dict:
        total = self.db.fetchone("SELECT COUNT(*) as c FROM crawled_items")["c"]
        by_source = self.db.fetchall(
            "SELECT source, COUNT(*) as cnt FROM crawled_items GROUP BY source"
        )
        latest = self.db.fetchone(
            "SELECT crawled_at FROM crawled_items ORDER BY crawled_at DESC LIMIT 1"
        )
        return {
            "total_crawled": total,
            "by_source": {r["source"]: r["cnt"] for r in by_source},
            "latest_crawl": latest["crawled_at"] if latest else None,
        }

    def mark_extracted(self, item_id: str):
        self.db.execute("UPDATE crawled_items SET extracted = 1 WHERE id = ?", (item_id,))

    def get_unextracted(self, limit: int = 50) -> List[CrawledItem]:
        rows = self.db.fetchall(
            "SELECT * FROM crawled_items WHERE extracted = 0 ORDER BY crawled_at ASC LIMIT ?", (limit,)
        )
        return [self._row_to_item(r) for r in rows]
