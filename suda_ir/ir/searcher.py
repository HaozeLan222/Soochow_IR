from __future__ import annotations

from suda_ir.ir.fielded_index import FieldedBM25Index
from suda_ir.ir.fuzzy import fuzzy_name_search
from suda_ir.ir.index import BM25Index, SearchResult
from suda_ir.ir.query_intent import analyze_query
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
            intent = analyze_query(query, field=field)
            allowed_doc_indices = self._college_doc_indices(intent.college) if intent.college else None
            if allowed_doc_indices is not None and not allowed_doc_indices:
                return []
            candidate_k = max(top_k, 20) if intent.kind == "paper" else top_k
            optimized_results = self.optimized_index.search(
                intent.cleaned_query,
                top_k=candidate_k,
                use_expansion=intent.use_expansion,
                use_fuzzy=intent.use_fuzzy,
                field_weights=intent.field_weights,
                expansion_weight=intent.expansion_weight,
                allowed_doc_indices=allowed_doc_indices,
            )
            if intent.kind == "paper":
                baseline_results = self.index.search(intent.original_query, top_k=candidate_k)
                return self._rrf_merge([optimized_results, baseline_results], top_k=top_k)
            return optimized_results[:top_k]
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

    def _college_doc_indices(self, college: str) -> set[int]:
        return {
            index
            for index, doc in enumerate(self.index.docs)
            if college and college in (doc.college or "")
        }

    def _rrf_merge(self, ranked_lists: list[list[SearchResult]], *, top_k: int, c: int = 60) -> list[SearchResult]:
        scores: dict[str, float] = {}
        docs_by_id = {}
        matched_terms: dict[str, set[str]] = {}
        for ranked in ranked_lists:
            for rank, result in enumerate(ranked, start=1):
                doc_id = result.doc.doc_id
                scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (c + rank)
                docs_by_id[doc_id] = result.doc
                matched_terms.setdefault(doc_id, set()).update(result.matched_terms)

        merged = [
            SearchResult(doc=docs_by_id[doc_id], score=score, matched_terms=sorted(matched_terms.get(doc_id, set())))
            for doc_id, score in scores.items()
        ]
        merged.sort(key=lambda item: item.score, reverse=True)
        return merged[:top_k]
