# 架构审查（v18.20.0）

> 审查范围：`botv/` 154 个文件、13,859 行有效代码（AST 有效行，不含空行/注释）、885 个函数；
> `tests/` + `checks/` 当前 **932 条测试**（功能 895 + 环境/迁移 37，最后验证：全绿）。
>
> 方法：AST 解析导入图 → Tarjan 求强连通分量 → 分层倒置检测 → 规模/函数长度统计。
> 结论尽量给证据；度量命令见 §7。

---

## 0. 一句话结论

**分层骨架仍然成立（包级 0 环），但 v18 把“时间调度”和“记忆迁移”做成了两套并存的结构：
启动时还在改表，`events` 以只读视图继续被读，持久层 9 模块环没解开。
功能能跑，架构上已经从“干净分层”滑到“能改但要多想一步”。**

| 维度 | 评分 | 说明 |
|---|---|---|
| 分层结构 | 7 / 10 | 包级 0 环；模块级 5 环 |
| 耦合度 | 4.5 / 10 | 9 模块持久层环 + 11 模块 ai/生活环 |
| 可测性 | 6 / 10 | 932 条测试，但 43 个模块从未被测试导入 |
| 一致性 | 6.5 / 10 | 三套缓存、三套迁移入口、双写/视图并存 |
| **综合** | **6.2 / 10** | 可维护性尚可，但边界在变模糊 |

---

## 1. 量化画像

### 1.1 各包规模

| 包 | 有效行 | 文件 | 说明 |
|---|---:|---:|---|
| `life` | 2718 | 20 | 生活/关系/事实/读书/日程/回忆，业务最重 |
| `infra` | 2243 | 18 | 连接池、仓库、schema、缓存、备份、日志 |
| `chat` | 1339 | 11 | 收消息、解析、分条、引用缓存、发送 |
| `cmd` | 1172 | 12 | 39 个命令 |
| `ai` | 1043 | 10 | 模型、解析、人设、工具、视觉 |
| `schedule` | 941 | 6 | cron / 时间解析 / 场景 / items 钩子 |
| `core` | 761 | 13 | 状态、配置、锁、指标、版本、时钟 |
| `executors` | 741 | 7 | ticker / idle / proactive / schedule / cron |
| `scheduler` | 361 | 4 | 队列 / 策略 / worker |
| `server` | 349 | 6 | HTTP API |
| `diary` | 324 | 5 | 日记生成 / 存储 / 查看 |
| `memory` | 298 | 7 | 上下文、检索、预算、时间线 |
| 其余 | 1,569 | 35 | image/egress/speech/app/log/ports/events… |
| **合计** | **13,859** | **154** | |

### 1.2 函数长度分布

| 长度 | 数量 | 占比 |
|---|---:|---:|
| < 20 行 | 688 | 77.7% |
| 20–40 行 | 145 | 16.4% |
| 40–60 行 | 28 | 3.2% |
| 60–100 行 | 20 | 2.3% |
| **≥ 100 行** | **4** | **0.5%** |

**结论**：绝大多数函数足够小；问题集中在 4 个巨石函数，不是全局性函数膨胀。
无 docstring：261 / 885（29%）。

### 1.3 依赖热点（被依赖次数）

| 模块 | 被依赖 | 评价 |
|---|---:|---|
| `botv.log` | 79 | 偏高，且仍依赖 db（环的根因之一） |
| `botv.core` | 55 | 合理（状态/配置/时钟） |
| `botv.config` | 41 | 合理 |
| `botv.infra.repo_memory` | 24 | **偏高**：465 行、30 函数，职责过载 |
| `botv.infra.conn` | 23 | 合理，但 `conn → settings → log` 形成环 |
| `botv.schedule` | 14 | 合理 |
| `botv.ai.client` | 12 | 合理 |
| `botv.infra.blocking` | 12 | 合理（统一阻塞入口） |

---

## 2. 依赖结构

### 2.1 包级：0 个环 ✅

`arch_deep.py` 的包级检测：22 个包之间无环。`core/infra/ports` 在底、`app/server` 在顶，
骨架仍然对。

### 2.2 模块级：5 个精确环（`arch_cycles2.py`）

