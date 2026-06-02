from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from suda_ir.crawler.parser import (  # noqa: E402
    FIELD_ALIASES,
    TITLE_WORDS,
    extract_by_alias,
    extract_sections,
    first_section,
    guess_title,
)
from suda_ir.data.storage import load_jsonl, save_jsonl  # noqa: E402
from suda_ir.models import TeacherDoc  # noqa: E402


EXACT_NOISE_LINES = {
    "教师个人主页",
    "返回首页",
    "欢迎登录",
    "导航",
    "english",
    "最新上线",
    "相关教师",
    "软件著作",
    "软件著作：",
    "专利",
    "专利：",
    "课程教学：",
    "科研成果（旧版）",
    "荣誉奖励（旧版）",
    "研究项目（旧版）",
    "copyright 苏州大学 2019, all rights reserved 苏州市十梓街1号",
}

FOOTER_PATTERNS = [
    re.compile(r"copyright", re.IGNORECASE),
    re.compile(r"all rights reserved", re.IGNORECASE),
    re.compile(r"版权所有"),
    re.compile(r"推荐使用ie", re.IGNORECASE),
    re.compile(r"信息化建设与管理中心"),
    re.compile(r"技术支持"),
]

FIELD_LABELS = {
    "姓名",
    "职称",
    "院部/部门",
    "直属机构",
    "学历",
    "学位",
    "毕业学校",
    "毕业院校",
    "毕业专业",
    "通讯地址",
    "邮政编码",
    "邮编",
    "电子邮箱",
    "联系电话",
    "传真",
    "传真号码",
    "办公地址",
    "办公地点",
    "专业技术职务",
    "性别",
}

SECTION_STOP_LINES = {
    "社会职务",
    "社会职务：",
    "基本信息",
    "个人资料",
    "个人资料：",
    "个人信息",
    "个人信息：",
    "个人概况",
    "个人概况：",
    "开授课程",
    "开授课程：",
    "科研项目",
    "科研项目：",
    "科研成果",
    "科研成果：",
    "荣誉及奖励",
    "荣誉及奖励：",
    "招生信息",
    "招生信息：",
    "论文",
    "论文：",
    "Teaching",
    "Research",
    "Research Area",
    "Recruiting",
    "Language",
}

SHORT_PLACEHOLDER_RE = re.compile(r"^(社会职务[:：]?|课程教学[:：]?|软件著作[:：]?|专利[:：]?|科研团队|科研生活)$")
LABEL_VALUE_RE = re.compile(r"^([\u4e00-\u9fffA-Za-z/（）()]+)\s*[:：]\s*(.*)$")
TITLE_RE = re.compile("|".join(map(re.escape, sorted(TITLE_WORDS, key=len, reverse=True))))
LAB_RE = re.compile(r"\b(lab|laboratory|members|gallery|join us|advisor)\b", re.IGNORECASE)
URL_RE = re.compile(r"https?://\S+")
BULLET_LINE_RE = re.compile(r"^(?:[-*•]|[（(]?\d+[）).、])")
NUMBER_ONLY_LINE_RE = re.compile(r"^[（(]?\d+[）).、]?$")
PUNCT_ONLY_LINE_RE = re.compile(r"^[：:；;，,。、）)\]】]+$")
OPEN_ONLY_LINE_RE = re.compile(r"^[（(\[【]+$")


def clean_lines(text: str, *, stop_at_footer: bool = True) -> list[str]:
    lines = [line.strip() for line in text.replace("\r", "\n").splitlines()]
    cleaned: list[str] = []

    for index, line in enumerate(lines):
        if not line:
            continue
        lower = line.lower()
        if lower in EXACT_NOISE_LINES:
            continue
        if line in EXACT_NOISE_LINES:
            continue
        if stop_at_footer and any(pattern.search(line) for pattern in FOOTER_PATTERNS):
            break
        if line == "访问":
            if cleaned and re.fullmatch(r"\d{1,6}", cleaned[-1]):
                cleaned.pop()
            continue
        if line == "相关教师":
            continue
        if line == "English":
            continue
        if re.fullmatch(r"\d{1,6}", line):
            next_line = ""
            for candidate in lines[index + 1 :]:
                if candidate.strip():
                    next_line = candidate.strip()
                    break
            if next_line in {"访问", "最新上线"}:
                continue
        cleaned.append(line)

    deduped: list[str] = []
    for line in cleaned:
        if deduped and deduped[-1] == line:
            continue
        deduped.append(line)
    return deduped


