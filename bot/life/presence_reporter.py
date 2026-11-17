# ===================== 主账号情境上报（v34.2.0.1） =====================

import json
import os
import sys
import time
import urllib.request
from datetime import datetime

ACTIVITY_MAP = (
    ("coding", ("code", "pycharm", "idea", "vim", "terminal", "powershell", "cmd")),
    ("meeting", ("zoom", "teams", "meet", "腾讯会议", "飞书", "钉钉")),
    ("video", ("bilibili", "youtube", "netflix", "potplayer", "vlc", "抖音")),
    ("gaming", ("steam", "game", "原神", "minecraft")),
    ("reading", ("kindle", "reader", "pdf", "微信读书")),
)


def classify(title):
    t = (title or "").lower()
    for activity, words in ACTIVITY_MAP:
        if any(w in t for w in words):
            return activity
    return "unknown"


def active_window():
    """返回前台窗口标题；失败返回空串。"""
    try:
        if sys.platform.startswith("win"):
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            buf = ctypes.create_unicode_buffer(512)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, 512)
            return buf.value
        if sys.platform.startswith("linux"):
            import subprocess
            return subprocess.check_output(
                ["xdotool", "getactivewindow", "getwindowname"],
                stderr=subprocess.DEVNULL, timeout=2).decode("utf-8", "ignore").strip()
    except Exception:
        pass
    return ""


def idle_minutes():
    try:
        if sys.platform.startswith("win"):
            import ctypes
            class LASTINPUTINFO(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
            li = LASTINPUTINFO(); li.cbSize = ctypes.sizeof(li)
            ctypes.windll.user32.GetLastInputInfo(ctypes.byref(li))
            ms = ctypes.windll.kernel32.GetTickCount() - li.dwTime
            return max(0, int(ms / 60000))
        if sys.platform.startswith("linux"):
            import subprocess
            ms = int(subprocess.check_output(["xprintidle"], timeout=2).strip())
            return max(0, int(ms / 60000))
    except Exception:
        pass
    return 0


def post(activity, detail="", idle=0, host=None, port=None):
    host = host or os.getenv("NAO_API_HOST", "127.0.0.1")
    port = int(port or os.getenv("NAO_API_PORT", "27004"))
    body = json.dumps({"activity": activity, "detail": detail,
                       "idle_min": int(idle), "source": "reporter"}).encode("utf-8")
    req = urllib.request.Request(f"http://{host}:{port}/internal/presence",
                                 data=body, headers={"Content-Type": "application/json"},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=3) as r:
        return r.status == 200


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--activity", default="")
    ap.add_argument("--interval", type=int, default=30)
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args(argv)
    while True:
        activity = args.activity or classify(active_window())
        idle = idle_minutes()
        if idle >= 15 and not args.activity:
            activity = "away"
        try:
            post(activity, idle=idle)
        except Exception:
            pass
        if args.once:
            return 0
        time.sleep(max(5, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
