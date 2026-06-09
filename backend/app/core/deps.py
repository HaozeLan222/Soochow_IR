from __future__ import annotations

from engine import SearchEngineBase, get_engine_class

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
import engine.bm25  # noqa: F401, E402
import engine.stub  # noqa: F401, E402
