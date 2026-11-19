# ===================== 周计划表（v35.2.21/22） =====================
# 后端解析教务 HTML + 按周存 JSON；插件点格子/导入共用同一份数据。
from __future__ import annotations

import html
import json
import os
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT / "data" / "weekly_plans"

PERIODS = [
    (1, 2, "上午第1-2节"),
    (3, 4, "上午第3-4节"),
    (5, 6, "下午第5-6节"),
    (7, 7, "下午第7节"),
    (8, 8, "下午第8节"),
    (9, 10, "晚上第9-10节"),
    (11, 11, "晚上第11节"),
]

WEEKDAYS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text or "")
    return html.unescape(text).replace("\xa0", " ").strip()


def _week_numbers(raw: str):
    """把 3-5,7 / 8-17 / 1-2,9-14 展开成周次集合。"""
    weeks = set()
    for part in re.split(r"[,，、;；\s]+", raw or ""):
        m = re.match(r"^(\d+)\s*-\s*(\d+)$", part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if a <= b and b - a <= 60:
                weeks.update(range(a, b + 1))
            continue
        if part.isdigit():
            weeks.add(int(part))
    return sorted(weeks)


def _week_range(raw: str):
    nums = _week_numbers(raw)
    return (nums[0], nums[-1]) if nums else (None, None)


def _parse_dl(block: str):
    """解析一个 dl：dt 课程名，dd 教师，dd 周次/地点。"""
    m = re.search(r"<dt[^>]*>(.*?)</dt>(.*?)</dl>", block, re.S | re.I)
    if not m:
        return None
    name = _clean(m.group(1))
    dds = re.findall(r"<dd[^>]*>(.*?)</dd>", m.group(2), re.S | re.I)
    teacher = _clean(dds[0]) if dds else ""
    raw = _clean(dds[1]) if len(dds) > 1 else ""
    location = ""
    lm = re.search(r"[（(]([^）)]*)[）)]", raw)
    if lm:
        location = lm.group(1).strip()
    prefix = re.split(r"[（(]", raw)[0].strip()
    weeks = _week_numbers(prefix)
    return {"name": name, "teacher": teacher, "location": location,
            "weeks_raw": raw, "weeks": weeks, "start_week": weeks[0] if weeks else None,
            "end_week": weeks[-1] if weeks else None}


def parse_html(text: str):
    """解析教务系统 KebiaoTable1；返回课程条目（含星期/节次）。"""
    text = text or ""
    table = re.search(r"<table[^>]*id=[\"']KebiaoTable1[\"'][^>]*>(.*?)</table>", text, re.S | re.I)
    body = table.group(1) if table else text
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", body, re.S | re.I)
    out = []
    for row in rows:
        day_m = re.search(r"Sjd([0-9])([0-9])", row, re.I)
        if not day_m:
            continue
        day = int(day_m.group(1)) + 1
        if day < 1 or day > 7:
            continue
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S | re.I)
        # 第一格是星期标签，后面依次 7 个节次
        for idx, cell in enumerate(cells[1:8]):
            if idx >= len(PERIODS):
                break
            p_start, p_end, _label = PERIODS[idx]
            for block in re.findall(r"<dl[^>]*>(.*?)</dl>", cell, re.S | re.I):
                item = _parse_dl("<dl>" + block + "</dl>")
                if not item or not item["name"]:
                    continue
                item.update({
                    "weekday": day,
                    "weekday_name": WEEKDAYS[day - 1],
                    "period_start": p_start,
                    "period_end": p_end,
                    "source": "jwc_html",
                })
                out.append(item)
    # 去重（同一课程同一格可能重复 dl）
    seen = set()
    uniq = []
    for x in out:
        key = (x["weekday"], x["period_start"], x["name"], x["weeks_raw"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(x)
    return uniq


def _uid_dir(uid: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", str(uid or "owner"))[:80] or "owner"
    d = DATA_ROOT / safe
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_week(uid: str, week: int):
    p = _uid_dir(uid) / f"week-{int(week)}.json"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_week(uid: str, week: int, courses):
    p = _uid_dir(uid) / f"week-{int(week)}.json"
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(courses, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, p)
    return p


def import_html(uid: str, text: str, week: int, dry_run: bool = False):
    all_courses = parse_html(text)
    selected = [x for x in all_courses if not x["weeks"] or int(week) in x["weeks"]]
    # 同一格同一课程去重；保留周次信息
    seen = set()
    rows = []
    for x in selected:
        key = (x["weekday"], x["period_start"], x["name"], x["weeks_raw"])
        if key in seen:
            continue
        seen.add(key)
        rows.append(x)
    if not dry_run:
        save_week(uid, week, rows)
    return rows, len(all_courses)
