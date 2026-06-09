from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.deps import get_engine
from app.schemas.models import FrontendQuery, SearchResponse, TeacherResult

router = APIRouter(prefix="/api", tags=["search"])


@router.post("/search", response_model=SearchResponse)
def search(
    body: FrontendQuery,
    engine_name: str = Query("bm25", alias="engine", description="Engine name: bm25, optimized, stub"),
    data: str | None = Query(None, description="Override data file path"),
) -> SearchResponse:
    engine = get_engine(engine_name=engine_name, data_path=data)
    eq = body.to_engine_query()
    results = engine.search(eq)

    items = [TeacherResult.from_search_result(r) for r in results]
    return SearchResponse(total=len(items), results=items)
