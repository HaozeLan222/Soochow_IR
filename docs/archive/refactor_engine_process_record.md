# 后端 Engine 重构方案

> 历史过程记录：本文记录后端 Engine 重构过程，当前可运行的 IR 模块说明以 `../ir_model_handoff.md` 和 `../engine_interface.md` 为准。

更新时间：2026-06-09

## 一、现状分析

### 1.1 当前数据模型

#### Domain 层（dataclass，`backend/domain/`）

| 模型 | 文件 | 字段 |
|------|------|------|
| `TeacherDoc` | `domain/teacher.py` | 14字段：doc_id, name, college, title, research, papers, profile, content, url, final_url, **email, phone, photo_url**, extra |
| `SearchResult` | `domain/search.py` | 3字段：doc(TeacherDoc), score(float), matched_terms(list[str]) |

#### Schemas 层（Pydantic，`backend/app/schemas/models.py`）

| 模型 | 用途 | 字段 |
|------|------|------|
| `SearchRequest` | 搜索请求（当前未使用，端点用 Query params） | q, field, top_k, college |
| `TeacherResult` | 搜索结果响应 | TeacherDoc 14字段 + score + matched_terms |
| `TeacherDetail` | 教师详情/列表响应 | 10字段（缺 email/phone/photo_url）+ extra |
| `SearchResponse` | 搜索端点包装 | total, results |
| `CollegeStats` | 单个学院统计 | name, count |
| `StatsResponse` | 统计端点响应 | total_teachers, colleges |

#### root suda_ir 中的相关模块

| 模块 | 内容 |
|------|------|
| `suda_ir/models.py` | `TeacherDoc` dataclass（11字段，缺 email/phone/photo_url） |
| `suda_ir/ir/tokenizer.py` | 中英文分词，支持 jieba 降级到 bigram |
| `suda_ir/ir/index.py` | `BM25Index` + `SearchResult` dataclass（与 domain 重复） |
| `suda_ir/ir/searcher.py` | `TutorSearcher`，封装 BM25Index，支持 name/college/all 三种 field |
| `suda_ir/data/storage.py` | `load_jsonl` / `save_jsonl`，读写 `TeacherDoc` JSONL |

### 1.2 问题

1. `TeacherDoc` 重复定义：`domain/teacher.py`（14字段）vs `suda_ir/models.py`（11字段）
2. `SearchResult` 重复定义：`domain/search.py` vs `suda_ir/ir/index.py`
3. API 层手动逐字段拷贝 domain dataclass → Pydantic schema
4. Engine 基类放在 `app/core/engine.py` 内部，`suda_ir` 模块无法方便导入
5. 无 Engine 注册机制，`deps.py` 硬编码 `SearchEngineStub`
6. BM25 未接入后端

## 二、目标架构

```
backend/
  domain/                          ← dataclass 模型，Engine ↔ 后端沟通的契约
    teacher.py                     ← TeacherDoc（不变）
    search.py                      ← SearchResult（不变）

  engine/                          ← 引擎子包（从 app/core/engine.py 提取）
    __init__.py                    ← SearchEngineBase ABC + register_engine + get_engine_class + list_engines
    bm25.py                        ← BM25Engine，@register_engine("bm25")
    stub.py                        ← SearchEngineStub，@register_engine("stub")

  suda_ir/                         ← 从 root suda_ir/ 复制，改为导入 domain 模型
    __init__.py                    ← 空
    tokenizer.py                   ← 原样复制
    index.py                       ← BM25Index，导入 domain.search.SearchResult
    searcher.py                    ← TutorSearcher，导入 domain.search.SearchResult
    storage.py                     ← load_jsonl/save_jsonl，导入 domain.teacher.TeacherDoc

  app/
    schemas/
      models.py                    ← Pydantic 模型 + from_* 工厂方法
    core/
      config.py                    ← 不变
      deps.py                      ← per-engine 单例，从 engine 包选择引擎
    api/
      search.py                    ← 用 TeacherResult.from_search_result()
      teacher.py                   ← 用 TeacherDetail.from_teacher_doc()
      stats.py                     ← 仅改 imports
    main.py                        ← 不变

  run.py                           ← 不变
```

