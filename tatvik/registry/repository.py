from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
import structlog

from shared.config import settings
from shared.types import Status

from .models import (
    AdapterRecord,
    BaseModelRecord,
    BenchmarkResult,
    ExperimentRecord,
    ModelVersion,
)

logger = structlog.get_logger()


class Base(DeclarativeBase):
    pass


class BaseModelTable(Base):
    __tablename__ = "base_models"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    tag: Mapped[str] = mapped_column(String(64), default="latest")
    digest: Mapped[str] = mapped_column(String(128), default="")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    is_available: Mapped[bool] = mapped_column(default=True)
    metadata_: Mapped[str] = mapped_column("metadata", Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


class AdapterTable(Base):
    __tablename__ = "adapters"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    base_model_id: Mapped[str] = mapped_column(String(32), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    name: Mapped[str] = mapped_column(String(255), default="")
    path: Mapped[str] = mapped_column(Text, default="")
    dataset_id: Mapped[str] = mapped_column(String(32), default="")
    dataset_hash: Mapped[str] = mapped_column(String(64), default="")
    training_config: Mapped[str] = mapped_column(Text, default="{}")
    metrics: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(32), default=Status.PENDING.value)
    parent_adapter_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    deployed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class BenchmarkTable(Base):
    __tablename__ = "benchmarks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    adapter_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    base_model_id: Mapped[str] = mapped_column(String(32), index=True)
    task: Mapped[str] = mapped_column(String(64))
    score: Mapped[float] = mapped_column(Float)
    metrics: Mapped[str] = mapped_column(Text, default="{}")
    samples: Mapped[int] = mapped_column(Integer, default=0)
    config: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class ExperimentTable(Base):
    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    experiment_type: Mapped[str] = mapped_column(String(64))
    base_model_id: Mapped[str] = mapped_column(String(32))
    adapter_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    config: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(32), default=Status.PENDING.value)
    metrics: Mapped[str] = mapped_column(Text, default="{}")
    benchmark_ids: Mapped[str] = mapped_column(Text, default="[]")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class RegistryRepository:
    def __init__(self) -> None:
        self._engine = create_async_engine(settings.resolved_registry_db_url, echo=False)
        self._session_factory = async_sessionmaker(self._engine, class_=AsyncSession, expire_on_commit=False)

    async def initialize(self) -> None:
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("registry_db_initialized")

    async def _session(self):
        async with self._session_factory() as session:
            yield session

    async def save_base_model(self, record: BaseModelRecord) -> BaseModelRecord:
        async with self._session_factory() as session:
            existing = await session.get(BaseModelTable, record.id)
            if existing:
                for k, v in record.model_dump().items():
                    if k == "metadata":
                        setattr(existing, "metadata_", __import__("json").dumps(v))
                    else:
                        setattr(existing, k, v)
            else:
                session.add(BaseModelTable(
                    id=record.id,
                    name=record.name,
                    tag=record.tag,
                    digest=record.digest,
                    size_bytes=record.size_bytes,
                    is_available=record.is_available,
                    metadata_=__import__("json").dumps(record.metadata),
                ))
            await session.commit()
        return record

    async def get_base_model(self, model_id: str) -> BaseModelRecord | None:
        async with self._session_factory() as session:
            row = await session.get(BaseModelTable, model_id)
            if not row:
                return None
            return BaseModelRecord(
                id=row.id, name=row.name, tag=row.tag, digest=row.digest,
                size_bytes=row.size_bytes, is_available=row.is_available,
                metadata=__import__("json").loads(row.metadata_ or "{}"),
                created_at=row.created_at, updated_at=row.updated_at,
            )

    async def list_base_models(self) -> list[BaseModelRecord]:
        async with self._session_factory() as session:
            from sqlalchemy import select
            result = await session.execute(select(BaseModelTable).order_by(BaseModelTable.name))
            rows = result.scalars().all()
            return [
                BaseModelRecord(
                    id=r.id, name=r.name, tag=r.tag, digest=r.digest,
                    size_bytes=r.size_bytes, is_available=r.is_available,
                    metadata=__import__("json").loads(r.metadata_ or "{}"),
                    created_at=r.created_at, updated_at=r.updated_at,
                )
                for r in rows
            ]

    async def save_adapter(self, record: AdapterRecord) -> AdapterRecord:
        async with self._session_factory() as session:
            existing = await session.get(AdapterTable, record.id)
            if existing:
                existing.base_model_id = record.base_model_id
                existing.version = record.version
                existing.name = record.name
                existing.path = record.path
                existing.dataset_id = record.dataset_id
                existing.dataset_hash = record.dataset_hash
                existing.training_config = __import__("json").dumps(record.training_config)
                existing.metrics = __import__("json").dumps(record.metrics)
                existing.status = record.status.value
                existing.parent_adapter_id = record.parent_adapter_id
                existing.notes = record.notes
                existing.deployed_at = record.deployed_at
            else:
                session.add(AdapterTable(
                    id=record.id, base_model_id=record.base_model_id,
                    version=record.version, name=record.name, path=record.path,
                    dataset_id=record.dataset_id, dataset_hash=record.dataset_hash,
                    training_config=__import__("json").dumps(record.training_config),
                    metrics=__import__("json").dumps(record.metrics),
                    status=record.status.value, parent_adapter_id=record.parent_adapter_id,
                    notes=record.notes, deployed_at=record.deployed_at,
                ))
            await session.commit()
        return record

    async def get_adapter(self, adapter_id: str) -> AdapterRecord | None:
        async with self._session_factory() as session:
            row = await session.get(AdapterTable, adapter_id)
            if not row:
                return None
            return self._adapter_from_row(row)

    async def list_adapters(self, base_model_id: str | None = None) -> list[AdapterRecord]:
        async with self._session_factory() as session:
            from sqlalchemy import select
            query = select(AdapterTable)
            if base_model_id:
                query = query.where(AdapterTable.base_model_id == base_model_id)
            query = query.order_by(AdapterTable.version.desc())
            result = await session.execute(query)
            return [self._adapter_from_row(r) for r in result.scalars().all()]

    async def get_latest_adapter(self, base_model_id: str) -> AdapterRecord | None:
        async with self._session_factory() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(AdapterTable)
                .where(AdapterTable.base_model_id == base_model_id)
                .order_by(AdapterTable.version.desc())
                .limit(1)
            )
            row = result.scalar_one_or_none()
            return self._adapter_from_row(row) if row else None

    async def save_benchmark(self, record: BenchmarkResult) -> BenchmarkResult:
        async with self._session_factory() as session:
            session.add(BenchmarkTable(
                id=record.id, adapter_id=record.adapter_id,
                base_model_id=record.base_model_id, task=record.task,
                score=record.score, metrics=__import__("json").dumps(record.metrics),
                samples=record.samples, config=__import__("json").dumps(record.config),
            ))
            await session.commit()
        return record

    async def get_benchmarks(self, adapter_id: str | None = None) -> list[BenchmarkResult]:
        async with self._session_factory() as session:
            from sqlalchemy import select
            query = select(BenchmarkTable)
            if adapter_id:
                query = query.where(BenchmarkTable.adapter_id == adapter_id)
            query = query.order_by(BenchmarkTable.created_at.desc())
            result = await session.execute(query)
            return [
                BenchmarkResult(
                    id=r.id, adapter_id=r.adapter_id, base_model_id=r.base_model_id,
                    task=r.task, score=r.score,
                    metrics=__import__("json").loads(r.metrics or "{}"),
                    samples=r.samples, config=__import__("json").loads(r.config or "{}"),
                    created_at=r.created_at,
                )
                for r in result.scalars().all()
            ]

    async def save_experiment(self, record: ExperimentRecord) -> ExperimentRecord:
        async with self._session_factory() as session:
            existing = await session.get(ExperimentTable, record.id)
            if existing:
                existing.experiment_type = record.experiment_type
                existing.base_model_id = record.base_model_id
                existing.adapter_id = record.adapter_id
                existing.config = __import__("json").dumps(record.config)
                existing.status = record.status.value
                existing.metrics = __import__("json").dumps(record.metrics)
                existing.benchmark_ids = __import__("json").dumps(record.benchmark_ids)
                existing.started_at = record.started_at
                existing.completed_at = record.completed_at
                existing.error = record.error
            else:
                session.add(ExperimentTable(
                    id=record.id, experiment_type=record.experiment_type,
                    base_model_id=record.base_model_id, adapter_id=record.adapter_id,
                    config=__import__("json").dumps(record.config),
                    status=record.status.value,
                    metrics=__import__("json").dumps(record.metrics),
                    benchmark_ids=__import__("json").dumps(record.benchmark_ids),
                    started_at=record.started_at, completed_at=record.completed_at,
                    error=record.error,
                ))
            await session.commit()
        return record

    async def list_experiments(self, limit: int = 50) -> list[ExperimentRecord]:
        async with self._session_factory() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(ExperimentTable).order_by(ExperimentTable.created_at.desc()).limit(limit)
            )
            return [
                ExperimentRecord(
                    id=r.id, experiment_type=r.experiment_type,
                    base_model_id=r.base_model_id, adapter_id=r.adapter_id,
                    config=__import__("json").loads(r.config or "{}"),
                    status=Status(r.status),
                    metrics=__import__("json").loads(r.metrics or "{}"),
                    benchmark_ids=__import__("json").loads(r.benchmark_ids or "[]"),
                    started_at=r.started_at, completed_at=r.completed_at,
                    error=r.error, created_at=r.created_at,
                )
                for r in result.scalars().all()
            ]

    def _adapter_from_row(self, row: AdapterTable) -> AdapterRecord:
        return AdapterRecord(
            id=row.id, base_model_id=row.base_model_id, version=row.version,
            name=row.name, path=row.path, dataset_id=row.dataset_id,
            dataset_hash=row.dataset_hash,
            training_config=__import__("json").loads(row.training_config or "{}"),
            metrics=__import__("json").loads(row.metrics or "{}"),
            status=Status(row.status), parent_adapter_id=row.parent_adapter_id,
            notes=row.notes, created_at=row.created_at, deployed_at=row.deployed_at,
        )

    async def close(self) -> None:
        await self._engine.dispose()
