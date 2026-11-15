# 插件运行时设计（v27/v28/v38）

> 本文件定 v28 的运行时契约。v28 只做运行时；具体能力层 v29–v44 一版一层。  
> DDL/迁移下沉到 v38 存储层，不在 v28 执行插件建表。

## 1. 信任模型

插件与核心同进程，**视为可信代码**：

- 插件代码经过主账号审核后安装。
- 所有监听地址只允许 loopback `127.0.0.1`（`127.0.0.0` 是网络地址，不能作为监听地址）。
- 不做 Python 沙箱；无法阻止插件直接 import 核心模块。
- 所有正常能力必须通过 `PluginContext`；绕过 context 的调用属于违规代码，审核拒绝。
- 插件包记录作者、hash、capability；安装时校验，不信任文件名。

## 2. PluginContext（先定接口）

```python
@dataclass(frozen=True)
class PluginContext:
    manifest: PluginManifest
    registry: RegistryPort          # 只读查询/注册，不允许改核心
    config: ConfigPort              # config.read / config.secret
    db: DbPort                      # 表级权限
    files: FilePort                 # 路径 glob 权限
    network: NetworkPort            # host suffix 权限
    events: EventPort               # event.read / event.emit
    ai: AiPort                      # 模型调用
    memory: MemoryPort              # 记忆读写
    storage: StoragePort            # 文件/对象存储
    tasks: TaskPort                 # TaskManager
    pool: BlockingPort              # 共享线程池
    logger: LoggerPort
    permissions: PermissionPort
    lifecycle: LifecyclePort
```

### 2.1 ConfigPort

```python
class ConfigPort(Protocol):
    def get(self, key: str, default=None): ...
    def require(self, key: str): ...      # 未授权 config.secret 抛 PermissionDenied
```

### 2.2 DbPort（表级拒绝）

```python
class DbPort(Protocol):
    def select(self, table: str, columns="*", where="", params=(), limit=100): ...
    def insert(self, table: str, values: dict) -> int: ...
    def update(self, table: str, values: dict, where: str, params=()): ...
    def delete(self, table: str, where: str, params=()): ...
    def transaction(self, tables: list[str]): ...   # 只允许授权表
```

规则：

- 每个方法先检查 `db.read/db.write` 的 scope。
- 表不在授权列表：直接 `PermissionDenied`，不执行 SQL。
- 禁止原始 `execute(sql)` 接口。
- `table` 必须是 `plugin_<name>_` 前缀；核心表一律拒绝。

### 2.3 FilePort / NetworkPort

```python
class FilePort(Protocol):
    def read(self, path: str) -> bytes: ...
    def write(self, path: str, data: bytes): ...
    def list(self, path: str) -> list[str]: ...

class NetworkPort(Protocol):
    async def request(self, method: str, url: str, **kwargs): ...
```

规则：

- 路径解析后必须落在授权 glob 内；越界/`..`/符号链接逃逸直接抛 `PermissionDenied`。
- 网络只允许授权 host suffix；其他 URL 直接拒绝。
- 不提供 `requests`/`httpx` 透传。

### 2.4 EventPort / AiPort / MemoryPort / StoragePort

```python
class EventPort(Protocol):
    def emit(self, kind: str, payload: dict): ...
    def on(self, kind: str, handler): ...
    def off(self, kind: str, handler): ...

class AiPort(Protocol):
    async def complete(self, messages, **kwargs): ...
    async def vision(self, image: bytes, prompt: str): ...

class MemoryPort(Protocol):
    async def add(self, item: dict) -> str: ...
    async def search(self, query: str, top_k: int = 5) -> list[dict]: ...

class StoragePort(Protocol):
    async def put(self, key: str, data: bytes, meta: dict | None = None): ...
    async def get(self, key: str) -> bytes | None: ...
    async def delete(self, key: str): ...
```

各 Port 由 v29–v44 对应层实现；v28 先给 interface + fake 实现。

### 2.5 TaskPort / BlockingPort

```python
class TaskPort(Protocol):
    def spawn(self, name: str, coro, owner: str | None = None): ...
    async def cancel_owner(self, owner: str): ...

class BlockingPort(Protocol):
    async def run(self, fn, *args, timeout: float = 120, **kwargs): ...
```

- 任务 owner 默认 `plugin:<name>`，worker 退出时统一 cancel。
- 线程池复用 `infra/blocking`。
- 不允许插件直接 `asyncio.create_task`。

