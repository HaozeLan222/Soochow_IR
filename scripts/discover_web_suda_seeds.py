from __future__ import annotations

import argparse
import csv
import html
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup


DEFAULT_LIST_URL = (
    "https://web.suda.edu.cn/ssjglm/list.htm?"
    "wp_tw_orgId=15&wp_tw_displayStyle=1&wp_tw_complete=1"
    f"&wp_tw_orgName={quote(quote('计算机科学与技术学院（软件学院）', safe=''), safe='')}"
    "&wp_tw_language=1&wp_tw_teachStatus=1&wp_tw_deptTecOrder=1"
)
DEFAULT_COLLEGE = "计算机科学与技术学院（软件学院）"
DEFAULT_AJAX_PAGE_CAP = 6
WEB_SUDA_RE = re.compile(r"(?:(?:https?:)?//)?web\.suda\.edu\.cn/[A-Za-z0-9_\-./%]+")


@dataclass(frozen=True)
class Seed:
    college: str
    name: str
    url: str


def build_list_url(org_id: str, college: str) -> str:
    encoded_college = quote(quote(college, safe=""), safe="")
    return (
        "https://web.suda.edu.cn/ssjglm/list.htm?"
        f"wp_tw_orgId={org_id}&wp_tw_displayStyle=1&wp_tw_complete=1"
        f"&wp_tw_orgName={encoded_college}"
        "&wp_tw_language=1&wp_tw_teachStatus=1&wp_tw_deptTecOrder=1"
    )


def normalize_teacher_url(raw_url: str, base_url: str = "") -> str:
    raw_url = raw_url.strip().strip("\"'，,。；;)")
    if raw_url.startswith("//"):
        raw_url = "https:" + raw_url
    elif raw_url.startswith("web.suda.edu.cn/"):
        raw_url = "https://" + raw_url
    elif base_url:
        raw_url = urljoin(base_url, raw_url)

    parsed = urlparse(raw_url)
    if parsed.netloc.lower() == "web.suda.edu.cn" and parsed.scheme == "http":
        parsed = parsed._replace(scheme="https")
    if parsed.netloc.lower() == "web.suda.edu.cn":
        path = parsed.path or "/"
        if "." not in path.rsplit("/", 1)[-1] and not path.endswith("/"):
            parsed = parsed._replace(path=path + "/")
    return urlunparse(parsed)


def clean_name(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"\s+(?:计算机科学与技术学院|访问).*$", "", value).strip()
    return value


def repeated_unquote(value: str, max_rounds: int = 3) -> str:
    for _ in range(max_rounds):
        decoded = unquote(value)
        if decoded == value:
            break
        value = decoded
    return value


def fetch_text(session: requests.Session, url: str, timeout: int) -> str:
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    if not response.encoding or response.encoding.lower() == "iso-8859-1":
        response.encoding = response.apparent_encoding
    return response.text


