from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from domain.teacher import TeacherDoc


def load_jsonl(path: str | Path) -> list[TeacherDoc]:
    docs: list[TeacherDoc] = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            docs.append(TeacherDoc.from_dict(json.loads(line)))
    return docs


def save_jsonl(docs: Iterable[TeacherDoc], path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        for doc in docs:
            f.write(json.dumps(doc.to_dict(), ensure_ascii=False) + "\n")
