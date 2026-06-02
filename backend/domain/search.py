from __future__ import annotations

from dataclasses import dataclass

from domain.teacher import TeacherDoc


@dataclass
class SearchResult:
    doc: TeacherDoc
    score: float
    matched_terms: list[str]