### 设计原则

- **domain 层**（dataclass）：Engine 与后端沟通的唯一契约。所有 Engine 实现的输入输出都使用 `domain.teacher.TeacherDoc` 和 `domain.search.SearchResult`。
- **engine 层**（独立子包）：ABC + 注册表 + 具体引擎实现。放在 `backend/engine/` 而非 `app/core/` 内部，便于 `suda_ir` 等模块直接导入基类。
- **schemas 层**（Pydantic）：仅用于 API 响应序列化，位于 `app/schemas/models.py` 内部。通过 `from_*` 工厂方法从 domain 模型转换。
- **suda_ir 层**：从 root `suda_ir/` 复制到 `backend/suda_ir/`，不定义自己的模型，统一导入 `domain` 中的定义。

## 三、详细步骤

### 步骤 1：保留 `backend/domain/` — 不改动

`domain/teacher.py` 和 `domain/search.py` 保持不变，作为唯一 dataclass 定义。

### 步骤 2：新建 `backend/engine/` 子包 — 引擎基类 + 注册表

**`backend/engine/__init__.py`**：

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from domain.teacher import TeacherDoc
from domain.search import SearchResult

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
```

### 步骤 3：新建 `backend/engine/bm25.py` — BM25Engine

```python
from suda_ir.searcher import TutorSearcher
from suda_ir.storage import load_jsonl
from domain.teacher import TeacherDoc
from domain.search import SearchResult
from engine import SearchEngineBase, register_engine


@register_engine("bm25")
class BM25Engine(SearchEngineBase):
    def __init__(self) -> None:
        self._docs: list[TeacherDoc] = []
        self._searcher: TutorSearcher | None = None

    def load(self, data_path: str) -> None:
        self._docs = load_jsonl(data_path)
        self._searcher = TutorSearcher(self._docs)

    def search(self, query: str, top_k: int = 10, field: str = "all") -> list[SearchResult]:
        if not self._searcher:
            return []
        return self._searcher.search(query, top_k=top_k, field=field)

    def get_teacher(self, doc_id: str) -> TeacherDoc | None:
        for doc in self._docs:
            if doc.doc_id == doc_id:
                return doc
        return None

    def list_teachers(self, college: str | None = None) -> list[TeacherDoc]:
        if college:
            return [d for d in self._docs if college in d.college]
        return list(self._docs)

    def get_stats(self) -> dict:
        from collections import Counter
        counts = Counter(d.college or "未知" for d in self._docs)
        return {
            "total_teachers": len(self._docs),
            "colleges": [{"name": k, "count": v} for k, v in counts.most_common()],
        }
```

### 步骤 4：新建 `backend/engine/stub.py` — SearchEngineStub

从 `app/core/deps.py` 中提取 `SearchEngineStub`，改用 `@register_engine("stub")` 装饰：

```python
import json
from pathlib import Path

from domain.teacher import TeacherDoc
from domain.search import SearchResult
from engine import SearchEngineBase, register_engine

MOCK_DATA_PATH = Path("mock/teachers.jsonl")


def _load_mock_docs() -> list[TeacherDoc]:
    docs: list[TeacherDoc] = []
    if MOCK_DATA_PATH.exists():
        with MOCK_DATA_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    docs.append(TeacherDoc.from_dict(json.loads(line)))
    return docs


@register_engine("stub")
class SearchEngineStub(SearchEngineBase):
    def __init__(self) -> None:
        self._docs: list[TeacherDoc] = []

    def load(self, data_path: str) -> None:
        self._docs = _load_mock_docs()

    def search(self, query: str, top_k: int = 10, field: str = "all") -> list[SearchResult]:
        # 原有逻辑不变
        ...

    def get_teacher(self, doc_id: str) -> TeacherDoc | None:
        # 原有逻辑不变
        ...

    def list_teachers(self, college: str | None = None) -> list[TeacherDoc]:
        # 原有逻辑不变
        ...

    def get_stats(self) -> dict:
        # 原有逻辑不变
        ...
