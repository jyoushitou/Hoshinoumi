# 架构图（v17.11.0）

> 配套阅读：**[ARCH-REVIEW.md](ARCH-REVIEW.md)**（审查结论与修复顺序）
> 本文只画结构，不评价好坏。图中 ⚠ 标记的位置是已知的架构债。

---

## 1. 分层总览

```
                        ┌──────────────────────────────┐
     启动              │  run.py                      │
                        │   └→ botv.main               │
                        │       └→ app.bootstrap       │  建表/迁移/加载状态
                        │       └→ app.loop.serve      │  常驻循环
                        └──────────────┬───────────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        │                              │                              │
┌───────▼────────┐          ┌──────────▼──────────┐        ┌──────────▼─────────┐
│ 接入：QQ        │          │ 接入：HTTP API       │        │ 接入：定时          │
│ chat.handler    │          │ server.http_api      │        │ schedule.runner     │
│ websocket_qq    │          │ routes_chat/meta     │        │ executors.ticker    │
└───────┬────────┘          └──────────┬──────────┘        └──────────┬─────────┘
        │                              │                              │
        │ 命令                          │ 状态/配置                     │ 到点判定
        └──────────────┬───────────────┴──────────────┬───────────────┘
                       │                              │
              ┌────────▼─────────┐          ┌─────────▼──────────┐
              │ 调度层            │          │ 命令层              │
              │ scheduler         │          │ cmd/*  (36 个命令)   │
              │  队列/策略/worker  │          └─────────┬──────────┘
              │ executors/*       │                    │
              └────────┬──────────┘                    │
                       │                               │
        ┌──────────────┴───────────────┬───────────────┘
        │                              │
┌───────▼─────────┐          ┌─────────▼──────────┐
│ 业务层           │          │ 能力层              │
│ chat  (收发/分条) │          │ ai     (模型/解析)  │
│ life  (生活/关系) │          │ memory (检索/预算)  │
│ diary (日记)      │          │ image  (抓图/存档)  │
│ schedule (定时)   │          │ speech (语音/转写)  │
└───────┬─────────┘          └─────────┬──────────┘
        │                              │
        └──────────────┬───────────────┘
                       │
        ┌──────────────▼───────────────────────────────┐
        │ 基础层                                        │
        │ core    运行时状态 / 配置 / 锁 / 指标 / 版本    │
        │ infra   连接池 / 仓库 repo_* / schema / 日志    │
        │ ports   接口（ChatModel / Transport）          │
        │ events  Event + 注册表                        │
        │ egress  唯一出站口 + 合并                      │
        └──────────────┬───────────────────────────────┘
                       │
              ┌────────▼─────────┐
              │ MySQL / SQLite   │
              │ + data/ 文件      │
              └──────────────────┘
```

**规则**：箭头只允许向下（上层可以依赖下层，反之不行）。
审查结果：**包级 0 环**，但有 12 处反向依赖（详见 §5）。

---

## 2. 一条消息的生命周期

```
 QQ 用户
   │  发消息
   ▼
 NapCat（QQ 协议端）
   │  WebSocket（机器人是服务端，监听 0.0.0.0:3001）
   ▼
 chat.handler.websocket_handle_qq
   │  ① inbound.parse_message_content   解析文本/图片/语音/@
   │  ② 去重（msg_id）+ 群聊闸门 + 冷却
   │  ③ chat.batcher                    连发合并（0.6 秒防抖）
   ▼
 ai.client.get_character_reply
   │  ⚠ 这里 import 了 8 个 life 模块来拼 prompt（v17.15 要修）
   │  → run_blocking → DeepSeek / 豆包
   ▼
 ai.parse.parse_ai_reply
   │  拆出：对话 / 动作 / 图片关键词 / 事件 / 精炼关键词
   ▼
 chat.send.send_short_reply
   │  ④ 分条 + 按时段延迟 + 归一化去重（v17.13）
   │  ⑤ 语音/贴图择时
   ▼
 egress.outbound
   │  ⑥ 全局锁 → ws.send（**唯一出口**，别处不许直接 ws.send）
   │  ⑦ 断线入队，重连补发
   ▼
 NapCat → QQ
```

---

## 3. 调度器模型（v17.1 起）

```
 触发源（全部转成 Event）
 ┌──────────────┐
 │ idle_tick     │  每 30 分钟：该不该读书
 │ proactive_tick│  每 30 分钟：该不该主动找他
 │ minute_tick   │  每 30 秒：跨天/日记/场景派发
 │ schedule_scene│  催起床/午睡/复盘…（定时表）
 │ agenda_remind │  日程到点
 │ pending_nudge │  待办到点
 │ cron_task     │  用户自建定时（cron 表）
 │ diary         │  凌晨 3 点写日记
 └──────┬───────┘
        │  submit(kind, key, args)
        ▼
 ┌──────────────────────────────────────────┐
 │ EventQueue（三档 + 去重）                  │
 │   CHAT  ── 不排队，独占快车道               │
 │   EVENT ── 快车道                          │
 │   IDLE  ── 慢车道，容量满丢最旧              │
 └──────┬───────────────────────┬───────────┘
        │                       │
 ┌──────▼───────┐        ┌──────▼──────────┐
 │ 快车道 worker │        │ 慢车道 worker ×2 │
 │ CHAT → EVENT │        │ EVENT → IDLE    │
 └──────┬───────┘        └──────┬──────────┘
        └───────────┬───────────┘
                    ▼
        ┌───────────────────────┐
        │ policy                │
        │  超时 → 放弃（不重试）  │
        │  失败 → 2/4/8 秒退避   │
        │  连败 3 次 → 熔断 1h   │
        └───────────────────────┘
```

