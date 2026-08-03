from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from shared.config import settings

router = APIRouter(prefix="/models", tags=["Context"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

INCLUDE_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".css", ".json", ".md", ".sh", ".toml", ".yaml", ".yml"}
SKIP_DIRS = {".git", ".next", "node_modules", ".venv", "venv", "dist", "build", "models", "data", "__pycache__", ".turbo", "coverage"}
MAX_SNIPPET_LINES = 40
MAX_SNIPPETS = 4


class ContextRequest(BaseModel):
    query: str
    max_results: int = MAX_SNIPPETS


class ContextSnippet(BaseModel):
    path: str
    line: int
    content: str
    score: float


class ContextResponse(BaseModel):
    query: str
    snippets: list[ContextSnippet]


def _tokenize(text: str) -> set[str]:
    tokens = set(re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{2,}", text.lower()))
    stopwords = {
        "the", "and", "for", "with", "that", "this", "how", "what", "where", "when",
        "which", "why", "can", "you", "tell", "explain", "write", "make", "create",
        "have", "from", "your", "code", "function", "about", "please", "some", "they",
        "there", "here", "then", "them", "just", "want", "like", "would", "should",
    }
    return tokens - stopwords


def _score_line(line: str, terms: set[str]) -> int:
    lower = line.lower()
    return sum(lower.count(t) for t in terms)


def _extract_snippet(file: Path, line_no: int, term: str) -> str:
    lines = file.read_text(errors="ignore").splitlines()
    start = max(0, line_no - 5)
    end = min(len(lines), line_no + MAX_SNIPPET_LINES)
    return "\n".join(lines[start:end])


@router.post("/context", response_model=ContextResponse)
async def search_context(req: ContextRequest) -> ContextResponse:
    terms = _tokenize(req.query)
    if not terms:
        return ContextResponse(query=req.query, snippets=[])

    results: list[tuple[float, Path, int, str]] = []
    for path in PROJECT_ROOT.rglob("*"):
        if path.is_dir():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in INCLUDE_EXTS:
            continue
        try:
            for i, line in enumerate(path.read_text(errors="ignore").splitlines(), 1):
                score = _score_line(line, terms)
                if score > 0:
                    results.append((score, path, i, line.strip()))
        except OSError:
            continue

    results.sort(key=lambda r: r[0], reverse=True)

    seen: set[str] = set()
    snippets: list[ContextSnippet] = []
    for score, path, line_no, first_line in results:
        rel = str(path.relative_to(PROJECT_ROOT))
        if rel in seen:
            continue
        seen.add(rel)
        content = _extract_snippet(path, line_no, terms)
        snippets.append(
            ContextSnippet(
                path=rel,
                line=line_no,
                content=content,
                score=float(score),
            )
        )
        if len(snippets) >= req.max_results:
            break

    return ContextResponse(query=req.query, snippets=snippets)
