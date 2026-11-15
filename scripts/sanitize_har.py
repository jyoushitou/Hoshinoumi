#!/usr/bin/env python3
"""v24.5 HAR 脱敏 + endpoint 摘要。

只处理用户自己导出、自己有权访问的 HAR：
- 删除 Cookie / Authorization / token / 密码
- 删除响应正文（避免保存受版权保护的章节）
- 输出 method/path/status/mime 摘要

    python3 scripts/sanitize_har.py own.har own.sanitized.har
"""

import argparse
import json
import re
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

SECRET_HEADERS = {
    "cookie", "set-cookie", "authorization", "proxy-authorization",
    "x-token", "x-auth-token", "x-csrf-token", "x-api-key",
}
SECRET_QUERY = re.compile(r"(token|key|sign|signature|auth|cookie|session|password)", re.I)
SECRET_TEXT = re.compile(r'("(?:password|token|access_token|refresh_token|cookie)"\s*:\s*)"[^"]*"', re.I)


def _redact_headers(headers):
    out = []
    for h in headers or []:
        name = str(h.get("name", ""))
        if name.lower() in SECRET_HEADERS:
            out.append({"name": name, "value": "[REDACTED]"})
        else:
            out.append({"name": name, "value": str(h.get("value", ""))[:300]})
    return out


def _redact_url(url):
    parts = urlsplit(url)
    query = []
    for k, v in parse_qsl(parts.query, keep_blank_values=True):
        query.append((k, "[REDACTED]" if SECRET_QUERY.search(k) else v))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))


def sanitize(har):
    entries = []
    endpoints = []
    for e in (har.get("log", {}).get("entries") or []):
        req = e.get("request") or {}
        resp = e.get("response") or {}
        url = _redact_url(req.get("url", ""))
        method = req.get("method", "GET")
        status = int(resp.get("status") or 0)
        mime = ((resp.get("content") or {}).get("mimeType") or "")[:120]
        endpoints.append({"method": method, "url": url, "status": status, "mime": mime})
        post = req.get("postData") or {}
        post_text = post.get("text") or ""
        post_text = SECRET_TEXT.sub(r'\1"[REDACTED]"', post_text)[:2000]
        entries.append({
            "request": {
                "method": method,
                "url": url,
                "headers": _redact_headers(req.get("headers")),
                "postData": {"mimeType": post.get("mimeType", ""), "text": post_text} if post else None,
            },
            "response": {
                "status": status,
                "headers": _redact_headers(resp.get("headers")),
                "content": {"mimeType": mime, "size": len(((resp.get("content") or {}).get("text") or ""))},
            },
            "time": e.get("time", 0),
        })
    return {"log": {"version": "1.2", "creator": {"name": "sanitize_har"}, "entries": entries}}, endpoints


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output")
    args = ap.parse_args()
    src = Path(args.input)
    har = json.loads(src.read_text(encoding="utf-8"))
    clean, endpoints = sanitize(har)
    Path(args.output).write_text(
        json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = Path(args.output).with_suffix(".endpoints.json")
    summary.write_text(json.dumps(endpoints, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] {args.output}（{len(endpoints)} 条）")
    print(f"[OK] {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
