from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from .inference_engine import InferenceEngine
from .config import SahapathaConfig

# Fallback pattern-based benchmarks (used when HF datasets cannot be loaded).
BENCHMARKS: dict[str, list[dict]] = {
    "async_python": [
        {"prompt": "Write an async function to fetch data from a URL using httpx",
         "expected_patterns": ["async def", "httpx", "await"]},
        {"prompt": "Create a FastAPI endpoint with async database session",
         "expected_patterns": ["async def", "AsyncSession", "Depends"]},
        {"prompt": "Implement async context manager for database connection",
         "expected_patterns": ["__aenter__", "__aexit__", "async with"]},
        {"prompt": "Write async task scheduler with asyncio",
         "expected_patterns": ["asyncio", "async def", "await"]},
        {"prompt": "Create async file reader using aiofiles",
         "expected_patterns": ["async with", "aiofiles", "await"]},
    ],
}

CODING_TASKS = ("humaneval", "mbpp")

_REASONING = re.compile(r"(?:<\|im_start\|>assistant|## Response|```python|```|[/][*]|#'# )", re.I)

PROMPT_TMPL = (
    "Complete the following Python function definition. Return ONLY the code, "
    "no explanation, no markdown.\n\n"
    "{prompt}"
)


class EvalHarness:
    def __init__(self, config: SahapathaConfig):
        self._config = config
        self._results_dir = Path(config.dataset_dir).parent / "eval_results"
        self._results_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Pattern-based benchmark (fallback / quick sanity)
    # ------------------------------------------------------------------
    def evaluate(self, engine: InferenceEngine, version: str | None = None) -> dict[str, Any]:
        engine.load_adapter(version)
        results = {}
        wanted = [b.lower() for b in self._config.evaluation.benchmarks]
        if "humaneval" in wanted or "mbpp" in wanted:
            try:
                results.update(self._evaluate_coding(engine, version, wanted))
            except Exception as e:
                results["coding_error"] = {"error": str(e)}
        if not results:
            results.update(self._evaluate_patterns(engine))
        return self._save(results, version)

    def _evaluate_patterns(self, engine: InferenceEngine) -> dict[str, Any]:
        results = {}
        for bench_name, cases in BENCHMARKS.items():
            case_results = []
            passed = 0
            for case in cases:
                start = time.time()
                try:
                    output = engine.generate(case["prompt"], max_new_tokens=150, temperature=0.1)
                except Exception as e:
                    output = f"[ERROR: {e}]"
                elapsed = time.time() - start
                patterns = case.get("expected_patterns", [])
                matched = sum(1 for p in patterns if p in output.lower())
                score = matched / len(patterns) if patterns else 0.0
                if score >= 0.5:
                    passed += 1
                case_results.append({
                    "prompt": case["prompt"][:80],
                    "patterns_found": matched,
                    "total_patterns": len(patterns),
                    "score": score,
                    "time_sec": round(elapsed, 2),
                    "output_preview": output[:200],
                })
            results[bench_name] = {
                "passed": passed,
                "total": len(cases),
                "accuracy": passed / len(cases) if cases else 0.0,
                "cases": case_results,
            }
        return results

    # ------------------------------------------------------------------
    # Real coding benchmarks (HumanEval / MBPP) — pass@1 via sandbox exec
    # ------------------------------------------------------------------
    def _load_tasks(self, name: str, max_samples: int) -> list[dict[str, Any]]:
        from datasets import load_dataset
        if name == "humaneval":
            ds = load_dataset("openai/openai_humaneval", split="test")
            tasks = [{
                "id": ex["task_id"],
                "prompt": ex["prompt"],
                "entry_point": ex["entry_point"],
                "test": ex["test"],
                "canonical_solution": ex["canonical_solution"],
            } for ex in ds]
        elif name == "mbpp":
            ds = load_dataset("google-research-datasets/mbpp", split="test")
            tasks = []
            for ex in ds:
                signature = ex["code"].strip().split("\n")[0]
                tasks.append({
                    "id": ex["task_id"],
                    "prompt": ex["text"] + "\n\n" + signature,
                    "signature": signature,
                    "test_list": ex["test_list"],
                    "test_setup_code": ex.get("test_setup_code", "") or "",
                    "canonical_solution": ex["code"],
                })
        else:
            raise ValueError(f"Unknown coding benchmark: {name}")
        if max_samples and max_samples > 0:
            step = max(1, len(tasks) // max_samples) if len(tasks) > max_samples else 1
            tasks = tasks[::step][:max_samples]
        return tasks

    def _evaluate_coding(self, engine: InferenceEngine, version: str | None, wanted: list[str]) -> dict[str, Any]:
        max_samples = self._config.evaluation.max_samples
        temperature = self._config.evaluation.temperature
        tokenizer = engine._tokenizer

        results = {}
        for name in wanted:
            if name not in CODING_TASKS:
                continue
            tasks = self._load_tasks(name, max_samples)
            case_results = []
            passed = 0
            for task in tasks:
                start = time.time()
                prompt = PROMPT_TMPL.format(prompt=task["prompt"])
                if tokenizer is not None and getattr(tokenizer, "chat_template", None):
                    msgs = [{"role": "user", "content": prompt}]
                    full = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
                else:
                    full = prompt
                try:
                    out = engine.generate_completion(full, max_new_tokens=256, temperature=temperature)
                except Exception as e:
                    out = ""
                elapsed = time.time() - start
                code = self._extract_code(out, "")
                ok, detail = self._run_sandbox(name, task, code)
                if ok:
                    passed += 1
                case_results.append({
                    "id": task["id"],
                    "passed": ok,
                    "time_sec": round(elapsed, 2),
                    "detail": detail,
                    "code": code[:300],
                })
            results[name] = {
                "passed": passed,
                "total": len(tasks),
                "accuracy": passed / len(tasks) if tasks else 0.0,
                "cases": case_results,
            }
        return results

    @staticmethod
    def _extract_code(out: str, prompt: str) -> str:
        code = out
        if prompt and code.startswith(prompt):
            code = code[len(prompt):]
        code = code.strip()
        fence = re.search(r"```(?:python)?\n(.*?)```", code, re.S)
        if fence:
            code = fence.group(1).strip()
        # Truncate at common test/validation markers the model emits after the
        # solution (its own asserts/prints would otherwise fail the sandbox).
        lines = code.split("\n")
        cleaned: list[str] = []
        for i, ln in enumerate(lines):
            stripped = ln.strip()
            if i > 0 and not stripped:
                continue
            lowered = stripped.lower()
            if any(m in lowered for m in ("if __name__ ==", "def check_function", "# test case",
                                          "# test cases", "assert ", "print(has_", "print(count",
                                          "print(same_")):
                break
            cleaned.append(ln)
        return "\n".join(cleaned).strip()

    def _run_sandbox(self, name: str, task: dict[str, Any], code: str) -> tuple[bool, str]:
        if name == "humaneval":
            program = (
                task["prompt"]
                + "\n" + code + "\n\n"
                + task["test"] + "\n"
                + f"check({task['entry_point']})\n"
            )
        else:
            body = code
            sig = task.get("signature", "").strip()
            if sig:
                sig_name = sig.split("(")[0].replace("def", "").strip()
                first = body.lstrip("\n").split("\n")[0].strip()
                if first.startswith("def ") and sig_name in first:
                    body = "\n".join(body.lstrip("\n").split("\n")[1:]).lstrip("\n")
            program = (
                sig + "\n" + body + "\n\n"
                + task["test_setup_code"] + "\n"
                + "\n".join(task["test_list"]) + "\n"
            )
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(program)
            path = f.name
        try:
            proc = subprocess.run(
                [sys.executable, path],
                capture_output=True, text=True, timeout=20,
                env={"PYTHONIOENCODING": "utf-8"},
            )
            if proc.returncode == 0:
                return True, "passed"
            err = (proc.stderr or "").strip().split("\n")
            return False, err[-1][:200] if err else "failed"
        except subprocess.TimeoutExpired:
            return False, "timeout"
        finally:
            Path(path).unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # Compare base vs adapter
    # ------------------------------------------------------------------
    def compare(
        self,
        engine: InferenceEngine,
        versions: list[str],
        benchmarks: list[str] | None = None,
    ) -> dict[str, Any]:
        wanted = [b.lower() for b in (benchmarks or self._config.evaluation.benchmarks)]
        wanted = [b for b in wanted if b in CODING_TASKS] or ["humaneval"]
        max_samples = self._config.evaluation.max_samples
        temperature = self._config.evaluation.temperature

        runs: dict[str, dict[str, Any]] = {}
        try:
            tasks_by_name = {b: self._load_tasks(b, max_samples) for b in wanted}
        except Exception as e:
            return {"error": f"Could not load coding datasets: {e}"}

        for label, adapter in [("base", None), *[(f"adapter:{v}", v) for v in versions]]:
            if adapter:
                engine.load_adapter(adapter)
            else:
                engine.load_base()
            tokenizer = engine._tokenizer
            runs[label] = {}
            for name in wanted:
                passed = 0
                for task in tasks_by_name[name]:
                    prompt = PROMPT_TMPL.format(prompt=task["prompt"])
                    if tokenizer is not None and getattr(tokenizer, "chat_template", None):
                        msgs = [{"role": "user", "content": prompt}]
                        full = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
                    else:
                        full = prompt
                    try:
                        out = engine.generate_completion(full, max_new_tokens=256, temperature=temperature)
                    except Exception:
                        out = ""
                    code = self._extract_code(out, "")
                    ok, _ = self._run_sandbox(name, task, code)
                    passed += int(ok)
                runs[label][name] = {
                    "passed": passed,
                    "total": len(tasks_by_name[name]),
                    "accuracy": passed / len(tasks_by_name[name]) if tasks_by_name[name] else 0.0,
                }
        result = {"runs": runs, "benchmarks": wanted}
        return self._save(result, "compare")

    def _save(self, results: dict, version: str | None) -> dict:
        filename = f"eval_{version or 'base'}_{int(time.time())}.json"
        path = self._results_dir / filename
        with open(path, "w") as f:
            json.dump(results, f, indent=2)
        for bench_name, data in results.items():
            if isinstance(data, dict) and "accuracy" in data:
                acc = data["accuracy"] * 100
                print(f"{bench_name}: {data['passed']}/{data['total']} passed ({acc:.0f}%)")
        return results