**为什么分车道**：慢车道的读书任务再多，也不能挡住 P0 聊天。

---

## 4. 存储与出站

### 4.1 存储（v17.11 支持双后端）

```
      业务代码
         │
         ├─ infra.repo_memory   (记忆/生活/阅读，49 条 SQL)
         ├─ infra.repo_ai       (原始返回)
         ├─ infra.repo_key      (API key)
         ├─ infra.repo_log      (日志落库)
         ├─ infra.repo_profile  (画像)
         ├─ infra.store_v2      (新表双读：先新表，空则回退旧表)
         └─ schedule.cron       (cron_tasks)
                    │
                    ▼
              infra.conn（连接池，5 条）
                    │
        ┌───────────┴───────────┐
        │ backend=mysql         │ backend=sqlite
        │ pymysql               │ data/nao.db
        └───────────────────────┘
```

### 4.2 出站（v17.2）

```
 chat.send.send_short_reply ─┐
 chat.transport              ├→ egress.outbound ──→ ws.send
 cmd.ops（运维命令）          │       │
 executors.schedule（合并）   ┘       ├ 全局锁（防帧交错）
                                     ├ 断线入队
                                     └ echo 等待（撤回/取消息）
```

---

## 5. 已知的架构债（在图上标 ⚠）

```
 ① 持久层九模块环（v17.14 修）

    core.settings ──→ log ──→ db ──→ repo_* ──→ infra.conn ──→ core.settings
         ↑                                              │
         └──────────────────────────────────────────────┘

    后果：数据库挂了日志也没了；导入顺序敏感。

 ② ai 反向依赖 life（v17.15 修）

    ai.client ──→ life.state / events / relation / habit
              ──→ life.milestone / friction / digest / reading

    后果：ai 层无法独立测试，启动连带加载 18 个 life 模块。

 ③ 命令层/HTTP 层写 SQL（v17.16 修）

    cmd.query(6) · cmd.memory_cmd(2) · server.routes_meta(6) · log(1)
```

更详细的分析与修法见 **[ARCH-REVIEW.md](ARCH-REVIEW.md)**。

---

## 6. 包职责一览

| 包 | 行数 | 一句话 |
|---|---|---|
| `app` | 136 | 启动装配：建表、加载状态、常驻循环 |
| `core` | 571 | 运行时状态、配置、锁、指标、单实例、版本 |
| `infra` | 1592 | 连接池、仓库层、schema、日志落库、监控、线程池 |
| `ports` | 106 | 接口定义（ChatModel / Transport），换后端用 |
| `events` | 95 | `Event` + 注册表 |
| `scheduler` | 351 | 队列 / 策略 / worker / 入口 |
| `egress` | 229 | 唯一出站口 + 定时消息合并 |
| `executors` | 652 | 调度器上的事件处理（ticker/idle/proactive/schedule/reminders/cron/diary） |
| `chat` | 1164 | 收消息、解析、闸门、分条、合并、发送 |
| `cmd` | 1003 | 36 个命令 |
| `ai` | 950 | 模型调用、回复解析、人设、工具、视觉 |
| `memory` | 236 | 上下文组装、BM25 检索、预算 |
| `life` | 2313 | 生活状态、关系、习惯、摩擦、里程碑、读书、日程、天气 |
| `diary` | 323 | 日记生成 / 存储 / 查看 |
| `schedule` | 537 | 定时任务表、时间解析、场景规划 |
| `image` | 248 | 抓图、存档、标签 |
| `speech` | 84 | TTS / ASR |
| `server` | 359 | HTTP API（聊天入口、状态、配置） |
| `utils` / `log` / `heartbeat` / `sticker_archive` / `clip` | 283 | 工具与兼容层 |

---

## 7. 三条硬约束

| 约束 | 位置 | 违反的后果 |
|---|---|---|
| **唯一出站口** | `egress.outbound` | 并发发送时 JSON 帧交错（心跳插进气泡中间） |
| **阻塞调用必须走 `run_blocking`** | `infra.blocking` | 一次卡住的请求永久占线程，池慢慢空 |
| **P0 聊天不排队** | `scheduler` 快车道 | 读书/抓取时回消息变慢 |

前两条都有测试守卫（`tests/test_egress_guard.py`、`tests/test_infra.py` 里的 no-raw-thread）。

---

## 8. 复现本图的数据来源

```bash
# 包规模、函数长度、依赖热点
python .tmp/arch_audit.py

# 真环（Tarjan）、未覆盖模块
python .tmp/arch_deep.py

# 精确环（按文件路径解析相对导入）
python .tmp/arch_cycles2.py
```
