from __future__ import annotations

import argparse

from suda_ir.data.storage import load_jsonl
from suda_ir.ir.searcher import TutorSearcher


def main() -> None:
    parser = argparse.ArgumentParser(description="Search Soochow tutor documents.")
    parser.add_argument("--data", default="data/sample/teachers.jsonl")
    parser.add_argument("--query", required=True)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--field", choices=["all", "name", "college", "research", "papers", "title"], default="all")
    parser.add_argument("--mode", choices=["baseline", "optimized"], default="baseline")
    args = parser.parse_args()

    docs = load_jsonl(args.data)
    searcher = TutorSearcher(docs, mode=args.mode)
    results = searcher.search(args.query, top_k=args.top_k, field=args.field)

    if not results:
        print("No results.")
        return

    for rank, result in enumerate(results, start=1):
        doc = result.doc
        print(f"[{rank}] {doc.name or '未知姓名'} | {doc.college} | score={result.score:.4f}")
        if doc.title:
            print(f"    职称: {doc.title}")
        if doc.research:
            print(f"    研究方向: {doc.research}")
        if doc.url:
            print(f"    URL: {doc.url}")
        print()


if __name__ == "__main__":
    main()

