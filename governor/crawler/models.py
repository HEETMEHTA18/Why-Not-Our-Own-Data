from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from enum import Enum


class SourceType(str, Enum):
    GITHUB_RELEASE = "github_release"
    OFFICIAL_DOCS = "official_docs"
    RFC = "rfc"
    LANGUAGE_SPEC = "language_spec"
    API_CHANGE = "api_change"
    CHANGELOG = "changelog"
    HUGGING_FACE = "hugging_face"
    STACK_OVERFLOW = "stack_overflow"
    ARXIV_PAPER = "arxiv_paper"
    BLOG = "blog"


class CrawledItem(BaseModel):
    id: str
    source: SourceType
    title: str
    url: str
    content: str
    summary: str
    published: Optional[str] = None
    crawled_at: str
    author: Optional[str] = None
    tags: List[str] = []
    metadata: dict = {}


class CrawlRequest(BaseModel):
    source: SourceType
    urls: Optional[List[str]] = None
    max_items: int = 10
    since_days: int = 7


class CrawlStats(BaseModel):
    total_crawled: int
    by_source: dict
    latest_crawl: Optional[str] = None
