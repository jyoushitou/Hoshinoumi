# ===================== 存钱/流水 API（v35.2.20.0 / schema 34） =====================
# 只读写 finance_entries / finance_imports；金额统一整数分。
from __future__ import annotations

import csv
import hashlib
import io
import json
import uuid
from datetime import datetime, date

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


def _meta_get(c, key, default=""):
    c.execute("SELECT v FROM bot_meta WHERE k=%s", (key,))
    row = c.fetchone()
    return str(row.get("v") or default) if row else default


def _meta_set(c, key, value):
    if _sqlite():
        c.execute("INSERT OR REPLACE INTO bot_meta(k,v,updated_at) VALUES(%s,%s,CURRENT_TIMESTAMP)", (key, value))
    else:
        c.execute("REPLACE INTO bot_meta(k,v,updated_at) VALUES(%s,%s,CURRENT_TIMESTAMP)", (key, value))


async def handle_savings_init_get(request):
    uid = _uid(request)
    from ..infra.conn import get_cursor
    c = get_cursor()
    try:
        _ensure_accounts(c, uid)
        c.execute("SELECT account FROM finance_accounts WHERE user_id=%s ORDER BY id", (uid,))
        accounts = [r["account"] for r in (c.fetchall() or [])]
        return json_response({
            "ok": True, "initialized": _meta_get(c, "savings_initialized") == "1",
            "accounts": accounts,
        })
    finally:
        try: c.close()
        except Exception: pass


async def handle_savings_init_post(request):
    uid = _uid(request)
    try:
        body = await request.json()
    except Exception:
        return json_response({"ok": False, "error": "invalid_json"}, 400)
    balances = (body or {}).get("balances")
    if not isinstance(balances, dict):
        return json_response({"ok": False, "error": "bad_balances"}, 400)
    from ..infra.conn import get_cursor
    from ..config import CST
    c = get_cursor()
    try:
        _ensure_accounts(c, uid)
        if _meta_get(c, "savings_initialized") == "1":
            return json_response({"ok": False, "error": "already_initialized"}, 409)
        allowed = {"银行卡", "微信", "支付宝", "现金"}
        now = datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S")
        created = 0
        for account, raw in balances.items():
            name = str(account)
            if name not in allowed:
                continue
            try:
                yuan = float(raw or 0)
            except (TypeError, ValueError):
                continue
            if abs(yuan) < 0.005:
                continue
            cents = int(round(yuan * 100))
            raw_hash = hashlib.sha256(f"init:{uid}:{name}:{cents}:{now}".encode()).hexdigest()
            c.execute(
                "INSERT INTO finance_entries(user_id,account,kind,amount_cents,category,note,occurred_at,raw_hash,source) "
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,'initial')",
                (uid, name, "income" if cents >= 0 else "expense", cents, "初始余额", "存钱初始化", now, raw_hash))
            created += 1
        _meta_set(c, "savings_initialized", "1")
        try: c.connection.commit()
        except Exception: pass
        return json_response({"ok": True, "initialized": True, "created": created})
    except Exception as e:
        try: c.connection.rollback()
        except Exception: pass
        return json_response({"ok": False, "error": "init_failed", "message": str(e)}, 500)
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
        cash = sum(int(x["balance_cents"] or 0) for x in accounts)
        c.execute("SELECT COALESCE(SUM(principal_cents),0) AS total FROM finance_fixed_deposits "
                  "WHERE user_id=%s AND status IN ('active','matured')", (uid,))
        row = c.fetchone()
        fixed = int((row or {}).get("total", 0) or 0) if isinstance(row, dict) else int((row or [0])[0] or 0)
        c.execute("SELECT COALESCE(SUM(value_cents),0) AS total FROM finance_fund_holdings WHERE user_id=%s", (uid,))
        row = c.fetchone()
        funds = int((row or {}).get("total", 0) or 0) if isinstance(row, dict) else int((row or [0])[0] or 0)
        total = cash + fixed + funds
        return json_response({"total_cents": total, "frozen_cents": 0, "available_cents": cash,
                              "fixed_cents": fixed, "funds_cents": funds})
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


