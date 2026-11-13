# ===================== 模型客户端 =====================
# DeepSeek + 豆包 双模型调用、降级、原始返回落库
# 迁移自 api.py（v5-R2）：斩断「文件末尾 import」的循环依赖写法
# 行为与迁移前完全一致

import asyncio  # 异步IO
import random  # 随机选择兜底回复

from ..config import (  # API 配置
    DS_API_URL, DS_MODEL, DS_TIMEOUT,
    DOUBAO_API_URL, DOUBAO_MODEL, DOUBAO_TIMEOUT,
    API_RETRY_DELAY, MAX_RETRY_TIMES, MASTER_QQ,
    CHAT_TIMEOUT, LONG_TIMEOUT,
)
from ..log import log_api, log_err, log_system  # 日志
from ..core.http import get_http_session  # 线程本地会话（v8-E27）
from ..infra.blocking import run_blocking  # v17.0.3：阻塞调用统一入口
from ..core.types import Fallback  # 兜底文案标记（v5-F2）
from ..infra.repo_ai import save_ai_raw_response  # 保存AI原始返回数据
from ..memory import build_memory_context, extract_keywords  # 记忆上下文与关键词
from ..personality import get_system_prompt  # 系统提示词
from .prompt import now_text  # 当前时间描述（v5-F7）
from ..chat.timing import tone_hint  # 时段语气提示（v6-A20）
# v17.15：ai 不再 import life，改成端口（life 启动时注册）
from ..core.lifeport import life  # noqa: E402
from ..infra.repo_profile import build_profile_text  # 对象画像（v7-B9）
from ..memory.inject import trim, BUDGET  # 分层预算（v8-B13）
from ..memory.timeline import build_timeline_text  # 时间线注入（v8-B16）
from .parse import parse_ai_reply  # 解析AI回复
from bot.core import state as cfg  # 全局运行时变量


async def _maybe_condense(tid, summary=None):
    """调 life 的浓缩能力（端口里是同步函数还是协程都兼容）"""
    import inspect

    fn = getattr(life, "condense", None)
    if fn is None:
        return None
    out = fn(tid, summary)
    if inspect.isawaitable(out):
        return await out
    return out


def _timeout_for(out_tokens):
    """按输出长度选超时：长文（日记/代码）给 40 秒，普通聊天 20 秒（v8-E28）"""
    return LONG_TIMEOUT if (out_tokens or 0) >= 1000 else CHAT_TIMEOUT


def _extract_user_msg(msgs):
    """从消息列表中提取用户消息内容（截断前500字符）"""
    for m in msgs:  # 遍历消息列表
        if m.get("role") == "user":  # 找到用户消息
            return m.get("content", "")[:500]  # 返回内容（截断）
    return ""  # 未找到返回空字符串


def _extract_target_id(msgs):
    """从消息中提取目标ID（取user消息末尾的tid信息，截断前80字符）"""
    user_content = _extract_user_msg(msgs)  # 获取用户消息内容
    return user_content[:80] if user_content else ""  # 截断前80字符作为ID


def _fallback_img_keywords(msgs, reply=""):
    """回复没给图片关键词时，从**用户消息**里补。

    v17.9：以前从她自己的回复里抽，会抽到「出来/一次/还有/几点」这种词。
    用户没打字就返回空——宁可不配图，也别乱搜。
    """
    user_text = _extract_user_msg(msgs)
    if not user_text:
        return []
    return extract_keywords(user_text)[:10]


