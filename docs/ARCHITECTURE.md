# 架构图（v35.2.0.0 / v27–v40 接口规划）

> 当前后端 v35.2.0.0；网关 v26.4.0；schema 32。
>
> 已部署架构：ingress 持有 3001/27004，worker 只走 Unix socket，蓝绿热更新。
>
> v27–v34 已完成；v35.1/v35.2 已实现；v35.2.1 起为规划。
>
 > 配套：v27–v36 总纲见 [INTERFACE-PLAN-v27-v36.md](INTERFACE-PLAN-v27-v36.md)。

---

## 0. 生产拓扑（v27.9.0）

```text
QQ 用户
  │ WS 3001
  ▼
NapCat ───────────────┐
                      │
客户端/Web/IDE         │
  │ HTTP+JWT 27005    │
  ▼                   │
gateway（C++）         │
  │ TCP 27004 帧      │
  ▼                   ▼
┌──────────────────────────────────────┐
│ nao-ingress（bot/ingress.py）          │
│ 持有 3001 / 27004                      │
│  qq.sock / internal.sock → current     │
│  27004 = 8+4+body TCP L4，不是 HTTP     │
└──────────────────┬───────────────────┘
                   │ Unix socket
                   ▼
┌──────────────────────────────────────┐
│ worker（run.py，NAO_WORKER_MODE=1）    │
│ 不监听 3001/27004，只接 Unix socket    │
│ 同一套 app.bootstrap / app.loop        │
└──────────────────▲───────────────────┘
                   │ 启动 / 健康检查 / 切 current
┌──────────────────┴───────────────────┐
│ supervisor（scripts/nao_supervisor.py）│
│ data/workers/versions/<version>        │
│ current 指针蓝绿切换                    │
└──────────────────────────────────────┘
```

规则：

```text
NapCat → ingress 3001 → worker qq.sock
gateway → ingress 27004 TCP 帧 → worker internal.sock
worker → server/tcp_internal.py → 内部 HTTP Unix → 业务
```

- worker 不绑定 3001/27004。
- 27004 只接受 8+4+body 帧，HTTP 不可用。
- ingress 每条新连接按 `current` 解析 socket；旧连接留在旧 worker。
- supervisor 先健康检查，再切 `current`，旧 worker drain 后退出。

## 1. 运行分层

| 层 | 内容 |
|---|---|
| 外部入口 | NapCat / gateway 27005 / 自有客户端 |
| 稳定入口 | ingress 3001 + 27004；supervisor/current |
| worker | app.bootstrap / app.loop / 业务与能力 |
| 存储资源 | MySQL / SQLite / data / backups / 远程 API |

## 2. worker 内部代码层

```text
1. 入口/装配   run.py → bot.main → app.bootstrap / app.loop
2. 接入/协议   ingress、server.http_api、server.tcp_internal、ports
3. 交互/控制   chat.handler、cmd.registry、events.registry、scheduler
4. 业务层      life、diary、schedule、reading
5. 能力层      ai、memory、image、speech
6. 基础设施    infra（conn/pool/repo/log/cache/blocking）、egress
7. 存储/外部   MySQL / SQLite / 文件 / 网络
8. 插件层      v27 注册表已完成；v28 运行时规划中
```

核心 native 不进入插件表；插件通过 v27/v28 的注册表、权限、加载器、任务池接入。

## 3. 一次请求的路径

### QQ

```text
NapCat WS 3001
→ ingress
→ current worker qq.sock
→ chat.handler
→ chat.inbound
→ ai / memory / life / schedule
→ egress
→ ingress
→ NapCat
```

### 网关 API

```text
客户端 27005 HTTP
→ gateway JWT/限流
→ 8+4+body TCP 27004
→ ingress L4
→ current worker internal.sock
→ tcp_internal.dispatch
→ 内部 HTTP Unix
→ 业务 handler
→ 帧回传 gateway
```


## 3.1 数据流（v28 计划）

### 数据面

```text
QQ:
NapCat WS 3001
  → ingress 3001
  → worker qq.sock
  → chat.handler / chat.inbound
  → 业务层（ai / memory / life / schedule）
  → egress
  → ingress
  → NapCat

网关 API:
客户端 HTTP 27005
  → gateway JWT / 限流 / 审计
  → 8+4+body TCP 帧 27004
  → ingress TCP L4
  → worker internal.sock
  → server.tcp_internal.dispatch
  → 内部 HTTP Unix
  → 业务 handler
  → frame 回传 gateway
```

