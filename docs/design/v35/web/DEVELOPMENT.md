# Hoshinoumi Web · v35.5 开发文档

## 1. 目标

v35.5 只做 **Vue Web 聊天室**：浏览器直接访问，完成登录、会话、历史、发送、实时接收、未读、媒体和离线恢复。

不做：

- 不做全量设置/存钱/周计划页面（v35.7）
- 不做桌面/手机套壳（v35.6）
- 不复刻 DSH 的侧栏布局

## 2. 技术栈

```text
Vue 3 + Vite
Pinia（会话/登录/未读状态）
Vue Router（/login /chat）
EventSource / fetch SSE
CSS Variables（ThemeToken）
```

## 2.2 Vue 前置

已落地：

```text
integrations/web/
  pnpm dev / build / test / lint
  Vue 3 + Vite + TS
  Vue Router + Pinia
  API client + env
  Vitest + Playwright 配置
```

命令：

```bash
cd integrations/web
pnpm install
pnpm dev
pnpm build
pnpm test
pnpm lint
```


```text
Node 20+ / pnpm 9+
Vue 3 + Vite + TypeScript
Vue Router 4 + Pinia
ESLint + Prettier
Vitest + Playwright
API client / env 约定
```

要求：

```text
pnpm dev / build / test 可跑
Mock adapter 与真实 API 同一接口
token 只在客户端存储，不写入仓库
```

## 2.3 页面框架

```text
src/
├─ main.ts
├─ App.vue
├─ router/
├─ stores/
├─ api/            # fetch + SSE + 错误
├─ layouts/        # AppShell / Rail / Side / Context
├─ components/     # 通用卡片/气泡/表单/空态
├─ views/          # chat / home / memory / ...
├─ styles/         # ThemeToken / light / dark
└─ mocks/          # MOCK 数据
```

框架要求：

```text
AppShell 固定四区：rail / side / main / context
导航配置驱动 12 个入口
路由懒加载
统一 loading / empty / error / offline 态
动画开关由 MotionPreset 控制
```

## 2.1 会话列表规则

```text
只列 QQ 私聊 + QQ 群
群名 / 群成员数 / 未读来自后端同步
存钱、记忆、周计划、人设、设置是功能页，只从左侧导航进入
功能页不能当会话显示
```

后端接口（v35.5.12）：

```text
GET /internal/conversations
→ [{type:'private'|'group', id, name, member_count, unread, last_message, updated_at}]
```

## 3.1 全局导航

导航必须对齐 DSH 功能，不是只做聊天：

```text
主页
nao（聊天）
记忆
关系
存钱
周计划表
信息
人设
设置
命令
定时任务
运行日志
```

v35.5 演示先给全部入口和命令页；完整功能页在 v35.7 实现。

## 2.4 页面框架已落地

```text
integrations/web/src/layouts/AppShell.vue
integrations/web/src/components/RailNav.vue
integrations/web/src/components/ConversationList.vue
integrations/web/src/components/ContextPanel.vue
integrations/web/src/views/ChatView.vue
integrations/web/src/views/PageView.vue
```

路由 12 项：home / chat / memory / relation / savings / weekly / info / persona / commands / cron / logs / settings。

开发端口固定：

```text
http://127.0.0.1:27006
```

## 2.5 登录与数据态

- 首次打开无凭据：弹窗填主人 QQ + token
- 后端同源，不填 URL
- 保存前调用 `/healthz` + `/api/status`
- 失败显示错误；未登录/未连接不展示假会话、假消息
- 会话/历史/关系/state 在后续版本接入，接口失败显示提示

## 2.6 不预填 QQ

登录弹窗不预填真实主人 QQ：

```text
QQ 默认空
placeholder 只写“请输入主人 QQ”
演示/文档用 10001 或 <主人QQ> 占位
```

## 2.7 周次规则

```text
周计划周次 = ISO 8601 年周（1–53）
不写死“第 12 周”
进入页面默认当前年周
```

## 3. 布局

```text
┌────┬──────────┬───────────────────────┬────────────┐
│ 导 │ 会话列表 │ 聊天区                │ 上下文     │
│ 航 │ 搜索     │ 消息 / 输入 / 媒体     │ 人设/记忆  │
└────┴──────────┴───────────────────────┴────────────┘
```

- 桌面：四列，上下文可折叠
- 窄屏：隐藏上下文和会话列表
- 动画：默认关闭；由 `MotionPreset` 控制

## 3.2 聊天内搜索

- 顶部按钮展开搜索条
- 只搜当前会话
- 命中高亮
- ↑ / ↓ 或 Enter 跳转
- Esc / × 关闭
- 演示用 DOM 搜索；最终可切到后端全文检索

## 3.3 主页

主页是功能入口，不是空统计页：

```text
聊天 / 记忆 / 存钱 / 信息 / 人设 / 设置
命令 / 定时任务 / 运行日志 / 插件
```

