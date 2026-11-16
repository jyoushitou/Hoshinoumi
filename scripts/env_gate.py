# ===================== v29.3 蓝绿发布环境门禁 =====================
# 新版本进入 prepare_worker / supervisor 前，必须有新鲜、匹配的环境报告。

from pathlib import Path


class EnvGateError(RuntimeError):
    pass


def check_report(report, expected_version):
    """纯校验：报告存在、版本匹配；详细 config/时效由 features.read_report 负责。"""
    if not report:
        raise EnvGateError("没有环境监测报告；先运行 python3 checks/env_check.py")
    got = str(report.get("version") or "").lstrip("v")
    want = str(expected_version or "").lstrip("v")
    if not got:
        raise EnvGateError("环境报告缺少 version；先重跑 python3 checks/env_check.py")
    if got != want:
        raise EnvGateError(
            f"环境报告版本 {got} 与当前代码 {want} 不符；先重跑 checks/env_check.py")
    return True


def require_env_check():
    """给 prepare_worker / supervisor 调用；失败抛 EnvGateError。"""
    from bot.core import features, version

    data = features.load()
    ok, reason, report = features.read_report(data)
    if not ok:
        raise EnvGateError(f"{reason}；先运行 python3 checks/env_check.py")
    check_report(report, version.get_version())
    return report