规则：

- 外部只看到 `3001` / `27005` / `27004`（本机）。
- ingress 只做连接和 L4 转发，不解析业务。
- worker 不绑定 3001/27004。
- 27004 是帧协议，不再是 HTTP。
- 核心 native 不经过插件表；插件只通过注册表/运行时接入。

### 控制面

```text
supervisor
  ├─ data/workers/current
  ├─ /healthz /readyz（Unix socket）
├─ /api/health（兼容）
├─ /api/tools（DSH 只读工具）
  ├─ 切换时清理 + 1h 后清理
  └─ worker.pid / worker.log

update
  ├─ update.json 准入
  ├─ schema / requires_restart 检查
  └─ 拒绝需迁移/重启版本

registry（v27+）
  ├─ command / events / life / ai / plugin
  ├─ MasterRegistry 静态登记
  └─ v28 增加安装/审批/权限/错误/任务
```

### 状态归属

| 数据 | 位置 | 生命周期 |
|---|---|---|
| NapCat / HTTP 连接 | ingress | 连接关闭即结束 |
| worker 内存、缓存、任务 | worker 进程 | 进程退出即结束 |
| 用户、记忆、对话、日程、阅读进度 | MySQL | 持久 |
| 本地书、日志、worker 版本目录 | `data/` | 文件生命周期 |
| 当前版本指针 | `data/workers/current` | 切换时更新 |
| 插件安装/审批/权限/错误 | `plugin_*`（v28 schema 30） | 持久 |
| 插件代码 | 版本目录快照 | 跟随 worker |

### 插件数据流（v28）

```text
启动:
  MasterRegistry 初始化
  → 读取插件注册表/审批状态
  → manifest-first loader
  → PluginContext 创建
  → 权限检查
  → register
  → auto_start（若启用）

运行:
  核心调用点
  → capability 路由
  → 核心 native 或插件 adapter
  → 权限/scope 校验
  → TaskManager 归属任务
  → 错误记录/降级

停止:
  worker drain / SIGTERM
  → TaskManager.cancel(plugin:...)
  → plugin.stop(ctx)
  → registry.unregister
```

插件状态不放在 `features.json`；核心 native 不实现 `PluginManifest`。v28 只做运行时，插件 DDL 统一在 v38。

## 4. 热更新与插件生命周期

worker 热更新：

```text
prepare_worker 复制新代码 + 启用插件快照
→ 新 worker 启动
→ health
→ current 切换
→ 旧 worker drain 60s
→ 旧 worker SIGTERM
```

插件生命周期**跟随 worker**，不跟随 ingress：

```text
worker SIGTERM / drain
→ TaskManager.cancel(plugin:...)
→ plugin.stop(ctx)，最多 5s
→ 关闭插件连接/游标
→ registry.unregister(plugin)
```

插件被禁用、连续失败自动停用、版本升级时走同一 stop 流程。ingress 重启不触发插件 stop；它只断流量。

## 5. 配置 / 注册表

```text
features.json       核心内置功能开关
config.local.json   核心参数
appconfig           核心运行时可调项
registry            插件安装/启用/审批/错误状态
```

插件启用状态在注册表，不在 `features.json`。

## 6. v27–v37 接口映射

```text
v27 插件注册表基础       v28 插件运行时
v29/30 模型              v31/32 记忆
v33 接口层收口（通道/工具/存储/调度/出站/默认链路）
v34 学习规划              v35 多端与客户端
v36 生态接入              v37 运维与嵌入式
```

v33 一次收口六层接口；核心 native 不实现 PluginManifest，不进入插件表。

## 7. 当前架构债

- `bot/ports` 实际只有 2 个模块引用，v29 起逐层补。
- `infra/conn` 与 `infra/pool` 并存，v28.1 已支持 repo pool，后续继续收口。
- 约 164 处 `except Exception: pass`，插件链路不得静默。
- 旧兼容层：`bot/api.py`、`api_server.py`、`handler.py`、`config.py`；`bot/db.py` 已无引用可删。
- v33–v37 是合并后的规划，落地前仍需逐版复审。
