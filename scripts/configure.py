#!/usr/bin/env python3
"""Hoshinoumi（REC）网关配置向导（v20.0）

    python3 scripts/configure.py            # 交互配置
    python3 scripts/configure.py --show     # 看当前配置
    python3 scripts/configure.py --check    # 只校验
"""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PATH = os.path.join(ROOT, "config", "gateway.json")
DEFAULTS = {
    "listen": {"host": "127.0.0.1", "port": 27005},
    "backend": {
        "base": "http://127.0.0.1:27004",
        "timeout_ms": 5000,
        "startup_wait": True,
        "startup_retry_interval_sec": 30,
        "startup_max_attempts": 5,
    },
    "log_level": "info",
}


def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("顶层必须是对象")
        return data
    except FileNotFoundError:
        return json.loads(json.dumps(DEFAULTS))
    except Exception as e:
        raise SystemExit(f"读配置失败: {e}")


def _validate(cfg):
    listen = cfg.get("listen") if isinstance(cfg.get("listen"), dict) else {}
    backend = cfg.get("backend") if isinstance(cfg.get("backend"), dict) else {}
    host = str(listen.get("host") or "127.0.0.1")
    try:
        port = int(listen.get("port") or 27005)
    except ValueError:
        raise SystemExit("listen.port 必须是整数")
    if not (1 <= port <= 65535):
        raise SystemExit("listen.port 必须在 1..65535")
    base = str(backend.get("base") or "http://127.0.0.1:27004").rstrip("/")
    if not (base.startswith("http://127.0.0.1:") or base.startswith("http://localhost:")):
        raise SystemExit("backend.base 只允许 http://127.0.0.1:... 或 http://localhost:...")
    try:
        timeout = int(backend.get("timeout_ms") or 5000)
    except ValueError:
        raise SystemExit("backend.timeout_ms 必须是整数")
    if timeout <= 0:
        raise SystemExit("backend.timeout_ms 必须大于 0")
    wait = backend.get("startup_wait", True)
    if isinstance(wait, str):
        wait = wait.strip().lower() in ("1", "true", "yes", "y", "on")
    try:
        retry_sec = int(backend.get("startup_retry_interval_sec") or 30)
        max_attempts = int(backend.get("startup_max_attempts") or 5)
    except ValueError:
        raise SystemExit("startup_retry_interval_sec / startup_max_attempts 必须是整数")
    if not (1 <= retry_sec <= 3600):
        raise SystemExit("backend.startup_retry_interval_sec 必须在 1..3600")
    if not (1 <= max_attempts <= 100):
        raise SystemExit("backend.startup_max_attempts 必须在 1..100")
    level = str(cfg.get("log_level") or "info")
    if level not in ("info", "debug"):
        raise SystemExit("log_level 只支持 info / debug")
    return {
        "listen": {"host": host, "port": port},
        "backend": {
            "base": base,
            "timeout_ms": timeout,
            "startup_wait": bool(wait),
            "startup_retry_interval_sec": retry_sec,
            "startup_max_attempts": max_attempts,
        },
        "log_level": level,
    }


def _ask(label, default):
    try:
        raw = input(f"{label} [{default}]: ").strip()
    except EOFError:
        raw = ""
    return raw or default


def _ask_bool(label, default):
    raw = _ask(label + "（y/n）", "y" if default else "n")
    return str(raw).strip().lower() in ("1", "true", "yes", "y", "on")


def _run_wizard(path):
    if not sys.stdin.isatty():
        raise SystemExit("非交互环境，请直接编辑 config/gateway.json 或加 --show")
    cfg = _load(path)
    print("=" * 56)
    print("  Hoshinoumi（REC）网关配置")
    print("=" * 56)
    listen = cfg.setdefault("listen", {})
    backend = cfg.setdefault("backend", {})
    listen["host"] = _ask("监听地址（默认只本机；对外填 0.0.0.0）", listen.get("host", "127.0.0.1"))
    listen["port"] = int(_ask("监听端口", listen.get("port", 27005)))
    backend["base"] = _ask("后端 API 地址", backend.get("base", "http://127.0.0.1:27004"))
    backend["timeout_ms"] = int(_ask("后端超时（毫秒）", backend.get("timeout_ms", 5000)))
    backend["startup_wait"] = _ask_bool(
        "启动时等待后端（30s 间隔，最多 5 次）",
        bool(backend.get("startup_wait", True)))
    backend["startup_retry_interval_sec"] = int(_ask(
        "启动等待间隔（秒）", backend.get("startup_retry_interval_sec", 30)))
    backend["startup_max_attempts"] = int(_ask(
        "启动等待次数", backend.get("startup_max_attempts", 5)))
    cfg["log_level"] = _ask("日志级别（info/debug）", cfg.get("log_level", "info"))
    cfg = _validate(cfg)

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        f.write("\n")
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass
    print(f"\n[OK] 已写入 {path}（权限 600）")
    print("提示：API 密钥仍用 python3 scripts/configure_api.py 配置")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=DEFAULT_PATH)
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    if args.show:
        cfg = _validate(_load(args.config))
        print(json.dumps(cfg, ensure_ascii=False, indent=2))
        return 0
    if args.check:
        _validate(_load(args.config))
        print(f"[OK] {args.config} 配置合法")
        return 0
    _run_wizard(args.config)
    return 0


if __name__ == "__main__":
    sys.exit(main())

