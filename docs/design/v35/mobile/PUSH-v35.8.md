# v35.8.4 消息推送（ntfy 自托管）

定位：手机壳装好之后，不靠 WebView 前台轮询，走自托管 ntfy 做离线通知。

```text
Android App
  → UnifiedPush / ntfy 订阅
  → 自托管 ntfy server
  → Hoshinoumi 后端 publish
```

## 通道

```text
ntfy self-hosted，HTTPS
每个设备一个随机 topic（不可猜）
订阅端只读 topic
后端 publish 用独立写 token
不回传消息正文，通知只显示“有新消息 / 有新提醒”
```

## 后端

表：

```text
push_devices(id, user_id, platform, topic, endpoint, created_at, last_seen_at, revoked_at)
push_outbox(id, user_id, device_id, kind, title, body, deep_link, dedupe_key, status, attempts, next_at, created_at)
```

接口：

```text
POST   /api/push/devices        注册设备 topic
DELETE /api/push/devices/{id}   注销设备
GET    /api/push/devices        当前账号设备列表
PATCH  /api/push/preferences    消息 / 提醒 / 免打扰
```

触发：

```text
新私聊消息      → kind=message
提醒到期        → kind=reminder
周计划变更      → kind=weekly（可选）
```

规则：

```text
dedupe_key = kind + 业务 id，防重复
push_outbox 异步发送，失败重试 3 次
通知正文不含 token、金额、私密内容
点击 deep link 回会话 / 提醒
退出登录注销当前设备
```

## Android 接入

```text
优先 UnifiedPush connector；ntfy 作为 distributor
没有 UnifiedPush 时，用 ntfy Android App 订阅同一 topic 作为兜底
App 被系统杀掉后仍要收到；不能只靠 WebView WebSocket
```

## iOS

```text
本轮不做 APNs
iOS 先用 ntfy App 订阅，或后续单独排 APNs 版本
```

## 版本

| 版本 | 内容 | 验收 |
|---|---|---|
| v35.8.4.0 | ntfy 自托管配置 / 设备注册接口 / 通知权限设计 | 能注册、注销设备 |
| v35.8.4.1 | push_outbox / 新消息与提醒触发 / 重试去重 | 后端能发出通知 |
| v35.8.4.2 | Android UnifiedPush/ntfy 接入 / 点击跳转 / 免打扰 / 真机验收 | 后台和杀进程能收到，点击进对应页 |

## 验收

```text
App 在前台：不重复弹系统通知
App 在后台：收到通知
App 被杀：仍能收到（ntfy/UnifiedPush）
点通知：进入对应会话 / 提醒
免打扰：不弹通知，进 App 仍可见
退出登录：设备注销，不再收到
两台设备：互不影响
无 token / 错 topic：401/403，不泄露
```

## 限制

```text
ntfy 不是 FCM，国内 Android 厂商后台策略仍需真机验证
部分 ROM 需要用户允许自启动 / 后台运行
iOS 无 APNs 时不能保证原生离线推送
```
