#!/usr/bin/env bash
# 检查 Linux 服务器能否跑 Android 容器/模拟器（番茄 App 读取）
# 用法：bash scripts/check_android_worker.sh
set -u

echo "== OS / kernel =="
uname -a
[ -f /etc/os-release ] && . /etc/os-release && echo "${PRETTY_NAME:-unknown}"

echo
echo "== CPU / 虚拟化 =="
echo "nproc: $(nproc 2>/dev/null || echo '?')"
if grep -Eq '(vmx|svm)' /proc/cpuinfo 2>/dev/null; then
  echo "CPU 虚拟化标志: 有（可能支持 KVM）"
else
  echo "CPU 虚拟化标志: 无（Android AVD 基本不可用）"
fi
if [ -e /dev/kvm ]; then
  echo "/dev/kvm: 存在"
  ls -l /dev/kvm
else
  echo "/dev/kvm: 不存在（AVD 不可用）"
fi

echo
echo "== binder（Waydroid / redroid 关键）=="
if grep -q binder /proc/filesystems 2>/dev/null; then
  echo "/proc/filesystems: 有 binder"
else
  echo "/proc/filesystems: 没有 binder"
fi
if lsmod 2>/dev/null | grep -q '^binder'; then
  echo "lsmod: binder 已加载"
else
  echo "lsmod: 未看到 binder"
fi
ls -l /dev/binder* 2>/dev/null || echo "/dev/binder*: 不存在"

echo
echo "== 内存 =="
free -h 2>/dev/null || true

echo
echo "== 已安装组件 =="
for c in waydroid redroid docker adb weston Xvfb; do
  if command -v "$c" >/dev/null 2>&1; then
    echo "$c: $(command -v "$c")"
  else
    echo "$c: 未安装"
  fi
done

echo
echo "== 结论参考 =="
echo "Waydroid: 需要 binder + Wayland/Weston（或 Xvfb）"
echo "redroid:  需要 binder + 特权容器 + 足够内存"
echo "AVD:      需要 /dev/kvm + x86_64 镜像"
echo "三者都没有：这台服务器不适合跑 Android，考虑云手机或换机器。"
