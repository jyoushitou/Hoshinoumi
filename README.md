# 友利奈绪 QQ 机器人 v18.5.0 —— 事实卡 + 元数据视图

> 世界观取自原作结局之后：能力消失，回归普通生活；**乙坂有宇已经意外去世**。
> 提到他需要克制，可以打哑谜，但不能假装他还活着。

基于 **NapCat** 收 QQ 消息，**Python** 后端，**DeepSeek** 为主模型、**豆包** 兜底，
MySQL 存记忆与日志。图片由她自己一句话打标签，正文小说用**截图 + OCR** 还原。

---

## 特性一览

| 能力 | 说明 |
|---|---|
| **可换角色** | 人设、生活模板、状态基线全在 `personas/<名字>/`，改文件就换人 |
| 说话像人 | 分条发送、按时段浮动延迟、语气受情绪影响 |
| 记得住 | 30 轮对话 + 长期记忆（BM25 + 关键词双路 RRF）+ 关系里程碑 |
| 有自己的生活 | 心情/精力/孤独随时间漂移，会写日记、会主动找你 |
| 会看图 | 多模态直接看，动图抽 24 帧拼网格 |
| 会说话 | edge-tts 语音，按心情和长度低频触发 |
| 会听 | 语音条转写（能转就转，不能就记一笔） |
| 会读小说 | 空闲时自己抓番茄章节（OCR 还原），攒够几章跟你分享 |
| 有摩擦 | 期待、失落、冷战、和好（24 小时自动恢复） |
| 能调参 | `!config` 改频率/概率，`!stats` 看今日数据，不用重启 |
| 跑得动 | 阻塞调用统一线程池（13 处），连接池复用 MySQL 连接 |
| 查版本 | `!version` 看版本号、提交、运行时长 |

**881 条测试**（功能 844 + 环境/迁移 37），静态检查零未定义名字。

---

## 开发计划

**当前：v18.5.0（uptime 与元数据视图）已完成** → 下一步：**v18.6 引用上下文（L21：引用原话 + 8 秒超时）**。

| 系列 | 主题 | 状态 | 文档 |
|---|---|---|---|
| v5 ~ v13 | 说话节奏 / 记忆 / 生活 / 感官 / 摩擦 | ✅ 已发布 | [versions/](docs/versions/) |
| v14 ~ v15 | 可换角色 / 调参与观测 | ✅ 已发布 | [v14.md](docs/versions/v14.md) |
| **v16** | **读小说（番茄 OCR + HTML 合并）** | ✅ 已发布 | [v16.md](docs/versions/v16.md) |
| v17 | 执行模型重构：阻塞池 → 事件/调度 → 出站层 → 主循环瘦身 | ✅ 已发布（v17.17） | [v17.md](docs/versions/v17.md) |
| v18 | 情感的深刻度：记忆分轻重、情绪跨天、时间与日志修复 | 🚧 进行中（v18.5 已完成 → v18.6 待开） | [v18.md](docs/versions/v18.md) |
| v19 | 后端 API：把能力做成服务（只监听本机） | 📋 已规划 | [v19.md](docs/versions/v19.md) |
| v20 | 网关：自有软件与 Web 的**唯一入口**（鉴权/限流/审计） | 📋 已规划 | [v20.md](docs/versions/v20.md) |
| v21 | DSH / Qoder / WorkBuddy 插件：她成为你所有工具的记忆层 | 📋 已规划 | [v21.md](docs/versions/v21.md) |
| v22 | 电脑 Web：聊天 + 历史 + 功能面板 | 📋 已规划 | [v22.md](docs/versions/v22.md) |
| v23 | 手机 App（Flutter）+ 推送通知 | 📋 已规划 | [v23.md](docs/versions/v23.md) |
| v24 | QQ 空间：发说说 + 只对熟人点赞/评论 | 📋 已规划 | [v24.md](docs/versions/v24.md) |
| v25 | 运维（一）bash 只读 | 📋 已规划 | [v25.md](docs/versions/v25.md) |
| v26 | 运维（二）agent | 📋 已规划 | [v26.md](docs/versions/v26.md) |
| v27 | 运维（三）有限写 | 📋 已规划 | [v27.md](docs/versions/v27.md) |
| v28 | 运维（四）可写体系 | 📋 已规划 | [v28.md](docs/versions/v28.md) |
| v29 | 视频（一）B 站 | 📋 已规划 | [v29.md](docs/versions/v29.md) |
| v30 | 视频（二）抖音 | 📋 已规划 | [v30.md](docs/versions/v30.md) |
| v31 | 微信接入（OpenClaw） | 📋 已规划 | [v31.md](docs/versions/v31.md) |
| v32 | 语音通话 | 📋 已规划 | [v32.md](docs/versions/v32.md) |
| v33 | 视频通话 | 📋 已规划 | [v33.md](docs/versions/v33.md) |
| v34 | 常驻（一）systemd / 看门狗 | 📋 已规划 | [v34.md](docs/versions/v34.md) |
| v35 | 常驻（二）LITE / ARM / 一键安装 | 📋 已规划 | [v35.md](docs/versions/v35.md) |

