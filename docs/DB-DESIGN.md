# 数据库设计（纯粹版）

> 目标：**一表一职责**。配置是配置、数据是数据、日志是日志。
> 现状把 8 种语义塞进 `events` 一张表（用 `kind` 区分），查询要带过滤、字段没约束、清理时互相牵连。

## 一、现状问题

| 问题 | 表现 |
|---|---|
| `events` 一表多义 | `kind` ∈ {event, life, photo, state, friction, reading, habit, rel} |
| 字段靠 JSON 顶着 | `event_summary` 里塞状态、进度、口癖 |
| 查不了 | 「今天谁的任务」要全表扫 + Python 过滤 |
| 无约束 | 写错 kind 不报错，读的时候才发现没数据 |
| 清理困难 | 删「配置类」数据会误伤「记忆类」 |

## 二、设计原则

| 原则 | 说明 |
|---|---|
| **一表一职责** | 状态、配置、记忆、日志不混表 |
| **配置与数据分离** | 可编辑的（cron/settings）与积累的（memories/diaries）分开 |
| **结构化优先** | 参与查询的字段必须是列，不是 JSON |
| **按 target 隔离** | 每人一份，`target_id` 是主查询维度 |
| **时间统一 UTC** | 服务器 TZ=UTC，存 UTC，展示转 CST |
| **软删除可追溯** | 需要保留历史的加 `deleted_at`，不物理删 |

## 三、表清单（按域）

### 3.1 身份与关系

```sql
CREATE TABLE targets (
    target_id   VARCHAR(64) PRIMARY KEY,      -- QQ号 / 群号 / 未来的微信id
    kind        ENUM('private','group') NOT NULL,
    display_name VARCHAR(64) NULL,
    first_seen  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen   DATETIME NULL,
    KEY idx_kind (kind)
);

CREATE TABLE relations (
    target_id   VARCHAR(64) PRIMARY KEY,
    affinity    DECIMAL(4,3) NOT NULL DEFAULT 0.600,   -- 0.000~1.000
    since       DATE NULL,                              -- 认识那天
    tier        VARCHAR(16) NULL,                       -- 冗余：陌生/认识/熟/亲近
    daily_gain  DECIMAL(4,3) NOT NULL DEFAULT 0,        -- 当日已涨（0.05 上限）
    gain_day    DATE NULL,
    updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### 3.2 记忆

```sql
CREATE TABLE memories (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    target_id   VARCHAR(64) NOT NULL,
    kind        ENUM('event','life','photo','diary_seed') NOT NULL DEFAULT 'event',
    summary     VARCHAR(500) NOT NULL,
    tags        VARCHAR(200) NULL,                 -- 逗号分隔
    importance  TINYINT NOT NULL DEFAULT 3,        -- 1~5
    source      ENUM('chat','life','image','manual') NOT NULL DEFAULT 'chat',
    dedupe_key  VARCHAR(128) NULL,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen   DATETIME NULL,
    deleted_at  DATETIME NULL,
    UNIQUE KEY uk_dedupe (target_id, dedupe_key),
    KEY idx_target_time (target_id, created_at),
    KEY idx_kind (kind)
);

CREATE TABLE keywords (
    target_id VARCHAR(64) NOT NULL,
    keyword   VARCHAR(32) NOT NULL,
    weight    DECIMAL(6,3) NOT NULL DEFAULT 1,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (target_id, keyword)
);

