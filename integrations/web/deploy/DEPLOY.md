# Hoshinoumi Web 生产部署（nginx）

## 1. 构建

```bash
cd integrations/web
pnpm install
pnpm build
# 产物：integrations/web/dist
```

## 2. 放置静态文件

```bash
sudo mkdir -p /opt/hoshinoumi/web
sudo rsync -a --delete integrations/web/dist/ /opt/hoshinoumi/web/dist/
```

## 3. 安装配置

```bash
sudo cp integrations/web/deploy/nginx.conf /etc/nginx/conf.d/hoshinoumi-web.conf
sudo nginx -t
sudo systemctl reload nginx
```

## 4. 后端（无公网）→ frpc → 公网前端

后端启动 gateway：

```bash
# gateway 监听 127.0.0.1:27005
curl -s http://127.0.0.1:27005/healthz
```

后端用 `deploy/frpc.toml` 主动连公网前端，把 gateway 27005 映射到前端 27015：

```bash
frpc -c deploy/frpc.toml
```

公网前端启动 frps：

```bash
frps -c deploy/frps.toml
```

nginx 的 `/api` 指向：

```text
127.0.0.1:27015
```

## 5. 访问

```text
http://公网前端:27006
```



## 6. 网络边界

```text
后端无公网：只主动出站 frpc
公网前端：frps 7000 + nginx 27006
frpc remotePort 27015 只允许本机 nginx 访问
公网防火墙：只放行 27006；7000 仅允许后端 IP
27004 / 27005 / internal 不对公网
```

## 7. 边界

```text
公网只开 27006
27004/27005 只监听本机
/internal 不暴露
/api 不缓存
上传上限 30m
SSE/WS 不缓冲
```

## 8. 客户端连接路径

```text
Web 浏览器
  → https://公网前端:27006
  → nginx /api → 127.0.0.1:27015 → frpc → gateway 27005

公网 VS Code / DSH 插件
  → https://公网前端:27006
  → nginx /api（同一路径，Bearer token）
  → 不直连 27015，更不直连 27005

本地插件（和 backend 同机）
  → http://127.0.0.1:27005 直连即可
```

插件配置的 base_url：

```text
公网：https://公网前端:27006
本地：http://127.0.0.1:27005
```

不要把 frpc 的 27015 或后端 27005 暴露给公网客户端。

## 9. HTTPS

有域名后加 443：

```text
listen 443 ssl http2;
ssl_certificate ...;
ssl_certificate_key ...;
```

不要在没有 TLS 时把网关直接暴露公网。
