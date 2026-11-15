# ===================== 运行时配置中心（v25.0） =====================
# 优先级：代码默认值 < config.local.json(app.*) < 环境变量 NAO_* < !config 运行时
# 任何一层非法/越界都回退上一层，最终保证默认值可用。

import json
import logging
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_FILE = os.path.join(ROOT, "config.local.json")

# key -> (默认值, 最小值, 最大值, 说明)
SPEC = {
    "memory.max_user_round": (50, 10, 200, "每个对象保留的对话轮数"),
    "memory.digest_rounds": (10, 1, 50, "每多少轮溢出对话写一条浓缩"),
    "summary.max_tokens": (1024, 128, 4096, "读书摘要最大输出 token"),
    "reading.chunk_chars": (1000, 200, 5000, "本地阅读每次读取字数"),
    "context.memory_budget": (250, 100, 4000, "注入上下文的记忆预算字数"),
}
ENV = {
    "memory.max_user_round": "NAO_MAX_USER_ROUND",
    "memory.digest_rounds": "NAO_DIGEST_ROUNDS",
    "summary.max_tokens": "NAO_SUMMARY_MAX_TOKENS",
    "reading.chunk_chars": "NAO_READ_CHUNK_CHARS",
    "context.memory_budget": "NAO_MEMORY_BUDGET",
}

_values = {}
_sources = {}
_loaded = False
_log = logging.getLogger("appconfig")


def default(key):
    return SPEC[key][0]


def _valid(key, raw):
    try:
        value = int(str(raw).strip())
    except Exception:
        return None
    lo, hi = SPEC[key][1], SPEC[key][2]
    return value if lo <= value <= hi else None


def _file_values():
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            data = json.load(f) or {}
    except Exception as e:
        _log.warning("config.local.json 读取失败：%s", e)
        return {}
    app = data.get("app") or {}
    if not isinstance(app, dict):
        return {}
    out = {}
    for k, raw in app.items():
        if k in SPEC:
            v = _valid(k, raw)
            if v is not None:
                out[k] = v
            else:
                _log.warning("配置 %s=%r 非法，忽略", k, raw)
    return out


def load(force=False):
    """重新计算生效值；force=True 用于 !reload / 文件热加载。"""
    global _loaded
    if _loaded and not force:
        return _values
    _values.clear()
    _sources.clear()
    for k in SPEC:
        _values[k] = SPEC[k][0]
        _sources[k] = "default"
    for k, v in _file_values().items():
        _values[k] = v
        _sources[k] = "config"
    for k, env in ENV.items():
        raw = os.getenv(env)
        if raw is None or str(raw).strip() == "":
            continue
        v = _valid(k, raw)
        if v is None:
            _log.warning("环境变量 %s=%r 非法，忽略", env, raw)
            continue
        _values[k] = v
        _sources[k] = "env"
    _loaded = True
    return _values


def get(key, default_value=None):
    if not _loaded:
        load()
    if key not in SPEC:
        return default_value
    return _values.get(key, SPEC[key][0])


def source(key):
    if not _loaded:
        load()
    return _sources.get(key, "default")


def set_runtime(key, raw):
    """运行时覆盖；只影响当前进程，不落盘。"""
    if key not in SPEC:
        return False, f"没有这个配置：{key}"
    v = _valid(key, raw)
    if v is None:
        return False, f"值越界：{key} 应在 {SPEC[key][1]}–{SPEC[key][2]}"
    if not _loaded:
        load()
    _values[key] = v
    _sources[key] = "runtime"
    return True, f"{key} = {v}（{SPEC[key][3]}）"


def reload():
    return load(force=True)


def all_items():
    if not _loaded:
        load()
    return [(k, _values[k], SPEC[k][0], _sources[k], SPEC[k][3]) for k in SPEC]
