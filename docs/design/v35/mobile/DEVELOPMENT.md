# v35.7 手机 Vue 框架

状态：v35.7.1.0 / v35.7.1.1 已实现，继续 v35.7.2.0 验收。

## 入口

```text
integrations/web/src/App.vue
```

规则：

```text
同一个 URL，同一套 Vue Router
不支持 /mobile、/m、手机专用子域名
≤ 820px：MobileShell + 手机页面组件
> 820px：AppShell + 桌面页面组件
窗口 resize 时实时切换
≤ 820px 手机/平板铺满视口，不做居中窄列
```

例：

```text
电脑打开 http://host:27006/chat   → AppShell + ChatView
手机打开 http://host:27006/chat   → MobileShell + MobileChatView
同一路径，仅视口尺寸不同
```

## 文件

```text
layouts/MobileShell.vue              手机壳 / 顶部栏 / 路由选择
components/mobile/MobileTabBar.vue   底部快捷栏 + 全部入口
composables/useMobileNav.ts          快捷项状态 / localStorage / 1–5 限制
views/mobile/MobileChatView.vue      会话列表 + 聊天骨架
views/mobile/MobilePageView.vue      其余页面框架
views/mobile/MobileSettingsView.vue  设置 + 快捷栏自定义
views/mobile/MobileWeeklyView.vue    手机周计划（真实 /api/weekly-plan 读写）
```

## 路由

沿用现有路由：

```text
/chat /home /memory /relation /savings /weekly /info
/persona /commands /cron /logs /settings
```

MobileShell 按路由名选择手机页面；不复制一套业务路由。

## 底部快捷栏

```text
收起：1–5 个快捷入口，均分一行
展开：12 个图标入口，4 列
点击入口：直接跳转并收起
自定义：设置 → 底部快捷栏
存储：localStorage: hoshinoumi.mobile.quick
```

## owner 判定

```text
composables/useIsOwner.ts
auth.qq === session.status.master_qq
```

非 owner：

```text
MobileTabBar / MobileSettingsView 隐藏 relation
RailNav 隐藏关系入口
MobileShell 访问 /relation 跳 /chat
RelationView 非 owner 不渲染并重定向
```

## 校验

```powershell
cd integrations/web
pnpm build
```

构建通过；手机 390×844 已截图验证：
- MobileShell 正常
- 会话列表 / 游客提示正常
- 设置页 12 个快捷候选、当前 4 个正常
