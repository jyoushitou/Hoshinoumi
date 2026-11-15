# v25.5.7 架构复审

> 复审对象：`bot/core/version.py` 中 `VERSION = "25.5.7"` 的当前代码。
> 范围：生产入口 `ingress/worker/supervisor`、多用户隔离、本地书、网关、现有架构闸门。
> 结论：**能跑，测试全绿；主要风险不在业务层，集中在生产入口的边界和本地 socket 权限。**

---

## 0. 一句话结论

v25 的 ingress/worker 拆分方向是对的：worker 不再直接暴露 3001/27004，蓝绿切换也有健康检查。

但生产边界还有三个缺口：

1. worker 的 Unix socket 没有设置 `0700 / 0600`，本机其他用户可能绕过 ingress/gateway 直接连 worker。
2. QQ WS 3001 默认 bind `0.0.0.0`，握手没有 token/HMAC 校验，公网可达时可注入伪造 QQ 事件。
3. `/internal/*` 明确免 Bearer，而 ingress 可配置为公网监听；一旦误配，内部接口直接暴露。

---

## 1. 验证结果

| 项 | 命令 | 结果 |
|---|---|---|
| 功能测试 | `.venv/Scripts/python scripts/run_tests.py --fast` | **1022 条，0 失败套件** |
| 未定义名字 | `python scripts/check_names.py` | **通过** |
| 架构闸门 | `python scripts/arch_check.py` | 4 项通过：long_functions / events_reads / startup_ddl / persistence_cycle |
| 代码版本 | `bot/core/version.py` | `25.5.7` |

> 注意：`arch_check.py` **不检查 import 环**，所以“0 环”不能从它推出来。本次没有重跑 Tarjan，不能宣称模块级 0 环。

---

## 2. 当前生产拓扑

```text
NapCat ──WS 3001──> nao-ingress ──qq.sock──> worker
客户端 ──HTTP+JWT 27005──> gateway ──27004──> nao-ingress ──api.sock──> worker
supervisor ──versions/current──> worker（蓝绿）
```

- ingress：`bot/ingress.py`，默认 HTTP `127.0.0.1:27004`、WS `0.0.0.0:3001`。
- worker：`run.py` + `NAO_WORKER_MODE=1`，只监听 Unix socket。
- gateway：`gateway/`，C++，27005，JWT/限流/审计。
- 本地单进程：`start.py`，仍直接监听 3001/27004，只适合调试。

---

## 3. 发现

### P0 · worker Unix socket 权限过宽

**证据**：

- `bot/core/worker.py` `socket_path()` 只 `mkdir`，没有 `chmod`。
- `bind_unix()` 直接 `bind()`，没有设置 socket 权限。
- 默认 umask 022 下，目录通常是 755、socket 通常是 755。

**影响**：

同机其他用户可以直接连 `api.sock` / `qq.sock`，绕过 ingress 和 gateway 的 JWT/限流/审计。多用户或共享主机上是高风险。

**建议**：

```python
os.makedirs(d, mode=0o700, exist_ok=True)
os.chmod(d, 0o700)
...
os.chmod(p, 0o600)
```

同时把 `data/workers` 的父目录权限收紧。

---

### P0 · QQ WS 3001 握手没有鉴权

**证据**：

- `bot/ingress.py` 默认 `--ws-host 0.0.0.0`。
- `bot/chat/handler.py::websocket_handle_qq` 直接接收并 `json.loads`，没有 token/HMAC/来源校验。
- ingress 的 `_ws_proxy` 只做双向字节转发。

**影响**：

任何能连到 3001 的客户端都可以伪造 NapCat 事件，向 bot 注入消息/命令。若 3001 暴露公网，风险为 P0。

**建议**：

- 生产只 bind `127.0.0.1`，由 NapCat 同机连接；或
- 在 ingress 做 WS 握手 token（`?token=` 或 header）+ 来源 IP allowlist；或
- 在 worker 侧校验 NapCat 的 `self_id`/签名，不只看消息结构。

---

### P1 · `/internal/*` 免鉴权 + ingress 可配置公网监听

**证据**：

- `bot/server/http_api.py` 的 auth middleware 明确跳过 `/internal/*`。
- `bot/ingress.py` 的 `--http-host` 可设置为 `0.0.0.0`。
- ingress 把 `/{tail:.*}` 全量转发给 worker。

**影响**：

默认 `127.0.0.1` 是安全的；但一旦为了调试/容器把 ingress HTTP 开到公网，`/internal/chat`、`/internal/audit`、`/internal/auth/*` 会直接可达，绕过 Bearer。

**建议**：

- ingress 强制 `/internal/*` 只接受 loopback；
- 或给 `/internal/*` 单独共享 secret；
- 或把内部接口放到独立 Unix socket，不和 `/api/*` 共用入口。

---

### P1 · ingress 到 worker 的 HTTP 代理没有超时

**证据**：

- `bot/ingress.py::_http_proxy` 每次请求新建 `ClientSession`，`session.request` 没有 `timeout`。
- worker 卡住时，ingress 连接会一直挂着。

**影响**：

worker 假死/慢查询会拖住 ingress，连接堆积；蓝绿切换期间也可能放大。

**建议**：

给 `ClientSession` 或 `session.request` 加 `ClientTimeout(total=...)`，并把 504 映射成可读错误。

---

### P2 · `reuse_port=True`

**证据**：

- `web.TCPSite(..., reuse_port=True)`。

**影响**：

同 UID 的其他进程可以 bind 同一个 27004 抢流量；本地多进程调试方便，但生产不是必要项。

**建议**：

生产默认关闭，调试用 flag 打开。

---

### P2 · 架构闸门没有 import 环检测

**证据**：

- `scripts/arch_check.py` 只有 4 个检查：long_functions、events_reads、startup_ddl、persistence_cycle。
- 文档里“`arch_check` 输出为准”的 0 环说法不成立。

**建议**：

把 Tarjan/import 图检查加进 `arch_check.py`，或明确写“本闸门不检查环”。

---

## 4. 做得好的地方

- ingress 默认 HTTP 只 bind `127.0.0.1`，没有默认把 API 开到公网。
- worker 不监听 3001/27004，方向正确。
- supervisor 先健康检查再切 `current`，失败不切流。
- `current` 支持 symlink 和文本指针，兼容没有 symlink 权限的环境。
- v23 多用户隔离在 repo/tenant 层，不是只靠 API 参数。
- 本地书路径做了 `..`、绝对路径、软链接逃逸检查。
- v24 本地书不导入数据库，符合“即读即清”的设计。

---

## 5. 建议修复顺序

```text
1. worker socket 0700/0600
2. QQ WS 3001 鉴权或改 bind 127.0.0.1
3. /internal/* 与 ingress 监听边界
4. ingress → worker 超时
5. reuse_port 生产关闭
6. arch_check 增加 import 环检查
```

前两项是上线前必须处理的；后四项可以进 v25 收尾或 v26。

---

## 6. 复审边界

- 本次没有做完整 Tarjan import 环复算。
- 没有做渗透测试/公网暴露实测。
- 没有审计全部 1022 条测试的覆盖质量，只确认全绿。
- 没有改代码，只出审查结论。
