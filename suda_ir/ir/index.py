from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass

from suda_ir.ir.tokenizer import tokenize
from suda_ir.models import TeacherDoc


FIELD_WEIGHTS = {
    "name": 5.0,
    "research": 3.0,
    "papers": 2.0,
    "title": 1.5,
    "profile": 1.2,
    "college": 1.0,
    "content": 1.0,
}


@dataclass
class SearchResult:
    doc: TeacherDoc
    score: float
    matched_terms: list[str]


class BM25Index:
    def __init__(self, docs: list[TeacherDoc], k1: float = 1.5, b: float = 0.75) -> None:
        self.docs = docs
        self.k1 = k1
        self.b = b
        self.doc_tokens: list[list[str]] = []
        self.term_freqs: list[Counter[str]] = []
        self.doc_freq: dict[str, int] = defaultdict(int)
        self.avg_doc_len = 0.0
        self._build()

    def _build(self) -> None:
        total_len = 0
        for doc in self.docs:
            tokens = self._weighted_doc_tokens(doc)
            freq = Counter(tokens)
            self.doc_tokens.append(tokens)
            self.term_freqs.append(freq)
            total_len += len(tokens)
            for term in freq:
                self.doc_freq[term] += 1
        self.avg_doc_len = total_len / len(self.docs) if self.docs else 0.0

    def _weighted_doc_tokens(self, doc: TeacherDoc) -> list[str]:
        tokens: list[str] = []
        for field, weight in FIELD_WEIGHTS.items():
            value = getattr(doc, field, "") or ""
            field_tokens = tokenize(value)
            repeat = max(1, int(round(weight)))
            for token in field_tokens:
                tokens.extend([token] * repeat)
        return tokens

    def search(self, query: str, top_k: int = 10) -> list[SearchResult]:
        query_terms = tokenize(query)
        if not query_terms:
            return []

        exact = self._exact_name_matches(query)
        scored: list[SearchResult] = []
        for doc_index, doc in enumerate(self.docs):
            score = self._score_doc(doc_index, query_terms)
            if doc in exact:
                score += 100.0
            if score > 0:
                matched = sorted(set(query_terms) & set(self.term_freqs[doc_index].keys()))
                scored.append(SearchResult(doc=doc, score=score, matched_terms=matched))

        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]

    def _exact_name_matches(self, query: str) -> list[TeacherDoc]:
        query = query.strip()
        if not query:
            return []
        return [doc for doc in self.docs if doc.name and query == doc.name]

    def _score_doc(self, doc_index: int, query_terms: list[str]) -> float:
        freq = self.term_freqs[doc_index]
        doc_len = len(self.doc_tokens[doc_index])
        if doc_len == 0 or self.avg_doc_len == 0:
            return 0.0

        score = 0.0
        total_docs = len(self.docs)
        for term in query_terms:
            tf = freq.get(term, 0)
            if tf == 0:
                continue
            df = self.doc_freq.get(term, 0)
            idf = math.log(1 + (total_docs - df + 0.5) / (df + 0.5))
            denom = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_len)
            score += idf * tf * (self.k1 + 1) / denom
        return score

