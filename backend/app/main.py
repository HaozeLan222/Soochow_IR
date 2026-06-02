from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.search import router as search_router
from app.api.stats import router as stats_router
from app.api.teacher import router as teacher_router
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes (highest priority)
    app.include_router(search_router)
    app.include_router(teacher_router)
    app.include_router(stats_router)

    # Static files (lowest priority, must be last)
    static_dir = settings.STATIC_DIR
    if static_dir.exists():
        app.mount(
            "/", StaticFiles(directory=static_dir, html=True), name="static"
        )

    return app


app = create_app()