> **约定**：每个大版本的**最后一个次版本**用来收尾修 bug 和技术债，不堆新功能。

> v17.11 起**MySQL 连不上会自动退 SQLite**；备份/恢复见 [docs/存储后端与备份.md](docs/存储后端与备份.md)。

> v17.12 起语音带**情绪与声线**：语气随心情变，声线跟角色卡走。


- **细到每个小版本**（`x.y.z` 级）的拆解与验收点：[ROADMAP.md](docs/ROADMAP.md)
- **数据库设计**（一表一职责）：[DB-DESIGN.md](docs/DB-DESIGN.md)
- **未排期需求**（A~E 组）：[V14-后续清单.md](docs/V14-后续清单.md)
- **v6 功能总表**（74 项封版）：[V6-功能.md](docs/V6-功能.md)

> 规矩：v6–v16 范围内的问题直接改代码；**超出范围的新需求先写进清单**，不直接动代码。

---

## 目录布局

```
项目根/
├── botv/            机器人代码（分层包）
├── tests/           功能测试（分模块 + 冒烟，448 条）
├── checks/          前置环境监测 + 迁移检查（37 条，与 botv 同级）
├── scripts/         迁移 / 打包 / 发布 / 自检脚本
├── docs/            版本计划、架构图、数据库设计、发布清单
├── personas/        角色卡（可换人设）
├── release/         打包与发布产物（不进版本库）
├── config.example.json   配置模板
├── config.local.json    真实配置（不进版本库）
└── run.py           启动入口
```

`release/` 里放所有交付物：

```
release/
  nao-v17.0.0.bundle        git 包（传服务器用）
  nao-v17.0.0-src.zip        源码包（给别人）
  nao-v17.0.0-full.zip       整包（带依赖）
  nao-bot-v17.0.0.tar.gz     Docker 镜像
  old/                      历史包（保留最近 5 个，其余归档到这里）
```

一键跑测试：

```bash
python3 scripts/run_tests.py            # tests + checks
python3 scripts/run_tests.py --fast     # 只跑功能测试
```

---

## 架构

```
run.py → app.bootstrap → app.loop
                 │
  接入(WS/HTTP/定时) → 调度器 → 业务/能力层 → 基础层 → MySQL/SQLite
                 │
            唯一出站口 egress.outbound → ws.send
```

完整分层图、消息生命周期、调度器模型、已知架构债：

> **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** —— 架构图
> **[docs/ARCH-REVIEW.md](docs/ARCH-REVIEW.md)** —— 审查结论与修复顺序（综合 6.3/10）

三条硬约束：

| 约束 | 违反的后果 |
|---|---|
| 所有发送只走 `egress.outbound` | 并发时帧交错（心跳插进气泡中间） |
| 阻塞调用只走 `run_blocking` | 卡住的请求永久占线程，池慢慢空 |
| P0 聊天不排队 | 读书/抓取时回消息变慢 |

---


> **新功能一律先进 `docs/versions/` 的开发计划，再按版本迭代。**
> 已发布版本冻结，bug 记进下一个版本的「遗留问题」。

> **部署/升级只有两条命令**：python3 scripts/setup.py → python3 run.py。
> 建表、旧数据迁移、内置定时场景导入，setup 一次做完，重复跑安全。

## 快速开始

### 环境要求

- Python 3.10+
- MySQL 8（8 张表，见下文）
- NapCat（QQ 协议端，WebSocket 连到本机 3001）

### 首次配置（v16 起必做）

数据库信息和主人 QQ **不再写死在代码里**。

**方式一：配置文件（推荐）**

```bash
cp config.example.json config.local.json
vi config.local.json          # 填 master_qq 和 db.*
chmod 600 config.local.json
```

```json
{
  "master_qq": "123456789",
  "ws_port": 3001,
  "api_port": 60908,
  "db": {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "your_user",
    "password": "your_password",
    "name": "TomoriNaoBotData"
  }
}
```

**方式二：环境变量**

```bash
export NAO_MASTER_QQ=123456789
export NAO_DB_HOST=127.0.0.1
export NAO_DB_USER=your_user
export NAO_DB_PASS=your_password
export NAO_DB_NAME=TomoriNaoBotData
```

优先级：**环境变量 > config.local.json > 空默认值**。没配齐时启动会直接退出并列出缺哪几项。

### 可选依赖（读书功能要用）

```bash
# 番茄正文 OCR（必需）
sudo apt install -y tesseract-ocr tesseract-ocr-chi-sim

# 无头浏览器（抓页面 + 截图）
python3 -m pip install --user --break-system-packages playwright
python3 -m playwright install chromium
# 缺系统库时：
sudo python3 -m playwright install-deps chromium
```

