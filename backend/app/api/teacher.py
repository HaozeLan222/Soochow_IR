from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.core.deps import get_engine
from app.schemas.models import TeacherDetail

router = APIRouter(prefix="/api", tags=["teachers"])


@router.get("/teachers/{doc_id}", response_model=TeacherDetail)
def get_teacher(
    doc_id: str,
    data: str | None = Query(None, description="Override data file path"),
) -> TeacherDetail:
    engine = get_engine(data)
    doc = engine.get_teacher(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Teacher {doc_id} not found")
    return TeacherDetail(
        doc_id=doc.doc_id,
        name=doc.name,
        college=doc.college,
        title=doc.title,
        research=doc.research,
        papers=doc.papers,
        profile=doc.profile,
        content=doc.content,
        url=doc.url,
        final_url=doc.final_url,
        extra=doc.extra,
    )


@router.get("/teachers", response_model=list[TeacherDetail])
def list_teachers(
    college: str | None = Query(None, description="Filter by college"),
    data: str | None = Query(None, description="Override data file path"),
) -> list[TeacherDetail]:
    engine = get_engine(data)
    docs = engine.list_teachers(college=college)
    return [
        TeacherDetail(
            doc_id=d.doc_id,
            name=d.name,
            college=d.college,
            title=d.title,
            research=d.research,
            profile=(d.profile or "")[:300],
            url=d.url,
        )
        for d in docs
    ]
