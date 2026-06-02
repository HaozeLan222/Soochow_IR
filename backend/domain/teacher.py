from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class TeacherDoc:
    doc_id: str
    name: str = ""
    college: str = ""
    title: str = ""
    research: str = ""
    papers: str = ""
    profile: str = ""
    content: str = ""
    url: str = ""
    final_url: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TeacherDoc":
        allowed = set(cls.__dataclass_fields__)
        values = {key: data.get(key, "") for key in allowed if key != "extra"}
        values["extra"] = data.get("extra") or {}
        return cls(**values)
