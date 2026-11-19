# Hoshinoumi for VS Code · v35.4.0

在 VS Code 内连接 Hoshinoumi 后端：nao 聊天、历史、记忆、存钱、人设、周计划表、状态、日志、定时任务、命令。

## 入口

- 左侧 Activity Bar 的 **Hoshinoumi** 图标
- 命令面板：`Hoshinoumi: 打开 nao`

## 配置

第一次打开 Webview 时填写：

```text
后端地址  http://127.0.0.1:27004
访问 token
主人 QQ
```

配置保存在 VS Code 扩展的 globalState；token 不写入日志。

## 说明

这是 VS Code 的独立扩展。扩展宿主负责 HTTP 代理，侧栏 Webview 不直接接触 token。
