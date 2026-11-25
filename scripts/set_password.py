#!/usr/bin/env python3
"""设置/重置 owner 或指定用户密码。

    python scripts/set_password.py                    # 默认 owner
    python scripts/set_password.py --user 82289153
"""
import argparse
import getpass
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default="", help="用户 ID，默认 owner")
    args = ap.parse_args()
    from bot.infra import repo_users, tenant
    uid = args.user.strip() or str(tenant.owner_id())
    password = getpass.getpass(f"{uid} 新密码（至少 8 位）：")
    if len(password) < 8:
        print("密码至少 8 位")
        return 1
    confirm = getpass.getpass("再次输入：")
    if password != confirm:
        print("两次输入不一致")
        return 1
    repo_users.finish_setup(uid, password)
    row = repo_users.get(uid)
    print("已写入 password_hash:", bool(row and row.get("password_hash")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
