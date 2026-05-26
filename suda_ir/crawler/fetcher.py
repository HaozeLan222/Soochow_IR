from __future__ import annotations

import random
import re
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Iterable
from urllib.error import URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


@dataclass
class FetchedPage:
    url: str
    final_url: str
    html: str
    status_code: int = 200
    redirect_url: str = ""
    error: str = ""


class LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for key, value in attrs:
            if key.lower() == "href" and value:
                self.links.append(value)


def fetch_url(url: str, timeout: int = 15) -> FetchedPage:
    try:
        import requests

        response = requests.get(url, timeout=timeout, headers=_headers(), allow_redirects=True)
        html = decode_html_bytes(
            response.content,
            candidates=[response.encoding, response.apparent_encoding],
        )
        return FetchedPage(
            url=url,
            final_url=response.url,
            html=html,
            status_code=response.status_code,
            redirect_url=extract_client_redirect(response.url, html),
        )
    except ImportError:
        return _fetch_with_urllib(url, timeout=timeout)
    except Exception:
        return _fetch_with_urllib(url, timeout=timeout)


def _fetch_with_urllib(url: str, timeout: int = 15) -> FetchedPage:
    candidates = [url]
    parsed = urlparse(url)
    if parsed.scheme == "https" and parsed.netloc == "web.suda.edu.cn":
        candidates.append(url.replace("https://", "http://", 1))

    last_error: Exception | None = None
    for candidate in candidates:
        try:
            request = Request(candidate, headers=_headers())
            with urlopen(request, timeout=timeout) as response:
                data = response.read()
                charset = response.headers.get_content_charset()
                html = decode_html_bytes(data, candidates=[charset])
                return FetchedPage(
                    url=url,
                    final_url=response.geturl(),
                    html=html,
                    status_code=getattr(response, "status", 200),
                    redirect_url=extract_client_redirect(response.geturl(), html),
                )
        except (URLError, OSError) as exc:
            last_error = exc

    if last_error:
        raise last_error
    raise RuntimeError(f"Unable to fetch URL: {url}")


def _headers() -> dict[str, str]:
    return {
        "User-Agent": "Mozilla/5.0 SoochowIRCourseBot/0.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.5",
    }


def decode_html_bytes(data: bytes, candidates: list[str | None] | None = None) -> str:
    candidate_list = ["utf-8"]
    if candidates:
        candidate_list.extend(candidate for candidate in candidates if candidate)

    head = data[:4096].decode("ascii", errors="ignore")
    meta = re.search(r"charset\s*=\s*['\"]?([A-Za-z0-9_\-]+)", head, flags=re.IGNORECASE)
    if meta:
        candidate_list.append(meta.group(1))
    candidate_list.extend(["gb18030", "gbk"])

    seen: set[str] = set()
    decoded: list[tuple[int, str]] = []
    for encoding in candidate_list:
        normalized = encoding.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        try:
            text = data.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
        decoded.append((_mojibake_score(text), text))

    if decoded:
        decoded.sort(key=lambda item: item[0])
        return decoded[0][1]
    return data.decode("utf-8", errors="replace")


def _mojibake_score(text: str) -> int:
    bad_tokens = ["�", "鍛", "瑙", "鐮", "绠", "瀛", "涓", "嗗", "俓n"]
    return sum(text.count(token) for token in bad_tokens)


def extract_client_redirect(base_url: str, html: str) -> str:
    patterns = [
        r'<meta[^>]+http-equiv=["\']?refresh["\']?[^>]+content=["\'][^"\']*url=([^"\'>]+)',
        r"(?:window\.)?location(?:\.href)?\s*=\s*['\"]([^'\"]+)['\"]",
    ]
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.IGNORECASE)
        if match:
            return urljoin(base_url, match.group(1).strip())
    return ""


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    normalized = f"{scheme}://{netloc}{path}"
    if parsed.query:
        normalized += f"?{parsed.query}"
    return normalized.rstrip("#")


def discover_links(
    base_url: str,
    html: str,
    same_domain: bool = True,
    allowed_domains: set[str] | None = None,
) -> list[str]:
    parser = LinkExtractor()
    parser.feed(html)
    base_domain = urlparse(base_url).netloc
    links: list[str] = []
    seen: set[str] = set()
    for href in parser.links:
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in {"http", "https"}:
            continue
        if allowed_domains and parsed.netloc not in allowed_domains:
            continue
        if same_domain and not allowed_domains and parsed.netloc != base_domain:
            continue
        if not _is_crawlable_path(parsed.path):
            continue
        normalized = normalize_url(absolute.split("#", 1)[0])
        if normalized not in seen:
            seen.add(normalized)
            links.append(normalized)
    return links


def _is_crawlable_path(path: str) -> bool:
    lowered = path.lower()
    if lowered.endswith((".jpg", ".jpeg", ".png", ".gif", ".css", ".js", ".pdf", ".doc", ".docx")):
        return False
    return lowered.endswith((".htm", ".html", "/")) or "." not in lowered.rsplit("/", 1)[-1]


def crawl_static_pages(
    seeds: Iterable[str],
    max_pages: int = 100,
    pause_range: tuple[float, float] = (1.0, 3.0),
    allowed_domains: set[str] | None = None,
    follow_links: bool = True,
) -> list[FetchedPage]:
    queue = [normalize_url(seed) for seed in seeds]
    visited: set[str] = set()
    pages: list[FetchedPage] = []

    while queue and len(pages) < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        try:
            page = fetch_url(url)
        except Exception as exc:
            pages.append(FetchedPage(url=url, final_url=url, html="", status_code=0, error=str(exc)))
            time.sleep(random.uniform(*pause_range))
            continue
        pages.append(page)
        if not follow_links:
            time.sleep(random.uniform(*pause_range))
            continue
        if page.redirect_url and page.redirect_url not in visited and page.redirect_url not in queue:
            queue.append(page.redirect_url)
        for link in discover_links(page.final_url, page.html, allowed_domains=allowed_domains):
            if link not in visited and link not in queue:
                queue.append(link)
        time.sleep(random.uniform(*pause_range))

    return pages
