# ===================== AI 回复解析 =====================
# 解析模型的「五行格式」输出：对话 / 动作 / 图片关键词 / 事件 / 提炼词
# 迁移自 utils.py（v5-R2），行为与迁移前完全一致

from ..log import log_api  # 日志


def parse_ai_reply(ans):
    """解析AI回复的五行格式
    返回 (dialog, action, img_kw, event, refined_kw)
    格式：
      第一行：对话内容
      第二行：动作描写（如（扭头））
      第三行：关键词搜索图片用：词1 词2 ...（20个纬度）
      第四行：事件摘要：xxx
      第五行：关键词提炼：词1 词2 ..."""
    if not ans:  # 安全处理None或空字符串
        return "嗯嗯", "", [], "", []
    # 清理AI回复中的特殊标记（[sticker]等），避免被当作文本发送
    cleaned = ans.replace("[sticker]", "").replace("[Sticker]", "").replace("[STICKER]", "").strip()
    # 剥离"第一行：""第二行："等行号前缀，AI偶尔会把内部标记原样输出
    import re as _re_strip
    cleaned = _re_strip.sub(r"^[第]{0,1}[一二三四五六七八九十0-9]{1,3}[行]：[\s　]*", "", cleaned, flags=_re_strip.MULTILINE)
    lines = [l.strip() for l in cleaned.split('\n') if l.strip()]
    if not lines:  # 清理后没有内容
        return "嗯嗯", "", [], "", []

    dialog = lines[0]  # 第一行：对话
    action = ""  # 动作描写
    img_kw = []  # 图片搜索关键词列表
    event = ""  # 事件摘要
    refined_kw = []  # AI提炼的关键词

    # 遍历所有行，按前缀标记分类解析
    # 第二行及之后：先找动作行（以（开头），再找带标记的行
    found_img_tag = False
    extra_dialogs = []  # 额外的对话内容（没有标记的中间行）

    for i, line in enumerate(lines[1:], 1):
        if "关键词搜索图片用" in line:
            kw_part = line.split("：")[-1].split(":")[-1].strip()
            # 支持中文顿号、逗号、空格、全角空格分隔
            img_kw = [k.strip() for k in kw_part.replace("，"," ").replace(","," ").replace("、"," ").replace("　"," ").replace("  "," ").split() if k.strip()]
            found_img_tag = True
        elif "事件摘要" in line:
            # 取第一个冒号后的内容（避免多个冒号时取到标签部分），并截断管道符后的标签
            event = line.split("：", 1)[-1].split(":", 1)[-1].strip()
            if "|" in event:
                event = event.split("|")[0].strip()
        elif "关键词提炼" in line:
            kw_part = line.split("：")[-1].split(":")[-1].strip()
            # 支持中文顿号、逗号、空格、全角空格分隔
            refined_kw = [k.strip() for k in kw_part.replace("，"," ").replace(","," ").replace("、"," ").replace("　"," ").replace("  "," ").split() if k.strip()]
        elif line.startswith("（") or line.startswith("("):
            # 动作描写行（以括号开头），只取第一个动作行
            if not action:
                action = line
        elif any(m in line for m in ("标签", "摘要", "关键词", "提炼", "事件")):
            # 内部元数据拦截：含内部标记词的行禁止混入对话
            log_api(f"[parse_ai_reply] 拦截内部元数据行: {line[:30]}")
        else:
            # 纯关键词行判断（如：睡觉,躺平,抱抱 — 无"关键词搜索图片用"前缀）
            # 特征：含逗号/顿号分隔，不含语句标点（。！？和括号），词数>=2
            import re
            if re.search(r"[，,、]", line) and not re.search(r"[。！？!?；;：:（()）]", line):
                tokens = [k.strip() for k in line.replace("，"," ").replace(","," ").replace("、"," ").replace("　"," ").replace("  "," ").split() if k.strip()]
                if len(tokens) >= 2:
                    # 纯关键词行 → 作为图片搜索关键词，不并入对话
                    img_kw = tokens
                    found_img_tag = True  # 标记已找到关键词行，避免第三行兜底重复解析
                else:
                    extra_dialogs.append(line)
            else:
                # 没有标记的普通行，且不是动作行，收集为额外对话
                extra_dialogs.append(line)

    # 如果没有找到带标记的关键词行，尝试用第三行兜底
    if not found_img_tag and len(lines) > 2:
        third_line = lines[2]
        # 排除明显不是关键词的行
        if third_line and not third_line.startswith("事件") and not third_line.startswith("关键词") and not third_line.startswith("（") and not third_line.startswith("("):
            # 支持中文顿号、逗号、空格、全角空格分隔
            img_kw = [k.strip() for k in third_line.replace("，"," ").replace(","," ").replace("、"," ").replace("　"," ").replace("  "," ").split() if k.strip()]

    # 如果有多行额外对话，追加到dialog后面
    if extra_dialogs:
        dialog = dialog + "\n" + "\n".join(extra_dialogs)

    if action in ("（无）","(无)","无"):
        action = ""  # 空动作视为无动作
    return dialog, action, img_kw, event, refined_kw
