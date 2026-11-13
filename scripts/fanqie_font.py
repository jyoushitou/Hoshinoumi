#!/usr/bin/env python3
# ===================== 番茄字体解密（探查版） =====================
# 番茄把正文里的字替换成私有区码点（U+E000~U+F8FF），再挂一个自定义字体渲染。
#
# 关键发现：字体元数据里写着 SourceHanSansSC / Adobe —— 是**思源黑体的子集**。
# 所以不需要 OCR：把私有区字形和思源黑体里每个汉字的字形轮廓比对，能对上就是原字。
#
# 用法（服务器上）：
#     python3 scripts/fanqie_font.py                 # 自动找参考字体
#     python3 scripts/fanqie_font.py <章节URL>
#     python3 scripts/fanqie_font.py <章节URL> <参考字体路径>
#
# 依赖：
#     python3 -m pip install --user --break-system-packages fonttools brotli
#     apt install fonts-noto-cjk        # 参考字体（和思源黑体同源）

import os
import re
import sys

# 允许直接 `python3 scripts/xxx.py` 运行时也能 import bot
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

CHAPTER_URL = "https://fanqienovel.com/reader/7688347832079614488"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# 参考字体（思源黑体 / Noto Sans CJK 同源，字形一致）
REF_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/source-han-sans/SourceHanSansSC-Regular.otf",
    "/usr/share/fonts/truetype/arphic/uming.ttc",
]

CJK = lambda cp: 0x4E00 <= cp <= 0x9FFF          # noqa: E731
PUA = lambda cp: 0xE000 <= cp <= 0xF8FF          # noqa: E731


def find_ref_font(explicit=None):
    if explicit and os.path.exists(explicit):
        return explicit
    for p in REF_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


def fetch_chapter(url=CHAPTER_URL):
    import requests
    r = requests.get(url, timeout=20, headers={"User-Agent": UA})
    r.raise_for_status()
    return r.text


def find_font_url(html):
    m = re.search(r'url\((https?://[^)]+\.woff2)\)', html)
    if not m:
        m = re.search(r'url\((https?://[^)]+\.otf)\)', html)
    return m.group(1) if m else None


def signature(font, glyph_name, grid=64):
    """把字形轮廓归一化成一个可比较的签名

    取所有轮廓点，平移到包围盒原点、按最大边长缩放到 grid，再取整。
    这样即使坐标整体平移/缩放，签名也一致。
    """
    from fontTools.pens.recordingPen import RecordingPen

    glyph_set = font.getGlyphSet()
    try:
        glyph = glyph_set[glyph_name]
    except Exception:
        return None
    pen = RecordingPen()
    try:
        glyph.draw(pen)
    except Exception:
        return None

    pts = []
    for op, args in pen.value:
        for a in args:
            if isinstance(a, tuple) and len(a) == 2:
                pts.append(a)
    if len(pts) < 3:
        return None

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    w = max(maxx - minx, 1e-6)
    h = max(maxy - miny, 1e-6)
    scale = grid / max(w, h)

    norm = tuple(sorted(
        (round((x - minx) * scale), round((y - miny) * scale))
        for x, y in pts
    ))
    return (len(norm), norm)


def build_reference(ref_path, cache_path=None):
    """参考字体：汉字 → 字形签名"""
    from fontTools.ttLib import TTFont, TTCollection
    import json

    if cache_path and os.path.exists(cache_path):
        try:
            with open(cache_path, encoding="utf-8") as f:
                raw = json.load(f)
            return {tuple(v): k for k, v in raw.items()}
        except Exception:
            pass

    if ref_path.lower().endswith(".ttc"):
        coll = TTCollection(ref_path)
        font = None
        for f in coll.fonts:
            if "SC" in (f["name"].getDebugName(1) or "") or "CJK" in (f["name"].getDebugName(1) or ""):
                font = f
                break
        font = font or coll.fonts[0]
    else:
        font = TTFont(ref_path)

    cmap = font.getBestCmap() or {}
    table = {}
    for cp, gname in cmap.items():
        if not CJK(cp):
            continue
        sig = signature(font, gname)
        if sig:
            table[sig] = chr(cp)

    if cache_path:
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump({str(k): v for k, v in table.items()}, f, ensure_ascii=False)
        except Exception:
            pass
    return table


def build_mapping(font_path, ref_table):
    """番茄字体：私有区码点 → 原字"""
    from fontTools.ttLib import TTFont

    font = TTFont(font_path)
    cmap = font.getBestCmap() or {}
    mapping = {}
    miss = 0
    for cp, gname in cmap.items():
        if not PUA(cp):
            continue
        sig = signature(font, gname)
        if sig and sig in ref_table:
            mapping[chr(cp)] = ref_table[sig]
        else:
            miss += 1
    return mapping, len(mapping), miss


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else CHAPTER_URL
    ref_path = find_ref_font(sys.argv[2] if len(sys.argv) > 2 else None)

    print("=== 1. 取章节 ===")
    html = fetch_chapter(url)
    print(f"  HTML 长度：{len(html)}")

    print("=== 2. 找字体 ===")
    font_url = find_font_url(html)
    print(f"  字体：{font_url}")
    if not font_url:
        print("  没找到字体，可能页面结构变了")
        return 1

    import tempfile
    import requests
    tmpdir = tempfile.mkdtemp(prefix="fq-font-")
    font_path = os.path.join(tmpdir, "obfuscated.otf")
    r = requests.get(font_url, timeout=30, headers={"User-Agent": UA})
    with open(font_path, "wb") as f:
        f.write(r.content)
    print(f"  已下载：{len(r.content)} 字节")

    print("=== 3. 参考字体 ===")
    print(f"  路径：{ref_path}")
    if not ref_path:
        print("  没找到参考字体！先跑：apt install fonts-noto-cjk")
        return 1
    ref_table = build_reference(ref_path, os.path.expanduser("~/.nao-ref-glyphs.json"))
    print(f"  已建表：{len(ref_table)} 个汉字")

    print("=== 4. 解密 ===")
    mapping, hit, miss = build_mapping(font_path, ref_table)
    total = hit + miss
    print(f"  私有区字形 {total} 个，匹配成功 {hit}，失败 {miss}，命中率 {hit/max(1,total):.1%}")

    from bot.life.novel import parse_chapter
    body = parse_chapter(html) if False else None

    # 直接对整章做替换，看效果
    text = re.sub(r"<[^>]+>", "", html)
    pua_before = sum(1 for c in text if PUA(ord(c)))
    decoded = "".join(mapping.get(c, c) for c in text)
    pua_after = sum(1 for c in decoded if PUA(ord(c)))
    print(f"  全文私有区字符：{pua_before} → {pua_after}")

    idx = decoded.find("云千珩")
    if idx < 0:
        idx = 0
    print("  样本：", " ".join(decoded[idx:idx + 200].split()))
    print("\n  映射示例：", dict(list(mapping.items())[:10]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
