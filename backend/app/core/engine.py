from __future__ import annotations

from abc import ABC, abstractmethod

from domain.search import SearchResult
from domain.teacher import TeacherDoc


class SearchEngineBase(ABC):
    @abstractmethod
    def load(self, data_path: str) -> None:
        ...

    @abstractmethod
    def search(self, query: str, top_k: int = 10, field: str = "all") -> list[SearchResult]:
        ...

    @abstractmethod
    def get_teacher(self, doc_id: str) -> TeacherDoc | None:
        ...

    @abstractmethod
    def list_teachers(self, college: str | None = None) -> list[TeacherDoc]:
        ...

    @abstractmethod
    def get_stats(self) -> dict:
        ...
