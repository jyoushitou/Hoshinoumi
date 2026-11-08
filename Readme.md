# 友利奈绪 QQ 机器人 v5.0 —— 模块化重构 + 缺陷修复（CLIP 识图 / HTTP API / 代码模式 / AI 日记）

> **v5.0 是一次「只重构 + 只修 bug」的迭代**：3100 行单层代码拆成 10 个包、76 个模块，根目录不再有超过 100 行的文件；
> 同时修掉 7 个线上缺陷（气泡吞字、兜底复读、图片发不出、上线重复、断线丢消息、无时间感）。
> 功能层面的新东西全部留到 v6。

基于 **NapCat** 的 QQ 收发，**Python** 作为后端，调用 **DeepSeek** 网络 API 为主模型、**豆包** 网络 API 为备用模型，使用 **OpenAI CLIP (ViT-B/32, CPU)** 进行本地图片识别打标存档的 QQ 聊天机器人。

---

## 快速开始

```bash
# 1. 部署前自检（依赖 / 模块 / 数据库 / 表 / 密钥 / 提示词）
python3 scripts/preflight.py

# 2. 启动
python3 run.py
```

预检脚本会逐项打勾，缺什么直接说，退出码 0 才算通过。

### 停止

- **推荐**：QQ 里发 `!exit`
- 前台运行：`Ctrl-C` 一次（会打印「[已中断]」，不吐栈）
- 后台 screen：`screen -S bot -X quit`

---

## 核心特性

### 0. MySQL 数据库存储
- 使用 MySQL 替代 JSON 文件存储 + txt 日志 + 环境变量密钥。
- 数据库共 **10 张表**：`logs`、`api_keys`、`global_keywords`、`user_memory`、`images`、`events`、`ai_raw_responses`、`acg_images`、`diaries`。
- 默认连接 `192.168.0.50:3306`，数据库 `TomoriNaoBotData`，用户 `TomoriNaoBot`。
- 日志、对话记忆、全局关键词、API 密钥全部从数据库读写，重启后自动加载。
- 表情包存档（图片文件 + JSON 索引）仍保留本地文件存储（`sticker_archive/` 目录）。
- 新图片统一存入 `images/` 目录 + `images` 数据库表。

### 1. 多轮对话记忆系统
- **私聊/群聊独立记忆**：对每个用户（私聊）和每个群（群聊）分别维护最近 **15 条** 对话记录，形成独立上下文。
- **全局关键词记忆**：从所有对话中提取高频词，长期保存（最多 **40 个**），用于丰富人设提示词。
- 记忆持久化到 **MySQL 数据库**，重启后自动加载。
- **记忆去旧逻辑**：插入新记忆时自动删除超出 15 轮的最旧记录，同时内存 `deque` 也限制 `maxlen=15`，双重保障。

### 2. 双模型兜底回复
- **主模型**：DeepSeek V4 Flash（需 `DS_API_KEY`），超时 60 秒，支持 2 次重试。
  - 异步非阻塞调用：`asyncio.to_thread` 将同步 HTTP 请求分发到子线程，不阻塞事件循环。
  - 调用详情全部日志记录：模型名、消息数、密钥有无、状态码、回复预览。
- **备用模型**：豆包（需 `ARK_API_KEY`），当 DeepSeek 失败时自动切换，最多重试 3 次（401 认证错误直接跳过不再重试）。
  - 仍失败时返回随机傲娇兜底话术（"哼(扭头)"、"才不理你(抱手)"、"切(翻白眼)"）。
- **本地话术**：两个模型都不可用时，随机返回预设的傲娇回复。
- **人设提示词**：固定为《Charlotte》友利奈绪（傲娇毒舌、外冷内热），动态注入全局关键词 + 当前对话历史 + 当前话题关键词 + 事件记忆。
- **身份区分**：对主人（配置中的 MASTER_QQ）以亲密的身份亲密对话，对其他用户保持普通朋友距离。
- **可选的在线人设补充**：支持从 URL 远程拉取人设补充文本（遍历 PERSONALITY_SUPPLEMENT_URLS 列表），也支持本地 `personality_supplement.txt` 文件加载。
- **AI 回复格式**（v5 起「动作」可选）：
  1. 对话内容（100 字以内，**可以多行**）
  2. 动作描写（用括号包裹，如"（扭头）"；**没有动作就整行省略，不要写"（无）"**）
  3. 关键词搜索图片用：20 个从可用列表选取的标签（逗号分隔）
  4. 事件摘要：xxx（可带标签 | tag1,tag2,tag3）
  5. 关键词提炼：5 个关键词（逗号分隔）
  - 解析方式：按**标记**（关键词搜索图片用 / 事件摘要 / 关键词提炼）定位元数据，不再按行号取前两行——多行对话与代码答案都不会被截断

