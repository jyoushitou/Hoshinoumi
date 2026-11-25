# ===================== 存钱/流水 API（v35.2.20.0 / schema 34） =====================
# 只读写 finance_entries / finance_imports；金额统一整数分。
from __future__ import annotations

import csv
import hashlib
import io
import json
import uuid
from datetime import datetime

from ..infra import tenant
from .common import json_response


def _uid(request=None):
    return tenant.owner_id()


def _cents(raw):
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float):
        return int(round(raw * 100))
    text = str(raw or "").strip().replace(",", "")
    if not text:
        raise ValueError("amount is required")
    if text.startswith("¥"):
        text = text[1:].strip()
    try:
        return int(round(float(text) * 100))
    except ValueError:
        raise ValueError("bad amount: " + text)


def _signed(kind, cents):
    kind = (kind or "expense").strip().lower()
    if kind not in ("income", "expense", "saving"):
        raise ValueError("bad kind: " + kind)
    if kind == "income":
        return abs(cents), kind
    return -abs(cents), kind


def _row(item):
    account = str(item.get("account") or "").strip()
    if not account:
        raise ValueError("account is required")
    amount, kind = _signed(item.get("kind"), _cents(item.get("amount")))
    occurred = str(item.get("date") or item.get("occurred_at") or "").strip()
    if occurred:
        # 宽松：只保留日期/时间字符串；数据库适配器接受
        occurred = occurred[:19]
    note = str(item.get("note") or "").strip()[:200]
    category = str(item.get("category") or "").strip()[:64]
    return {
        "account": account[:64],
        "kind": kind,
        "amount_cents": amount,
        "category": category or None,
        "note": note or None,
        "occurred_at": occurred or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": str(item.get("source") or "manual")[:16],
    }


def _hash(uid, row):
    raw = "|".join([str(uid), row["account"], row["kind"], str(row["amount_cents"]),
                    row["occurred_at"], row["note"] or "", row["category"] or ""])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def parse_rows(body):
    rows = body.get("rows")
    if rows is None and body.get("csv"):
        text = str(body.get("csv") or "")
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
    if not isinstance(rows, list):
        raise ValueError("rows must be an array or csv")
    out = [_row(x) for x in rows if isinstance(x, dict)]
    if not out:
        raise ValueError("no rows")
    return out


def _existing_hashes(c, uid):
    c.execute("SELECT raw_hash FROM finance_entries WHERE user_id=%s", (uid,))
    return {r["raw_hash"] for r in (c.fetchall() or [])}


def _insert_ignore(c, uid, row, raw_hash):
    sql = ("INSERT OR IGNORE INTO finance_entries "
           "(user_id,account,kind,amount_cents,category,note,occurred_at,raw_hash,source) "
           "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)") if _sqlite() else (
           "INSERT IGNORE INTO finance_entries "
           "(user_id,account,kind,amount_cents,category,note,occurred_at,raw_hash,source) "
           "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)")
    c.execute(sql, (uid, row["account"], row["kind"], row["amount_cents"],
                    row["category"], row["note"], row["occurred_at"], raw_hash, row["source"]))


_DEFAULT_ACCOUNTS = (("银行卡", "bank"), ("微信", "wallet"), ("支付宝", "wallet"), ("现金", "cash"))


def _ensure_accounts(c, uid):
    for name, kind in _DEFAULT_ACCOUNTS:
        try:
            if _sqlite():
                c.execute("INSERT OR IGNORE INTO finance_accounts(user_id,account,kind) VALUES(%s,%s,%s)", (uid, name, kind))
            else:
                c.execute("INSERT IGNORE INTO finance_accounts(user_id,account,kind) VALUES(%s,%s,%s)", (uid, name, kind))
        except Exception:
            pass


def _sqlite():
    try:
        from ..infra.conn import _resolve_backend
        return _resolve_backend() == "sqlite"
    except Exception:
        return False



