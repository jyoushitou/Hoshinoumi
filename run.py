# ===================== 模块入口 =====================
# 友利奈绪 QQ 机器人 v2.0 — CLIP视觉识图 + 简短动作回复 + HTTP API 服务
# 不导入任何模块，避免循环依赖
# 所有子模块通过 botv.xxx 方式导入

import os               # 环境变量开关
import sys              # 系统模块：退出程序、获取解释器路径
import subprocess       # 子进程：执行 pip install
import importlib.util   # 导入工具：动态检查模块是否已安装

# ===================== 依赖检查与自动安装 =====================
# 项目所需的所有依赖包列表
REQUIRED_PACKAGES = [
    "websockets",       # WebSocket 服务器：与 QQ 协议端通信
    "requests",         # HTTP 请求：调用外部 API
    "urllib3",          # HTTP 底层库：requests 的底层依赖
    "pymysql",          # MySQL 数据库：存储聊天记录
    "jieba",            # 中文分词：自然语言处理
    "Pillow",           # 图片处理（PIL）：处理用户图片
    "aiohttp",          # HTTP API 服务器：提供外部接口
]

# 可选依赖（缺失只降级，绝不自动安装——没网会卡死）
OPTIONAL_PACKAGES = [
    "chinesecalendar",  # 中国节假日判断（可选，降级为 weekday）
    "torch",            # PyTorch：CLIP 模型需要
]

# 体积小、缺了就少一块功能的包：启动时尝试装一次（装不上就降级）
# 规则：单个包 < 5MB 才放进来，torch 这种几百 MB 的永远不许自动装
AUTO_OPTIONAL_PACKAGES = [
    "edge-tts",         # 语音合成（pip 名），import 名是 edge_tts
]

# 装超时就放弃，别把启动卡死
INSTALL_TIMEOUT = 120

# ===================== 函数定义 =====================
def _lock_timezone():
    """v18.0：把进程时区锁到东八区（服务器常是 UTC，会差 8 小时）"""
    try:
        from botv.core import clock

        changed = clock.ensure_tz()
        print(f"[启动] 时区 Asia/Shanghai（{'已纠正' if changed else '原本正确'}）"
              f"，当前 {clock.fmt_full()}")
    except Exception as e:
        print(f"[启动] 时区设置失败：{e}")


def _runtime_gate():
    """v19.0：只读功能清单 + 环境监测报告；只保留网络/人设运行时探测"""
    from botv.core import features

    try:
        data = features.load()
    except Exception as e:
        print(f"❌ 功能清单不可用：{e}")
        return False

    ok, reason, report = features.read_report(data)
    if not ok:
        print("=" * 60)
        print(f"❌ 还没有有效的环境监测报告：{reason}")
        print("先运行：python3 checks/env_check.py")
        print("=" * 60)
        return False

    feats = report.get("features") or {}
    for name, conf in (data.get("features") or {}).items():
        if not conf.get("enabled"):
            continue
        available = bool((feats.get(name) or {}).get("available"))
        if conf.get("required") and not available:
            detail = (feats.get(name) or {}).get("reason") or "不可用"
            print(f"❌ 必需能力 {name} 不可用：{detail}")
            return False
        if not available:
            print(f"⚠️ 能力 {name} 不可用，已降级：{(feats.get(name) or {}).get('reason', '')}")

    try:
        from botv.app.runtime_checks import check_network, check_persona

        try:
            detail = check_network()
            print(f"[启动] {detail}")
        except Exception as e:
            if (data.get("environment") or {}).get("network_required", True):
                print(f"❌ {e}")
                return False
            print(f"⚠️ {e}（network_required=false，继续）")
        try:
            detail = check_persona()
            print(f"[启动] {detail}")
        except Exception as e:
            print(f"❌ {e}")
            return False
    except Exception as e:
        print(f"❌ 运行时探测失败：{e}")
        return False
    return True