## 3. 权限

```text
config.read / config.secret
db.read / db.write
file.read / file.write
network.outbound
event.read / event.emit
plugin.call
```

三档：

```text
0 = 拒绝
1 = 调用时询问主账号
2 = 直接允许
默认 = 1
```

scope：

```text
config: <key>
db: <table>
file: <glob>
network: <host suffix>
event: <kind>
plugin: <capability>
```

所有 Port 在入口做权限检查；违规直接抛 `PermissionDenied`，不执行副作用。

## 4. Manifest / 安装 / hash

```json
{
  "name": "example.weather",
  "author": "author-name",
  "layer": "tools",
  "version": "1.0.0",
  "api_version": 1,
  "requires_core": ">=27.0.0",
  "capabilities": ["tool.weather@1"],
  "entrypoint": "plugin:factory",
  "auto_start": true
}
```

安装：

```text
!plugin install <package>
→ 读取 manifest，校验 author/layer/version/api_version
→ 计算包 hash 并与 manifest/包记录比对
→ 复制到 plugins/<layer>/<name>/
→ 写 plugin_registry（name 唯一，hash 记录）
→ 进入 pending，等待批准
```

规则：

- 安装目录固定为 `plugins/<layer>/<name>/`，不能由插件指定任意路径。
- 包文件名不参与身份判断；插件身份 = manifest `name`，hash 只做完整性和同名覆盖判断。
- 同名已安装：hash 相同视为重复安装；hash 不同拒绝覆盖，需先卸载。
- `layer` 只能是 `models/channels/memory/tools/storage`。

## 5. capability 版本

能力名：

```text
<domain>.<name>@<version>
```

规则：

- 核心只支持已声明的 `@1` 能力。
- 插件要求 `@2` 而核心只有 `@1`：**拒绝加载**，记录 `plugin_errors`，不降级。
- 同一插件不得同时声明同一能力的多个版本。
- 冲突检测由 MasterRegistry 统一处理。

## 6. registry generation / plugin-lock

`plugin-lock.json`：

```json
{
  "registry_generation": 42,
  "core_version": "27.0.0",
  "plugins": [
    {
      "name": "example.weather",
      "author": "author-name",
      "layer": "tools",
      "version": "1.0.0",
      "hash": "sha256:...",
      "capabilities": ["tool.weather@1"]
    }
  ]
}
```

流程：

```text
prepare_worker 读 registry generation + enabled/auto_start
→ 复制插件到版本目录
→ 写 plugin-lock.json
→ worker 启动读 lock
→ 校验 registry generation == DB generation
→ 不一致：拒绝加载插件（核心仍启动）
→ 一致：加载 lock 中的插件
```

运行中 disable：

```text
registry.disable(name)
→ plugin.stop(ctx)
→ cancel owner tasks
→ 从内存 registry 移除
→ 写 registry generation +1
→ 下一个 worker 不加载
```

当前 worker 不再自动恢复；`!plugin enable` 后由下一次 worker 启动加载。

## 7. 错误 / 停用 / 自启

```text
5 分钟内 3 次失败 → degraded
10 分钟内 5 次失败 → disabled
disabled：stop + cancel tasks，不自动回启
```

启动自启：

```text
manifest.auto_start = true
且 registry enabled
→ 新 worker 启动时自动加载
```

自动停用后不会自动回复；需要主账号重新 enable。

## 8. 初始化顺序

```text
1. command registry
2. events registry
3. life registry
4. ai registry
5. plugin registry（最后）
```

理由：插件注册表依赖前 4 个注册表快照；最后初始化避免半空视图。

## 9. DDL / 卸载

- 插件 DDL/迁移在 **v38 存储层**，不在 v28。
- v38 提供 MySQL/SQLite 方言、dry-run、事务、`plugin_schema_version`。
- 插件表只允许 `plugin_<name>_` 前缀；核心表拒绝。
- `uninstall(ctx)` 只是提供给开发者的接口；**核心不自动调用**。
- `!plugin uninstall` 只停止插件、移除插件文件和注册表记录，不 drop 表、不执行开发者清理逻辑。
- 插件自己的数据/表由开发者自行维护删除。

## 10. `!plugin list`

只列注册表中的第三方插件，不显示核心 native、不显示 fallback 实现。
