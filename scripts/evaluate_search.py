from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from suda_ir.data.storage import load_jsonl  # noqa: E402
from suda_ir.ir.fielded_index import FieldedBM25Index  # noqa: E402
from suda_ir.ir.fuzzy import fuzzy_name_search  # noqa: E402
from suda_ir.ir.index import BM25Index, SearchResult  # noqa: E402
from suda_ir.ir.query_intent import analyze_query  # noqa: E402
from suda_ir.ir.semantic_gate import should_use_semantic  # noqa: E402
from suda_ir.ir.semantic_index import SemanticDependencyError, SemanticIndex  # noqa: E402
from suda_ir.models import TeacherDoc  # noqa: E402


FIELD_FILTERS = {"college", "research", "papers", "title"}
NAME_CATEGORIES = {"exact_name", "fuzzy_name"}


@dataclass(frozen=True)
class QueryCase:
    query_id: str
    query: str
    relevant: dict[str, int]
    field: str = "all"
    category: str = "uncategorized"


@dataclass
class MetricSums:
    count: int = 0
    precision: float = 0.0
    mrr: float = 0.0
    ndcg: float = 0.0
    latency_ms: float = 0.0

    def add(self, metrics: dict[str, float]) -> None:
        self.count += 1
        self.precision += metrics["precision"]
        self.mrr += metrics["mrr"]
        self.ndcg += metrics["ndcg"]
        self.latency_ms += metrics["latency_ms"]

    def average(self) -> dict[str, float]:
        count = self.count or 1
        return {
            "cases": self.count,
            "precision": self.precision / count,
            "mrr": self.mrr / count,
            "ndcg": self.ndcg / count,
            "avg_latency_ms": self.latency_ms / count,
        }


def load_qrels(path: str | Path) -> dict[str, dict[str, int]]:
    qrels: dict[str, dict[str, int]] = defaultdict(dict)
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            qrels[str(item["query_id"])][str(item["doc_id"])] = int(item.get("relevance", 1))
    return dict(qrels)


def load_queries(path: str | Path, qrels_path: str | Path | None = None) -> list[QueryCase]:
    qrels = load_qrels(qrels_path) if qrels_path else {}
    cases: list[QueryCase] = []
    with Path(path).open("r", encoding="utf-8") as f:
        for index, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            query_id = str(item.get("query_id") or f"Q{index:03d}")
            category = str(item.get("category", "uncategorized"))
            field = str(item.get("field") or infer_field(category))
            if qrels_path:
                relevant = qrels.get(query_id, {})
            else:
                relevant = {str(value): 3 for value in item.get("relevant", [])}
            cases.append(
                QueryCase(
                    query_id=query_id,
                    query=str(item["query"]),
                    field=field,
                    category=category,
                    relevant=relevant,
                )
            )
    return cases


def infer_field(category: str) -> str:
    if category in NAME_CATEGORIES:
        return "name"
    return "all"