### 3. CLIP 本地识图打标 & 统一图片系统
- **OpenAI CLIP (ViT-B/32)** 运行在 CPU 上，使用 **约 200 个候选标签** 对用户发送的图片进行本地识别、多标签分类。
  - 候选标签分布在 7 大类：表情包常用（20 个）、可爱系（30 个）、二次元（30 个）、场景背景（20 个）、食物（20 个）、日常（20 个）、其他补充（60 个）。
  - 推理过程在子线程中执行（`asyncio.to_thread`），不阻塞主事件循环。
  - 使用 `torch.no_grad()` 禁用梯度计算优化性能。
  - 返回前 3 个得分 > 0.01 的标签，最高分标签作为描述。
- 所有图片以 **MD5 哈希** 命名保存到 `images/` 目录，标签、来源、使用次数存入 `images` 数据库表。
- 回复时根据对话关键词，从数据库中按标签搜索匹配图片（`LIKE %kw%` 匹配，按 use_count DESC 排序），优先返回高频图。
- **ALAPI 在线搜图兜底**：本地无匹配时自动从 ALAPI 斗图接口（`/api/doutu`）或 ACG 接口（`/api/acg`）下载、打标、入库，后续可直接复用。
- **旧 sticker_archive 兼容**：启动时自动将旧存档 JSON 索引数据（`sticker_index.json`）迁入新库（`images` 表 + `sticker_archive/` 目录）。

### 4. AI 回复自动关键词补全
- 位于 `api.py` 中 `get_character_reply()` 函数的最后一步修复逻辑：
  若 AI 回复缺少图片搜索关键词行（第三行），系统自动用 **jieba 分词** 从对话内容（第一行）中提取关键词补充到回复末尾（限制前 10 个）。
- 在 `send.py` 中 `build_reply_message()` 函数的发图逻辑：
  无论 AI 是否提供图片关键词（第三行有 img_kw 还是空），始终立即用 jieba 从对话+动作中提取关键词兜底搜图（`get_best_image`），**无需等待 60 秒**。
- 旧的 `_delayed_jieba_fallback()`（延迟 60 秒后用 jieba 兜底）作为兼容保留，不再被调用。
- 回复限 **max_tokens=200**，保证回复简短精炼。
- AI 完整回复格式由 `botv/ai/parse.py` 的 `parse_ai_reply()` 解析（按标记切分，动作行可选）：
  - 第二行以 `（` 或 `(` 开头 → 动作
  - 含"关键词搜索图片用" → 图片关键词列表
  - 含"事件摘要" → 事件描述
  - 含"关键词提炼" → 提炼关键词
  - 不满足以上条件的中间行 → 额外对话内容追加到第一行

### 5. AI 日记系统（v4.0 新增 · v5 拆为 `botv/diary/` 包）
- **日记生成**：调用 AI 以奈绪视角写日记（傲娇毒舌 + 温柔），数据源为当天 `events` 表事件记录 + `ai_raw_responses` 表对话片段。
- **双模型支持**：优先 DeepSeek，失败自动切换豆包，返回文本自动清理格式行并限制 500 字内。
- **数据库持久化**：日记存入 `diaries` 表（按 target_id + diary_date 唯一），已存在的日记直接读取不重复生成。
- **内存缓存**：生成结果缓存 10 分钟（最多 20 条），避免高频查看时重复调用 AI。
- **无素材降级**：当天无事件记录时返回友好提示；无 API 密钥时直接返回事件列表作为简易纪要。
- **查看命令**（仅主人可用）：
  - `!diary` — 查看今天的日记（自动生成）
  - `!diary <YYYY-MM-DD>` — 查看指定日期的日记（自动生成）
  - `!diary list [天数]` — 最近 N 天日记概览（默认 7，上限 30，显示"日记已生成/有事件/空"状态）
  - `!diary raw <YYYY-MM-DD>` — 查看指定日期的**原始事件记录**（不打 AI）
- **启动追溯自检**（`run.py` 的 `check_diary()`）：
  - **上线消息发出 10 分钟后**再执行追溯（`run.py` 中 `asyncio.sleep(600)` 延迟），确保 API 密钥已从数据库加载、上线消息已发出、CLIP 模型已就绪
  - 检查 `diaries` 表是否为空，若为空 → 追溯最近 7 天有事件记录的日期（`generate_missing_7day_diaries()`）
  - 调用 `generate_diary()` 为最多前 3 个有事件的日期生成日记并写入数据库
  - 打印日志验证：`日记自检通过 ✅ 日记功能正常工作（共 N 篇）`
  - 已有日记时自动跳过，不重复生成
  - **日常日记仅在凌晨 3 点**由定时任务（`schedule.py`）自动生成，启动追溯仅做历史补录