async def call_deepseek(msgs, retry=2, max_tokens=None, target_id=None):
    """调用DeepSeek API，支持重试，返回回复文本或None
    max_tokens: 可选，覆盖默认输出长度（聊天默认200，代码模式2000；日记等长文场景调用方传入更大值）
    target_id: 可选，显式指定目标ID（日记等场景无法从消息中提取时传入）"""
    log_api(f"[DS] 开始调用, model={DS_MODEL}, 消息数={len(msgs)}, key={'有' if cfg.DS_API_KEY else '无'}")  # 日志记录调用信息
    if not cfg.DS_API_KEY:  # 无API密钥
        log_api("[DS] 无API key，跳过")  # 日志记录
        return None  # 返回None
    h={"Authorization":f"Bearer {cfg.DS_API_KEY}","Content-Type":"application/json"}  # 请求头：Bearer认证

    # 输出长度：调用方显式指定 max_tokens 时优先使用（日记等长文场景），否则走默认（代码模式2000/聊天200）
    out_tokens = max_tokens if max_tokens is not None else (2000 if cfg.CODE_MODE else 200)
    d={"model":DS_MODEL,"messages":msgs,"max_tokens":out_tokens,"temperature":0.7}  # 请求体：模型、消息、最大token（代码模式扩大至2000，保证完整详细回复）
    user_msg = _extract_user_msg(msgs)  # 提取用户消息
    if not target_id:  # 未显式指定时才从消息中提取
        target_id = _extract_target_id(msgs)  # 提取目标ID
    target_id = (target_id or "")[:50]  # 截断，防止超过数据库 VARCHAR(50) 上限
    for a in range(retry):  # 重试循环
        try:
            log_api(f"[DS] 第{a+1}次请求...")  # 日志记录重试次数
            def req():
                """同步HTTP请求函数（在子线程中运行）"""
                s=get_http_session()  # 复用线程本地会话（v8-E27）
                return s.post(DS_API_URL, headers=h, json=d, timeout=_timeout_for(out_tokens), verify=False)  # POST请求
            r=await run_blocking(req, timeout=_timeout_for(out_tokens) + 10, name="deepseek")  # v17.0.3：走统一线程池
            log_api(f"[DS] 响应状态码: {r.status_code}")  # 日志记录状态码
            if r.status_code==200:  # 请求成功
                raw_json = r.json()  # 解析JSON
                t=raw_json["choices"][0]["message"]["content"].strip()  # 提取回复文本
                log_api(f"[DS] 回复内容: {t[:60]}")  # 日志记录回复前60字符
                if t:  # 回复非空
                    log_api("[DS] 回复成功")  # 日志记录成功
                    # 保存原始完整JSON返回数据到数据库
                    save_ai_raw_response(
                        model_name=f"DeepSeek({DS_MODEL})",  # 模型名称
                        user_msg=user_msg,  # 用户消息
                        raw_response_json=raw_json,  # 完整JSON
                        response_text=t,  # 回复文本
                        target_id=target_id,  # 目标ID
                        status="success"  # 状态：成功
                    )
                    return t  # 返回回复文本
                else:  # 回复为空
                    log_api("[DS] 回复内容为空")  # 日志记录
                    save_ai_raw_response("DeepSeek", user_msg, raw_json, "", target_id, "empty_reply")  # 保存空回复记录
            else:  # 非200状态码
                log_api(f"[DS] 非200响应: {r.text[:200]}")  # 日志记录错误信息
                save_ai_raw_response("DeepSeek", user_msg, {"status_code": r.status_code, "text": r.text[:500]}, "", target_id, f"http_error_{r.status_code}")  # 保存错误记录
        except Exception as e:  # 捕获异常
            log_api(f"[DS] 第{a+1}次失败: {e}")  # 日志记录异常
        await asyncio.sleep(API_RETRY_DELAY*(a+1))  # 指数退避等待
    log_api("[DS] 全部重试失败，返回None")  # 所有重试都失败
    return None  # 返回None


