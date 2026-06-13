from __future__ import annotations

from collections import Counter
from pathlib import Path

from app.core.config import settings
from domain.query import EngineQuery
from domain.search import SearchResult
from domain.teacher import TeacherDoc
from engine import SearchEngineBase, register_engine
from suda_ir.query_intent import analyze_query
from suda_ir.semantic_gate import should_use_semantic
from suda_ir.semantic_index import SemanticDependencyError, SemanticIndex
from suda_ir.searcher import TutorSearcher
from suda_ir.storage import load_jsonl


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@register_engine("optimized")
class OptimizedEngine(SearchEngineBase):
    def __init__(self) -> None:
        self._docs: list[TeacherDoc] = []
        self._searcher: TutorSearcher | None = None
        self._semantic_index: SemanticIndex | None = None
        self._semantic_unavailable_reason: str = ""

    def load(self, data_path: str) -> None:
        self._docs = load_jsonl(data_path)
        self._searcher = TutorSearcher(self._docs, mode="optimized")

    def search(self, query: EngineQuery) -> list[SearchResult]:
        if not self._searcher:
            return []
        candidate_k = max(query.top_k, 50) if settings.SEMANTIC_OPTIMIZED_ENABLED else query.top_k
        results = self._searcher.search(query.query, top_k=candidate_k, field=query.field)
        if settings.SEMANTIC_OPTIMIZED_ENABLED:
            results = self._maybe_add_semantic(query, results, top_k=query.top_k)
        else:
            results = results[: query.top_k]
        if query.college:
            results = [r for r in results if query.college in (r.doc.college or "")]
        return results[: query.top_k]

    def _maybe_add_semantic(self, query: EngineQuery, optimized_results: list[SearchResult], *, top_k: int) -> list[SearchResult]:
        intent = analyze_query(query.query, field=query.field)
        if not should_use_semantic(query.query, intent, field=query.field, optimized_results=optimized_results):
            return optimized_results[:top_k]

        semantic_college = query.college or intent.college
        allowed_doc_indices = self._college_doc_indices(semantic_college) if semantic_college else None
        if allowed_doc_indices is not None and not allowed_doc_indices:
            return optimized_results[:top_k]

        semantic_query = intent.cleaned_query or intent.original_query
        try:
            semantic_results = self._get_semantic_index().search(
                semantic_query,
                top_k=max(top_k, 50),
                allowed_doc_indices=allowed_doc_indices,
            )
        except (SemanticDependencyError, ValueError, OSError, KeyError, RuntimeError) as exc:
            self._semantic_unavailable_reason = str(exc)
            return optimized_results[:top_k]

        return weighted_rrf_merge(
            [optimized_results, semantic_results],
            weights=[1.0, settings.SEMANTIC_WEIGHT],
            top_k=top_k,
        )

    def _get_semantic_index(self) -> SemanticIndex:
        if self._semantic_index is None:
            cache_path = Path(settings.SEMANTIC_CACHE)
            if not cache_path.is_absolute():
                cache_path = PROJECT_ROOT / cache_path
            self._semantic_index = SemanticIndex(
                self._docs,
                model_name=settings.SEMANTIC_MODEL,
                cache_path=cache_path,
                backend=settings.SEMANTIC_BACKEND,
                local_files_only=settings.SEMANTIC_LOCAL_FILES_ONLY,
            )
        return self._semantic_index

    def _college_doc_indices(self, college: str) -> set[int]:
        return {
            index
            for index, doc in enumerate(self._docs)
            if college and college in (doc.college or "")
        }

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
            "semantic_optimized_enabled": settings.SEMANTIC_OPTIMIZED_ENABLED,
            "semantic_unavailable_reason": self._semantic_unavailable_reason,
        }


def weighted_rrf_merge(
    ranked_lists: list[list[SearchResult]],
    *,
    weights: list[float],
    top_k: int,
    c: int = 60,
) -> list[SearchResult]:
    scores: dict[str, float] = {}
    docs_by_id: dict[str, TeacherDoc] = {}
    matched_terms: dict[str, set[str]] = {}
    for list_index, ranked in enumerate(ranked_lists):
        weight = weights[list_index] if list_index < len(weights) else 1.0
        for rank, result in enumerate(ranked, start=1):
            doc_id = result.doc.doc_id
            scores[doc_id] = scores.get(doc_id, 0.0) + weight / (c + rank)
            docs_by_id[doc_id] = result.doc
            matched_terms.setdefault(doc_id, set()).update(result.matched_terms)

    merged = [
        SearchResult(doc=docs_by_id[doc_id], score=score, matched_terms=sorted(matched_terms.get(doc_id, set())))
        for doc_id, score in scores.items()
    ]
    merged.sort(key=lambda item: item.score, reverse=True)
    return merged[:top_k]

