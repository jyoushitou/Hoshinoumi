# v25 热更新原理与数据交换（独立说明）

> 面向问题：热更到底怎么实现？新进程怎么读代码？旧代码为什么不变？
> ingress 和 worker 是网络通讯还是 Python 内部通讯？数据怎么交换？
>
> 对应版本：**v25.6.0**｜代码：`bot/ingress.py`、`bot/core/worker.py`、
> `bot/core/worker_gc.py`、`scripts/nao_supervisor.py`、`scripts/prepare_worker.py`

## 一句话

```text
不是在一个 Python 进程里热替换代码；
是入口进程不动，另起一个完整的新 Python 进程，
用 current 软链把新流量切过去，旧进程 drain 后退出。
```

这属于**进程级蓝绿部署**，不是线程注入。

## 1. 先排除误解

### 不是这样

```text
原程序里开一个新线程
新线程读新代码
新线程跑新逻辑
旧线程销毁
```

v25 没有这样做。

### 是这样

```text
PID 100  nao-ingress       一直活着，持有 3001/27004
PID 200  worker 25.5.x     旧进程，继续处理已有连接
PID 300  worker 25.6.0     新进程，加载完整新代码
```

切换后：

```text
新 HTTP / 新 WebSocket -> PID 300
已有 WebSocket          -> PID 200
60 秒后 PID 200 退出
```

粒度是**进程**，不是线程。

## 2. 为什么不用线程

Python 线程共享：

```text
同一个解释器
同一份 sys.modules
同一份全局变量
同一份内存
```

如果在原进程里 `importlib.reload`：

```text
旧线程还在执行旧函数
新线程已经导入新模块
同一个模块名只能有一份
```

会出现：

```text
旧协程引用旧模块
新代码依赖的全局变量没初始化
旧连接对象属于旧类
定时任务一半旧、一半新
单例状态被覆盖
```

所以 v25 选择：

```text
新进程 + 完整新代码 + 入口切流量
```

旧进程的代码对象在内存里不会被磁盘修改影响。

## 3. 新进程怎么读到新代码

`prepare_worker.py` 先复制源码：

```text
data/workers/versions/25.6.0/
  run.py
  bot/
    ...
  scripts/
  ...
```

再把运行时共享项软链过去：

```text
.env
config.local.json
data
personas
```

supervisor 启动：

```python
subprocess.Popen(
    ["python3", "-u", "run.py"],
    cwd="data/workers/versions/25.6.0",
    env={
        "NAO_WORKER_MODE": "1",
        "NAO_WORKER_SOCKET_DIR": ".../25.6.0",
    },
)
```

新进程启动时：

```text
cwd = .../versions/25.6.0
sys.path[0] = .../versions/25.6.0
```

所以：

```python
import bot
```

导入的是：

```text
.../versions/25.6.0/bot/
```

不是旧目录：

```text
.../versions/25.5.7/bot/
```

## 4. 旧代码为什么不会变

Python 启动后：

```text
读 .py
编译成 code object
放进 sys.modules
之后一直用内存里的 code object
```

修改磁盘上的 `.py` 文件，不会自动改变已加载的模块。

v25 又明确不做：

```text
importlib.reload
exec 新代码到旧进程
monkey patch 运行中的函数
```

所以：

```text
旧进程：旧代码对象 + 旧内存状态
新进程：新代码对象 + 新内存状态
```

它们只共享持久化数据，不共享解释器。

## 5. 通讯到底是什么

### 外部 → ingress

```text
NapCat  --WebSocket/TCP-->  ingress:3001
网关/客户端 --HTTP/TCP--> ingress:27004
```

这是网络通讯。

### ingress → worker

```text
Unix domain socket
data/workers/versions/<version>/api.sock
data/workers/versions/<version>/qq.sock
```

这是**本机进程间通讯（IPC）**，不是 TCP/IP 网络，也不是 Python 进程内调用。

上层协议仍然是：

```text
HTTP
WebSocket
JSON
```

