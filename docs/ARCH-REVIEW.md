# 架构审查（v17.11.0）

> 审查范围：`botv/` 全部 143 个文件、11,325 行有效代码、711 个函数；`tests/` 36 个文件 712 条、
> `checks/` 2 个文件 37 条测试。
>
> 方法：AST 解析导入图 → Tarjan 求强连通分量（真环）→ 分层倒置检测 → 规模/函数长度统计。
> 不是读后感，每条结论都能用命令复现。

---

## 0. 一句话结论

**分层是干净的（包级 0 环），但持久层和日志层缠成了一个 9 模块的结；`ai` 层反向依赖 `life` 层；
命令层和 HTTP 层几乎没有直接测试。**

| 维度 | 评分 | 说明 |
|---|---|---|
| 分层结构 | 7 / 10 | 包级无环，22 个包职责清楚 |
| 耦合度 | 5 / 10 | 9 模块环 + `ai → life` 8 处倒置 |
| 可测性 | 6 / 10 | 749 条测试，但 server 0 覆盖、cmd 偏薄 |
| 一致性 | 7 / 10 | 命名/日志/错误处理统一，5 份 JSON 存取重复 |
| **综合** | **6.3 / 10** | 能用、能改，但「改一处要理解三处」 |

---

## 1. 量化画像

### 1.1 各包规模

| 包 | 行数 | 文件 | 说明 |
|---|---|---|---|
| `life` | 2313 | 18 | 生活/关系/读书/日记状态，业务最重 |
| `infra` | 1592 | 14 | 连接池、仓库层、schema、日志、监控 |
| `chat` | 1164 | 10 | 收消息、解析、分条合并、发送 |
| `cmd` | 1003 | 12 | 36 个命令实现 |
| `ai` | 950 | 10 | 模型调用、人设、工具、视觉 |
| `executors` | 652 | 7 | 调度器上的事件处理 |
| `core` | 571 | 11 | 状态、配置、指标、锁 |
| `schedule` | 537 | 6 | 定时任务、时间解析、cron 存储 |
| `server` | 359 | 6 | HTTP API |
| `scheduler` | 351 | 4 | 队列/策略/worker/入口 |
| `diary` | 323 | 5 | 日记生成与查询 |
| 其余 11 个包 | 1013 | 25 | image/memory/egress/app/ports/events/speech… |
| **合计** | **11325** | **143** | |

### 1.2 函数长度分布

| 长度 | 数量 | 占比 |
|---|---|---|
| < 20 行 | 560 | 79% |
| 20–40 行 | 109 | 15% |
| 40–60 行 | 24 | 3% |
| 60–100 行 | 14 | 2% |
| **≥ 100 行** | **4** | **0.6%** |

**结论**：绝大多数函数足够小，只有 4 个巨石函数需要处理（见 §3）。

### 1.3 依赖热点（被依赖次数）

| 模块 | 被依赖 | 评价 |
|---|---|---|
| `botv.log` | 72 | 合理，但要小心它依赖 db |
| `botv.core` | 44 | 合理（状态/配置） |
| `botv.config` | 40 | 合理 |
| `botv.infra.repo_memory` | 21 | **偏高**：471 行 29 函数 49 条 SQL，职责过载 |
| `botv.infra.conn` | 17 | 合理 |
| `botv.ai.client` | 12 | 合理 |
| `botv.chat.send` | 12 | 合理（出站门面） |

---

## 2. 依赖结构

### 2.1 包级：0 个环 ✅

22 个包之间没有任何循环依赖，`core/infra/ports` 在底、`app/server` 在顶，这个骨架是对的。

### 2.2 模块级：6 个环（需要修）

用 Tarjan 求强连通分量，模块粒度真环 6 个：

| # | 环 | 规模 | 成因 | 危害 |
|---|---|---|---|---|
| 1 | `core.settings ↔ db ↔ infra.conn ↔ repo_ai/key/log/memory ↔ store_v2 ↔ log` | **9 模块** | `log → db`（写日志入库）、`db → repo_*`（门面转发）、`repo_* → conn`、`conn → settings`（读配置）、`settings → log` | **最严重**：导入顺序敏感、日志强依赖数据库、`settings` 无法独立使用 |
| 2 | `server ↔ http_api ↔ routes_meta` | 3 | 包 `__init__` 反向 import 子模块 | 入口副作用，测试要连整个 server |
| 3 | `diary ↔ generate ↔ view` | 3 | 同上 | 同上 |
| 4 | `schedule ↔ planner ↔ runner` | 3 | 同上 | 同上 |
| 5 | `memory.context ↔ memory.retrieval` | 2 | context 调 retrieval 召回，retrieval 读 context 的预算 | 预算逻辑散在两处 |
| 6 | `chat.batcher ↔ chat.handler` | 2 | batcher 在函数内 import `handler._reply_and_send` | 合并器与主流程互锁 |