def clean_content(text: str) -> str:
    lines = clean_lines(text)
    return normalize_content_text("\n".join(strip_navigation_blocks(lines)).strip())


def clean_field_text(text: str, field: str) -> str:
    if not text:
        return ""

    lines = clean_lines(text)
    cleaned: list[str] = []

    for line in lines:
        if SHORT_PLACEHOLDER_RE.fullmatch(line):
            continue
        if field in {"research", "profile", "papers"} and line in SECTION_STOP_LINES:
            break
        if field == "research" and line in {"基本信息", "个人资料", "个人信息"}:
            break
        if field == "profile" and line in {"研究领域", "研究方向", "科研方向"}:
            break
        match = LABEL_VALUE_RE.match(line)
        if match and match.group(1) in FIELD_LABELS:
            value = match.group(2).strip()
            if value:
                cleaned.append(value)
            continue
        cleaned.append(line)

    if cleaned:
        first = cleaned[0]
        match = LABEL_VALUE_RE.match(first)
        if match and match.group(1) not in FIELD_LABELS:
            head = match.group(1)
            tail = match.group(2).strip()
            if head in {"研究方向", "研究领域", "科研方向", "个人简介", "个人简历", "个人概况", "论文", "学术论文"}:
                cleaned = ([tail] if tail else []) + cleaned[1:]

    while cleaned and cleaned[0] in SECTION_STOP_LINES:
        cleaned.pop(0)
    while cleaned and SHORT_PLACEHOLDER_RE.fullmatch(cleaned[-1]):
        cleaned.pop()

    value = normalize_field_layout(cleaned, field)
    value = postprocess_field_value(value, field)
    if not value:
        return ""
    if SHORT_PLACEHOLDER_RE.fullmatch(value):
        return ""
    return value