不装也能跑——读书功能自动降级成「浅层在读」（只有书名和进度）。

### 启动

```bash
# 1. 数据库迁移（首次升级到 v7/v8 时必须先跑）
python3 scripts/migrate_v7.py --apply    # events 扩成记忆主表
python3 scripts/migrate_v8.py --apply    # global_keywords 按对象隔离

# 2. 部署前自检（13 项：依赖 / 静态检查 / 环境变量 / 能力 / 网络 / 数据库 ...）
python3 scripts/preflight.py

# 3. 启动
python3 run.py
```

预检逐项打勾，退出码 0 才算通过。**迁移必须先于启动**——新代码会查 `kind`、`target_id`，
列不存在直接报 `Unknown column`。

### 停止

- **推荐**：QQ 里发 `!exit`
- 前台运行：`Ctrl-C` 一次（打印「[已中断]」，不吐栈）
- 后台 screen：`screen -S bot -X quit`

### 单实例

启动时自动抢 `.botv.lock`，已有实例在跑会直接退出并打印对方 PID。
锁由操作系统维护，进程死了自动释放。

---

## 角色卡：换一个人设（重点）

人设**不在代码里**，全部放在 `personas/<名字>/` 下。改文件就能换角色，不用动一行 Python。

### 目录结构

```
personas/nao/
├── prompt.txt       主提示词（含 {now}{tone} 等占位符）
├── supplement.txt   人设补充：她是谁、口癖、关系、边界、示例
├── life.txt         生活事件模板（# weight 0.25 分组，每组一行一条）
└── state.json       状态基线 {"mood":0.1,"energy":0.7,"lonely":0.15}
```

### 四个文件各管什么

| 文件 | 作用 | 改动效果 |
|---|---|---|
| `prompt.txt` | 主提示词：世界观、性格锚点、说话规则、分条机制 | 说话风格、价值观 |
| `supplement.txt` | 补充人设：口癖、称呼、日常习惯、软肋、示例对话 | 语气细节、关系感 |
| `life.txt` | 她「今天经历了什么」的模板（109 条，带权重） | 生活内容、日常话题 |
| `state.json` | 情绪基线（心情/精力/孤独） | 默认神态、活跃度 |

### 占位符必须保留

`prompt.txt` 里的这些占位符**一个都不能删**，否则渲染会报 `KeyError`：

| 占位符 | 内容 |
|---|---|
| `{now}` | 当前时间（含时段描述） |
| `{tone}` | 语气提示（情绪 + 天气） |
| `{profile}` | 他的画像 + 口头禅 + 关系里程碑 |
| `{relation}` | 关系档位 + 称呼建议 |
| `{timeline}` | 最近事件时间线 |
| `{events}` | 检索到的记忆 |
| `{current_dialogue}` | 最近 30 轮对话 |
| `{global_keywords}` | 关键词 |
| `{available_tags}` | 图库标签（600 个） |
| `{master_qq}` | 主人 QQ |
| `{digest}` | 她自己的浓缩记录（每 10 轮压一行） |
| `{reading}` | 她最近在看的小说 |

### 三种换卡方式

| 方式 | 命令 | 生效时机 | 持久化 |
|---|---|---|---|
| **运行时切换** | `!persona <名字>` | 下一句话 | ✅ 写 `personas/.active` |
| 环境变量 | `NAO_PERSONA=<名字> python3 run.py` | 启动时 | ❌ |
| 默认 | 无 | 用 `nao` | — |

优先级：**`!persona` > `.active` > `NAO_PERSONA` > `nao`**，每层都会检查目录是否存在，不存在就往下落。

### 自制一张卡

```bash
cp -r personas/nao personas/mychar
# 改 personas/mychar 下的四个文件
```

QQ 里发：

```
!persona mychar
```

她会回「✅ 已切换到「mychar」。下一句话就生效。」

### 导出当前人设

如果人设还在代码里（从老版本升上来），跑：

```bash
python3 scripts/export_persona.py
```

会把当前硬编码的提示词、补充、生活模板、状态基线**无损导出**成 `personas/nao/` 四件套。

### 注意

- `life.txt` 每组第一行是权重：`# weight 0.25`，下面每行一条模板
- 权重总和不必等于 1，程序会归一化
- `supplement.txt` 留空也可以，不影响启动
- 卡目录名不能以 `.` 开头（会被忽略）

---

## 命令（34 个，仅主人可用）

### 基础

| 命令 | 说明 |
|---|---|
| `!ping` | 测试是否在线 |
| `!status` | 详细状态（配置 / API / 记忆 / 定时） |
| `!uptime` | 运行时长 |
| `!usage` | 最近 10 次 token 用量 |
| `!help` | 命令列表 |
| `!exit` / `!quit` | 安全退出 |

### 记忆与关系

