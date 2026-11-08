# ===================== API 公共工具 =====================
# JSON 响应统一 UTF-8；时间格式化

import json

from aiohttp import web


def format_dt(dt):
    """数据库时间字段统一转字符串"""
    if hasattr(dt, 'strftime'):
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    return str(dt)[:19] if dt else ""


def json_response(data, status=200):
    """统一的 JSON 响应（中文不转义）"""
    return web.json_response(data, status=status, dumps=lambda x: json.dumps(x, ensure_ascii=False))