async def call_doubao(msgs, max_tokens=None, target_id=None):
    """调用豆包API，支持重试，失败时返回随机兜底回复
    max_tokens: 可选，覆盖默认输出长度（聊天默认300，代码模式2000；日记等长文场景调用方传入更大值）
    target_id: 可选，显式指定目标ID（日记等场景无法从消息中提取时传入）"""
    log_api(f"[豆包] 开始调用, model={DOUBAO_MODEL}, key={'有' if cfg.DOUBAO_API_KEY else '无'}")  # 日志记录调用信息
    user_msg = _extract_user_msg(msgs)  # 提取用户消息
    if not target_id:  # 未显式指定时才从消息中提取
        target_id = _extract_target_id(msgs)  # 提取目标ID
    target_id = (target_id or "")[:50]  # 截断，防止超过数据库 VARCHAR(50) 上限
    if not cfg.DOUBAO_API_KEY:  # 无API密钥
        log_api("[豆包] 无API key，返回默认回复")  # 日志记录
        fallback = random.choice(["哼(扭头)","才不理你(抱手)","切(翻白眼)"])  # 随机选择兜底回复
        save_ai_raw_response("豆包(无key)", user_msg, {}, fallback, target_id, "no_api_key")  # 保存无key记录
        return Fallback(fallback)  # 标记为兜底，调用方不得入库
    h={"Authorization":f"Bearer {cfg.DOUBAO_API_KEY}","Content-Type":"application/json"}  # 请求头：Bearer认证
    temp = 0.2 if cfg.CODE_MODE else 0.7  # 代码模式降低温度以提高准确性
    # 输出长度：调用方显式指定 max_tokens 时优先使用（日记等长文场景），否则走默认（代码模式2000/聊天300）
    out_tokens = max_tokens if max_tokens is not None else (2000 if cfg.CODE_MODE else 300)
    d={"model":DOUBAO_MODEL,"messages":msgs,"max_tokens":out_tokens,"temperature":temp}  # 请求体（代码模式扩大max_tokens至2000，保证完整详细回复）
    for a in range(MAX_RETRY_TIMES):  # 重试循环（最大重试次数）
        try:
            log_api(f"[豆包] 第{a+1}次请求...")  # 日志记录重试次数
            def req():
                """同步HTTP请求函数（在子线程中运行）"""
                s=get_http_session()  # 复用线程本地会话（v8-E27）
                return s.post(DOUBAO_API_URL, headers=h, json=d, timeout=_timeout_for(out_tokens), verify=False)  # POST请求
            r=await run_blocking(req, timeout=_timeout_for(out_tokens) + 10, name="doubao")  # v17.0.3：走统一线程池
            log_api(f"[豆包] 响应状态码: {r.status_code}")  # 日志记录状态码
            if r.status_code==200:  # 请求成功
                raw_json = r.json()  # 解析JSON
                t=raw_json["choices"][0]["message"]["content"].strip()  # 提取回复文本
                log_api(f"[豆包] 回复内容: {t[:60]}")  # 日志记录回复前60字符
                if t:  # 回复非空
                    log_api("[豆包] 回复成功")  # 日志记录成功
                    # 保存原始完整JSON返回数据到数据库
                    save_ai_raw_response(
                        model_name=f"豆包({DOUBAO_MODEL})",  # 模型名称
                        user_msg=user_msg,  # 用户消息
                        raw_response_json=raw_json,  # 完整JSON
                        response_text=t,  # 回复文本
                        target_id=target_id,  # 目标ID
                        status="success"  # 状态：成功
                    )
                    return t  # 返回回复文本
                else:  # 回复为空
                    log_api("[豆包] 回复内容为空")  # 日志记录
                    save_ai_raw_response("豆包", user_msg, raw_json, "", target_id, "empty_reply")  # 保存空回复记录
            elif r.status_code==401:  # 认证错误，直接返回兜底，不再重试
                log_api(f"[豆包] 认证失败(401)，跳过重试: {r.text[:200]}")  # 日志记录
                save_ai_raw_response("豆包", user_msg, {"status_code": 401, "text": r.text[:500]}, "", target_id, "auth_error")  # 保存错误记录
                break  # 跳出重试循环
            else:  # 其他非200状态码
                log_api(f"[豆包] 非200响应: {r.text[:200]}")  # 日志记录错误信息
                save_ai_raw_response("豆包", user_msg, {"status_code": r.status_code, "text": r.text[:500]}, "", target_id, f"http_error_{r.status_code}")  # 保存错误记录
        except Exception as e:  # 捕获异常
            log_api(f"[豆包] 第{a+1}次失败: {e}")  # 日志记录异常
        await asyncio.sleep(API_RETRY_DELAY*(a+1))  # 指数退避等待
    fallback = random.choice(["哼(扭头)","才不理你(抱手)","切(翻白眼)"])  # 所有重试失败，随机选择兜底回复
    log_api(f"[豆包] 全部重试失败，返回兜底: {fallback}")  # 日志记录
    return Fallback(fallback)  # 标记为兜底，调用方不得入库