共 10 个模块卡片，点击进入对应页面。

## 3.4 存钱页

```text
总余额 / 本月收入 / 本月支出 / 目标进度
记一笔：金额、账户、类型、备注、AI 可见
导入：CSV（account,kind,amount,date,note）
最近流水
```

演示数据为 MOCK；最终走 `/api/savings`、`/api/savings/entries`、`/api/savings/import`。

## 3.6 信息页

```text
版本 / schema / 表数量 / 命令数量
运行：地址、延迟、运行时长、API 余额
数据库：引擎、表数、记忆/事件、日志
日志：最近 24h、WARN、失败
学习计划 / 阅读 / 多端在线状态
```

演示数据为 MOCK；最终走 `/api/status`、`/api/logs`、`/api/plan`、`/api/balance`。

## 3.9 关系卡规则

```text
只展示后端真实字段：
  亲密度 affinity
  档位 tier
  最近变化 events
```

未来多维关系用后端 `dimensions` 数组动态渲染：

```text
dimensions: [{key,label,value,visible}]
→ 默认展示前 3 个
→ 更多折叠为“展开全部”
```

不要写死“信任 / 理解 / 安全感”这类前端虚构维度。

## 3.10 右侧上下文

右侧只放：

```text
关系：亲密度 / 档位 / 最近变化
生活状态：心情 / 精力 / 正在 / 今日互动
快捷入口
```

记忆详情归记忆页，不在聊天右侧重复堆卡片。

## 3.11 人设页

```text
人设卡列表：名称 / 文件清单 / 摘要 / 当前标记
导入 JSON
导出 JSON
激活（仅 owner）
预览
```

最终接口：`/api/persona`、`/api/persona/import`、`/api/persona/export`、`/api/persona/activate`。

## 3.12 周计划按周配置

```text
节次数每周可不同
上下课时间每周可不同
节次设置：加/删/改时间
切周加载该周配置
```

课程仍按星期 × 节次存；后端周计划需要保存该周的 period 配置。

## 3.13 未读规则

```text
未读 badge 分两层：
  会话项：该会话未读数
  左侧导航：所有会话未读总数
点开会话：
  清该会话未读
  重算导航总数
  总数为 0 时隐藏 badge
```

## 3.14 首次登录

第一次打开没有本地登录配置时，弹窗：

```text
后端：当前 Web 站点同源，不填 URL
访问 token
主人 QQ
测试连接
保存并进入
稍后配置
```

保存到 localStorage，不写入仓库；设置页可重新打开配置。

## 3.15 她的状态

右侧只显示后端真实字段：

```text
/internal/state   → mood / energy / lonely / emotion
/internal/presence → activity / detail / idle_min / stale
```

规则：

```text
presence 超过 TTL → unknown
没有数据 → 显示未知
不展示前端虚构的“今日互动次数”
```

Web 需要同源 `/api/state`、`/api/presence` 的 owner 只读代理。

## 3.16 多端同步边界

```text
Web：拉取，不做 Web Push
插件：host notification / badge
手机：前台服务或 ntfy 系统通知
所有端：after_seq + ack + read，按 message_id 去重
推送只带 message_id，打开再拉正文
```

## 3.17 开发转发与生产代理

开发阶段不需要 nginx：

```text
Vite :27006
  /api      → 127.0.0.1:27004
  /internal → 127.0.0.1:27004
  /healthz  → 127.0.0.1:27004
  /readyz   → 127.0.0.1:27004
```

生产如果只需要本机访问，可以直接由后端静态托管；如果要同源 + TLS + 多端入口，再用 nginx：

```text
nginx :27006
  /        → dist 静态文件
  /api/    → gateway :27005
  /ws      → gateway/ingress
  其余内部接口不暴露公网
```

nginx 要点：SPA fallback、上传大小、SSE/WebSocket 不缓冲、API 不缓存。

## 3.18 nginx 生产配置

文件：

```text
integrations/web/deploy/nginx.conf
integrations/web/deploy/DEPLOY.md
```

入口：

```text
27006 → dist 静态
/api/ → frpc 映射 127.0.0.1:27015
/ws/  → 127.0.0.1:27015（Upgrade）
/internal/ → 404

后端无公网：
frpc 主动连公网前端 frps
gateway 27005 → remotePort 27015
nginx 只访问 127.0.0.1:27015
```

## 3.19 后端能力审计

```text
已有：chat/history、memory、relation、savings/entries/events/balance/import、persona、logs
部分：weekly（缺按周节次）、info（缺 shelf）、commands（缺目录）、cron（缺公开 CRUD）、state/presence（缺公开 API）
没有：插件管理公开接口
```

补全顺序：

```text
v35.7.23  /api/commands ✅
v35.7.24  /api/cron
v35.7.25  /api/state + /api/presence ✅
v35.7.26  /api/shelf
v35.7.27  插件管理
```

