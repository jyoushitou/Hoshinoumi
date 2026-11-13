#!/usr/bin/env python3
"""构建 C++ 网关 Docker 镜像并导出（v20.0）

    python3 scripts/build_gateway.py --version 20.0.0
    # release/REC-v20.0.0-docker.tar.gz
"""

import argparse
import gzip
import os
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
    args = ap.parse_args()
    ver = args.version.strip().lstrip("v")
    tag = f"hoshinoumi-gateway:{ver}"

    rc = run(["docker", "build", "-f", "gateway/Dockerfile", "-t", tag, "."]).returncode
    if rc != 0:
        print("[X] docker build 失败")
        return rc
    if args.no_save:
        return 0

    os.makedirs(DIST, exist_ok=True)
    out = os.path.join(DIST, docker_name(ver))
    print(f"\n>> 导出 {os.path.relpath(out, ROOT)}")
    with gzip.open(out, "wb") as f:
        p = subprocess.Popen(["docker", "save", tag], stdout=subprocess.PIPE)
        assert p.stdout is not None
        while True:
            chunk = p.stdout.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
        p.wait()
    if p.returncode != 0:
        print("[X] docker save 失败")
        return p.returncode
    print(f"[OK] {os.path.relpath(out, ROOT)}（{os.path.getsize(out) / 1024 / 1024:.0f} MB）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
