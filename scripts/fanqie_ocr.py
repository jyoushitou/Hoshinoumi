#!/usr/bin/env python3
# ===================== 番茄正文解密（OCR 版） =====================
# 字体比对失败（字形被扰动，命中率 0.3%），改用最稳的办法：
#   浏览器渲染页面 → 截图（此时字是**正确**的）→ tesseract OCR
#
# 依赖：
#     sudo apt install -y tesseract-ocr tesseract-ocr-chi-sim
#     pip install --user --break-system-packages playwright
#     python3 -m playwright install chromium
#
# 用法：
#     python3 scripts/fanqie_ocr.py
#     python3 scripts/fanqie_ocr.py <章节URL>

import os
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")

CHAPTER_URL = "https://fanqienovel.com/reader/7688347832079614488"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def pua_count(text):
    return sum(1 for ch in (text or "") if 0xE000 <= ord(ch) <= 0xF8FF)


def screenshot_chapter(url, out_png):
    """用浏览器打开章节并截正文区域"""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(
            user_agent=UA, locale="zh-CN", timezone_id="Asia/Shanghai",
            viewport={"width": 1100, "height": 1600}, device_scale_factor=2,
        )
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        # 等字体加载完（字体没加载时字是乱的）
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass
        page.wait_for_timeout(2500)

        # 优先截正文容器，找不到就整页
        target = None
        for sel in (".muye-reader-content", "#content", "article", "body"):
            try:
                el = page.query_selector(sel)
                if el:
                    target = el
                    break
            except Exception:
                continue
        if target is None:
            page.screenshot(path=out_png, full_page=True)
        else:
            target.screenshot(path=out_png)
        browser.close()


def ocr(image_path, lang="chi_sim"):
    """调 tesseract CLI；返回文本"""
    try:
        r = subprocess.run(
            ["tesseract", image_path, "stdout", "-l", lang, "--psm", "6"],
            capture_output=True, timeout=120,
        )
    except FileNotFoundError:
        return None
    if r.returncode != 0:
        print(f"  tesseract 失败：{r.stderr.decode('utf-8', 'ignore')[:200]}")
        return None
    return r.stdout.decode("utf-8", "ignore")


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else CHAPTER_URL
    print("=== 1. 截图 ===")
    tmpdir = tempfile.mkdtemp(prefix="fq-ocr-")
    png = os.path.join(tmpdir, "chapter.png")
    try:
        screenshot_chapter(url, png)
    except Exception as e:
        print(f"  截图失败：{e}")
        return 1
    print(f"  已保存：{png}（{os.path.getsize(png)//1024} KB）")

    print("=== 2. OCR ===")
    text = ocr(png)
    if text is None:
        print("  没装 tesseract：sudo apt install -y tesseract-ocr tesseract-ocr-chi-sim")
        return 1

    clean = " ".join(text.split())
    print(f"  OCR 长度：{len(clean)}")
    print(f"  私有区字符：{pua_count(clean)}")
    print(f"  样本：{clean[:300]}")

    # 和 DOM 文本做个对比
    print("\n=== 3. 对比 DOM 文本 ===")
    try:
        import requests
        html = requests.get(url, timeout=20, headers={"User-Agent": UA}).text
        import re
        body = re.sub(r"<[^>]+>", "", html)
        print(f"  DOM 私有区字符：{pua_count(body)}")
    except Exception as e:
        print(f"  取 DOM 失败：{e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
