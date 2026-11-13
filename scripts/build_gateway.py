#!/usr/bin/env python3
"""构建 C++ 网关 Docker 镜像并导出（v20.0）

    python3 scripts/build_gateway.py --version 20.0.0
    # release/REC-v20.0.0-docker.tar.gz
"""

import argparse
import gzip
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "release")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from artifact_names import docker as docker_name  # noqa: E402


def run(cmd, **kw):
    print("+ " + " ".join(cmd))
    return subprocess.run(cmd, cwd=ROOT, **kw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="20.0.0")
    ap.add_argument("--no-save", action="store_true")
    ap.add_argument("--offline", action="store_true",
                    help="用系统 Boost/OpenSSL 构建，不依赖 vcpkg/GitHub")
    ap.add_argument("--base-image", default="",
                    help="覆盖基础镜像，例如 docker.m.daocloud.io/library/ubuntu:24.04")
    args = ap.parse_args()
    ver = args.version.strip().lstrip("v")
    tag = f"hoshinoumi-gateway:{ver}" + ("-offline" if args.offline else "")
    dockerfile = "gateway/Dockerfile.offline" if args.offline else "gateway/Dockerfile"

    cmd = ["docker", "build", "-f", dockerfile, "-t", tag]
    if args.base_image:
        cmd += ["--build-arg", f"BASE_IMAGE={args.base_image}"]
    cmd.append(".")
    rc = run(cmd).returncode
    if rc != 0:
        print("[X] docker build 失败")
        return rc
    if args.no_save:
        return 0

    os.makedirs(DIST, exist_ok=True)
    out = os.path.join(DIST, docker_name(ver))
    tmp = os.path.join(DIST, ".docker-save.tar")
    print(f"\n>> 导出 {os.path.relpath(out, ROOT)}")
    if run(["docker", "save", tag, "-o", tmp]).returncode != 0:
        print("[X] docker save 失败")
        return 1
    try:
        with open(tmp, "rb") as f, gzip.open(out, "wb") as g:
            shutil.copyfileobj(f, g)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
    print(f"[OK] {os.path.relpath(out, ROOT)}（{os.path.getsize(out) / 1024 / 1024:.0f} MB）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
