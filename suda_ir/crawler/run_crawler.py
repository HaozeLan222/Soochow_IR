from __future__ import annotations

import argparse
from pathlib import Path

from suda_ir.crawler.fetcher import crawl_static_pages
from suda_ir.crawler.parser import parse_teacher_page
from suda_ir.data.storage import save_jsonl


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl Soochow tutor pages.")
    parser.add_argument("--seed", action="append", required=True, help="Seed URL. Can be used multiple times.")
    parser.add_argument("--college", default="", help="College name for crawled pages.")
    parser.add_argument("--max-pages", type=int, default=50)
    parser.add_argument("--output", default="data/processed/teachers.jsonl")
    args = parser.parse_args()

    pages = crawl_static_pages(args.seed, max_pages=args.max_pages)
    docs = []
    raw_dir = Path("data/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)

    for index, page in enumerate(pages, start=1):
        raw_path = raw_dir / f"page_{index:04d}.html"
        raw_path.write_text(page.html, encoding="utf-8")
        doc = parse_teacher_page(page.html, url=page.url, college=args.college)
        doc.final_url = page.final_url
        doc.extra["raw_path"] = str(raw_path)
        doc.extra["status_code"] = page.status_code
        docs.append(doc)

    save_jsonl(docs, args.output)
    print(f"Saved {len(docs)} documents to {args.output}")


if __name__ == "__main__":
    main()

