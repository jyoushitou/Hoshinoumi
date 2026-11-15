# v27–v44 接口层开发总纲

> 目标：**一个大版本只开放一层接口**。每层都同时具备：
> 核心 native 实现、第三方插件实现、统一注册表、审批、错误记录、任务归属、热更新加载。

## 1. 十八个接口版本

| 版本 | 层 | 开放的能力 | 核心 native |
|---|---|---|---|
| v27 | 插件注册表基础 | PluginManifest / PluginRegistry / MasterRegistry | 无 |
| v28 | 插件运行时 | PluginContext / 审批 / loader / errors / tasks | 无 |
| v29 | 模型契约 + native | `model.<name>@1` | DeepSeek / 豆包 |
| v30 | 模型插件接入 | `model.<name>@1` 第三方实现 | 同上 |
| v31 | 记忆契约 + native | `memory.store.<name>@1` / `memory.retriever.<name>@1` | SQLMemoryStore / BM25 |
| v32 | 记忆插件接入 | 第三方 store / retriever | 同上 |
| v33 | 通道契约 + native | `channel.<name>@1` | NapCat / QQ |
| v34 | 通道插件接入 | 第三方通道 | 同上 |
| v35 | 工具契约 + native | `tool.<name>@1` | 现有工具 |
| v36 | 工具插件接入 | 第三方工具 | 同上 |
| v37 | 存储契约 + native | `storage.backend.<name>@1` / `storage.repository.<name>@1` | MySQL / SQLite |
| v38 | 存储插件接入 | 第三方 backend / repository + 插件 DDL/迁移 | 同上 |
| v39 | 调度契约 + native | `scheduler.<name>@1` / `schedule.trigger.<name>@1` | asyncio |
| v40 | 调度插件接入 | 第三方 scheduler / trigger | 同上 |
| v41 | 出站契约 + native | `transport.<name>@1` | WebSocket |
| v42 | 出站插件接入 | 第三方 transport | 同上 |
| v43 | 默认链路契约 + native | `route.<layer>.<name>@1` | 核心默认链路 |
| v44 | 默认链路插件接入 | 第三方 route candidate | 同上 |

规则：

- 运行时契约见 [PLUGIN-RUNTIME-DESIGN.md](PLUGIN-RUNTIME-DESIGN.md)。
- v28 不做插件 DDL；DDL/迁移统一在 v38 存储层。
- 初始化顺序：command → events → life → ai → plugin（最后）。
- `@2` 能力在核心只有 `@1` 时拒绝加载，不做降级。
- 安装按 manifest name + 包 hash，复制到 `plugins/<layer>/<name>/`。
- `!plugin list` 不显示核心 native/fallback。

- **核心 native 不实现 PluginManifest，不进入插件表。**
- 插件实现某一层的 Protocol，通过 v27 的 PluginRegistry 注册。
- 调用方 `registry.get(capability)` 返回 `None` 时，回落核心 native。
- 每层的默认选择由 v43 RouteRegistry 统一定义（v44 接第三方候选）；默认仍优先核心 native。

## 2. 六个注册表

```text
第 1：命令注册表        bot/cmd/registry.py
第 2：事件注册表        bot/events/registry.py
第 3：生活能力端口      bot/core/lifeport.py
第 4：AI 文本端口       bot/core/ai_port.py
第 5：插件注册表        bot/registry/plugins.py
第 6：注册表管理器      bot/registry/master.py
```

第 6 个是**静态注册表的注册表**：

```text
master.py 启动时注册 5 个注册表对象
不支持运行时动态新增注册表
负责统一查询、冲突检测、快照、健康状态
```

前 4 个保留现有实现，由 master 做 adapter，不重写。

## 3. 插件目录

```text
plugins/
  models/
  channels/
  memory/
  tools/
  storage/
    <plugin-name>/
      plugin.json
      plugin.py
      migrations/
        001_init.sql
```

层目录使用英文小写：`models`、`channels`、`memory`、`tools`、`storage`。

`plugin.json` 至少：

```json
{
  "name": "example.weather",
  "version": "1.0.0",
  "api_version": 1,
  "requires_core": ">=27.0.0",
  "capabilities": ["tool.weather@1"],
  "entrypoint": "plugin:factory",
  "priority": 100
}
```

## 4. 权限与审批

敏感权限点：

```text
config.read
config.secret
db.read
db.write
file.read
file.write
network.outbound
event.read
event.emit
plugin.call
```

等级：

```text
0 = 拒绝
1 = 调用时询问主账号
2 = 直接允许
默认 = 1
```

流程：

```text
安装插件
→ 主账号审核（询问所有权限点）
→ 写入 plugin_permissions
→ 后续可用 !plugin permission <name> <permission> <0|1|2> 修改
```

安装时审核一次；后续每个权限点可单独改等级。

## 5. 热更新

插件采用**进程级热更新**，不做运行中 `importlib.reload`：

```text
prepare_worker 把当前启用插件快照到版本目录
→ 新 worker 启动加载
→ 健康检查
→ current 切换
→ 旧 worker drain
```

已启用插件在热更后自动加载：

```text
启用状态在注册表/数据库
插件代码快照在版本目录
新 worker 读同一份启用清单
```

## 6. 错误与停用

```text
插件异常 → registry 记录 plugin_errors
→ 连续失败达到阈值自动停用
→ 主账号 !plugin errors 查看
→ !plugin enable/disable 手动恢复
```

## 7. 任务 / 线程 / 连接

插件不能自己创建裸任务或连接。

```python
ctx.tasks.spawn(name, coro, owner="plugin:...")
await ctx.pool.run_blocking(fn, timeout=...)
with ctx.db.cursor() as c: ...
```

- 任务统一由 TaskManager 持有，worker 关闭时 cancel。
- 线程池复用 `infra/blocking`。
- 连接池复用统一 DB pool。
- v27 期间把核心 DB 主路径从 `infra/conn` 线程本地连接切到统一 pool。

## 8. 插件 DDL

```text
plugins/<layer>/<name>/migrations/001_init.sql
```

规则：

- 运行时契约见 [PLUGIN-RUNTIME-DESIGN.md](PLUGIN-RUNTIME-DESIGN.md)。
- v28 不做插件 DDL；DDL/迁移统一在 v38 存储层。
- 初始化顺序：command → events → life → ai → plugin（最后）。
- `@2` 能力在核心只有 `@1` 时拒绝加载，不做降级。
- 安装按 manifest name + 包 hash，复制到 `plugins/<layer>/<name>/`。
- `!plugin list` 不显示核心 native/fallback。

- MySQL + SQLite 两套方言。
- 插件表前缀 `plugin_<name>_`。
- 不允许改核心表。
- 不在 worker 启动时自动建表。
- `!plugin migrate <name>` 先 dry-run，主账号确认后执行。
- 记录 `plugin_schema_version`。

## 9. 每版验收共同项

```text
本层 Protocol 定义完成
核心 native adapter 行为不变
第三方 adapter 通过 PluginRegistry 接入
权限、错误、任务、热更走统一入口
旧测试全绿 + 本层 fake adapter 测试
```
