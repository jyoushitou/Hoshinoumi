# ingress / 蓝绿 Linux 集成测试

这是 v25.2–v25.3 的 Docker Linux 集成夹具，不会进入运行时。

## 运行

```bash
docker build -f ingress_test/Dockerfile -t nao-ingress-test:latest .
docker run --rm nao-ingress-test:latest
```

`Dockerfile` 默认跑 `bluegreen_integration.py`：

- 假 worker 绑定 Unix socket
- ingress 绑定 18004/18001
- 验证 HTTP `/api/health`、`POST /echo`
- 验证 WebSocket echo
- 用 supervisor 从 25.4.0 切到 25.5.0
- 验证切换前 WS 在 drain 窗口内仍能 echo

基础 ingress 测试：

```bash
docker run --rm nao-ingress-test:latest python ingress_integration.py
```

## 注意

- 镜像基于 `docker.m.daocloud.io/library/python:3.13-slim`。
- 依赖从清华 PyPI 镜像安装。
- 仅用于验证，不含真实 NapCat / 真实 bot worker。
