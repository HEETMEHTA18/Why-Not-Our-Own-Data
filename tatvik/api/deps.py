from __future__ import annotations

from typing import AsyncGenerator

from deployment.manager import DeploymentManager
from deployment.rollback import RollbackManager
from evaluation.engine import BenchmarkEngine
from evaluation.runner import BenchmarkRunner
from monitor.gpu import GPUMonitor
from registry.manager import RegistryManager
from registry.repository import RegistryRepository
from runtime.client import OllamaClient
from runtime.llama_client import LlamaClient
from runtime.manager import ModelManager
from scheduler.queue import JobQueue
from scheduler.gpu import GPUMonitor as SchedulerGPUMonitor
from training.adapter import AdapterManager
from training.engine import TrainingEngine
from shared.config import settings
from shared.logging import configure_logging


class Container:
    def __init__(self) -> None:
        configure_logging()

        self.ollama_client = OllamaClient()
        self.llama_client = LlamaClient()
        self.model_manager = ModelManager(self.llama_client)

        self.registry_repo = RegistryRepository()
        self.registry_manager = RegistryManager(self.registry_repo)

        self.adapter_manager = AdapterManager()
        self.benchmark_runner = BenchmarkRunner()
        self.benchmark_engine = BenchmarkEngine(self.registry_manager, self.benchmark_runner)
        self.training_engine = TrainingEngine(self.registry_manager, self.adapter_manager)
        self.deployment_manager = DeploymentManager(self.registry_manager, self.benchmark_engine)
        self.rollback_manager = RollbackManager(self.registry_manager, self.benchmark_engine)

        self.job_queue = JobQueue(max_concurrent=settings.training_max_concurrent)
        self.gpu_monitor = GPUMonitor()

    async def initialize(self) -> None:
        await self.registry_repo.initialize()
        await self.gpu_monitor.start()

    async def shutdown(self) -> None:
        await self.job_queue.stop()
        await self.gpu_monitor.stop()
        await self.ollama_client.close()
        await self.registry_repo.close()


container = Container()


async def get_container() -> AsyncGenerator[Container, None]:
    yield container