CREATE TABLE digests (
    target_id VARCHAR(64) NOT NULL,
    day       DATE NOT NULL,
    content   TEXT NOT NULL,          -- 浓缩后的几行（原 lines，MySQL 保留字）
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (target_id, day)
);
```

### 3.3 她自己的状态

```sql
CREATE TABLE bot_states (
    target_id  VARCHAR(64) PRIMARY KEY,
    mood       DECIMAL(4,3) NOT NULL DEFAULT 0.100,
    energy     DECIMAL(4,3) NOT NULL DEFAULT 0.700,
    lonely     DECIMAL(4,3) NOT NULL DEFAULT 0.150,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE friction_states (
    target_id    VARCHAR(64) PRIMARY KEY,
    expect_ts    DATETIME NULL,
    expect_text  VARCHAR(60) NULL,
    disappoint   TINYINT NOT NULL DEFAULT 0,
    cold_ts      DATETIME NULL,
    last_grudge  DATETIME NULL,
    updated_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE habits (
    target_id  VARCHAR(64) NOT NULL,
    phrase     VARCHAR(16) NOT NULL,
    count      INT NOT NULL DEFAULT 1,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (target_id, phrase)
);
```

### 3.4 阅读与定时

```sql
CREATE TABLE reading_progress (
    target_id    VARCHAR(64) NOT NULL,
    book_url     VARCHAR(255) NOT NULL,
    title        VARCHAR(120) NULL,
    intro        VARCHAR(300) NULL,
    last_no      INT NOT NULL DEFAULT 0,
    last_chapter VARCHAR(120) NULL,
    updated_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (target_id, book_url)
);

-- 见 v17.4：cron_tasks（配置，不是数据）
```

### 3.5 日记与日志

```sql
CREATE TABLE diaries (
    id         BIGINT AUTO_INCREMENT PRIMARY KEY,
    day        DATE NOT NULL,
    content    TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_day (day)
);

CREATE TABLE ai_logs (
    id         BIGINT AUTO_INCREMENT PRIMARY KEY,
    target_id  VARCHAR(64) NULL,
    model      VARCHAR(64) NULL,
    latency_ms INT NULL,
    ok         TINYINT(1) NOT NULL DEFAULT 1,
    err        VARCHAR(300) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_time (created_at)
);

CREATE TABLE ops_audit (
    id         BIGINT AUTO_INCREMENT PRIMARY KEY,
    target_id  VARCHAR(64) NULL,
    action     VARCHAR(64) NOT NULL,       -- bash / agent / write
    command    VARCHAR(300) NULL,
    result     VARCHAR(300) NULL,
    ok         TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_time (created_at)
);

CREATE TABLE settings (
    k          VARCHAR(64) PRIMARY KEY,
    v          VARCHAR(500) NOT NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

## 四、字段规范

| 项 | 规范 |
|---|---|
| 主键 | 自增 `id`；需要「一人一条」的用 `target_id` 做主键 |
| 时间 | `DATETIME`，存 UTC；展示层转 CST |
| 布尔 | `TINYINT(1)` |
| 枚举 | 用 `ENUM`，写错直接报错 |
| 金额/概率 | `DECIMAL`，别用 `FLOAT` |
| 长文本 | `TEXT`（日记、浓缩）；摘要用 `VARCHAR(500)` |
| 软删除 | 需要追溯的表加 `deleted_at` |

## 五、索引规范

| 场景 | 索引 |
|---|---|
| 按人查 | `(target_id, created_at)` |
| 按类型查 | `(kind)` |
| 去重 | `UNIQUE (target_id, dedupe_key)` |
| 时间范围 | `(created_at)` |

**不建多余索引**：写多读少的表（`ai_logs`）只保留时间索引。

## 六、从旧表迁移

`events` 现在的 `kind` → 目标表：

| 旧 kind | 新去处 |
|---|---|
| `event` / `life` / `photo` | `memories` |
| `state` | `bot_states` |
| `friction` | `friction_states` |
| `reading` | `reading_progress` |
| `habit` | `habits` |
| `rel` | `relations` |

迁移脚本 `scripts/migrate_v18.py`：

| 步骤 | 内容 |
|---|---|
| 1 | 建新表（`IF NOT EXISTS`） |
| 2 | 按 kind 拆数据到新表 |
| 3 | 校验条数一致 |
| 4 | 保留 `events` 只存记忆三类，其余行标 `deleted_at` |
| 5 | 默认 dry-run，`--apply` 执行 |
| 6 | 失败可回滚（先 dump） |

## 七、不做的事

| 不做 | 原因 |
|---|---|
| 外键约束 | 单机、低并发，约束反而增加迁移难度 |
| 分库分表 | 数据量级远没到 |
| ORM | 现有 pymysql + 手写 SQL 够用，换 ORM 是另一场重构 |
| 数据库存业务配置 | `config.local.json` 继续管连接信息，表里只存运行时设置 |

## 八、与版本的关系

| 版本 | 内容 |
|---|---|
| v17.4.0 | `cron_tasks`（第一张按新规范建的表） |
| **v17.5.0** | 数据模型重建：本文件全部表 + 迁移脚本 |

**先有 v17.4 的 `cron_tasks` 做出样板，再整体搬迁。**
