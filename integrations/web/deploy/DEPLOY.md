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

## 4. 启动 gateway

Web 的 `/api` 转发到 gateway 27005：

```bash
# gateway 按现有部署启动，监听 127.0.0.1:27005
curl -s http://127.0.0.1:27005/healthz
```

## 5. 访问

```text
http://服务器:27006
```

## 6. 边界

```text
公网只开 27006
27004/27005 只监听本机
/internal 不暴露
/api 不缓存
上传上限 30m
SSE/WS 不缓冲
```

## 7. HTTPS

有域名后加 443：

```text
listen 443 ssl http2;
ssl_certificate ...;
ssl_certificate_key ...;
```

不要在没有 TLS 时把网关直接暴露公网。
