from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class BenchmarkDifficulty(str, Enum):
    BEGINNER = "beginner"
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


class BenchmarkDomain(str, Enum):
    PYTHON = "python"
    FASTAPI = "fastapi"
    REACT = "react"
    NEXTJS = "nextjs"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    GITHUB_ACTIONS = "github_actions"
    LINUX = "linux"
    SQL = "sql"
    SYSTEM_DESIGN = "system_design"
    REFACTORING = "refactoring"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    SECURITY = "security"
    GIT = "git"
    GENERAL = "general"


class BenchmarkTask(BaseModel):
    id: str
    domain: BenchmarkDomain
    difficulty: BenchmarkDifficulty
    prompt: str
    expected_patterns: List[str]
    description: str = ""
    language: str = ""


class BenchmarkSuite(BaseModel):
    domain: BenchmarkDomain
    tasks: List[BenchmarkTask]
    total: int
    by_difficulty: dict