| 命令 | 说明 |
|---|---|
| `!memory [关键词]` | 检索记忆 |
| `!memorybook` | 记忆本：认识天数 / 关系 / 口头禅 / 最近记得的事 |
| `!growth` | 成长轨迹：关系进度条、一起经历过多少件事 |
| `!profile` | 他/她的画像 |
| `!event` | 查看/管理事件 |
| `!keywords` | 关键词 |
| `!clear` | 清理 |

### 媒体

| 命令 | 说明 |
|---|---|
| `!img` | 图库管理 |
| `!sticker` | 表情包 |
| `!acg` | 在线图源 |
| `!clip` | CLIP 状态（v8 起已停用，仅展示） |
| `!voice <文本>` | 合成一条语音 |

### 日常

| 命令 | 说明 |
|---|---|
| `!diary` | 今天的日记 |
| `!diary <日期>` | 指定日期 |
| `!diary list [天数]` | 最近几天概览 |
| `!diary raw <日期>` | 原始事件记录 |
| `!todo` | 待办 |
| `!task` | 定时任务 |

### 模式与运维

| 命令 | 说明 |
|---|---|
| `!code` | 代码模式（知识正确性优先，30 分钟无消息自动退出） |
| `!code off` | 手动退出 |
| `!persona [名字]` | 查看 / 切换角色卡 |
| `!config` | 列出可调参数 |
| `!config <参数> <值>` | 改一个参数，立即生效 |
| `!stats` | 今日统计：回复 / 配图 / 语音 / 群接话率 / 配图率 |
| `!set` | 设置项 |
| `!db` | 数据库信息 |
| `!log` | 日志 |
| `!apikeys` | 密钥管理 |
| `!reload` | 重载配置 |
| `!say` / `!sayg` | 以她的口吻说话（私聊 / 群聊） |

---

## 核心机制

### 1. 记忆系统

**三层结构**

| 层 | 存法 | 上限 |
|---|---|---|
| 对话记忆 | `user_memory` | 每人/每群最近 **30 轮** |
| 长期记忆 | `events` | life 60 / event 30 / promise 30 / profile 20 |
| 画像 | `events` 里 `kind='profile'` | 每字段一行，重写即覆盖 |

**检索不用 LIKE**

```
用户消息 → 分词 → BM25 排名 + 关键词命中排名 → RRF 融合 → top 5
```

- 候选池：这个对象最近 300 条记忆
- 两路都不命中 → 退回最近 3 条
- 读库失败 → 给「无」，不影响回复

**去重**：同一句话（去标点、转小写）7 天内重复只累加 `hit_count`，不新增行。

**分层预算**

| 层 | 预算 |
|---|---|
| 画像 | 120 字 |
| 最近对话 | 700 字（30 轮，从最新往回留） |
| 检索到的记忆 | 250 字 |
| 全局关键词 | 120 字 |
| 时间线 | 200 字 |

**长会话浓缩**：超过 30 轮后，溢出缓冲攒够 10 轮就压成一行，写进 `data/digests/<对象>.md`
（最多 20 行，每行 ≤40 字）。注入 prompt 的 `{digest}`。

### 2. 对话模型

- **主模型** DeepSeek（`deepseek-flash`），**兜底**豆包，都挂了返回傲娇短句（`Fallback` 标记，**不进记忆**）
- **超时分级**：普通聊天 20 秒，长文（日记 / 代码模式）40 秒
- **并发**：不同对象各一把锁，同时在飞的请求最多 5 个

### 3. 说话方式

**分条**：她写几行就发几条，代码只兜底「超过 10 行」。

```
今天好累啊
不想动了
（缩成一团）
      ↓ 三条独立消息，间隔 1.5~3.0 秒
```

**延迟**：按时段浮动，平方压低到短端。深夜慢、白天快，整体倍率可用 `!config delay_scale` 调。

**语气**：受 mood / energy / lonely 影响，也受关系档位影响（亲近才会损你）。

### 4. 她自己的生活（v9）

状态向量 `mood / energy / lonely` 随时间指数回归 + 孤独拉低心情基线。
每天生成「生活事件」（109 条模板），写进记忆，聊天时自然提起。

### 5. 读小说（v16）

**触发**：你空闲 ≥2 小时、不在深夜（01:00~07:00）、今天没读够 20 章。

**流程**

```
挑书（热榜 / 内置书单 / 你点名）
   ↓
抓章节 HTML → 正文有私有区字符？ → 截图 + tesseract OCR
   ↓
HTML 骨架 + OCR 补字（difflib 对齐）→ 合并正文
   ↓
AI 摘要（≤100 字）→ 记进度
   ↓ 攒够 3 个点
主动说一句（3 小时冷却）
```

**为什么这么做**：番茄把多数字符替换成私有区码点，靠自定义字体渲染，正文 54% 是乱码。
字体比对失败（字形被扰动，命中率 0.3%），所以改用截图 OCR——渲染出来的字是对的。

**成本**：每章 8~12 秒（浏览器 + OCR + 摘要），每天最多 20 章。

**你点名**：