def _add_months(day, months):
    month = day.month - 1 + int(months)
    year = day.year + month // 12
    month = month % 12 + 1
    import calendar
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(day.day, last))


def _fixed_rows(c, uid):
    today = date.today()
    c.execute("UPDATE finance_fixed_deposits SET status='matured' "
              "WHERE user_id=%s AND status='active' AND matures_at<=%s", (uid, today.isoformat()))
    c.execute("SELECT id,name,principal_cents,rate_bps,start_at,matures_at,status,account,note "
              "FROM finance_fixed_deposits WHERE user_id=%s ORDER BY matures_at,id", (uid,))
    rows = []
    for r in c.fetchall() or []:
        item = dict(r)
        start = item.get("start_at")
        mature = item.get("matures_at")
        start_d = datetime.strptime(str(start)[:10], "%Y-%m-%d").date() if start else today
        mature_d = datetime.strptime(str(mature)[:10], "%Y-%m-%d").date() if mature else today
        days_left = (mature_d - today).days
        days_total = max(1, (mature_d - start_d).days)
        interest = int(round(int(item.get("principal_cents") or 0) * int(item.get("rate_bps") or 0) / 10000 * days_total / 365))
        item.update({"days_left": days_left, "interest_cents": interest,
                     "mature": days_left <= 0, "start_at": str(start)[:10], "matures_at": str(mature)[:10]})
        rows.append(item)
    return rows


async def handle_fixed(request):
    uid = _uid(request)
    from ..infra.conn import get_cursor
    c = get_cursor()
    try:
        rows = _fixed_rows(c, uid)
        try: c.connection.commit()
        except Exception: pass
        reminders = [x for x in rows if x["status"] in ("active", "matured") and x["days_left"] <= 7]
        total = sum(int(x["principal_cents"] or 0) for x in rows if x["status"] in ("active", "matured"))
        return json_response({"ok": True, "data": rows, "reminders": reminders, "total_cents": total})
    finally:
        try: c.close()
        except Exception: pass


async def handle_fixed_add(request):
    uid = _uid(request)
    try:
        body = await request.json()
    except Exception:
        return json_response({"ok": False, "error": "invalid_json"}, 400)
    name = str(body.get("name") or "定期存款").strip()[:80]
    try:
        amount = float(body.get("amount") or 0)
        rate = float(body.get("rate") or 0)
        months = int(body.get("months") or 0)
    except (TypeError, ValueError):
        return json_response({"ok": False, "error": "bad_values"}, 400)
    if amount <= 0 or months <= 0 or months > 120 or rate < 0 or rate > 30:
        return json_response({"ok": False, "error": "bad_values"}, 400)
    start = date.today()
    mature = _add_months(start, months)
    from ..infra.conn import get_cursor
    c = get_cursor()
    try:
        c.execute("INSERT INTO finance_fixed_deposits(user_id,name,principal_cents,rate_bps,start_at,matures_at,status,account,note) "
                  "VALUES(%s,%s,%s,%s,%s,%s,'active',%s,%s)",
                  (uid, name, int(round(amount * 100)), int(round(rate * 100)), start.isoformat(),
                   mature.isoformat(), str(body.get("account") or "")[:64] or None, str(body.get("note") or "")[:120] or None))
        try: c.connection.commit()
        except Exception: pass
        c.execute("SELECT id FROM finance_fixed_deposits WHERE user_id=%s ORDER BY id DESC LIMIT 1", (uid,))
        row = c.fetchone()
        return json_response({"ok": True, "id": row.get("id") if row else None,
                              "matures_at": mature.isoformat(), "months": months})
    finally:
        try: c.close()
        except Exception: pass


