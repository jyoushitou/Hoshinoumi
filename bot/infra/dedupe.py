# ===================== 记忆去重指纹（v7-B14/B15） =====================
# 写入时用它在 7 天窗口内判重；迁移脚本用它回填历史数据。

import hashlib
import re

_PUNCT = re.compile(r"[\s，。、,.!?！？：:；;\"'“”‘’（）()【】\[\]…—~～]+")


def normalize(text):
    """归一化：去标点空白、转小写、截断 80 字"""
    return _PUNCT.sub("", text or "").lower()[:80]


def dedupe_key(target_id, kind, text):
    """同一个人 + 同一类 + 同一句话 → 同一个 key"""
    raw = f"{target_id}|{kind or 'event'}|{normalize(text)}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()
