# ===================== 登录态注入（v16） =====================
# 番茄/起点有些页面要登录（起点章节页尤其）。
# cookie 放 data/cookies.json，启动浏览器时注入。
#
# 文件格式（两种都认）：
#   1) Cookie-Editor 之类导出的数组：
#      [{"name":"SESSDATA","value":"xxx","domain":".qidian.com","path":"/"}]
#   2) 按域名分组：
#      {"qidian": [...], "fanqie": [...]}
#
# 安全：文件在 .gitignore 里，日志只打 cookie 名的前 4 位。

import json
import os
from datetime import datetime

from ..log import log_api

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STORE = os.path.join(ROOT, "data", "cookies.json")

DOMAIN_HINTS = {
    "qidian": "qidian.com",
    "fanqie": "fanqienovel.com",
    "bilibili": "bilibili.com",
}


def _mask(value):
    v = str(value or "")
    return (v[:4] + "…") if len(v) > 4 else "…"


def load():
    """读 cookie 文件；坏文件返回 {}"""
    try:
        with open(STORE, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, (dict, list)) else {}
    except FileNotFoundError:
        return {}
    except Exception as e:
        log_api(f"[Cookie] 读取失败: {e}")
        return {}


def _normalize(items, default_domain=""):
    """把各种格式统一成 playwright 的 cookie dict 列表"""
    out = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        name = it.get("name")
        value = it.get("value")
        if not name or value is None:
            continue
        domain = it.get("domain") or default_domain
        if not domain:
            continue
        if not domain.startswith("."):
            # 让 cookie 对整个域生效
            domain = "." + domain.lstrip(".")
        out.append({
            "name": name,
            "value": str(value),
            "domain": domain,
            "path": it.get("path") or "/",
        })
    return out


def for_site(site):
    """取某个站点的 cookie 列表（site: qidian / fanqie / bilibili）"""
    data = load()
    hint = DOMAIN_HINTS.get(site, "")

    if isinstance(data, list):
        return _normalize(data, hint)

    if isinstance(data, dict):
        # 分组格式
        for key in (site, hint, site.capitalize()):
            if key in data:
                return _normalize(data[key], hint)
        # 单站扁平格式
        if "name" in data and "value" in data:
            return _normalize([data], hint)
    return []


def describe():
    """日志用：有哪几个站点的登录态"""
    data = load()
    sites = []
    if isinstance(data, dict):
        sites = [k for k, v in data.items() if isinstance(v, list) and v]
    elif isinstance(data, list):
        sites = ["(通用)"]
    return sites or []


def apply_to(context, site):
    """把 cookie 注入 Playwright context；返回注入条数"""
    items = for_site(site)
    if not items:
        return 0
    try:
        context.add_cookies(items)
        log_api(f"[Cookie] {site}: 注入 {len(items)} 条（{_mask(items[0]['value'])}）")
        return len(items)
    except Exception as e:
        log_api(f"[Cookie] {site} 注入失败: {e}")
        return 0


def save(site, items):
    """写入某个站点的 cookie（供以后自动化登录用）"""
    data = load()
    if not isinstance(data, dict):
        data = {}
    data[site] = items
    try:
        os.makedirs(os.path.dirname(STORE), exist_ok=True)
        with open(STORE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        try:
            os.chmod(STORE, 0o600)
        except Exception:
            pass
        log_api(f"[Cookie] {site} 已保存 {len(items)} 条")
        return True
    except Exception as e:
        log_api(f"[Cookie] 保存失败: {e}")
        return False