def _accounts_now(c, uid):
    c.execute("SELECT account,kind,SUM(amount_cents) AS total FROM finance_entries "
              "WHERE user_id=%s GROUP BY account,kind ORDER BY account", (uid,))
    accounts = {}
    for row in c.fetchall() or []:
        item = accounts.setdefault(row["account"], {"account": row["account"], "balance_cents": 0})
        item["balance_cents"] += int(row["total"] or 0)
    return sorted(accounts.values(), key=lambda x: x["account"])


async def handle_snapshots_get(request):
    uid = _uid(request)
    from ..infra.conn import get_cursor
    c = get_cursor()
    try:
        c.execute("SELECT id,taken_at,total_cents,accounts_json,note FROM finance_snapshots "
                  "WHERE user_id=%s ORDER BY id DESC LIMIT 20", (uid,))
        rows = []
        for row in c.fetchall() or []:
            item = dict(row)
            try:
                item["accounts"] = json.loads(item.pop("accounts_json") or "[]")
            except Exception:
                item["accounts"] = []
            rows.append(item)
        return json_response({"ok": True, "data": rows, "count": len(rows)})
    except Exception as e:
        return json_response({"ok": False, "error": "snapshots_failed", "message": str(e)}, 500)
    finally:
        try: c.close()
        except Exception: pass


async def handle_snapshot_create(request):
    uid = _uid(request)
    from ..infra.conn import get_cursor
    c = get_cursor()
    try:
        try:
            body = await request.json()
        except Exception:
            body = {}
        accounts = _accounts_now(c, uid)
        total = sum(int(x["balance_cents"] or 0) for x in accounts)
        note = str((body or {}).get("note") or "").strip()[:200]
        c.execute("INSERT INTO finance_snapshots(user_id,total_cents,accounts_json,note) "
                  "VALUES(%s,%s,%s,%s)", (uid, total, json.dumps(accounts, ensure_ascii=False), note))
        try: c.connection.commit()
        except Exception: pass
        c.execute("SELECT id,taken_at,total_cents,accounts_json,note FROM finance_snapshots "
                  "WHERE user_id=%s ORDER BY id DESC LIMIT 1", (uid,))
        row = c.fetchone()
        item = dict(row) if row else {}
        if item:
            try: item["accounts"] = json.loads(item.pop("accounts_json") or "[]")
            except Exception: item["accounts"] = []
        return json_response({"ok": True, "data": item})
    except Exception as e:
        try: c.connection.rollback()
        except Exception: pass
        return json_response({"ok": False, "error": "snapshot_failed", "message": str(e)}, 500)
    finally:
        try: c.close()
        except Exception: pass


async def handle_reconcile(request):
    uid = _uid(request)
    from ..infra.conn import get_cursor
    c = get_cursor()
    try:
        c.execute("SELECT id,taken_at,total_cents,accounts_json,note FROM finance_snapshots "
                  "WHERE user_id=%s ORDER BY id DESC LIMIT 1", (uid,))
        row = c.fetchone()
        if not row:
            return json_response({"ok": True, "snapshot": None, "accounts": [], "difference_cents": 0})
        snapshot = dict(row)
        try:
            old = json.loads(snapshot.pop("accounts_json") or "[]")
        except Exception:
            old = []
        old_map = {x.get("account"): int(x.get("balance_cents") or 0) for x in old if isinstance(x, dict)}
        now = _accounts_now(c, uid)
        now_map = {x["account"]: int(x["balance_cents"] or 0) for x in now}
        names = sorted(set(old_map) | set(now_map))
        rows = [{"account": name, "snapshot_cents": old_map.get(name, 0), "current_cents": now_map.get(name, 0),
                 "difference_cents": now_map.get(name, 0) - old_map.get(name, 0)} for name in names]
        return json_response({"ok": True, "snapshot": snapshot, "accounts": rows,
                              "difference_cents": sum(x["difference_cents"] for x in rows)})
    except Exception as e:
        return json_response({"ok": False, "error": "reconcile_failed", "message": str(e)}, 500)
    finally:
        try: c.close()
        except Exception: pass