def check_and_install(package_name, optional=False, allow_install=False):
    """检查包是否已安装，未安装则优先用 Ubuntu apt 命令自动安装，失败回退 pip"""
    # 特殊处理：某些 pip 包名 ≠ 导入模块名
    IMPORT_NAME_MAP = {
        "Pillow": "PIL",          # Pillow 的 import 名是 PIL
        "PIL": "PIL",
        "chinesecalendar": "chinese_calendar",  # pip 包名是 chinesecalendar，但 import 是 chinese_calendar
        "edge-tts": "edge_tts",   # 语音合成（pip 名带横线）
        "pyyaml": "yaml",         # 备用
        "beautifulsoup4": "bs4",  # 备用
    }
    import_name = IMPORT_NAME_MAP.get(package_name, package_name)
    
    
    try:
        importlib.import_module(import_name)  # 尝试导入
        print(f"{package_name}导入成功")
        return True  # 已安装
    except ImportError:
        pass  # 未安装，继续安装流程
    
    # Python 包名 → Ubuntu apt 包名映射
    APT_MAP = {
        "websockets": "python3-websockets",   # WebSocket 服务器
        "requests": "python3-requests",       # HTTP 请求
        "urllib3": "python3-urllib3",         # HTTP 底层库
        "pymysql": "python3-pymysql",         # MySQL 数据库
        "jieba": "python3-jieba",             # 中文分词
        "Pillow": "python3-pil",              # 图片处理（PIL）
        "PIL": "python3-pil",
        "aiohttp": "python3-aiohttp",         # HTTP API 服务器
        "chinesecalendar": "python3-chinesecalendar",  # 中国节假日
        "torch": "pytorch",                   # PyTorch（apt 通常没有，会回退 pip）
        "transformers": "python3-transformers",  # HuggingFace（apt 通常没有，会回退 pip）
    }
    
    # 未安装，尝试自动安装
    tag = "[可选]" if optional else "[必需]"
    # 可选依赖默认只检查；只有 allow_install=True 的小包才尝试安装
    if optional and not allow_install:
        print(f"{tag} 未安装 {package_name}（可选，跳过安装，功能降级）")
        return False
    if optional and allow_install:
        print(f"{tag} 尝试安装 {package_name}（装不上就降级）...")
    print(f"{tag} 正在安装 {package_name}...")
    apt_pkg = APT_MAP.get(package_name)
    
    # ① 优先使用 Ubuntu apt 命令安装系统包
    if apt_pkg:
        try:
            subprocess.check_call(  # 执行 apt-get install
                ["sudo", "apt-get", "install", "-y", apt_pkg],
                stdout=subprocess.DEVNULL,  # 丢弃标准输出
                stderr=subprocess.DEVNULL,  # 丢弃错误输出
                timeout=INSTALL_TIMEOUT,
            )
            # 安装后验证模块是否可用
            if importlib.util.find_spec(import_name) is not None:
                print(f"  ✅ {package_name} 安装成功（apt）")
                return True
        except Exception:
            pass  # apt 失败，回退到 pip

    # ② apt 没有对应包或安装失败 → 回退到 pip install
    # 使用 --break-system-packages 绕过 Ubuntu 24.04 的 PEP 668 限制
    # （Ubuntu 23.04+ 默认禁止 pip 直接安装到系统 Python）
    try:
        # torch 特殊处理：默认源包含 CUDA 依赖，体积巨大（>800MB）且容易失败
        # 改用官方 CPU 专用源，体积小（~200MB）更适合无 GPU 服务器
        pip_cmd = [sys.executable, "-m", "pip", "install", package_name, "-q", "--break-system-packages"]
        if package_name == "torch":
            pip_cmd += ["--index-url", "https://download.pytorch.org/whl/cpu"]
            print(f"  🔧 使用 CPU 版 PyTorch 源（无 GPU 服务器专用）...")
        subprocess.check_call(
            pip_cmd,
            stdout=subprocess.DEVNULL,  # 丢弃标准输出
            stderr=subprocess.DEVNULL,  # 丢弃错误输出
            timeout=INSTALL_TIMEOUT
        )
        # 安装后再次验证，防止 pip 返回码为 0 但模块实际不可用

        # 直接 import 验证（比 find_spec 更贴近真实导入结果，避免误判）
        try:
            importlib.import_module(import_name)
        except Exception:
            raise ImportError(f"{package_name} 安装后验证失败：模块仍不可导入")
        print(f"  ✅ {package_name} 安装成功（pip）")
        return True
    except Exception as e:
        if optional:
            print(f"  ⚠️ {package_name} 安装失败（可选，跳过）: {e}")
            return False
        else:
            print(f"  ❌ {package_name} 安装失败: {e}")
            print(f"  💡 请手动执行: sudo apt-get install {apt_pkg or package_name} 或 pip install {package_name}")
            return False

def check_all_dependencies():
    """检查并安装所有依赖"""
    print("=" * 50)
    print("  🤖 友利奈绪 QQ 机器人 — 依赖检查")
    print("=" * 50)
    print()
    
    all_ok = True  # 标记所有必需依赖是否成功
    
    # 检查必需依赖
    print("📦 必需依赖：")
    for pkg in REQUIRED_PACKAGES:
        if not check_and_install(pkg, optional=False):
            all_ok = False  # 任一必需依赖失败 → 标记
        else :
            print(f"必需的软件包：{pkg} 存在！",end=" ")
    
    print(" ")
    
    # 检查可选依赖
    print("📦 可选依赖（不影响基础功能）：")
    for pkg in OPTIONAL_PACKAGES:
        check_and_install(pkg, optional=True)  # 可选失败不影响 all_ok

    # 小体积增强包：启动时试着装一次（装了功能更全，装不上就降级）
    no_auto = os.getenv("NAO_NO_AUTOINSTALL") == "1"
    print("📦 可选增强（缺失会尝试自动安装，可用 NAO_NO_AUTOINSTALL=1 关闭）：")
    for pkg in AUTO_OPTIONAL_PACKAGES:
        check_and_install(pkg, optional=True, allow_install=not no_auto)
    
    print(" ")
    
    if all_ok:
        print("✅ 所有必需依赖已就绪，启动机器人...")
    else:
        print("⚠️ 部分依赖安装失败，请手动安装后重试")
        print("   命令: pip install -r requirements.txt")
    
    print("=" * 50)
    print()
    return all_ok


