#!/usr/bin/env python3
"""Reference parser for Hoshinoumi .hoshinoumi plugin packages.

Usage:
    python scripts/plugin_package.py inspect path/to/plugin.hoshinoumi
    python scripts/plugin_package.py extract path/to/plugin.hoshinoumi data/plugins/weather
"""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path, PurePosixPath

MAX_PACKAGE_BYTES = 20 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
MAX_FILES = 500
ALLOWED_PERMISSIONS = {"read-only", "network", "filesystem", "db", "notifications", "finance"}
REQUIRED_FIELDS = ("id", "name", "version", "apiVersion", "entry")


class PluginPackageError(ValueError):
    pass


def _safe_member(name: str) -> bool:
    path = PurePosixPath(name)
    return bool(name) and not path.is_absolute() and ".." not in path.parts and "\\" not in name


def inspect_package(path: Path) -> dict:
    if path.suffix.lower() not in {".hoshinoumi", ".zip"}:
        raise PluginPackageError("包后缀必须是 .hoshinoumi 或 .zip")
    if not path.exists() or not path.is_file():
        raise PluginPackageError("插件包不存在")
    if path.stat().st_size > MAX_PACKAGE_BYTES:
        raise PluginPackageError("插件包超过 20 MB")
    if not zipfile.is_zipfile(path):
        raise PluginPackageError("不是有效的 ZIP 容器")

    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_FILES:
            raise PluginPackageError("文件数量超过限制")
        total = 0
        for info in infos:
            if not _safe_member(info.filename):
                raise PluginPackageError(f"非法路径：{info.filename}")
            total += info.file_size
        if total > MAX_UNCOMPRESSED_BYTES:
            raise PluginPackageError("解压后体积超过限制")
        if "plugin.json" not in archive.namelist():
            raise PluginPackageError("根目录缺少 plugin.json")
        try:
            manifest = json.loads(archive.read("plugin.json").decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PluginPackageError(f"plugin.json 不是有效 UTF-8 JSON：{exc}") from exc
        if not isinstance(manifest, dict):
            raise PluginPackageError("plugin.json 必须是对象")
        for field in REQUIRED_FIELDS:
            if not manifest.get(field):
                raise PluginPackageError(f"plugin.json 缺少字段：{field}")
        if not isinstance(manifest.get("apiVersion"), int) or manifest["apiVersion"] > 1:
            raise PluginPackageError("apiVersion 不支持")
        permissions = manifest.get("permissions", ["read-only"])
        if not isinstance(permissions, list) or any(p not in ALLOWED_PERMISSIONS for p in permissions):
            raise PluginPackageError("包含未知权限")
        entry = str(manifest["entry"])
        if PurePosixPath(entry).is_absolute() or ".." in PurePosixPath(entry).parts:
            raise PluginPackageError("entry 路径非法")
        if entry not in archive.namelist():
            raise PluginPackageError(f"entry 文件不存在：{entry}")
        return {**manifest, "permissions": permissions, "files": [i.filename for i in infos]}


def extract_package(path: Path, destination: Path) -> dict:
    manifest = inspect_package(path)
    destination = destination.resolve()
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            target = (destination / info.filename).resolve()
            if not str(target).startswith(str(destination) + str(Path.sep)):
                raise PluginPackageError(f"路径穿越：{info.filename}")
        archive.extractall(destination)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Hoshinoumi .hoshinoumi parser")
    parser.add_argument("action", choices=["inspect", "extract"])
    parser.add_argument("package")
    parser.add_argument("destination", nargs="?")
    args = parser.parse_args()
    try:
        if args.action == "inspect":
            print(json.dumps(inspect_package(Path(args.package)), ensure_ascii=False, indent=2))
            return 0
        if not args.destination:
            print("extract 需要目标目录", file=sys.stderr)
            return 2
        print(json.dumps(extract_package(Path(args.package), Path(args.destination)), ensure_ascii=False, indent=2))
        return 0
    except PluginPackageError as exc:
        print(f"invalid package: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
