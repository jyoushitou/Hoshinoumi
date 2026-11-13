# ===================== 定时任务执行器（v17.6） =====================
# 钩子到点 → 投递 cron_task 事件 → 这里真正「说话」。
#
#   cron_task（P1，key=cron:<id>）
#        ↓ worker 执行
#   读任务 → 让模型按 content 组织一句话 → 发送 → 更新 last_fire/next_ts
#
# 两条纪律：
#   - 任务被删/停用 → 直接返回（钩子可能比删除晚一步）
#   - 发送失败 → 不重试（定时消息补发没意义，见计划「错过不补发」）

import time

from ..core import state as cfg
from ..events.base import Priority
from ..events.registry import register
from ..log import log_api, log_err, log_system
from ..core import clock

# v18.7：exact 任务提前 30 秒生成，到点直接发
_prepared = {}


@register("cron_prepare", priority=Priority.EVENT, timeout=120, retries=0,
          description="准点提醒的预生成（只生成不发送）")
async def handle_cron_prepare(ev):
    args = getattr(ev, "args", ()) or ()
    if not args:
        return {"ok": False}
    task_id = int(args[0])
    from ..schedule import cron

    try:
        task = cron.get(task_id)
    except Exception:
        return {"ok": False, "reason": "读任务失败"}
    if not task or not int(task.get("enabled") or 0):
        return {"ok": False, "reason": "任务不可用"}

    content = (task.get("content") or "").strip()
    try:
        if content.startswith("scene:"):
            from .schedule import generate_scene_reply
            rep = await generate_scene_reply(content.split(":", 1)[1].strip())
        else:
            from ..ai.client import get_character_reply
            rep = await get_character_reply(
                _PROMPT.format(content=content),
                str(task.get("target_id") or cfg.MASTER_QQ))
    except Exception as e:
        log_err(f"[定时] 预生成失败({task_id}): {e}")
        return {"ok": False, "reason": "生成失败"}

    if rep:
        _prepared[task_id] = (rep, time.time())
        log_api(f"[定时] 预生成完成：任务 {task_id}")
        return {"ok": True}
    return {"ok": False, "reason": "空回复"}

# content 前面加这句，让她以「提醒/告知」的语气说，而不是自言自语
_PROMPT = "（现在是你要主动提醒他的时间。要提醒的事：{content}。用一句话说出来，别解释为什么）"


@register("cron_task", priority=Priority.EVENT, timeout=90, retries=1,
          description="定时任务到点执行（提醒/告知）")
async def handle_cron_task(ev):
    """ev.args = (task_id,)"""
    from ..schedule import cron

    args = getattr(ev, "args", ()) or ()
    if not args:
        return {"ok": False, "reason": "没有任务 id"}
    task_id = int(args[0])

    try:
        task = cron.get(task_id)
    except Exception as e:
        log_err(f"[定时] 读任务失败({task_id}): {e}")
        return {"ok": False, "reason": "读任务失败"}

    if not task:
        log_api(f"[定时] 任务 {task_id} 已不存在，跳过")
        return {"ok": False, "reason": "任务不存在"}

    if not int(task.get("enabled") or 0):
        log_api(f"[定时] 任务 {task_id} 已停用，跳过")
        return {"ok": False, "reason": "已停用"}

    content = (task.get("content") or "").strip()
    if not content:
        return {"ok": False, "reason": "内容为空"}

    # v18.7：预生成的内容（180 秒内有效）
    prep = _prepared.pop(task_id, None)
    prepared = prep[0] if prep and time.time() - prep[1] < 180 else None

    # scene:xxx → 交给场景执行器（带提示词/配图），不是念一句话
    if content.startswith("scene:"):
        scene = content.split(":", 1)[1].strip()
        try:
            from .schedule import handle_schedule_scene

            class _Ev:
                kind = "schedule_scene"
                args = (scene,)

            out = await handle_schedule_scene(_Ev(), prepared=prepared)
            _mark(task_id, ok=bool(out.get("ok")))
            log_system(f"[定时] 场景 {scene} 已完成")
            return {"ok": bool(out.get("ok")), "scene": scene}
        except Exception as e:
            log_err(f"[定时] 场景 {scene} 执行失败: {e}")
            _mark(task_id, ok=False)
            return {"ok": False, "reason": "场景失败"}

    target = str(task.get("target_id") or cfg.MASTER_QQ)

    # 生成 + 发送（有预生成就不调模型）
    try:
        from ..chat.send import send_short_reply

        rep = prepared
        if not rep:
            from ..ai.client import get_character_reply
            rep = await get_character_reply(_PROMPT.format(content=content), target)
        if not rep:
            log_err(f"[定时] 任务 {task_id} 生成空回复")
            _mark(task_id, ok=False)
            return {"ok": False, "reason": "空回复"}

        await send_short_reply(target, rep, cfg.active_ws_qq, target)
        log_system(f"[定时] 已提醒：{content[:20]}（任务 {task_id}）")
        _mark(task_id, ok=True)
        return {"ok": True, "task_id": task_id}
    except Exception as e:
        log_err(f"[定时] 任务 {task_id} 执行失败: {e}")
        _mark(task_id, ok=False)
        return {"ok": False, "reason": "执行失败"}


def _mark(task_id, ok=True):
    """更新 last_fire；失败的也记（避免同一时刻反复重试）"""
    from datetime import datetime

    from ..schedule import cron

    try:
        import pymysql

        c = None
        from ..infra.conn import get_cursor

        c = get_cursor()
        c.execute("UPDATE cron_tasks SET last_fire=%s WHERE id=%s",
                  (clock.naive(), int(task_id)))
        c.connection.commit()
    except Exception as e:
        log_err(f"[定时] 更新 last_fire 失败({task_id}): {e}")