def normalize_field_layout(lines: list[str], field: str) -> str:
    compacted: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if compacted and should_merge_lines(compacted[-1], stripped, field):
            compacted[-1] = merge_line_pair(compacted[-1], stripped)
        else:
            compacted.append(stripped)

    text = "\n".join(compacted).strip()
    text = re.sub(r"\n([：:；;，,。、）)\]】])", r"\1", text)
    text = re.sub(r"([（(\[【])\n", r"\1", text)
    text = re.sub(r"\n([\-—–/])\n", r"\1", text)
    text = re.sub(r"\n([0-9０-９]+[.、])\s*", r"\n\1 ", text)
    text = re.sub(r"\n([（(]?[0-9０-９]+[）)])\s*", r"\n\1", text)
    text = re.sub(r"([（(]\d+)\s+([）)])", r"\1\2", text)
    text = re.sub(r":(?!//)", "：", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def postprocess_field_value(text: str, field: str) -> str:
    if not text:
        return ""
    text = normalize_broken_tokens(text)
    if field == "research":
        text = collapse_simple_bullet_lines(text)
    elif field == "profile":
        text = normalize_profile_text(text)
    elif field == "papers":
        text = normalize_papers_text(text)
    return text.strip()


def collapse_simple_bullet_lines(text: str) -> str:
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if len(lines) < 2:
        return text
    if not all(BULLET_LINE_RE.match(line) for line in lines):
        return text
    if max(len(line) for line in lines) > 35:
        return text

    normalized: list[str] = []
    for index, line in enumerate(lines):
        item = line
        if not item.endswith(("。", "；", ";")) and index < len(lines) - 1:
            item = item + "；"
        normalized.append(item)
    return "".join(normalized)


def normalize_broken_tokens(text: str) -> str:
    text = re.sub(r"([A-Za-z])\n-\s*([A-Za-z])", r"\1-\2", text)
    text = re.sub(r"C\*\s*-\s*\n\s*代数", "C*-代数", text)
    text = re.sub(r"(\d)\n\s*(?=\d+[、.])", r"\1", text)
    text = re.sub(r"(\d)\.\s+(\d)", r"\1.\2", text)
    text = re.sub(
        r"(https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+)(?=[\u4e00-\u9fff])",
        r"\1\n",
        text,
    )
    text = re.sub(r"\b(19|20)\s+(\d{2})\b", r"\1\2", text)
    text = re.sub(r"\b(\d{3})\s+(\d)\b", r"\1\2", text)
    text = re.sub(r"(?<=\d)\s+(?=\.\d)", "", text)
    text = re.sub(r"(?<=\d\.)\s+(?=\d)", "", text)
    text = re.sub(r"(?<=\bArxiv[:：]\s)([0-9][0-9.\svV-]{5,})", lambda m: re.sub(r"\s+", "", m.group(1)), text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def normalize_profile_text(text: str) -> str:
    text = re.sub(r"(\d{4}年\d{1,2}月)\n-\s*(\d{4}年\d{1,2}月)", r"\1-\2", text)
    text = re.sub(r"(\d{4}年\d{1,2}月)-\s*\n\s*(\d{4}年\d{1,2}月)", r"\1-\2", text)
    text = re.sub(r"(\d{4}\.\d{2})\n([~-])\s*(\d{4}\.\d{2})", r"\1\2\3", text)
    text = re.sub(r"(?<![\n\-—–~至])(?=(?:19|20)\d{2}年\d{1,2}月(?:[-~至]|$))", "\n", text)
    text = re.sub(r"(?<![\n\-—–~至])(?=(?:19|20)\d{2}年\d{1,2}月(?:[-~至]\d{4}年\d{1,2}月)?[,，])", "\n", text)
    text = re.sub(r"(?<![\n\-—–~至])(?=(?:19|20)\d{2}\.\d{2}\s*[~-])", "\n", text)
    text = re.sub(r"(?<!\n)(?=(Google Scholar|ORCID|Education:|Professional Experiences:|Professiobal Experiences:))", "\n", text)
    text = re.sub(r"(?<!\n)(?=(预印本信息如下[:：]|具体信息如下[。：]|正式发表论文信息如下[:：]))", "\n", text)
    text = re.sub(r"((?:预印本信息如下[:：]|具体信息如下[。：]|正式发表论文信息如下[:：]))(?=[A-Z])", r"\1\n", text)
    text = re.sub(r"(?<=[0-9a-zA-Z]\.)(?=(?:[A-Z]\.|在此项目资助期内|以下论文被正式接受))", "\n", text)
    text = re.sub(r"(Arxiv[:：]\s*[0-9.vV-]+)(?=[\u4e00-\u9fff])", r"\1\n", text)
    text = re.sub(r"(?<=[0-9*]\.)(?=(?:[A-Z]\.|[A-Z][a-z]+,\s*[A-Z]\.))", "\n", text)
    text = re.sub(r"。。+", "。", text)
    text = re.sub(r"([。；])\n([。；])", r"\1\2", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_papers_text(text: str) -> str:
    text = re.sub(r"\n(?=\d+\.\d)", "", text)
    text = re.sub(r"\n(?=(H-index|i10-index|Google Scholar|ORCID|更多介绍：|课题组主页：))", "", text)
    text = re.sub(r"(?<![\n\d])(?=(?:\(?\d{1,2}\)|\d+[、.])\s*[A-Za-z])", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_content_text(text: str) -> str:
    text = normalize_broken_tokens(text)
    text = re.sub(
        r"(?<!\n)(?=(教育经历|工作经历|个人简介|个人简历|个人概况|研究领域|研究方向|科研项目|论文|科研成果|荣誉及奖励|招生信息|开授课程)(?:[:：]))",
        "\n",
        text,
    )
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def should_merge_lines(previous: str, current: str, field: str) -> bool:
    prev = previous.strip()
    curr = current.strip()

    if not prev or not curr:
        return False
    if PUNCT_ONLY_LINE_RE.fullmatch(curr):
        return True
    if OPEN_ONLY_LINE_RE.fullmatch(prev):
        return True
    if prev.endswith(("（", "(", "[", "【", "-", "—", "–", "/", "·")):
        return True
    if NUMBER_ONLY_LINE_RE.fullmatch(prev):
        return True
    if URL_RE.fullmatch(curr) and prev.endswith(("：", ":")):
        return True
    if curr in {"-", "—", "–", "/", ":", "："}:
        return True
    if not BULLET_LINE_RE.match(curr) and not URL_RE.fullmatch(curr) and not prev.endswith(("。", "！", "？", "!", "?", ";", "；")):
        return True
    if field == "papers" and not BULLET_LINE_RE.match(curr) and not prev.endswith(("。", "！", "？", "!", "?", ";", "；")):
        return True
    return False


def strip_navigation_blocks(lines: list[str]) -> list[str]:
    stripped: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line in SECTION_STOP_LINES:
            window = lines[i : i + 8]
            section_like = sum(1 for item in window if item in SECTION_STOP_LINES)
            if section_like >= 4:
                while i < len(lines) and lines[i] in SECTION_STOP_LINES:
                    i += 1
                continue
        stripped.append(line)
        i += 1
    return stripped


def merge_line_pair(previous: str, current: str) -> str:
    prev = previous.rstrip()
    curr = current.lstrip()

    if PUNCT_ONLY_LINE_RE.fullmatch(curr):
        return prev + curr
    if NUMBER_ONLY_LINE_RE.fullmatch(prev):
        if prev.endswith(("、", "）", ")")):
            return prev + curr
        return prev + " " + curr
    if prev.endswith(("（", "(", "[", "【", "-", "—", "–", "/", "·", "：", ":")):
        return prev + curr
    if curr in {"-", "—", "–", "/", ":", "："}:
        return prev + curr
    if URL_RE.fullmatch(curr):
        separator = "" if prev.endswith(("：", ":")) else " "
        return prev + separator + curr
    if prev and curr and _is_ascii_wordish(prev[-1]) and _is_ascii_wordish(curr[0]):
        return prev + " " + curr
    return prev + curr


def _is_ascii_wordish(char: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9]", char))


def infer_title_from_text(*texts: str) -> str:
    for text in texts:
        if not text:
            continue
        guess = guess_title(text)
        if guess:
            return guess
        match = TITLE_RE.search(text[:600])
        if match:
            return match.group(0)
    return ""


def infer_research(text: str, profile: str, sections: dict[str, str]) -> str:
    candidates = [
        first_section(sections, ["研究领域", "研究方向", "科研方向"]),
        extract_by_alias(text, FIELD_ALIASES["research"], max_chars=800),
    ]
    profile_patterns = [
        re.compile(r"(?:研究方向|主要研究方向|研究兴趣)[：:\s]*(.+)"),
        re.compile(r"长期从事(.+?)(?:研究。|研究工作。|研究工作|。)"),
    ]
    for pattern in profile_patterns:
        match = pattern.search(profile.replace("\n", " "))
        if match:
            candidates.append(match.group(1).strip())
    for item in candidates:
        cleaned = clean_field_text(item, "research")
        if cleaned:
            return cleaned
    return ""


def clean_sections(sections: dict[str, str]) -> dict[str, str]:
    cleaned: dict[str, str] = {}
    field_map = {
        "研究领域": "research",
        "研究方向": "research",
        "科研方向": "research",
        "论文": "papers",
        "学术论文": "papers",
        "发表论文": "papers",
        "科研成果": "papers",
        "科技成果": "papers",
        "个人简介": "profile",
        "个人简历": "profile",
        "个人概况": "profile",
    }
    for key, value in sections.items():
        field = field_map.get(key, "content")
        cleaned_value = clean_field_text(value, field)
        if cleaned_value:
            cleaned[key] = cleaned_value
    return cleaned


def assess_quality(doc: TeacherDoc) -> tuple[str, list[str]]:
    flags: list[str] = []
    if not doc.title:
        flags.append("missing_title")
    if not doc.research:
        flags.append("missing_research")
    if not doc.profile:
        flags.append("missing_profile")
    if not doc.url:
        flags.append("missing_url")
    if LAB_RE.search(doc.content) and not doc.title and not doc.profile:
        flags.append("lab_like_homepage")
    page_reason = str(doc.extra.get("page_reason", ""))
    if page_reason.startswith("weak_teacher_signals") or page_reason == "too_short":
        flags.append("weak_page_signal")
    if len(doc.content) < 200:
        flags.append("very_short_content")

    score = 0
    score += int(bool(doc.title))
    score += int(bool(doc.research))
    score += int(bool(doc.profile))
    score += int(bool(doc.url))
    score += int("lab_like_homepage" not in flags)

    if score >= 5 and "weak_page_signal" not in flags:
        return "high", flags
    if score >= 3:
        return "medium", flags
    return "low", flags


def build_clean_content(
    doc: TeacherDoc,
    *,
    cleaned_content: str,
    title: str,
    profile: str,
    research: str,
    papers: str,
    sections: dict[str, str],
) -> str:
    parts: list[str] = []

    for value in [doc.college.strip(), doc.name.strip(), title.strip()]:
        if value and value not in parts:
            parts.append(value)

    section_order = [
        ("个人简介", profile),
        ("研究领域", research),
        ("教育经历", first_section(sections, ["教育经历"])),
        ("工作经历", first_section(sections, ["工作经历"])),
        ("科研项目", first_section(sections, ["科研项目"])),
        ("论文", papers),
        ("荣誉及奖励", first_section(sections, ["荣誉及奖励"])),
        ("招生信息", first_section(sections, ["招生信息"])),
    ]
    for label, value in section_order:
        value = (value or "").strip()
        if value:
            parts.append(f"{label}\n{value}")

    if len(parts) <= 3 and cleaned_content:
        parts.append(cleaned_content)

    return "\n\n".join(parts).strip()


def clean_doc(doc: TeacherDoc) -> TeacherDoc:
    cleaned_content = clean_content(doc.content)
    extracted_sections = clean_sections(extract_sections(cleaned_content))
    original_sections = clean_sections(doc.extra.get("sections", {}))

    combined_sections = dict(original_sections)
    combined_sections.update({key: value for key, value in extracted_sections.items() if key not in combined_sections})

    profile = clean_field_text(doc.profile, "profile") or first_section(
        combined_sections, ["个人简介", "个人简历", "个人概况"]
    )
    research = clean_field_text(doc.research, "research") or infer_research(cleaned_content, profile, combined_sections)
    papers = clean_field_text(doc.papers, "papers") or first_section(
        combined_sections, ["论文", "学术论文", "发表论文", "科研成果", "科技成果"]
    )
    title = doc.title.strip()
    if not title:
        title = infer_title_from_text(cleaned_content, profile, research)

    final_url = doc.final_url or doc.url
    url = doc.url or final_url

    doc.profile = profile
    doc.research = research
    doc.papers = papers
    doc.title = title
    doc.url = url
    doc.final_url = final_url
    doc.extra["sections"] = combined_sections
    doc.extra["cleaned_from"] = "handoff_teachers.jsonl"
    doc.content = build_clean_content(
        doc,
        cleaned_content=cleaned_content,
        title=title,
        profile=profile,
        research=research,
        papers=papers,
        sections=combined_sections,
    )

    quality, flags = assess_quality(doc)
    doc.extra["clean_quality"] = quality
    doc.extra["clean_flags"] = flags
    return doc


def clean_dataset(docs: list[TeacherDoc], *, drop_low_quality: bool = False) -> tuple[list[TeacherDoc], dict[str, object]]:
    cleaned_docs: list[TeacherDoc] = []
    quality_counter: Counter[str] = Counter()
    flag_counter: Counter[str] = Counter()
    dropped: list[dict[str, str]] = []

    for doc in docs:
        cleaned = clean_doc(doc)
        quality = str(cleaned.extra.get("clean_quality", "unknown"))
        flags = list(cleaned.extra.get("clean_flags", []))
        quality_counter[quality] += 1
        flag_counter.update(flags)

        if drop_low_quality and quality == "low":
            dropped.append(
                {
                    "name": cleaned.name,
                    "college": cleaned.college,
                    "url": cleaned.url,
                    "raw_path": str(cleaned.extra.get("raw_path", "")),
                    "flags": ",".join(flags),
                }
            )
            continue
        cleaned_docs.append(cleaned)

    summary = {
        "input_docs": len(docs),
        "output_docs": len(cleaned_docs),
        "dropped_docs": len(dropped),
        "quality": dict(sorted(quality_counter.items())),
        "flags": dict(sorted(flag_counter.items())),
    }
    return cleaned_docs, {"summary": summary, "dropped": dropped}


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean parsed teacher JSONL for retrieval use.")
    parser.add_argument("--input", default="data/processed/handoff_teachers.jsonl")
    parser.add_argument("--output", default="data/processed/handoff_teachers.clean.jsonl")
    parser.add_argument("--report", help="Path to write clean report JSON.")
    parser.add_argument("--drop-low-quality", action="store_true", help="Drop documents whose clean quality is low.")
    args = parser.parse_args()

    docs = load_jsonl(args.input)
    cleaned_docs, report = clean_dataset(docs, drop_low_quality=args.drop_low_quality)
    save_jsonl(cleaned_docs, args.output)

    report_path = Path(args.report) if args.report else Path(args.output).with_suffix(".report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Saved {report['summary']['output_docs']} cleaned documents to {args.output}")
    print(f"Quality: {report['summary']['quality']}")
    print(f"Dropped: {report['summary']['dropped_docs']}")
    print(f"Saved clean report to {report_path}")


if __name__ == "__main__":
    main()
