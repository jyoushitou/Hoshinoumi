# ===================== 热更新准入（v25.4） =====================
# 需要迁移数据库 / 必须重启的版本，一律拒绝热更新。

import json
from pathlib import Path


def read_manifest(path):
    """读取版本目录的 update.json；缺失/坏 JSON 返回 (None, 原因)。"""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as e:
        return None, f"update.json 读取失败：{e}"
    if not isinstance(data, dict):
        return None, "update.json 不是对象"
    return data, ""


def check(manifest, current_schema):
    """返回 (allowed, reason)。任何“需要停机”的声明都拒绝。"""
    if not isinstance(manifest, dict):
        return False, "缺少 update.json"
    if not manifest.get("version"):
        return False, "update.json 缺少 version"
    if manifest.get("requires_restart") is True:
        return False, "这个版本必须重启进程，不能热更新"
    if manifest.get("requires_schema") is True:
        return False, "这个版本必须停机迁移数据库，不能热更新"
    declared = manifest.get("schema_version")
    if declared is not None and str(declared) != str(current_schema):
        return False, (f"schema 不一致：版本要求 {declared}，当前 {current_schema}；"
                       "必须走维护窗口迁移")
    return True, ""


def status_text(manifest, allowed, reason):
    if allowed:
        return f"允许热更新：{manifest.get('version')}"
    return (f"拒绝热更新：{reason}\n"
            f"当前版本继续运行，未切换。\n"
            "请安排维护窗口后手动升级。")
