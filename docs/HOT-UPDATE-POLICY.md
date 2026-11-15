# 热更新策略（v25 之后强制）

> 结论：**v25 之后，普通业务版本只切 worker，不停 ingress/gateway。**  
> 只有改动到“协议/端口/schema/系统依赖”这类无法共存的变更，才允许整套重启。

## 1. 稳定入口

```text
NapCat ──3001──> ingress ──unix qq.sock──> worker
gateway ──27004 TCP──> ingress ──unix internal.sock──> worker
外部客户端 ──27005──> gateway
```

`ingress` 和 `gateway` 是稳定层，`worker` 是版本层。

worker 每次发布：

```text
data/workers/versions/<version>/
  bot/...
  api.sock / qq.sock / internal.sock
  .env -> 根目录 .env
  config.local.json -> 根目录
  data -> 根目录 data
  personas -> 根目录 personas
```

## 2. 什么必须热更

| 改动 | 需要重启 ingress/gateway？ | 方式 |
|---|---|---|
| `bot/` 业务代码 | 否 | `prepare_worker` + supervisor |
| 配置 / 提示词 / 人设 / 模板 | 否 | 热加载或 worker 重启 |
| Python 依赖（已装好） | 否 | 新 worker 启动时加载 |
| 新增 worker 内部模块 | 否 | 新版本目录 |
| 网关代码 | 是（只重启 gateway 容器） | 重建镜像 |
| ingress 代码 | 是（只重启 ingress） | 端口短暂中断 |
| 帧格式 / 协议不兼容 | 是（ingress + gateway + worker） | 整套切换 |
| DB schema 不兼容 | 是（按迁移窗口） | 停写、迁移、启动 |
| OS/Python/驱动升级 | 是 | 整套维护窗口 |

## 3. 验收强制项

每个版本合入前必须通过：

```bash
python3 scripts/run_tests.py
python3 scripts/check_names.py
python3 scripts/arch_check.py --strict
```

并包含 `tests/test_hot_update_contract.py`：

- worker mode 必须用 `start_unix_frame_server`
- ingress 必须有 `_tcp_proxy` 和 `internal.sock`
- supervisor 必须注入 `NAO_WORKER_MODE` / `NAO_WORKER_VERSION` / `NAO_INTERNAL_TCP`
- ingress 必须按 `current` 解析 socket

## 4. 部署操作约束

生产**禁止**：

```text
python3 -u run.py 直接占 3001/27004
```

除非是本地调试。生产必须：

```text
ingress（TCP L4）
→ supervisor 启 worker
→ current 切换
```

## 5. v25 → v26 的唯一例外

v25 的 27004 是 HTTP，v26 是 8+4+body TCP。协议不兼容，所以第一次升 v26 必须：

```text
重启一次 ingress，加载 --protocol tcp
之后 worker 更新全部热更
```

这不是“每次版本都重启整套设备”，只是协议切换的一次性 ingress 重启。

## 6. 热更新流程

```bash
python3 scripts/prepare_worker.py --version X.Y.Z
python3 scripts/nao_supervisor.py \
  --base data/workers \
  --version X.Y.Z \
  --worker-cmd "python3 -u run.py" \
  --timeout 90 \
  --drain-seconds 60
```

ingress 不重启；新 TCP/WS 连接走新 worker，旧连接 drain 后退出。
