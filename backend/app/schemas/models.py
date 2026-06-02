from __future__ import annotations

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    q: str = Field(..., min_length=1, description="Search query")
    field: str = Field(default="all", description="Search field: all, name, college")
    top_k: int = Field(default=10, ge=1, le=100, description="Max results")
    college: str | None = Field(default=None, description="Filter by college name")


class TeacherResult(BaseModel):
    doc_id: str
    name: str = ""
    college: str = ""
    title: str = ""
    research: str = ""
    profile: str = ""
    url: str = ""
    score: float = 0.0
    matched_terms: list[str] = []


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
    extra: dict = {}


class CollegeStats(BaseModel):
    name: str
    count: int


class StatsResponse(BaseModel):
    total_teachers: int
    colleges: list[CollegeStats]
