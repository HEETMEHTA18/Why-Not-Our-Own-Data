from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from api.deps import container
from api.routes import (
    context,
    deployment,
    evaluation,
    experiments,
    forecast,
    models,
    registry,
    sahapatha,
    system,
    training,
    websearch,
)
from gateways.whatsapp import router as whatsapp_router
from shared.logging import configure_logging

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging()
    logger.info("tatvik_runtime_starting")
    await container.initialize()
    await container.job_queue.start()
    yield
    await container.shutdown()
    logger.info("tatvik_runtime_stopped")


app = FastAPI(
    title="Tatvik AI Runtime",
    description="Privacy-first local AI operating system — Runtime, Training & Model Lifecycle API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_exception", error=str(exc), path=str(request.url))
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "code": "INTERNAL_ERROR"},
    )


app.include_router(models.router)
app.include_router(context.router)
app.include_router(websearch.router)
app.include_router(training.router)
app.include_router(evaluation.router)
app.include_router(registry.router)
app.include_router(deployment.router)
app.include_router(system.router)
app.include_router(experiments.router)
app.include_router(sahapatha.router)
app.include_router(forecast.router)
app.include_router(whatsapp_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": "Tatvik AI Runtime",
        "version": "0.1.0",
        "docs": "/docs",
    }
