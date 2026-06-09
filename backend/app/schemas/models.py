from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from domain.query import EngineQuery
from domain.search import SearchResult
from domain.teacher import TeacherDoc


class FrontendQuery(BaseModel):
    """前端发送的查询模型。"""
    query: str = Field(..., min_length=1, description="Search query")
    field: str = Field(default="all", description="Search field: all, name, college, research, papers, title")
    top_k: int = Field(default=10, ge=1, le=100, description="Max results")
    college: str | None = Field(default=None, description="Filter by college name")

    def to_engine_query(self) -> EngineQuery:
        return EngineQuery(
            query=self.query,
            field=self.field,
            top_k=self.top_k,
            college=self.college,
        )


class TeacherResult(BaseModel):
    doc_id: str
    name: str = ""
    college: str = ""
    title: str = ""
    research: str = ""
    papers: str = ""
    profile: str = ""
    content: str = ""
    url: str = ""
    final_url: str = ""
    email: str = ""
    phone: str = ""
    photo_url: str = ""
    score: float = 0.0
    matched_terms: list[str] = []

    @classmethod
    def from_search_result(cls, r: SearchResult) -> "TeacherResult":
        d = r.doc.to_dict()
        return cls(**d, score=r.score, matched_terms=r.matched_terms)


class SearchResponse(BaseModel):
    total: int
    results: list[TeacherResult]


class TeacherDetail(BaseModel):
    doc_id: str
    name: str = ""
    college: str = ""
    title: str = ""
    research: str = ""
    papers: str = ""
    profile: str = ""
    content: str = ""
    url: str = ""
    final_url: str = ""
    email: str = ""
    phone: str = ""
    photo_url: str = ""
    extra: dict[str, Any] = {}

    @classmethod
    def from_teacher_doc(cls, doc: TeacherDoc) -> "TeacherDetail":
        return cls(**doc.to_dict())


class CollegeStats(BaseModel):
    name: str
    count: int


class StatsResponse(BaseModel):
    total_teachers: int
    colleges: list[CollegeStats]