### 6. 定时任务 + 随机偏移
- **7 个预设场景**：催起床、周末吐槽赖床、提醒点外卖、叮嘱午睡、提醒起身、提醒晚餐、催睡觉。
- **随机偏移 ±10 分钟**，避免机械感。
- **智能起床时间**：使用 `chinesecalendar` 模块判断中国法定工作日/节假日，**工作日 7:30** 叫起床，**周末/法定节假日 8:30** 叫起床（国庆、春节等假期自动延后，调休上班日自动提前）。
- **智能催睡时间**：根据**明天**是否是工作日决定今晚催睡觉时间，**工作日前一晚 23:00**，**休息日前一晚 23:30**。
- **周末吐槽赖床**：仅非工作日触发（涵盖周末及法定节假日，`only_holiday=True`）。
- **起床/催睡时附带 ACG 二次元图片**：调 ALAPI ACG 接口获取一张二次元图片，消息后直接发送。
- **上线检测**：程序启动连接 QQ 成功后，同样发送 ACG 图片检验全链路连通性。
- **随机日常闲聊**：每天随机 2~4 个时刻（8:00~23:00），自动避开定时任务前后 60 分钟，闲聊之间也至少间隔 60 分钟。
- **闲聊话题关联事件记忆**：优先从数据库加载用户最近事件作为闲聊话题，让闲聊更加自然有记忆。
- **生日祝福**：
  - 9月6日 12:00 — 主人生日（由主人设定），自动发送生日祝福并附带生日相关图片
  - 11月13日 8:00 — 奈绪生日（Charlotte 角色生日），自动发送祝福并附带奈绪/夏洛特相关图片或 ACG 图
- **自动写日记（凌晨3点）**：每天凌晨 3:00 自动为**昨天**生成奈绪视角日记（基于当天 events + 对话记录），保存到 `diaries` 表（不主动推送），使用 `!diary <日期>` 命令随时查看。
- **跨天自动初始化**：每天首次运行清空 `daily_trigger`、`triggered_today`，重新计算当天所有任务触发时刻和闲聊时间点（`_calc_day_tasks`）。
- **任务执行防重复**：触发前先标记 `daily_trigger.add(key)`，即使异常也不会重复触发同一任务。
- **每个定时任务使用随机自然提示**：催起床/催睡觉/提醒吃饭等场景各有 2~3 种不同的 Prompt 模板，每次随机选一个，让 AI 每次说不同的话而不是固定回复。

### 7. 对话命令系统
- 主人（MASTER_QQ）通过私聊发送 `!` 前缀命令查看/修改运行时参数。
- 非主人发送的命令被忽略（返回 False 继续走 AI 对话）。
- 支持 **26 个命令**：
  - `!help` - 显示完整帮助列表
  - `!status` - 运行状态概览（DS/豆包/CLIP 状态、工作日、对话对象数、关键词数、存档数等）
  - `!status all` - 详细参数（WebSocket 地址、心跳间隔、消息去重缓存、chinesecalendar 状态、今天的日期/星期/工作日类型）
  - `!task` - 定时任务列表与下次触发时间，含今日闲聊时间点
  - `!memory` - 对话记忆统计（总对象数，每个对象的轮数、最后消息预览）
  - `!memory <uid>` - 指定对象的记忆详情（最近 10 条）
  - `!sticker` - 表情包存档统计（总数、贡献用户数）
  - `!clip` - CLIP 状态（是否加载、候选标签数）
  - `!keywords` - 查看全局关键词（按排序显示前 40 个）
  - `!apikeys` - API 密钥状态（DS/豆包/ALAPI 是否存在）
  - `!reload` - 重新加载 API 密钥和记忆数据
  - `!set <键> <值>` - 修改配置（支持：`master_qq`、`heartbeat`）
  - `!say <内容>` - 让奈绪用 AI 回复一句话
  - `!sayg <群号> <内容>` - 让奈绪在指定群说话
  - `!img <关键词...>` - 手动搜图并发送（自动调用 get_best_image）
  - `!acg` - 获取一张 ACG 二次元图（调用 ALAPI ACG 接口）
  - `!event <uid>` - 查看指定对象的事件记忆（最近 10 条）
  - `!clear <uid>` - 清除指定对象的对话记忆和事件记录
  - `!log <行数>` - 查看最近 N 条日志（默认 20，上限 100）
  - `!db` - 数据库统计数据（图片数、记忆条数、事件条数、日志条数、关键词条数）
  - `!usage` - 最近 10 次 token 用量和使用模型（含合计统计）
  - `!uptime` - 机器人运行时长（从数据库第一条日志计算）
  - `!ping` - 测试机器人是否在线
  - `!code` - 开启代码模式（知识正确性优先于人设，30分钟无消息自动退出）
  - `!code off` - 手动退出代码模式
  - `!diary` - 查看今天的日记（AI 生成奈绪视角日记）
  - `!diary <日期>` - 查看指定日期日记，如 `!diary 2026-07-15`
  - `!diary list [天数]` - 最近几天日记概览（默认 7 天，上限 30 天）
  - `!diary raw <日期>` - 查看指定日期的原始事件记录（不调用 AI）

