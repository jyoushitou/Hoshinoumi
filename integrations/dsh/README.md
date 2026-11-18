# DSH 工具桥

v35.2.0 只读前置。

```text
GET  /api/tools
POST /api/tools/<name>/call
```

仅开放：

```text
recall
search_images
```

不开放：

```text
remember
agenda_add
```

鉴权：`Authorization: Bearer <API_TOKEN>`。

清单：`integrations/dsh/manifest.json`。

本机服务地址：`http://127.0.0.1:27004`（worker 模式走 Unix socket 时由网关/本机服务转发）。
