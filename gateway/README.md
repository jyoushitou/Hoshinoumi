# Hoshinoumi（REC）Gateway v22

基于用户自己的 **NetWorkCommunication / CommonNet**（Boost.Asio + Boost.Beast）实现的 C++ 网关。

- HTTP 入口：`Net::Server::HttpServer`
- 出站探活/代理：`Net::Client::Http::HttpClient`
- 依赖：vcpkg overlay ports（`commonnet` + `utils`）
- 部署：Docker 镜像，部署机不编译

## 当前范围（v22，试运行）

| 有 | 没有（后续） |
|---|---|
| `/healthz` / `/readyz` | 多用户隔离（v23） |
| `/api/login` / `/api/refresh` / JWT | 内置 TLS（用 tls_proxy.py 终止） |
| `/api/*` Bearer 鉴权 | 分布式限流（当前进程内） |
| 每 IP 60/min 令牌桶，429 | |
| `gateway_log` 审计（owner/path/status/耗时/IP） | |
| `!gw` 观测 | |
| TLS 终止代理 `gateway/tls_proxy.py` | |
| 压测 `scripts/gateway_load_test.py` | |
| Dockerfile 多阶段构建 | |

## v21 登录

```bash
curl -s -X POST http://127.0.0.1:27005/api/login \
  -H 'Content-Type: application/json' \
  -d '{"secret":"<NAO_GATEWAY_OWNER_SECRET>"}'
```

返回 `data.access` 后：

```bash
curl -s http://127.0.0.1:27005/api/state \
  -H "Authorization: Bearer <access>"
```

## v22 限流 / 审计 / TLS

- 同一 IP 每分钟 60 次；超限 429，带 `Retry-After`。
- 每次 `/api/*` 异步写 `gateway_log`；不记 token/secret/body。
- TLS 由独立代理终止：

```bash
python3 gateway/tls_proxy.py \
  --cert /etc/nao/fullchain.pem \
  --key  /etc/nao/privkey.pem \
  --listen 0.0.0.0:27443 \
  --backend 127.0.0.1:27005
```

- 证书不存在时不要启动代理；本地开发可继续 HTTP。
- 回滚：停 TLS 代理和网关，插件仍可直连 `127.0.0.1:27004`。

## 启动等待（v20.6）

网关先启动、后端还没起来时：

- `/healthz` 立即 200
- `/readyz` 返回 503
- 每 30 秒探测一次，一轮最多 5 次；5 次都失败后网关继续运行
- 后端起来后再请求 `/readyz` 会补一次探测，成功后返回 200

配置：

```json
"backend": {
  "startup_wait": true,
  "startup_retry_interval_sec": 30,
  "startup_max_attempts": 5
}
```

## 本机构建

```bash
# Windows（MinGW 示例）
vcpkg install utils commonnet \
  --triplet x64-mingw-static \
  --overlay-ports=third_party/NetWorkCommunication/ports \
  --overlay-ports=third_party/Utils/ports

cmake -S gateway -B gateway/build -G "MinGW Makefiles" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_TOOLCHAIN_FILE=D:/vcpkg/scripts/buildsystems/vcpkg.cmake \
  -DVCPKG_TARGET_TRIPLET=x64-mingw-static \
  -DVCPKG_MANIFEST_MODE=OFF

cmake --build gateway/build -j
```

Linux 下把 triplet 换成 `x64-linux`，生成器用 `Ninja`。

## 配置

```bash
python3 scripts/configure.py
# 写入 config/gateway.json
```

启动：

```bash
./gateway/build/rec_gateway --config config/gateway.json

curl -s http://127.0.0.1:27005/healthz
curl -s http://127.0.0.1:27005/readyz
```

## Docker（推荐部署方式）

```bash
docker build -f gateway/Dockerfile -t hoshinoumi-gateway:20.5.0 .
# 国内网络拉不到 Docker Hub 时：
# docker build --build-arg BASE_IMAGE=docker.m.daocloud.io/library/ubuntu:24.04 \
#   -f gateway/Dockerfile -t hoshinoumi-gateway:20.5.0 .

# 导出给部署机
python3 scripts/build_gateway.py --version 20.5.0
# release/REC-v20.5.0-docker.tar.gz

# 部署机
docker load -i REC-v20.5.0-docker.tar.gz
mkdir -p config
cp gateway/config.example.json config/gateway.json
docker run -d --name hoshinoumi-gateway \
  --network host \
  -v "$PWD/config:/app/config:ro" \
  hoshinoumi-gateway:20.5.0
```

> 构建机访问不了 GitHub / vcpkg 时，用离线版（系统 Boost/OpenSSL，不走 vcpkg）：
>
> ```bash
> docker build --build-arg BASE_IMAGE=docker.m.daocloud.io/library/ubuntu:24.04 \
>   -f gateway/Dockerfile.offline -t hoshinoumi-gateway:20.5.0-offline .
>
> python3 scripts/build_gateway.py --version 20.5.0 --offline \
>   --base-image docker.m.daocloud.io/library/ubuntu:24.04
> ```

> v20 后端只允许 `127.0.0.1` / `localhost`；容器里用 `--network host` 让
> `127.0.0.1:27004` 指向宿主机后端（v19 API 默认端口）。不要给后端配公网地址。

