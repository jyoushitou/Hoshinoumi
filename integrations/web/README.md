# Hoshinoumi Web

v35.5.0.0 Vue 前置 + v35.5.1.0 AppShell 框架。

```bash
pnpm install
pnpm dev      # http://127.0.0.1:27006
pnpm build
pnpm test
pnpm lint
```

环境变量见 `.env.example`；API base 默认同源。页面框架在 v35.5.1.0。

## 生产部署

```text
deploy/nginx.conf
deploy/DEPLOY.md
```

27006 同源：静态 dist + /api、/ws 反代 frpc 映射端口 27015（后端 gateway 27005）。
