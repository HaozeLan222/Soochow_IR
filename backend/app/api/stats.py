from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.deps import get_engine
from app.schemas.models import CollegeStats, StatsResponse

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats", response_model=StatsResponse)
def get_stats(
    engine_name: str = Query("bm25", alias="engine", description="Engine name"),
    data: str | None = Query(None, description="Override data file path"),
) -> StatsResponse:
    engine = get_engine(engine_name=engine_name, data_path=data)
    stats = engine.get_stats()
    colleges = [
        CollegeStats(name=c["name"], count=c["count"])
        for c in stats.get("colleges", [])
    ]
    return StatsResponse(
        total_teachers=stats.get("total_teachers", 0),
        colleges=colleges,
    )
