#!/usr/bin/env python3
# ===================== 起点/番茄 抓取实测（v2） =====================
# 第一版直接打章节页，起点只回了「安全检测中」5 个字。
# 这一版：
#   1. 持久化浏览器上下文（cookie 留得住，挑战过了就不用再过）
#   2. 真实 UA + 关掉自动化特征
#   3. 循环重试：一直刷新直到页面不再是挑战页
#
# 用法（服务器上）：
#     python3 scripts/test_scrape.py 起点
#     python3 scripts/test_scrape.py 番茄
#     python3 scripts/test_scrape.py 起点 https://www.qidian.com/chapter/xxx/yyy/

import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

PROFILE_DIR = os.path.expanduser("~/.nao-browser-profile")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

QIDIAN_HOME = "https://www.qidian.com/"
QIDIAN_CHAPTER = "https://www.qidian.com/chapter/1019470044/241813268/"
FANQIE_CHAPTER = "https://fanqienovel.com/reader/7688347832079614488"

BAD_MARKS = ("安全检测", "验证", "滑动", "captcha", "Just a moment")


def pua_count(text):
    return sum(1 for ch in (text or "") if 0xE000 <= ord(ch) <= 0xF8FF)


def is_challenge(text):
    t = (text or "").strip()
    if len(t) < 200:
        return True
    return any(mark in t[:200] for mark in BAD_MARKS)


def open_page(ctx, url, tries=6, wait=2500):
    """打开页面并等挑战过去；返回 (text, ok)"""
    page = ctx.new_page()
    for i in range(1, tries + 1):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            print(f"    第 {i} 次加载出错：{e}")
            time.sleep(wait / 1000)
            continue

        # 给挑战脚本时间跑完并自动跳转
        try:
            page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        page.wait_for_timeout(wait)

        text = page.inner_text("body")
        print(f"    第 {i} 次：长度 {len(text)}，开头「{' '.join(text.split())[:24]}」")
        if not is_challenge(text):
            return text, True
        time.sleep(1.5)
    text = page.inner_text("body")
    page.close()
    return text, False


def main():
    which = (sys.argv[1] if len(sys.argv) > 1 else "起点").strip()
    custom = sys.argv[2] if len(sys.argv) > 2 else ""

    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print("没装 playwright：python3 -m pip install --user --break-system-packages playwright")
        return 1

    with sync_playwright() as p:
        print(f"用持久化上下文：{PROFILE_DIR}")
        ctx = p.chromium.launch_persistent_context(
            PROFILE_DIR,
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
            user_agent=UA,
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            viewport={"width": 1280, "height": 800},
        )
        try:
            if which in ("起点", "qidian"):
                print("\n=== 先过首页挑战 ===")
                home_text, home_ok = open_page(ctx, QIDIAN_HOME, tries=5)
                print(f"  首页过挑战：{'是' if home_ok else '否'}")
                cookies = {c['name']: c['value'] for c in ctx.cookies()}
                print(f"  cookie：{list(cookies)[:6]}")

                url = custom or QIDIAN_CHAPTER
                print(f"\n=== 章节页 {url} ===")
                text, ok = open_page(ctx, url, tries=6)
                print(f"\n  结果：长度 {len(text)} | 乱码 {pua_count(text)} | "
                      f"占比 {pua_count(text)/max(1,len(text)):.1%} | 过挑战 {'是' if ok else '否'}")
                print(f"  样本：{' '.join(text.split())[:300]}")

            else:
                url = custom or FANQIE_CHAPTER
                print(f"\n=== 番茄 {url} ===")
                text, ok = open_page(ctx, url, tries=3)
                print(f"\n  结果：长度 {len(text)} | 乱码 {pua_count(text)} | "
                      f"占比 {pua_count(text)/max(1,len(text)):.1%}")
                print(f"  样本：{' '.join(text.split())[:300]}")
        finally:
            ctx.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