def _profile_with_habit(tid):
    """画像 + 他的口头禅 + 关系里程碑（v12）"""
    base = build_profile_text(tid)
    extras = []
    try:
        line = life.habit_line(tid)
        if line:
            extras.append(line)
    except Exception:
        pass
    try:
        ms = life.milestone_line(tid)
        if ms:
            extras.append(ms)
    except Exception:
        pass
    if not extras:
        return base
    tail = "｜".join(extras)
    if not base or base == "无":
        return tail
    return f"{base}｜{tail}"


async def _digest_summary(convo):
    """把一段对话压成一行事实（v14.1-D3）"""
    msgs = [{"role": "system",
             "content": "把下面这段对话浓缩成一行事实，不超过30字，只写发生了什么，"
                        "不评价、不加引号、不写『他们』。"},
            {"role": "user", "content": convo}]
    return await call_deepseek(msgs, max_tokens=60) or await call_doubao(msgs, max_tokens=60)

async def _build_tone_line(tid):
    """v19.5：状态/别扭/天气/日常从 get_character_reply 拆出"""
    try:
        state_line = life.state_line(tid)
    except Exception:
        state_line = ""
    try:
        tone_line = (state_line + tone_hint()) if state_line else tone_hint()
    except Exception:
        tone_line = state_line or ""

    try:
        life.friction_refresh(tid)
        _f = life.friction_line(tid)
        if _f:
            tone_line += " " + _f
    except Exception:
        pass

    try:
        from ..life.weather import current as weather_now, describe as weather_desc
        _w = await weather_now()
        if _w:
            tone_line += weather_desc(_w)
    except Exception:
        pass

    try:
        life.ensure_daily()
    except Exception:
        pass
    return tone_line


async def _maybe_run_tool(r, msgs, tid):
    """v19.5：工具调用从 get_character_reply 拆出（最多一轮）"""
    if not r or isinstance(r, Fallback):
        return r
    try:
        from .tools import parse_call, run_tool
        _name, _arg, _body = parse_call(r)
        if _name:
            _result = await run_tool(_name, _arg, tid)
            msgs.append({"role": "assistant", "content": r})
            msgs.append({"role": "user",
                         "content": f"（工具 {_name} 返回：{_result}）"
                                    f"现在用正常的话回他，不要再输出 @tool。"})
            _r2 = await call_deepseek(msgs) or await call_doubao(msgs)
            r = _r2 or _body or r
    except Exception as e:
        log_api(f"[工具] 调用失败: {e}")
    return r


