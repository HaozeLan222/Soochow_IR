from __future__ import annotations

import random
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Iterable
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


@dataclass
class FetchedPage:
    url: str
    final_url: str
    html: str
    status_code: int = 200


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

        response = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "SoochowIRCourseBot/0.1"},
            allow_redirects=True,
        )
        response.encoding = response.apparent_encoding or response.encoding
        return FetchedPage(
            url=url,
            final_url=response.url,
            html=response.text,
            status_code=response.status_code,
        )
    except ImportError:
        request = Request(url, headers={"User-Agent": "SoochowIRCourseBot/0.1"})
        with urlopen(request, timeout=timeout) as response:
            data = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
            return FetchedPage(
                url=url,
                final_url=response.geturl(),
                html=data.decode(charset, errors="replace"),
                status_code=getattr(response, "status", 200),
            )


def discover_links(base_url: str, html: str, same_domain: bool = True) -> list[str]:
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
        if same_domain and parsed.netloc != base_domain:
            continue
        if not parsed.path.endswith((".htm", ".html", "/")):
            continue
        normalized = absolute.split("#", 1)[0]
        if normalized not in seen:
            seen.add(normalized)
            links.append(normalized)
    return links


def crawl_static_pages(
    seeds: Iterable[str],
    max_pages: int = 100,
    pause_range: tuple[float, float] = (1.0, 3.0),
) -> list[FetchedPage]:
    queue = list(seeds)
    visited: set[str] = set()
    pages: list[FetchedPage] = []

    while queue and len(pages) < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        page = fetch_url(url)
        pages.append(page)
        for link in discover_links(page.final_url, page.html):
            if link not in visited and link not in queue:
                queue.append(link)
        time.sleep(random.uniform(*pause_range))

    return pages