### 8. 消息发送优化（`botv/chat/reply.py` + `botv/chat/send.py`）
- **`build_reply_message()` 核心函数**：
  1. 解析 AI 回复格式（按标记切分）→ 得到对话行 / 动作 / 元数据
  2. 有对话内容 → 添加文本消息段
  3. 有动作描写 → 添加动作文本段
  4. 用 AI 提供的图片关键词（第三行 20 纬度）搜图 → 找到图则添加图片段
  5. AI 没提供关键词或 20 纬度搜不到 → **立即**用 jieba 从对话+动作提取关键词兜底搜图（不等 60s）
  6. jieba 也搜不到 → 从数据库中随机取一张本地图片
  7. 全部失败 → 不发图
- **消息逐条发送间隔 2 秒**，避免刷屏。
- **`send_short_reply()` 入口函数**：接收 AI 回复文本 → 调用 `build_reply_message()` 构建消息列表 → 逐条调用 `send_private_msg()` / `send_group_msg()` 通过 WebSocket 发送。
- **并发安全**：`send_private_msg()` 和 `send_group_msg()` 内部使用 `cfg.send_lock`（`asyncio.Lock`）避免 WebSocket 发送冲突。
- **`select_best_sticker()` 旧接口兼容**：查新库 images 表 → 旧存档 STICKER_DATA → QQ 表情 ID 兜底。
- **`send_sticker_private/group()` 表情包发送**：调用 `select_best_sticker()` → 文件路径用 `make_image_msg()` 构建 NapCat 图片消息，ID 字符串用 `face` 类型消息。
- **`make_image_msg()` 统一图片消息构建**：将本地路径转为 NapCat 绝对路径格式 `[{"type":"image","data":{"file":"绝对路径"}}]`。

### 9. 心跳保活（`botv/heartbeat.py`）
- **通用心跳协程** `heartbeat_monitor(label, ws_ref)`：
  - 每 `HEARTBEAT_INTERVAL=15` 秒发送一次 WebSocket ping 帧
  - `label` 参数用于日志区分（如 'QQ'）
  - `ws_ref` 是全局变量的引用（如 `cfg.active_ws_qq`），每次循环重新读取以获取最新连接
  - 只检测不处理：ping 失败只记日志，不主动关闭连接，由主循环处理重连逻辑

### 10. 日志与容错（`botv/log.py` + `botv/db.py`）
- **五级日志**：系统（初始化/定时任务等）、接收（收到的消息）、发送（发出去的内容）、接口（API 调用/图片处理/CLIP）、异常（错误捕获）
- **双写**：控制台 `print()` + MySQL 数据库 `logs` 表，数据库写入失败不影响主流程（`try/except pass`）
- **`get_recent_logs(limit)`**：从数据库按 id DESC 查询，反转使时间正序返回，带 `[时间] [级别] 内容` 格式
- **消息去重**：`cfg.PROCESSED_MSG_IDS` — `deque(maxlen=80)`，收到消息检查 message_id 是否已存在
- **消息处理锁**：`cfg.PROCESS_LOCK`（`asyncio.Lock`），防止并发处理同一消息，锁释放延迟 `LOCK_RELEASE_DELAY=0.8` 秒
- **网络容错**：图片下载失败记录日志不崩溃；模型请求重试 2~3 次；API 密钥缺失时自动降级
- **AI 原始返回保存**（`db.py` 的 `save_ai_raw_response()`）：
  - 每次模型调用结果（完整 JSON）存入 `ai_raw_responses` 表
  - 从 JSON 中提取 `usage.prompt_tokens`、`usage.completion_tokens`、`usage.total_tokens`
  - 兼容 DeepSeek 和豆包的 usage 格式
  - 记录 status：`success` / `empty_reply` / `http_error_xxx` / `auth_error` / `no_api_key`
- **自动建表和迁移**：启动时自动创建 `acg_images` 表；自动检查 `ai_raw_responses` 表的 token 字段，不存在时 ALTER TABLE
- **`get_recent_usage(limit)`**：查询最近 N 次成功调用的 token 用量统计，用于 `!usage` 命令

### 11. 事件记忆系统（`botv/db.py`）
- **`add_event_to_db(tid, event_summary, tags)`**：从对话中提取重要事件存入 `events` 表，每个对象最多保留 20 条，超出时删除最旧记录
- **`load_events_from_db(tid, tag_keywords=None, limit=5)`**：按目标 ID + 可选的标签关键词过滤（最多 3 个 LIKE 条件），返回 `[(event_summary, tags), ...]`
- **注入提示词**：在 `memory.py` 的 `build_memory_context()` 中，按当前对话关键词过滤并注入最近事件记忆，让 AI 记住用户的重要日程
- **闲聊关联**：定时闲聊触发时优先从数据库加载最近 5 条事件作为话题传递给 AI，让闲聊更自然