async def handle_fixed_settle(request):
    uid = _uid(request)
    try:
        item_id = int(request.match_info["id"])
    except (KeyError, ValueError):
        return json_response({"ok": False, "error": "bad_id"}, 400)
    from ..infra.conn import get_cursor
    c = get_cursor()
    try:
        c.execute("SELECT id,name,principal_cents,rate_bps,start_at,matures_at,status,account "
                  "FROM finance_fixed_deposits WHERE id=%s AND user_id=%s", (item_id, uid))
        row = c.fetchone()
        if not row:
            return json_response({"ok": False, "error": "not_found"}, 404)
        if row.get("status") == "settled":
            return json_response({"ok": True, "id": item_id, "status": "settled", "credited_cents": 0})
        principal = int(row.get("principal_cents") or 0)
        start_d = datetime.strptime(str(row.get("start_at"))[:10], "%Y-%m-%d").date()
        mature_d = datetime.strptime(str(row.get("matures_at"))[:10], "%Y-%m-%d").date()
        days_total = max(1, (mature_d - start_d).days)
        interest = int(round(principal * int(row.get("rate_bps") or 0) / 10000 * days_total / 365))
        credited = principal + interest
        account = row.get("account") or "银行卡"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        raw_hash = hashlib.sha256(f"fixed-settle:{uid}:{item_id}".encode()).hexdigest()
        c.execute("INSERT INTO finance_entries(user_id,account,kind,amount_cents,category,note,occurred_at,raw_hash,source) "
                  "VALUES(%s,%s,'income',%s,'定期转回',%s,%s,%s,'fixed')",
                  (uid, account, credited, str(row.get("name") or "定期存款")[:60], now, raw_hash))
        c.execute("UPDATE finance_fixed_deposits SET status='settled' WHERE id=%s AND user_id=%s", (item_id, uid))
        try: c.connection.commit()
        except Exception: pass
        return json_response({"ok": True, "id": item_id, "status": "settled",
                              "principal_cents": principal, "interest_cents": interest,
                              "credited_cents": credited, "account": account})
    finally:
        try: c.close()
        except Exception: pass


def _fund_rows(c, uid):
    c.execute("SELECT id,code,name,kind,shares,nav,cost_cents,value_cents,account FROM finance_fund_holdings "
              "WHERE user_id=%s ORDER BY id", (uid,))
    rows = []
    for r in c.fetchall() or []:
        item = dict(r)
        shares = float(item.get("shares") or 0)
        nav = float(item.get("nav") or 1)
        value = int(round(shares * nav * 100))
        item.update({"shares": round(shares, 4), "nav": round(nav, 4), "value_cents": value,
                     "profit_cents": value - int(item.get("cost_cents") or 0)})
        rows.append(item)
    return rows


async def handle_funds(request):
    uid = _uid(request)
    from ..infra.conn import get_cursor
    c = get_cursor()
    try:
        rows = _fund_rows(c, uid)
        return json_response({"ok": True, "data": rows, "total_cents": sum(x["value_cents"] for x in rows)})
    finally:
        try: c.close()
        except Exception: pass


