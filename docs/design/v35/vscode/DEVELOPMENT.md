# Hoshinoumi for VS Code · 开发文档

## 1. 定位

一个 VS Code 扩展，在**源代码管理（SCM）整栏**中显示 Hoshinoumi 客户端。

- 不占代码编辑区
- 不打开额外 WebviewPanel
- 不做独立命令中心
- 侧栏宽度约 300–320px
- 视觉使用 VS Code 主题变量（Dark+ / Light+ 自动适配）
- 所有数据来自 Hoshinoumi 后端；没有后端时显示未连接，不伪造数据

> VS Code API 不允许扩展替换内置的 Source Control 视图。实现上使用一个 SCM 风格的独立 Activity Bar 容器，整栏显示 Hoshinoumi；视觉效果与设计稿一致，但不覆盖 VS Code 自带的“更改/存储库/图表”。

## 2. 模块拆分

### 2.1 扩展宿主

文件：`integrations/vscode-plugin/extension.js`

职责：

- 读写配置（`context.globalState`）
- 保存 token，不暴露给 Webview
- 代理 HTTP 请求到 Hoshinoumi
- 统一错误、超时、状态码
- 注册 SCM 侧栏 View
- 注册命令

不负责：

- 页面渲染
- 业务文案
- 直接操作数据库

### 2.2 侧栏壳

文件：`integrations/vscode-plugin/media/sidebar.html`

职责：

- SCM 整栏布局
- Hoshinoumi 标题、连接状态、五组板块导航；无“源代码管理/main*”横条、无折叠条
- 板块导航
- 页面容器
- 输入框/发送按钮
- VS Code 主题变量

### 2.3 业务板块

| 板块 | 主要接口 | 内容 |
|---|---|---|
| 主页 | `status` / 各模块摘要 | 入口、状态、功能总览 |
| 聊天 | `history` / `chat` | 最近消息、发送、连接状态 |
| 记忆 | `/api/memory` | 目标列表、条数、最后一条 |
| 存钱 | `/api/savings`、`/api/balance`、`/api/savings/entries` | 总余额、账户、API 余额、记一笔 |
| 周计划 | `/api/weekly-plan`、`/api/weekly-plan/import` | 周次、课程、导入 HTML |
| 信息 | `/api/status`、`/api/plan`、`/api/logs` | 状态、数据库、学习计划 |
| 命令 | `/api/command` | 51 个命令、输入框、执行、结果区 |
| 定时任务 | `/internal/cron` | 任务列表、启用状态、立即运行 |
| 运行日志 | `/api/logs` | 最近日志、筛选、错误 |
| 人设 | `/api/persona` | 卡片、文件清单、摘要、导入/导出 |
| 关系 | `/api/relation` | 亲密度、档位、最近变化 |
| 设置 | `config` / `test` | 后端地址、token、主人 QQ、连接测试 |

每个板块必须：

- 有加载态
- 有错误态
- 有未配置态
- 不显示上一板块的旧数据
- 切换板块时保留滚动位置（可选）

### 2.4 Webview 通信

Webview 不直接 fetch。统一走：

```text
Webview postMessage
→ extension host handleRequest
→ Hoshinoumi HTTP
→ postMessage response
```

消息：

```json
{ "type": "hoshinoumi:request", "id": 1, "path": "/api/hoshinoumi/...", "method": "GET", "body": null }
```

返回：

```json
{ "type": "hoshinoumi:response", "id": 1, "status": 200, "data": {} }
```

规则：

- 30 秒超时
- 非 2xx 返回错误，不抛到 Webview 外
- token 只在宿主拼接 Authorization
- 配置保存后必须实际请求 `/healthz` + `/readyz` 才显示已连接

## 3. 页面结构

```text
SCM 侧栏（整栏 Hoshinoumi）
├─ 标题 Hoshinoumi · 状态
├─ 对话
│  ├─ 主页
│  └─ 聊天
├─ 数据
│  ├─ 记忆
│  ├─ 存钱
│  └─ 关系
├─ 计划
│  └─ 周计划
├─ 信息
│  ├─ 信息
│  ├─ 命令
│  ├─ 定时任务
│  └─ 运行日志
└─ 系统
   ├─ 人设
   └─ 设置
```

聊天板块底部固定输入框；其他板块隐藏输入框。

## 4. 版本拆分

| 版本 | 内容 | 验收 |
|---|---|---|
| v35.4.0.0 | VS Code 扩展骨架、SCM 整栏 View、配置代理 | 侧栏出现 Hoshinoumi，能保存/测试连接 |
| v35.4.1.0 | 主页 + 聊天板块：历史、发送、连接状态 | 能在侧栏和 nao 聊天 |
| v35.4.2.0 | 记忆 + 关系板块 | 能看目标、记忆摘要、关系档位/事件 |
| v35.4.3.0 | 存钱板块：总览、API 余额、记一笔、导入 | 能看余额并写入一笔 |
| v35.4.4.0 | 周计划板块：周次、课程、HTML 导入 | 能按周查看和导入 |
| v35.4.5.0 | 信息 + 命令 + 定时任务 + 运行日志 | DSH 功能对齐 |
| v35.4.6.0 | 人设 + 设置板块 | 能看人设卡、改配置 |
| v35.4.7.0 | 打包、安装、主题/窄栏适配、验收 | VSIX 可安装，Dark+/Light+ 正常 |

## 5. 验收标准

- 侧栏宽度 300px 时不横向滚动
- 切换板块不闪烁、不残留旧数据
- token 不出现在 DOM、日志、错误文本
- 后端未启动时显示“未连接”，不显示假数据
- 关系仅 owner 可查全部；普通用户只显示自己
- 周计划表第 3 周导入你给的教务 HTML 能显示命中课程
- 存钱新增后总余额刷新
- 命令页可输入命令并显示后端结果
- 关闭/重开 VS Code 后配置保留

## 6. 文件结构

```text
integrations/vscode-plugin/
├─ package.json
├─ extension.js
├── media/
│  ├─ sidebar.html       # 当前单文件设计稿
│  └─ nao.svg
├─ README.md
└─ hoshinoumi-vscode.vsix
```

后续拆分：

```text
media/
├─ sidebar.html          # 壳
├─ styles/sidebar.css
├─ bridge.js
└─ panels/
   ├─ chat.js
   ├─ memory.js
   ├─ savings.js
   ├─ weekly.js
   ├─ persona.js
   ├─ relation.js
   └─ settings.js
```