class VariantRunner:
    def __init__(
        self,
        docs: list[TeacherDoc],
        *,
        semantic_model: str,
        semantic_cache: str,
        semantic_backend: str,
        semantic_weight: float,
        semantic_local_files_only: bool,
    ) -> None:
        self.docs = docs
        self.baseline_index = BM25Index(docs)
        self.fielded_index = FieldedBM25Index(docs)
        self.semantic_model = semantic_model
        self.semantic_cache = semantic_cache
        self.semantic_backend = semantic_backend
        self.semantic_weight = semantic_weight
        self.semantic_local_files_only = semantic_local_files_only
        self._semantic_index: SemanticIndex | None = None

    def search(self, mode: str, case: QueryCase, top_k: int) -> list[SearchResult]:
        if mode == "baseline":
            return self._baseline(case.query, top_k=top_k, field=case.field)
        if mode == "fielded":
            return self._fielded(case.query, top_k=top_k, field=case.field, use_expansion=False, use_fuzzy=False)
        if mode == "fielded+fuzzy":
            return self._fielded(case.query, top_k=top_k, field=case.field, use_expansion=False, use_fuzzy=True)
        if mode == "fielded+expand":
            return self._fielded(case.query, top_k=top_k, field=case.field, use_expansion=True, use_fuzzy=False)
        if mode == "adaptive":
            return self._adaptive(case.query, top_k=top_k, field=case.field, use_paper_rrf=False)
        if mode == "optimized":
            return self._adaptive(case.query, top_k=top_k, field=case.field, use_paper_rrf=True)
        if mode == "semantic":
            return self._semantic(case.query, top_k=top_k, field=case.field)
        if mode == "hybrid_semantic":
            return self._hybrid_semantic(case.query, top_k=top_k, field=case.field)
        if mode == "conditional_semantic":
            return self._conditional_semantic(case.query, top_k=top_k, field=case.field)
        raise ValueError(f"Unsupported mode: {mode}")

    def _baseline(self, query: str, *, top_k: int, field: str) -> list[SearchResult]:
        if field == "name":
            return exact_name_search(query, self.docs, top_k=top_k)
        if field in FIELD_FILTERS:
            return filter_contains(field, query, self.docs, top_k=top_k)
        return self.baseline_index.search(query, top_k=top_k)

    def _fielded(self, query: str, *, top_k: int, field: str, use_expansion: bool, use_fuzzy: bool) -> list[SearchResult]:
        if field == "name":
            if use_fuzzy:
                return fuzzy_name_search(query, self.docs, top_k=top_k)
            return exact_name_search(query, self.docs, top_k=top_k)
        if field in FIELD_FILTERS:
            return filter_contains(field, query, self.docs, top_k=top_k)
        return self.fielded_index.search(query, top_k=top_k, use_expansion=use_expansion, use_fuzzy=use_fuzzy)

    def _adaptive(self, query: str, *, top_k: int, field: str, use_paper_rrf: bool) -> list[SearchResult]:
        if field == "name":
            return fuzzy_name_search(query, self.docs, top_k=top_k)
        if field in FIELD_FILTERS:
            return filter_contains(field, query, self.docs, top_k=top_k)

        intent = analyze_query(query, field=field)
        allowed_doc_indices = self._college_doc_indices(intent.college) if intent.college else None
        if allowed_doc_indices is not None and not allowed_doc_indices:
            return []

        candidate_k = max(top_k, 20) if use_paper_rrf and intent.kind == "paper" else top_k
        adaptive_results = self.fielded_index.search(
            intent.cleaned_query,
            top_k=candidate_k,
            use_expansion=intent.use_expansion,
            use_fuzzy=intent.use_fuzzy,
            field_weights=intent.field_weights,
            expansion_weight=intent.expansion_weight,
            allowed_doc_indices=allowed_doc_indices,
        )
        if use_paper_rrf and intent.kind == "paper":
            baseline_results = self.baseline_index.search(intent.original_query, top_k=candidate_k)
            return rrf_merge([adaptive_results, baseline_results], top_k=top_k)
        return adaptive_results[:top_k]

    def _college_doc_indices(self, college: str) -> set[int]:
        return {
            index
            for index, doc in enumerate(self.docs)
            if college and college in (doc.college or "")
        }

    def _semantic(self, query: str, *, top_k: int, field: str) -> list[SearchResult]:
        if field == "name":
            return fuzzy_name_search(query, self.docs, top_k=top_k)
        if field in FIELD_FILTERS:
            return filter_contains(field, query, self.docs, top_k=top_k)

        intent = analyze_query(query, field=field)
        allowed_doc_indices = self._college_doc_indices(intent.college) if intent.college else None
        if allowed_doc_indices is not None and not allowed_doc_indices:
            return []
        semantic_query = intent.cleaned_query or intent.original_query
        return self._get_semantic_index().search(semantic_query, top_k=top_k, allowed_doc_indices=allowed_doc_indices)

    def _hybrid_semantic(self, query: str, *, top_k: int, field: str) -> list[SearchResult]:
        if field == "name":
            return self._adaptive(query, top_k=top_k, field=field, use_paper_rrf=True)

        candidate_k = max(top_k, 50)
        optimized_results = self._adaptive(query, top_k=candidate_k, field=field, use_paper_rrf=True)
        semantic_results = self._semantic(query, top_k=candidate_k, field=field)
        return rrf_merge(
            [optimized_results, semantic_results],
            top_k=top_k,
            weights=[1.0, self.semantic_weight],
        )

    def _conditional_semantic(self, query: str, *, top_k: int, field: str) -> list[SearchResult]:
        candidate_k = max(top_k, 50)
        optimized_results = self._adaptive(query, top_k=candidate_k, field=field, use_paper_rrf=True)
        intent = analyze_query(query, field=field)
        if not should_use_semantic(query, intent, field=field, optimized_results=optimized_results):
            return optimized_results[:top_k]

        semantic_results = self._semantic(query, top_k=candidate_k, field=field)
        return rrf_merge(
            [optimized_results, semantic_results],
            top_k=top_k,
            weights=[1.0, self.semantic_weight],
        )

    def _get_semantic_index(self) -> SemanticIndex:
        if self._semantic_index is None:
            self._semantic_index = SemanticIndex(
                self.docs,
                model_name=self.semantic_model,
                cache_path=self.semantic_cache,
                backend=self.semantic_backend,
                local_files_only=self.semantic_local_files_only,
            )
        return self._semantic_index


