# HTML TO JSONL PARSER


from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from suda_ir.crawler.parser import classify_teacher_page, parse_teacher_page
from suda_ir.data.storage import save_jsonl
from suda_ir.models import TeacherDoc


@dataclass(frozen=True)
class SeedMeta:
    college: str
    name: str
    url: str
    seed_file: str


def raw_filename(url: str) -> str:
    digest = hashlib.sha1(url.encode("utf-8", errors="ignore")).hexdigest()[:16]
    return f"{digest}.html"


def discover_seed_files(handoff_root: str | Path, seed_root: str | Path | None = None) -> list[Path]:
    colleges_dir = Path(seed_root) if seed_root else Path(handoff_root) / "colleges"
    if not colleges_dir.exists():
        return []
    return sorted(colleges_dir.glob("*/teacher_seeds.csv"))


def load_seed_index(handoff_root: str | Path, seed_root: str | Path | None = None) -> dict[str, SeedMeta]:
    index: dict[str, SeedMeta] = {}
    for seed_file in discover_seed_files(handoff_root, seed_root=seed_root):
        with seed_file.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = (row.get("url") or "").strip()
                if not url:
                    continue
                filename = raw_filename(url)
                index[filename] = SeedMeta(
                    college=(row.get("college") or seed_file.parent.name).strip(),
                    name=(row.get("name") or "").strip(),
                    url=url,
                    seed_file=str(seed_file),
                )
    return index


def iter_handoff_html_files(handoff_root: str | Path) -> list[Path]:
    root = Path(handoff_root)
    html_files: list[Path] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir() or child.name == "colleges":
            continue
        html_files.extend(sorted(child.glob("*.html")))
    return html_files


def build_documents(
    handoff_root: str | Path,
    *,
    seed_root: str | Path | None = None,
    include_nonteacher: bool = True,
    dedupe: bool = True,
) -> tuple[list[TeacherDoc], list[dict[str, object]]]:
    handoff_root = Path(handoff_root)
    seed_index = load_seed_index(handoff_root, seed_root=seed_root)
    docs: list[TeacherDoc] = []
    report: list[dict[str, object]] = []
    seen_keys: set[str] = set()

    for html_path in iter_handoff_html_files(handoff_root):
        html = html_path.read_text(encoding="utf-8", errors="ignore")
        seed = seed_index.get(html_path.name)
        canonical_college = html_path.parent.name
        parse_college = seed.college if seed else canonical_college
        doc = parse_teacher_page(html, url=seed.url if seed else "", college=parse_college)
        is_teacher_page, page_reason = classify_teacher_page(doc.content)

        if not include_nonteacher and not is_teacher_page:
            report.append(
                {
                    "path": str(html_path),
                    "status": "skipped_nonteacher",
                    "reason": page_reason,
                }
            )
            continue

        if seed:
            if seed.name:
                if doc.name and doc.name != seed.name:
                    doc.extra["parsed_name"] = doc.name
                doc.name = seed.name
            doc.url = seed.url
            doc.final_url = seed.url
            doc.extra["seed_file"] = seed.seed_file
            if seed.college and seed.college != canonical_college:
                doc.extra["seed_college"] = seed.college
        elif not doc.final_url:
            doc.final_url = doc.url

        if doc.college and doc.college != canonical_college:
            doc.extra["parsed_college"] = doc.college
        doc.college = canonical_college
        doc.extra["raw_path"] = str(html_path)
        doc.extra["is_teacher_page"] = is_teacher_page
        doc.extra["page_reason"] = page_reason
        doc.extra["source"] = "handoff_html"

        dedupe_key = doc.url or doc.name or str(html_path)
        if dedupe and dedupe_key in seen_keys:
            report.append(
                {
                    "path": str(html_path),
                    "status": "skipped_duplicate",
                    "name": doc.name,
                    "url": doc.url,
                }
            )
            continue
        seen_keys.add(dedupe_key)

        docs.append(doc)
        report.append(
            {
                "path": str(html_path),
                "status": "saved",
                "name": doc.name,
                "college": doc.college,
                "title": doc.title,
                "url": doc.url,
                "section_count": len(doc.extra.get("sections", {})),
                "page_reason": page_reason,
            }
        )

    docs.sort(key=lambda item: (item.college, item.name, item.doc_id))
    return docs, report


def summarize_documents(docs: list[TeacherDoc]) -> dict[str, object]:
    by_college = Counter(doc.college or "未知学院" for doc in docs)
    return {
        "doc_count": len(docs),
        "college_count": len(by_college),
        "by_college": dict(sorted(by_college.items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse local teacher HTML directories into a single JSONL file.")
    parser.add_argument("handoff_root", help="Path to raw HTML root, e.g. data/raw.")
    parser.add_argument(
        "--seed-root",
        help="Optional seed directory. Defaults to <handoff_root>/colleges. Use data/seeds/colleges for this repo.",
    )
    parser.add_argument("--output", default="data/processed/handoff/handoff_teachers.jsonl")
    parser.add_argument("--report", help="Path for parse report JSON.")
    parser.add_argument("--skip-nonteacher", action="store_true", help="Skip pages that do not look like teacher pages.")
    parser.add_argument("--keep-duplicates", action="store_true", help="Do not deduplicate by url/name.")
    args = parser.parse_args()

    docs, report = build_documents(
        args.handoff_root,
        seed_root=args.seed_root,
        include_nonteacher=not args.skip_nonteacher,
        dedupe=not args.keep_duplicates,
    )
    save_jsonl(docs, args.output)

    report_path = Path(args.report) if args.report else Path(args.output).with_suffix(".report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                "summary": summarize_documents(docs),
                "items": report,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    summary = summarize_documents(docs)
    print(f"Saved {summary['doc_count']} documents to {args.output}")
    print(f"Covered {summary['college_count']} colleges")
    for college, count in summary["by_college"].items():
        print(f"  - {college}: {count}")
    print(f"Saved parse report to {report_path}")


if __name__ == "__main__":
    main()
