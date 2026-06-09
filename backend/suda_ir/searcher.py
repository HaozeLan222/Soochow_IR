from __future__ import annotations

from domain.search import SearchResult
from domain.teacher import TeacherDoc
from suda_ir.index import BM25Index


class TutorSearcher:
    def __init__(self, docs: list[TeacherDoc]) -> None:
        self.index = BM25Index(docs)

    def search(self, query: str, top_k: int = 10, field: str = "all") -> list[SearchResult]:
        if field == "name":
            return self._search_name(query, top_k)
        if field == "college":
            return self._filter_contains("college", query, top_k)
        return self.index.search(query, top_k=top_k)

    def _search_name(self, query: str, top_k: int) -> list[SearchResult]:
        query = query.strip()
        results: list[SearchResult] = []
        for doc in self.index.docs:
            if doc.name == query:
                results.append(SearchResult(doc=doc, score=100.0, matched_terms=[query]))
            elif query and query in doc.name:
                results.append(SearchResult(doc=doc, score=50.0, matched_terms=[query]))
        return results[:top_k]

    def _filter_contains(self, field: str, query: str, top_k: int) -> list[SearchResult]:
        query = query.strip()
        results = []
        for doc in self.index.docs:
            value = getattr(doc, field, "") or ""
            if query and query in value:
                results.append(SearchResult(doc=doc, score=1.0, matched_terms=[query]))
        return results[:top_k]