```
去看看十日终焉呢     → 识别出书名 → 番茄搜索 → 开始追
《十日终焉》你去看看  → 同上
去看 <番茄链接> 这本   → 直接按链接追
```

### 6. 图片与语音

- **看图**：多模态直接看，不猜标签；动图抽 24 帧拼 4×6 网格
- **配图**：AI 给关键词 → 过闸门（30% 概率 / 10 分钟冷却 / 心情差减半）→ 搜图
- **语音**：8% 概率转语音 + 20 分钟冷却，长度 4~60 字

### 7. 摩擦（v13）

```
她说「早点睡」→ 记一次期待 → 8 小时没回应 → 失望
     ↓ 累计 3 次
   冷战 ── 24 小时自动结束
     ├─ 说「对不起」→ 立刻和好
     └─ 3 句话 → 和好
```

红线写死在代码：`COLD_WAR_MAX=24h`、`GRUDGE_LIMIT=1/周`、`DISAPPOINT_MAX=3`。

### 8. 调参与观测（v15）

```
!stats                   今日统计
!config                  列出可调参数
!config image_prob 0.2   改一个，立即生效
```

| 参数 | 默认 | 含义 |
|---|---|---|
| `group_base_prob` | 0.20 | 群里没被  的接话概率 |
| `group_mention_prob` | 0.75 | 被  时的回话概率 |
| `image_prob` | 0.30 | 配图概率 |
| `image_cooldown` | 600 | 配图间隔（秒） |
| `voice_prob` | 0.08 | 语音概率 |
| `lonely_threshold` | 0.45 | 孤独到多少主动开口 |
| `proactive_cap` | 3 | 每天主动上限 |
| `delay_scale` | 1.0 | 回复延迟倍率 |

存在 `data/tunables.json`，重启也记得。

---

## 运维

### 测试

```bash
python3 scripts/run_tests.py             # 872 条（tests 835 + checks 37）
python3 scripts/check_names.py            # 静态检查：未定义名字 / 先用后赋值
```

### 自检

```bash
python3 scripts/setup.py              # 装依赖 + 建表 + 迁移 + 场景（幂等）
python3 scripts/preflight.py         # 13 项自检
```

13 项：依赖 / 静态检查 / 环境变量 / 能力 / 网络 / 数据库表结构 / 目录 / 单实例 ...

### 发布正式版

```bash
# 1. 提交改动
git add -A && git commit -m "..."

# 2. 预演（不改任何东西）
python3 scripts/release.py --version v16.1.0

# 3. 真发布
python3 scripts/release.py --version v16.1.0 --apply
```

脚本会：检查工作区 → 跑测试 → 打 tag `vX.Y.Z` → 移动 `正式版` → 打包 `release/nao-vX.Y.Z.bundle` → 生成 `docs/RELEASE-NOTES.md`。

**版本号必须三段式**（`v17.0.0`），两段会直接拒绝。

### 服务器部署

```bash
cd ~/NapCat-Pyhon
find . -name "__pycache__" -type d -prune -exec rm -rf {} +
git pull ./nao-vX.Y.Z.bundle main
rm nao-vX.Y.Z.bundle
python3 -m unittest discover -s tests
# 重启
```

### 打包（四种形式）

| 形式 | 命令 | 产物 |
|---|---|---|
| git bundle | `python3 scripts/release.py --apply` | `release/nao-vX.Y.Z.bundle` |
| 源码 zip | `python3 scripts/package.py` | 含依赖清单 |
| 可执行 | `python3 scripts/build_exe.py` | PyInstaller |
| Docker | `python3 scripts/build_docker.py` | 镜像 |

Docker 镜像里自带 Chromium，抓小说可用。

---

## 架构

```
botv/
├── core/       常量、运行时状态、锁、单实例、参数中心、统计
├── infra/      数据库连接与仓储（记忆 / 画像 / 密钥 / 日志 / AI 原文）
├── memory/     上下文、检索（BM25+RRF）、分层预算、时间线、浓缩
├── ai/         人设、角色卡加载、提示词、模型调用、工具调用、回复解析、视觉
├── chat/       入站解析、回复组装、发送、群聊节奏、通知事件、摩擦反馈
├── cmd/        34 个命令（注册表 + 各分类实现）
├── diary/      日记生成与存储
├── schedule/   定时任务、随机闲聊、空闲读书
├── image/      图库：存图、打标、检索、在线图源
├── speech/     语音合成（TTS）与转写（ASR）
├── life/       状态、生活事件、愿望、日程、关系、习惯、摩擦、读书、OCR
├── server/     HTTP API
└── app/        启动引导与主循环

personas/       角色卡（不进代码，可直接改）
scripts/        迁移 / 自检 / 发布 / 打包 / 探测
data/           运行时数据（tunables、digests、cookies、凭据）——不进版本库
```

---

## 版本历史