def exact_name_search(query: str, docs: list[TeacherDoc], *, top_k: int) -> list[SearchResult]:
    query = query.strip()
    results: list[SearchResult] = []
    for doc in docs:
        if doc.name == query:
            results.append(SearchResult(doc=doc, score=100.0, matched_terms=[query]))
        elif query and query in doc.name:
            results.append(SearchResult(doc=doc, score=50.0, matched_terms=[query]))
    return results[:top_k]


def filter_contains(field: str, query: str, docs: list[TeacherDoc], *, top_k: int) -> list[SearchResult]:
    query = query.strip()
    results: list[SearchResult] = []
    for doc in docs:
        value = getattr(doc, field, "") or ""
        if query and query in value:
            results.append(SearchResult(doc=doc, score=1.0, matched_terms=[query]))
    return results[:top_k]


def rrf_merge(
    ranked_lists: list[list[SearchResult]],
    *,
    top_k: int,
    c: int = 60,
    weights: list[float] | None = None,
) -> list[SearchResult]:
    scores: dict[str, float] = {}
    docs_by_id: dict[str, TeacherDoc] = {}
    matched_terms: dict[str, set[str]] = {}
    active_weights = weights or [1.0] * len(ranked_lists)
    for ranked, weight in zip(ranked_lists, active_weights):
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


def evaluate(
    mode: str,
    runner: VariantRunner,
    cases: list[QueryCase],
    top_k: int,
    rel_threshold: int,
) -> dict[str, object]:
    overall = MetricSums()
    by_category: dict[str, MetricSums] = defaultdict(MetricSums)

    for case in cases:
        started = time.perf_counter()
        results = runner.search(mode, case, top_k)
        latency_ms = (time.perf_counter() - started) * 1000

        result_ids = [result.doc.doc_id for result in results]
        metrics = score_case(result_ids, case.relevant, top_k=top_k, rel_threshold=rel_threshold)
        metrics["latency_ms"] = latency_ms
        overall.add(metrics)
        by_category[case.category].add(metrics)

    return {
        "overall": overall.average(),
        "by_category": {category: sums.average() for category, sums in sorted(by_category.items())},
    }


def score_case(result_ids: list[str], relevant: dict[str, int], *, top_k: int, rel_threshold: int) -> dict[str, float]:
    graded_hits = [relevant.get(doc_id, 0) for doc_id in result_ids[:top_k]]
    binary_hits = [grade >= rel_threshold for grade in graded_hits]
    precision = sum(binary_hits) / top_k

    reciprocal_rank = 0.0
    for rank, grade in enumerate(graded_hits, start=1):
        if grade >= rel_threshold:
            reciprocal_rank = 1.0 / rank
            break

    dcg = discounted_gain(graded_hits)
    ideal_grades = sorted((grade for grade in relevant.values() if grade >= rel_threshold), reverse=True)[:top_k]
    ideal_dcg = discounted_gain(ideal_grades)
    ndcg = dcg / ideal_dcg if ideal_dcg else 0.0

    return {"precision": precision, "mrr": reciprocal_rank, "ndcg": ndcg, "latency_ms": 0.0}


