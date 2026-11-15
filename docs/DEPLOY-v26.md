# v26 部署与热更新（8+4+body TCP / protobuf）

> 后端：v26.7.1  
> 网关：v26.4.0（`backend.protocol=tcp`）  
> 数据库 schema：29，不需要迁移  
> 对外端口：ingress `3001` WS + `27004` TCP；gateway `27005` HTTP

## 1. 边界

```text
NapCat ──WS 3001──> ingress ──unix qq.sock──> worker
gateway ──TCP 27004──> ingress ──unix internal.sock──> worker
```

v26 没有拿掉 ingress：

- ingress 继续持有 3001/27004，负责蓝绿切流。
- 27004 从 HTTP 改成 **8+4+body TCP 帧的 L4 透传**。
- worker 在 Unix socket `internal.sock` 上接帧。
- 新连接按 `current` 解析；已有连接留在旧 worker，drain 后退出。
- gateway 完全不感知蓝绿，只连 `127.0.0.1:27004`。

## 2. 升级前的 v25.7 状态

当前 v25.7 的 ingress 是 HTTP 模式，不能直接接 TCP 帧。升级时需要重启一次 ingress，加载 `--protocol tcp`。

worker 仍由 supervisor 启动，保留：

```text
data/workers/current
data/workers/versions/<version>
```

## 3. 更新代码

```bash
cd ~/Hoshinoumi

git bundle verify Release/REC-v26.7.1.bundle
git fetch Release/REC-v26.7.1.bundle main:refs/remotes/bundle/main
git merge --ff-only refs/remotes/bundle/main

grep 'VERSION =' bot/core/version.py
# 26.7.0
```

环境检查：

```bash
set -a
. ./.env
set +a

python3 checks/env_check.py
```

## 4. 停旧 ingress / worker

```bash
screen -ls
ps -ef | grep -E '[b]ot.ingress|[r]un.py'
```

先停 ingress（第一次 Ctrl-C 优雅，第二次强制）：

```text
screen -r <ingress>
Ctrl-C
```

再停 worker：

```bash
pkill -f 'run.py'
```

确认 3001/27004 已释放：

```bash
ss -lntp | grep -E ':3001|:27004'
```

27005 可以保持运行。

## 5. 启动 v26 ingress（TCP 模式）

```bash
screen -S ingress-v267

cd ~/Hoshinoumi
set -a
. ./.env
set +a

NAO_INGRESS_PROTOCOL=tcp python3 -m bot.ingress \
  --worker-dir data/workers \
  --http-host 127.0.0.1 \
  --ws-host 0.0.0.0 \
  --http-port 27004 \
  --ws-port 3001 \
  --protocol tcp
```

`Ctrl-A D` detach。

应看到：

```text
[ingress] TCP 127.0.0.1:27004 WS 0.0.0.0:3001 -> data/workers
```

注意：此时 27004 是 TCP，不是 HTTP，`curl 27004` 会失败，这是正常的。

## 6. 准备并启动 26.7 worker

```bash
cd ~/Hoshinoumi

set -a
. ./.env
set +a

python3 scripts/prepare_worker.py --version 26.7.0

pkill -f 'run.py' 2>/dev/null
: > data/workers/versions/26.7.0/worker.log

python3 scripts/nao_supervisor.py \
  --base data/workers \
  --version 26.7.0 \
  --worker-cmd "python3 -u run.py" \
  --timeout 90 \
  --drain-seconds 60
```

supervisor 会注入：

```text
NAO_WORKER_MODE=1
NAO_WORKER_VERSION=26.7.0
NAO_INTERNAL_TCP=1
```

worker 启动：

```text
[TCP] 内部帧服务已启动: unix:.../26.7.0/internal.sock
QQ worker 已启动: unix:.../qq.sock
```

## 7. 验证 TCP 链路

```bash
cd ~/Hoshinoumi
python3 scripts/nao_tcp_ping.py
```

应返回：

```text
type=2 status=200 body={'ok': True, 'status': 'ok'}
```

这个探活会经过：

```text
scripts/nao_tcp_ping.py -> ingress 27004 TCP -> current worker internal.sock
```

## 8. 网关

网关 config：

```json
{
  "backend": {
    "protocol": "tcp",
    "tcp_host": "127.0.0.1",
    "tcp_port": 27004
  }
}
```

重建 / 重启：

```bash
docker compose build gateway
docker compose up -d gateway
docker logs --tail 100 hoshinoumi-gateway
```

验证：

```bash
curl -s http://127.0.0.1:27005/healthz
curl -s http://127.0.0.1:27005/readyz
```

## 9. 热更新（v26 仍支持）

后续升级只换 worker 版本，ingress 不动：

```bash
python3 scripts/prepare_worker.py --version 26.7.1
python3 scripts/nao_supervisor.py \
  --base data/workers \
  --version 26.7.1 \
  --worker-cmd "python3 -u run.py" \
  --timeout 90 \
  --drain-seconds 60
```

行为：

```text
新 worker 起在 26.7.1/internal.sock
health 通过
current 切到 26.7.1
ingress 新 TCP/WS 连接走新 worker
旧连接留在 26.7.0，drain 60s 后退出
```

网关不重启，NapCat 新连接自动落到新版本。

## 10. 回滚

```text
1. supervisor 切回旧版本目录
2. 或手动 ln -sfn data/workers/versions/25.7.0 data/workers/current
3. ingress 保持 --protocol tcp
```

回滚 v25 HTTP 协议才需要同时：

```text
停 v26 ingress
启 v25 ingress（--protocol http）
网关 config 改 protocol=http
```

## 11. 验收

```bash
python3 scripts/nao_tcp_ping.py
curl -s http://127.0.0.1:27005/readyz
```

QQ：

```text
!version
!ping
!cron
提醒我过30min吃药
! corn
```

应：

```text
v26.7.1
标准命令：!cron once ... 吃药
你是不是想用 !cron？
```
