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

## 4. 次次版本

| 版本 | 交付 | 验收 |
|---|---|---|
| v35.5.0.0 | Vue 基座、ThemeToken/MotionPreset、Bearer 登录 | 浏览器能登录 |
| v35.5.1.0 | QQ 会话列表、历史分页、已读位点 | 群列表与 QQ 一致 |
| v35.5.2.0 | 文本发送、乐观更新、失败回滚、幂等 | 能聊天 |
| v35.5.3.0 | 图片发送/预览、上传 | 图片可用 |
| v35.5.4.0 | SSE 实时接收、event id 去重、重连 | 实时收消息 |
| v35.5.5.0 | 未读 badge、多标签、已读上报 | 刷新/断网不丢 |
| v35.5.6.0 | 语音/表情/识图/搜图媒体工具 | 媒体可用 |
| v35.5.7.0 | 在线状态、已读回执、seq 缺口提示 | 多端一致 |
| v35.5.8.0 | 话题结束判断与追问、频控/免打扰 | 能判断并追问 |
| v35.5.9.0 | 聊天动画，默认关闭 | 动画可关 |
| v35.5.10.0 | 聊天内搜索：高亮/上下条 | 搜索可用 |
| v35.5.11.0 | 窄屏/手机浏览器适配 | 手机可用 |
| v35.5.12.0 | 会话数据源统一 QQ 私聊/群 | 群列表一致 |
| v35.5.13.0 | Vite build、Mock 标注、视觉/接口回归 | 可演示 |

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
