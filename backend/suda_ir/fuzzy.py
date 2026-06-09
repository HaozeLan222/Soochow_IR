from __future__ import annotations

from difflib import SequenceMatcher

from domain.search import SearchResult
from domain.teacher import TeacherDoc


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


def fuzzy_name_bonus(query: str, doc: TeacherDoc) -> float:
    if not (doc.name and 2 <= len(query.strip()) <= 6):
        return 0.0
    score = similarity(query, doc.name)
    if score < 82.0:
        return 0.0
    return (score - 80.0) / 4.0

