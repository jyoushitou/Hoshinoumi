# ===================== API 服务器配置 =====================
# 常量 + Token 加载（迁移自 api_server.py，v5-R5）

import secrets

from ..log import log_system, log_err
from ..infra.conn import get_cursor

API_HOST = "0.0.0.0"
from ..core import settings as _settings

API_PORT = int(_settings.get("api_port") or 60908)  # v16：可被 NAO_API_PORT / 配置文件覆盖
API_TOKEN = ""
API_TOKEN_KEY_NAME = "API_SERVER_TOKEN"
MAX_CONCURRENT_REQUESTS = 20


def load_api_token():
    """从数据库加载 API Token，不存在则生成并落库"""
    global API_TOKEN
    try:
        c = get_cursor()
        c.execute("SELECT key_value FROM api_keys WHERE key_name=%s", (API_TOKEN_KEY_NAME,))
        r = c.fetchone()
        if r and r.get("key_value"):
            API_TOKEN = r["key_value"]
            log_system("API Token 已从数据库加载")
            return
    except Exception as e:
        log_err(f"加载 API Token 失败: {e}")

    API_TOKEN = "nao_" + secrets.token_hex(20)
    try:
        c = get_cursor()
        c.execute(
            "INSERT INTO api_keys (key_name, key_value) VALUES (%s, %s) ON DUPLICATE KEY UPDATE key_value=%s",
            (API_TOKEN_KEY_NAME, API_TOKEN, API_TOKEN)
        )
        c.connection.commit()
        log_system(f"已生成默认 API Token: {API_TOKEN[:20]}...")
    except Exception as e:
        log_err(f"保存 API Token 失败: {e}")


def format_api_token_info():
    """给 !token / 调试用的 Token 说明文本"""
    return (
        f"API 服务器 Token：\n"
        f"  Token: {API_TOKEN}\n"
        f"  地址: http://{API_HOST}:{API_PORT}\n"
        f"  用法: Authorization: Bearer {API_TOKEN}\n"
        f"  接口列表:"
        f"    GET  /api/health   - 健康检查（无需Token）"
        f"    GET  /api/status   - 运行状态"
        f"    GET  /api/usage    - Token用量"
        f"    GET  /api/memory   - 对话记忆"
        f"    GET  /api/logs     - 最近日志"
        f"    GET  /api/token    - Token信息"
        f"    POST /api/chat     - AI对话"
        f"    POST /api/command  - 执行命令"
    )
