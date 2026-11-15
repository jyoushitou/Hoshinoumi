# 复盘：2026-11-15 上线后“只发上线了，消息全不回复”

> 版本：v27.3.0 现象，v27.3.1/v27.4.1 修复  
> 影响：QQ 连接看起来在线，机器人发了「哼,上线了(叉腰)」，随后 `!ping`、普通消息都不回。  
> 结论：不是 v27 注册表导致的；问题在 WebSocket 连接建立后的上线通知与连接生命周期。

## 1. 现象

```text
22:57  机器人：哼,上线了(叉腰)
22:57  用户：？
22:57  用户：发生了什么事啊
22:57  用户：!ping
       没有任何回复
```

表现像“上线了但失联”。

## 2. 直接原因：三条缺陷叠加

### 2.1 上线配图在 ws.recv() 之前被 await

v27.3.0 的 [bot/chat/handler.py](../bot/chat/handler.py)：

```python
await send_short_reply(MASTER_QQ, notice_text(mode), ws, MASTER_QQ)

img_fp = await fetch_and_save_acg_image()   # ← 在这里等
...
try:
    while True:
        raw = await ws.recv()               # ← 才开始收消息
```

`fetch_and_save_acg_image()` 内部包含：

```text
ALAPI 请求 timeout=10
图片下载 timeout=60
图片处理/打标
```

网络慢时，最多可以阻塞几十秒。阻塞期间 NapCat 发来的 `!ping` 和普通消息都堆在 WebSocket 里，`recv()` 没开始，所以没有任何回复。

这就是“先看到上线了，然后所有消息都不回”的直接原因。

### 2.2 新连接被旧 active_ws_qq 挡住

原来的连接接管逻辑：

```python
if cfg.active_ws_qq and not getattr(cfg.active_ws_qq, "closed", False):
    await ws.close()   # 直接关闭新连接
    return
cfg.active_ws_qq = ws
```

NapCat 重连时，旧 WebSocket 对象可能还没被标记 `closed`，但实际已经半死。于是：

```text
旧连接：看起来还 active，实际收不到消息
新连接：刚建立就被 close
结果：上线通知可能来自旧连接，之后没有任何连接能收消息
```

### 2.3 断线清理是全局的，会误杀新连接任务

连接结束时的清理：

```python
for _t in list(_bg_tasks):
    _t.cancel()
for _t in list(_online_tasks):
    _t.cancel()
```

`_bg_tasks` 是全局集合。旧连接断开时，会把**新连接刚创建的消息任务**一起 cancel。

于是即使新连接已经接上，它的消息处理任务也可能被旧连接的 finally 清掉。

## 3. 为什么是“突然上线了”

触发链通常是：

```text
ingress/worker 切换或网络抖动
→ NapCat 重连
→ 新连接建立 / 旧连接未完全关闭
→ 上线通知发送
→ ACG 图片慢，或旧连接挡住新连接
→ ws.recv() 没有正常接上
→ 所有消息无回复
```

所以用户看到的是“突然上线了”，不是普通启动；它是重连路径。

## 4. 为什么不是 v27 注册表的问题

v27.1–v27.3 只新增：

```text
bot/registry/plugins.py
bot/registry/master.py
bot/registry/manifest.py
```

这些模块没有接进消息主循环，也没有被 bootstrap 调用。  
问题在上线通知和 WebSocket 连接生命周期，属于 chat 链路。

## 5. 修复

### v27.3.1

```text
上线配图转后台任务
不阻塞 ws.recv()
```

### v27.4.1

```text
上线文字 + 配图全部转后台
新连接替换旧连接，不再直接 close 新连接
断线只取消本连接的 _bg_tasks/_online_tasks
```

修复后的顺序：

```text
连接建立
→ 登记新连接（替换旧连接）
→ 上线通知/配图后台
→ 立即进入 ws.recv()
→ 命令和普通消息正常处理
```

## 6. 验证

```text
tests/test_online_nonblocking.py
tests/test_cron_once_cleanup.py
tests/test_dual_write_dialect.py
```

当前：

```text
1120 条测试，0 失败
```

## 7. 防复发规则

1. **接收循环之前不允许 await 可选 I/O。**
   上线通知、配图、欢迎语都必须后台化，并带超时。

2. **重连必须替换旧连接。**
   旧连接 `closed=False` 不能作为“新连接拒绝”的唯一依据。

3. **后台任务按连接归属。**
   禁止全局 `for task in _bg_tasks: task.cancel()`；只取消 `task.ws is 当前连接`。

4. **上线通知必须有端到端回归。**
   测试要覆盖：连接建立 → 上线通知 → 立即 `!ping` → 必须回复。

5. **worker 日志必须能区分：**
   ```text
   QQ上线
   QQ重连：替换旧 WebSocket
   QQ断开
   ```
   否则下次只能靠猜。

## 8. 相关文档

- [v27 开发记录](versions/v27.md)
- [v26 部署与热更新](DEPLOY-v26.md)
- [架构图](ARCHITECTURE.md)
