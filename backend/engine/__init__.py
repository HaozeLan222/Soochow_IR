from __future__ import annotations

from abc import ABC, abstractmethod

from domain.query import EngineQuery
from domain.search import SearchResult
from domain.teacher import TeacherDoc

_REGISTRY: dict[str, type["SearchEngineBase"]] = {}


def register_engine(name: str):
    """装饰器：将 Engine 子类注册到全局 registry。"""
    def decorator(cls: type[SearchEngineBase]):
        _REGISTRY[name] = cls
        return cls
    return decorator


def get_engine_class(name: str) -> type[SearchEngineBase]:
    if name not in _REGISTRY:
        raise ValueError(f"Unknown engine: {name!r}. Available: {list(_REGISTRY)}")
    return _REGISTRY[name]


def list_engines() -> list[str]:
    return list(_REGISTRY.keys())


class SearchEngineBase(ABC):
    @abstractmethod
    def load(self, data_path: str) -> None:
        ...

    @abstractmethod
    def search(self, query: EngineQuery) -> list[SearchResult]:
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
