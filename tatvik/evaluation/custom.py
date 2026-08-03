from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class CustomBenchmarkCase(BaseModel):
    name: str
    prompt: str
    expected: str | None = None
    language: str = "python"
    difficulty: str = "medium"


class CustomBenchmark(BaseModel):
    name: str
    description: str = ""
    cases: list[CustomBenchmarkCase]


class CustomBenchmarkRunner:
    def __init__(self) -> None:
        self._cases: list[CustomBenchmarkCase] = []

    def load(self, path: str | Path) -> CustomBenchmark:
        data = json.loads(Path(path).read_text())
        benchmark = CustomBenchmark(**data)
        self._cases = benchmark.cases
        return benchmark

    def add_case(self, case: CustomBenchmarkCase) -> None:
        self._cases.append(case)

    async def run(
        self,
        generate_fn: Any,
        model_name: str,
    ) -> list[dict[str, Any]]:
        results = []
        for case in self._cases:
            try:
                response = await generate_fn(
                    model=model_name,
                    prompt=case.prompt,
                )
                results.append({
                    "name": case.name,
                    "prompt": case.prompt,
                    "response": response,
                    "expected": case.expected,
                    "language": case.language,
                    "difficulty": case.difficulty,
                })
            except Exception as e:
                results.append({
                    "name": case.name,
                    "error": str(e),
                })
        return results