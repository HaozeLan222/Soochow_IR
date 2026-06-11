from __future__ import annotations

import re
from collections.abc import Sequence

from suda_ir.ir.query_intent import PAPER_TERMS, QueryIntent
from suda_ir.ir.query_expansion import DOMAIN_SYNONYMS


DESCRIPTIVE_TERMS = [
    "研究",
    "从事",
    "做",
    "方向",
    "相关",
    "导师",
    "老师",
    "哪些",
    "有没有",
    "推荐",
    "理解",
    "分析",
    "应用",
]

NON_SEMANTIC_KINDS = {"name", "paper", "college", "title"}
SEMANTIC_CANDIDATE_KINDS = {"general", "research", "college_research", "title_research", "colloquial"}


def should_use_semantic(
    query: str,
    intent: QueryIntent,
    *,
    field: str = "all",
    optimized_results: Sequence[object] | None = None,
    min_query_chars: int = 10,
) -> bool:
    """Return True when embedding recall is likely to add useful semantic coverage.

    The gate is intentionally conservative. It avoids name, paper and direct field
    queries, and mainly targets natural-language rewrites such as "研究人类语言理解
    和文本分析的老师". This keeps optimized BM25 as the default path and uses
    semantic recall only as a supplemental signal.
    """

    if field != "all":
        return False
    if intent.kind in NON_SEMANTIC_KINDS:
        return False
    if has_paper_keyword(query):
        return False

    compact_query = re.sub(r"\s+", "", query or "")
    if len(compact_query) < min_query_chars:
        return False

    if intent.kind not in SEMANTIC_CANDIDATE_KINDS:
        return False

    if intent.kind == "research" and has_direct_domain_keyword(compact_query):
        return False

    if intent.kind == "colloquial":
        return True

    if has_descriptive_language(compact_query):
        return True

    return is_weak_optimized_result(optimized_results)


def has_descriptive_language(query: str) -> bool:
    return any(term in query for term in DESCRIPTIVE_TERMS)


def has_direct_domain_keyword(query: str) -> bool:
    normalized = (query or "").lower()
    return any(term.lower() in normalized for term in DOMAIN_SYNONYMS)


def has_paper_keyword(query: str) -> bool:
    normalized = (query or "").lower()
    return any(term.lower() in normalized for term in PAPER_TERMS)


def is_weak_optimized_result(results: Sequence[object] | None) -> bool:
    if results is None:
        return False
    if not results:
        return True
    return False