**环 2–4 是同一个毛病**：包 `__init__.py` 里 `from .sub import ...`，而子模块又反过来
`from . import ...`。修法统一——`__init__` 只做「再导出函数」，子模块之间直接 `from .sibling import`。

### 2.3 分层倒置：53 处

按「低层不该 import 高层」判定：

| 次数 | 方向 | 判断 |
|---|---|---|
| 8 | `ai → life`（`client.py:24-31`、`tools.py:69`） | ❌ **该修**：ai 层被生活状态绑架 |
| 3 | `chat → utils` | ✅ 可接受（utils 是叶子工具） |
| 3 | `cmd → db`（`admin.py:10`、`memory_cmd.py:7`、`query.py:7`） | ❌ 该修：命令层直接摸数据库 |
| 2 | `chat → egress` | ✅ 可接受（send 是出站门面） |
| 2 | `image → utils` | ✅ 可接受 |
| 1 | `log → db` | ❌ 该修：日志不该依赖库 |
| 其余 | `ai → personality`、`app → clip` 等 | ✅ 兼容层，可接受 |

**真正要处理的只有 12 处**（`ai→life` 8 + `cmd→db` 3 + `log→db` 1），其余是合理的工具依赖。

---

## 3. 七个具体问题

### P0-1 持久层九模块结（`log → db → repo → conn → settings → log`）

**证据**

```
botv/log.py:9          from .db import write_log_to_db     （函数内，延迟导入）
botv/log.py:54         from .db import get_cursor
botv/db.py:1-12        门面：从 infra.conn / repo_* 再导出
botv/infra/conn.py     从 core.settings 读 db_config
botv/core/settings.py  从 log 取日志函数
```

**影响**

- 导入任何一层都可能触发整个 DB 栈；离线跑单元测试必须先打桩 `pymysql`
- 日志要写库，**数据库挂了日志也没了**（排障时最需要日志）
- `db.py` 这层门面没有增加价值，只是把环放大

**修法（三步，可独立上线）**

1. `infra/conn.py` 不再 import `core.settings`：`connect(config)` 由调用方传参，
   配置在 `app/bootstrap.py` 里读一次注入
2. `log.py` 改成「写文件 + 异步刷库」：库不可用时只写文件，**永不因 DB 失败丢日志**
3. 删除 `botv/db.py` 门面，`repo_*`/业务代码直接用 `infra.repo_*`

**验收**：`python -c "import botv.log"` 不触发 DB 连接；SCC 中 9 模块环消失。

---

### P0-2 `ai/client.py` 顶部 import 8 个 life 模块

**证据**（`botv/ai/client.py:24-31`）

```python
from ..life.state import current as life_current, describe as describe_state, touch_talk
from ..life.events import ensure_daily_life
from ..life.relation import describe as relation_desc, bump as relation_bump, addressing
from ..life.habit import phrases_for, describe as habit_line
from ..life.milestone import milestone_text
from ..life import friction as life_friction
from ..life import digest as life_digest
from ..life import reading as life_reading
```

**影响**

- `ai` 层无法脱离 `life` 单独测试（每条模型测试都要造一整套生活状态）
- 启动时 `ai.client` 一导入，18 个 life 模块跟着全加载
- 新人理解「模型调用」要先理解「她的生活系统」

**修法**

引入一个「提示词上下文」结构，由**调用方**组装后传入：

```python
# ai/prompt_context.py
@dataclass
class PromptContext:
    state_line: str = ""
    relation_line: str = ""
    habit_line: str = ""
    friction_line: str = ""
    reading_line: str = ""
    milestone_line: str = ""
```

`get_character_reply(prompt, tid, ctx=...)`；`ctx` 由 `chat/handler.py`（本来就懂 life）组装。
`ai` 层退回「纯模型 + 纯解析」。

**验收**：`grep -r "life" botv/ai/*.py` 只剩 0 处顶层 import；`ai` 测试可在无 life 下跑。

---

### P0-3 命令层与日志层直接写 SQL

**证据**（SQL 字符串分布，共 104 处 / 21 文件）

| 文件 | SQL 处数 | 是否该有 |
|---|---|---|
| `infra/repo_memory.py` | 49 | ✅ 仓库层 |
| `cmd/query.py` | 6 | ❌ |
| `cmd/memory_cmd.py` | 2 | ❌ |
| `diary/store.py` | 6 | ⚠️ 应有自己的 repo |
| `image/store.py` | 6 | ⚠️ 同上 |
| `schedule/cron.py` | 6 | ✅ 独立存储 |
| `server/routes_meta.py` | 6 | ❌ |
| `infra/store_v2.py` | 6 | ✅ 双读层 |
| `log.py` | 1 | ❌ |

**影响**：v17.10 刚加了 SQLite 后端，靠 DDL 方言适配兜住；再换一次后端（PG）这些散落 SQL 就是债。

**修法**：`cmd/*` 里的查询全部下沉到 `infra/repo_query.py`；`routes_meta` 同理。
**验收**：`grep -r "SELECT " botv/cmd botv/server` 为 0。

---

