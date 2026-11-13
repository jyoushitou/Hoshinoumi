# ===================== 截图 OCR（v16-U26） =====================
# 番茄把正文字符替换成私有区码点，靠自定义字体渲染。
# 字体比对失败（字形被扰动），但**渲染出来是对的**——所以截图 + OCR。
#
# 依赖：
#     tesseract-ocr + tesseract-ocr-chi-sim
#     playwright + chromium
#
# 全部走线程，不阻塞事件循环。

import os
import re
import shutil
import subprocess
import sys
import tempfile

from ..log import log_api

OCRLANG = os.getenv("NAO_OCR_LANG", "chi_sim")
OCR_TIMEOUT = 120
SHOT_TIMEOUT = 30
PUA_RANGE = (0xE000, 0xF8FF)

_ok_cache = {}
_UNCERTAIN = {"n": 0}


def paddle_ok():
    """PaddleOCR 装了没（可选；没装就只用 tesseract）"""
    if "p" not in _ok_cache:
        try:
            import paddleocr  # noqa: F401
            _ok_cache["p"] = True
        except Exception:
            _ok_cache["p"] = False
    return _ok_cache["p"]


def ocr_uncertain_count():
    return _UNCERTAIN["n"]


def merge_ocr_results(tess, paddle):
    """v18.18：两引擎一致就用 tesseract；不一致记日志并标记不确定"""
    tess = (tess or "").strip()
    paddle = (paddle or "").strip()
    if not tess:
        return paddle
    if not paddle:
        return tess
    import difflib

    ratio = difflib.SequenceMatcher(a=tess, b=paddle, autojunk=False).ratio()
    if ratio >= 0.90:
        return tess
    _UNCERTAIN["n"] += 1
    log_api(f"[OCR] 两引擎不一致（相似度 {ratio:.2f}），标记不确定，以 tesseract 为主")
    return tess


def tesseract_ok():
    """tesseract 装了没（带缓存）"""
    if "t" not in _ok_cache:
        _ok_cache["t"] = shutil.which("tesseract") is not None
    return _ok_cache["t"]


def pua_count(text):
    """私有区字符个数"""
    return sum(1 for ch in (text or "") if PUA_RANGE[0] <= ord(ch) <= PUA_RANGE[1])


def pua_ratio(text):
    """私有区字符占比（越高说明字体加密没解开）"""
    if not text:
        return 0.0
    bad = sum(1 for ch in text if PUA_RANGE[0] <= ord(ch) <= PUA_RANGE[1])
    return bad / len(text)