### 12. HTTP API 服务器（v2.0 新增 ⭐ `botv/api_server.py`）
- 基于 `aiohttp` 的异步 HTTP 服务器，监听端口 **60908**，共享 `aiohttp.ClientSession`
- 所有接口需 **Bearer Token** 验证（自动生成 32 位字母数字字符串，存入数据库 `api_keys` 表 `API_SERVER_TOKEN` 行）
- 认证中间件统一使用 `hmac.compare_digest` 安全比较，避免时序攻击
- 支持 **20 个并发** 请求（`aiohttp.TCPConnector(limit=20)`），所有响应统一 UTF-8 编码
- **接口列表**：
  - `GET /api/health` — 无需 Token，返回 `{"status":"ok","timestamp":"..."}`
  - `GET /api/status` — 运行状态 + 数据库统计（图片数、记忆数、事件数、日志数、关键词数、AI 响应数）+ 运行时数据
  - `GET /api/usage?limit=N` — 最近 N 次 AI 调用的 token 用量统计
  - `GET /api/memory?target_id=XXX` — 指定对象对话记忆详情（每条的用户/机器人消息）；不传 target_id 返回所有对象概况
  - `GET /api/logs?limit=N` — 最近 N 条日志
  - `GET /api/token` — 返回 Token 前缀、地址、端口、完整接口列表说明
  - `POST /api/chat` — 传入 `{"message":"...","target_id":"..."}`，返回 AI 回复（共享 QQ 的对话记忆和关键词系统）
  - `POST /api/command` — 传入 `{"command":"help"}`，执行 ! 命令并返回文本结果

---

## 项目结构（v5.0）

```
NapCat+Python/
├── run.py                     # 入口：依赖自检 → botv.main（Ctrl-C 干净退出）
├── botv/
│   ├── core/                  # 基础设施（零业务）
│   │   ├── constants.py       #   不可变配置：QQ号、端口、模型名、标签表、DB_CONFIG
│   │   ├── state.py           #   唯一可变全局状态：连接/锁/密钥/记忆池/代码模式/出站队列
│   │   ├── http.py            #   HTTP 会话工厂
│   │   └── types.py           #   Fallback 标记（兜底文案，禁止入库）
│   ├── ai/                    # 模型与提示词
│   │   ├── client.py          #   DS/豆包调用、降级、原始返回落库
│   │   ├── models.py          #   ChatModel 适配器（DeepSeek / 豆包）
│   │   ├── chain.py           #   FallbackChain：依次尝试多个模型
│   │   ├── parse.py           #   回复解析（五行 → 对话/动作/关键词/事件）
│   │   ├── persona.py         #   人设文本 + 20 纬度标签表
│   │   └── prompt.py          #   人设补充加载 + 提示词渲染 + 当前时间
│   ├── chat/                  # 会话链路
│   │   ├── handler.py         #   QQ 主循环：连接去重、上线通知、消息分发
│   │   ├── inbound.py         #   入站解析：文本/图片/表情 → 文本
│   │   ├── reply.py           #   回复组装：按标记切分 → 气泡 + 图片
│   │   ├── send.py            #   发送：并发锁、断线入队、重连补发
│   │   └── transport.py       #   QqTransport（Transport 端口实现）
│   ├── cmd/                   # 命令（26 个，注册表分发）
│   │   ├── registry.py        #   @command 装饰器 + 上下文
│   │   ├── formatters.py      #   8 个纯文本格式化函数
│   │   ├── basic.py           #   help/status/task/memory/sticker/clip/keywords/apikeys
│   │   ├── query.py           #   ping/log/db/uptime/usage
│   │   ├── admin.py           #   reload/set/code/exit/quit
│   │   ├── media.py           #   say/sayg/img/acg
│   │   ├── memory_cmd.py      #   event/clear
│   │   └── diary_cmd.py       #   diary
│   ├── infra/                 # 数据访问（唯一写 SQL 的地方）
│   │   ├── conn.py            #   线程本地连接
│   │   ├── repo_log.py / repo_key.py / repo_memory.py / repo_ai.py
│   ├── server/                # HTTP API
│   │   ├── http_api.py        #   鉴权中间件 + 路由注册 + 启动
│   │   ├── routes_meta.py     #   health/status/usage/memory/logs/token
│   │   ├── routes_chat.py     #   chat/command
│   │   └── config.py, common.py
│   ├── diary/                 # 日记：store（存取）/ generate（生成）/ view（展示）/ cache（缓存）
│   ├── schedule/              # 定时：config（任务表）/ planner（排期）/ runner（主循环）
│   ├── image/                 # 图片：store（存取）/ fetch（在线源）/ pick（选图）
│   ├── ports/                 # 端口定义：ChatModel / Transport / MemoryStore / Embedder / Retriever / Clock
│   ├── app/                   # 装配：bootstrap（初始化建表）/ loop（WebSocket+心跳+定时）
│   ├── main.py                # 20 行，只做装配
│   ├── log.py, memory.py, clip.py, heartbeat.py, utils.py, sticker_archive.py
│   └── （api.py / send.py / db.py / handler.py / api_server.py / personality.py 为兼容转发层）
├── scripts/
│   ├── preflight.py           # 部署预检：依赖/模块/数据库/表/密钥/提示词
│   └── clean_fallback_data.py # 清理历史兜底数据（默认 dry-run）
├── tests/
│   ├── test_smoke.py          # 冒烟测试：解析/组装/命令/结构/时间/队列
│   └── test_ports.py          # 端口实现测试：模型适配器/模型链/传输
├── docs/                      # 重构记录、功能清单、索引
├── images/                    # 图片存储（MD5 命名，不入库）
└── sticker_archive/           # 旧表情包存档
```