```

### 步骤 5：复制 suda_ir 到 `backend/suda_ir/`

| 源文件 | 目标文件 | 改动 |
|--------|----------|------|
| `suda_ir/ir/tokenizer.py` | `backend/suda_ir/tokenizer.py` | 原样复制，不改 |
| `suda_ir/ir/index.py` | `backend/suda_ir/index.py` | 删除 `SearchResult` dataclass 定义；`from domain.teacher import TeacherDoc`；`from domain.search import SearchResult` |
| `suda_ir/ir/searcher.py` | `backend/suda_ir/searcher.py` | `from domain.search import SearchResult`；`from suda_ir.index import BM25Index` |
| `suda_ir/data/storage.py` | `backend/suda_ir/storage.py` | `from domain.teacher import TeacherDoc` |

`backend/suda_ir/__init__.py` 保持为空。

### 步骤 6：更新 `backend/app/schemas/models.py` — Pydantic + 工厂方法

```python
from __future__ import annotations

from pydantic import BaseModel, Field
from domain.teacher import TeacherDoc
from domain.search import SearchResult


class SearchRequest(BaseModel):
    q: str = Field(..., min_length=1, description="Search query")
    field: str = Field(default="all", description="Search field: all, name, college")
    top_k: int = Field(default=10, ge=1, le=100, description="Max results")
    college: str | None = Field(default=None, description="Filter by college name")


class TeacherResult(BaseModel):
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
    email: str = ""
    phone: str = ""
    photo_url: str = ""
    score: float = 0.0
    matched_terms: list[str] = []

    @classmethod
    def from_search_result(cls, r: SearchResult) -> "TeacherResult":
        d = r.doc.to_dict()
        return cls(**d, score=r.score, matched_terms=r.matched_terms)


class SearchResponse(BaseModel):
    total: int
    results: list[TeacherResult]


class TeacherDetail(BaseModel):
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
    email: str = ""
    phone: str = ""
    photo_url: str = ""
    extra: dict = {}

    @classmethod
    def from_teacher_doc(cls, doc: TeacherDoc) -> "TeacherDetail":
        return cls(**doc.to_dict())


class CollegeStats(BaseModel):
    name: str
    count: int


class StatsResponse(BaseModel):
    total_teachers: int
    colleges: list[CollegeStats]
```

改动点：
- `TeacherDetail` 补全 email / phone / photo_url
- `TeacherResult` 增加 `from_search_result()` 工厂方法
- `TeacherDetail` 增加 `from_teacher_doc()` 工厂方法

### 步骤 7：重写 `backend/app/core/deps.py` — per-engine 单例

```python
from __future__ import annotations

from engine import get_engine_class, SearchEngineBase

# per-engine 单例缓存
_engines: dict[str, SearchEngineBase] = {}


def get_engine(engine_name: str = "bm25", data_path: str | None = None) -> SearchEngineBase:
    """获取引擎单例。不同 engine_name 各自缓存一个实例。"""
    if engine_name not in _engines:
        from app.core.config import settings

        cls = get_engine_class(engine_name)
        engine = cls()
        engine.load(data_path or settings.DEFAULT_DATA_FILE)
        _engines[engine_name] = engine
    return _engines[engine_name]


# 触发注册：import 引擎模块，使 @register_engine 装饰器执行
import engine.bm25   # noqa: F401, E402
import engine.stub    # noqa: F401, E402
```

### 步骤 8：更新 API 层

**`backend/app/api/search.py`** — 替换手动字段拷贝：

```python
# 旧：
TeacherResult(
    doc_id=r.doc.doc_id, name=r.doc.name, college=r.doc.college,
    title=r.doc.title, research=r.doc.research, papers=r.doc.papers,
    profile=r.doc.profile, content=r.doc.content, url=r.doc.url,
    final_url=r.doc.final_url, email=r.doc.email, phone=r.doc.phone,
    photo_url=r.doc.photo_url, score=r.score, matched_terms=r.matched_terms,
)

