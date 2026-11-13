# ===================== 角色卡加载（v14-A1/A2） =====================
# 人设从代码里剥出来，放进 personas/<名字>/：
#
#   prompt.txt      主提示词（保留 {now} {tone} 等占位符）
#   supplement.txt  人设补充
#   life.txt        生活事件模板（# weight 0.25 分组）
#   state.json      状态基线 mood/energy/lonely
#
# 选择顺序：NAO_PERSONA 环境变量 → 默认 nao → 内置代码。
# 任何一项读不到就用内置默认值，加载失败不崩。

import json
import os

from ..log import log_api, log_system

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CARD_ROOT = os.path.join(ROOT, "personas")
DEFAULT_CARD = "nao"
DEFAULT_WEIGHT = 0.2


ACTIVE_FILE = os.path.join(CARD_ROOT, ".active")


def available_cards():
    """列出所有可用的角色卡（目录名）"""
    try:
        return sorted(
            n for n in os.listdir(CARD_ROOT)
            if os.path.isdir(os.path.join(CARD_ROOT, n)) and not n.startswith(".")
        )
    except Exception:
        return []


def _saved_name():
    try:
        with open(ACTIVE_FILE, encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def save_active(name):
    """记住切换结果（重启也生效）"""
    try:
        with open(ACTIVE_FILE, "w", encoding="utf-8") as f:
            f.write(name)
        return True
    except Exception:
        return False


def active_name():
    """当前角色名：运行时覆盖 > 持久化 > 环境变量 > 默认"""
    from ..core import state as cfg
    for name in (getattr(cfg, "persona_name", ""), _saved_name(),
                 os.getenv("NAO_PERSONA") or "", DEFAULT_CARD):
        name = (name or "").strip()
        if name and os.path.isdir(os.path.join(CARD_ROOT, name)):
            return name
    return DEFAULT_CARD


def card_dir():
    """当前生效的卡片目录；不存在就返回默认目录"""
    name = active_name()
    path = os.path.join(CARD_ROOT, name)
    if os.path.isdir(path):
        return path
    fallback = os.path.join(CARD_ROOT, DEFAULT_CARD)
    if os.path.isdir(fallback):
        if name != DEFAULT_CARD:
            log_api(f"[角色卡] 找不到 {name}，改用 {DEFAULT_CARD}")
        return fallback
    return None


def load_text(filename):
    """读卡片里的文本文件；读不到返回 None"""
    d = card_dir()
    if not d:
        return None
    path = os.path.join(d, filename)
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read().strip()
        return text or None
    except Exception:
        return None


def load_life():
    """读生活事件模板；返回 [(权重, [模板...]), ...] 或 None"""
    text = load_text("life.txt")
    if not text:
        return None
    pools = []
    weight = DEFAULT_WEIGHT
    current = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            if line.lower().startswith("# weight"):
                if current:
                    pools.append((weight, current))
                    current = []
                try:
                    weight = float(line.split()[-1])
                except Exception:
                    weight = DEFAULT_WEIGHT
            continue
        current.append(line)
    if current:
        pools.append((weight, current))
    return pools or None


def load_state_base():
    """读状态基线；读不到返回 None"""
    text = load_text("state.json")
    if not text:
        return None
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def describe():
    """日志用：当前用的是哪张卡"""
    d = card_dir()
    if not d:
        return "内置人设"
    return os.path.basename(d)


def log_current():
    log_system(f"角色卡: {describe()}（{card_dir() or '代码内置'}）")
