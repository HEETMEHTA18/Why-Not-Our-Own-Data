#!/usr/bin/env python3
"""Tatvik AI Runtime — Entry point."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import uvicorn

from shared.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level=settings.log_level.lower(),
    )
