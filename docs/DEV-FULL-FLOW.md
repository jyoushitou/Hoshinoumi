# 开发机完整启动流程

> 适用：本机真实 gateway + worker + Vue，不使用 Mock，不接 NapCat。

## 0. 目录与端口

```text
D:\Desktop\Desktop\develop\NapCat+Pyhon
27006  Vue 客户端
27005  rec_gateway HTTP
27004  gateway ↔ worker TCP 帧（typed protobuf）
27007  worker 内部 HTTP API（Windows 专用）
```

## 1. 停掉旧进程

```powershell
$ports = 27004,27005,27006,27007
$pids = Get-NetTCPConnection -State Listen -LocalPort $ports -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
$pids | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
```

## 2. 配置 worker

编辑 `config.local.json`：

```json
{
  "master_qq": "10001",
  "ws_port": 3001,
  "api_port": 27004,
  "db": {
    "backend": "sqlite",
    "path": "data/nao.db"
  }
}
```

用 MySQL 时改 `db`：

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

## 3. 初始化数据库（只第一次或换库时）

SQLite：

```powershell
$env:NAO_DB_BACKEND='sqlite'
$env:PYTHONIOENCODING='utf-8'
.venv\Scripts\python.exe scripts\init_db.py --apply
.venv\Scripts\python.exe scripts\migrate.py --apply
```

MySQL 去掉 `NAO_DB_BACKEND` 那一行。

## 4. 配置 API Key

```powershell
.venv\Scripts\python.exe scripts\configure_api.py
```

填写：

```text
DS_API_KEY     DeepSeek 对话 Key
ARK_API_KEY    豆包/方舟视觉 Key
ALAPI_TOKEN    ALAPI 搜图 Token
```

Windows 默认可见输入，支持粘贴；没有的项输入 `-` 清空。

## 5. 环境预检

```powershell
$env:NAO_DB_BACKEND='sqlite'
$env:PYTHONIOENCODING='utf-8'
.venv\Scripts\python.exe checks\env_check.py
```

必须看到：

```text
全部通过，可以启动：python run.py
```

以后改配置、代码、schema 都要重跑这一步。

## 6. 启动 worker

新开一个 PowerShell：

```powershell
cd D:\Desktop\Desktop\develop\NapCat+Pyhon
$env:NAO_DB_BACKEND='sqlite'
$env:PYTHONIOENCODING='utf-8'
.venv\Scripts\python.exe -u run.py
```

看到：

```text
内部 API 已启动: http://127.0.0.1:27007
[T] 内部帧服务已启动: 127.0.0.1:27004
```

## 7. 启动 gateway

新开一个 PowerShell：

```powershell
cd D:\Desktop\Desktop\develop\NapCat+Pyhon
.\gateway\build\Release\rec_gateway.exe --config config\gateway.json
```

看到：

```text
HTTP 监听 127.0.0.1:27005
```

`config/gateway.json` 当前使用：

```json
"auth": {"secret": "dev-owner-secret"}
```

正式使用必须换掉。

## 8. 启动前端

新开一个 PowerShell：

```powershell
cd D:\Desktop\Desktop\develop\NapCat+Pyhon
pnpm --dir integrations/web dev --host 127.0.0.1 --port 27006
```

打开：

```text
http://127.0.0.1:27006
```

## 9. 首次登录

### 方式 A：管理员 token

```powershell
$r = Invoke-RestMethod http://127.0.0.1:27005/api/login -Method Post `
  -Body '{"secret":"dev-owner-secret"}' -ContentType application/json
$r.data.access
```

登录页选 token 模式：

```text
QQ: 10001
token: 上面返回的 access
```

### 方式 B：首次设置密码

```powershell
.venv\Scripts\python.exe -c "from bot.infra import repo_users; repo_users.create_client_user('10001','HSHM-2026')"
```

登录页选“首次设置”：

```text
QQ: 10001
密码: 至少 8 位
setup code: HSHM-2026
```

设置成功后，以后用登录模式 + 密码。

## 10. 验收

```powershell
Invoke-RestMethod http://127.0.0.1:27005/healthz
Invoke-RestMethod http://127.0.0.1:27005/readyz
```

正常：

```json
{"ok":true,"service":"hoshinoumi-gateway","version":"26.4.0"}
{"ok":true,"backend":"backend ok"}
```

真实请求链：

```text
浏览器 27006
  → Vite proxy
  → gateway 27005
  → TCP 帧 27004
  → worker 内部 API 27007
  → 业务 handler
```

## 11. 查看日志

worker 终端直接看；gateway 终端直接看。

如果后台启动：

```powershell
Get-Content data\gateway.stdout.log -Wait
Get-Content data\worker.stdout.log -Wait
```

## 12. 停止

```powershell
$ports = 27004,27005,27006,27007
$pids = Get-NetTCPConnection -State Listen -LocalPort $ports -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
$pids | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
```

## 13. 常见问题

| 现象 | 处理 |
|---|---|
| 环境报告过期 | 重跑 `checks/env_check.py` |
| 已有实例在运行 | 先停 27004 对应进程 |
| 登录 401 | 检查 gateway secret / token 是否过期 |
| Key 改了没生效 | 重启 worker |
| 前端 502 | 确认 gateway 27005 在监听 |
| 网关 503 | 确认 worker 27004 在监听 |
| NapCat 未接 | 不影响自有客户端与 REST API 测试；QQ 消息功能不可用 |
