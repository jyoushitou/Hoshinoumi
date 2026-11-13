# ===================== 兼容层 =====================
# v5-R2：常量在 core/constants.py，可变状态在 core/state.py
# 本文件只转发常量，保证旧的 `from .config import X` 仍然可用
# 注意：可变状态已不在本模块，请使用 `from bot.core import state as cfg`

from .core.constants import *  # noqa: F401,F403
