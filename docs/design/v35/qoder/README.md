# Qoder 扩展 Webview 模拟

`qoder-extension.html` 模拟的是 Qoder 扩展，不是 DSH 插件。

## 入口

左侧 Activity Bar 的 `Q` 图标：

- 点击打开 / 收起 Qoder 任务侧栏
- 侧栏顶部 `Qoder 任务面板` 显示扩展已启用
- `Ctrl+Shift+P` 命令面板执行 `Qoder: 打开任务面板`

## 页面

- 期末复习规划
- Linux 复习题
- 思政专题 3
- 第三期海龟汤
- 修复启动问题

## 交互

- 点任务切换 Webview 文档
- 新建任务
- Webview 底部发送消息
- 关闭/重新打开侧栏
- Esc 关闭命令面板

## 文件

- `qoder-extension.html`
- `qoder-extension.png`
