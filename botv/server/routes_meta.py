# ===================== 查询类路由 =====================
# health / status / usage / memory / logs / token
# 迁移自 api_server.py（v5-R5），逻辑逐字未改

from datetime import datetime

from botv.core import state as cfg
from ..config import CST, MASTER_QQ
from ..infra.repo_ai import get_recent_usage
from ..infra.log_sink import get_recent_logs
from . import config as apicfg
from .common import json_response, format_dt


async def handle_health(request):
    return json_response({
        "status": "ok",
        "timestamp": datetime.now(CST).strftime('%Y-%m-%d %H:%M:%S'),
    })


async def handle_status(request):
    try:
        # v17.16：路由层不写 SQL
        from ..infra.repo_query import counts

        n = counts(("images", "user_memory", "events", "logs",
                    "global_keywords", "ai_raw_responses"))
        img_count = n["images"]
        mem_count = n["user_memory"]
        evt_count = n["events"]
        log_count = n["logs"]
        kw_count = n["global_keywords"]
        ai_count = n["ai_raw_responses"]
    except Exception as e:
        return json_response({"error": "db_query_failed", "message": str(e)}, 500)

    return json_response({
        "status": "running",
        "master_qq": MASTER_QQ,
        "deepseek": bool(cfg.DS_API_KEY),
        "doubao": bool(cfg.DOUBAO_API_KEY),
        "clip": cfg.CLIP_ENABLED,
        "sticker_api": bool(cfg.STICKER_API_ALAPI_TOKEN),
        "stats": {
            "images": img_count,
            "memories": mem_count,
            "events": evt_count,
            "logs": log_count,
            "keywords": kw_count,
            "ai_responses": ai_count,
        },
        "runtime": {
            "dialogue_targets": len(cfg.user_memory_pool),
            "global_keywords": len(cfg.global_keyword_set),
            "stickers": len(cfg.STICKER_DATA),
            "daily_triggers": len(cfg.daily_trigger),
        }
    })


async def handle_usage(request):
    try:
        limit = int(request.query.get("limit", 10))
        limit = min(max(limit, 1), 100)
    except ValueError:
        limit = 10

    try:
        records = get_recent_usage(limit)
        result = []
        total_prompt = 0
        total_completion = 0
        total_all = 0
        for r in records:
            pt = r["prompt_tokens"] or 0
            ct = r["completion_tokens"] or 0
            tt = r["total_tokens"] or 0
            result.append({
                "model": r["model_name"],
                "prompt_tokens": pt,
                "completion_tokens": ct,
                "total_tokens": tt,
                "status": r["status"],
                "created_at": format_dt(r.get("created_at")),
            })
            total_prompt += pt
            total_completion += ct
            total_all += tt
        return json_response({
            "records": result,
            "summary": {
                "total_prompt_tokens": total_prompt,
                "total_completion_tokens": total_completion,
                "total_tokens": total_all,
                "count": len(result),
            }
        })
    except Exception as e:
        return json_response({"error": "query_failed", "message": str(e)}, 500)


async def handle_memory(request):
    target_id = request.query.get("target_id", "")
    if target_id:
        if target_id in cfg.user_memory_pool:
            deq = cfg.user_memory_pool[target_id]
            records = []
            for u, b in deq:
                records.append({"user": u, "bot": b})
            return json_response({
                "target_id": target_id,
                "count": len(records),
                "records": records[-20:],
            })
        return json_response({
            "target_id": target_id,
            "count": 0,
            "records": [],
        })
    targets = []
    for tid, deq in cfg.user_memory_pool.items():
        targets.append({
            "target_id": tid,
            "count": len(deq),
            "last_message": deq[-1][0][:30] if deq else "",
        })
    return json_response({
        "total_targets": len(cfg.user_memory_pool),
        "targets": targets,
    })


async def handle_logs(request):
    try:
        limit = int(request.query.get("limit", 20))
        limit = min(max(limit, 1), 100)
    except ValueError:
        limit = 20

    try:
        logs_text = get_recent_logs(limit)
        return json_response({
            "count": limit,
            "logs": logs_text,
        })
    except Exception as e:
        return json_response({"error": "log_query_failed", "message": str(e)}, 500)


async def handle_get_token(request):
    return json_response({
        "token_prefix": apicfg.API_TOKEN[:12] + "...",
        "host": apicfg.API_HOST,
        "port": apicfg.API_PORT,
        "endpoints": [
            {"path": "/api/health", "method": "GET", "auth": False},
            {"path": "/api/status", "method": "GET", "auth": True},
            {"path": "/api/usage", "method": "GET", "auth": True},
            {"path": "/api/memory", "method": "GET", "auth": True},
            {"path": "/api/logs", "method": "GET", "auth": True},
            {"path": "/api/chat", "method": "POST", "auth": True},
            {"path": "/api/command", "method": "POST", "auth": True},
            {"path": "/api/token", "method": "GET", "auth": True},
        ]
    })

