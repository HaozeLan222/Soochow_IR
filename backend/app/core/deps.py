from __future__ import annotations

import json
from pathlib import Path

from app.core.engine import SearchEngineBase
from domain.search import SearchResult
from domain.teacher import TeacherDoc

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


class SearchEngineStub(SearchEngineBase):
    def __init__(self, data_path: str) -> None:
        self._data_path = data_path
        self._docs = _load_mock_docs()

    def load(self, data_path: str) -> None:
        self._data_path = data_path

    def search(self, query: str, top_k: int = 10, field: str = "all") -> list[SearchResult]:
        results: list[SearchResult] = []
        query = query.strip().lower()
        for doc in self._docs:
            if field == "name":
                if query in doc.name.lower():
                    results.append(SearchResult(doc=doc, score=100.0, matched_terms=[query]))
            elif field == "college":
                if query in doc.college.lower():
                    results.append(SearchResult(doc=doc, score=1.0, matched_terms=[query]))
            else:
                text = f"{doc.name} {doc.college} {doc.title} {doc.research} {doc.profile}".lower()
                if query in text:
                    results.append(SearchResult(doc=doc, score=10.0, matched_terms=[query]))
        return results[:top_k]

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
        from collections import Counter

        college_counts: Counter[str] = Counter()
        for doc in self._docs:
            college_counts[doc.college or "未知"] += 1
        return {
            "total_teachers": len(self._docs),
            "colleges": [{"name": name, "count": count} for name, count in college_counts.most_common()],
        }


_engine: SearchEngineBase | None = None


def get_engine(data_path: str | None = None) -> SearchEngineBase:
    global _engine
    if _engine is None:
        from app.core.config import settings

        _engine = SearchEngineStub(data_path or settings.DEFAULT_DATA_FILE)
    elif data_path and data_path != _engine._data_path:
        _engine.load(data_path)
    return _engine
