"""把当前硬编码的人设导出成 personas/nao/ 卡片（一次性脚本）"""

import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARD = os.path.join(ROOT, "personas", "nao")
os.makedirs(CARD, exist_ok=True)

# 1) 主提示词：直接抄 persona.py 里的字符串
import bot.ai.persona as P  # noqa: E402

with open(os.path.join(CARD, "prompt.txt"), "w", encoding="utf-8") as f:
    f.write(P.LOCAL_SYSTEM_PROMPT.strip() + "\n")

# 2) 人设补充
src_sup = os.path.join(ROOT, "bot", "personality_supplement.txt")
if os.path.exists(src_sup):
    with open(src_sup, encoding="utf-8") as f:
        sup = f.read()
    with open(os.path.join(CARD, "supplement.txt"), "w", encoding="utf-8") as f:
        f.write(sup.strip() + "\n")

# 3) 生活事件模板（带权重头）
import bot.life.events as E  # noqa: E402

with open(os.path.join(CARD, "life.txt"), "w", encoding="utf-8") as f:
    f.write("# 每组第一行是权重，后面每行一条模板\n")
    for weight, texts in E.POOLS:
        f.write(f"# weight {weight}\n")
        for t in texts:
            f.write(t + "\n")

# 4) 状态基线
import bot.life.state as S  # noqa: E402

with open(os.path.join(CARD, "state.json"), "w", encoding="utf-8") as f:
    json.dump(S.BASE, f, ensure_ascii=False, indent=2)

print("导出完成:")
for name in sorted(os.listdir(CARD)):
    path = os.path.join(CARD, name)
    print(f"  {name:16} {os.path.getsize(path)} bytes")
