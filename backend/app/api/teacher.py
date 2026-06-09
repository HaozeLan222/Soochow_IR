from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.core.deps import get_engine
from app.schemas.models import TeacherDetail

router = APIRouter(prefix="/api", tags=["teachers"])


@router.get("/teachers/{doc_id}", response_model=TeacherDetail)
def get_teacher(
    doc_id: str,
    engine_name: str = Query("bm25", alias="engine", description="Engine name"),
    data: str | None = Query(None, description="Override data file path"),
) -> TeacherDetail:
    engine = get_engine(engine_name=engine_name, data_path=data)
    doc = engine.get_teacher(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Teacher {doc_id} not found")
    return TeacherDetail.from_teacher_doc(doc)


@router.get("/teachers", response_model=list[TeacherDetail])
def list_teachers(
    college: str | None = Query(None, description="Filter by college"),
    engine_name: str = Query("bm25", alias="engine", description="Engine name"),
    data: str | None = Query(None, description="Override data file path"),
) -> list[TeacherDetail]:
    engine = get_engine(engine_name=engine_name, data_path=data)
    docs = engine.list_teachers(college=college)
    return [
        TeacherDetail.from_teacher_doc(d).model_copy(
            update={"profile": (d.profile or "")[:300]}
        )
        for d in docs
    ]
