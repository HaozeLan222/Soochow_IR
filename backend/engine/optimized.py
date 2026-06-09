from __future__ import annotations

from collections import Counter

from domain.query import EngineQuery
from domain.search import SearchResult
from domain.teacher import TeacherDoc
from engine import SearchEngineBase, register_engine
from suda_ir.searcher import TutorSearcher
from suda_ir.storage import load_jsonl


@register_engine("optimized")
class OptimizedEngine(SearchEngineBase):
    def __init__(self) -> None:
        self._docs: list[TeacherDoc] = []
        self._searcher: TutorSearcher | None = None

    def load(self, data_path: str) -> None:
        self._docs = load_jsonl(data_path)
        self._searcher = TutorSearcher(self._docs, mode="optimized")

    def search(self, query: EngineQuery) -> list[SearchResult]:
        if not self._searcher:
            return []
        results = self._searcher.search(query.query, top_k=query.top_k, field=query.field)
        if query.college:
            results = [r for r in results if query.college in (r.doc.college or "")]
        return results

    def get_teacher(self, doc_id: str) -> TeacherDoc | None:
        for doc in self._docs:
            if doc.doc_id == doc_id:
                return doc
        return None

    def list_teachers(self, college: str | None = None) -> list[TeacherDoc]:
        if college:
            return [d for d in self._docs if college in d.college]
        return list(self._docs)

    def get_stats(self) -> dict:
        counts: Counter[str] = Counter()
        for doc in self._docs:
            counts[doc.college or "未知"] += 1
        return {
            "total_teachers": len(self._docs),
            "colleges": [{"name": k, "count": v} for k, v in counts.most_common()],
        }

