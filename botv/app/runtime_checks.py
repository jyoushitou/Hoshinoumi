# ===================== 运行时必要探测（v19.0） =====================
# 只放 run.py 启动必须的：网络 + 人设。
# 其他环境检查（依赖/DB/表结构/密钥/视觉）在 scripts/preflight.py。

import socket
import time


def check_network(host="api.deepseek.com", port=443, timeout=5):
    """TCP 探测模型 API 端口；失败抛 RuntimeError，带主机/端口/原因"""
    t0 = time.time()
    try:
        socket.create_connection((host, port), timeout=timeout).close()
    except Exception as e:
        raise RuntimeError(f"网络不可达 {host}:{port}（{type(e).__name__}: {e}）")
    return f"{host}:{port} 可达（{(time.time() - t0) * 1000:.0f}ms）"


def check_persona():
    """角色卡/补充文本/system prompt 必须能构建"""
    try:
        from ..ai.prompt import get_system_prompt, load_personality_supplement

        load_personality_supplement()
        prompt = get_system_prompt()
    except Exception as e:
        raise RuntimeError(f"人设加载失败：{type(e).__name__}: {e}")
    if not prompt or "{available_tags}" in prompt:
        raise RuntimeError("人设提示词为空或占位符未替换")
    return f"system prompt {len(prompt)} 字"
