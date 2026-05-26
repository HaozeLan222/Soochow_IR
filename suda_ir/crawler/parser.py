from __future__ import annotations

import hashlib
import re
from html.parser import HTMLParser

from suda_ir.models import TeacherDoc


PHONE_RE = re.compile(r"(?<!\d)(?:\+?86[-\s]?)?(?:0\d{2,3}[-\s]?)?\d{7,8}(?!\d)")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
WHITESPACE_RE = re.compile(r"\s+")
SECTION_RE = re.compile(
    r"^(#{1,6}\s*)?(个人资料|个人概况|个人简介|个人简历|研究领域|研究方向|科研方向|论文|学术论文|发表论文|科研项目|科技成果|招生信息|教育经历|工作经历|学术活动)\s*[:：]?$"
)

FIELD_ALIASES = {
    "research": ["研究方向", "研究领域", "科研方向", "主要研究方向", "研究兴趣", "目前主要研究方向"],
    "papers": ["代表论文", "论文", "发表论文", "学术论文", "科研成果", "主要成果", "代表性成果"],
    "profile": ["个人简介", "个人简历", "简介", "个人概况"],
    "title": ["职称", "专业技术职务", "职务", "岗位"],
    "college": ["直属机构", "院部/部门", "学院", "所在学院"],
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
        for tag in soup.find_all(["h1", "h2", "h3", "h4"]):
            tag.insert_before("\n")
            tag.insert_after("\n")
        text = soup.get_text("\n")
    except ImportError:
        parser = TextExtractor()
        parser.feed(html)
        text = parser.get_text()

    lines = [WHITESPACE_RE.sub(" ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def normalize_obfuscated_email(text: str) -> str:
    text = re.sub(r"\s*\[\s*at\s*\]\s*", "@", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+at\s+", "@", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*\[\s*dot\s*\]\s*", ".", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+dot\s+", ".", text, flags=re.IGNORECASE)
    return text


def redact_privacy(text: str) -> str:
    text = normalize_obfuscated_email(text)
    text = PHONE_RE.sub("***", text)
    text = EMAIL_RE.sub("***", text)
    return text


def extract_section(text: str, heading: str, max_chars: int = 500) -> str:
    lines = [line.strip() for line in text.splitlines()]
    for index, line in enumerate(lines):
        normalized = line.lstrip("#").strip()
        if normalized not in {heading, f"{heading}：", f"{heading}:"}:
            continue

        collected: list[str] = []
        for next_line in lines[index + 1 :]:
            next_line = next_line.strip()
            if not next_line:
                continue
            if SECTION_RE.match(next_line) and collected:
                break
            if next_line in {f"{heading}：", f"{heading}:"}:
                continue
            collected.append(next_line)
            if sum(len(item) for item in collected) >= max_chars:
                break
        return "\n".join(collected).strip()[:max_chars]
    return ""


def extract_by_alias(text: str, aliases: list[str], max_chars: int = 300) -> str:
    compact = normalize_obfuscated_email(text.replace("\r", "\n"))
    for alias in aliases:
        block = extract_section(compact, alias, max_chars=max_chars)
        if block:
            return block
        pattern = re.compile(rf"{re.escape(alias)}\s*[:：]\s*(.+)")
        for line in compact.splitlines():
            match = pattern.search(line)
            if match:
                return match.group(1).strip()[:max_chars]
    return ""


def guess_name(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    patterns = [
        r"^姓名\s*[:：]\s*([\u4e00-\u9fff·]{2,8})",
        r"^([\u4e00-\u9fff·]{2,8})的个人主页$",
        r"^欢迎来到([\u4e00-\u9fff·]{2,8})的个人主页$",
        r"^([\u4e00-\u9fff·]{2,8})\s*(特聘教授|教授|副教授|讲师|研究员|副研究员|博士)?$",
        r"^([\u4e00-\u9fff])\s+([\u4e00-\u9fff]{1,3})$",
    ]
    skipped = ["学院", "大学", "首页", "教师个人主页", "导航", "目录", "English", "欢迎"]
    titles = {"特聘教授", "教授", "副教授", "讲师", "研究员", "副研究员", "博士"}

    for line in lines[:30]:
        clean = line.lstrip("#").strip()
        if any(token in clean for token in skipped):
            continue
        for pattern in patterns:
            match = re.search(pattern, clean)
            if match:
                parts = [group for group in match.groups() if group and group not in titles]
                return "".join(parts)
    return ""


def guess_title(text: str) -> str:
    explicit = extract_by_alias(text, FIELD_ALIASES["title"], max_chars=80)
    if explicit:
        return explicit
    first_lines = "\n".join(text.splitlines()[:40])
    for title in ["特聘教授", "副教授", "副研究员", "教授", "讲师", "研究员"]:
        if title in first_lines:
            return title
    return ""


def guess_college(text: str, fallback: str = "") -> str:
    explicit = extract_by_alias(text, FIELD_ALIASES["college"], max_chars=120)
    if explicit:
        return explicit
    for line in text.splitlines()[:100]:
        clean = line.strip().lstrip("#").strip()
        if "学院" in clean and len(clean) <= 50:
            return clean
    return fallback


def is_probable_teacher_page(text: str) -> bool:
    if len(text) < 20:
        return False
    positive = ["教师个人主页", "个人资料", "个人简介", "个人简历", "研究领域", "研究方向", "职称", "电子邮箱"]
    negative = ["学院列表", "教师分类查询", "热点主页", "最新更新"]
    positive_hits = sum(1 for token in positive if token in text)
    negative_hits = sum(1 for token in negative if token in text[:300])
    return positive_hits >= 2 and negative_hits < 3


def parse_teacher_page(html: str, url: str = "", college: str = "") -> TeacherDoc:
    raw_text = normalize_obfuscated_email(html_to_text(html))
    text = redact_privacy(raw_text)
    doc_id = hashlib.sha1((url + text[:200]).encode("utf-8", errors="ignore")).hexdigest()[:16]
    return TeacherDoc(
        doc_id=doc_id,
        name=guess_name(text),
        college=guess_college(text, fallback=college),
        title=guess_title(text),
        research=extract_by_alias(text, FIELD_ALIASES["research"], max_chars=500),
        papers=extract_by_alias(text, FIELD_ALIASES["papers"], max_chars=800),
        profile=extract_by_alias(text, FIELD_ALIASES["profile"], max_chars=800),
        content=text,
        url=url,
        final_url=url,
    )