async def get_character_reply(txt, tid, current_kws=None,
                             speaker=None, is_group=False):
    """核心函数：获取角色回复，优先DeepSeek，失败时降级到豆包"""
    log_api(f"[get_character_reply] 收到消息: {txt[:40]}, tid={tid}, kws={current_kws}")  # 日志记录输入
    kw, dia, events = build_memory_context(tid, current_kws, query=txt)

    # v18.3 U4：事实卡常驻（「没有早八」这类状态，不走检索）
    try:
        from ..life import facts as _facts

        # v18.4：按「说话人」取事实；群聊只带 group_ok
        _fb = _facts.prompt_block(speaker or tid, group=is_group)
        if _fb:
            events = (_fb + "\n" + events) if events else _fb
    except Exception as _e:
        log_api(f"[事实] 注入失败（忽略）：{_e}")  # 上下文（关键词、对话历史、检索到的记忆）
    log_api(f"[get_character_reply] 记忆: kw_len={len(kw)}, dia_len={len(dia)}, events={events[:40]}")  # 日志记录上下文信息
    cur_kw_str = "、".join(current_kws) if current_kws else "无"  # 当前话题关键词（顿号分隔）
    tone_line = await _build_tone_line(tid)

    sys_p = get_system_prompt().format(
        global_keywords=kw,
        current_dialogue=dia,
        events=events,
        digest=life.digest_line(tid),  # v14.1-D3：浓缩记录
        reading=life.reading_line(tid) or "最近没在看书",  # v16：在追的小说
        profile=trim(_profile_with_habit(tid), BUDGET["profile"]),  # v7-B9 画像 + v12 口头禅
        timeline=build_timeline_text(tid),  # v8-B16：最近 7 天
        relation=life.relation_line(tid),  # v10-U8 / v13-G54
        master_qq=MASTER_QQ,
        now=now_text(),  # v5-F7：让她知道现在几点
        tone=tone_line,  # v6-A20 时段 + v9-U4 状态
    )  # 格式化系统提示词
    log_api(f"[get_character_reply] system_prompt长度: {len(sys_p)}")  # 日志记录提示词长度
    user_content = f"{txt}\n(当前话题关键词:{cur_kw_str})"  # 构建用户消息（追加当前话题关键词）
    # v10-U8：他提到过去的事，但记忆里可能真没有
    # v14-C2：只有检索确实没命中时才提示「记不清」，免得误伤正常叙述
    if events == "无" and any(w in (txt or "") for w in ("上次", "之前", "记得", "说过", "那天", "当时", "你说过")):
        user_content += "\n（他提到了过去的事，但你记忆里确实没有。直说记不太清，别硬编。）"

    # v13-G55：他糟蹋身体的时候，你会管
    if any(w in (txt or "") for w in ("熬夜", "通宵", "没吃饭", "不吃饭", "不吃早饭", "又没睡", "失眠")):
        user_content += "\n（他刚说了伤身体的事。你可以管他一句，像真的在意，但别唠叨、别说教。）"

    msgs = [{"role":"system","content":sys_p}, {"role":"user","content":user_content}]  # 构建消息列表
    from ..core.locks import model_semaphore
    async with model_semaphore():  # v6-E26：最多 5 个模型请求同时在飞
        r = await call_deepseek(msgs)  # 优先调用DeepSeek
        if not r:  # DeepSeek无回复
            log_api("[get_character_reply] DeepSeek无回复，转豆包")  # 日志记录降级
            r = await call_doubao(msgs)  # 降级到豆包
        if not r:  # v18.16：空回复要能区分原因（调用层日志已带 HTTP 状态/超时）
            try:
                from ..core import metrics
                metrics.inc("empty_reply")
            except Exception:
                pass
            log_err("[空回复] DeepSeek 与豆包均未返回可用内容（空/超时/HTTP 失败）")

    r = await _maybe_run_tool(r, msgs, tid)

    # v9-U4：她真的回话了，算一次"被陪着"——缓解孤独
    if r and not isinstance(r, Fallback):
        try:
            life.touch_talk(tid)
            life.relation_bump(tid)  # v10-U8：聊一轮，近一点
        except Exception:
            pass
        try:  # v14.1-D3：超过 30 轮后，把溢出的旧对话浓缩成一行
            await _maybe_condense(tid, _digest_summary)
        except Exception:
            pass

    # v5-F2：兜底文案不是她的回复，不做关键词补全，交给调用方按「失败」处理
    if isinstance(r, Fallback):
        log_api("[get_character_reply] 两个模型均失败，返回兜底标记")
        return r

    # ===== 修复：AI回复缺少图片关键词行时，自动从对话内容提取关键词兜底 =====
    if r:
        dialog, action, img_kw, event, refined_kw = parse_ai_reply(r)
        if not img_kw:
            # v17.9：只从**用户原文**补关键词；用户没打字就不补
            fallback_kws = _fallback_img_keywords(msgs, dialog)
            if fallback_kws:
                # 限制最多10个关键词
                fallback_kws = fallback_kws[:10]
                # 在回复末尾追加图片关键词行
                r = r.strip() + f"\n关键词搜索图片用：{'、'.join(fallback_kws)}"
                log_api(f"[get_character_reply] 自动补充图片关键词: {fallback_kws}")
            else:
                log_api("[get_character_reply] 无法提取图片关键词，保持原回复")

    log_api(f"[get_character_reply] 最终回复: {r[:60] if r else 'None'}")  # 日志记录最终回复
    return r  # 返回回复文本