| 版本 | 主题 | 关键内容 |
|---|---|---|
| v5 | 重构 | 分层包、兼容 shim、单实例、断线重发 |
| v6 | 说话节奏 | 分条、延迟、群聊节奏、代码模式 |
| v7 | 记忆地基 | events 主表、去重、画像 |
| v8 | 检索 | BM25+RRF、分层预算、时间线、CLIP 停用 |
| v9 | 她自己的生活 | 状态向量、生活事件、日记、主动消息 |
| v10 | 关系与主动 | 亲密度、TODO、日程、承诺 |
| v11 | 感官 | 多模态看图、图片记忆、语音合成与转写 |
| v12 | 共同的东西 | 口头禅、里程碑、记忆本、撤回、戳一戳、天气 |
| v13 | 摩擦与成长 | 期待/冷战/和好、成长轨迹、称呼演化、工具调用 |
| v14 | 可换角色 | 人设卡片化、发图择时、主动自适应、 判断 |
| v14.1 | 会话延长 | 30 轮 + 浓缩记录、状态按人分 |
| v15 | 调参与观测 | `!config` / `!stats`、参数持久化 |
| v16 | 读小说 | 番茄抓取、字体加密实测、截图 OCR、HTML+OCR 合并 |
| v16.0.4 | 点名 | 无书名号识别、按书名搜索 |
| **v17.13.0** | **热修** | 重复回复拦截、贴图带上下文、空语音过滤 |
| v17.0 | 并发基建 | 线程池 + 连接池 + `run_blocking` 统一阻塞入口；17 条行为基线 |
| v17.1 | 事件驱动 | 事件对象/注册表/三档队列/worker 池；四个执行器接管定时、主动、读书、日程 |\n| v17.1.1 | 观测 | `!stats` 显示调度状态（队列/完成/失败/熔断） |
| v17.2 | 出站层 | 唯一出口 + 全局锁 + 3 秒合并 + 命令专用通道 |
| v17.3 | 主循环瘦身 | 接收循环 190→22 行；连发合并；runner 408→86 行 |\n| v17.3.1 | 修 | `digests.lines` 撞 MySQL 保留字；建表单表失败不再中断 |\n| v17.4 | 数据模型 | 21 张新表；迁移脚本 8 种 kind；六类读新表、四类双写 |\n| v17.4.1 | 修 | 老库 `events` 无 `deleted_at` 列时迁移失败；`!exit` 要 Ctrl+C 才退 |\n| v17.4.2 | 修 | 迁移脚本五类函数定义在 `sys.exit` 之后 → `NameError` |\n| v17.4.3 | 修 | 迁移 rel/habit/reading 三类：主键重复、缺 phrase、缺 book_url |\n| v17.5 | 日志 | TXT 按天切、保留 180 天（txt + DB 统一清理） |\n| v17.6 | 定时 | `cron_tasks` 表 + 每任务一个 `call_at` 钩子 + 04:00 对账 |\n| v17.7 | 定时入口 | `!cron` 命令；对话提取「明天七点叫我」；8 个场景迁进表 |\n| v17.8 | 线程监护 | 线程池 3→5、连接池 5→6、一个监护线程看两个池 |\n| v17.9 | 体验收尾 | 图片不再误报、表情正常对话、要求看书真读正文、语音后不撤文字 |\n| v17.10 | 稳定性收尾 | 重启熔断 10 次 + 指数退避、重试上限 5、停写旧表 |\n| v17.11 | 存储后端 | MySQL 优先、连不上自动退 SQLite；22 张表方言适配 + 互导脚本 |\n| v17.12 | 语音情绪 | 五档情绪参数 + 角色声纹文件 + `!voice` 调参/试听 |\n| v17.13 | 对话质量 | 重复回复拦截、空语音过滤、贴图带上下文 |\n| v17.14 | 解耦 | conn 配置注入、日志文件优先+异步刷库、db 降级为别名 |\n| v17.15 | 解耦 | ai 不再 import life，改用 lifeport 注册表 |\n| v17.16 | 收尾 | 命令层/HTTP 层零 SQL + server 补 11 条测试 |
| v17.17 | 部署 | `setup.py` 一条命令：依赖+建表+迁移+场景 |

---

## 事件与调度（v17.1）

所有会触发动作的东西——聊天、定时、主动、读书、日程——最终都是同一种对象：

```python
Event(kind="idle_read", key="read:1:u1", fn=read_chapter,
      priority=Priority.IDLE, timeout=300, retries=1)
```

### 三档优先级

| 档位 | 用途 | 排队行为 |
|---|---|---|
| `P0_CHAT` | 聊天回复、命令 | 独占快车道，不排队 |
| `P1_EVENT` | 定时任务、主动消息、提醒 | 快车道，可等 |
| `P2_IDLE` | 读书、抓取、浓缩 | 慢车道，容量满时丢最旧 |

### 调度器结构

