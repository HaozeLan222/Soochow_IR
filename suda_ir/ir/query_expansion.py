from __future__ import annotations

from collections import defaultdict

from suda_ir.ir.tokenizer import tokenize


DOMAIN_SYNONYMS = {
    "自然语言处理": ["NLP", "中文信息处理", "机器翻译", "信息抽取", "文本挖掘", "文本理解"],
    "nlp": ["自然语言处理", "中文信息处理", "机器翻译", "信息抽取", "文本挖掘"],
    "机器翻译": ["自然语言处理", "NLP", "神经机器翻译", "统计机器翻译"],
    "信息抽取": ["自然语言处理", "实体识别", "关系抽取", "文本挖掘"],
    "文本挖掘": ["自然语言处理", "信息抽取", "文本理解", "数据挖掘"],
    "知识图谱": ["知识表示", "图数据", "智能问答", "语义网络", "实体关系"],
    "智能问答": ["知识图谱", "问答系统", "自然语言处理", "知识表示"],
    "问答系统": ["智能问答", "知识图谱", "自然语言处理", "知识表示"],
    "机器学习": ["深度学习", "模式识别", "人工智能", "数据挖掘"],
    "深度学习": ["机器学习", "神经网络", "人工智能", "计算机视觉"],
    "计算机视觉": ["图像处理", "模式识别", "医学图像", "深度学习"],
    "医学图像": ["计算机视觉", "图像处理", "医学影像", "深度学习"],
    "医学影像": ["医学图像", "计算机视觉", "图像处理", "深度学习"],
    "数据挖掘": ["机器学习", "知识发现", "图数据", "智能分析"],
    "图论": ["组合优化", "图算法", "离散数学"],
    "优化算法": ["组合优化", "运筹优化", "智能算法", "最优化"],
}


def expand_query(query: str) -> list[str]:
    normalized = query.strip().lower()
    if not normalized:
        return []

    expanded = [query.strip()]
    seen = {normalized}
    for key, synonyms in DOMAIN_SYNONYMS.items():
        key_norm = key.lower()
        if key_norm in normalized or normalized in key_norm:
            for synonym in synonyms:
                synonym_norm = synonym.lower()
                if synonym_norm not in seen:
                    expanded.append(synonym)
                    seen.add(synonym_norm)
    return expanded


def weighted_query_terms(query: str, *, expansion_weight: float = 0.65) -> dict[str, float]:
    weights: dict[str, float] = defaultdict(float)
    expanded = expand_query(query)
    if not expanded:
        return {}

    original_terms = tokenize(expanded[0])
    for term in original_terms:
        weights[term] = max(weights[term], 1.0)

    for phrase in expanded[1:]:
        for term in tokenize(phrase):
            weights[term] = max(weights[term], expansion_weight)
    return dict(weights)
