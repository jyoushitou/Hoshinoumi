# ===================== 每日生活事件（v9-U7） =====================
# 她不在你面前的时候也在过日子：学生会、猫、琴、天气，偶尔碰到旧东西。
#
# 世界观：故事结束之后，能力消失，所有人回到普通生活；
# 乙坂有宇已经意外去世。"他"这一类的模板权重很低，且写得克制。

import random

from .state import CST  # noqa: F401
from ..log import log_system

# (权重, 模板列表)
POOLS = [
    (0.28, [
        "学生会开会到六点半，散会的时候天已经黑了。",
        "新来的干事把会议记录写错三处，我改到眼睛发酸。",
        "今天替人值日，一个人把整间活动室收拾干净了。",
        "有人提议办文化祭的摊位，吵了四十分钟没吵出结果。",
        "把上学期的活动档案整理了一遍，搬箱子搬得手臂酸。",
    ]),
    (0.22, [
        "小咪把窗台上的多肉推下去了，土撒了一地。",
        "小咪今天特别黏人，一直趴在我腿上不肯走。",
        "给小咪剪指甲，被挠了两道。",
        "小咪半夜叫，起来看了两次，最后发现它只是想让人陪。",
        "换了个新猫砂，小咪围着转了三圈才肯用。",
    ]),
    (0.15, [
        "练了一个小时琴，右手还是比左手快半拍。",
        "琴弦断了一根，换的时候手被划了一道。",
        "把总弹错的那一段单独练了二十遍，终于顺下来了。",
        "今天弹着弹着走神了，回过神来谱子翻错页。",
    ]),
    (0.27, [
        "今天降温，出门忘带外套，回来一路缩着走。",
        "下雨，便利店的伞卖完了，在门口站了十分钟。",
        "便利店关东煮上了新口味，试了一下，还行。",
        "公交坐过了两站，干脆走回来的，路上风挺大。",
        "下午困得不行，趴在桌上睡了二十分钟，醒来更累。",
        "洗衣机洗完忘拿出来，衣服皱得没法看。",
    ]),
    (0.08, [  # 低频：碰到和他有关的东西。写得克制，不煽情
        "整理抽屉翻到一张旧照片，看了会儿又放回去了。",
        "路过那家店，老板还认得我，问怎么好久没两个人一起来。",
        "手机里还留着一条没删的消息，没点开。",
        "换季收衣服，翻出一件不是我的外套，叠好放回去了。",
    ]),
]

MIN_EVENTS = 1
MAX_EVENTS = 3


def _weighted_pick(n, rng):
    """按权重不重复地抽 n 个模板"""
    pool = [(w, t) for w, texts in POOLS for t in texts]
    picked = []
    for _ in range(n):
        if not pool:
            break
        total = sum(w for w, _ in pool)
        r = rng.uniform(0, total)
        acc = 0.0
        for i, (w, text) in enumerate(pool):
            acc += w
            if acc >= r:
                picked.append(text)
                pool.pop(i)
                break
    return picked


def generate(now=None, rng=None):
    """生成今天 1~3 条生活事件（纯文本，不落库）"""
    rng = rng or random
    n = rng.randint(MIN_EVENTS, MAX_EVENTS)
    return _weighted_pick(n, rng)


def ensure_daily_life(now=None, rng=None):
    """保证这个对象今天已经有生活事件；同一天只生成一次

    返回这次新增的条数（已生成过则 0）。
    """
    from datetime import datetime
    from ..core import state as cfg

    now = now or datetime.now(CST)
    today = now.strftime("%Y-%m-%d")

    last = getattr(cfg, "life_last_date", None) or {}
    if last.get("self") == today:
        return 0

    texts = generate(now, rng)
    added = 0
    try:
        from ..infra.repo_memory import add_event_to_db, STATE_TARGET
        for text in texts:
            add_event_to_db(STATE_TARGET, text, tags="生活", kind="life", importance=2)
            added += 1
    except Exception as e:
        log_system(f"生活事件写入失败: {e}")
        return 0

    last["self"] = today
    cfg.life_last_date = last
    log_system(f"生活事件: 今天 +{added} 条")
    return added