| 文件 | 作用 |
|---|---|
| `events/base.py` | `Event` + 三档优先级 |
| `events/registry.py` | `kind → handler` 注册（重复注册直接报错） |
| `scheduler/queue.py` | 三档队列 + 去重 + 容量（**只限空闲档**） |
| `scheduler/policy.py` | 超时 / 退避重试 / 熔断（按 kind 隔离） |
| `scheduler/workers.py` | 双车道 worker 池 |
| `scheduler/dispatcher.py` | 入口：`submit` / `stats` / `describe` |

### 已注册的事件

| kind | 档位 | 做什么 |
|---|---|---|
| `idle_tick` | P2 | 每 30 分钟判断该不该读书 |
| `idle_read` | P2 | 读一章（几百秒上限） |
| `idle_pick_book` | P2 | 没在追书时挑一本 |
| `proactive_tick` | P1 | 每 30 分钟掷骰决定要不要主动 |
| `proactive_say` | P1 | 真正生成并发送主动消息 |
| `schedule_scene` | P1 | 催起床/催睡觉/午睡/复盘等八个场景 |
| `agenda_remind` | P1 | 日程到点提醒 |
| `pending_nudge` | P1 | 待办到点回访 |

### 三条运行规则

| 规则 | 说明 |
|---|---|
| 超时不重试 | 卡住的任务重试只会更慢，直接放弃并计数 |
| 失败退避重试 | 2→4→8 秒，封顶 30 秒 |
| 连续失败熔断 | 同 kind 连续 3 次失败 → 停 1 小时，到期自动恢复 |

### 观测

```
!stats
📊 今日统计 ...
🧵 线程池：3 线程，排队 0
🗄️ 连接池：空闲 3/5，借出 2
⚙️ 调度：运行中 | 队列 1（聊天 0 / 定时 0 / 空闲 1）
   完成 128 | 失败 0 | 超时 0 | 重试 0
📤 出站：在线 | 已发 128 | 失败 0 | 入队 0（积压 0）
⌨️ 命令：23 次 | 平均 12.4 ms | 最慢 stats 45 ms
```

### 主循环瘦身效果

改造前，runner 每秒都在判断「要不要读书」，读书时还要排队等它跑完；
现在 tick 30 分钟醒一次，重活全在 worker 里，**聊天永远能插进来**。

---

## 出站层（v17.2）

所有发出去的东西都从一个口走：

```python
out = get_outbound()
await out.send("send_private_msg", params, label="私聊", kind="chat")
await out.send("get_msg", params, want_response=True)   # 等回包拿 message_id
await out.flush()                                        # 重连补发
```

### 为什么必须唯一

| 问题 | 以前 | 现在 |
|---|---|---|
| 并发发送 | 各处自己加锁，可能交错 | 一把全局锁，一次只发一帧 |
| 断线丢消息 | 各函数各自入队 | 统一入队 + `flush()` 补发 |
| 撤回要 id | 单独一套 echo 逻辑 | 同一个 `want_response` |
| 出问题排查 | 不知道谁发的 | `!stats` 按 kind 计数 |

### 三个配套件

| 文件 | 作用 |
|---|---|
| `egress/outbound.py` | 唯一出口（锁 / 入队 / echo / 计数） |
| `egress/merge.py` | 3 秒合并窗口：**只合定时消息**，聊天永不合并 |
| `cmd/channel.py` | 命令专用通道：不进调度队列、并发 2、超时 15 秒 |

### 合并规则

```
定时消息 A ─┐
定时消息 B ─┴─→ 3 秒窗口 → 一条气泡（"A\nB"）
聊天回复   ───→ 不合并，立刻发
图片/语音  ───→ 不合并，立刻发
```

**为什么聊天不合并**：聊天是「你问我答」，合并会破坏节奏；定时消息是「她主动说」，合成一条更自然。

### 命令为什么绕开队列

```
!stats  →  命令通道  →  立刻执行（人就在等）
读书    →  调度器队列 →  排队慢慢跑（能等）
```

**队列堆满时，命令照样秒回。**

---

## 连发合并（v17.3）

你连着发三句「在吗」「问你个事」「那个…」，她**只回一次**，但三句都看得到。

```
消息 A ─┐
消息 B ─┼→ 静默 0.6 秒 → 合并成 "A\nB\nC" → 回一次
消息 C ─┘        ↑
            最多等 2 秒（window）
```

| 参数 | 值 | 理由 |
|---|---|---|
| 防抖 | 0.6 秒 | 单条只多等这一点，相对 1.5–3 秒回复可忽略 |
| 窗口上限 | 2 秒 | 一直发也得在 2 秒内处理 |
| 单批上限 | 5 条 | 满了提前处理 |

**不合并的情况**：命令（`!` 开头）、群聊、代码模式、纯图片消息。开关：`NAO_BATCH_CHAT=0`。

### 顺带瘦身

| 文件 | 之前 | 现在 |
|---|---|---|
| `chat/handler.py` 接收循环 | 190 行 | 22 行 |
| `schedule/runner.py` | 408 行 | 86 行 |

