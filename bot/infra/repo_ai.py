# ===================== AI 调用记录仓储 =====================
# 原始返回落库、token 用量查询
# 迁移自 db.py（v5-R6）

import json
from datetime import datetime

from ..config import CST
from ..log import log_err
from .conn import get_cursor


def save_ai_raw_response(model_name, user_msg, raw_response_json, response_text, target_id, status="success"):
    """保存AI的原始完整返回数据到 ai_raw_responses 表（用于调试和分析）"""
    try:
        c = get_cursor()
        # 从原始JSON中提取token用量（兼容DeepSeek和豆包格式）
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0
        if isinstance(raw_response_json, dict):
            usage = raw_response_json.get("usage", {})
            if isinstance(usage, dict):
                prompt_tokens = usage.get("prompt_tokens", 0) or 0
                completion_tokens = usage.get("completion_tokens", 0) or 0
                total_tokens = usage.get("total_tokens", 0) or 0
        c.execute("""
            INSERT INTO ai_raw_responses 
            (model_name, user_msg, raw_response_json, response_text, target_id, status, created_at,
             prompt_tokens, completion_tokens, total_tokens)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            model_name,  # 模型名称
            user_msg[:500],  # 用户消息（截断）
            json.dumps(raw_response_json, ensure_ascii=False),  # 完整JSON
            response_text[:1000] if response_text else '',  # 提取的文本
            (target_id or "")[:50],  # 对话目标ID（截断防超长）
            status,  # 状态
            datetime.now(CST).strftime('%Y-%m-%d %H:%M:%S'),  # 创建时间
            prompt_tokens,  # 输入token数
            completion_tokens,  # 输出token数
            total_tokens  # 总token数
        ))
        c.connection.commit()
    except Exception as e:
        log_err(f"保存AI原始数据失败: {e}")


def get_recent_usage(limit=10):
    """获取最近N次AI调用的token用量和使用模型"""
    try:
        c = get_cursor()
        c.execute("""
            SELECT model_name, prompt_tokens, completion_tokens, total_tokens, status, created_at
            FROM ai_raw_responses
            WHERE status = 'success'
            ORDER BY id DESC LIMIT %s
        """, (limit,))
        return c.fetchall()
    except Exception as e:
        log_err(f"查询token用量失败: {e}")
        return []
