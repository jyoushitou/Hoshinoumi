# Hoshinoumi Mobile · v35.7 设计稿

## 文件

```text
hoshinoumi-mobile-v35.7.html   六屏手机画板
mobile.css                     设计稿样式
hoshinoumi-mobile-v35.7.png    渲染截图
```

## 画板

```text
390 × 844（iPhone 14 基准）
六屏：登录 / 会话 / 聊天 / 记忆 / 关系 / 设置
```

## 页面映射

| 设计屏 | Vue 入口 | 说明 |
|---|---|---|
| 登录 | 登录弹窗 | QQ + owner token，不存密码 |
| 会话列表 | `/chat` | 搜索、私聊/群聊筛选、未读 |
| 聊天 | `/chat` | 消息、输入栏、安全区、输入法避让 |
| 记忆 | `/memory` | 记忆本 / 事件 / 画像 |
| 关系 | `/relation` | 档位与最近变化，不显示精确数值 |
| 设置 | `/settings` | 连接、通知、记忆、关系范围、关于 |

## 移动端规则

```text
底部导航 69px，含 safe-area
列表项触控高度 ≥ 44px
底部输入栏避开 Home Indicator / 输入法
聊天页滚动区独立，输入栏固定
关系页不显示亲密数值，只显示档位/变化
非主人不可访问财务、私密记忆
```

## 断点

```text
< 430px   手机单栏
430–767px 大屏手机 / 小折叠
≥ 768px   平板两栏，进入 v35.14 平板设计
```

## 这个 HTML 是什么

独立移动端外观 / 交互设计稿，用于确认移动 Web 的结构、尺寸和触控，不是最终客户端。

真实页面来源：

```text
Vue 页面实现
→ integrations/web/dist
→ v35.7 手机浏览器 Web
```