async def handle_savings(request):
    uid = _uid(request)
    from ..infra.conn import get_cursor
    c = get_cursor()
    try:
        _ensure_accounts(c, uid)
        c.execute("SELECT account,kind,SUM(amount_cents) AS total FROM finance_entries "
                  "WHERE user_id=%s GROUP BY account,kind ORDER BY account", (uid,))
        rows = c.fetchall() or []
        accounts = {}
        for r in rows:
            item = accounts.setdefault(r["account"], {"account": r["account"], "balance_cents": 0})
            item["balance_cents"] += int(r["total"] or 0)
        c.execute("SELECT e.id,e.account,e.kind,e.amount_cents,e.category,e.note,e.occurred_at,e.source,"
                  "m.event_id,m.ai_visible FROM finance_entries e "
                  "LEFT JOIN finance_entry_meta m ON m.entry_id=e.id "
                  "WHERE e.user_id=%s ORDER BY e.id DESC LIMIT 50", (uid,))
        entries = [dict(r) for r in (c.fetchall() or [])]
        c.execute("SELECT account FROM finance_accounts WHERE user_id=%s ORDER BY id", (uid,))
        for row in c.fetchall() or []:
            accounts.setdefault(row["account"], {"account": row["account"], "balance_cents": 0})
        total = sum(x["balance_cents"] for x in accounts.values())
        return json_response({
            "ok": True,
            "total_cents": total,
            "accounts": list(accounts.values()),
            "entries": entries,
        })
    except Exception as e:
        return json_response({"ok": False, "error": "savings_failed", "message": str(e)}, 500)
    finally:
        try:
            c.close()
        except Exception:
            pass


async def handle_savings_import(request):
    uid = _uid(request)
    try:
        body = await request.json()
    except Exception:
        return json_response({"ok": False, "error": "invalid_json"}, 400)
    if not isinstance(body, dict):
        return json_response({"ok": False, "error": "invalid_body"}, 400)
    try:
        rows = parse_rows(body)
    except Exception as e:
        return json_response({"ok": False, "error": "invalid_rows", "message": str(e)}, 400)
    dry_run = bool(body.get("dry_run"))
    from ..infra.conn import get_cursor
    c = get_cursor()
    try:
        existing = _existing_hashes(c, uid)
        hashes = [_hash(uid, row) for row in rows]
        dup = sum(1 for h in hashes if h in existing)
        if dry_run:
            return json_response({
                "ok": True, "dry_run": True, "rows": len(rows),
                "duplicates": dup, "new": len(rows) - dup,
                "preview": rows[:50],
            })
        batch = uuid.uuid4().hex
        ok = 0
        for row, h in zip(rows, hashes):
            if h in existing:
                continue
            _insert_ignore(c, uid, row, h)
            existing.add(h)
            ok += 1
        sql = ("INSERT OR REPLACE INTO finance_imports "
               "(user_id,batch_id,source,rows_count,ok_count,status,meta) VALUES(%s,%s,%s,%s,%s,%s,%s)") if _sqlite() else (
               "REPLACE INTO finance_imports "
               "(user_id,batch_id,source,rows_count,ok_count,status,meta) VALUES(%s,%s,%s,%s,%s,%s,%s)")
        c.execute(sql, (uid, batch, str(body.get("source") or "json")[:16], len(rows), ok, "done",
                        json.dumps({"duplicates": dup}, ensure_ascii=False)))
        try:
            c.connection.commit()
        except Exception:
            pass
        return json_response({"ok": True, "batch_id": batch, "rows": len(rows), "inserted": ok, "duplicates": dup})
    except Exception as e:
        try:
            c.connection.rollback()
        except Exception:
            pass
        return json_response({"ok": False, "error": "import_failed", "message": str(e)}, 500)
    finally:
        try:
            c.close()
        except Exception:
            pass


async def handle_savings_events(request):
    uid = _uid(request)
    from ..infra.conn import get_cursor
    c = get_cursor()
    try:
        c.execute("SELECT id,summary,created_at FROM memories WHERE user_id=%s AND target_id=%s "
                  "AND kind='event' AND deleted_at IS NULL ORDER BY id DESC LIMIT 50", (uid, uid))
        rows = [dict(r) for r in (c.fetchall() or [])]
        return json_response({"ok": True, "events": rows})
    except Exception as e:
        return json_response({"ok": False, "error": "events_failed", "message": str(e)}, 500)
    finally:
        try:
            c.close()
        except Exception:
            pass


