from __future__ import annotations

from suda_ir.ir.fielded_index import FieldedBM25Index
from suda_ir.ir.fuzzy import fuzzy_name_search
from suda_ir.ir.index import BM25Index, SearchResult
from suda_ir.models import TeacherDoc


class TutorSearcher:
    def __init__(self, docs: list[TeacherDoc], mode: str = "baseline") -> None:
        self.mode = mode
        self.index = BM25Index(docs)
        self.optimized_index = FieldedBM25Index(docs)

    def search(self, query: str, top_k: int = 10, field: str = "all") -> list[SearchResult]:
        if field == "name":
            if self.mode == "optimized":
                return fuzzy_name_search(query, self.index.docs, top_k=top_k)
            return self._search_name(query, top_k)
        if field in {"college", "research", "papers", "title"}:
            return self._filter_contains(field, query, top_k)
        if self.mode == "optimized":
            return self.optimized_index.search(query, top_k=top_k)
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

