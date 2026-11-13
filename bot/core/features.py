# ===================== 功能启用清单 + 环境监测报告（v19.0） =====================
# 只做文件读取/校验/哈希，不 import 业务模块，方便 run.py 在依赖检查前使用。

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PATH = ROOT / "config" / "features.json"
DEFAULT_REPORT = ROOT / "data" / "env_report.json"
SCHEMA_VERSION = 1

DEFAULTS = {
    "chat": {"enabled": True, "required": True},
    "vision": {"enabled": True},
    "voice": {"enabled": True},
    "reading": {"enabled": True},
    "ocr": {"enabled": True},
    "backup": {"enabled": True},
    "proactive": {"enabled": True},
}


class FeaturesError(RuntimeError):
    pass


def path():
    return Path(os.getenv("NAO_FEATURES") or DEFAULT_PATH)


def load(feature_path=None):
    """读功能清单；缺失/非法直接报错，不猜默认"""
    p = Path(feature_path) if feature_path else path()
    if not p.exists():
        raise FeaturesError(f"缺功能清单：{p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        raise FeaturesError(f"功能清单 JSON 非法：{e}")
    if not isinstance(data, dict):
        raise FeaturesError("功能清单必须是 JSON 对象")
    feats = data.get("features")
    if not isinstance(feats, dict):
        raise FeaturesError("features 必须是对象")
    if int(data.get("schema_version") or 0) != SCHEMA_VERSION:
        raise FeaturesError(f"features schema_version 应为 {SCHEMA_VERSION}")
    return data


def enabled(data, name):
    conf = (data.get("features") or {}).get(name) or {}
    return bool(conf.get("enabled"))


def required(data, name):
    conf = (data.get("features") or {}).get(name) or {}
    return bool(conf.get("required"))


def report_path(data):
    env = data.get("environment") or {}
    p = Path(env.get("report") or DEFAULT_REPORT)
    return p if p.is_absolute() else ROOT / p


def _config_bytes():
    """把 features 本身 + 连接配置纳入哈希：改任一项，旧报告失效"""
    parts = [path().read_bytes()]
    for name in ("config.local.json", "config.example.json"):
        p = ROOT / name
        if p.exists():
            parts.append(name.encode())
            parts.append(p.read_bytes())
    return b"\0".join(parts)


def config_hash(data):
    return "sha256:" + hashlib.sha256(_config_bytes()).hexdigest()


def _parse_dt(value):
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def read_report(data, now=None):
    """返回 (ok, reason, report)；ok=False 时 run.py 必须拒绝启动"""
    p = report_path(data)
    if not p.exists():
        return False, f"没有环境监测报告：{p}", None
    try:
        report = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return False, f"环境监测报告损坏：{e}", None
    if int(report.get("schema_version") or 0) != SCHEMA_VERSION:
        return False, "环境监测报告版本不符", report
    if not report.get("ok"):
        return False, "最近一次环境监测未通过", report
    if report.get("config_hash") != config_hash(data):
        return False, "功能清单/配置已变，报告过期", report
    max_age = float((data.get("environment") or {}).get("max_age_hours") or 24)
    checked = _parse_dt(report.get("checked_at"))
    if not checked:
        return False, "环境监测报告缺少 checked_at", report
    current = now or datetime.now(timezone.utc)
    age = (current - checked.astimezone(timezone.utc)).total_seconds() / 3600.0
    if age > max_age:
        return False, f"环境监测报告已过期（{age:.1f} 小时）", report
    return True, "ok", report


def write_report(data, report):
    """原子写报告；失败不影响环境监测退出码"""
    p = report_path(data)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(tmp, 0o600)
    except Exception:
        pass
    os.replace(tmp, p)
    return p