def discounted_gain(grades: list[int]) -> float:
    return sum((2**grade - 1) / math.log2(rank + 1) for rank, grade in enumerate(grades, start=1))


def parse_modes(value: str, ablation: bool) -> list[str]:
    if value:
        return [item.strip() for item in value.split(",") if item.strip()]
    if ablation:
        return ["baseline", "fielded", "fielded+fuzzy", "fielded+expand", "adaptive", "optimized"]
    return ["baseline", "optimized"]


def print_report(mode: str, report: dict[str, object], top_k: int, show_breakdown: bool) -> None:
    overall = report["overall"]
    assert isinstance(overall, dict)
    print(
        f"{mode:15s} "
        f"P@{top_k}={overall['precision']:.4f} "
        f"MRR={overall['mrr']:.4f} "
        f"NDCG@{top_k}={overall['ndcg']:.4f} "
        f"avg_ms={overall['avg_latency_ms']:.2f}"
    )
    if not show_breakdown:
        return
    by_category = report["by_category"]
    assert isinstance(by_category, dict)
    for category, metrics in by_category.items():
        print(
            f"  {category:18s} "
            f"n={metrics['cases']:2.0f} "
            f"P@{top_k}={metrics['precision']:.4f} "
            f"MRR={metrics['mrr']:.4f} "
            f"NDCG@{top_k}={metrics['ndcg']:.4f}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate tutor search with optional qrels and ablation variants.")
    parser.add_argument("--data", default="data/sample/teachers.jsonl")
    parser.add_argument("--queries", default="data/sample/eval_queries.jsonl")
    parser.add_argument("--qrels", default="")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--rel-threshold", type=int, default=2)
    parser.add_argument("--ablation", action="store_true")
    parser.add_argument("--modes", default="", help="Comma-separated modes, e.g. baseline,optimized")
    parser.add_argument("--no-breakdown", action="store_true")
    parser.add_argument("--output", default="", help="Optional JSON output path for metrics.")
    parser.add_argument("--semantic-model", default="BAAI/bge-small-zh-v1.5")
    parser.add_argument("--semantic-cache", default="data/processed/eval/semantic_embeddings.npz")
    parser.add_argument("--semantic-backend", choices=["sentence-transformers", "hashing"], default="sentence-transformers")
    parser.add_argument("--semantic-weight", type=float, default=0.05)
    parser.add_argument("--semantic-local-files-only", action="store_true")
    args = parser.parse_args()

    cases = load_queries(args.queries, qrels_path=args.qrels or None)
    if not cases:
        raise SystemExit("No query cases found.")

    docs = load_jsonl(args.data)
    runner = VariantRunner(
        docs,
        semantic_model=args.semantic_model,
        semantic_cache=args.semantic_cache,
        semantic_backend=args.semantic_backend,
        semantic_weight=args.semantic_weight,
        semantic_local_files_only=args.semantic_local_files_only,
    )
    modes = parse_modes(args.modes, args.ablation)
    reports: dict[str, object] = {}

    print(f"data={args.data}")
    print(f"queries={args.queries}")
    if args.qrels:
        print(f"qrels={args.qrels}")
    print(f"docs={len(docs)} cases={len(cases)} top_k={args.top_k} rel_threshold={args.rel_threshold}")
    print()

    for mode in modes:
        try:
            report = evaluate(mode, runner, cases, args.top_k, args.rel_threshold)
        except SemanticDependencyError as exc:
            print(f"{mode:15s} skipped: {exc}")
            print()
            continue
        reports[mode] = report
        print_report(mode, report, args.top_k, show_breakdown=not args.no_breakdown)
        print()

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "data": args.data,
            "queries": args.queries,
            "qrels": args.qrels or None,
            "top_k": args.top_k,
            "rel_threshold": args.rel_threshold,
            "reports": reports,
        }
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved metrics to {output_path}")


if __name__ == "__main__":
    main()
