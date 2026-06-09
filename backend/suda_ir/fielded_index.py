from __future__ import annotations

import math
from collections import Counter, defaultdict

from domain.search import SearchResult
from domain.teacher import TeacherDoc
from suda_ir.fuzzy import fuzzy_name_bonus
from suda_ir.index import FIELD_WEIGHTS
from suda_ir.query_expansion import expand_query, weighted_query_terms
from suda_ir.tokenizer import tokenize


class FieldedBM25Index:
    def __init__(self, docs: list[TeacherDoc], k1: float = 1.5, b: float = 0.75) -> None:
        self.docs = docs
        self.k1 = k1
        self.b = b
        self.field_freqs: dict[str, list[Counter[str]]] = {field: [] for field in FIELD_WEIGHTS}
        self.field_lengths: dict[str, list[int]] = {field: [] for field in FIELD_WEIGHTS}
        self.field_doc_freqs: dict[str, dict[str, int]] = {field: defaultdict(int) for field in FIELD_WEIGHTS}
        self.field_avg_lens: dict[str, float] = {field: 0.0 for field in FIELD_WEIGHTS}
        self._build()

    def _build(self) -> None:
        for field in FIELD_WEIGHTS:
            total_len = 0
            for doc in self.docs:
                value = getattr(doc, field, "") or ""
                tokens = tokenize(value)
                freq = Counter(tokens)
                self.field_freqs[field].append(freq)
                self.field_lengths[field].append(len(tokens))
                total_len += len(tokens)
                for term in freq:
                    self.field_doc_freqs[field][term] += 1
            self.field_avg_lens[field] = total_len / len(self.docs) if self.docs else 0.0

    def search(self, query: str, top_k: int = 10, *, use_expansion: bool = True, use_fuzzy: bool = True) -> list[SearchResult]:
        terms = weighted_query_terms(query) if use_expansion else {term: 1.0 for term in tokenize(query)}
        if not terms:
            return []

        expanded_phrases = expand_query(query) if use_expansion else [query.strip()]
        scored: list[SearchResult] = []
        for doc_index, doc in enumerate(self.docs):
            score = 0.0
            for field, field_weight in FIELD_WEIGHTS.items():
                score += field_weight * self._score_field(doc_index, field, terms)
                score += field_weight * self._phrase_bonus(doc, field, expanded_phrases)

            if use_fuzzy:
                score += fuzzy_name_bonus(query, doc)
            if doc.name and query.strip() == doc.name:
                score += 100.0

            if score > 0:
                scored.append(SearchResult(doc=doc, score=score, matched_terms=self._matched_terms(doc_index, terms)))

        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]

    def _score_field(self, doc_index: int, field: str, terms: dict[str, float]) -> float:
        freq = self.field_freqs[field][doc_index]
        doc_len = self.field_lengths[field][doc_index]
        avg_len = self.field_avg_lens[field]
        if doc_len == 0 or avg_len == 0:
            return 0.0

        score = 0.0
        total_docs = len(self.docs)
        doc_freq = self.field_doc_freqs[field]
        for term, query_weight in terms.items():
            tf = freq.get(term, 0)
            if tf == 0:
                continue
            df = doc_freq.get(term, 0)
            idf = math.log(1 + (total_docs - df + 0.5) / (df + 0.5))
            denom = tf + self.k1 * (1 - self.b + self.b * doc_len / avg_len)
            score += query_weight * idf * tf * (self.k1 + 1) / denom
        return score

    def _phrase_bonus(self, doc: TeacherDoc, field: str, expanded_phrases: list[str]) -> float:
        value = getattr(doc, field, "") or ""
        if not value:
            return 0.0

        bonus = 0.0
        for index, phrase in enumerate(expanded_phrases):
            phrase = phrase.strip()
            if len(phrase) >= 2 and phrase in value:
                bonus += 2.0 if index == 0 else 0.8
        return bonus

    def _matched_terms(self, doc_index: int, terms: dict[str, float]) -> list[str]:
        matched: set[str] = set()
        for field in FIELD_WEIGHTS:
            matched.update(set(terms) & set(self.field_freqs[field][doc_index]))
        return sorted(matched)

