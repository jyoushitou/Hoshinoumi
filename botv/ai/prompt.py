# ===================== 提示词组装 =====================
# 人设补充加载（远程/本地）+ 系统提示词渲染
# 迁移自 personality.py（v5-R5）

import os
from datetime import datetime

from botv.core import state as cfg
from ..config import CST  # 东八区
from ..log import log_system, log_api
from ..core.http import create_http_session
from .persona import LOCAL_SYSTEM_PROMPT, CODE_MODE_SYSTEM_PROMPT, build_available_tags
from .tools import tool_prompt  # v13-U22
from .persona_loader import load_text as load_card_text  # v14-A1

_WEEKDAY = "一二三四五六日"


def now_text(now=None):
    """当前时间的人话描述（v5-F7）

    例：2026年11月8日 周六 21:30（晚上）
    """
    now = now or datetime.now(CST)
    h = now.hour
    if h < 6:
        period = "凌晨"
    elif h < 9:
        period = "早上"
    elif h < 12:
        period = "上午"
    elif h < 14:
        period = "中午"
    elif h < 18:
        period = "下午"
    elif h < 23:
        period = "晚上"
    else:
        period = "深夜"
    return f"{now.year}年{now.month}月{now.day}日 周{_WEEKDAY[now.weekday()]} {now.strftime('%H:%M')}（{period}）"

# 本地人设补充文件路径（botv/personality_supplement.txt）
LOCAL_SUPPLEMENT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "personality_supplement.txt")

# 远程人设补充URL列表（可选，按需配置）
PERSONALITY_SUPPLEMENT_URLS = [
    # "https://raw.githubusercontent.com/your-repo/nao_personality/main/base.txt",
]

PERSONALITY_SUPPLEMENT = ""  # 缓存远程拉取的人设补充文本


def load_personality_supplement():
    """加载人设补充文本，优先级：远程URL > 本地文件"""
    global PERSONALITY_SUPPLEMENT

    # 1. 尝试从远程URL加载
    for url in PERSONALITY_SUPPLEMENT_URLS:
        try:
            s = create_http_session()
            r = s.get(url, timeout=(5, 10), verify=False)  # 5秒连接超时，10秒读取超时
            if r.status_code == 200 and r.text.strip():
                PERSONALITY_SUPPLEMENT = r.text.strip()
                log_system(f"人设补充加载成功（远程）: {url}")
                return
        except Exception as e:
            log_api(f"人设补充加载失败（远程） {url}: {e}")
        finally:
            try:
                s.close()
            except Exception:
                pass

    # 1.5 尝试从角色卡加载（v14-A1）
    card_sup = load_card_text("supplement.txt")
    if card_sup:
        PERSONALITY_SUPPLEMENT = card_sup
        log_system("人设补充加载成功（角色卡）")
        return

    # 2. 尝试从本地文件加载
    try:
        if os.path.exists(LOCAL_SUPPLEMENT_FILE):
            with open(LOCAL_SUPPLEMENT_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if content:
                PERSONALITY_SUPPLEMENT = content
                log_system(f"人设补充加载成功（本地）: {LOCAL_SUPPLEMENT_FILE}")
                return
    except Exception as e:
        log_api(f"人设补充加载失败（本地）: {e}")

    log_system("人设补充未加载，使用基础人设")


def get_system_prompt():
    """生成完整的系统提示词，包含20个纬度×30个标签的可用图片标签列表"""
    available_tags = build_available_tags()

    # 代码模式下：使用代码模式提示词（知识正确性优先）
    if cfg.CODE_MODE:
        prompt = CODE_MODE_SYSTEM_PROMPT
    else:
        # v14-A1：优先读角色卡的 prompt.txt，读不到用代码内置
        prompt = load_card_text("prompt.txt") or LOCAL_SYSTEM_PROMPT
    if PERSONALITY_SUPPLEMENT:
        prompt = PERSONALITY_SUPPLEMENT + "\n\n" + prompt  # 补充文本放在前面
    prompt = prompt.replace("{available_tags}", available_tags)
    if not cfg.CODE_MODE:  # v13-U22：普通模式才给工具
        prompt += "\n\n" + tool_prompt()
    return prompt
