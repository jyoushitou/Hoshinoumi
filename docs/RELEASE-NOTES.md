# v18.20.0 发布说明

- 发布时间：2026-11-12
- 上一个发布版本：v18.4.0
- v18 系列封版：v18.6–v18.20 共 15 个次版本
- 完整升级步骤：[升级到 v18.20.0](升级到v18.20.md)

## 本次变更

### 对话与记忆

- v18.6 引用上下文：接收/处理解耦、200 条消息缓存、引用原话；取不到时明确降级，不再每条卡 8 秒
- v18.11 情绪跨天：情绪标签按 3/5 天半衰保留，语音情绪不再只看当天
- v18.12 回忆触发：重记忆每天最多主动提一次，心情差时跳过
- v18.15 双写失败计数、空回复原因可见
- v18.16 读书进度按书落 `reading_progress`，不再反复读同一章

### 时间与调度

- v18.7 规则化时间调度：起床工作日 7:30 / 周末 8:00；睡觉看明天工作日 23:00 / 否则 23:30；晚餐 16:40；13:30 叫午睡起床；周日复盘 21:00
- 支持「今天 7:40 叫我」这类当天微调，不新建任务
- 准点提醒提前 30 秒预生成，到点绕过 3 秒合并窗口
- 日程/待办/主动/空闲统一 `call_at` 秒级钩子，60 秒看门狗重排丢失钩子

### 运维与观测

- v18.8 `!stats` 增加定时行、近 1 分钟完成数、引用命中/未命中/超时
- v18.9 删除 `!task`，新增 `!hooks`；旧 `SCHEDULE_TASKS`/planner 链清理
- v18.13 进程内 TTL 缓存；`!stats` 显示命中率
- v18.14 索引清单脚本 `scripts/migrate_indexes.py`
- v18.17 旧表 `events` 迁入 `memories`，旧表改名并保留只读兼容视图；删 `NAO_LEGACY_WRITE`
- v18.19 每月 1 号 04:30 自动备份，保留 6 份；`!backup` 看清单/立即备份
- v18.20 `!exit` 5 秒看门狗；全角 `！version` 等命令归一化；版本号 18.20.0

### 其它

- v18.10 一条回复最多 4 个气泡，超出合并相邻短句
- v18.18 番茄 OCR 可选 PaddleOCR 双引擎；不一致时记录「不确定」

## 升级步骤（摘要）

> v18.17 改了数据库结构，**必须先迁移再启动新代码**；迁移前务必备份。

```bash
cd ~/NapCat-Pyhon
sudo systemctl stop nao-bot

# 1. 备份（MySQL 示例，SQLite 用 sqlite3 .backup）
mysqldump -h 127.0.0.1 -u 用户 -p 库名 > ~/nao-before-v18.20.sql

# 2. 取代码
git fetch ./nao-v18.20.0.bundle \
  refs/heads/main:refs/remotes/bundle/main \
  refs/tags/v18.20.0:refs/tags/v18.20.0
git checkout v18.20.0

# 3. 依赖
python3 -m pip install -r requirements.txt

# 4. 迁移（顺序不能反）
python3 scripts/migrate_v18.py          # 预览
python3 scripts/migrate_v18.py --apply  # events → memories
python3 scripts/setup.py

# 5. 自检并启动
python3 scripts/preflight.py
python3 run.py
```

详细说明、systemd 切换、验证清单和回滚见 [升级到 v18.20.0](升级到v18.20.md)。

## 回滚

代码回滚到 `v18.4.0` **必须同时恢复升级前的数据库备份**；v18.17 已修改表结构，旧代码不能直接读新库。

```bash
git checkout v18.4.0
mysql -h 127.0.0.1 -u 用户 -p 库名 < ~/nao-before-v18.20.sql
# 或：cp ~/nao-before-v18.20.db data/nao.db
```
