from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import get_engine
from app.schemas.models import CollegeStats, StatsResponse

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats", response_model=StatsResponse)
def get_stats() -> StatsResponse:
    engine = get_engine()
    stats = engine.get_stats()
    colleges = [
        CollegeStats(name=c["name"], count=c["count"])
        for c in stats.get("colleges", [])
    ]
    return StatsResponse(
        total_teachers=stats.get("total_teachers", 0),
        colleges=colleges,
    )
