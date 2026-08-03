from __future__ import annotations

from shared.types import GPUInfo, Status, JobType


def test_status_values():
    assert Status.PENDING.value == "pending"
    assert Status.RUNNING.value == "running"
    assert Status.COMPLETED.value == "completed"
    assert Status.FAILED.value == "failed"
    assert Status.ROLLED_BACK.value == "rolled_back"


def test_job_type_values():
    assert JobType.TRAINING.value == "training"
    assert JobType.EVALUATION.value == "evaluation"
    assert JobType.DEPLOYMENT.value == "deployment"
    assert JobType.ROLLBACK.value == "rollback"


def test_gpu_info_creation():
    gpu = GPUInfo(
        index=0,
        name="NVIDIA RTX 4090",
        total_memory_mb=24576,
        used_memory_mb=10240,
        free_memory_mb=14336,
        utilization_pct=65.5,
        temperature_c=72.0,
    )
    assert gpu.name == "NVIDIA RTX 4090"
    assert gpu.utilization_pct == 65.5
