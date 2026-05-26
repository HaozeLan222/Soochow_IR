from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from suda_ir.crawler.fetcher import crawl_static_pages
from suda_ir.crawler.parser import classify_teacher_page, html_to_text, parse_teacher_page
from suda_ir.data.storage import save_jsonl


def read_seed_file(path: str | Path) -> list[dict[str, str]]:
    seeds: list[dict[str, str]] = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = (row.get("url") or "").strip()
            if url:
                seeds.append(
                    {
                        "url": url,
                        "college": (row.get("college") or "").strip(),
                        "name": (row.get("name") or "").strip(),
                    }
                )
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
    parser.add_argument("--follow-links", action="store_true", help="Follow discovered links from seed pages.")
    parser.add_argument("--report", help="Path for crawl report JSON. Defaults to output path with .report.json.")
    parser.add_argument("--raw-dir", default="data/raw", help="Directory for saved raw HTML pages.")
    args = parser.parse_args()

    seed_items = [{"url": seed, "college": args.college, "name": ""} for seed in args.seed]
    if args.seed_file:
        seed_items.extend(read_seed_file(args.seed_file))
    if not seed_items:
        parser.error("Provide --seed or --seed-file.")

    seed_meta = {item["url"]: item for item in seed_items}
    pages = crawl_static_pages(
        [item["url"] for item in seed_items],
        max_pages=args.max_pages,
        pause_range=(0, 0) if args.no_delay else (1.0, 3.0),
        allowed_domains={"web.suda.edu.cn"},
        follow_links=args.follow_links,
    )
    docs = []
    raw_dir = Path(args.raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    seen_docs: set[str] = set()
    report: list[dict[str, str | int]] = []

    for page in pages:
        raw_path = raw_dir / raw_filename(page.final_url)
        raw_path.write_text(page.html, encoding="utf-8")
        if page.error or not page.html:
            report.append(
                {
                    "url": page.url,
                    "final_url": page.final_url,
                    "status": "fetch_error",
                    "status_code": page.status_code,
                    "error": page.error,
                }
            )
            continue
        text = html_to_text(page.html)
        is_teacher_page, page_reason = classify_teacher_page(text)
        if not args.include_nonteacher and not is_teacher_page:
            report.append(
                {
                    "url": page.url,
                    "final_url": page.final_url,
                    "status": "skipped_nonteacher",
                    "status_code": page.status_code,
                    "reason": page_reason,
                    "text_head": text[:120],
                }
            )
            continue
        meta = seed_meta.get(page.url, {})
        doc = parse_teacher_page(page.html, url=page.url, college=meta.get("college", args.college))
        if meta.get("name") and doc.name != meta["name"]:
            doc.extra["parsed_name"] = doc.name
            doc.name = meta["name"]
        doc.final_url = page.final_url
        doc.extra["raw_path"] = str(raw_path)
        doc.extra["status_code"] = page.status_code
        doc.extra["client_redirect_url"] = page.redirect_url
        doc.extra["error"] = page.error
        dedupe_key = doc.name or doc.final_url or doc.doc_id
        if dedupe_key in seen_docs:
            report.append(
                {
                    "url": page.url,
                    "final_url": page.final_url,
                    "status": "skipped_duplicate",
                    "status_code": page.status_code,
                    "name": doc.name,
                }
            )
            continue
        seen_docs.add(dedupe_key)
        docs.append(doc)
        report.append(
            {
                "url": page.url,
                "final_url": page.final_url,
                "status": "saved",
                "status_code": page.status_code,
                "name": doc.name,
                "title": doc.title,
                "section_count": len(doc.extra.get("sections", {})),
                "page_reason": page_reason,
            }
        )

    save_jsonl(docs, args.output)
    report_path = Path(args.report) if args.report else Path(args.output).with_suffix(".report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(docs)} documents to {args.output}")
    print(f"Saved crawl report to {report_path}")


if __name__ == "__main__":
    main()