| # | 环 | 规模 | 成因 | 危害 |
|---|---|---|---:|---|
| 1 | `ai.client ↔ ai.prompt/tools ↔ life.agenda/pending ↔ schedule/runner ↔ diary/personality` | 11 | `ai.tools → life.agenda`、`diary.generate → ai.client`、`schedule.runner → diary/ai` | **最严重**：模型、日记、日程、生活互相拖启动 |
| 2 | `core.settings ↔ db ↔ infra.conn ↔ repo_* ↔ store_v2 ↔ log` | 9 | `log → db`（日志入库）、`db → repo_*`（门面）、`conn → settings`（读配置） | 持久层导入顺序敏感；DB 挂了日志也没了 |
| 3 | `server ↔ http_api ↔ routes_meta` | 3 | 包 `__init__` 反向 import 子模块 | 测试 server 要连整个包 |
| 4 | `memory.context ↔ memory.retrieval` | 2 | context 调 retrieval，retrieval 读 context 预算 | 预算逻辑散两处 |
| 5 | `chat.batcher ↔ chat.handler` | 2 | batcher 函数内 import `handler._reply_and_send` | 合并器与主流程互锁 |

> `arch_deep.py` 显示 3 个环，是因为它只统计模块顶层 import；
> `arch_cycles2.py` 按文件路径解析，包含函数内延迟导入，给出精确的 5 个。
> 两者不矛盾：**顶层 3 个，精确 5 个**。

### 2.3 分层倒置：48 处

`arch_audit.py` 的启发式检测：

| 次数 | 方向 | 判断 |
|---:|---|---|
| 5 | `core → life` | ⚠ 需看：`lifeport.setup_life_bridge` 在 core 里反向 import life |
| 3 | `ai → life` | ❌ 该修：`ai.tools → life.agenda` 等，lifeport 只覆盖了一部分 |
| 3 | `chat → utils` | ✅ 可接受（叶子工具） |
| 2 | `chat → egress` | ✅ 可接受（send 是门面） |
| 2 | `cmd → send` | ✅ 可接受（命令回复） |
| 2 | `cmd → conn` | ⚠ 需看：SQL 已移 repo，但层依赖仍在 |
| 2 | `image → utils` | ✅ |
| 1 | `log → db` | ❌ 该修：日志不应强依赖数据库 |
| 其余 | `app → clip/sticker/heartbeat` | ✅ 兼容层 |

真正要先处理的：`log → db`、`ai → life`、`core → life`、`cmd → conn`。

---

## 3. 七个具体问题

### P0-1 迁移入口不唯一，启动仍在改表

**证据**

```text
run.py
  └→ botv.main → app.bootstrap
       ├→ _ensure_tables()        # 建 acg_images / diaries，补 token 列
       └→ _ensure_cron_schema()   # 建 cron_overrides，补 rule/timing
scripts/migrate.py                 # 新的统一入口
scripts/setup.py                   # 仍会建表/迁移/补 cron 列/导场景
scripts/migrate_v18.py             # 只做 v18.17
```

**后果**

- 用户按“三步走”执行 `migrate.py --apply` 后，启动时还会再改一次表；迁移不是单一事实源。
- 两套逻辑对“什么算迁移完成”的判断不同：`migrate.py` 看列/表，`bootstrap` 直接 ALTER。
- 预检严格了，但 `run.py` 仍会自动装依赖、建表；流程上没有真正锁死。

**修法（v19.0）**

1. `bootstrap` 只读 schema，不再 `ALTER/CREATE`；缺结构直接报错并提示 `migrate.py --apply`。
2. `migrate.py` 成为唯一入口；`setup.py` 只保留“装依赖/首次配置”，不再建表。
3. 加 `schema_version` / `bot_meta.schema_version`，`preflight` 校验版本而不是逐列猜。

### P0-2 `events` 兼容视图 + 双源写入

**证据**

```text
schema.VIEWS["events"]  → SELECT ... FROM memories（只读）
migrate_v18             → events 基表改名 events_old_YYYYMMDD
repo_memory             → 仍有 FROM events 读查询（load_*）
store_v2                → 回退 events 视图
diary/store             → FROM events
save_state_json         → memories JSON + bot_states 三列
save_relation           → memories JSON + relations
save_habit              → memories JSON；habits 表另有路径
```

