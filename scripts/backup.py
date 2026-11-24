#!/usr/bin/env python3
"""Hoshinoumi instance backup CLI.

Examples:
  python scripts/backup.py export  --out hoshinoumi-backup.json
  python scripts/backup.py validate --file hoshinoumi-backup.json
  python scripts/backup.py import  --file hoshinoumi-backup.json --yes
  python scripts/backup.py rollback
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request

DEFAULT_BASE = "http://127.0.0.1:27005"
DEFAULT_TOKEN = "mock-token"


def request(base: str, token: str, path: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(base.rstrip("/") + path, data=data, method="POST" if payload is not None else "GET")
    req.add_header("Authorization", f"Bearer {token}")
    if data is not None:
        req.add_header("Content-Type", "application/json; charset=utf-8")
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Hoshinoumi instance backup")
    parser.add_argument("action", choices=["export", "validate", "import", "rollback"])
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--token", default=DEFAULT_TOKEN)
    parser.add_argument("--file", default="hoshinoumi-backup.json")
    parser.add_argument("--out", default="hoshinoumi-backup.json")
    parser.add_argument("--yes", action="store_true", help="skip import confirmation")
    args = parser.parse_args()

    try:
        if args.action == "export":
            backup = request(args.base, args.token, "/api/backup/export")
            with open(args.out, "w", encoding="utf-8") as handle:
                json.dump(backup, handle, ensure_ascii=False, indent=2)
            manifest = backup.get("manifest", {})
            print(f"exported: {args.out}")
            print(f"created:  {manifest.get('created_at')}")
            print(f"checksum: {manifest.get('checksums', {}).get('data')}")
            return 0

        with open(args.file, encoding="utf-8") as handle:
            backup = json.load(handle)

        if args.action == "validate":
            result = request(args.base, args.token, "/api/backup/import", {"backup": backup, "dry_run": True})
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0

        if args.action == "import":
            if not args.yes:
                print("refusing to import without --yes", file=sys.stderr)
                return 2
            result = request(args.base, args.token, "/api/backup/import", {"backup": backup})
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0

        result = request(args.base, args.token, "/api/backup/rollback", {})
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"backup failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