主循环从「每秒醒一次」改成「30 秒心跳」——跨天、日记、生日、场景派发、日程检查全在 `minute_tick` 里。

---

## 并发与性能（v17.0）

以前所有同步调用（模型、浏览器、OCR、下载）都直接卡在事件循环上——抓小说时你发消息要等它跑完。

现在统一走 `run_blocking()`：

```python
r = await run_blocking(requests.post, url, json=payload, timeout=60, name="deepseek")
```

| 机制 | 参数 | 默认 | 说明 |
|---|---|---|---|
| 线程池 | `NAO_TASK_THREADS` | 3 | 阻塞调用并发数 |
| | `NAO_BLOCKING_TIMEOUT` | 120 | 默认超时（秒） |
| 连接池 | `NAO_DB_POOL_SIZE` | 5 | 复用 MySQL 连接（**≥ 线程池大小**） |
| | `NAO_DB_POOL_TIMEOUT` | 5.0 | 借连接超时，池满快速失败 |

看实时状态：

```
!stats
📊 今日统计 ...
🧵 线程池：3 线程，排队 0
🗄️ 连接池：空闲 3/5，借出 2，复用 47，超时 0
```

**怎么读这几个数**：

| 现象 | 说明 |
|---|---|
| 线程池排队持续 > 3 | 并发不够或任务卡住 |
| 连接池空闲长期 0 且借出等于容量 | 连接泄漏（有人没还） |
| 连接池超时 > 0 | 池太小或漏还 |

新增代码里**不允许再用裸 `asyncio.to_thread`**——有测试守卫（`test_no_raw_thread.py`）。

---

## 数据库表

表定义集中在 `botv/infra/schema.py`（现状表 + 未来纯表），全部 `CREATE TABLE IF NOT EXISTS`。

```bash
python3 scripts/init_db.py            # 看缺哪些表
python3 scripts/init_db.py --apply    # 建缺的（不会动已有表）
python3 scripts/preflight.py --init-db   # 前置检查时自动建
```

**只建不存在的表，永不修改已有表结构**——加列/改类型仍走 `scripts/migrate_*.py`。

---

## 已知限制
| 限制 | 说明 |
|---|---|
| **番茄正文有 OCR 错字** | 约 5%（`神谨`→`神龛`），对摘要够用，逐字引用不可靠 |
| **起点抓不了** | 章节页对机房 IP + 未登录双重限制，已放弃 |
| **抖音未实现** | 规划在 v22.1，且只做看和转发，发评论不可行 |
| 群聊记忆按群号 | 同一个人在私聊和群里是两份记忆 |
| 语义检索靠关键词 | 无外网装不了 embedding，BM25 + 关键词双路 |
| 视觉/ASR 依赖外部接口 | 失败静默降级，不影响聊天 |
| 读书需要 tesseract | 没装就退化成浅层在读 |

---

## 配置项速查

| 环境变量 | 默认 | 说明 |
|---|---|---|
| `NAO_MASTER_QQ` | 空 | 主人 QQ（只有他能用命令） |
| `NAO_DB_HOST` / `NAO_DB_PORT` / `NAO_DB_USER` / `NAO_DB_PASS` / `NAO_DB_NAME` | 空 | 数据库 |
| `NAO_PERSONA` | `nao` | 用哪个角色卡 |
| `NAO_CITY` | 空 | 城市名，设了才查天气 |
| `NAO_READ_IDLE_HOURS` | `2` | 多久没说话才去读书 |
| `NAO_READ_DAILY_CHAPTERS` | `20` | 每天最多读几章 |
| `NAO_BOOK_URLS` | 内置三本 | 自定义书单：`名字\|url,名字\|url` |
| `NAO_OCR_LANG` | `chi_sim` | tesseract 语言包 |
| `NAO_NO_AUTOINSTALL` | 未设置 | 设 `1` 关闭启动时自动装包 |

完整清单见 [`docs/发布检查清单.md`](docs/发布检查清单.md)。

## 文档索引

| 文档 | 内容 |
|---|---|
| [`docs/README.md`](docs/README.md) | 文档总索引（版本 → 条目 → 状态） |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | 发布路线图：v17~v21 每个小版本的拆解与验收点 |
| [`docs/DB-DESIGN.md`](docs/DB-DESIGN.md) | 数据库设计（一表一职责） |
| [`docs/发布检查清单.md`](docs/发布检查清单.md) | 5 组检查项 + 环境变量表 + 发布流程 |
| [`docs/versions/`](docs/versions/) | 各版本设计文档（v6 ~ v21） |
| [`docs/V14-后续清单.md`](docs/V14-后续清单.md) | 未排期需求（A~E 组） |
| [`docs/V6-功能.md`](docs/V6-功能.md) | v6 时代的功能总表（74 项，封版） |
| [`docs/RELEASE-NOTES.md`](docs/RELEASE-NOTES.md) | 最近一次发布说明 |
