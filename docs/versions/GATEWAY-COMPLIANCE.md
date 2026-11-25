# 网关架构合规审计

日期：2026-11-25

## 1. 传输层

```text
客户端 → gateway :27005 HTTP
gateway → ingress :27004
  8 字节头 + 4 字节长度 + body
  body = protobuf InternalRequest/InternalResponse
ingress → worker internal.sock
```

结论：✅ 传输层使用 TCP 帧 + protobuf。

`gateway/src/config.h` 默认：

```cpp
std::string backendProtocol = "tcp";
```

`BackendClient::Request` 在 tcp 模式下编码 protobuf；HTTP/JSON 仅回滚模式。

## 2. 路由层

已删除：

```cpp
// 旧：任意 /api/* 直接转发
if (url.target.rfind("/api/", 0) == 0) Proxy(...)
```

改为 `gateway/src/router.cpp` 的 `AllowedApiRoute` 显式白名单：

```text
GET    状态 / 信息 / 会话 / 人设 / 存钱 / 周计划 / 插件 / 推送 / 群聊...
POST   聊天 / 命令 / 人设写 / 存钱写 / 周计划写 / 插件写 / 推送 / 群聊...
PATCH  仅 /api/push/preferences
DELETE 仅 health meals / push devices / endpoints
动态路由只允许：
  /api/messages/{id}/recall
  /api/tools/{name}/call
  /api/endpoints/{id}/ack
  /api/reminders/{id}/ack
  /api/cron/{id}/run
  /api/plugins/{id}/toggle|approve|reject
```

不在表内的 `/api/*` 网关直接 `404 route_not_found`，不再透传到 worker。

结论：✅ 网关重新掌握路由权。

## 3. protobuf 内容契约

当前 `proto/nao/v1/internal.proto`：

```proto
message JsonPayload { string json = 1; }
bytes payload = 5;  // JsonPayload
```

即：

```text
protobuf 外壳 + JSON 字符串
```

不是结构化 `ChatRequest/HistoryRequest/StateRequest` RPC。

`proto/nao/v1/nao.proto` 已定义 History/Chat/State 三个 typed RPC，但未接入网关与 worker。

结论：❌ 仍未完成 typed protobuf。

## 4. 仍未按架构完成的部分

```text
1. 所有 /api/* 的 payload 仍是 JsonPayload.json
2. worker 的 tcp_internal.dispatch 仍然把 protobuf 转成内部 HTTP
3. 网关白名单里的路径仍直接对应 worker 的 /api/*，不是逐接口 /internal/* 契约
4. 新增接口还没有逐一定义 proto message
```

## 5. 已完成与未完成

```text
✅ 删除通用 /api/* 兜底
✅ 显式路由白名单
✅ 动态路由后缀收紧
✅ 网关 JWT / 限流 / 审计
✅ 8+4+body TCP + protobuf 外壳

❌ typed protobuf payload
❌ worker 按 typed message 分发
❌ 逐接口 /internal/* 契约
```

下一步要真正完成第 3 节，需要逐接口定义 proto message 并替换 JsonPayload；这是一次协议迁移，不是补一个路由表。
