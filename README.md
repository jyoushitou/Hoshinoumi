# Hoshinoumi（REC）v27.9.0

> 后端 **v27.9.0** · 网关 **v26.4.0** · schema **29** · 测试 **10000 条**
>
> 以 QQ 为入口的 AI 陪伴后端：长期记忆、关系与生活状态、主动消息、语音/图像、小说阅读，以及可选的 HTTP 网关。

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
![C++17](https://img.shields.io/badge/C%2B%2B-17-00599C)
![Gateway](https://img.shields.io/badge/Gateway-v26.4.0-blue)
![Database](https://img.shields.io/badge/Database-MySQL%20%7C%20SQLite-4479A1)
![Tests](https://img.shields.io/badge/Tests-10000%20passing-brightgreen)
![License](https://img.shields.io/badge/License-MIT-green)

> **Hoshinoumi（REC，记录）** · 友利奈绪 · 星之海学园学生会室
>
> 世界观取自原作结局之后：能力消失，回归普通生活；**乙坂有宇已经意外去世**。
>
> 提到他需要克制，可以打哑谜，但不能假装他还活着。

---

## 1. 这是什么

这不是“接上模型就能聊天”的通用客服机器人，而是：

```text
有长期记忆
有生活状态
有关系变化
会定时/主动找人
人设与代码分离
```

模型只负责“这一句怎么说”；记忆、状态、关系、日程由数据库和代码组装。

| 层 | 管什么 |
|---|---|
| 人设 | 她是谁、怎么说话、在意什么 |
| 记忆 | 对话、长期记忆、事实、关键词、浓缩 |
| 生活 | 心情/精力/孤独、生活事件、日记 |
| 关系 | 亲密度、档位、里程碑、摩擦/冷战/和好 |
| 表达 | 分条、延迟、文字/语音/图片/贴图 |
| 调度 | 定时、主动、空闲、日程 |
| 入口 | QQ WS、HTTP API、C++ 网关 |

### 不是什么

- 不是通用客服 / 知识库问答。
- 不是多租户 SaaS；当前是单主人 `__owner__`。
- 不是公网即开即用；网关有 JWT，但没有 TLS/限流/完整审计。
- 不是插件市场；v27 只有注册表基础，v28 才做运行时。
- 不是零依赖一键包；读书/语音/视觉需要额外依赖和 Key。

### 适合谁

| 适合 | 不适合 |
|---|---|
| 想长期养一个固定角色的个人用户 | 想要开箱即用的客服/知识库 |
| 有 Linux/Windows 基础，能维护 Python、MySQL、Docker | 完全不想碰配置和命令行 |
| 愿意改人设、调参数、看日志 | 要求 100% 事实准确、永不跑偏 |
| 想研究记忆/调度/出站/网关实现 | 需要多租户、高并发、合规审计的团队 |

---

## 2. 当前状态

```text
代码版本    v27.9.0
网关版本    v26.4.0
数据库      schema 29
命令        46 个
数据表      32 张
测试        10000 条（功能 9963 + 环境/迁移 37）
```

v27 当前只完成：

```text
PluginManifest
PluginRegistry
MasterRegistry（5 个注册表，插件表最后）
Manifest/capability/semver 校验
注册表快照与健康状态
```

**还没有**：

```text
插件 loader
插件安装/审批命令
PluginContext
插件 DDL/迁移
!plugin 命令
```

这些在 v28。核心 native 仍然是默认实现，现有功能没有被插件化。

---

## 3. 技术栈

| 部分 | 技术 / 当前实现 |
|---|---|
| **Python 后端** | Python 3.10+（服务器实测 3.12）、asyncio、websockets、aiohttp、protobuf（内部帧）、PyMySQL / SQLite、requests、Pillow、jieba、edge-tts；Playwright / tesseract 按需 |
| **稳定入口** | `bot/ingress.py`：NapCat WS **3001**、gateway TCP **27004**（8+4+body 帧）；worker 只连 Unix socket |
| **C++ 网关** | C++17、Boost.Asio / Boost.Beast、CommonNet、CMake 3.20+、vcpkg overlay ports；客户端 HTTP/JWT **27005** |
| **热更新** | `supervisor` + `data/workers/versions/<version>` + `current` 蓝绿切换；`prepare_worker` 复制代码，共享 `data`、`logs`、`personas`；旧 worker drain 后退出 |
| **存储** | MySQL 8（默认，schema 29）/ SQLite（自动回退）；当前走连接池，v28 计划统一到 `infra/pool` |
| **部署** | gateway 用 Docker / docker compose；ingress / worker 用 systemd 或 screen；Linux 生产、Windows 开发 |
| **外部服务** | NapCat（QQ 协议）、DeepSeek（主对话）、豆包 / 火山方舟（视觉）、ALAPI（搜图） |

### 拓扑

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
│ ingress（bot/ingress.py）              │
│ 持有 3001 / 27004                      │
│ qq.sock / internal.sock → current      │
└──────────────────┬───────────────────┘
                   │ Unix socket
                   ▼
┌──────────────────────────────────────┐
│ worker（run.py，NAO_WORKER_MODE=1）    │
│ 不监听 3001/27004，只接 Unix socket    │
└──────────────────▲───────────────────┘
                   │ 启动 / 健康检查 / 切 current
┌──────────────────┴───────────────────┐
│ supervisor（scripts/nao_supervisor.py）│
│ data/workers/versions/<version>        │
└──────────────────────────────────────┘
```

规则：

```text
NapCat → ingress 3001 → worker qq.sock
gateway 27005 → TCP 27004 帧 → ingress L4 → worker internal.sock
worker 不绑定 3001/27004
27004 只接受 8+4+body 帧，不是 HTTP
```

> ingress 的 3001 对外，必须靠防火墙限制来源；worker 不直接暴露公网。

---

## 4. 特性

| 能力 | 说明 |
|---|---|
| 可换角色 | 人设、生活模板、状态基线在 `personas/<名字>/`，改文件就换人 |
| 说话像人 | 分条发送、按时段浮动延迟、语气受情绪影响 |
| 记得住 | 30 轮对话 + 长期记忆（BM25 + 关键词双路 RRF）+ 关系里程碑 |
| 有自己的生活 | 心情/精力/孤独随时间漂移，会写日记、会主动找你 |
| 会看图 | 多模态看静态图，动图抽帧拼网格 |
| 会说话 | edge-tts 语音，按心情和长度低频触发 |
| 会听 | 语音条转写；转不了就记一笔 |
| 会读小说 | 空闲抓章节、OCR 还原、书架、分享 |
| 有摩擦 | 期待、失落、冷战、和好（24 小时自动恢复） |
| 能调参 | `!config` 改频率/概率，`!stats` 看今日数据 |
| C++ 网关 | 客户端 27005 HTTP/JWT → 27004 TCP 帧 → ingress → worker |
| 可观测 | `!status` `!stats` `!usage` `!db` `!hooks` `!log` |

---

## 5. 快速开始（单进程调试）

### 5.1 依赖

```bash
python3 --version          # 3.10+
python3 -m venv .venv
. .venv/bin/activate       # Windows: .venv\Scripts\activate
python3 -m pip install -r requirements.txt
```

可选：

```bash
python3 -m pip install edge-tts
python3 -m pip install playwright
python3 -m playwright install chromium
```

### 5.2 配置

```bash
cp .env.example .env
cp config.example.json config.local.json
```

编辑 `.env`：

```dotenv
NAO_MASTER_QQ=你的QQ
NAO_DB_HOST=127.0.0.1
NAO_DB_PORT=3306
NAO_DB_USER=nao
NAO_DB_PASS=change-me
NAO_DB_NAME=TomoriNaoBotData
```

API Key 可以：

- 写进 `.env` 的 `DS_API_KEY` / `ARK_API_KEY` / `ALAPI_TOKEN`；
- 或运行 `python3 scripts/configure_api.py` 写数据库。

### 5.3 初始化

```bash
python3 scripts/migrate.py --apply
python3 checks/env_check.py
```

`migrate.py` 幂等；首次和升级都建议跑。

### 5.4 启动

```bash
python3 run.py
```

单进程会启动 QQ WebSocket 与 API，默认端口：

```text
3001  NapCat WS
27004 后端 API / 内部入口
27005  C++ gateway（单独启动）
```

NapCat 的 WebSocket 指向：

```text
ws://服务器地址:3001
```

### 5.5 停止

```bash
Ctrl-C
```

`!exit` / `!quit` 只给主人用。

---

## 6. 生产部署（ingress + worker + supervisor）

不要用 `screen bot` 直接跑一个 `run.py` 当生产入口；那样没有热更新，也容易被误杀。

### 6.1 ingress

```bash
cd ~/Hoshinoumi

set -a
. ./.env
set +a

screen -S ingress

python3 -m bot.ingress \
  --worker-dir data/workers \
  --http-host 127.0.0.1 \
  --ws-host 0.0.0.0 \
  --http-port 27004 \
  --ws-port 3001 \
  --protocol tcp
```

`Ctrl-A D` detach。

### 6.2 准备 worker

```bash
cd ~/Hoshinoumi

set -a
. ./.env
set +a

python3 scripts/prepare_worker.py --version 27.9.0
```

### 6.3 supervisor

```bash
screen -S nao-supervisor

cd ~/Hoshinoumi

set -a
. ./.env
set +a

python3 scripts/nao_supervisor.py \
  --base data/workers \
  --version 27.9.0 \
  --worker-cmd "python3 -u run.py" \
  --timeout 90 \
  --drain-seconds 60
```

### 6.4 gateway

```bash
docker run -d \
  --name hoshinoumi-gateway \
  --network host \
  --restart unless-stopped \
  hoshinoumi-gateway:26.4.0
```

检查：

```bash
curl -s http://127.0.0.1:27005/healthz
curl -s http://127.0.0.1:27005/readyz
```

### 6.5 验收

```bash
python3 scripts/nao_tcp_ping.py
```

QQ：

```text
!version
!ping
```

---

## 7. 热更新

前提：worker 由 supervisor 管，ingress 不动。

```bash
cd ~/Hoshinoumi

# 1. 更新代码
git bundle verify Release/REC-vX.Y.Z.bundle
git fetch Release/REC-vX.Y.Z.bundle main:refs/remotes/bundle/main
git merge --ff-only refs/remotes/bundle/main

# 2. 环境检查
set -a
. ./.env
set +a
python3 checks/env_check.py

# 3. 准备新版本
python3 scripts/prepare_worker.py --version X.Y.Z

# 4. 切流（ingress 不重启）
python3 scripts/nao_supervisor.py \
  --base data/workers \
  --version X.Y.Z \
  --worker-cmd "python3 -u run.py" \
  --timeout 90 \
  --drain-seconds 60
```

注意：

```text
手工 screen 跑的 run.py 不属于 supervisor
→ 不能热更
→ 必须先迁到 supervisor
```

日志：

```text
根 logs/nao-YYYY-MM-DD.log        # prepare_worker 软链共享
data/workers/versions/<v>/worker.log  # supervisor stdout
```

---

## 8. 命令（46 个，仅主人）

### 基础

```text
!ping  !version  !help  !status  !uptime  !stats  !usage
!log  !db  !meta  !update  !reload  !code  !exit  !quit
```

### 记忆与关系

```text
!memory  !memorybook  !event  !keywords  !relation
!growth  !profile  !clear
```

### 媒体

```text
!img  !voice  !vision  !sticker  !acg  !clip
```

### 日常

```text
!diary  !todo  !cron  !hooks  !task
```

### 阅读

```text
!book  !books
```

### 配置与运维

```text
!config  !set  !persona  !apikeys  !adduser
!gw  !say  !sayg  !backup  !history
```

完整命令表与参数以 `!help` / `bot/cmd/` 为准。

---

## 9. 数据与存储

```text
默认 MySQL 8
连不上自动退 SQLite
schema 29
32 张表
```

迁移：

```bash
python3 scripts/migrate.py          # 预览
python3 scripts/migrate.py --apply  # 执行
```

备份/恢复：

- [docs/存储后端与备份.md](docs/存储后端与备份.md)
- `!backup`

---

## 10. 测试

```bash
python3 scripts/run_tests.py          # 10000 条
python3 scripts/check_names.py        # 静态检查
```

当前：

```text
功能 9963
环境/迁移 37
合计 10000
```

以后新增功能按影响面系数扩测试：

```text
新命令：参数 × 权限 × 成功/失败 × 边界
新存储：操作 × MySQL/SQLite × 异常/回滚
新接口：方法 × 正常/越权/非法参数/并发
修 bug：根因 + 相邻边界 + 回归
```

---

## 11. 目录

```text
bot/               Python 后端
  ingress.py       稳定入口（3001 / 27004）
  registry/        v27 插件注册表基础
  cmd/             命令
  chat/            QQ 收发与消息处理
  ai/              模型调用与回复解析
  memory/          记忆检索
  life/            生活状态/日记/摩擦
  schedule/        定时/日程/提醒
  infra/           DB/连接池/仓储/日志/阻塞
  egress/          唯一出站口

gateway/           C++ 网关（v26.4）
proto/             内部帧契约
scripts/           迁移/打包/自检/热更新
tests/             功能测试
checks/            环境与迁移检查
personas/          角色卡
data/              运行时数据
logs/              日志
docs/              文档
```

---

## 12. 已知限制

| 限制 | 状态 |
|---|---|
| 单主人 `__owner__` | 当前就是单用户模型 |
| 多用户隔离 | 后续版本 |
| 网关 TLS / 按用户限流 | 还没有 |
| 插件运行时 | v28 |
| `!plugin` 命令 | v28 |
| Web / 桌面 / 手机端 | v45+ |
| 100% 稳定 | 不保证；有降级/备份/看门狗，但不是高可用系统 |
| Windows 生产 | 仅开发；生产建议 Linux |

---

## 13. 文档

| 文档 | 内容 |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 分层与消息生命周期 |
| [docs/DB-DESIGN.md](docs/DB-DESIGN.md) | 数据库设计 |
| [docs/INTERFACE-PLAN-v27-v44.md](docs/INTERFACE-PLAN-v27-v44.md) | 18 个接口版本 |
| [docs/PLUGIN-RUNTIME-DESIGN.md](docs/PLUGIN-RUNTIME-DESIGN.md) | v28 插件运行时契约 |
| [docs/versions/](docs/versions/) | 每版开发记录 |
| [docs/ROADMAP.md](docs/ROADMAP.md) | 大版本总表 |
| [docs/HOT-UPDATE-POLICY.md](docs/HOT-UPDATE-POLICY.md) | 热更新策略 |
| [docs/DEPLOY-v26.md](docs/DEPLOY-v26.md) | v26 部署 |
| [docs/POSTMORTEM-2026-11-15-STARTUP-HANG.md](docs/POSTMORTEM-2026-11-15-STARTUP-HANG.md) | 上线后失联复盘 |

---

## 14. 声明

- 本项目是《Charlotte》的非官方二创，不包含官方素材。
- 本地小说阅读只提供 TXT/EPUB 解析工具；文件与来源由使用者提供，本项目不提供、不审核、不托管版权内容。
- QQ 平台风控、账号风险由使用者自行承担。
- 仓库代码使用 MIT License；第三方组件遵循各自许可证。
