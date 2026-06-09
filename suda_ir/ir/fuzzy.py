from __future__ import annotations

from difflib import SequenceMatcher

from suda_ir.ir.index import SearchResult
from suda_ir.models import TeacherDoc


def similarity(left: str, right: str) -> float:
    left = left.strip().lower()
    right = right.strip().lower()
    if not left or not right:
        return 0.0
    if left == right:
        return 100.0

    try:
        from rapidfuzz import fuzz

        return float(fuzz.WRatio(left, right))
    except ImportError:
        return SequenceMatcher(None, left, right).ratio() * 100.0


def fuzzy_name_search(query: str, docs: list[TeacherDoc], *, top_k: int = 10, threshold: float = 60.0) -> list[SearchResult]:
    query = query.strip()
    if not query:
        return []

    results: list[SearchResult] = []
    for doc in docs:
        if not doc.name:
            continue
        score = similarity(query, doc.name)
        if query in doc.name or doc.name in query:
            score = max(score, 88.0)
        if score >= threshold:
            results.append(SearchResult(doc=doc, score=score, matched_terms=[query]))

    results.sort(key=lambda item: item.score, reverse=True)
    return results[:top_k]


def fuzzy_field_bonus(query: str, doc: TeacherDoc, fields: list[str]) -> float:
    best = 0.0
    for field in fields:
        value = getattr(doc, field, "") or ""
        if not value:
            continue
        if query and query in value:
            best = max(best, 8.0)
        elif len(query) >= 2:
            for part in _candidate_parts(value):
                score = similarity(query, part)
                if score >= 82.0:
                    best = max(best, (score - 80.0) / 4.0)
    return best


def _candidate_parts(text: str) -> list[str]:
    separators = "、,，;；/|\n\t "
    parts = [text]
    for sep in separators:
        next_parts: list[str] = []
        for part in parts:
            next_parts.extend(part.split(sep))
        parts = next_parts
    return [part.strip() for part in parts if 2 <= len(part.strip()) <= 30]