**分层规则**：
- `core/` 只管常量和状态，不 import 任何业务模块
- `infra/` 是唯一写 SQL 的地方，`domain` 层不出现 `SELECT`
- `ports/` 只有 Protocol，零依赖、零副作用
- 根目录的 `api.py` 等只做转发，调用方迁完后可删

---

## 数据库建表

提前创建数据库及 10 张表：

```sql
CREATE DATABASE IF NOT EXISTS TomoriNaoBotData;
USE TomoriNaoBotData;

CREATE TABLE logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    level VARCHAR(10) NOT NULL COMMENT '日志级别：系统/接收/发送/接口/异常',
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE api_keys (
    id INT AUTO_INCREMENT PRIMARY KEY,
    key_name VARCHAR(50) NOT NULL UNIQUE COMMENT '密钥名称，如 DS_API_KEY / ARK_API_KEY / ALAPI_TOKEN / API_SERVER_TOKEN',
    key_value VARCHAR(255) NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

INSERT INTO api_keys (key_name, key_value) VALUES ('DS_API_KEY', 'your_deepseek_key');
INSERT INTO api_keys (key_name, key_value) VALUES ('ARK_API_KEY', 'your_doubao_key');
INSERT INTO api_keys (key_name, key_value) VALUES ('ALAPI_TOKEN', 'your_alapi_token');
-- API_SERVER_TOKEN 由程序首次启动时自动生成并写入

CREATE TABLE global_keywords (
    id INT AUTO_INCREMENT PRIMARY KEY,
    keyword VARCHAR(50) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_memory (
    id INT AUTO_INCREMENT PRIMARY KEY,
    target_id VARCHAR(50) NOT NULL COMMENT '私聊用QQ号，群聊用群号',
    user_msg TEXT NOT NULL,
    bot_msg TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_target_id (target_id)
);

CREATE TABLE images (
    id INT AUTO_INCREMENT PRIMARY KEY,
    md5_hash VARCHAR(32) NOT NULL UNIQUE,
    image_data MEDIUMBLOB COMMENT '图片二进制数据',
    tags VARCHAR(255) DEFAULT '' COMMENT 'CLIP标签，逗号分隔',
    source_url VARCHAR(512) DEFAULT '' COMMENT '来源URL',
    file_path VARCHAR(255) DEFAULT '' COMMENT '本地文件路径',
    ext VARCHAR(10) DEFAULT 'jpg' COMMENT '文件扩展名',
    use_count INT DEFAULT 0 COMMENT '使用次数',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    target_id VARCHAR(50) NOT NULL,
    event_summary VARCHAR(255) NOT NULL COMMENT '事件摘要',
    tags VARCHAR(100) DEFAULT '' COMMENT '事件相关标签，逗号分隔',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_target_id (target_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE ai_raw_responses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    model_name VARCHAR(50) NOT NULL COMMENT '模型名称，如 DeepSeek(deepseek-v4-flash)',
    user_msg TEXT COMMENT '用户消息',
    raw_response_json JSON COMMENT 'AI返回的完整JSON',
    response_text TEXT COMMENT '提取的回复文本',
    target_id VARCHAR(50) DEFAULT '' COMMENT '对话目标ID',
    status VARCHAR(20) DEFAULT '' COMMENT '状态：success/empty_reply/http_error/auth_error等',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    prompt_tokens INT DEFAULT 0 COMMENT '输入token数',
    completion_tokens INT DEFAULT 0 COMMENT '输出token数',
    total_tokens INT DEFAULT 0 COMMENT '总token数'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- acg_images 表由程序启动时自动创建，结构与 images 表一致，用于缓存ACG二次元图片

-- diaries 日记表（程序启动时也会自动创建）：存储AI生成的奈绪视角日记
CREATE TABLE diaries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    target_id VARCHAR(50) NOT NULL COMMENT '日记所属人（主QQ号）',
    diary_date DATE NOT NULL COMMENT '日记对应的日期',
    content TEXT COMMENT '日记正文（AI生成）',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_target_date (target_id, diary_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## Python 依赖

```bash
pip install websockets requests urllib3 jieba Pillow pymysql chinesecalendar aiohttp
```

**CLIP 额外依赖（可选，不影响核心功能）：**
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install git+https://github.com/openai/CLIP.git
```
> 若未安装 CLIP 依赖，程序会禁用 CLIP 识图功能，仅做普通图片存档。

**NapCat 配置：**
- NapCat 网络配置中添加 WebSocket 客户端地址：`ws://127.0.0.1:3001`

