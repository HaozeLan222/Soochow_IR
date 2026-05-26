from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path

from suda_ir.crawler.fetcher import crawl_static_pages
from suda_ir.crawler.parser import html_to_text, is_probable_teacher_page, parse_teacher_page
from suda_ir.data.storage import save_jsonl


def read_seed_file(path: str | Path) -> list[tuple[str, str]]:
    seeds: list[tuple[str, str]] = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = (row.get("url") or "").strip()
            if url:
                seeds.append((url, (row.get("college") or "").strip()))
    return seeds


def raw_filename(url: str) -> str:
    digest = hashlib.sha1(url.encode("utf-8", errors="ignore")).hexdigest()[:16]
    return f"{digest}.html"


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl Soochow tutor pages.")
    parser.add_argument("--seed", action="append", default=[], help="Seed URL. Can be used multiple times.")
    parser.add_argument("--seed-file", help="CSV file with columns: college,url.")
    parser.add_argument("--college", default="", help="College name for crawled pages.")
    parser.add_argument("--max-pages", type=int, default=50)
    parser.add_argument("--output", default="data/processed/teachers.jsonl")
    parser.add_argument("--include-nonteacher", action="store_true", help="Keep pages that do not look like teacher pages.")
    parser.add_argument("--no-delay", action="store_true", help="Disable crawl delay for local tests.")
    args = parser.parse_args()

    seed_pairs = [(seed, args.college) for seed in args.seed]
    if args.seed_file:
        seed_pairs.extend(read_seed_file(args.seed_file))
    if not seed_pairs:
        parser.error("Provide --seed or --seed-file.")

    seed_college = {url: college for url, college in seed_pairs}
    pages = crawl_static_pages(
        [url for url, _college in seed_pairs],
        max_pages=args.max_pages,
        pause_range=(0, 0) if args.no_delay else (1.0, 3.0),
        allowed_domains={"web.suda.edu.cn"},
    )
    docs = []
    raw_dir = Path("data/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    seen_docs: set[str] = set()

    for page in pages:
        raw_path = raw_dir / raw_filename(page.final_url)
        raw_path.write_text(page.html, encoding="utf-8")
        if page.error or not page.html:
            continue
        text = html_to_text(page.html)
        if not args.include_nonteacher and not is_probable_teacher_page(text):
            continue
        doc = parse_teacher_page(page.html, url=page.url, college=seed_college.get(page.url, args.college))
        doc.final_url = page.final_url
        doc.extra["raw_path"] = str(raw_path)
        doc.extra["status_code"] = page.status_code
        doc.extra["client_redirect_url"] = page.redirect_url
        doc.extra["error"] = page.error
        dedupe_key = doc.name or doc.final_url or doc.doc_id
        if dedupe_key in seen_docs:
            continue
        seen_docs.add(dedupe_key)
        docs.append(doc)

    save_jsonl(docs, args.output)
    print(f"Saved {len(docs)} documents to {args.output}")


if __name__ == "__main__":
    main()
