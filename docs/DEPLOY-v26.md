# v26 部署与回滚（8+4+body TCP / protobuf）

> 后端：v26.6.3  
> 网关：v26.4.0（`backend.protocol=tcp`）  
> 数据库 schema：29，不需要迁移  
> 外部端口：gateway `27005` HTTP；backend `3001` NapCat WS + `27004` 内部 TCP

## 1. 边界

```text
NapCat ──WS 3001──> backend
外部客户端 ──HTTP 27005──> gateway ──TCP 27004──> backend
```

v26 起 backend 不再在 27004 提供 HTTP。旧的 `nao-ingress` 会占用 27004，部署前必须停。

## 2. 停 v25 ingress

```bash
screen -ls
```

找到 ingress screen，进入后：

```text
Ctrl-C
```

确认 27004 已释放：

```bash
ss -lntp | grep -E ':27004|:3001|:27005'
```

## 3. 更新代码

```bash
cd ~/Hoshinoumi

git bundle verify Release/REC-v26.6.3.bundle
git fetch Release/REC-v26.6.3.bundle main:refs/remotes/bundle/main
git merge --ff-only refs/remotes/bundle/main

grep 'VERSION =' bot/core/version.py
# 26.6.2
```

环境：

```bash
set -a
. ./.env
set +a

python3 checks/env_check.py
```

## 4. 启动 backend（直连 3001/27004）

v26 由 backend 自己绑定 3001/27004，不再走 ingress / supervisor 蓝绿。

```bash
screen -S bot26

cd ~/Hoshinoumi
set -a
. ./.env
set +a

NAO_INTERNAL_TCP=1 python3 -u run.py
```

`Ctrl-A D` detach。

确认：

```bash
ss -lntp | grep -E ':3001|:27004'
python3 scripts/nao_tcp_ping.py
```

预期：

```text
type=2 status=200 body={'ok': True, 'status': 'ok'}
```

## 5. 启动网关 v26.4.0

网关配置：

```json
{
  "listen": {"host": "127.0.0.1", "port": 27005},
  "backend": {
    "protocol": "tcp",
    "tcp_host": "127.0.0.1",
    "tcp_port": 27004,
    "timeout_ms": 5000,
    "startup_wait": true
  }
}
```

重建 / 重启 gateway 容器：

```bash
docker compose build gateway
docker compose up -d gateway
docker logs --tail 50 hoshinoumi-gateway
```

## 6. 验收

```bash
curl -s http://127.0.0.1:27005/healthz
curl -s http://127.0.0.1:27005/readyz
curl -s http://127.0.0.1:27005/api/status \
  -H "Authorization: Bearer $TOKEN"
```

QQ：

```text
!version
!ping
!cron
```

自然语言：

```text
提醒我过30min吃药
```

应：

```text
好，... 提醒你吃药
标准命令：!cron once ... 吃药
```

并且 `!cron` 里能看到新任务。

## 7. 回滚

```text
1. 停 bot26
2. 启动 v25 ingress + v25 worker
3. 网关 config backend.protocol 改回 http
4. 重启旧网关
```

v26 的 protobuf/TCP 不向后兼容；回滚必须同时回滚网关和后端。

## 8. 已知限制

- v26.0 的 WS token 已实现（可选 `NAO_WS_TOKEN`）；`/internal` 独立 secret 仍未做，靠 loopback 边界。
- 27004 TCP 目前一请求一连接，未做连接池；后续可加。
- WS token 开启后 NapCat URL 要带 `?token=...`；不配置则保持旧行为。
- v26 直连 3001/27004 后，v25 的蓝绿热更新不再适用；热更新方案需要 v27 再设计。
