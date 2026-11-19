# hoshinoumi-dsh

Hoshinoumi 的 DSH 客户端插件。

## 已完成

```text
DSH 会话标题栏 “nao” 入口
全屏 Hoshinoumi 界面
首次打开检查后端地址，无配置弹配置框
后端地址 / token / target_id 保存到 ~/.dsh/hoshinoumi.json
聊天 POST /api/hoshinoumi/chat → 后端 /api/chat
历史 GET /api/hoshinoumi/history → 后端 /internal/history
命令 POST /api/hoshinoumi/command → 后端 /api/command
```

## 安装

Web profile：

```powershell
dsh plugin --profile web add link:D:\Desktop\Desktop\develop\NapCat+Pyhon\integrations\dsh-plugin
```

桌面版通过 DSH 插件管理安装本地目录（本机已安装到 desktop/web 两个 profile，版本 35.2.24.6（mock 35.2.24.2））。

## 使用

1. 打开 DSH。
2. 会话标题栏点 `nao`。
3. 第一次会弹出“连接 Hoshinoumi”。
4. 填后端地址（默认 `http://127.0.0.1:27004`）、token、target_id。
5. 保存后进入聊天/命令。

## 后端

```text
GET  /healthz
GET  /readyz
GET  /internal/history?target_id=...&limit=...
POST /api/chat       {message,target_id}
POST /api/command    {command,args}
```

插件只在 `~/.dsh/hoshinoumi.json` 存配置；token 不写入日志。

## 开发

```text
index.js   宿主半端：配置、代理、UI 静态页
client.js  浏览器半端：会话标题栏入口 + 全屏 iframe
ui.html    完整前端界面
```

改 `client.js` 由 DSH HMR 热换；改 `index.js` 需要重启 DSH。

## Mock 网关

没有启动真实 Bot 后端时，可以用 mock 网关测试插件：

```powershell
python integrations/dsh-plugin/mock_gateway.py
```

配置：

```text
后端地址  http://127.0.0.1:27005
token     mock-token
主人 QQ   822891053
```

mock 会返回状态、记忆、历史、日志、计划、定时任务、聊天和命令数据；页面上显示的是 mock 数据，不是真实 Bot 数据。
