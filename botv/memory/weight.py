# ===================== 记忆分量判定（v18.0 U2） =====================
# 「你妈住院了」和「今天吃了面」不该一样重。
#
# 先规则、后模型：
#   1. 关键词命中 → 直接定档（快、免费、可测）
#   2. 规则拿不准 → 交给调用方决定是否问模型（这里不调）
#
# 三档：
#   heavy  0.9 —— 亲人/重病/离世/分手/结婚/怀孕/手术/搬家（长期）
#   medium 0.6 —— 工作/学业/考试/吵架/承诺/借钱/面试
#   light  0.3 —— 其余（吃什么、天气、随口吐槽）

import re

TIERS = ("light", "medium", "heavy")
WEIGHTS = {"light": 0.3, "medium": 0.6, "heavy": 0.9}

# 关键词按「从重到轻」匹配，命中重的就不再往下看
_RULES = [
    ("heavy", (
        "去世", "离世", "过世", "走了", "葬礼", "火化",
        "癌症", "肿瘤", "手术", "住院", "病危", "确诊",
        "分手", "离婚", "出轨", "背叛",
        "结婚", "婚礼", "领证", "怀孕", "生了个", "生了",
        "爸爸", "妈妈", "爸", "妈", "爷爷", "奶奶", "外婆", "外公",
        "亲人", "家里出事", "自杀", "抑郁",
    )),
    ("medium", (
        "工作", "上班", "加班", "辞职", "被裁", "裁员", "失业",
        "面试", "考试", "考研", "高考", "挂科", "论文", "答辩",
        "吵架", "冷战", "道歉", "和好", "借钱", "还钱",
        "搬家", "搬走", "出差", "异地",
        "答应", "承诺", "约定", "说好",
    )),
]

# 明确「轻」的信号：有这些词且没有重/中关键词，压到 light
_LIGHT_HINTS = ("吃了", "好吃", "天气", "下雨", "无聊", "好累", "困", "睡")

_PUNCT = re.compile(r"[\s，。！？、,.!?~～…·\-—_（）()\[\]【】\"'“”‘’:：;；]+")


def _clean(text):
    return _PUNCT.sub("", text or "")


def classify(text):
    """返回 (tier, weight, 命中词)；纯函数，不碰数据库

    >>> classify("我妈住院了")
    ('heavy', 0.9, '住院')
    >>> classify("今天吃了碗面")
    ('light', 0.3, '')
    """
    s = _clean(text)
    if not s:
        return "light", WEIGHTS["light"], ""

    for tier, words in _RULES:
        for w in words:
            if w in s:
                return tier, WEIGHTS[tier], w

    return "light", WEIGHTS["light"], ""


def bump(current, tier):
    """已经存在的记忆被再次提起时，往上抬一档（最多 heavy）"""
    order = {t: i for i, t in enumerate(TIERS)}
    cur = current if current in order else "light"
    target = tier if tier in order else "light"
    final = TIERS[max(order[cur], order[target])]
    return final, WEIGHTS[final]


def describe(tier):
    """给人看的一行"""
    return {"heavy": "重（长期保留）", "medium": "中（90 天）",
            "light": "轻（7 天）"}.get(tier, "未定")