只是底层从 TCP 换成 Unix socket。

### worker → MySQL

```text
TCP 192.168.0.50:3306
```

这是网络通讯。

### 新旧 worker 之间

```text
没有直接 RPC
没有共享内存
```

它们只通过共享存储交换数据：

```text
MySQL
data/
config.local.json
personas/
```

## 6. 数据怎么交换

### 业务数据

```text
记忆、用户、阅读进度、摘要 -> MySQL
本地书文件                 -> data/books/
人设、提示词               -> personas/
运行配置                   -> config.local.json
```

新旧 worker 连同一个数据库，所以：

```text
旧 worker 写的记忆，新 worker 能读到
新 worker 写的进度，旧 worker 也能读到
```

### 控制面数据

```text
data/workers/current       当前生效版本
data/workers/versions/...  版本代码和 socket
worker.pid                 进程号
worker.log                 日志
data/update_status.json    最近一次热更结果
```

ingress 每次新请求/新 WS 连接都会解析 `current`：

```text
current -> 25.6.0 -> 新请求进新 worker
```

## 7. 为什么入口不用重启

`nao-ingress` 只做两件事：

```text
持有 3001/27004
把字节转发给 current 指向的 Unix socket
```

它不 import 业务代码，也不关心 worker 是哪个版本。

所以换 worker 对它是透明的：

```text
旧 socket 还在 -> 旧连接继续
新 socket 起来 -> 新连接过去
```

## 8. 旧连接会怎样

切换后：

```text
新 QQ 连接   -> 新 worker
旧 QQ 连接   -> 旧 worker
```

旧连接不会被立即掐断，supervisor 默认保留：

```text
--drain-seconds 60
```

窗口内：

```text
旧 worker 继续服务已有 WS/在途 HTTP
```

窗口结束：

```text
SIGTERM 旧 worker
```

注意：

```text
旧连接上的代码仍是旧版本
重连后才走新版本
```

这不是“在旧连接上替换代码”，而是“保留旧连接，新连接切新进程”。

## 9. 源码会不会越积越大

会。每个版本目录是完整源码副本，约 6 MB。

v25.6 起，supervisor 在切换时清理，1 小时后再清一次：

```text
默认 NAO_WORKER_KEEP=2
保留 current + 上一个旧版本
切换时清理一次，1 小时后再清理一次，不循环扫描
worker.pid 仍存活的目录不删
```

手动检查：

```bash
python3 scripts/nao_gc.py --base data/workers --keep 2
```

真正删除：

```bash
python3 scripts/nao_gc.py --base data/workers --keep 2 --apply
```

想保留更多回滚点：

```bash
NAO_WORKER_KEEP=3
```

## 10. 什么情况拒绝热更

```text
requires_restart=true   必须停进程
requires_schema=true    必须迁移数据库
schema_version 不一致   必须维护窗口
```

拒绝后：

```text
不启动新 worker
不切 current
旧版本继续服务
写 data/update_status.json
QQ !update 显示原因
```

数据库迁移永远不走热更。

## 11. 完整流程图

```text
1. prepare_worker 复制新代码到 versions/25.6.0
2. supervisor 用 cwd=versions/25.6.0 启动新进程
3. 新进程监听 25.6.0/api.sock、qq.sock
4. supervisor GET /api/health 通过 Unix socket
5. current 原子切到 25.6.0
6. ingress 新请求/新 WS 走 25.6.0
7. 旧 worker 保留 60 秒 drain
8. SIGTERM 旧 worker
9. supervisor 切换时清理，1 小时后再清一次，保留 current + 1 个旧版本
```

## 12. 已知限制

- 不是进程内代码热替换，旧 WS 连接仍跑旧代码直到重连。
- ingress 自身重启仍会短暂释放 3001/27004。
- 新旧 worker 共享数据库，但没有跨进程调度器 leader 锁；drain 窗口内定时任务可能重叠。
- 依赖包是共享环境，升级 Python 包不属于 v25 热更范围。
- 数据库 schema 变更必须停机。
