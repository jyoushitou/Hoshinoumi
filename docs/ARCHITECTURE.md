# 架构图（v18.20.0）

> 配套阅读：**[ARCH-REVIEW.md](ARCH-REVIEW.md)**（量化审查、问题与修复顺序）
>
> v18 已封存，本图描述 **v18.20.0 的实际运行结构**；v19 的架构/对话底座、v20 网关、v21 多用户目标见
> [versions/v19.md](versions/v19.md) 与 [versions/v20.md](versions/v20.md)、[versions/v21.md](versions/v21.md)。图中 ⚠ 是已知架构债，不代表当前不能用。

---

## 1. 分层总览

```
                        ┌──────────────────────────────────┐
     启动              │  run.py                          │
                        │   ├→ 配置检查 / 依赖检查          │
                        │   └→ botv.main                    │
                        │        ├→ app.bootstrap           │  加载密钥/状态/人设
                        │        │   ├→ _ensure_tables()    │  ⚠ 启动时改表
                        │        │   └→ _ensure_cron_schema()│  ⚠ 启动时补列
                        │        └→ app.loop.serve          │  常驻循环
                        └──────────────┬───────────────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        │                              │                              │
┌───────▼────────┐          ┌──────────▼──────────┐        ┌──────────▼─────────┐
│ 接入：QQ        │          │ 接入：HTTP API       │        │ 接入：调度          │
│ chat.handler    │          │ server.http_api      │        │ scheduler           │
│ chat.inbound    │          │ routes_chat/meta     │        │ executors/*         │
│ chat.cache ⭐    │          └──────────┬──────────┘        │ schedule.items ⭐    │
└───────┬────────┘                     │                   └──────────┬─────────┘
        │                              │                              │
        │ 命令（同步）                  │ 状态/配置                     │ 到点事件
        └──────────────┬───────────────┴──────────────┬───────────────┘
                       │                              │
              ┌────────▼─────────┐          ┌─────────▼──────────┐
              │ 调度层            │          │ 命令层              │
              │ 三档队列 / worker │          │ cmd/*（39 个命令）   │
              │ 超时/重试/熔断     │          └─────────┬──────────┘
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
│ executors (执行器)│          │ life.recall ⭐       │
└───────┬─────────┘          └─────────┬──────────┘
        │                              │
        └──────────────┬───────────────┘
                       │
        ┌──────────────▼───────────────────────────────┐
        │ 基础层                                        │
        │ core    状态 / 配置 / 锁 / 指标 / 版本 / 时钟   │
        │ infra   conn / repo_* / schema / cache ⭐ /     │
        │         backup ⭐ / blocking / log             │
        │ ports   接口（ChatModel / Transport）           │
        │ events  Event + 注册表                         │
        │ egress  唯一出站口 + 合并                       │
        └──────────────┬───────────────────────────────┘
                       │
              ┌────────▼─────────────────────────┐
              │ MySQL（默认）/ SQLite（自动降级）  │
              │ memories / 新表 / events 只读视图  │
              │ + data/ 文件 + backups/            │
              └──────────────────────────────────┘
```

⭐ = v18 新增或显著改动的部件：
`chat.cache`（引用消息缓存）、`life.recall`（突然想起）、`infra.cache`（TTL）、
`infra.backup`（自动备份）、`schedule.items`（日程/待办 `call_at` 钩子）。

**规则**：箭头只允许向下；上层可依赖下层，下层不反向依赖上层。
当前：**包级 0 环**；模块级精确环 **5 个**（见 §5 与审查文档），比 v17.11 的 6 个少 1 个
（`schedule.planner` 已在 v18.9 删除）。

---

## 2. 一条消息的生命周期（v18.6 起异步派发）