## 3.20 网关路由边界

```text
nginx /api/* → gateway 27005
gateway 已鉴权 GET → worker HTTP API（v35.7 通配）
chat/history/state/cron/diary/shelf 仍走内部专用路径
```

注意：gateway 是 C++ 二进制，改 router.cpp 后必须重新构建/部署；当前已安装旧二进制不会自动生效。

## 4. 次次版本

| 版本 | 交付 | 验收 |
|---|---|---|
| v35.5.0.0 ✅ | Node 20+/pnpm、Vue 3 + Vite + TS、Router/Pinia、ESLint/Vitest/Playwright、API client/env | 空项目可构建、可测 |
| v35.5.1.0 ✅ | AppShell/Router/导航/ThemeToken/错误空态/Mock adapter | 12 个导航空壳 |
| v35.5.2.0 ✅ | 首次登录 QQ/token（同源）、连接测试、错误态 | 能登录，失败有提示 |
| v35.5.3.0 | QQ 会话列表、历史分页、已读位点 | 群列表一致 |
| v35.5.4.0 ✅ | 文本发送、乐观更新、失败回滚、幂等 | 能聊天 |
| v35.5.5.0 ✅ | 图片发送/预览、后端落盘、历史回显、4MB 限制 | 刷新后图片仍在 |
| v35.5.5.1 ✅ | 语音录音、表情包、附件落盘、历史回显 | 多端可拉取附件 |
| v35.5.6.0 | 增量拉取、after_seq、focus/visibility、重连 | 拉取不丢消息 |
| v35.5.7.0 | 未读 badge、多标签、已读上报、导航总数 | 刷新/断网不丢 |
| v35.5.8.0 | 语音/表情/识图/搜图媒体工具 | 媒体可用 |
| v35.5.9.0 | 在线/已读/seq 缺口；mood/energy/presence | 缺失显示未知 |
| v35.5.10.0 | 话题结束判断与追问、频控/免打扰 | 能判断并追问 |
| v35.5.11.0 | 聊天动画，默认关闭 | 动画可关 |
| v35.5.12.0 | 聊天内搜索：高亮/上下条 | 搜索可用 |
| v35.5.13.0 | 窄屏/手机浏览器适配 | 手机可用 |
| v35.5.14.0 | 会话数据源统一 QQ 私聊/群 | 群列表一致 |
| v35.5.15.0 | Vite build、Mock 标注、视觉/接口回归 | 可演示 |
| v35.5.16.0 | Web 消息同步：seq/ack/read/多标签 | 与后端一致 |
| v35.5.17.0 | Web nginx 生产部署（27006） | nginx -t 通过 |

## 4.1 命令目录

命令页最终不硬编码：

```text
GET /api/commands
→ name / group / help / owner / risk
```

客户端只渲染接口返回；执行仍走 `POST /api/command`。

命令页布局：

```text
上半：命令目录（分组/搜索）
     命令行输入（支持参数）
     二级命令提示
下半：固定执行结果区
```

带参命令不直接执行：点击后填入命令并提示 usage/args；二级命令显示可选项；缺参在结果区提示，不伪造成功。

演示里的 51 条是 MOCK，最终版删除硬编码。

## 5. 接口

```text
POST /api/chat                 发送
GET  /api/conversations        会话列表
GET  /api/history              会话历史
GET  /api/commands             命令目录
POST /api/command              执行命令
GET  /internal/history         历史
GET  /api/memory               记忆
GET  /api/relation             关系
GET  /api/status               连接状态
SSE  事件流                    实时消息/已读/在线
```

约束：

```text
token 只在前端登录后保存；不写死
Mock 数据必须打 MOCK 标识
未连接不伪造在线/已读
QQ 无法判断的已读状态不主动上报
```

## 6. 组件

```text
App
├─ RailNav
├─ ConversationList
├─ ChatHeader
├─ MessageList
│  ├─ MessageBubble
│  └─ MemoryChip
├─ Composer
│  ├─ MediaTools
│  └─ SendButton
└─ ContextPanel
   ├─ PersonaCard
   ├─ MemoryCards
   └─ LifeState
```

## 7. 演示

```text
docs/design/v35/web/hoshinoumi-web-v35.5.html
docs/design/v35/web/hoshinoumi-web-v35.5.png
```

所有演示数据为 MOCK。
'''

## 8. 演示交互

`hoshinoumi-web-v35.5.html` + `demo.js` 是纯前端 MOCK 交互：

- 点击会话切换聊天
- 输入后发送 / Enter 发送
- 模拟“正在输入”，返回 MOCK 回复
- 左侧导航切换记忆/存钱/周计划/人设/关系/设置
- 媒体按钮插入占位
- 右侧快捷卡片跳页
- 页面内“返回聊天”

不需要后端，直接浏览器打开即可。
