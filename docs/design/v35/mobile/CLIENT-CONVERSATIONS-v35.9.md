# 自有客户端会话 ID（v35.9.0.4）

问题：QQ 私聊号、QQ 群号都是数字。如果自有客户端新建群聊直接写数字/随机串，可能和 QQ 群号撞。

规则：

```text
QQ 会话：保持原样，纯数字
自有客户端：统一前缀 h_ + ULID
例如：h_01JC8Z6K4M9QW3T7Y2V5N1P0RS
```

表：

```text
conversations.target_id  存储字符串 ID
conversations.origin     qq / client
```

约束：

```text
自有客户端创建只接受 h_ 开头
QQ 同步只写纯数字 target_id
唯一索引 target_id
正则：^h_[0-9A-HJKMNP-TV-Z]{26}$
不允许把 h_ ID 写进 QQ 群号字段
```

API：

```text
POST /api/client/conversations
{
  "type": "group" | "private",
  "name": "周末计划",
  "members": ["10001"]
}
→ { "target_id": "h_...", "origin": "client" }
```

发送消息继续走现有 target_id，不改 QQ 发送路径。

版本：

```text
v35.9.0.4  h_ ID 规则 / 新建群聊 API / schema
v35.9.0.5  桌面 + 手机新建群聊 UI
```

验收：

```text
QQ 数字群号不受影响
自有客户端群 ID 全部 h_ 开头
同表可共存，不冲突
重复创建不覆盖
非 h_ 的自有客户端创建请求被拒绝
```
