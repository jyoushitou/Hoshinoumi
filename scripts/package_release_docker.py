#!/usr/bin/env python3
"""本机打完整发布 Docker 包（bot + gateway）

    python3 scripts/package_release_docker.py --version 20.0.0

产物：
    release/REC-v20.0.0-docker.tar.gz   两个镜像（docker load 一次）
    release/REC-v20.0.0-deploy.tar.gz   compose + .env.example + 网关配置

部署机只需要：docker load、填 .env、docker compose up -d。
"""

import argparse
import gzip
import os
import shutil
import subprocess
import sys
import tarfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RELEASE = os.path.join(ROOT, "release")
DEFAULT_BOT_BASE = "python:3.12-slim"
DEFAULT_GW_BASE = "ubuntu:24.04"
DEFAULT_PIP = "https://pypi.org/simple"


def run(cmd):
    print("+ " + " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=ROOT).returncode


def save_images(tag_bot, tag_gw, out_path):
    raw = os.path.join(RELEASE, ".images.tar")
    if run(["docker", "save", tag_bot, tag_gw, "-o", raw]) != 0:
        return False
    try:
        with open(raw, "rb") as f, gzip.open(out_path, "wb") as g:
            shutil.copyfileobj(f, g)
    finally:
        try:
            os.remove(raw)
        except OSError:
            pass
    return True


def make_deploy_bundle(version):
    deploy = os.path.join(RELEASE, f"REC-v{version}-deploy")
    if os.path.isdir(deploy):
        shutil.rmtree(deploy)
    os.makedirs(os.path.join(deploy, "config"), exist_ok=True)
    shutil.copy2(os.path.join(ROOT, "docker-compose.release.yml"),
                 os.path.join(deploy, "docker-compose.yml"))
    shutil.copy2(os.path.join(ROOT, ".env.example"), os.path.join(deploy, ".env.example"))
    shutil.copy2(os.path.join(ROOT, "gateway", "config.example.json"),
                 os.path.join(deploy, "config", "gateway.json"))
    out = os.path.join(RELEASE, f"REC-v{version}-deploy.tar.gz")
    with tarfile.open(out, "w:gz") as tar:
        tar.add(deploy, arcname=f"REC-v{version}-deploy")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="20.0.0")
    ap.add_argument("--bot-base", default=DEFAULT_BOT_BASE)
    ap.add_argument("--gateway-base", default=DEFAULT_GW_BASE)
    ap.add_argument("--pip-index", default=DEFAULT_PIP)
    args = ap.parse_args()
    ver = args.version.strip().lstrip("v")
    tag_bot = f"hoshinoumi-bot:{ver}"
    tag_gw = f"hoshinoumi-gateway:{ver}"
    os.makedirs(RELEASE, exist_ok=True)

    rc = run([
        "docker", "build",
        "--build-arg", f"BASE_IMAGE={args.bot_base}",
        "--build-arg", f"PIP_INDEX_URL={args.pip_index}",
        "-t", tag_bot, ".",
    ])
    if rc != 0:
        return rc

    rc = run([
        "docker", "build",
        "-f", "gateway/Dockerfile.offline",
        "--build-arg", f"BASE_IMAGE={args.gateway_base}",
        "-t", tag_gw, ".",
    ])
    if rc != 0:
        return rc

    images = os.path.join(RELEASE, f"REC-v{ver}-docker.tar.gz")
    if not save_images(tag_bot, tag_gw, images):
        return 1
    deploy = make_deploy_bundle(ver)

    print(f"\n[OK] {os.path.relpath(images, ROOT)}")
    print(f"[OK] {os.path.relpath(deploy, ROOT)}")
    print("\n服务器：")
    print(f"  docker load -i REC-v{ver}-docker.tar.gz")
    print(f"  tar -xzf REC-v{ver}-deploy.tar.gz")
    print(f"  cd REC-v{ver}-deploy")
    print("  cp .env.example .env && vi .env")
    print("  docker compose up -d")
    return 0


if __name__ == "__main__":
    sys.exit(main())
