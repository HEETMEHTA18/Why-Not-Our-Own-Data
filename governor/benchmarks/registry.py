from typing import List, Dict
from .models import BenchmarkDomain, BenchmarkDifficulty, BenchmarkTask, BenchmarkSuite
from .tasks_python import BENCHMARK_TASKS as PYTHON_TASKS
from .tasks_fastapi import BENCHMARK_TASKS as FASTAPI_TASKS
from .tasks_react import BENCHMARK_TASKS as REACT_TASKS
from .tasks_devops import BENCHMARK_TASKS as DEVOPS_TASKS
from .tasks_platform import BENCHMARK_TASKS as PLATFORM_TASKS
from .tasks_design import BENCHMARK_TASKS as DESIGN_TASKS


ALL_TASK_SOURCES = {
    BenchmarkDomain.PYTHON: PYTHON_TASKS,
    BenchmarkDomain.FASTAPI: FASTAPI_TASKS,
    BenchmarkDomain.REACT: REACT_TASKS,
    BenchmarkDomain.NEXTJS: REACT_TASKS,
    BenchmarkDomain.DOCKER: DEVOPS_TASKS,
    BenchmarkDomain.KUBERNETES: DEVOPS_TASKS,
    BenchmarkDomain.GITHUB_ACTIONS: DEVOPS_TASKS,
    BenchmarkDomain.GIT: DEVOPS_TASKS,
    BenchmarkDomain.SQL: PLATFORM_TASKS,
    BenchmarkDomain.LINUX: PLATFORM_TASKS,
    BenchmarkDomain.SECURITY: PLATFORM_TASKS,
    BenchmarkDomain.SYSTEM_DESIGN: DESIGN_TASKS,
    BenchmarkDomain.JAVASCRIPT: DESIGN_TASKS,
    BenchmarkDomain.TYPESCRIPT: DESIGN_TASKS,
}


def get_benchmark_domains() -> List[str]:
    return sorted(set(d.value for d in BenchmarkDomain))


def get_all_tasks() -> List[BenchmarkTask]:
    tasks = []
    seen_ids = set()
    for domain, src_list in ALL_TASK_SOURCES.items():
        for item in src_list:
            if isinstance(item, dict):
                tid = item.get("id", "")
                if tid and tid not in seen_ids:
                    seen_ids.add(tid)
                    if "domain" not in item:
                        item["domain"] = domain.value
                    tasks.append(BenchmarkTask(**item))
            elif isinstance(item, BenchmarkTask):
                if item.id not in seen_ids:
                    seen_ids.add(item.id)
                    tasks.append(item)
    return tasks


def get_tasks_by_domain(domain: BenchmarkDomain) -> List[BenchmarkTask]:
    return [t for t in get_all_tasks() if t.domain == domain]


def get_tasks_by_difficulty(difficulty: BenchmarkDifficulty) -> List[BenchmarkTask]:
    return [t for t in get_all_tasks() if t.difficulty == difficulty]


def get_suite(domain: BenchmarkDomain) -> BenchmarkSuite:
    tasks = get_tasks_by_domain(domain)
    by_diff = {}
    for d in BenchmarkDifficulty:
        count = sum(1 for t in tasks if t.difficulty == d)
        if count > 0:
            by_diff[d.value] = count
    return BenchmarkSuite(
        domain=domain,
        tasks=tasks,
        total=len(tasks),
        by_difficulty=by_diff,
    )


def get_all_suites() -> Dict[str, BenchmarkSuite]:
    return {d.value: get_suite(d) for d in BenchmarkDomain}


def get_stats() -> dict:
    all_tasks = get_all_tasks()
    by_domain = {}
    by_difficulty = {}
    for t in all_tasks:
        by_domain[t.domain.value] = by_domain.get(t.domain.value, 0) + 1
        by_difficulty[t.difficulty.value] = by_difficulty.get(t.difficulty.value, 0) + 1
    return {
        "total_tasks": len(all_tasks),
        "domains": len(by_domain),
        "by_domain": by_domain,
        "by_difficulty": by_difficulty,
    }