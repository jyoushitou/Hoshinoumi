# 开发机真实后端配置

日期：2026-11-25

## 端口

```text
27006  Vue 客户端（Vite）
27005  rec_gateway HTTP
27004  gateway ↔ worker TCP 帧（typed protobuf）
27007  worker 内部 HTTP API（Windows 替代 Unix socket）
3001   QQ WebSocket（当前未接 NapCat，可不用）
```

## 1. worker 配置

文件：`config.local.json`

当前 SQLite 配置：

```json
{
  "master_qq": "10001",
  "ws_port": 3001,
  "api_port": 27004,
  "db": {
    "backend": "sqlite",
    "path": "data/nao.db",
    "host": "127.0.0.1",
    "port": 3306,
    "user": "unused",
    "password": "unused",
    "name": "unused"
  }
}
```

切 MySQL 时改成：

```json
"db": {
  "backend": "mysql",
  "host": "127.0.0.1",
  "port": 3306,
  "user": "你的用户",
  "password": "你的密码",
  "name": "TomoriNaoBotData"
}
```

改完后初始化：

```powershell
$env:NAO_DB_BACKEND='sqlite'   # MySQL 时去掉这一行
$env:PYTHONIOENCODING='utf-8'
.venv\Scripts\python.exe scripts\init_db.py --apply
.venv\Scripts\python.exe scripts\migrate.py --apply
.venv\Scripts\python.exe checks\env_check.py
```

## 2. API Key

```powershell
.venv\Scripts\python.exe scripts\configure_api.py
```

写入：

```text
DS_API_KEY        DeepSeek 对话
ARK_API_KEY       豆包/方舟视觉
ALAPI_TOKEN       ALAPI 搜图（可空）
```

当前本地是占位值，只够启动和测页面/网关；聊天识图要换真实 Key。

## 3. 网关配置

文件：`config/gateway.json`（已 gitignore）

```json
{
  "listen": {"host": "127.0.0.1", "port": 27005},
  "backend": {
    "protocol": "tcp",
    "tcp_host": "127.0.0.1",
    "tcp_port": 27004,
    "startup_wait": false
  },
  "auth": {"secret": "dev-owner-secret"}
}
```

生产必须改掉 `dev-owner-secret`，并限制文件权限。

## 4. 启动顺序

```powershell
# 1) worker
$env:PYTHONIOENCODING='utf-8'
$env:NAO_DB_BACKEND='sqlite'
.venv\Scripts\python.exe -u run.py

# 2) gateway
.\gateway\build\Release\rec_gateway.exe --config config\gateway.json

# 3) 前端
pnpm --dir integrations/web dev --host 127.0.0.1 --port 27006
```

## 5. 登录

### 管理员 token

```powershell
$r = Invoke-RestMethod http://127.0.0.1:27005/api/login -Method Post `
  -Body '{"secret":"dev-owner-secret"}' -ContentType application/json
$r.data.access
```

客户端登录页选 token 模式，QQ `10001`，粘贴 access。

### 首次设置密码

先给 owner 生成 setup code：

```powershell
.venv\Scripts\python.exe -c "from bot.infra import repo_users; repo_users.create_client_user('10001','HSHM-2026')"
```

客户端登录页选“首次设置”：

```text
QQ: 10001
密码: 至少 8 位
setup code: HSHM-2026
```

### 邀请码注册新用户

需要 `invites` 表里有可用邀请码，然后登录页填邀请码注册。

## 6. 验证

```powershell
Invoke-RestMethod http://127.0.0.1:27005/healthz
Invoke-RestMethod http://127.0.0.1:27005/readyz
```

正常：

```json
{"ok":true,"service":"hoshinoumi-gateway","version":"26.4.0"}
{"ok":true,"backend":"backend ok"}
```

## 7. 日志

```powershell
Get-Content data\gateway.stdout.log -Wait
Get-Content data\worker.stdout.log -Wait
```

## 8. 停止

```powershell
Get-Process rec_gateway,python -ErrorAction SilentlyContinue | Stop-Process -Force
```

只停 gateway：

```powershell
Get-Process rec_gateway | Stop-Process -Force
```
