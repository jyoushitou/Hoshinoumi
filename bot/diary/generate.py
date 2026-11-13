# ===================== 日记生成 =====================
# 素材收集 → AI 生成 → 清理 → 落库 → 缓存
# 迁移自 diary.py（v5-R5）

import re
from datetime import datetime

from ..log import log_system, log_err, log_api
from ..core import ai_port
from . import cache
from .store import (
    get_diary_from_db, save_diary_to_db, get_events_by_date,
    get_dialogs_by_date, get_dates_with_events, count_diaries_of_target,
)


def _clean_diary_text(text: str) -> str:
    """清理 AI 输出：去除格式行、多余空行、限制长度"""
    if not text:
        return text

    lines = []
    for line in text.strip().split("\n"):
        stripped = line.strip()
        # 跳过 AI 可能输出的格式行
        if stripped.startswith("关键词搜索图片用") or stripped.startswith("关键词提炼") or stripped.startswith("事件摘要"):
            continue
        if stripped.startswith("（无）") or stripped == "(无)":
            continue
        lines.append(stripped)

    cleaned = "\n".join(lines)
    # 合并多余空行
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    # 安全阀：限制 2000 字
    if len(cleaned) > 2000:
        cleaned = cleaned[:2000] + "..."
    return cleaned


def _build_diary_prompt(date_str, events, dialogs):
    """把当天事件/对话拼成日记提示词（v19.5 从 generate_diary 拆出）"""
    event_lines = []
    for summary, tags in events:
        tag_str = f" [{tags}]" if tags else ""
        event_lines.append(f"- {summary}{tag_str}")
    event_text = "\n".join(event_lines)

    dialog_lines = []
    for user_msg, response_text in dialogs[:8]:
        if user_msg:
            dialog_lines.append(f"主人: {user_msg[:100]}")
        if response_text:
            dialog_lines.append(f"奈绪: {response_text[:100]}")
    dialog_text = "\n".join(dialog_lines)

    user_prompt = (
        f"日期：{date_str}\n"
        f"\n【当天事件记录】\n{event_text}\n"
        f"\n【当天对话片段】\n{dialog_text if dialog_text else '（无对话记录）'}"
    )
    system_prompt = (
        "你是友利奈绪（Tomori Nao），一个傲娇毒舌但内心温柔的二次元少女。\n"
        "请根据下面提供的事件记录和对话片段，以第一人称视角写一篇完整的日记。\n"
        "要求：\n"
        "1. 以日期自然开头（如'今天''X月X日'），像人类日记一样叙事\n"
        "2. 全文至少200字，是一篇有开头、正文、结尾的完整文章\n"
        "3. 自然地融入事件和对话细节，不要列清单\n"
        "4. 偶尔带出性格特点（'哼''笨蛋主人'等），但不要过度\n"
        "5. 行文流畅、口语化、有温度，体现对主人的关心\n"
        "6. 直接输出日记正文，不要任何前缀、标题、格式行、表情符号"
    )
    return system_prompt, user_prompt, event_text


async def generate_diary(target_id: str, date_str: str, force: bool = False):
    """生成指定日期的奈绪视角日记（一篇文章样式，200字以上）

    流程：查缓存 → 查库 → 收集素材 → AI 生成 → 保存 → 返回
    参数 force=True 时跳过缓存/数据库，强制重新生成
    无事件记录时返回友好提示（不生成）
    """
    # ---- 参数校验 ----
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return "❌ 日期格式错误，请用 YYYY-MM-DD 格式"

    cache_key = f"{target_id}_{date_str}"

    # ---- 1. 非强制时查内存缓存 ----
    if not force:
        cached_text = cache.get(cache_key)
        if cached_text:
            log_api(f"[diary] 命中缓存: {cache_key}")
            return cached_text

    # ---- 2. 非强制时查数据库（已存在的直接读取） ----
    if not force:
        db_text = get_diary_from_db(target_id, date_str)
        if db_text:
            cache.put(cache_key, db_text)
            log_api(f"[diary] 命中数据库: {cache_key}")
            return db_text

    # ---- 3. 收集素材：当天事件 + 当天对话片段 ----
    events = get_events_by_date(target_id, date_str)
    dialogs = get_dialogs_by_date(target_id, date_str)

    # ---- 4. 无事件记录 → 友好提示，不生成 ----
    if not events:
        log_system(f"日记({date_str}): {target_id} 当天无事件记录，跳过 AI 生成")
        return f"📭 {date_str} 没有事件记录，暂时无法生成日记。"

    # ---- 5. 构造 AI 提示词 ----
    system_prompt, user_prompt, event_text = _build_diary_prompt(date_str, events, dialogs)
    msgs = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # ---- 6. 调用 AI 生成（双模型兜底，max_tokens 1500 保证 200 字以上） ----
    log_system(f"日记({date_str}): 开始 AI 生成（事件{len(events)}条，对话{len(dialogs)}条）")
    diary_text = await ai_port.generate_text(
        msgs, max_tokens=1500, target_id=target_id)

    # ---- 7. 清理 AI 输出 ----
    diary_text = _clean_diary_text(diary_text)

    # ---- 8. AI 生成失败降级：返回事件纪要 ----
    if not diary_text or len(diary_text.strip()) < 20:
        log_err(f"日记 AI 生成失败({target_id}, {date_str})，降级为事件纪要")
        diary_text = f"（AI 生成失败，以下为 {date_str} 事件纪要）\n{event_text}"

    # ---- 9. 保存到数据库 ----
    save_diary_to_db(target_id, date_str, diary_text)

    # ---- 9.5 v9-U11：日记回流成记忆，并留下一点情绪余韵 ----
    try:
        from ..life.reflow import reflow
        reflow(date_str, diary_text)
    except Exception as e:
        log_api(f"日记回流失败: {e}")

    # ---- 10. 更新缓存 ----
    cache.put(cache_key, diary_text)

    log_system(f"日记({date_str}) 已生成并保存（{len(diary_text)}字）")
    return diary_text


async def generate_missing_7day_diaries(target_id: str):
    """追溯生成：diaries 表为空但 events 有历史事件时，为最近 7 个日期各生成一篇
    返回 (已生成日期列表, 跳过日期列表)"""
    # 1. 若该目标已有任何日记记录，则跳过追溯（避免重复消耗 AI）
    if count_diaries_of_target(target_id) > 0:
        log_system(f"日记追溯：{target_id} 已有历史日记，跳过追溯生成")
        return [], []

    # 2. 追溯最近有事件记录的 7 个日期
    targets = get_dates_with_events(target_id, limit=7)
    if not targets:
        log_system(f"日记追溯：{target_id} 的 events 表无任何记录，跳过")
        return [], []

    log_system(f"日记追溯：{target_id} diaries 表为空但 events 有 {len(targets)} 个有记录的日期，开始生成")

    generated = []
    skipped = []
    for d in targets:
        # 逐天生成（generate_diary 内部会保存到 diaries 表）
        try:
            text = await generate_diary(target_id, d)
            if text and not text.startswith("📭"):
                generated.append(d)
                log_system(f"  追溯日记 {d}: {text[:40]}...")
            else:
                skipped.append(d)
        except Exception as e:
            log_err(f"追溯日记生成失败({d}): {e}")
            skipped.append(d)

    log_system(f"日记追溯完成：生成 {len(generated)} 篇，跳过 {len(skipped)} 篇")
    return generated, skipped