### P1-4 四个巨石函数

| 函数 | 行数 | 位置 | 拆分建议 |
|---|---|---|---|
| `_reply_and_send` | 131 | `chat/handler.py:173` | 拆成「解析回复 / 发文字 / 发图 / 记账」四段 |
| `get_character_reply` | 122 | `ai/client.py:219` | 拆成「组装消息 / 调模型 / 兜底重试」 |
| `parse_message_content` | 115 | `chat/inbound.py:46` | 按消息类型分派到 `_parse_text/_parse_image/...` |
| `generate_diary` | 109 | `diary/generate.py:41` | 拆成「取数据 / 生成 / 落库」 |

**判断依据**：全项目 79% 的函数在 20 行以内，这 4 个是明显异常值。

---

### P1-5 五份重复的 JSON 存取

`life/cookies.py`、`friction.py`、`habit.py`、`reading.py`、`state.py` 各自实现了一套
`load()/save()`：路径拼接、读文件、解析失败回默认值、写临时文件再替换——五份几乎一样。

**修法**：抽 `core/jsonstore.py`

```python
def load(path, default): ...
def save(path, data): ...      # 原子写：tmp + os.replace
```

**收益**：约 −80 行重复；原子写只实现一次（现在是有的写 tmp 有的直接覆盖）。

---

### P1-6 包 `__init__` 反向 import（环 2–4）

`diary/__init__.py`、`server/__init__.py`、`schedule/__init__.py` 都 `from .sub import *`，
子模块又 `from . import sibling`，形成 3 个三元环。

**修法**：`__init__` 只保留「对外 API 再导出」，子模块之间一律 `from .sibling import name`。
**验收**：SCC 只剩 0 个。

---

### P2-7 测试覆盖的结构性缺口

| 包 | 测试引用次数 | 评价 |
|---|---|---|
| `life` | 136 | ✅ |
| `chat` | 116 | ✅ |
| `ai` | 91 | ✅ |
| `infra` | 89 | ✅ |
| `core` | 66 | ✅ |
| `cmd` | 39 | ⚠️ 多为间接（`handle_command`） |
| `scheduler` | 32 | ✅ |
| `schedule` | 23 | ⚠️ |
| `executors` | 15 | ⚠️ 7 个执行器只有 15 次引用 |
| **`server`** | **0** | ❌ HTTP API 完全没测 |
| `diary` | 3 | ❌ |
| `egress` | 4 | ⚠️ 有 `test_outbound.py`，但门面覆盖薄 |

**优先补**：`server/routes_meta.py`（暴露配置/状态的接口，最该防泄漏）、`diary`（生成失败要能降级）。

---

## 4. 不建议改的地方

审查不等于「都该拆」。以下保持现状：

| 项 | 理由 |
|---|---|
| 单文件 shim（`api.py`/`handler.py`/`config.py`/`send.py`） | 外部脚本和旧测试靠它，删了会断 |
| 16 个同名 `describe()` | 各自模块的「一句话摘要」，不是重复实现 |
| `life` 包 2313 行 18 文件 | 业务本身就有这么大，再拆会碎成「一个文件一个状态」 |
| `core` 44 次被依赖 | 状态/配置天然是共享的，不算耦合 |
| `log` 72 次被依赖 | 日志本来就该到处可用 |

---

## 5. 修复顺序与版本映射

| 顺序 | 内容 | 建议版本 | 风险 |
|---|---|---|---|
| 1 | 持久层解结（P0-1） | v17.12 | 中：动连接与日志，要回归全量测试 |
| 2 | `ai` 剥离 `life`（P0-2） | v17.13 | 中：动提示词组装，行为要对比 |
| 3 | 命令层去 SQL + `server` 冒烟（P0-3/P2-7） | v17.14 | 低 |
| 4 | 四个巨石函数拆分（P1-4） | v18 前 | 低（有测试兜底） |
| 5 | 五份 JSON 存取合并（P1-5） | 随手 | 低 |
| 6 | 包 `__init__` 去反向 import（P1-6） | 随手 | 低 |

**为什么先修持久层**：它是唯一一个「会让排障变难」的问题——数据库出问题时日志也没了。

---

## 6. 验收指标

修完之后应达到：

| 指标 | 现在 | 目标 |
|---|---|---|
| 模块级环 | 6 | **0** |
| 分层倒置（真问题） | 12 | **0** |
| ≥100 行函数 | 4 | **0** |
| `cmd`/`server` 里的 SQL | 14 处 | **0** |
| 重复 JSON 存取 | 5 份 | **1 份** |
| `server` 测试引用 | 0 | **≥ 10** |
| 全量测试 | 749 | **不减** |

---

## 附：复现本报告的命令

```bash
# 规模 / 大文件 / 依赖热点
python .tmp/arch_audit.py

# 真环（Tarjan）/ 各包规模 / 未覆盖模块
python .tmp/arch_deep.py

# 精确环（按文件路径解析相对导入）
python .tmp/arch_cycles2.py
```
