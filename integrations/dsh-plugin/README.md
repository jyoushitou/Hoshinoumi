# hoshinoumi-dsh

Hoshinoumi 的 DSH 客户端插件。

## 版本

```text
插件            35.2.25.1
Mock 网关       35.2.25.0
后端 schema     35
DSH             0.2.2-rc.1 已验证
```

## 已完成

```text
输入框右侧 “nao” 入口（不再只放在会话标题栏）
全屏 Hoshinoumi 界面，ESC / 右上角 × 关闭
后端地址 / token / target_id 保存到 ~/.dsh/hoshinoumi.json
保存配置后自动测试连接

聊天 / 历史 / 命令 / 定时任务 / 运行日志 / 记忆
关系页：owner 可看所有目标；普通用户只能看自己
人设页：读取 personas/*；JSON 导入 / 导出 / 激活
存钱页：账户/流水、CSV/JSON 导入、记一笔、关联/新建事件、AI 可见开关
存钱页：DeepSeek API 余额
周计划表：按周查看、点格子录入/删除、教务 HTML 导入
```

## 入口

1. 打开 DSH。
2. 打开任意会话或首页。
3. 点输入框右侧的 `nao`。
4. 第一次会弹“连接 Hoshinoumi”。

配置：

```text
后端地址 真实后端 http://127.0.0.1:27004
         mock     http://127.0.0.1:27005
token    真实后端 API token / mock-token
target_id 主人 QQ
```

## 安装

Web / 本地 profile：

```powershell
dsh plugin --profile web add link:D:\Desktop\Desktop\develop\NapCat+Pyhon\integrations\dsh-plugin
```

桌面版可以用 DSH 插件管理安装本地目录，或把本目录文件覆盖到：

```text
C:\Users\<你>\.dsh\profiles\desktop\node_modules\hoshinoumi-dsh
```

覆盖安装不会改 `dsh.profile.bundles`。

## 后端迁移

插件后端已经用到 **schema 35**，正式启动 Hoshinoumi 前必须跑：

```powershell
.venv\Scripts\python.exe scripts\migrate.py --apply
```

否则正式后端会因 `schema_version` 不匹配拒绝启动。

## 后端接口

插件宿主代理：

```text
GET  /api/hoshinoumi/health
GET  /api/hoshinoumi/config
POST /api/hoshinoumi/test
GET  /api/hoshinoumi/ui
POST /api/hoshinoumi/chat
GET  /api/hoshinoumi/history
POST /api/hoshinoumi/command
GET  /api/hoshinoumi/status
GET  /api/hoshinoumi/memory
GET  /api/hoshinoumi/logs
GET  /api/hoshinoumi/plan
GET  /api/hoshinoumi/cron
GET  /api/hoshinoumi/persona
GET  /api/hoshinoumi/persona/export
POST /api/hoshinoumi/persona/import
POST /api/hoshinoumi/persona/activate
GET  /api/hoshinoumi/savings
GET  /api/hoshinoumi/savings/events
POST /api/hoshinoumi/savings/import
POST /api/hoshinoumi/savings/entries
GET  /api/hoshinoumi/weekly-plan
POST /api/hoshinoumi/weekly-plan
POST /api/hoshinoumi/weekly-plan/import
GET  /api/hoshinoumi/balance
GET  /api/hoshinoumi/relation
```

真实后端对应：

```text
/api/persona
/api/savings
/api/savings/entries
/api/savings/events
/api/weekly-plan
/api/balance
/api/relation
```

## 权限

```text
关系页：
  owner         可查询任意 target 的关系
  普通用户      服务端强制只能看自己
  普通用户身份  由网关传 X-User-Id
```

DSH 本机插件默认使用 owner token，所以桌面端看到的是全部目标。

## Mock 网关

没有真实后端时：

```powershell
python integrations/dsh-plugin/mock_gateway.py --port 27005 --token mock-token
```

配置：

```text
后端地址  http://127.0.0.1:27005
token     mock-token
主人 QQ   822891053
```

Mock 支持：

```text
状态 / 记忆 / 历史 / 日志 / 计划 / 定时任务
聊天 / 命令
人设卡
存钱 / 存钱导入 / 记一笔 / 关联事件
周计划表 / 教务 HTML 导入
API 余额
关系（owner 与其他 target 不同）
```

Mock 数据在内存里，重启后恢复初始值；页面会明确标记 mock 来源。

## 开发

```text
index.js   宿主半端：配置、代理、UI 静态页
client.js  浏览器半端：输入框右侧 nao 入口 + 全屏 iframe
ui.html    完整前端界面
```

改 `client.js` / `ui.html` 后重新打开 `nao`；改 `index.js` 需要重启 DSH。

一个次次版本一个提交；页面/交互修订走第四位版本。
