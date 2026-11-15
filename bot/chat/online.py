# ===================== 上线提示（v25.7） =====================
# 首次启动 / 热更新 / 普通上线，三种措辞分开。

from ..core.version import get_version


def notice_text(mode, version=""):
    ver = version or get_version()
    if mode == "first":
        return (f"第一次上线完成。\n"
                f"我是友利奈绪，版本 {ver}。\n"
                f"连接正常，接下来请多指教。")
    if mode == "hot":
        return (f"热更新完成，我已经换到 {ver} 了。\n"
                f"旧连接还在收尾，新消息由新版本回复。")
    return "哼,上线了(叉腰)"