def clean(text):
    """收拾 OCR 输出：去掉 CJK 之间的空格、压掉空行"""
    if not text:
        return ""
    # 中文之间的空格通常是 OCR 硬塞的
    text = re.sub(r"(?<=[\u4e00-\u9fff])[ \t\u3000]+(?=[\u4e00-\u9fff])", "", text)
    text = re.sub(r"[ \t\u3000]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _ocr_file(path, lang=OCRLANG):
    """调 tesseract CLI；失败返回空串"""
    try:
        r = subprocess.run(
            ["tesseract", path, "stdout", "-l", lang, "--psm", "6"],
            capture_output=True, timeout=OCR_TIMEOUT,
        )
    except FileNotFoundError:
        log_api("[OCR] 没装 tesseract")
        return ""
    except Exception as e:
        log_api(f"[OCR] 调用失败: {e}")
        return ""
    if r.returncode != 0:
        log_api(f"[OCR] tesseract 返回 {r.returncode}: {r.stderr[:120]!r}")
        return ""
    return clean(r.stdout.decode("utf-8", "ignore"))


def _ocr_paddle(path, lang=OCRLANG):
    """可选：PaddleOCR（没装/失败返回空串）"""
    if not paddle_ok():
        return ""
    try:
        from paddleocr import PaddleOCR
        engine = _ok_cache.get("p_engine")
        if engine is None:
            engine = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
            _ok_cache["p_engine"] = engine
        result = engine.ocr(path, cls=True) or []
        lines = []
        for block in result:
            for item in block or []:
                try:
                    lines.append(item[1][0])
                except Exception:
                    continue
        return clean("\n".join(lines))
    except Exception as e:
        log_api(f"[OCR] PaddleOCR 失败: {e}")
        return ""


def _ocr_file_dual(path, lang=OCRLANG):
    """tesseract + 可选 PaddleOCR；两引擎不一致时记不确定"""
    tess = _ocr_file(path, lang)
    paddle = _ocr_paddle(path, lang)
    return merge_ocr_results(tess, paddle)


def _shot_and_ocr(url):
    """同步执行：开浏览器截图 → OCR。放在线程里跑。"""
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        log_api("[OCR] 没装 playwright")
        return ""

    UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
    tmpdir = tempfile.mkdtemp(prefix="nao-ocr-")
    png = os.path.join(tmpdir, "page.png")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            try:
                ctx = browser.new_context(
                    user_agent=UA, locale="zh-CN", timezone_id="Asia/Shanghai",
                    viewport={"width": 1100, "height": 1600}, device_scale_factor=2,
                )
                try:  # v16：注入登录态（有就注入，没有不影响）
                    from . import cookies as life_cookies
                    life_cookies.apply_to(ctx, "fanqie")
                except Exception:
                    pass
                page = ctx.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=SHOT_TIMEOUT * 1000)
                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass
                page.wait_for_timeout(2500)  # 等字体加载
                el = page.query_selector(".muye-reader-content") or page.query_selector("body")
                el.screenshot(path=png)
            finally:
                browser.close()
    except Exception as e:
        log_api(f"[OCR] 截图失败: {e}")
        return ""

    return _ocr_file_dual(png)


async def ocr_url(url):
    """异步入入口：截图 + OCR（v17.0.3 统一线程池）

    截图 + tesseract 加起来可能 60 秒，超时给 SHOT_TIMEOUT + OCR_TIMEOUT。
    """
    from ..infra.blocking import run_blocking

    if not tesseract_ok():
        return ""
    return await run_blocking(_shot_and_ocr, url,
                              timeout=SHOT_TIMEOUT + OCR_TIMEOUT + 15, name="ocr")


# ===================== HTML + OCR 合并（v16） =====================
# 两者互补：
#   HTML：非加密的字 100% 准确，标点/段落结构完整，但加密字是私有区码点
#   OCR ：所有字都能认出来，但有 ~5% 错字、空格噪音
#
# 做法：HTML 当骨架，用 difflib 对齐，只在「差异段且含私有区」的位置用 OCR 补字。

import difflib


def _is_pua(ch):
    return PUA_RANGE[0] <= ord(ch) <= PUA_RANGE[1]


def merge_html_ocr(html_text, ocr_text):
    """合并：已知字用 HTML，加密字用 OCR"""
    if not html_text:
        return ocr_text or ""
    if not ocr_text:
        return html_text or ""

    sm = difflib.SequenceMatcher(a=list(html_text), b=list(ocr_text), autojunk=False)

    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        seg_html = html_text[i1:i2]
        seg_ocr = ocr_text[j1:j2]

        if tag == "equal":
            out.append(seg_html)
        elif tag == "insert":
            # OCR 多认出来的字（通常是把一个字认成两个）——不补，避免重复
            continue
        else:  # replace / delete
            if any(_is_pua(c) for c in seg_html):
                out.append(seg_ocr or seg_html)
            else:
                out.append(seg_html)

    merged = "".join(out)
    merged = "".join(c for c in merged if not _is_pua(c))
    return clean(merged)


def best_text(html_text, ocr_text):
    """挑最好的结果：能合并就合并，合并后仍差就用 OCR"""
    merged = merge_html_ocr(html_text, ocr_text)
    ok = (merged and pua_ratio(merged) < 0.01
          and len(merged) >= len(ocr_text or "") * 0.8)
    return merged if ok else (ocr_text or merged or html_text or "")