async def handle_savings_add(request):
    uid = _uid(request)
    try:
        body = await request.json()
    except Exception:
        return json_response({"ok": False, "error": "invalid_json"}, 400)
    if not isinstance(body, dict):
        return json_response({"ok": False, "error": "invalid_body"}, 400)
    try:
        row = _row(body)
    except Exception as e:
        return json_response({"ok": False, "error": "invalid_row", "message": str(e)}, 400)
    event_id = body.get("event_id")
    event_title = str(body.get("event_title") or "").strip()
    ai_visible = 1 if bool(body.get("ai_visible", True)) else 0
    from ..infra.conn import get_cursor
    c = get_cursor()
    try:
        if event_title:
            c.execute("INSERT INTO memories(user_id,target_id,kind,summary,tags,importance,weight,tier,"
                      "source,due_date,last_seen) VALUES(%s,%s,'event',%s,%s,3,0.6,'medium','manual',%s,%s)",
                      (uid, uid, event_title[:500], "finance" + ("" if ai_visible else ",no_ai"),
                       row["occurred_at"][:10], row["occurred_at"]))
            event_id = getattr(c, "lastrowid", None)
        elif event_id:
            c.execute("SELECT id FROM memories WHERE id=%s AND user_id=%s AND target_id=%s AND deleted_at IS NULL",
                      (event_id, uid, uid))
            if not c.fetchone():
                return json_response({"ok": False, "error": "event_not_found"}, 404)
        c.execute("INSERT INTO finance_entries(user_id,account,kind,amount_cents,category,note,occurred_at,raw_hash,source) "
                  "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                  (uid, row["account"], row["kind"], row["amount_cents"], row["category"], row["note"],
                   row["occurred_at"], _hash(uid, row), row["source"]))
        entry_id = getattr(c, "lastrowid", None)
        c.execute("INSERT INTO finance_entry_meta(entry_id,event_id,ai_visible) VALUES(%s,%s,%s)",
                  (entry_id, event_id or None, ai_visible))
        try:
            c.connection.commit()
        except Exception:
            pass
        return json_response({"ok": True, "id": entry_id, "event_id": event_id, "ai_visible": bool(ai_visible)})
    except Exception as e:
        try:
            c.connection.rollback()
        except Exception:
            pass
        return json_response({"ok": False, "error": "add_failed", "message": str(e)}, 500)
    finally:
        try:
            c.close()
        except Exception:
            pass

async def handle_overview(request):
    uid = _uid(request)
    from ..infra.conn import get_cursor
    c = get_cursor()
    try:
        accounts = _accounts_now(c, uid)
        total = sum(int(x["balance_cents"] or 0) for x in accounts)
        return json_response({"total_cents": total, "frozen_cents": 0, "available_cents": total})
    finally:
        try: c.close()
        except Exception: pass


async def handle_monthly(request):
    uid = _uid(request)
    from ..infra.conn import get_cursor
    c = get_cursor()
    try:
        c.execute("SELECT occurred_at,kind,amount_cents FROM finance_entries WHERE user_id=%s ORDER BY occurred_at", (uid,))
        months = {}
        for row in c.fetchall() or []:
            month = str(row.get("occurred_at") or "")[:7]
            if not month:
                continue
            item = months.setdefault(month, {"month": month, "income_cents": 0, "expense_cents": 0})
            amount = int(row.get("amount_cents") or 0)
            if amount >= 0:
                item["income_cents"] += amount
            else:
                item["expense_cents"] += -amount
        return json_response({"ok": True, "data": sorted(months.values(), key=lambda x: x["month"])[-6:]})
    finally:
        try: c.close()
        except Exception: pass


async def handle_goals(request):
    return json_response({"ok": True, "data": []})


async def handle_frozen(request):
    return json_response({"ok": True, "data": []})


async def handle_fixed(request):
    return json_response({"ok": True, "data": []})


async def handle_funds(request):
    return json_response({"ok": True, "data": []})


async def handle_finance_audit(request):
    return json_response({"ok": True, "data": [], "count": 0})