def describe_page(page_html: str) -> str:
    soup = BeautifulSoup(page_html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    return (
        f"title={title!r}, "
        f"bytes={len(page_html.encode('utf-8', errors='ignore'))}, "
        f"news_box={len(soup.select('a.news_box[href]'))}, "
        f"search_data={1 if soup.select_one('#search_data') else 0}, "
        f"paging={1 if soup.select_one('.wp_paging') else 0}, "
        f"contains_generalQuery={'generalQuery' in page_html}, "
        f"contains_login={'登录' in page_html or 'login' in page_html.lower()}"
    )


def parse_static_cards(page_html: str, list_url: str, college: str) -> list[Seed]:
    soup = BeautifulSoup(page_html, "html.parser")
    seeds: list[Seed] = []
    seen: set[str] = set()

    for link in soup.select("a.news_box[href]"):
        href = link.get("href", "").strip()
        if "web.suda.edu.cn" not in href:
            continue
        card_text = link.get_text(" ", strip=True)
        if college and college not in card_text:
            continue
        title = link.select_one(".news_title")
        name = clean_name(title.get_text(" ", strip=True) if title else card_text)
        url = normalize_teacher_url(href, base_url=list_url)
        if name and url and url not in seen:
            seen.add(url)
            seeds.append(Seed(college=college, name=name, url=url))

    if seeds:
        return seeds

    # Fallback for markdown/text copies of the page.
    pattern = re.compile(r"\]\((?P<url>https?://web\.suda\.edu\.cn/[^)\s]+)\)")
    for match in pattern.finditer(page_html):
        url = normalize_teacher_url(match.group("url"), base_url=list_url)
        head = page_html[max(0, match.start() - 160) : match.start()]
        name_match = re.search(r"([\u4e00-\u9fffA-Za-z（）()·]{2,30})\s+计算机科学与技术学院", head)
        name = clean_name(name_match.group(1)) if name_match else ""
        if name and url and url not in seen:
            seen.add(url)
            seeds.append(Seed(college=college, name=name, url=url))
    return seeds


def parse_search_config(page_html: str, list_url: str) -> dict[str, str]:
    config: dict[str, str] = {}
    soup = BeautifulSoup(page_html, "html.parser")
    node = soup.select_one("#search_data")
    if node and node.get("value"):
        raw_value = html.unescape(node["value"])
        try:
            loaded = json.loads(raw_value)
            config.update({str(key): str(value) for key, value in loaded.items() if value is not None})
        except json.JSONDecodeError:
            pass

    query = parse_qs(urlparse(list_url).query)
    for key, values in query.items():
        if key.startswith("wp_tw_") and values:
            config.setdefault(key.removeprefix("wp_tw_"), repeated_unquote(values[0]))

    config.setdefault("language", "1")
    config.setdefault("level", "0")
    config.setdefault("orgId", "15")
    config.setdefault("displayStyle", "1")
    config.setdefault("complete", "1")
    config.setdefault("queryUrl", "/_wp3services/generalQuery?queryObj=teacherHome")
    return config


def parse_page_count(page_html: str, rows_per_page: int) -> int:
    soup = BeautifulSoup(page_html, "html.parser")
    all_pages = soup.select_one(".all_pages")
    if all_pages:
        try:
            return max(1, int(all_pages.get_text(strip=True)))
        except ValueError:
            pass
    all_count = soup.select_one(".all_count em")
    if all_count:
        try:
            count = int(all_count.get_text(strip=True))
            return max(1, (count + rows_per_page - 1) // rows_per_page)
        except ValueError:
            pass
    return 1


def build_query_payload(config: dict[str, str], page_index: int, rows: int) -> dict[str, Any]:
    org_id = config.get("orgId", "")
    keyword = config.get("keyword", "")
    conditions = [
        {"field": "language", "value": config.get("language", "1"), "judge": "="},
        {"field": "ownDepartment", "value": org_id, "judge": "="},
        {"field": "title", "value": keyword, "judge": "like"},
        {"field": "published", "value": "1", "judge": "="},
    ]
    orders = []
    if config.get("deptTecOrder", "") != "":
        orders.append({"field": "deptTecOrder", "type": "asc"})

    return_infos = [
        {"field": field, "name": field}
        for field in [
            "title",
            "career",
            "visitCount",
            "headerPic",
            "cnUrl",
            "department",
            "publishStatus",
        ]
    ]

    return {
        "siteId": org_id or config.get("siteId", ""),
        "pageIndex": page_index,
        "rows": rows,
        "conditions": conditions,
        "orders": orders,
        "returnInfos": return_infos,
        "articleType": 1,
        "level": int(config.get("level", "0") or 0),
        "deptTecOrder": config.get("deptTecOrder", "1_1"),
        "pageEvent": "dataSearchByPageIndex",
    }


def build_unfiltered_payload(config: dict[str, str], page_index: int, rows: int) -> dict[str, Any]:
    payload = build_query_payload(config, page_index=page_index, rows=rows)
    payload["rows"] = rows
    return payload


def collect_from_any_response(text: str, college: str, site_id: str = "") -> list[Seed]:
    seeds: list[Seed] = []
    seen: set[str] = set()

    def add(name: str, raw_url: str, record_text: str = "", record_site_id: str = "") -> None:
        if site_id and record_site_id and record_site_id != site_id:
            return
        if college and record_text and college not in record_text and not (site_id and record_site_id == site_id):
            return
        url = normalize_teacher_url(raw_url)
        if not url or "web.suda.edu.cn" not in url or url in seen:
            return
        seen.add(url)
        seeds.append(Seed(college=college, name=clean_name(name), url=url))

    def walk(node: Any, context_name: str = "") -> None:
        if isinstance(node, dict):
            record_text = json.dumps(node, ensure_ascii=False)
            record_site_id = str(node.get("siteId", ""))
            name = context_name
            for key in ("name", "title", "teacherName", "cnName"):
                if node.get(key):
                    name = str(node[key])
                    break
            for key, value in node.items():
                if isinstance(value, str):
                    for raw_url in WEB_SUDA_RE.findall(value):
                        add(name, raw_url, record_text=record_text, record_site_id=record_site_id)
                else:
                    walk(value, name)
        elif isinstance(node, list):
            for item in node:
                walk(item, context_name)
        elif isinstance(node, str):
            for raw_url in WEB_SUDA_RE.findall(node):
                add(context_name, raw_url, record_text=node)

    try:
        walk(json.loads(text))
    except json.JSONDecodeError:
        pass

    if seeds:
        return seeds

    if not site_id:
        seeds.extend(parse_static_cards(text, "https://web.suda.edu.cn/", college))
    return seeds


def response_preview(text: str, max_chars: int = 240) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    return compact[:max_chars]


def infer_total_pages_from_response(text: str, rows_per_page: int) -> int:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = None

    def find_count(node: Any) -> int:
        if isinstance(node, dict):
            for key in ("total", "totalCount", "allCount", "recordCount", "count"):
                value = node.get(key)
                if isinstance(value, int):
                    return value
                if isinstance(value, str) and value.isdigit():
                    return int(value)
            for value in node.values():
                found = find_count(value)
                if found:
                    return found
        elif isinstance(node, list):
            for value in node:
                found = find_count(value)
                if found:
                    return found
        return 0

    count = find_count(data)
    if count:
        return max(1, (count + rows_per_page - 1) // rows_per_page)

    soup = BeautifulSoup(text, "html.parser")
    all_pages = soup.select_one(".all_pages")
    if all_pages:
        try:
            return max(1, int(all_pages.get_text(strip=True)))
        except ValueError:
            pass
    all_count = soup.select_one(".all_count em")
    if all_count:
        try:
            count = int(all_count.get_text(strip=True))
            return max(1, (count + rows_per_page - 1) // rows_per_page)
        except ValueError:
            pass
    return 1


def fetch_ajax_page(
    session: requests.Session,
    list_url: str,
    config: dict[str, str],
    page_index: int,
    rows: int,
    timeout: int,
    college: str,
    debug_ajax_dir: Path | None = None,
) -> tuple[list[Seed], int, str]:
    query_url = urljoin(list_url, html.unescape(config.get("queryUrl", "")))
    payload = build_query_payload(config, page_index=page_index, rows=rows)
    headers = {
        "User-Agent": session.headers.get("User-Agent", "Mozilla/5.0"),
        "Referer": list_url,
        "X-Requested-With": "XMLHttpRequest",
    }

    attempts = [
        ("json", {"json": payload}),
        (
            "form",
            {
                "data": {
                    **{k: v for k, v in payload.items() if k not in {"conditions", "orders", "returnInfos"}},
                    "conditions": json.dumps(payload["conditions"], ensure_ascii=False),
                    "orders": json.dumps(payload["orders"], ensure_ascii=False),
                    "returnInfos": json.dumps(payload["returnInfos"], ensure_ascii=False),
                }
            },
        ),
    ]
    errors: list[str] = []
    for mode, kwargs in attempts:
        try:
            response = session.post(query_url, timeout=timeout, headers=headers, **kwargs)
            if debug_ajax_dir:
                debug_ajax_dir.mkdir(parents=True, exist_ok=True)
                suffix = "json" if "application/json" in response.headers.get("content-type", "") else "txt"
                debug_path = debug_ajax_dir / f"ajax_page{page_index}_{mode}.{suffix}"
                debug_path.write_text(response.text, encoding="utf-8", errors="ignore")
            response.raise_for_status()
            seeds = collect_from_any_response(response.text, college=college, site_id=config.get("orgId", ""))
            if seeds:
                return seeds, infer_total_pages_from_response(response.text, rows_per_page=rows), mode
            errors.append(
                f"{mode}: no teacher urls in response "
                f"(status={response.status_code}, bytes={len(response.content)}, "
                f"preview={response_preview(response.text)!r})"
            )
        except requests.RequestException as exc:
            errors.append(f"{mode}: {exc}")

    print(f"[warn] page {page_index}: AJAX failed ({'; '.join(errors)})")
    return [], 1, ""


def fetch_unfiltered_bulk(
    session: requests.Session,
    list_url: str,
    config: dict[str, str],
    rows: int,
    timeout: int,
    college: str,
    debug_ajax_dir: Path | None = None,
) -> tuple[list[Seed], int]:
    query_url = urljoin(list_url, html.unescape(config.get("queryUrl", "")))
    payload = build_unfiltered_payload(config=config, page_index=1, rows=rows)
    headers = {
        "User-Agent": session.headers.get("User-Agent", "Mozilla/5.0"),
        "Referer": list_url,
        "X-Requested-With": "XMLHttpRequest",
    }
    data = {
        **{k: v for k, v in payload.items() if k not in {"conditions", "orders", "returnInfos"}},
        "conditions": json.dumps(payload["conditions"], ensure_ascii=False),
        "orders": json.dumps(payload["orders"], ensure_ascii=False),
        "returnInfos": json.dumps(payload["returnInfos"], ensure_ascii=False),
    }
    response = session.post(query_url, timeout=timeout, headers=headers, data=data)
    if debug_ajax_dir:
        debug_ajax_dir.mkdir(parents=True, exist_ok=True)
        debug_path = debug_ajax_dir / "ajax_bulk_unfiltered.txt"
        debug_path.write_text(response.text, encoding="utf-8", errors="ignore")
    response.raise_for_status()
    seeds = collect_from_any_response(response.text, college=college, site_id=config.get("orgId", ""))
    return seeds, infer_total_pages_from_response(response.text, rows_per_page=rows)


def read_existing(path: Path) -> tuple[list[Seed], set[str]]:
    if not path.exists():
        return [], set()
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = [
            Seed(
                college=(row.get("college") or "").strip(),
                name=(row.get("name") or "").strip(),
                url=normalize_teacher_url((row.get("url") or "").strip()),
            )
            for row in reader
            if (row.get("url") or "").strip()
        ]
    return rows, {row.url for row in rows}


def write_seed_file(path: Path, rows: list[Seed]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["college", "name", "url"])
        writer.writeheader()
        for row in rows:
            writer.writerow({"college": row.college, "name": row.name, "url": row.url})


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover web.suda teacher homepage seeds from the teacher list page.")
    parser.add_argument("--list-url", help="web.suda teacher list URL. If omitted, built from --org-id and --college.")
    parser.add_argument("--org-id", default="15", help="College/department id used by web.suda, e.g. 15 for CS.")
    parser.add_argument("--output", default="data/seeds/teacher_seeds.csv", help="Seed CSV to update.")
    parser.add_argument("--college", default=DEFAULT_COLLEGE)
    parser.add_argument("--rows", type=int, default=20)
    parser.add_argument("--max-pages", type=int, default=0, help="0 means use the page count found in HTML.")
    parser.add_argument(
        "--bulk-rows",
        type=int,
        default=10000,
        help="Rows to request for the bulk fallback that filters siteId locally.",
    )
    parser.add_argument(
        "--ajax-page-cap",
        type=int,
        default=DEFAULT_AJAX_PAGE_CAP,
        help="Safety cap when AJAX reports a suspicious global page count. Use 0 to disable.",
    )
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--sleep", type=float, default=0.5)
    parser.add_argument("--dry-run", action="store_true", help="Print results without writing the seed CSV.")
    parser.add_argument("--debug-html", help="Save the fetched list-page HTML here for inspection.")
    parser.add_argument("--debug-ajax-dir", help="Save AJAX responses in this directory for inspection.")
    args = parser.parse_args()

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 SoochowIRCourseBot/0.1",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.5",
        }
    )

    output = Path(args.output)
    existing_rows, existing_urls = read_existing(output)
    debug_ajax_dir = Path(args.debug_ajax_dir) if args.debug_ajax_dir else None
    list_url = args.list_url or build_list_url(args.org_id, args.college)

    print(f"[info] fetching list page: {list_url}")
    page_html = fetch_text(session, list_url, timeout=args.timeout)
    print(f"[info] fetched page diagnostics: {describe_page(page_html)}")
    if args.debug_html:
        debug_path = Path(args.debug_html)
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        debug_path.write_text(page_html, encoding="utf-8")
        print(f"[info] saved fetched HTML to {debug_path}")
    discovered = parse_static_cards(page_html, list_url, college=args.college)
    config = parse_search_config(page_html, list_url)
    config["orgId"] = args.org_id
    total_pages = args.max_pages or parse_page_count(page_html, rows_per_page=args.rows)
    print(f"[info] first page seeds: {len(discovered)}")
    print(f"[info] total pages found in HTML: {total_pages}")

    if not discovered:
        print("[info] HTML has no teacher cards; trying AJAX page 1")
        page_seeds, ajax_pages, ajax_mode = fetch_ajax_page(
            session=session,
            list_url=list_url,
            config=config,
            page_index=1,
            rows=args.rows,
            timeout=args.timeout,
            college=args.college,
            debug_ajax_dir=debug_ajax_dir,
        )
        print(f"[info] AJAX page 1: {len(page_seeds)} seeds" + (f" via {ajax_mode}" if ajax_mode else ""))
        discovered.extend(page_seeds)
        if len(page_seeds) < 5:
            try:
                print(f"[info] AJAX page 1 yielded few seeds; trying bulk fallback with rows={args.bulk_rows}")
                bulk_seeds, bulk_pages = fetch_unfiltered_bulk(
                    session=session,
                    list_url=list_url,
                    config=config,
                    rows=args.bulk_rows,
                    timeout=args.timeout,
                    college=args.college,
                    debug_ajax_dir=debug_ajax_dir,
                )
                print(f"[info] bulk fallback: {len(bulk_seeds)} seeds")
                if bulk_seeds:
                    discovered.extend(bulk_seeds)
                    total_pages = 1
            except requests.RequestException as exc:
                print(f"[warn] bulk fallback failed: {exc}")
        if not args.max_pages and ajax_pages > total_pages:
            if args.ajax_page_cap and ajax_pages > args.ajax_page_cap:
                print(
                    f"[warn] AJAX reported {ajax_pages} pages; capping at {args.ajax_page_cap}. "
                    "Pass --max-pages N if the college has more pages."
                )
                total_pages = args.ajax_page_cap
            else:
                total_pages = ajax_pages

    print(f"[info] total pages to try: {total_pages}")

    for page_index in range(2, total_pages + 1):
        time.sleep(args.sleep)
        page_seeds, _, ajax_mode = fetch_ajax_page(
            session=session,
            list_url=list_url,
            config=config,
            page_index=page_index,
            rows=args.rows,
            timeout=args.timeout,
            college=args.college,
            debug_ajax_dir=debug_ajax_dir,
        )
        print(f"[info] page {page_index}: {len(page_seeds)} seeds" + (f" via {ajax_mode}" if ajax_mode else ""))
        discovered.extend(page_seeds)

    new_rows: list[Seed] = []
    for seed in discovered:
        if not seed.name or not seed.url or seed.url in existing_urls:
            continue
        existing_urls.add(seed.url)
        new_rows.append(seed)

    print(f"[info] discovered unique new seeds: {len(new_rows)}")
    for seed in new_rows[:20]:
        print(f"  {seed.name},{seed.url}")
    if len(new_rows) > 20:
        print(f"  ... {len(new_rows) - 20} more")

    if args.dry_run:
        print("[info] dry run: seed CSV not modified")
        return

    write_seed_file(output, existing_rows + new_rows)
    print(f"[info] wrote {len(existing_rows) + len(new_rows)} total seeds to {output}")


if __name__ == "__main__":
    main()