---

## 启动流程（v5）

1. **创建 MySQL 数据库** `TomoriNaoBotData` 并执行建表 SQL。
2. 在 `api_keys` 表中插入 DeepSeek、豆包、ALAPI 密钥（`API_SERVER_TOKEN` 启动时自动生成）。
3. **启动 NapCat**，反向 WebSocket 指向 `ws://127.0.0.1:3001`。
4. **预检 + 启动**：

   ```bash
   python3 scripts/preflight.py
   python3 run.py
   ```

5. 启动时的实际顺序：

   | 阶段 | 位置 | 做什么 |
   |---|---|---|
   | 依赖自检 | `run.py` | 必需依赖缺失才安装；**可选依赖只检查不安装**（无网不会卡） |
   | 初始化 | `app/bootstrap.py` | 加载密钥 → 记忆 → 表情包 → CLIP → 人设补充 |
   | 建表迁移 | `app/bootstrap.py` | 建 `acg_images` / `diaries`，给 `ai_raw_responses` 补 token 字段 |
   | 状态初始化 | `app/bootstrap.py` | 消息处理锁、退出事件 |
   | API 服务器 | `server/http_api.py` | 监听 `0.0.0.0:60908`，生成/加载 Token |
   | 常驻循环 | `app/loop.py` | WebSocket `:3001` + 心跳 + 定时任务，异常 5 秒后重启 |
   | 上线通知 | `chat/handler.py` | 连接成功发一次（**60 秒内不重复**）+ ACG 图 |
   | 日记追溯 | `run.py` | 上线 10 分钟后检查 `diaries` 表，空则补录最近 7 天 |

6. 停止：QQ 里发 `!exit`，或前台 `Ctrl-C` 一次（干净退出，不打印栈）。

---

## 各模块核心函数一览

| 包 / 模块 | 关键函数 | 说明 |
|---|---|---|
| `ai/client` | `call_deepseek` / `call_doubao` / `get_character_reply` | 双模型调用、降级、原始返回落库 |
| `ai/models` | `DeepSeekModel` / `DoubaoModel` | ChatModel 端口适配器 |
| `ai/chain` | `FallbackChain` | 模型链：依次尝试 |
| `ai/parse` | `parse_ai_reply` | 五行解析（按标记切分） |
| `ai/prompt` | `get_system_prompt` / `now_text` | 提示词渲染 + 当前时间 |
| `ai/persona` | `LOCAL_SYSTEM_PROMPT` / `build_available_tags` | 人设文本与标签表 |
| `chat/handler` | `websocket_handle_qq` / `claim_online_notice` | QQ 主循环、上线去重 |
| `chat/inbound` | `parse_message_content` | 文本 / 图片 / 表情 → 文本 |
| `chat/reply` | `build_reply_message` / `split_reply_text` | 回复组装（对话 / 动作 / 图片） |
| `chat/send` | `send_private_msg` / `flush_outbox` | 发送、断线入队、重连补发 |
| `chat/transport` | `QqTransport` | Transport 端口实现（含戳一戳） |
| `cmd/registry` | `command` / `run` / `has` | 命令注册表与分发 |
| `infra/conn` | `get_db` / `get_cursor` | 线程本地连接 |
| `infra/repo_memory` | `add_user_memory_to_db` / `load_events_from_db` | 记忆仓储 |
| `infra/repo_log` / `repo_key` / `repo_ai` | 日志 / 密钥 / AI 记录 | 其余仓储 |
| `server/http_api` | `start_api_server` | HTTP API 启动与鉴权 |
| `diary/generate` | `generate_diary` | 日记生成（素材 → AI → 落库） |
| `schedule/runner` | `cycle_task_run` | 定时任务主循环 |
| `image/pick` | `get_best_image` | 选图：本地 → ALAPI → 随机 |
| `image/store` | `process_and_save_image` / `materialize_image` | 图片存取、路径解析、blob 恢复 |
| `memory` | `add_target_memory` / `build_memory_context` | 记忆写入（拒绝兜底）与上下文构建 |
| `app/bootstrap` | `bootstrap` | 初始化：加载 → 建表 → 状态 |
| `app/loop` | `serve` | WebSocket + 心跳 + 定时常驻 |

## 开发与测试

```bash
# 跑测试（不需要数据库，缺失依赖会自动打桩）
python3 -m unittest discover -s tests -v

# 部署前预检（需要数据库）
python3 scripts/preflight.py

# 清理历史兜底数据（默认 dry-run）
python3 scripts/clean_fallback_data.py
python3 scripts/clean_fallback_data.py --apply
```

**分层规则**：

- `core/` 只放常量和状态，不 import 业务模块
- `infra/` 是唯一写 SQL 的地方
- `ports/` 只有 Protocol，零依赖
- 根目录的 `api.py` / `send.py` / `db.py` / `handler.py` / `api_server.py` / `personality.py` 是兼容转发层，调用方迁完后可删

