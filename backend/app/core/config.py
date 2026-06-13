from __future__ import annotations

import os
from pathlib import Path


class Settings:
    PROJECT_NAME: str = "Soochow IR API"
    VERSION: str = "0.1.0"
    DATA_DIR: Path = Path(os.getenv("SUDA_IR_DATA_DIR", "data"))
    DEFAULT_DATA_FILE: str = os.getenv(
        "SUDA_IR_DEFAULT_DATA", "mock/teachers.jsonl"
    )
    STATIC_DIR: Path = Path("static")
    SEMANTIC_OPTIMIZED_ENABLED: bool = os.getenv("SUDA_IR_SEMANTIC_OPTIMIZED", "1").lower() not in {"0", "false", "no"}
    SEMANTIC_MODEL: str = os.getenv("SUDA_IR_SEMANTIC_MODEL", "BAAI/bge-small-zh-v1.5")
    SEMANTIC_CACHE: str = os.getenv("SUDA_IR_SEMANTIC_CACHE", "data/processed/eval/bge-small-zh-v1.5.npz")
    SEMANTIC_BACKEND: str = os.getenv("SUDA_IR_SEMANTIC_BACKEND", "sentence-transformers")
    SEMANTIC_LOCAL_FILES_ONLY: bool = os.getenv("SUDA_IR_SEMANTIC_LOCAL_FILES_ONLY", "1").lower() not in {"0", "false", "no"}
    SEMANTIC_WEIGHT: float = float(os.getenv("SUDA_IR_SEMANTIC_WEIGHT", "0.05"))
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


settings = Settings()
