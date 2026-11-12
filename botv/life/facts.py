# ===================== 事实卡（v18.3） =====================
# 「没有早八」是**状态**，不是事件。事件靠检索，状态要**常驻**。
#
# 提取：规则优先（不花 token），抽不到就放弃（v18.3 不做模型打标）
# 存储：同 (target, slot, value) 覆盖，带 polarity / 时效
# 注入：每轮取未过期事实，最多 10 条，带日期语境

import re

from ..log import log_api

# slot 白名单（避免乱塞）
SLOTS = ("课程", "考试", "工作", "饮食", "作息")

# 中文数字 → 1..7（周一=1）
_WEEK = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "日": 7, "天": 7}

_NEG = ("没有", "没", "不用", "不上", "取消了", "放假")
_POS = ("有", "要", "得", "上")


# v18.4：隐私分级用词表（命中就降级）
_PRIVATE_WORDS = ("住院", "病", "手术", "去世", "离婚", "吵架", "工资", "借钱",
                  "裁员", "抑郁", "分手", "怀孕", "流产", "欠", "债")
_SECRET_WORDS = ("别告诉", "不要告诉", "保密", "秘密", "只告诉你")

_SUBJECT_RULES = (
    (r"我(妈|母亲)", "妈妈"),
    (r"我(爸|父亲)", "爸爸"),
    (r"我(爷|爷爷)", "爷爷"),
    (r"我(奶|奶奶)", "奶奶"),
    (r"我(外婆|姥姥)", "外婆"),
    (r"我(外公|姥爷)", "外公"),
    (r"我(哥|兄)", "哥哥"),
    (r"我(姐)", "姐姐"),
    (r"我(弟)", "弟弟"),
    (r"我(妹)", "妹妹"),
    (r"我(朋友|同学|同事)[\u4e00-\u9fa5]{0,3}", "朋友"),
)

def subject_of(text):
    """这句话在说谁：默认是说话人自己"""
    for pattern, name in _SUBJECT_RULES:
        if re.search(pattern, text or ""):
            return name
    return "自己"

def visibility_of(text, subject="自己"):
    """判断能不能公开说"""
    s = text or ""
    if any(w in s for w in _SECRET_WORDS):
        return "secret"
    if subject != "自己":
        # 关于别人的事，默认不公开
        return "private"
    if any(w in s for w in _PRIVATE_WORDS):
        return "private"
    return "group_ok"


def _clean(text):
    return (text or "").replace(" ", "").replace("　", "")


def _day_window(text, now):
    """从话里猜日期窗口，返回 (valid_from, valid_until, 日期说明)

    v18.3 只处理：今天 / 明天 / 后天 / 周X / 下周X / 没说
    """
    from datetime import datetime, timedelta

    def day_at(d, hour=0, minute=0, second=0):
        return datetime(d.year, d.month, d.day, hour, minute, second)

    def end_of_day(d):
        return day_at(d, 23, 59, 59)

    base = now or datetime.now()
    today = base.date()

    if "今天" in text or "今晚" in text:
        return day_at(today), end_of_day(today), "今天"
    if "明天" in text:
        d = today + timedelta(days=1)
        return day_at(d), end_of_day(d), "明天"
    if "后天" in text:
        d = today + timedelta(days=2)
        return day_at(d), end_of_day(d), "后天"

    if "下周" in text and not re.search(r"下周[一二三四五六日天]", text):
        # 只说「下周」不说周几：整周有效（下周一 0 点 ~ 下周日 23:59）
        today0 = today
        days_to_next_mon = (7 - today0.isoweekday()) + 1
        mon = today0 + timedelta(days=days_to_next_mon)
        sun = mon + timedelta(days=6)
        return day_at(mon), end_of_day(sun), "下周"

    m = re.search(r"(下周|周|星期)([一二三四五六日天])", text)
    if m:
        wd = _WEEK[m.group(2)]
        delta = (wd - today.isoweekday()) % 7
        if m.group(1) == "下周":
            delta += 7
        if delta == 0:
            delta = 7 if m.group(1) == "下周" else 0
        d = today + timedelta(days=delta)
        return day_at(d), end_of_day(d), f"周{m.group(2)}"

    # 没说日期：当作「最近一次」，当天有效
    return day_at(today), end_of_day(today), "今天"