## v5.0 更新日志（重构 + 修复）

### 🔧 模块化重构

- 3100 行单层代码 → **10 个包、76 个模块**，根目录最大文件 92 行
- 新增分层：`core`（常量/状态）/ `infra`（仓储）/ `ports`（协议）/ `ai` / `chat` / `cmd` / `server` / `diary` / `schedule` / `image` / `app`
- 斩断循环依赖：`api.py` 原来把 import 放在文件末尾，现在方向单一（`ai/client → memory/personality/db`）
- 常量化：`config.py` 从 92 行降到 6 行，可变状态集中到 `core/state.py`
- 端口化：`ChatModel` / `Transport` / `MemoryStore` / `Embedder` / `Retriever` / `Clock` 六个 Protocol，模型与传输各有适配器
- 命令系统：26 个命令从 `if/elif` 长链改为注册表，`commands.py` 426 → 45 行
- 六个兼容转发层保留旧 import 路径，调用方零改动

### 🐞 缺陷修复

| 编号 | 问题 | 修复方式 |
|---|---|---|
| F1 | 无动作时硬发「（无）」气泡 | 动作行可选，空则不发送；prompt 同步改口 |
| F2 | 兜底文案入库导致复读 | `Fallback` 标记 + 记忆层拒收 + 清理脚本 |
| F3 | 吞字 / 代码答案被截断 | 元数据改为**按标记**识别，多行对话与代码块完整发送 |
| F4 | 图片发送失败 | 相对路径按项目根解析 + 缺失时从数据库 blob 恢复 |
| F5 | 上线通知重连时重复 | 60 秒冷却 |
| F6 | 断线期间消息丢失 | 出站队列（最多 50 条）+ 重连补发 + 心跳看门狗 |
| F7 | 没有时间感知 | prompt 注入「当前时间/星期/时段」 |

### 🧪 测试与工具

- `tests/`：47 个用例（解析 / 组装 / 命令 / 结构 / 时间 / 队列 / 端口实现），`python3 -m unittest discover -s tests`
- `scripts/preflight.py`：部署预检（依赖 / 模块 / 数据库 / 表 / 密钥 / 提示词）
- `scripts/clean_fallback_data.py`：清理历史兜底数据，默认 dry-run
- `run.py`：可选依赖不再自动安装（无网会卡）；`Ctrl-C` 一次干净退出

---

## v4.0 更新日志

### 🆕 AI 日记系统
- 新增 `botv/diary.py` 模块：从 `events` 表事件 + `ai_raw_responses` 对话素材生成奈绪视角日记
- 双模型支持（DeepSeek → 豆包降级），缓存 10 分钟，持久化到 `diaries` 表
- 4 个日记查看命令：`!diary`、`!diary <日期>`、`!diary list [天数]`、`!diary raw <日期>`

### 🚀 启动追溯自检
- `run.py` 新增 `check_diary()`：空日记表时自动追溯最近 7 天有事件记录的日期
- **上线消息发出 10 分钟后再执行追溯**（`asyncio.sleep(600)`），确保 API 密钥已从数据库加载完成，避免生成假日记
- 调用 AI 生成最多 3 篇测试日记并写入数据库，验证日记功能正常工作
- 日常日记仅在凌晨 3 点由定时任务自动生成，启动追溯仅做历史补录

### 🔧 API 密钥加载顺序修复
- `main.py` 中 `reload_api_keys()` 调整到 `load_memories()` **之前**执行，确保任何时候触发日记生成时 API 密钥都已就绪
- `api.py` 的 `call_deepseek()` / `call_doubao()` 新增 `target_id` 参数，日记场景下不再依赖从消息中提取 target_id（此前会截断导致 `Data too long` 报错）
- `diary.py` 调用 AI 时显式传入真实 `target_id`，避免 `_extract_target_id` 取消息前 80 字符导致超长
- `db.py` 的 `save_ai_raw_response()` 对 `target_id` 做防御性截断（50 字符），防止数据库写超限

### ⏰ 定时任务扩展
- 凌晨 3 点自动为昨天生成日记（不主动推送，用 `!diary` 随时查看）

### 📚 命令系统扩充
- 命令数从 22 个扩展到 **26 个**（新增 4 个日记命令）

---

## 写在最后

- 部署环境：**7 核 / 12G Linux**，CLIP CPU 推理单张图片约 1~3 秒；纯文字消息从收到到发出，耗时主要在模型 API（1~3 秒），本地处理在毫秒级。
- 配置入口：`botv/core/constants.py`（不可变）、`botv/core/state.py`（运行时状态）、`botv/ai/persona.py`（人设与标签表）。
- 启动文件：**`run.py`**；旧版单文件 **`botv.py`**（v1.x）已归档保留，不再使用。
- 排查问题：先跑 `python3 scripts/preflight.py`，再看 `logs` 表或控制台输出。
- 自动化测试：`python3 -m unittest discover -s tests -v`（不需要数据库）。