**后果**

- 写路径已经切 memories，读路径还有视图；结构上“旧表没了”，代码里“旧名字还在”。
- 状态/关系/摩擦是双写：一张写失败就出现两个版本；目前只有失败计数，没有对账。
- `events_old_*` 是回滚资产，不是运行数据；容易被误认为还在用。

**修法（v19.0–v19.1）**

1. 把 `repo_memory` / `store_v2` / `diary` 的 `FROM events` 全部改 `FROM memories`（或专用表）。
2. 删除 `events` 视图；`events_old_*` 保留 30 天后归档。
3. 双写改成“单写 + 事务/补偿”，或明确只保留新表为唯一源。

### P0-3 持久层 9 模块环仍在

`core.settings → log → db → repo_* → conn → settings` 没有解除。
v17.14 把 `conn` 配置改成注入，但 `log._db_writer` 仍在函数内 `from .db import ...`，
Tarjan 仍能看到环。

**修法（v19.0）**

- `log` 只写内存/文件，DB 落库由独立 `log_sink` 线程消费；导入时零 DB 依赖。
- `settings` 不 import `log`；配置错误通过返回值/异常上抛。
- `db.py` 门面删除或只做显式注册，不做模块级转发。

### P0-4 ai / diary / life / schedule 11 模块环

`lifeport` 解决了 `ai.client` 顶部 import 8 个 life 模块的问题，但：

- `ai.tools` 仍 import `life.agenda`
- `diary.generate` 仍 import `ai.client`
- `schedule.runner` 仍 import `diary`、`ai.client`

**后果**：AI 层仍不能独立测试；改日程/日记会牵动模型调用。

**修法（v19.1）**

- 把 `ai.tools` 的 agenda 操作改成 `core.lifeport` 的 `agenda_add` / `agenda_list`。
- diary 生成通过 `ai.generate` 端口，不直接 import `ai.client`。
- `schedule.runner` 只依赖 `executors` 注册表，不直接 import 业务模块。

### P1-5 调度钩子生命周期

**证据**

```text
cron._make_handle
  ├→ loop.call_at(nxt, _fire)          # 登记 handles
  └→ loop.call_at(nxt-30s, _fire_prepare)  # 没有登记！
items.watchdog() → schedule_all()       # 每 60 秒整批重挂
cron.watchdog()  → 重排丢失任务 + 清过期 override
```

**后果**

- 删除/重排任务时，预生成钩子不会被取消；最坏情况是多一次模型调用（不发送）。
- `items.watchdog` 每分钟重挂全部日程/待办；数量大时是无谓开销，且会重置 call_at 的微小时序。
- 看门狗“只重排不补发”是正确策略，但没有钩子代数/版本，难以判断是否真的丢失。

**修法（v19.2）**

- 所有 `call_at` 句柄进统一注册表（含 prepare / fire / item），带 generation。
- 看门狗只补“应该存在但没有”的钩子，不整批重挂。
- 记录 `last_fire` / `next_ts`，用对账而不是猜测。

### P1-6 三套缓存 + 失效策略不统一

| 缓存 | 内容 | 失效 |
|---|---|---|
| `chat.cache` | 最近 200 条消息 | 环形淘汰 |
| `infra.cache` | counts 5s / cron list 3s | TTL + 手动 `invalidate` |
| `diary.cache` | 日记摘要 | 各自实现 |

`cron.list_tasks` 3 秒缓存的正确性依赖 `add/remove/set_enabled/set_next` 都记得 invalidate；
新增写路径很容易漏。`repo_query.counts` 5 秒缓存对写操作不失效，只靠 TTL。

**修法（v19.2）**

- 统一 `cache` 服务：命名空间、TTL、依赖失效；写路径通过仓储层统一 invalidate。
- 聊天消息缓存保持独立（语义不同），但要标明“非 TTL 缓存”。

### P2-7 测试覆盖的结构性缺口

`arch_deep.py` 列出 **43 个模块从未在测试里被 import**，包括：

- `app.bootstrap`（启动装配）
- `cmd.admin/basic/cron_cmd/media/memory_cmd/ops/query`
- `chat.cache`
- `core.clock/version/single_instance`
- `diary.generate/store`