def extract(text, now=None):
    """从一句话里抽事实卡；返回 list[dict]（可能空）

    >>> extract("明天没有早八", now) →
        [{"slot":"课程","value":"早八","polarity":0,...}]
    """
    s = _clean(text)
    if not s:
        return []
    # 疑问句不是陈述（「有课吗」不该存成事实）
    _q_end = ("吗", "呢", "？", "?")
    _q_start = ("有没有", "是不是", "要不要")
    if s.rstrip().endswith(_q_end) or s.startswith(_q_start):
        return []

    vf, vu, day_label = _day_window(s, now)
    subj = subject_of(s)
    vis = visibility_of(s, subj)
    out = []

    def add(slot, value, polarity, conf=0.7):
        out.append({
            "slot": slot, "value": value, "polarity": 1 if polarity else 0,
            "valid_from": vf, "valid_until": vu, "confidence": conf,
            "day_label": day_label,
            "subject": subj, "visibility": vis,
        })

    # ---- 家人近况（v18.4）：住院 / 手术 / 生病 → 默认 private ----
    if subj != "自己" and re.search(r"(住院|手术|生病|病|出院|去世)", s):
        m = re.search(r"(住院|手术|生病|出院|去世)", s)
        add("近况", m.group(1), 1, conf=0.8)
        for f in out:
            f["visibility"] = "secret" if vis == "secret" else "private"
            f["valid_until"] = None      # 近况不是「当天有效」
        return out

    # ---- 课程：早八 / 有课 / 没课 ----
    m = re.search(r"(早八|早课|第一节课)", s)
    if m:
        neg = any(w in s for w in _NEG) or re.search(r"(不用上|不上|取消)", s)
        add("课程", "早八", 0 if neg else 1)
        return out

    m = re.search(r"(有课|没课|没有课)", s)
    if m:
        add("课程", "课", 1 if m.group(1) == "有课" else 0)
        return out

    # ---- 考试 ----
    m = re.search(r"(考试|期末|补考|测验)", s)
    if m:
        add("考试", m.group(1), 1)
        return out

    # ---- 工作 ----
    if re.search(r"(上班|加班|值班|出差)", s):
        neg = any(w in s for w in ("不用", "不", "取消", "请假"))
        add("工作", "班", 0 if neg else 1)
        return out

    # ---- 饮食禁忌 ----
    m = re.search(r"(不吃|不能吃|忌口|过敏)[了]?([\u4e00-\u9fa5]{1,6})", s)
    if m:
        food = m.group(2)
        # 长期事实：不过期
        out.append({
            "slot": "饮食", "value": food, "polarity": 0,
            "valid_from": None, "valid_until": None,
            "confidence": 0.9, "day_label": "长期",
            "subject": subj, "visibility": vis,
        })
        return out

    return out


def describe(fact):
    """给人看的一行：「周四（11-13）没有早八」"""
    day = fact.get("day_label") or "最近"
    pol = "有" if int(fact.get("polarity") or 0) else "没有"
    return f"{day}{pol}{fact.get('value', '')}"


# ===================== 存储 =====================

def remember(tid, facts, cursor=None):
    """写事实卡（同 target/slot/value 覆盖）；返回写入条数"""
    if not facts:
        return 0
    owned = cursor is None
    c = cursor
    n = 0
    try:
        if c is None:
            from ..infra.conn import get_cursor

            c = get_cursor()
        for f in facts:
            try:
                # 同一条事实：先删旧的（确保 polarity/时效被覆盖）
                c.execute(
                    "DELETE FROM facts WHERE target_id=%s AND slot=%s AND value=%s",
                    (str(tid), f["slot"], f["value"]))
                c.execute(
                    "INSERT INTO facts(target_id, slot, value, subject, "
                    "visibility, polarity, valid_from, valid_until, "
                    "confidence, source) "
                    "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,'chat')",
                    (str(tid), f["slot"], f["value"],
                     f.get("subject", ""), f.get("visibility", "group_ok"),
                     f["polarity"], f.get("valid_from"),
                     f.get("valid_until"), f.get("confidence", 0.7)))
                n += 1
            except Exception as e:
                log_api(f"[事实] 写入失败（忽略）：{e}")
        c.connection.commit()
        return n
    except Exception as e:
        log_api(f"[事实] 存储失败：{e}")
        return n
    finally:
        if owned and c is not None:
            try:
                c.close()
            except Exception:
                pass


def active(tid, now=None, limit=10, cursor=None, group=False):
    """取未过期的事实（valid_until 为空或 >= 现在）"""
    from datetime import datetime

    now = now or datetime.now()
    owned = cursor is None
    c = cursor
    try:
        if c is None:
            from ..infra.conn import get_cursor

            c = get_cursor()
        sql = ("SELECT slot, value, subject, visibility, polarity, "
               "valid_from, valid_until, confidence "
               "FROM facts WHERE target_id=%s "
               "AND (valid_until IS NULL OR valid_until >= %s) ")
        if group:
            sql += "AND visibility='group_ok' "
        sql += "ORDER BY valid_until DESC, updated_at DESC LIMIT %s"
        c.execute(sql, (str(tid), now, int(limit)))
        return list(c.fetchall())
    except Exception as e:
        log_api(f"[事实] 读取失败：{e}")
        return []
    finally:
        if owned and c is not None:
            try:
                c.close()
            except Exception:
                pass


def prompt_block(tid, now=None, limit=10, group=False):
    """给 prompt 用的一段；没有事实返回空串"""
    rows = active(tid, now=now, limit=limit, group=group)
    if not rows:
        return ""
    from datetime import datetime

    now = now or datetime.now()
    parts = []
    for r in rows:
        subj = r.get("subject") or ""
        # 近况类带主语（「妈妈住院」），不用「有/没有」
        if r.get("slot") == "近况":
            v = r.get("value", "")
            parts.append(f"{subj or '她'}{v}")
            continue
        pol = "有" if int(r.get("polarity") or 0) else "没有"
        vu = r.get("valid_until")
        when = ""
        if vu:
            try:
                if hasattr(vu, "strftime"):
                    when = f"{vu.month}月{vu.day}日"
            except Exception:
                when = ""
        parts.append(f"{when}{pol}{r.get('value', '')}".strip())
    head = "【最近说过的安排】"
    if group:
        head += "（只提公事；下面没有的，你不知道，别人问起就像没听过一样岔开）"
    return head + "；".join(parts[:limit]) + "。"
