from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from domain.query import EngineQuery
from domain.search import SearchResult
from domain.teacher import TeacherDoc
from engine import SearchEngineBase, register_engine

MOCK_DATA_PATH = Path("mock/teachers.jsonl")


def _load_mock_docs() -> list[TeacherDoc]:
    docs: list[TeacherDoc] = []
    if MOCK_DATA_PATH.exists():
        with MOCK_DATA_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    docs.append(TeacherDoc.from_dict(json.loads(line)))
    return docs


@register_engine("stub")
class SearchEngineStub(SearchEngineBase):
    def __init__(self) -> None:
        self._docs: list[TeacherDoc] = []

    def load(self, data_path: str) -> None:
        self._docs = _load_mock_docs()

    def search(self, query: EngineQuery) -> list[SearchResult]:
        results: list[SearchResult] = []
        q = query.query.strip().lower()
        for doc in self._docs:
            if query.field == "name":
                if q in doc.name.lower():
                    results.append(SearchResult(doc=doc, score=100.0, matched_terms=[q]))
            elif query.field == "college":
                if q in doc.college.lower():
                    results.append(SearchResult(doc=doc, score=1.0, matched_terms=[q]))
            else:
                text = f"{doc.name} {doc.college} {doc.title} {doc.research} {doc.profile}".lower()
                if q in text:
                    results.append(SearchResult(doc=doc, score=10.0, matched_terms=[q]))
        return results[:query.top_k]

    def get_teacher(self, doc_id: str) -> TeacherDoc | None:
        for doc in self._docs:
            if doc.doc_id == doc_id:
                return doc
        return None

    def list_teachers(self, college: str | None = None) -> list[TeacherDoc]:
        if college:
            return [d for d in self._docs if college in d.college]
        return self._docs

    def get_stats(self) -> dict:
        college_counts: Counter[str] = Counter()
        for doc in self._docs:
            college_counts[doc.college or "未知"] += 1
        return {
            "total_teachers": len(self._docs),
            "colleges": [{"name": name, "count": count} for name, count in college_counts.most_common()],
        }
