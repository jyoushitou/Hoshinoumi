# ===================== 兼容层 =====================
# v5-R5：人设文本在 botv/ai/persona.py，组装逻辑在 botv/ai/prompt.py
# 本文件只做转发

from .ai.prompt import (  # noqa: F401
    load_personality_supplement,
    get_system_prompt,
    LOCAL_SUPPLEMENT_FILE,
    PERSONALITY_SUPPLEMENT_URLS,
)
from .ai.persona import (  # noqa: F401
    LOCAL_SYSTEM_PROMPT,
    CODE_MODE_SYSTEM_PROMPT,
    CATEGORY_MAP,
)
