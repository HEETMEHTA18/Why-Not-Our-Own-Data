from fastapi import APIRouter, Query
from typing import Optional, List
from .models import BenchmarkDomain, BenchmarkDifficulty, BenchmarkTask
from .registry import (
    get_all_tasks, get_all_suites, get_suite,
    get_tasks_by_domain, get_tasks_by_difficulty, get_stats,
)

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


@router.get("/")
def list_benchmarks():
    return get_all_suites()


@router.get("/stats")
def benchmark_stats():
    return get_stats()


@router.get("/domain/{domain}")
def get_domain_benchmarks(domain: str, difficulty: str = None, limit: int = 50):
    try:
        d = BenchmarkDomain(domain)
    except ValueError:
        return {"error": f"Unknown domain: {domain}"}

    if difficulty:
        try:
            diff = BenchmarkDifficulty(difficulty)
            tasks = [t for t in get_tasks_by_domain(d) if t.difficulty == diff]
        except ValueError:
            tasks = get_tasks_by_domain(d)
    else:
        tasks = get_tasks_by_domain(d)
    return {"domain": domain, "total": len(tasks), "tasks": [t.model_dump() for t in tasks[:limit]]}


@router.get("/random")
def get_random_tasks(domain: str = None, count: int = 5, difficulty: str = None):
    import random
    all_tasks = list(get_all_tasks())
    if domain:
        try:
            all_tasks = [t for t in all_tasks if t.domain.value == domain]
        except ValueError:
            pass
    if difficulty:
        try:
            all_tasks = [t for t in all_tasks if t.difficulty.value == difficulty]
        except ValueError:
            pass
    selected = random.sample(all_tasks, min(count, len(all_tasks)))
    return {"tasks": [t.model_dump() for t in selected], "count": len(selected)}


@router.get("/search")
def search_benchmarks(q: str = "", domain: str = None, limit: int = 20):
    q = q.lower()
    all_tasks = list(get_all_tasks())
    if domain:
        all_tasks = [t for t in all_tasks if t.domain.value == domain]
    if q:
        all_tasks = [t for t in all_tasks if q in t.prompt.lower() or q in t.description.lower()]
    return {"results": [t.model_dump() for t in all_tasks[:limit]], "count": len(all_tasks[:limit])}