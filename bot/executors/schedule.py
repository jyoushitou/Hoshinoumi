# ===================== 定时场景执行器（v17.1.0） =====================
# 把 runner 里那一大段「if scene == 催起床 / elif 催睡觉 / else ...」
# 搬到这里，变成注册在调度器上的一个事件。
#
#   schedule_scene（P1，key=scene:<名字>:<日期>）
#        ↓ worker 执行
#   挑提示词 → 调模型 → 发消息（起床/睡觉还配一张 ACG 图）
#
# 好处：
#   - 定时任务不再内联在 1 秒循环里（生成要几秒，会拖慢其他定时）
#   - 每个场景的提示词集中在一处，加场景只改这张表

from ..core import state as cfg
from ..events.base import Priority
from ..events.registry import register
from ..log import log_api, log_err

# 场景 → 提示词列表；with_image=True 表示发完文字再配一张图
SCENES = {
    "催起床": {
        "prompts": [
            "现在是早上，该催主人起床了，你主动发消息给他",
            "早上好，主人还在睡懒觉，你叫他起床",
            "天亮了，主人还没醒，你去喊他起床",
        ],
        "with_image": True,
        "image_hint": "ACG起床图",
    },
    "催睡觉": {
        "prompts": [
            "夜深了，该催主人睡觉了，你主动发消息给他",
            "很晚了，主人还没睡，你催他去睡觉",
            "已经深夜了，主人还在熬夜，你叫他早点休息",
        ],
        "with_image": True,
        "image_hint": "ACG催睡图",
    },
    "周末吐槽赖床": {
        "prompts": [
            "周末了，主人还在睡懒觉，你主动吐槽他",
            "休息日了，主人还没起床，你去调侃他一下",
        ],
    },
    "提醒点外卖": {
        "prompts": [
            "中午了，提醒主人该点外卖了，你主动发消息",
            "到饭点了，主人还没吃饭，你催他去吃饭",
        ],
    },
    "叮嘱午睡": {
        "prompts": [
            "中午了，叮嘱主人睡个午觉，你主动发消息",
            "午休时间到了，提醒主人休息一下，你主动说",
        ],
    },
    "提醒起身": {
        "prompts": [
            "下午了，提醒主人起来活动活动，你主动发消息",
            "坐太久了，叫主人起来走走，你主动说",
        ],
    },
    "提醒晚餐": {
        "prompts": [
            "晚上了，提醒主人该吃晚饭了，你主动发消息",
            "到晚饭时间了，主人还没吃，你催他去吃饭",
        ],
    },
    "周日复盘": {
        "prompts": [
            "周日晚上了，回顾这一周：问问他这周过得怎么样，也说说你自己这周的事",
            "一周要结束了，跟主人聊聊这周发生的事，别像做汇报",
        ],
    },
}

DEFAULT_PROMPTS = ["你主动找主人聊聊天"]


def scene_config(name):
    """取场景配置；未知场景用默认"""
    return SCENES.get(name, {"prompts": DEFAULT_PROMPTS})


async def generate_scene_reply(scene):
    """只生成不发送（v18.7 预生成用）"""
    import random

    from ..ai.client import get_character_reply

    conf = scene_config(scene)
    prompt = random.choice(conf["prompts"])
    log_api(f"[定时] 生成场景：{scene}")
    return await get_character_reply(prompt, str(cfg.MASTER_QQ))


@register("schedule_scene", priority=Priority.EVENT, timeout=120, retries=1,
          description="执行一个定时场景（催起床/午睡/复盘…）")
async def handle_schedule_scene(ev, prepared=None):
    """ev.args = (场景名,)；prepared 有值就直接发，不再生成"""
    from ..chat.send import send_short_reply

    args = getattr(ev, "args", ()) or ()
    scene = args[0] if args else ""
    conf = scene_config(scene)

    log_api(f"[定时] 执行场景：{scene}")

    try:
        rep = prepared or await generate_scene_reply(scene)
    except Exception as e:
        log_err(f"[定时] {scene} 生成失败: {e}")
        return {"ok": False, "reason": "生成失败"}

    if not rep:
        return {"ok": False, "reason": "空回复"}

    # v18.7：预生成（exact）绕过 3 秒合并窗口，到点先发首条
    if prepared:
        await send_short_reply(cfg.MASTER_QQ, rep, cfg.active_ws_qq, cfg.MASTER_QQ)
    else:
        # v17.2 U3：走合并窗口——相邻的定时消息 3 秒内并成一条气泡
        from ..egress.merge import get_merger
        merged = await get_merger().offer(str(cfg.MASTER_QQ), rep, kind="schedule")
        if not merged:
            await send_short_reply(cfg.MASTER_QQ, rep, cfg.active_ws_qq, cfg.MASTER_QQ)

    # 起床/睡觉配一张图（失败不影响文字已发）
    if conf.get("with_image"):
        try:
            await _send_acg_image(conf.get("image_hint", "ACG图"))
        except Exception as e:
            log_api(f"[定时] 配图失败（忽略）: {e}")

    return {"ok": True, "scene": scene}


async def _send_acg_image(hint=""):
    from ..chat.send import make_image_msg, send_private_msg
    from ..image import fetch_and_save_acg_image

    if not cfg.active_ws_qq or getattr(cfg.active_ws_qq, "closed", False):
        return False
    fp = await fetch_and_save_acg_image()
    msg = make_image_msg(fp)
    if not msg:
        return False
    await send_private_msg(cfg.MASTER_QQ, msg, cfg.active_ws_qq)
    log_api(f"[定时] {hint}已发送")
    return True


def submit_scene(scene, day=None, scheduler=None):
    """把某个场景投给调度器；key 带日期，天然一天一次"""
    from ..scheduler.dispatcher import get_scheduler

    sched = scheduler or get_scheduler()
    key = f"scene:{scene}:{day or ''}"
    return sched.submit("schedule_scene", key, args=(scene,))
