from __future__ import annotations

import os
from pathlib import Path


class Settings:
    PROJECT_NAME: str = "Soochow IR API"
    VERSION: str = "0.1.0"
    DATA_DIR: Path = Path(os.getenv("SUDA_IR_DATA_DIR", "data"))
    DEFAULT_DATA_FILE: str = os.getenv(
        "SUDA_IR_DEFAULT_DATA", "data/sample/teachers.jsonl"
    )
    STATIC_DIR: Path = Path("static")
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


settings = Settings()
