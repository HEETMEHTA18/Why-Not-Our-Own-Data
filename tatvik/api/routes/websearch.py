from __future__ import annotations

import re
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/models", tags=["WebSearch"])

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"


class WebSearchRequest(BaseModel):
    query: str
    max_results: int = 5
    fetch_content: bool = True


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    content: str = ""


class WebSearchResponse(BaseModel):
    query: str
    results: list[SearchResult]


def _parse_html(text: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", text)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


async def _ddg_search(query: str) -> list[dict[str, str]]:
    """DuckDuckGo HTML search — no API key required."""
    url = "https://html.duckduckgo.com/html/"
    async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
        try:
            r = await client.post(url, data={"q": query, "b": "", "kl": "us-en"})
            r.raise_for_status()
        except Exception as e:
            raise HTTPException(502, f"DuckDuckGo request failed: {e}")

    html = r.text
    results = []
    # ddg html results: <a rel="nofollow" class="result__a" href="...">Title</a>
    #                    <a class="result__snippet" ...>Snippet</a>
    blocks = re.findall(r'<a rel="nofollow" class="result__a" href="([^"]+)"[^>]*>(.*?)</a>', html)
    snippets = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', html)
    for i, (href, title) in enumerate(blocks):
        title = re.sub(r"<[^>]+>", "", title).strip()
        snippet = re.sub(r"<[^>]+>", "", snippets[i]).strip() if i < len(snippets) else ""
        results.append({"title": title, "url": href, "snippet": snippet})
    return results


async def _fetch_page_text(url: str) -> str:
    async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
        try:
            r = await client.get(url)
            r.raise_for_status()
            return _parse_html(r.text)[:4000]
        except Exception:
            return ""


@router.post("/websearch", response_model=WebSearchResponse)
async def web_search(req: WebSearchRequest) -> WebSearchResponse:
    if not req.query.strip():
        raise HTTPException(400, "query is required")

    results = await _ddg_search(req.query)

    out: list[SearchResult] = []
    for r in results[: req.max_results]:
        content = ""
        if req.fetch_content:
            content = await _fetch_page_text(r["url"])
        out.append(
            SearchResult(
                title=r["title"],
                url=r["url"],
                snippet=r["snippet"],
                content=content,
            )
        )
    return WebSearchResponse(query=req.query, results=out)
