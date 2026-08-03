import re
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from .models import CrawledItem, SourceType


class GitHubCrawler:
    def __init__(self, token: Optional[str] = None):
        self.token = token
        self._client = None

    async def _get(self, url: str) -> Optional[dict]:
        import httpx
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, headers=headers)
            if r.status_code == 200:
                return r.json()
            return None

    async def fetch_releases(self, repo: str, since_days: int = 7) -> List[CrawledItem]:
        url = f"https://api.github.com/repos/{repo}/releases?per_page=20"
        data = await self._get(url)
        if not data:
            return []
        since = datetime.now(timezone.utc) - timedelta(days=since_days)
        items = []
        for rel in data:
            published = rel.get("published_at") or rel.get("created_at")
            if published:
                pub_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                if pub_dt < since:
                    continue
            body = rel.get("body") or ""
            clean_body = re.sub(r"<[^>]+>", "", body)[:2000]
            items.append(CrawledItem(
                id=f"gh-rel-{rel['id']}",
                source=SourceType.GITHUB_RELEASE,
                title=rel["name"] or rel["tag_name"],
                url=rel["html_url"],
                content=clean_body,
                summary=clean_body[:300],
                published=published,
                crawled_at=datetime.now(timezone.utc).isoformat(),
                author=rel.get("author", {}).get("login"),
                tags=[repo.split("/")[-1], "release"],
                metadata={"repo": repo, "tag": rel["tag_name"], "prerelease": rel.get("prerelease", False)},
            ))
        return items

    async def fetch_commits(self, repo: str, path: str = "", since_days: int = 7) -> List[CrawledItem]:
        since = (datetime.now(timezone.utc) - timedelta(days=since_days)).isoformat()
        url = f"https://api.github.com/repos/{repo}/commits?path={path}&since={since}&per_page=20"
        data = await self._get(url)
        if not data:
            return []
        items = []
        for c in data:
            commit = c.get("commit", {})
            msg = commit.get("message", "")
            items.append(CrawledItem(
                id=f"gh-commit-{c['sha'][:12]}",
                source=SourceType.CHANGELOG,
                title=msg.split("\n")[0],
                url=c["html_url"],
                content=msg[:2000],
                summary=msg[:300],
                published=commit.get("committer", {}).get("date"),
                crawled_at=datetime.now(timezone.utc).isoformat(),
                author=commit.get("author", {}).get("name"),
                tags=[repo.split("/")[-1]],
                metadata={"repo": repo, "sha": c["sha"]},
            ))
        return items
