# ===================== 可调参数（v15） =====================
# 这些参数以前写死在各个模块里，改一次要重启。
# 现在集中在这里：可以运行时改，改完立刻生效，并持久化到 data/tunables.json。

import json
import os

from ..log import log_api, log_system

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(ROOT, "data")
STORE = os.path.join(DATA_DIR, "tunables.json")

# 名字 → (默认值, 说明, 类型)
SPEC = {
    "group_base_prob": (0.20, "群聊没被@时的接话概率", float),
    "group_mention_prob": (0.75, "群里被@时的回话概率", float),
    "image_prob": (0.30, "私聊回复配图的概率", float),
    "image_cooldown": (600, "同一个人两次配图的最小间隔（秒）", int),
    "voice_prob": (0.08, "回复变语音的概率", float),
    "lonely_threshold": (0.45, "孤独到多少才主动开口", float),
    "proactive_cap": (3, "每天主动消息上限", int),
    "delay_scale": (1.0, "回复延迟的整体倍率（0.5=快一倍）", float),
}

_values = {}


def _coerce(value, kind):
    if kind is int:
        return int(float(value))
    return float(value)


def load():
    """启动时读盘；坏数据忽略"""
    global _values
    _values = {k: v[0] for k, v in SPEC.items()}
    try:
        with open(STORE, encoding="utf-8") as f:
            saved = json.load(f)
        for k, v in (saved or {}).items():
            if k in SPEC:
                _values[k] = _coerce(v, SPEC[k][2])
    except Exception:
        pass
    log_system(f"可调参数: {len(_values)} 项（{len(_values)}）")


def get(name, default=None):
    """取参数；没加载过就懒加载"""
    if not _values:
        load()
    if name in _values:
        return _values[name]
    return default if default is not None else SPEC.get(name, (None,))[0]


def set_value(name, value):
    """改一个参数并落盘；返回 (ok, 说明)"""
    if name not in SPEC:
        return False, f"没有这个参数：{name}"
    _default, desc, kind = SPEC[name]
    try:
        new = _coerce(value, kind)
    except Exception:
        return False, f"值不对：{value}（要 {kind.__name__}）"

    # 概率类夹在 0~1，倍率夹在 0.1~5
    if kind is float and "prob" in name:
        new = max(0.0, min(1.0, new))
    if name == "delay_scale":
        new = max(0.1, min(5.0, new))
    if name in ("image_cooldown", "proactive_cap"):
        new = max(0, new)

    _values[name] = new
    _save()
    log_api(f"[参数] {name} = {new}")
    return True, f"{name} = {new}（{desc}）"


def _save():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(STORE, "w", encoding="utf-8") as f:
            json.dump(_values, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log_api(f"[参数] 保存失败: {e}")


def all_items():
    """[(名字, 当前值, 说明)]"""
    if not _values:
        load()
    return [(k, _values[k], v[1]) for k, v in SPEC.items()]
