#!/usr/bin/env python3
"""v22.1 网关压测：并发 / 超限 / 后端断开。

    python3 scripts/gateway_load_test.py --base http://127.0.0.1:27005 \
        --token "$TOKEN" --n 100 --concurrency 20

只统计状态码，不打印 token/响应体。
"""

import argparse
import collections
import concurrent.futures
import json
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, ".")


def one(base, token, path):
    req = urllib.request.Request(base.rstrip("/") + path)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:27005")
    ap.add_argument("--token", default="")
    ap.add_argument("--path", default="/api/state")
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--concurrency", type=int, default=20)
    args = ap.parse_args()

    start = time.time()
    counts = collections.Counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = [ex.submit(one, args.base, args.token, args.path) for _ in range(args.n)]
        for f in concurrent.futures.as_completed(futs):
            counts[f.result()] += 1
    elapsed = max(0.001, time.time() - start)
    print(json.dumps({
        "n": args.n,
        "seconds": round(elapsed, 3),
        "rps": round(args.n / elapsed, 1),
        "codes": dict(sorted(counts.items())),
    }, ensure_ascii=False))
    return 0 if counts.get(0, 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