```
 QQ 用户
   │
   ▼
 NapCat（QQ 协议端）
   │  WebSocket（机器人是服务端，监听 0.0.0.0:3001）
   ▼
 chat.handler.websocket_handle_qq
   │  ① 命令判定：! / ！，全角先归一化（v18.20）
   │     ├─ 是命令 → 同步执行（不排模型后面）
   │     └─ 普通消息 → asyncio.create_task(_handle_message)（v18.6）
   │        NAO_ASYNC_DISPATCH=0 时退回串行
   ▼
 chat.inbound.parse_message_content
   │  ② 解析文本/图片/语音/@
   │  ③ 引用消息：先查 chat.cache（200 条环形）
   │     未命中 → get_msg，2 秒超时；仍没有 → 明确降级（v18.6）
   ▼
 chat.handler._handle_message
   │  ④ 去重（msg_id）+ 群聊闸门 + 冷却
   │  ⑤ chat.batcher 连发合并（0.6 秒防抖）
   ▼
 ai.client.get_character_reply
   │  ⑥ 生命周期/记忆/人设/画像拼 prompt
   │     lifeport 取生活状态；memory 做 BM25 + RRF；图片/时间线注入
   │  ⑦ run_blocking → DeepSeek / 豆包（失败/空回复可见）
   ▼
 ai.parse.parse_ai_reply
   │  ⑧ 拆出：对话 / 动作 / 图片关键词 / 事件 / 精炼关键词
   ▼
 chat.send.send_short_reply
   │  ⑨ 分条：最多 4 个气泡，超出合并相邻短句（v18.10）
   │  ⑩ 按时段浮动延迟；语音/贴图择时
   ▼
 egress.outbound
   │  ⑪ 全局锁 → ws.send（唯一出口）
   │  ⑫ 断线入队，重连补发；echo 等待（撤回/取消息）
   ▼
 NapCat → QQ
```

**NapCat 的定位：QQ 通道网关，不是 v20 体系网关。**

| 维度 | NapCat | v20 网关 |
|---|---|---|
| 位置 | **南向**：QQ ↔ botv | **北向**：公网 ↔ botv |
| 角色 | QQ 协议适配器 / 通道网关 | 体系网关 / 公网唯一入口 |
| 协议 | OneBot v11（WS/HTTP） | HTTPS/WSS + JSON ↔ gRPC |
| 鉴权 | QQ 登录（一个 bot 账号） | JWT `sub=user_id` + 角色 |
| 多用户 | 一个 QQ 号服务多个 QQ 用户 | 多个人类账号/租户 |
| 可信边界 | 本机可信 | 公网不可信 |
| 能否互相替代 | **不能** | **不能** |

### 流量控制放哪

| 方案 | 做法 | 结论 |
|---|---|---|
| **A. 直连 + 进程内限流**（默认） | NapCat → botv loopback；`chat/inbound` / `egress/outbound` 做令牌桶 + 有界队列 | ✅ 少一跳、低延迟 |
| **B. 独立 QQ 通道网关** | NapCat → channel-gw → botv；mTLS、按 QQ 号配额 | 🟡 多 QQ 号 / NapCat 不在本机时 |
| **C. 走 v20 体系网关** | v20 同时说 OneBot/JWT，代理 NapCat | ❌ 协议/鉴权/信任边界全混 |

v20 **不接** OneBot；QQ 限流在 channel adapter，不在 v20。

---

## 3. 调度模型（v18.7 起：`call_at` 秒级钩子）

v17.1 的三档队列仍然是底座；但**到点触发**已经从 `minute_tick` 扫表改成 `loop.call_at`。

```
  触发源
  ┌─────────────────────────────────────────────────────────────┐
  │ cron_tasks       每个任务一个 call_at；exact 提前 30 秒预生成 │
  │ agenda / pending schedule.items 每个 item 一个 call_at       │
  │ proactive        20–40 分钟 + 随机秒                          │
  │ idle             25–35 分钟 + 随机秒                          │
  │ minute_tick      每 30 秒：跨天 / 04:00 对账 / 看门狗 / 备份   │
  └───────────────────────────┬─────────────────────────────────┘
                              │ Event
                              ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ EventQueue（三档 + 去重）                                     │
  │   CHAT  ── 不排队，独占快车道                                │
  │   EVENT ── 快车道                                            │
  │   IDLE  ── 慢车道，容量满丢最旧                               │
  └───────────────────────────┬─────────────────────────────────┘
                              │
        ┌─────────────────────┴─────────────────────┐
        ▼                                           ▼
  快车道 worker（CHAT → EVENT）              慢车道 worker ×2（EVENT → IDLE）
        │                                           │
        └─────────────────────┬─────────────────────┘
                              ▼
                    policy：超时放弃 / 2·4·8 秒退避 / 连败 3 次熔断 1 小时
```

