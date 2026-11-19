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

## 4. 次次版本

| 版本 | 交付 | 验收 |
|---|---|---|
| v35.5.0.0 | Vue 基座、ThemeToken/MotionPreset、Bearer 登录 | 浏览器能登录 |
| v35.5.1.0 | 会话列表、历史分页、已读位点 | 能看历史 |
| v35.5.2.0 | 文本发送、乐观更新、失败回滚、幂等 | 能聊天 |
| v35.5.3.0 | 图片发送/预览、上传 | 图片可用 |
| v35.5.4.0 | SSE 实时接收、event id 去重、重连 | 实时收消息 |
| v35.5.5.0 | 未读 badge、多标签、已读上报 | 刷新/断网不丢 |
| v35.5.6.0 | 语音/表情/识图/搜图媒体工具 | 媒体可用 |
| v35.5.7.0 | 在线状态、已读回执、seq 缺口提示 | 多端一致 |
| v35.5.8.0 | 话题结束判断、追问状态、频控/免打扰 | 能判断并追问 |
| v35.5.9.0 | 聊天动画，默认关闭 | 动画可关 |
| v35.5.10.0 | 窄屏/手机浏览器适配 | 手机可用 |
| v35.5.11.0 | Vite build、Mock 标注、视觉/接口回归 | 可演示 |

## 5. 接口

```text
POST /api/chat                 发送
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
