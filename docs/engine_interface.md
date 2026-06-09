# Engine 接口文档

## 架构概览

```
domain/                      dataclass 模型，Engine 的输入输出契约
  teacher.py                 TeacherDoc
  search.py                  SearchResult
  query.py                   EngineQuery

engine/                      引擎子包
  __init__.py                SearchEngineBase ABC + 注册表
  bm25.py                    BM25Engine（@register_engine("bm25")）
  stub.py                    SearchEngineStub（@register_engine("stub")）

app/core/deps.py             get_engine() — per-engine 单例工厂
app/schemas/models.py        FrontendQuery — 前端请求体，to_engine_query() 转换
```

## Domain 模型

### TeacherDoc

```python
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
    email: str = ""
    phone: str = ""
    photo_url: str = ""
    extra: dict[str, Any] = field(default_factory=dict)
```

所有 Engine 的 `get_teacher` / `list_teachers` 返回此类型。

### SearchResult

```python
@dataclass
class SearchResult:
    doc: TeacherDoc
    score: float
    matched_terms: list[str]
```

`search` 方法的返回元素。`score` 越高越相关，`matched_terms` 为命中词列表。

### EngineQuery

```python
@dataclass
class EngineQuery:
    query: str              # 用户输入的查询文本
    field: str = "all"      # 搜索范围："all" | "name" | "college"
    top_k: int = 10         # 最大返回数量
    college: str | None = None  # 按学院过滤（可选）
```

`search` 方法的输入参数。

## SearchEngineBase 接口

```python
class SearchEngineBase(ABC):
    @abstractmethod
    def load(self, data_path: str) -> None: ...

    @abstractmethod
    def search(self, query: EngineQuery) -> list[SearchResult]: ...

    @abstractmethod
    def get_teacher(self, doc_id: str) -> TeacherDoc | None: ...

    @abstractmethod
    def list_teachers(self, college: str | None = None) -> list[TeacherDoc]: ...

    @abstractmethod
    def get_stats(self) -> dict: ...
```

| 方法 | 说明 | 调用时机 |
|------|------|----------|
| `load` | 加载数据源，建立索引 | 引擎首次实例化时调用一次 |
| `search` | 根据 `EngineQuery` 执行搜索，返回按相关性降序排列的结果 | `POST /api/search` |
| `get_teacher` | 按 `doc_id` 精确查询单个教师，不存在返回 `None` | `GET /api/teachers/{doc_id}` |
| `list_teachers` | 列出全部教师，或按学院名子串过滤 | `GET /api/teachers` |
| `get_stats` | 返回统计信息，格式：`{"total_teachers": int, "colleges": [{"name": str, "count": int}]}` | `GET /api/stats` |

## 注册机制

使用 `@register_engine(name)` 装饰器将 Engine 子类注册到全局注册表：

```python
from engine import SearchEngineBase, register_engine

@register_engine("my_engine")
class MyEngine(SearchEngineBase):
    ...
```

注册后可通过 `get_engine("my_engine")` 获取实例。

已注册的引擎：

| 名称 | 类 | 说明 |
|------|------|------|
| `"bm25"` | `BM25Engine` | 基于 jieba 分词 + BM25 算法，支持 all/name/college/research/papers/title |
| `"optimized"` | `OptimizedEngine` | 字段级 BM25 + 查询扩展 + 姓名模糊匹配，支持 all/name/college/research/papers/title |
| `"stub"` | `SearchEngineStub` | 纯子串匹配，硬编码分数，用于开发测试 |

查看已注册引擎：`engine.list_engines()`。

## 单例工厂

`app/core/deps.py` 中的 `get_engine()` 为每种引擎维护独立的单例：

```python
def get_engine(engine_name: str = "bm25", data_path: str | None = None) -> SearchEngineBase:
```

- 不同 `engine_name` 各自缓存一个实例，互不干扰
- 首次调用时创建实例并执行 `load(data_path)`
- 后续调用返回已缓存的实例

新引擎注册后，需要在 `deps.py` 底部添加触发 import：

```python
import engine.bm25   # noqa: F401, E402
import engine.stub    # noqa: F401, E402
import engine.optimized  # noqa: F401, E402
import engine.my_engine  # noqa: F401, E402  ← 添加这一行
```

## 集成新引擎：完整步骤

以添加一个向量检索引擎为例：

### 1. 创建引擎文件

在 `backend/engine/` 下新建 `vector.py`：

```python
from __future__ import annotations

from domain.query import EngineQuery
from domain.search import SearchResult
from domain.teacher import TeacherDoc
from engine import SearchEngineBase, register_engine
from suda_ir.storage import load_jsonl


@register_engine("vector")
class VectorEngine(SearchEngineBase):
    def __init__(self) -> None:
        self._docs: list[TeacherDoc] = []
        self._index = None  # 你的向量索引

    def load(self, data_path: str) -> None:
        self._docs = load_jsonl(data_path)
        # 构建向量索引
        # self._index = build_vector_index(self._docs)

    def search(self, query: EngineQuery) -> list[SearchResult]:
        if not self._index:
            return []
        # 执行向量检索
        # results = self._index.search(query.query, top_k=query.top_k)
        # 按 query.field 和 query.college 过滤
        return results

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

### 2. 注册到 deps.py

编辑 `backend/app/core/deps.py`，在底部添加：

```python
import engine.vector  # noqa: F401, E402
```

### 3. 使用

```python
# 使用新引擎
engine = get_engine("vector", data_path="data/processed/teachers.jsonl")
results = engine.search(EngineQuery(query="自然语言处理", top_k=5))

# 或通过 API（需在请求中指定引擎，或修改默认引擎）
POST /api/search
{ "query": "自然语言处理", "top_k": 5 }
```

## API 数据流

```
前端 POST /api/search
  body: { query, field, top_k }
        ↓
app/api/search.py
  body → FrontendQuery (Pydantic)
  body.to_engine_query() → EngineQuery (dataclass)
        ↓
engine.search(eq) → list[SearchResult]
        ↓
TeacherResult.from_search_result(r) → Pydantic 模型
        ↓
SearchResponse { total, results } → JSON 响应
```
