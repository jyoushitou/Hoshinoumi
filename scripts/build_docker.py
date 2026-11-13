#!/usr/bin/env python3
# ===================== Docker 镜像构建 =====================
#     python3 scripts/build_docker.py --version 16.0.0
#     python3 scripts/build_docker.py --version 16.0.0 --browser   # 带 Chromium
#     python3 scripts/build_docker.py --version 16.0.0 --save      # 导出 tar.gz
#
# 产物：
#     hoshinoumi:16.0.0         本地镜像
#     release/REC-v16.0.0-docker.tar.gz  可拷到别的机器 docker load 的整包

import argparse
import os
import platform
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "release")   # v17.x：打包产物集中放这里

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from artifact_names import docker as docker_name  # noqa: E402


def run(cmd):
    print("  $ " + " ".join(cmd))
    rc = subprocess.call(cmd, cwd=ROOT)
    return rc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True, help="形如 16.0.0")
    ap.add_argument("--browser", action="store_true", help="把 Chromium 打进镜像")
    ap.add_argument("--save", action="store_true", help="导出 tar.gz")
    ap.add_argument("--compose", action="store_true", help="用 docker compose 构建")
    args = ap.parse_args()

    version = args.version.strip().lstrip("v")
    tag = f"hoshinoumi:{version}"
    if args.browser:
        tag += "-browser"

    print("=" * 56)
    print(f"  构建镜像 {tag}（{platform.system()}）")
    print("=" * 56)

    if subprocess.call(["docker", "--version"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL) != 0:
        print("\n[X] 没装 docker，或者当前用户没有权限")
        print("   检查：docker --version / sudo usermod -aG docker $USER")
        return 1

    # 守护进程没起时，docker build 的报错很难看懂，先探一下
    rc_info = subprocess.call(["docker", "info"], stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
    if rc_info != 0:
        print("\n[X] docker 命令有了，但**守护进程没运行**")
        print("   Linux：sudo systemctl start docker")
        print("   Windows/macOS：先打开 Docker Desktop")
        print("   验证：docker info | head -5")
        return 1

    if args.compose:
        rc = run(["docker", "compose", "build"])
        if rc == 0:
            rc = run(["docker", "tag", "hoshinoumi:19.5.7", tag])
    else:
        cmd = ["docker", "build", "-t", tag, "--build-arg",
               f"WITH_BROWSER={'1' if args.browser else '0'}", "."]
        rc = run(cmd)

    if rc != 0:
        print(f"\n[X] 构建失败（退出码 {rc}）")
        return rc

    print(f"\n[OK] 镜像已生成：{tag}")
    if not args.save:
        print("   导出 tar.gz：加 --save")
        return 0

    os.makedirs(DIST, exist_ok=True)
    out = os.path.join(DIST, docker_name(version, args.browser))
    print(f"\n>> 导出 {os.path.relpath(out, ROOT)}")
    with open(out, "wb") as f:
        p1 = subprocess.Popen(["docker", "save", tag], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(["gzip", "-c"], stdin=p1.stdout, stdout=f)
        p1.stdout.close()
        p2.communicate()
        p1.wait()
    if p2.returncode == 0:
        size = os.path.getsize(out) / 1024 / 1024
        print(f"[OK] {os.path.relpath(out, ROOT)}（{size:.0f} MB）")
        print(f"   别的机器：docker load -i {os.path.basename(out)}")
    else:
        print("[X] 导出失败")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