# ===================== 日记功能自检（启动追溯） =====================
# 启动时检查 diaries 表是否为空，若为空则追溯最近7天有事件记录的日期，
# 调用 AI 生成日记并写入 diaries 表，确保日记功能有历史数据可展示/测试

async def check_diary():
    """
    日记功能自检：
    1. 确保 diaries 表存在（main.py 启动时也会创建，这里先建避免自检报错）
    2. 若 diaries 表无任何历史日记 → 调用 diary.py 的 generate_missing_7day_diaries()
       追溯最近有事件记录的日期（最多7天），逐天生成日记并写入 diaries 表
    3. 生成后打印验证日志，确认日记功能正常
    """
    try:
        # 延迟导入，避免循环依赖
        from botv.db import get_cursor
        from botv.config import MASTER_QQ
        from botv.diary import generate_missing_7day_diaries
        from botv.log import log_system

        tid = str(MASTER_QQ)

        # ---- 1. 确保 diaries 表存在 ----
        c = get_cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS diaries (
                id INT AUTO_INCREMENT PRIMARY KEY,
                target_id VARCHAR(50) NOT NULL,
                diary_date DATE NOT NULL,
                content TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_target_date (target_id, diary_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        c.connection.commit()

        # ---- 2. 调用统一的追溯生成函数 ----
        # 若 diaries 表已有日记或 events 表无记录，函数内部会自动跳过
        generated, skipped = await generate_missing_7day_diaries(tid)

        # ---- 3. 输出自检结果 ----
        if generated:
            log_system(f"日记自检通过 ✅ 本次追溯生成 {len(generated)} 篇日记: {', '.join(generated)}")
            if skipped:
                log_system(f"  跳过 {len(skipped)} 篇: {', '.join(skipped)}")
        elif skipped:
            log_system(f"日记自检完成：有事件记录但生成失败/跳过 {len(skipped)} 篇")
        else:
            log_system("日记自检：无追溯生成（已有日记或 events 无记录，跳过不影响启动）")

        # ---- 4. 验证：查询 diaries 表确认写入成功 ----
        c.execute("SELECT COUNT(*) AS n FROM diaries WHERE target_id=%s", (tid,))
        total = c.fetchone()["n"] or 0
        log_system(f"日记自检：{tid} 当前共有 {total} 篇日记")
    except Exception as e:
        log_system(f"日记自检跳过（非致命错误）: {e}")


# ===================== 启动入口 =====================
import asyncio  # 异步 IO：运行主函数

if __name__ == "__main__":  # 直接运行本文件时
    # v19.0：环境监测报告 + 网络/人设运行时探测；不再扫依赖/建表/查密钥
    if not _runtime_gate():
        sys.exit(1)
    _lock_timezone()

    # v7-E32：单实例锁——同一时刻只允许一个进程连 NapCat
    from botv.core.single_instance import acquire, release, holder_pid
    if not acquire():
        print(f"❌ 已有实例在运行（PID {holder_pid()}），本次退出")
        sys.exit(1)

    # 依赖检查通过后再导入主模块（延迟导入，避免依赖缺失时崩溃）
    from botv.main import main
    # 启动机器人（先运行主程序，上线消息发出10分钟后再追溯日记）
    async def _start():
        main_task = asyncio.create_task(main())  # 启动主程序（异步，不阻塞后续延迟任务）
        try:
            # 延迟10分钟再追溯日记：确保 API key 已从数据库加载、上线消息已发出、CLIP模型已就绪
            # 平时日记只在凌晨3点由 schedule.py 的定时任务生成，这里仅做历史补录
            await asyncio.sleep(600)  # 600秒=10分钟
            await check_diary()       # 日记追溯：若 diaries 表为空则补录最近7天有事件记录的日期
            await main_task           # 等待主程序退出
        finally:
            # 退出时确保主程序被取消，避免留下悬挂的 WebSocket 连接
            if not main_task.done():
                main_task.cancel()

    try:
        asyncio.run(_start())
    except KeyboardInterrupt:
        # 第一次 Ctrl-C 走到这里：干净退出，不打印调用栈
        print("\n[已中断] 收到 Ctrl-C，程序退出。")
        sys.exit(130)
    except Exception as e:  # v7-E33：启动失败给人话，不给栈
        print(f"\n❌ 启动失败：{type(e).__name__}: {e}")
        print("   建议先跑：python3 scripts/preflight.py")
        sys.exit(1)
    finally:
        release()
