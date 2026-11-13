# ===================== 通用工具模块 =====================
# 网络下载、Base64编码、图片消息构建
# 注：AI 回复解析已迁至 bot/ai/parse.py（v5-R2）

import os, base64
from urllib.parse import urlparse
from .core.http import create_http_session
from .log import log_api

# 默认请求头，模拟浏览器访问，避免403
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.google.com/"
}

def referer_for(url):
    """按图片自身域名生成 Referer（v8-FIX：防盗链站点认自己的域名）"""
    try:
        p = urlparse(url)
        if p.scheme and p.netloc:
            return f"{p.scheme}://{p.netloc}/"
    except Exception:
        pass
    return "https://www.google.com/"


def download_url(url, referer=None):
    """下载URL内容，返回二进制数据，失败返回None"""
    if not url:
        log_api(f"[下载] URL为空")
        return None
    s=create_http_session()  # 创建带连接池的会话
    try:
        log_api(f"[下载] 开始下载: {url[:80]}")
        headers = dict(DEFAULT_HEADERS)
        headers["Referer"] = referer or referer_for(url)  # 防盗链：用图片自己的域名
        r=s.get(url,timeout=(5,10),verify=False,headers=headers)  # 5秒连接超时，10秒读取超时
        r.raise_for_status()  # 检查HTTP状态码
        log_api(f"[下载] 成功: {len(r.content)} bytes")
        return r.content
    except Exception as e:
        log_api(f"[下载] 失败: {e}")
        return None
    finally:
        s.close()  # 关闭会话

def encode_image_base64(d):
    """将二进制图片数据编码为NapCat的base64格式"""
    try:
        return "base64://" + base64.b64encode(d).decode()
    except:
        return ""

# 项目根目录（bot 的上一级），用于把相对路径固定下来
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resolve_image_path(filepath):
    """把图片路径解析成真实存在的绝对路径；找不到返回 None（v5-F4）

    库里历史数据存的是 `images/xxx.jpg` 这种相对路径，
    以前直接用 os.path.exists 判断，换个工作目录启动就全查不到。
    """
    if not filepath:
        return None
    if os.path.isabs(filepath):
        return os.path.abspath(filepath) if os.path.exists(filepath) else None
    # 相对路径：先按项目根找，再按当前目录找
    for base in (_PROJECT_ROOT, os.getcwd()):
        candidate = os.path.abspath(os.path.join(base, filepath))
        if os.path.exists(candidate):
            return candidate
    return None


def make_image_msg(filepath):
    """统一将本地图片路径转为 NapCat 图片消息体
    返回 [{"type":"image","data":{"file":"绝对路径"}}] 或 None"""
    abs_path = resolve_image_path(filepath)
    if not abs_path:
        return None
    return [{"type":"image","data":{"file":abs_path}}]
