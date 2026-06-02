from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.deps import get_engine
from app.schemas.models import SearchResponse, TeacherResult

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search", response_model=SearchResponse)
def search(
    q: str = Query(..., min_length=1, description="Search query"),
    field: str = Query("all", description="Search field: all, name, college"),
    top_k: int = Query(10, ge=1, le=100, description="Max results"),
    college: str | None = Query(None, description="Filter by college name"),
    data: str | None = Query(None, description="Override data file path"),
) -> SearchResponse:
    engine = get_engine(data)
    results = engine.search(q, top_k=top_k, field=field)

    if college:
        results = [r for r in results if college in (r.doc.college or "")]

    items = [
        TeacherResult(
            doc_id=r.doc.doc_id,
            name=r.doc.name,
            college=r.doc.college,
            title=r.doc.title,
            research=r.doc.research,
            profile=(r.doc.profile or "")[:300],
            url=r.doc.url,
            score=r.score,
            matched_terms=r.matched_terms,
        )
        for r in results
    ]
    return SearchResponse(total=len(items), results=items)
