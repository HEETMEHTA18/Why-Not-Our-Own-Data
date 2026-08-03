from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.deps import Container, get_container
from monitor.gpu import GPUMonitor
from shared.config import settings

router = APIRouter(prefix="/system", tags=["System"])


def _settings_snapshot() -> dict[str, Any]:
    return {
        "default_model": settings.training_default_model,
        "context_length": 4096,
        "temperature": 0.7,
        "max_tokens": 2048,
        "lora_rank": settings.training_default_lora_r,
        "learning_rate": settings.training_default_lr,
        "epochs": settings.training_default_epochs,
        "min_dataset_size": settings.min_examples_for_training if hasattr(settings, "min_examples_for_training") else 50,
        "training_ready": True,
        "benchmark_complete": True,
        "gpu_temp_warning": True,
        "error_alerts": True,
        "dataset_retention_days": settings.registry_adapter_retention,
        "log_retention_days": 30,
        "auto_cleanup": True,
    }


class SettingsUpdate(BaseModel):
    default_model: str | None = None
    lora_rank: int | None = None
    learning_rate: float | None = None
    epochs: int | None = None


@router.get("/settings")
async def get_settings() -> dict[str, Any]:
    return _settings_snapshot()


@router.put("/settings")
async def update_settings(payload: SettingsUpdate) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    if payload.default_model is not None:
        settings.training_default_model = payload.default_model
        updates["default_model"] = payload.default_model
    if payload.lora_rank is not None:
        settings.training_default_lora_r = payload.lora_rank
        updates["lora_rank"] = payload.lora_rank
    if payload.learning_rate is not None:
        settings.training_default_lr = payload.learning_rate
        updates["learning_rate"] = payload.learning_rate
    if payload.epochs is not None:
        settings.training_default_epochs = payload.epochs
        updates["epochs"] = payload.epochs

    env_path = Path(".env")
    lines: list[str] = []
    if env_path.exists():
        lines = env_path.read_text().splitlines()
    ENV_KEYS = {
        "default_model": "TATVIK_TRAINING_DEFAULT_MODEL",
        "lora_rank": "TATVIK_TRAINING_DEFAULT_LORA_R",
        "learning_rate": "TATVIK_TRAINING_DEFAULT_LR",
        "epochs": "TATVIK_TRAINING_DEFAULT_EPOCHS",
    }
    for key, value in updates.items():
        env_key = ENV_KEYS.get(key)
        if env_key is None:
            continue
        matched = False
        for i, line in enumerate(lines):
            if line.startswith(env_key + "="):
                lines[i] = f"{env_key}={value}"
                matched = True
                break
        if not matched:
            lines.append(f"{env_key}={value}")
    env_path.write_text("\n".join(lines) + "\n")

    return _settings_snapshot()


@router.get("/health")
async def health(container: Container = Depends(get_container)) -> dict[str, Any]:
    ollama_ok = await container.model_manager.is_ollama_running()
    return {
        "status": "ok",
        "ollama_running": ollama_ok,
        "gpu_available": container.gpu_monitor.is_gpu_available(),
    }


@router.get("/gpu")
async def gpu_status(container: Container = Depends(get_container)) -> dict[str, Any]:
    return container.gpu_monitor.get_stats()


@router.get("/scheduler")
async def scheduler_status(container: Container = Depends(get_container)) -> dict[str, Any]:
    return container.job_queue.get_stats()


@router.get("/scheduler/jobs")
async def list_jobs(
    limit: int = 50, container: Container = Depends(get_container),
) -> list[dict[str, Any]]:
    jobs = container.job_queue.list_jobs(limit)
    return [
        {
            "id": j.id,
            "type": j.job_type.value,
            "status": j.status.value,
            "progress": j.progress,
            "error": j.error,
            "retry_count": j.retry_count,
            "created_at": j.created_at.isoformat(),
            "started_at": j.started_at.isoformat() if j.started_at else None,
            "completed_at": j.completed_at.isoformat() if j.completed_at else None,
        }
        for j in jobs
    ]


@router.get("/logs")
async def system_logs(
    limit: int = 100,
    container: Container = Depends(get_container),
) -> list[dict[str, Any]]:
    logs: list[dict[str, Any]] = []

    for j in container.job_queue.list_jobs(limit):
        ts = j.completed_at or j.started_at or j.created_at
        logs.append({
            "id": f"job-{j.id}",
            "level": "error" if j.status.value == "failed" else ("success" if j.status.value == "completed" else "info"),
            "message": f"Job [{j.job_type.value}] {j.status.value}" + (f": {j.error}" if j.error else ""),
            "source": "scheduler",
            "timestamp": ts.isoformat() if ts else j.created_at.isoformat(),
        })

    try:
        results = await container.registry_manager.get_benchmarks(None)
        for r in (results or [])[:limit]:
            score = 0.0
            if getattr(r, "metrics", None):
                for v in r.metrics.values():
                    if isinstance(v, (int, float)):
                        score = float(v)
                        break
            logs.append({
                "id": f"bench-{getattr(r, 'id', r.created_at)}",
                "level": "success",
                "source": "evaluation",
                "message": f"Benchmark {getattr(r, 'task', '?')} → {score:.4f} ({getattr(r, 'base_model_id', '?')})",
                "timestamp": getattr(r, "created_at", None),
            })
    except Exception:
        pass

    try:
        import httpx
        resp = await httpx.AsyncClient(timeout=2.0).get("http://127.0.0.1:8000/sahapatha/status")
        if resp.status_code == 200:
            data = resp.json()
            logs.append({
                "id": "sahapatha-status",
                "level": "info",
                "source": "sahapatha",
                "message": f"Sahapatha: {data.get('total_versions', 0)} adapter versions trained, buffer size {data.get('buffer_size', 0)}",
                "timestamp": None,
            })
    except Exception:
        pass

    def _ts(x: dict[str, Any]) -> str:
        return x.get("timestamp") or ""

    logs = [l for l in logs if l.get("timestamp")]
    logs.sort(key=_ts, reverse=True)
    return logs[:limit]
