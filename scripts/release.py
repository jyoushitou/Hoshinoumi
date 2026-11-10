#!/usr/bin/env python3
# ===================== 发布脚本 =====================
# 一条命令做完整套：检查 → 打 tag → 打包 → 生成发布说明
#
#     python3 scripts/release.py --version v14.2            # 预演，不改任何东西
#     python3 scripts/release.py --version v14.2 --apply    # 真的发布
#
# 做的事：
#   1. 检查工作区干净
#   2. 跑静态检查 + 全部测试
#   3. 打附注 tag（vX.Y），并把「正式版」移到最新
#   4. 生成 release/nao-vX.Y.Z.bundle（**带 tag**）
#   5. 写 docs/RELEASE-NOTES.md（相对上一个版本的提交列表）

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "release")   # v17.x：打包产物集中放这里
NOTES = os.path.join(ROOT, "docs", "RELEASE-NOTES.md")


def _ver(v):
    """版本号去掉开头的 v（避免打成 nao-vv17.1.1）"""
    return str(v).lstrip("vV")


def run(cmd, check=True, capture=True):
    """跑一个命令，返回 (退出码, 输出)"""
    proc = subprocess.run(
        cmd, cwd=ROOT, shell=isinstance(cmd, str),
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
        text=True, encoding="utf-8", errors="ignore",
    )
    if check and proc.returncode != 0:
        print(f"❌ 命令失败: {cmd}")
        print((proc.stdout or "")[-800:])
        print((proc.stderr or "")[-800:])
        sys.exit(1)
    return proc.returncode, (proc.stdout or "").strip()


def step(name, fn):
    print(f"\n▶ {name}")
    return fn()


def check_clean():
    _, out = run(["git", "status", "--porcelain"])
    if out:
        print("   工作区不干净：")
        for line in out.splitlines()[:10]:
            print("     " + line)
        sys.exit(1)
    print("   ✅ 工作区干净")


def check_static():
    code, out = run([sys.executable, os.path.join("scripts", "check_names.py")], check=False)
    if code != 0:
        print(out)
        sys.exit(1)
    print("   ✅ 静态检查通过")


def check_tests():
    code, out = run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], check=False)
    last = [ln for ln in out.splitlines() if ln.startswith(("Ran ", "OK", "FAILED"))]
    for line in last:
        print("   " + line)
    if code != 0:
        sys.exit(1)


def previous_tag():
    code, out = run(["git", "describe", "--tags", "--abbrev=0", "--exclude=正式版"], check=False)
    return out if code == 0 and out else ""


def commit_list(prev):
    rng = f"{prev}..HEAD" if prev else "HEAD"
    _, out = run(["git", "log", "--oneline", "--no-decorate", rng])
    return out.splitlines()


def write_notes(version, prev, commits):
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# {version} 发布说明",
        "",
        f"- 发布时间：{stamp}",
        f"- 上一个版本：{prev or '（首次）'}",
        f"- 提交数：{len(commits)}",
        "",
        "## 本次变更",
        "",
    ]
    lines += [f"- {c}" for c in commits] or ["- （无）"]
    lines += [
        "",
        "## 升级步骤",
        "",
        "```bash",
        f"git pull ./nao-v{_ver(version)}.bundle main",
        "python3 scripts/preflight.py",
        "python3 -m unittest discover -s tests",
        "# 重启进程",
        "```",
        "",
        "## 回滚",
        "",
        "```bash",
        f"git reset --hard {prev or 'HEAD~1'}",
        "```",
        "",
    ]
    os.makedirs(os.path.dirname(NOTES), exist_ok=True)
    with open(NOTES, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"   ✅ 已写 {os.path.relpath(NOTES, ROOT)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True, help="形如 v16.0.0（必须三段）")
    ap.add_argument("--apply", action="store_true", help="真的执行（默认只预演）")
    ap.add_argument("--no-正式版", dest="move_stable", action="store_false",
                    help="不移动「正式版」标签")
    ap.add_argument("--allow-dirty", action="store_true", help="仅测试用：跳过工作区检查")
    args = ap.parse_args()

    version = args.version.strip()
    if not version.startswith("v"):
        version = "v" + version
    if not re.fullmatch(r"v\d+\.\d+\.\d+", version):
        print(f"❌ 版本号必须是三段式 vX.Y.Z（收到 {version}）")
        print("   例：v16.0.0 / v16.1.2")
        sys.exit(1)

    print("=" * 56)
    print(f"  发布 {version}  " + ("" if args.apply else "（预演模式）"))
    print("=" * 56)

    if args.allow_dirty:
        print("   ⚠️ 跳过了工作区检查（--allow-dirty）")
    else:
        step("检查工作区", check_clean)
    step("静态检查", check_static)
    step("运行测试", check_tests)

    prev = previous_tag()
    commits = commit_list(prev)
    print(f"\n   上一个版本：{prev or '（无）'}")
    print(f"   待发布提交：{len(commits)} 条")
    for c in commits[:8]:
        print("     " + c)

    if not args.apply:
        print("\n预演结束。确认无误后加 --apply 真跑。")
        return 0

    # 打 tag
    print(f"\n▶ 打 tag {version}")
    run(["git", "tag", "-a", version, "-m", f"{version} 正式发布"])
    print(f"   ✅ {version}")
    if args.move_stable:
        # 显式指定目标提交，并**验证真的挪了**（之前这步静默失败过）
        _, head = run(["git", "rev-parse", "HEAD"])
        run(["git", "tag", "-f", "-a", "正式版", head, "-m", f"正式版：{version}"])
        _, stable = run(["git", "rev-parse", "正式版^{commit}"])
        if not stable.startswith(head[:7]):
            print(f"   ❌ 正式版没挪成功：{stable[:7]} != {head[:7]}")
            sys.exit(1)
        print(f"   ✅ 正式版 → {version}（{head[:7]}）")

    # 打包（带 tag）
    os.makedirs(DIST, exist_ok=True)
    bundle = os.path.join(DIST, f"nao-v{_ver(version)}.bundle")
    run(["git", "bundle", "create", bundle, "main", "--tags"])
    size = os.path.getsize(bundle) / 1024
    print(f"   ✅ {os.path.relpath(bundle, ROOT)}（{size:.0f} KB）")

    # 发布说明
    print("\n▶ 生成发布说明")
    write_notes(version, prev, commits)

    print("\n🎉 发布完成")
    print(f"   包：{os.path.relpath(bundle, ROOT)}")
    print(f"   说明：{os.path.relpath(NOTES, ROOT)}")
    print("   tag 只在本地；要同步到服务器，用这个 bundle 拉过去即可。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
