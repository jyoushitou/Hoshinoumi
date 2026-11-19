#!/usr/bin/env python3
"""v35.4.15: 后端启动器；进程名显示为 nao-run，兼容 run.py。"""
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from bot.core.process_name import set_process_name

if __name__ == "__main__":
    set_process_name()
    runpy.run_path(str(ROOT / "run.py"), run_name="__main__")
