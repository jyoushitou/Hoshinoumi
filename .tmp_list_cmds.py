import sys, types
try:
    import jieba
except ImportError:
    m=types.ModuleType('jieba'); m.lcut=lambda s:list(s); sys.modules['jieba']=m
import bot.commands
from bot.cmd import registry
for n,c in sorted(registry.COMMANDS.items()):
    desc=(c.help_text or (c.handler.__doc__ or '').splitlines()[0] if (c.handler.__doc__ or '').strip() else '')
    print(f"{n:14} | {desc.strip()}")
