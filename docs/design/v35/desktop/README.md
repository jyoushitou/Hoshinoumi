# Hoshinoumi Desktop · v35.6.0 设计稿

## 视觉基准

以 Vue Web 预览为基准，桌面壳只加原生外壳，不另起视觉：

```text
docs/design/v35/web/hoshinoumi-web-v35.5-nginx.png
```

```text
rail 64 / side 292 / context 304
聊天头 66
消息区 20/22
输入区 11/18/13
```

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

## 这个 HTML 是什么

```text
独立客户端的外观 / 交互设计稿
用于确认壳、托盘、窗口、页面布局
不是最终客户端本体
不是第二套业务代码
```

当前各页面是设计稿数据；真实内容来源：

```text
Vue 页面实现
→ 打包 integrations/web/dist
→ Electron 壳加载同一套构建
→ 客户端自动获得全部内容
```

所以这个 HTML 不需要重复写全部业务；它只负责确认壳和视觉。
页面内容扩充在 Vue 页面做，v35.6.4 做全路由接入验收。

## 运行环境

```text
Windows / macOS / Linux：Electron 内置 Chromium
不再依赖系统 WebView
Chromium 随 Electron 打包
```

内置 Chromium，页面渲染与系统浏览器无关。

## 设计范围

v35.6.0 只做 Electron/Chromium 套壳：

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

保存后由 Electron 安全存储保存；WebView 内只拿运行时配置，不写死。

设计截图：

```text
hoshinoumi-desktop-v35.6-settings.png
```


## 显示兜底

```text
启动前检测引擎/版本/能力
A 完整模式
B 兼容模式
C 安全模式
D 本地 fallback.html
5 秒无心跳 → 兜底页
绝不白屏
```

设计稿：

```text
hoshinoumi-desktop-v35.6-fallback.html
```

---

POWERED BY JYOUSUITOU