932 条测试里，大量是行为/工具测试；启动、命令、缓存、迁移入口仍偏薄。
新加的 `test_migrate_events`、`test_cache`、`test_backup`、`test_v1820` 补了一部分，
但 `migrate.py`、`preflight`、`bootstrap` 仍没有直接测试。

**修法（v19.2–v19.3）**

- 给 `migrate.py` 加 SQLite 临时库集成测试（建旧表→迁移→断言列/视图/数据）。
- 给 `preflight` 加 fake cursor 测试：缺列/缺表必须返回非 0。
- 给 `bootstrap` 加“只读 schema”测试，防止它再偷偷 ALTER。

### P2-8 巨石函数

| 函数 | 行数 |
|---|---:|
| `ai/client.py:get_character_reply` | 141 |
| `chat/inbound.py:parse_message_content` | 139 |
| `chat/handler.py:_reply_and_send` | 133 |
| `diary/generate.py:generate_diary` | 109 |
| `chat/handler.py:_handle_message` | 90 |
| `schedule/cron.py:compute_next` | 89 |
| `executors/ticker.py:handle_minute_tick` | 86 |

这些不是“必须马上拆”，但 `get_character_reply` 和 `parse_message_content` 已经影响可读性；
拆的时候按“纯函数 → 编排”切，不要只按行数切。

---

## 4. 不建议改的地方

- **出站唯一口 + 全局锁**：并发帧交错是真实踩过的坑，不要为了“少一层”绕开。
- **三档调度队列**：P0 聊天不排队是硬约束。
- **双后端（MySQL/SQLite）**：降级能力有价值；不要为了简化只留 MySQL。
- **`call_at` 到点触发**：比 `minute_tick` 扫表精确；修钩子生命周期，不要退回轮询。
- **分条上限 4**：v18.10 的产品决策，别为了“多表达”改回 10。

---

## 5. 修复顺序与版本映射

| 顺序 | 版本 | 动作 | 验收 |
|---:|---|---|---|
| 1 | v19.0 | 迁移单一入口：`bootstrap` 只读 schema；`setup.py` 不再建表；加 schema_version | 启动不改表；缺结构直接报错 |
| 2 | v19.3 | 去掉 `events` 视图读路径；`events_old` 归档 | `grep FROM events` 仅迁移脚本 |
| 3 | v19.3 | 解持久层 9 环：`log` 不依赖 db，`settings` 不依赖 log | Tarjan 持久层环消失 |
| 4 | v20.3 | 解 ai/diary/life 11 环：lifeport 补 agenda/diary 能力 | 包级仍 0 环；精确环 ≤2 |
| 5 | v20.3 | 钩子注册表 + 看门狗按差量补；不再整批重挂 | 删除任务无残留 prepare；watchdog 不重排全部 |
| 6 | v20.3 | 缓存统一失效；`cron` 写路径集中 invalidate | 连点 `!stats`/`!cron` 不脏读 |
| 7 | v20.3 | 拆 2 个 100+ 行函数；补 migrate/preflight/bootstrap 测试 | 43 个未覆盖模块降到 <20 |

---

## 6. 验收指标

| 指标 | 当前 | 目标 |
|---|---:|---:|
| 包级环 | 0 | 0 |
| 模块级精确环 | 5 | ≤1 |
| 分层倒置 | 48（含合理工具依赖） | 真实问题 ≤5 |
| 函数 >60 行 | 24 | ≤15 |
| 函数 ≥100 行 | 4 | ≤1 |
| 无 docstring 函数 | 261（29%） | ≤15% |
| 测试里未 import 的模块 | 43 | ≤20 |
| 测试总数 | 932 | ≥1000 |
| 启动时 schema 写入 | 有 | 0 |

---

## 7. 复现本报告

```bash
# 规模 / 大文件 / 函数长度 / 依赖热点 / 分层倒置
python .tmp/arch_audit.py

# 包规模 / 未覆盖模块 / 同名函数 / 顶层环
python .tmp/arch_deep.py

# 精确环（含函数内 import）
python .tmp/arch_cycles2.py
```

统计口径：`botv/` 下 AST 有效行；测试数来自 `python scripts/run_tests.py`（932 条全绿）。