async def handle_fund_buy(request):
    uid = _uid(request)
    try:
        body = await request.json()
    except Exception:
        return json_response({"ok": False, "error": "invalid_json"}, 400)
    code = str(body.get("code") or "").strip()[:32]
    name = str(body.get("name") or code).strip()[:80]
    kind = "money" if str(body.get("kind") or "") == "money" else "fund"
    try:
        amount = float(body.get("amount") or 0)
        nav = 1.0 if kind == "money" else float(body.get("nav") or 0)
    except (TypeError, ValueError):
        return json_response({"ok": False, "error": "bad_values"}, 400)
    if not code or amount <= 0 or nav <= 0:
        return json_response({"ok": False, "error": "bad_values"}, 400)
    shares = amount / nav
    cents = int(round(amount * 100))
    account = str(body.get("account") or "银行卡")[:64]
    from ..infra.conn import get_cursor
    c = get_cursor()
    try:
        c.execute("SELECT id,shares,cost_cents FROM finance_fund_holdings WHERE user_id=%s AND code=%s", (uid, code))
        row = c.fetchone()
        if row:
            new_shares = float(row.get("shares") or 0) + shares
            new_cost = int(row.get("cost_cents") or 0) + cents
            c.execute("UPDATE finance_fund_holdings SET name=%s,kind=%s,shares=%s,nav=%s,cost_cents=%s,"
                      "value_cents=%s,account=%s,updated_at=CURRENT_TIMESTAMP WHERE id=%s",
                      (name, kind, new_shares, nav, new_cost, int(round(new_shares * nav * 100)), account, row.get("id")))
            hid = row.get("id")
        else:
            c.execute("INSERT INTO finance_fund_holdings(user_id,code,name,kind,shares,nav,cost_cents,value_cents,account) "
                      "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                      (uid, code, name, kind, shares, nav, cents, int(round(shares * nav * 100)), account))
            c.execute("SELECT id FROM finance_fund_holdings WHERE user_id=%s AND code=%s", (uid, code))
            hid = (c.fetchone() or {}).get("id")
        try: c.connection.commit()
        except Exception: pass
        return json_response({"ok": True, "id": hid, "code": code, "shares": round(shares, 4),
                              "nav": round(nav, 4), "amount_cents": cents})
    finally:
        try: c.close()
        except Exception: pass


async def handle_fund_redeem(request):
    uid = _uid(request)
    try:
        item_id = int(request.match_info["id"])
    except (KeyError, ValueError):
        return json_response({"ok": False, "error": "bad_id"}, 400)
    try:
        body = await request.json()
    except Exception:
        body = {}
    from ..infra.conn import get_cursor
    c = get_cursor()
    try:
        c.execute("SELECT id,code,name,shares,nav,cost_cents,account FROM finance_fund_holdings "
                  "WHERE id=%s AND user_id=%s", (item_id, uid))
        row = c.fetchone()
        if not row:
            return json_response({"ok": False, "error": "not_found"}, 404)
        total_shares = float(row.get("shares") or 0)
        if total_shares <= 0:
            return json_response({"ok": False, "error": "empty_holding"}, 400)
        try:
            shares = float(body.get("shares")) if (body or {}).get("shares") is not None else total_shares
        except (TypeError, ValueError):
            return json_response({"ok": False, "error": "bad_shares"}, 400)
        shares = min(max(0.0, shares), total_shares)
        if shares <= 0:
            return json_response({"ok": False, "error": "bad_shares"}, 400)
        nav = float(row.get("nav") or 1)
        proceeds = int(round(shares * nav * 100))
        cost_removed = int(round(float(row.get("cost_cents") or 0) * shares / total_shares))
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        raw_hash = hashlib.sha256(f"fund-redeem:{uid}:{item_id}:{shares}:{now}".encode()).hexdigest()
        account = row.get("account") or "银行卡"
        c.execute("INSERT INTO finance_entries(user_id,account,kind,amount_cents,category,note,occurred_at,raw_hash,source) "
                  "VALUES(%s,%s,'income',%s,'基金赎回',%s,%s,%s,'fund')",
                  (uid, account, proceeds, str(row.get("name") or row.get("code") or "基金")[:60], now, raw_hash))
        remain = total_shares - shares
        if remain <= 1e-6:
            c.execute("DELETE FROM finance_fund_holdings WHERE id=%s AND user_id=%s", (item_id, uid))
        else:
            c.execute("UPDATE finance_fund_holdings SET shares=%s,cost_cents=%s,value_cents=%s,updated_at=CURRENT_TIMESTAMP "
                      "WHERE id=%s AND user_id=%s",
                      (remain, max(0, int(row.get("cost_cents") or 0) - cost_removed),
                       int(round(remain * nav * 100)), item_id, uid))
        try: c.connection.commit()
        except Exception: pass
        return json_response({"ok": True, "id": item_id, "shares": round(shares, 4), "proceeds_cents": proceeds,
                              "account": account})
    finally:
        try: c.close()
        except Exception: pass


async def handle_finance_audit(request):
    return json_response({"ok": True, "data": [], "count": 0})
