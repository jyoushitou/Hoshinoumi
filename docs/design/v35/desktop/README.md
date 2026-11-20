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

## 运行环境

```text
Windows：Tauri + WebView2 Fixed Version Runtime
macOS：WKWebView 系统组件 + 最低版本检测
Linux：WebKitGTK / AppImage 固定依赖
```

不是内置完整 Chromium；是固定 WebView2 运行时。

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


## 壳路由设置

v35.6.0 设计稿的 ⚙ 设置内新增“连接与路由”：

```text
连接方式：公网前端 nginx / 本机 gateway / 自定义
后端入口：http://127.0.0.1:27006
API 路由：/api
实际请求预览
访问 token
启动页路由：/chat / /home / 上次会话
测试连接 / 保存路由
```

保存后由 Tauri 系统安全存储保存；WebView 内只拿运行时配置，不写死。

设计截图：

```text
hoshinoumi-desktop-v35.6-settings.png
```