**关键变化**：

- 到点判定不再由 `minute_tick` 每 30 秒扫 `process_due`；`cron`、`items`、`proactive`、`idle`
  各自 `call_at`。
- `minute_tick` 只做跨天、04:00 对账、60 秒钩子看门狗、每月 1 号 04:30 备份。
- 看门狗只重排丢失的钩子，**不补发**已过期提醒。
- 准点任务（`timing=exact`）在 T−30 秒预生成；到点绕过 3 秒合并窗口。
- 习惯任务（`timing=habit`）只允许晚 0–jitter 分钟，不提前。
- 日程/待办钩子集中在 `schedule/items.py`；启动 `schedule_all()` 重建。

**⚠ 生命周期债**：`cron._fire_prepare` 的 `call_at` 没有登记进 `handles`，删除/重排任务时
不会取消；`items.watchdog()` 每 60 秒调用 `schedule_all()`，会整批重挂钩子。功能上安全，
但高频重排和预生成残留值得在 v19 收敛。

---

## 4. 存储与出站

### 4.1 存储（v18.17：memories 统一，events 变只读视图）

```
       业务代码
          │
          ├─ infra.repo_memory   (记忆/生活/阅读/状态/待办/画像)
          ├─ infra.repo_ai       (原始返回)
          ├─ infra.repo_key      (API key)
          ├─ infra.repo_log      (日志落库)
          ├─ infra.repo_profile  (画像)
          ├─ infra.store_v2      (新表双读：先 memories/bot_states，空则回退)
          ├─ infra.cache         (TTL：counts 5s / cron list 3s)
          ├─ infra.backup        (SQLite .backup / MySQL mysqldump + gzip)
          └─ schedule.cron       (cron_tasks / cron_overrides)
                     │
                     ▼
              infra.conn（连接池，5 条）
                     │
        ┌────────────┴────────────┐
        │ backend=mysql           │ backend=sqlite
        │ pymysql                 │ data/nao.db
        └────────────┬────────────┘
                     ▼
   memories（统一记忆：event/life/photo/todo/agenda/state/rel/habit/reading/profile）
   + 专用新表：bot_states / relations / friction_states / habits /
              reading_progress / facts / cron_tasks / cron_overrides / ...
   + events（只读视图，映射 memories）
   + events_old_YYYYMMDD（迁移前旧表，存档，不读）
```

**双写与读回退**：

- `save_state_json`：写 `memories` 完整 JSON + `bot_states` 三列。
- `save_relation` / `save_friction`：写 `memories` JSON + `relations` / `friction_states`。
- `save_reading`：只写 `reading_progress`，按书一行。
- `save_habit`：写 `memories` JSON；`habits` 表另有计数路径。
- 读路径优先新表/`memories`，空则回退 `events` 视图；`events` 视图只读。
- `!backup run` 生成 `backups/nao-YYYY-MM.db`（SQLite）或 `.sql.gz`（MySQL），保留 6 份。

### 4.2 出站（v17.2，未变）

```
 chat.send.send_short_reply ─┐
 chat.transport              ├→ egress.outbound ──→ ws.send
 cmd.ops（运维命令）          │       │
 executors.schedule（合并）   ┘       ├ 全局锁（防帧交错）
                                     ├ 断线入队
                                     └ echo 等待（撤回/取消息）
```

---

## 5. 已知架构债（v18.20）

1. **`events` 兼容视图是过渡态**  
   写路径已切 `memories`，但 `repo_memory`、`store_v2`、`diary/store` 仍有 `FROM events` 读查询。
   视图不能删；彻底移除需要把读路径全部改成 `FROM memories` 并删视图。

2. **启动时仍会改表**  
   `app.bootstrap._ensure_tables()` 和 `_ensure_cron_schema()` 在启动时建表/补列；这与
   “迁移只走 `scripts/migrate.py`”的三步流程冲突。迁移入口目前有 `migrate.py`、`setup.py`、
   `migrate_v18.py` 三个，虽然都幂等，但职责没有单一化。

3. **持久层 9 模块环仍在**  
   `core.settings ↔ db ↔ infra.conn ↔ repo_* ↔ store_v2 ↔ log`。`log → db` 是根因；
   数据库不可用时日志也不能落库。

