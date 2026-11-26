# 网关架构合规审计

日期：2026-11-26

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

`BackendClient::Request` 只编码 protobuf；`backend.protocol` 配置校验只允许 `tcp`，HTTP/JSON 回退分支已删除。

## 2. 路由层

已删除：

```cpp
// 旧：任意 /api/* 直接转发
if (url.target.rfind("/api/", 0) == 0) Proxy(...)
```

改为 `gateway/src/router.cpp` 的 `AllowedApiRoute` 显式白名单：

```text
GET    状态 / 信息 / 会话 / 人设 / 存钱 / 周计划 / 插件 / 推送 / 群聊...
POST   聊天 / 命令 / 人设写 / 存钱写 / 基金买入 / 周计划写 / 插件写 / 推送 / 群聊...
PATCH  仅 /api/push/preferences
DELETE 仅 health meals/exercises / push devices / endpoints
动态路由只允许：
  /api/messages/{id}/recall
  /api/tools/{name}/call
  /api/endpoints/{id}/ack
  /api/reminders/{id}/ack
  /api/cron/{id}/run
  /api/savings/fixed/{id}/settle
  /api/savings/funds/{id}/redeem
  /api/plugins/{id}/toggle|approve|reject
```

不在表内的 `/api/*` 网关直接 `404 route_not_found`，不再透传到 worker。

结论：✅ 网关重新掌握路由权。

## 3. typed protobuf v2

新契约：

```text
proto/nao/v1/internal_v2.proto
gateway/src/proto/nao/v1/internal_v2.pb.{h,cc}
bot/server/proto/nao/v1/internal_v2_pb2.py
```

已删除 `JsonPayload.json`：

```proto
message InternalRequest {
  string request_id = 1;
  ApiMethod method = 2;
  string path = 3;
  string http_method = 4;
  string user_id = 5;
  string role = 6;
  google.protobuf.Struct params = 7;
  map<string,string> query = 8;
  map<string,string> path_params = 9;
}
```

结论：✅ 不再传 JSON 字符串；参数/结果使用 protobuf typed tree（Struct/Value）。

## 4. 逐接口 /internal/* 契约

`bot/server/internal_contracts.py` 注册了 66 条内部契约：

```text
/internal/status
/internal/chat
/internal/persona/import
/internal/savings/snapshots
/internal/plugins/{id}/toggle
/internal/cron/{id}/run
...
```

网关 `InternalPathFor` 把公开 `/api/*` 映射到 `/internal/*`；worker 先验证契约、再转发到对应 handler，未登记路径返回 `internal_contract_not_found`。

结论：✅ 逐接口契约已落地。

## 5. 验证

```text
gateway 使用 vcpkg CommonNet + protobuf 编译通过
gateway 启动 /healthz 通过
fake typed backend 往返测试通过：
  /api/login -> /internal/auth/owner
  /api/status -> /internal/status
  protobuf InternalRequest/Response 编解码正常
```

## 6. 仍需说明

```text
当前 params/result 使用 google.protobuf.Struct typed tree，
不是每个接口一个独立 ChatRequest/HistoryRequest 类。
worker 契约验证后仍复用内部 HTTP handler，没有改写业务 handler。
```

如果要做到“每个接口一个独立 message class”，需要继续把 Struct 拆成逐接口 message；当前完成的是 typed protobuf 传输 + 逐接口路径契约。
