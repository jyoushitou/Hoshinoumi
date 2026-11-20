# Hoshinoumi Desktop · v35.6.0 设计稿

## 文件

```text
hoshinoumi-desktop-v35.6.html
desktop.css
desktop.js
hoshinoumi-desktop-v35.6.png
```

## 交互

```text
窗口入场动画
侧栏 hover / 选中
会话切换 / 私聊 / 群聊筛选
发送消息 → 用户气泡 → 打字指示 → 回复
托盘小窗按钮 ▣ 打开/关闭快捷回复小窗
标题栏最小化/最大化/关闭到托盘 toast
更新卡片
导航 / 快捷入口 toast
```

## 设计范围

v35.6.0 只做 Tauri/WebView 套壳：

```text
自定义标题栏
托盘常驻
托盘小窗
自动更新入口
状态栏
```

不重写 Web 页面。
