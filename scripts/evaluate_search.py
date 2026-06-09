from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from suda_ir.data.storage import load_jsonl  # noqa: E402
from suda_ir.ir.searcher import TutorSearcher  # noqa: E402


@dataclass
class QueryCase:
    query: str
    relevant: set[str]
    field: str = "all"


def load_queries(path: str | Path) -> list[QueryCase]:
    cases: list[QueryCase] = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            relevant = {str(value) for value in item.get("relevant", [])}
            cases.append(QueryCase(query=str(item["query"]), field=str(item.get("field", "all")), relevant=relevant))
    return cases


def evaluate(mode: str, data_path: str, cases: list[QueryCase], top_k: int) -> dict[str, float]:
    docs = load_jsonl(data_path)
    searcher = TutorSearcher(docs, mode=mode)
    precision_sum = 0.0
    reciprocal_rank_sum = 0.0
    elapsed_sum = 0.0

    for case in cases:
        started = time.perf_counter()
        results = searcher.search(case.query, top_k=top_k, field=case.field)
        elapsed_sum += time.perf_counter() - started

        result_ids = [result.doc.doc_id for result in results]
        hits = [doc_id for doc_id in result_ids if doc_id in case.relevant]
        precision_sum += len(hits) / top_k

        reciprocal_rank = 0.0
        for rank, doc_id in enumerate(result_ids, start=1):
            if doc_id in case.relevant:
                reciprocal_rank = 1.0 / rank
                break
        reciprocal_rank_sum += reciprocal_rank

    count = len(cases) or 1
    return {
        f"precision@{top_k}": precision_sum / count,
        "mrr": reciprocal_rank_sum / count,
        "avg_latency_ms": elapsed_sum / count * 1000,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate baseline and optimized tutor search.")
    parser.add_argument("--data", default="data/sample/teachers.jsonl")
    parser.add_argument("--queries", default="data/sample/eval_queries.jsonl")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    cases = load_queries(args.queries)
    if not cases:
        raise SystemExit("No query cases found.")

    print(f"data={args.data}")
    print(f"queries={args.queries}")
    print(f"cases={len(cases)} top_k={args.top_k}")
    print()
    for mode in ["baseline", "optimized"]:
        metrics = evaluate(mode, args.data, cases, args.top_k)
        print(
            f"{mode:9s} "
            f"P@{args.top_k}={metrics[f'precision@{args.top_k}']:.4f} "
            f"MRR={metrics['mrr']:.4f} "
            f"avg_ms={metrics['avg_latency_ms']:.2f}"
        )


if __name__ == "__main__":
    main()

