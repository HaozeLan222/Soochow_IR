from __future__ import annotations

import re
from dataclasses import dataclass

from suda_ir.ir.index import FIELD_WEIGHTS
from suda_ir.ir.query_expansion import DOMAIN_SYNONYMS


COLLEGE_ALIASES = {
    "计算机科学与技术学院": "计算机科学与技术学院",
    "计算机学院": "计算机科学与技术学院",
    "计科院": "计算机科学与技术学院",
    "软件学院": "计算机科学与技术学院",
    "数学科学学院": "数学科学学院",
    "数学学院": "数学科学学院",
    "物理科学与技术学院": "物理科学与技术学院",
    "物理学院": "物理科学与技术学院",
    "功能纳米与软物质研究院": "功能纳米与软物质研究院",
    "纳米学院": "功能纳米与软物质研究院",
    "纳米研究院": "功能纳米与软物质研究院",
    "未来科学与工程学院": "未来科学与工程学院",
    "未来学院": "未来科学与工程学院",
}

TITLE_TERMS = ["特聘教授", "副教授", "副研究员", "高级实验师", "教授", "讲师", "研究员", "实验师", "博导", "硕导"]
PAPER_TERMS = ["论文", "成果", "发表", "期刊", "会议", "ACL", "CCF", "SCI", "Nature", "Arxiv", "H-index"]
COLLOQUIAL_TERMS = ["想找", "找", "做", "研究", "方向", "相关", "导师", "老师", "有没有", "推荐"]


@dataclass(frozen=True)
class QueryIntent:
    original_query: str
    cleaned_query: str
    kind: str = "general"
    college: str = ""
    title: str = ""
    field_weights: dict[str, float] | None = None
    use_expansion: bool = True
    expansion_weight: float = 0.65
    use_fuzzy: bool = True


def analyze_query(query: str, field: str = "all") -> QueryIntent:
    original = normalize_query(query)
    college, college_alias = extract_college(original)
    title = extract_title(original)
    cleaned = original
    if college_alias:
        cleaned = cleaned.replace(college_alias, " ")
    if title:
        cleaned = cleaned.replace(title, " ")
    cleaned = strip_query_fillers(cleaned)

    kind = infer_kind(original, cleaned, field=field, college=college, title=title)
    return QueryIntent(
        original_query=original,
        cleaned_query=cleaned or original,
        kind=kind,
        college=college,
        title=title,
        field_weights=weights_for_kind(kind),
        use_expansion=use_expansion_for_kind(kind),
        expansion_weight=expansion_weight_for_kind(kind),
        use_fuzzy=kind in {"name", "general", "research", "paper", "college_research", "title_research", "colloquial"},
    )


def normalize_query(query: str) -> str:
    return re.sub(r"\s+", " ", query.strip())


def extract_college(query: str) -> tuple[str, str]:
    for alias in sorted(COLLEGE_ALIASES, key=len, reverse=True):
        if alias in query:
            return COLLEGE_ALIASES[alias], alias
    return "", ""


def extract_title(query: str) -> str:
    for term in sorted(TITLE_TERMS, key=len, reverse=True):
        if term in query:
            return term
    return ""


def strip_query_fillers(query: str) -> str:
    cleaned = query
    for term in sorted(COLLOQUIAL_TERMS, key=len, reverse=True):
        cleaned = cleaned.replace(term, " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = cleaned.strip("，,。；;：:")
    return cleaned


def infer_kind(query: str, cleaned: str, *, field: str, college: str, title: str) -> str:
    if field == "name":
        return "name"
    if field == "papers":
        return "paper"
    if field == "research":
        return "research"
    if field == "title" or title:
        return "title_research" if cleaned else "title"
    if college and cleaned:
        return "college_research"
    if college:
        return "college"
    if any(term.lower() in query.lower() for term in PAPER_TERMS):
        return "paper"
    if any(term.lower() in query.lower() for term in DOMAIN_SYNONYMS):
        return "research"
    if any(term in query for term in COLLOQUIAL_TERMS):
        return "colloquial"
    return "general"


def weights_for_kind(kind: str) -> dict[str, float]:
    weights = dict(FIELD_WEIGHTS)
    if kind == "name":
        return {
            "name": 8.0,
            "research": 0.4,
            "papers": 0.3,
            "title": 0.3,
            "profile": 0.3,
            "college": 0.2,
            "content": 0.2,
        }
    if kind == "research":
        weights.update({"name": 0.6, "research": 5.5, "papers": 1.4, "title": 0.5, "profile": 1.3, "college": 0.2, "content": 0.7})
    if kind in {"college_research", "colloquial", "general"}:
        weights.update({"name": 0.8, "research": 5.0, "papers": 1.8, "title": 0.6, "profile": 1.4, "college": 0.2, "content": 0.9})
    if kind == "paper":
        weights.update({"name": 0.5, "research": 3.6, "papers": 3.2, "title": 0.5, "profile": 1.0, "college": 0.2, "content": 0.6})
    if kind == "title_research":
        weights.update({"name": 0.5, "research": 4.5, "papers": 1.8, "title": 3.2, "profile": 1.0, "college": 0.2, "content": 0.8})
    return weights


def use_expansion_for_kind(kind: str) -> bool:
    return kind not in {"name", "college", "title"}


def expansion_weight_for_kind(kind: str) -> float:
    if kind == "paper":
        return 0.25
    if kind == "research":
        return 0.35
    if kind in {"college_research", "title_research"}:
        return 0.4
    if kind == "colloquial":
        return 0.75
    return 0.55