4. **模块级 5 个环**  
   `ai.client ↔ ai.prompt/tools ↔ life.agenda/pending ↔ schedule/runner ↔ diary/personality`
   （11 模块）、持久层 9 模块、`server` 3 模块、`memory.context/retrieval`、`chat.batcher/handler`。
   包级仍是 0 环。

5. **三套缓存各自为政**  
   `chat.cache`（200 条环形消息）、`infra.cache`（TTL）、`diary.cache`，失效策略不统一；
   `cron.list_tasks` 3 秒缓存依赖写操作手动 invalidate。

6. **调度钩子生命周期**  
   预生成 `call_at` 未登记；`items.watchdog` 每分钟整批重挂；长轮询/重排时需要收敛。

7. **巨石函数**  
   24 个函数超过 60 行，4 个超过 100 行：`get_character_reply`(141)、
   `parse_message_content`(139)、`_reply_and_send`(133)、`generate_diary`(109)。

详见 **[ARCH-REVIEW.md](ARCH-REVIEW.md)** 的证据、评分与修复顺序。

---

## 6. 包职责一览（v18.20 有效行数）

> 数据来自 `.tmp/arch_deep.py`：AST 有效行，不含空行/注释；154 个文件，13,859 行，885 个函数。

| 包 | 行数 | 文件 | 一句话 |
|---|---:|---:|---|
| `life` | 2718 | 20 | 生活状态、关系、事实、读书、日程、回忆 |
| `infra` | 2243 | 18 | 连接池、仓库、schema、缓存、备份、日志落库 |
| `chat` | 1339 | 11 | 收消息、解析、分条、合并、发送、引用缓存 |
| `cmd` | 1172 | 12 | 39 个命令（含 `!cron` / `!hooks` / `!backup`） |
| `ai` | 1043 | 10 | 模型调用、解析、人设、工具、视觉 |
| `schedule` | 941 | 6 | cron 表、时间解析、场景、日程/待办钩子 |
| `core` | 761 | 13 | 状态、配置、锁、指标、版本、时钟、lifeport |
| `executors` | 741 | 7 | ticker / idle / proactive / schedule / cron / diary |
| `scheduler` | 361 | 4 | 队列 / 策略 / worker / 入口 |
| `server` | 349 | 6 | HTTP API |
| `diary` | 324 | 5 | 日记生成 / 存储 / 查看 |
| `memory` | 298 | 7 | 上下文、BM25、预算、时间线 |
| `image` | 248 | 4 | 抓图、存档、标签 |
| `egress` | 229 | 2 | 唯一出站口 + 合并 |
| `speech` | 228 | 4 | TTS / ASR / 声纹 |
| `app` | 204 | 3 | 启动装配、主循环 |
| 其余 | 660 | 35 | log / ports / events / utils / clip / heartbeat / 兼容层 |

---

## 7. 五条硬约束

| 约束 | 位置 | 违反后果 |
|---|---|---|
| **唯一出站口** | `egress.outbound` | 并发发送时 JSON 帧交错 |
| **阻塞调用走 `run_blocking`** | `infra.blocking` | 线程池被慢请求占满 |
| **P0 聊天不排队** | `scheduler` 快车道 | 读书/抓取时回消息变慢 |
| **时间任务用 `call_at`** | `schedule.cron` / `items` / executors | 整点/半点扎堆、延迟不可控 |
| **迁移只走 `scripts/migrate.py`**（目标） | `scripts/migrate.py` | 启动自愈与迁移脚本各改一半，结构漂移 |

前三条有测试守卫（`test_egress_guard.py`、`test_no_raw_thread.py`、调度测试）；
第四条 v18.7 已落地；第五条目前仍有启动自愈，属于待收敛项。

---

## 8. 复现本图的数据来源

```bash
# 规模 / 大文件 / 函数长度 / 依赖热点
python .tmp/arch_audit.py

# 包规模 / 未覆盖模块 / 同名函数
python .tmp/arch_deep.py

# 精确环（按文件路径解析相对导入，含函数内导入）
python .tmp/arch_cycles2.py
```

当前基线：154 个文件、13,859 有效行、885 个函数、24 个函数 >60 行、
261 个函数无 docstring、模块级 5 环、包级 0 环。

