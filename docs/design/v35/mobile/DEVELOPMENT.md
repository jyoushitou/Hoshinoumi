# v35.7 手机 Vue 框架

状态：框架已接入（v35.7.0.0），页面按补丁继续补。

## 入口

```text
integrations/web/src/App.vue
```

规则：

```text
≤ 820px：MobileShell
> 820px：原 AppShell，桌面不变
```

## 文件

```text
layouts/MobileShell.vue              手机壳 / 顶部栏 / 路由选择
components/mobile/MobileTabBar.vue   底部快捷栏 + 全部入口
composables/useMobileNav.ts          快捷项状态 / localStorage / 1–5 限制
views/mobile/MobileChatView.vue      会话列表 + 聊天骨架
views/mobile/MobilePageView.vue      其余页面框架
views/mobile/MobileSettingsView.vue  设置 + 快捷栏自定义
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
