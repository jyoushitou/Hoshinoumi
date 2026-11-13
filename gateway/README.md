# Hoshinoumi（REC）Gateway v20

基于用户自己的 **NetWorkCommunication / CommonNet**（Boost.Asio + Boost.Beast）实现的 C++ 网关。

- HTTP 入口：`Net::Server::HttpServer`
- 出站探活/代理：`Net::Client::Http::HttpClient`
- 依赖：vcpkg overlay ports（`commonnet` + `utils`）
- 部署：Docker 镜像，部署机不编译

## v20.0 范围

| 有 | 没有（后续） |
|---|---|
| `/healthz` | 登录 / JWT |
| `/readyz`（探后端 `/api/health`） | 限流 / 审计 |
| `/api/chat` → `/internal/chat` | TLS |
| `/api/history` → `/internal/history` | 多用户隔离（v23） |
| `/api/state` / `/api/cron` / `/api/diary` / `/api/shelf` | |
| 配置向导 `scripts/configure.py` | |
| Dockerfile 多阶段构建 | |

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

curl -s http://127.0.0.1:8080/healthz
curl -s http://127.0.0.1:8080/readyz
```

## Docker（推荐部署方式）

```bash
docker build -f gateway/Dockerfile -t hoshinoumi-gateway:20.0.0 .
# 国内网络拉不到 Docker Hub 时：
# docker build --build-arg BASE_IMAGE=docker.m.daocloud.io/library/ubuntu:24.04 \
#   -f gateway/Dockerfile -t hoshinoumi-gateway:20.0.0 .

# 导出给部署机
python3 scripts/build_gateway.py --version 20.0.0
# release/REC-v20.0.0-docker.tar.gz

# 部署机
docker load -i REC-v20.0.0-docker.tar.gz
mkdir -p config
cp gateway/config.example.json config/gateway.json
docker run -d --name hoshinoumi-gateway \
  --network host \
  -v "$PWD/config:/app/config:ro" \
  hoshinoumi-gateway:20.0.0
```

> 构建机访问不了 GitHub / vcpkg 时，用离线版（系统 Boost/OpenSSL，不走 vcpkg）：
>
> ```bash
> docker build --build-arg BASE_IMAGE=docker.m.daocloud.io/library/ubuntu:24.04 \
>   -f gateway/Dockerfile.offline -t hoshinoumi-gateway:20.0.0-offline .
>
> python3 scripts/build_gateway.py --version 20.0.0 --offline \
>   --base-image docker.m.daocloud.io/library/ubuntu:24.04
> ```

> v20 后端只允许 `127.0.0.1` / `localhost`；容器里用 `--network host` 让
> `127.0.0.1:60908` 指向宿主机后端（v19 API 默认端口）。不要给后端配公网地址。