# 新：
TeacherResult.from_search_result(r)
```

**`backend/app/api/teacher.py`** — 替换手动字段拷贝：

```python
# 旧 get_teacher：
TeacherDetail(
    doc_id=doc.doc_id, name=doc.name, college=doc.college, title=doc.title,
    research=doc.research, papers=doc.papers, profile=doc.profile,
    content=doc.content, url=doc.url, final_url=doc.final_url, extra=doc.extra,
)

# 新：
TeacherDetail.from_teacher_doc(doc)

# 旧 list_teachers（截断 profile）：
TeacherDetail(
    doc_id=d.doc_id, name=d.name, college=d.college, title=d.title,
    research=d.research, profile=(d.profile or "")[:300], url=d.url,
)

# 新（截断逻辑保留）：
td = TeacherDetail.from_teacher_doc(d)
td.profile = (td.profile or "")[:300]
td = td.model_copy(update={"profile": (d.profile or "")[:300]})
```

**`backend/app/api/stats.py`** — 仅改 imports（不变逻辑）。

## 四、文件变更清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 不变 | `backend/domain/teacher.py` | 唯一 TeacherDoc 定义 |
| 不变 | `backend/domain/search.py` | 唯一 SearchResult 定义 |
| **新建** | `backend/engine/__init__.py` | ABC + register_engine + get_engine_class + list_engines |
| **新建** | `backend/engine/bm25.py` | BM25Engine，@register_engine("bm25") |
| **新建** | `backend/engine/stub.py` | SearchEngineStub，@register_engine("stub") |
| **新建** | `backend/suda_ir/tokenizer.py` | 从 `suda_ir/ir/` 原样复制 |
| **新建** | `backend/suda_ir/index.py` | 从 `suda_ir/ir/` 复制，改 import 到 domain |
| **新建** | `backend/suda_ir/searcher.py` | 从 `suda_ir/ir/` 复制，改 import 到 domain |
| **新建** | `backend/suda_ir/storage.py` | 从 `suda_ir/data/` 复制，改 import 到 domain |
| **重写** | `backend/app/schemas/models.py` | 补全 TeacherDetail 字段 + from_* 工厂方法 |
| **重写** | `backend/app/core/deps.py` | per-engine 单例 + 触发注册 |
| **修改** | `backend/app/api/search.py` | 用 TeacherResult.from_search_result() |
| **修改** | `backend/app/api/teacher.py` | 用 TeacherDetail.from_teacher_doc() |
| **修改** | `backend/app/api/stats.py` | 仅改 imports |
| 删除 | `backend/app/core/engine.py` | 提取到 engine/ 包 |
| 不变 | `backend/app/core/config.py` | |
| 不变 | `backend/app/main.py` | |
| 不变 | `backend/run.py` | |

## 五、导入路径关系

```
domain.teacher.TeacherDoc  ←── engine/ (ABC, bm25, stub)
domain.search.SearchResult ←── engine/
                            ←── suda_ir/ (index, searcher, storage)
                            ←── app/schemas/models.py

engine.SearchEngineBase    ←── app/core/deps.py
engine.get_engine_class    ←── app/core/deps.py

app.schemas.models         ←── app/api/ (search, teacher, stats)
```

## 六、运行时执行流程

```
run.py 启动 uvicorn
  → app.main 加载
    → app.core.deps 触发 import engine.bm25, engine.stub
      → @register_engine 注册到 engine._REGISTRY

请求到达 /api/search?q=xxx
  → get_engine("bm25") → per-engine 单例缓存
    → BM25Engine.load("data/processed/.../xxx.jsonl")
      → suda_ir.storage.load_jsonl() → list[TeacherDoc]
      → suda_ir.searcher.TutorSearcher(docs)
  → engine.search(query, top_k, field)
    → TutorSearcher.search() → list[SearchResult]
  → TeacherResult.from_search_result(r) → Pydantic 序列化
  → SearchResponse 返回
```
