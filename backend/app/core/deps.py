from __future__ import annotations

from app.core.config import settings
from engine import SearchEngineBase, get_engine_class

_engines: dict[tuple[str, str], SearchEngineBase] = {}


def get_engine(engine_name: str = "bm25", data_path: str | None = None) -> SearchEngineBase:
    """获取引擎单例。不同引擎和数据源各自缓存一个实例。"""
    resolved_data_path = data_path or settings.DEFAULT_DATA_FILE
    cache_key = (engine_name, resolved_data_path)
    if cache_key not in _engines:
        cls = get_engine_class(engine_name)
        engine = cls()
        engine.load(resolved_data_path)
        _engines[cache_key] = engine
    return _engines[cache_key]


# 触发注册：import 引擎模块，使 @register_engine 装饰器执行
import engine.bm25  # noqa: F401, E402
import engine.optimized  # noqa: F401, E402
import engine.stub  # noqa: F401, E402
