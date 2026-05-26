from __future__ import annotations

import hashlib
import re
from html.parser import HTMLParser

from suda_ir.models import TeacherDoc


PHONE_RE = re.compile(r"(?<!\d)(?:\+?86[-\s]?)?(?:0\d{2,3}[-\s]?)?\d{7,8}(?!\d)")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
WHITESPACE_RE = re.compile(r"\s+")

FIELD_ALIASES = {
    "research": ["研究方向", "研究领域", "科研方向", "主要研究方向", "研究兴趣"],
    "papers": ["代表论文", "论文", "发表论文", "科研成果", "主要成果", "代表性成果"],
    "profile": ["个人简介", "简介", "教育经历", "工作经历", "个人履历"],
    "title": ["职称", "岗位", "职务"],
}


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.parts.append(text)

    def get_text(self) -> str:
        return "\n".join(self.parts)


def html_to_text(html: str) -> str:
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text("\n")
    except ImportError:
        parser = TextExtractor()
        parser.feed(html)
        text = parser.get_text()
    lines = [WHITESPACE_RE.sub(" ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def redact_privacy(text: str) -> str:
    text = PHONE_RE.sub("***", text)
    text = EMAIL_RE.sub("***", text)
    return text


def extract_by_alias(text: str, aliases: list[str], max_chars: int = 300) -> str:
    compact = text.replace("\r", "\n")
    for alias in aliases:
        pattern = re.compile(rf"{re.escape(alias)}\s*[:：]?\s*(.+)")
        for line in compact.splitlines():
            match = pattern.search(line)
            if match:
                return match.group(1).strip()[:max_chars]
    return ""


def guess_name(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines[:20]:
        if 2 <= len(line) <= 8 and not any(ch.isdigit() for ch in line):
            if not any(token in line for token in ["学院", "大学", "首页", "教师", "苏州"]):
                return line
    return ""


def parse_teacher_page(html: str, url: str = "", college: str = "") -> TeacherDoc:
    raw_text = html_to_text(html)
    text = redact_privacy(raw_text)
    doc_id = hashlib.sha1((url + text[:200]).encode("utf-8", errors="ignore")).hexdigest()[:16]
    return TeacherDoc(
        doc_id=doc_id,
        name=guess_name(text),
        college=college,
        title=extract_by_alias(text, FIELD_ALIASES["title"], max_chars=80),
        research=extract_by_alias(text, FIELD_ALIASES["research"], max_chars=500),
        papers=extract_by_alias(text, FIELD_ALIASES["papers"], max_chars=800),
        profile=extract_by_alias(text, FIELD_ALIASES["profile"], max_chars=800),
        content=text,
        url=url,
        final_url=url,
    )

