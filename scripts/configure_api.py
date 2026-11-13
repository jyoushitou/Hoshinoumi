#!/usr/bin/env python3
"""API 配置向导（v19.5.6）

在环境监测之前运行：
    python3 scripts/configure_api.py

交互填写 DeepSeek / 豆包方舟 / ALAPI 密钥，以及视觉接入点。
密钥写入数据库 api_keys；视觉接入点写入 config.local.json 的 vision 段。
"""

import getpass
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CONFIG = ROOT / "config.local.json"


def _mask(value):
    value = str(value or "")
    if not value:
        return "（未配置）"
    if len(value) <= 8:
        return value[:2] + "***"
    return value[:4] + "..." + value[-2:]


def _ask(label, current="", secret=False):
    shown = _mask(current) if secret else (current or "（未配置）")
    prompt = f"{label}\n  当前：{shown}\n  新值（回车保留）："
    try:
        value = getpass.getpass(prompt) if secret else input(prompt)
    except (EOFError, KeyboardInterrupt):
        print("\n已取消。")
        raise SystemExit(1)
    return value.strip() or current


def _read_config():
    if not CONFIG.exists():
        return {}
    try:
        data = json.loads(CONFIG.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"❌ config.local.json 读取失败：{e}")
        return {}


def _write_config(data):
    tmp = CONFIG.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, CONFIG)
    try:
        os.chmod(CONFIG, 0o600)
    except Exception:
        pass


def main():
    print("=" * 60)
    print("  友利奈绪 API 配置向导")
    print("=" * 60)
    print("密钥写入数据库 api_keys；视觉接入点写入 config.local.json。")
    print("直接回车 = 保留当前值；输入 - = 清空该项。\n")

    from bot.infra import repo_key

    # 当前值：DB > 环境变量；数据库还没迁移时明确提示，不直接崩
    try:
        current = {
            "DS_API_KEY": repo_key.get_api_key_from_db("DS_API_KEY") or os.getenv("DS_API_KEY", ""),
            "ARK_API_KEY": repo_key.get_api_key_from_db("ARK_API_KEY") or os.getenv("ARK_API_KEY", ""),
            "ALAPI_TOKEN": repo_key.get_api_key_from_db("ALAPI_TOKEN") or os.getenv("ALAPI_TOKEN", ""),
        }
    except Exception as e:
        print(f"❌ 数据库里还没有 api_keys 表：{e}")
        print("先跑：python3 scripts/migrate.py --apply")
        return 1

    values = {}
    for name, label in (
        ("DS_API_KEY", "DeepSeek 主对话 API Key（sk-...）"),
        ("ARK_API_KEY", "豆包/方舟 Vision API Key（不是 Access Key）"),
        ("ALAPI_TOKEN", "ALAPI 搜图 Token（可跳过）"),
    ):
        values[name] = _ask(label, current[name], secret=True)
        if values[name] == "-":
            values[name] = ""

    cfg = _read_config()
    vision = cfg.get("vision") or {}
    vision["model"] = _ask("视觉接入点/模型（方舟 ep-...，可跳过）", vision.get("model", ""))
    vision["url"] = _ask("视觉接口地址（留空用默认方舟地址）", vision.get("url", ""))
    if vision["model"] == "-":
        vision["model"] = ""
    if vision["url"] == "-":
        vision["url"] = ""
    cfg["vision"] = vision
    _write_config(cfg)

    ok = 0
    for name, value in values.items():
        if repo_key.save_api_key(name, value):
            ok += 1
        else:
            print(f"❌ {name} 写入数据库失败（先跑 python3 scripts/migrate.py --apply）")

    print("\n" + "=" * 60)
    print(f"已保存：{ok}/3 个密钥；视觉接入点：{vision.get('model') or '未配置'}")
    print("下一步：")
    print("  python3 checks/env_check.py")
    print("  python3 run.py")
    print("=" * 60)
    return 0 if ok == 3 else 1


if __name__ == "__main__":
    raise SystemExit(main())
