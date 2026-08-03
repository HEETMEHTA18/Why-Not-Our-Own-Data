import re
from datetime import datetime, timezone
from typing import List, Optional
from .models import CrawledItem, SourceType


class WebCrawler:
    async def fetch_page(self, url: str, source: SourceType) -> Optional[CrawledItem]:
        import httpx
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            try:
                r = await client.get(url, headers={"User-Agent": "Tatvik/1.0"})
                if r.status_code != 200:
                    return None
                html = r.text
            except Exception:
                return None

        from ..extractor.parser import HTMLParser
        parsed = HTMLParser.extract(html, url)

        return CrawledItem(
            id=f"web-{abs(hash(url)):x}",
            source=source,
            title=parsed.get("title", url),
            url=url,
            content=parsed.get("content", "")[:5000],
            summary=parsed.get("content", "")[:300],
            crawled_at=datetime.now(timezone.utc).isoformat(),
            tags=parsed.get("tags", []),
            metadata={"description": parsed.get("description", "")},
        )

    async def fetch_docs(self, url: str, max_pages: int = 10) -> List[CrawledItem]:
        import httpx
        from urllib.parse import urljoin
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            try:
                r = await client.get(url, headers={"User-Agent": "Tatvik/1.0"})
                if r.status_code != 200:
                    return []
                html = r.text
            except Exception:
                return []

        links = self._extract_links(html, url)
        items = []
        seen = set()
        for link in links[:max_pages]:
            if link in seen:
                continue
            seen.add(link)
            page = await self.fetch_page(link, SourceType.OFFICIAL_DOCS)
            if page:
                items.append(page)
        return items

    def _extract_links(self, html: str, base_url: str) -> List[str]:
        from urllib.parse import urljoin, urlparse
        links = set()
        for m in re.finditer(r'href="([^"]+)"', html):
            href = m.group(1)
            full = urljoin(base_url, href)
            if urlparse(full).netloc == urlparse(base_url).netloc:
                links.add(full)
        return list(links)

    async def fetch_hf(self, model_or_dataset: str, since_days: int = 7) -> List[CrawledItem]:
        import httpx
        from datetime import datetime, timezone, timedelta
        since = datetime.now(timezone.utc) - timedelta(days=since_days)
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                r = await client.get(
                    f"https://huggingface.co/api/models/{model_or_dataset}",
                    headers={"User-Agent": "Tatvik/1.0"},
                )
                if r.status_code != 200:
                    return []
                data = r.json()
            except Exception:
                return []

        last_modified = data.get("lastModified")
        if last_modified and datetime.fromisoformat(last_modified.replace("Z", "+00:00")) < since:
            return []

        return [CrawledItem(
            id=f"hf-{model_or_dataset.replace('/', '-')}",
            source=SourceType.HUGGING_FACE,
            title=data.get("modelId", model_or_dataset),
            url=f"https://huggingface.co/{model_or_dataset}",
            content=data.get("cardData", {}).get("text", "")[:5000],
            summary=data.get("cardData", {}).get("text", "")[:300],
            published=last_modified,
            crawled_at=datetime.now(timezone.utc).isoformat(),
            author=data.get("author"),
            tags=data.get("tags", []),
            metadata={
                "downloads": data.get("downloads"),
                "likes": data.get("likes"),
                "pipeline_tag": data.get("pipeline_tag"),
            },
        )]
