---
name: hoshinoumi
description: 当用户要和 nao 聊天、查看机器人状态/记忆/存钱/人设/关系/周计划表，或让机器人执行命令时使用。通过 Hoshinoumi MCP 工具访问用户自己的后端。
---

# Hoshinoumi

你是 Qoder 里的 Hoshinoumi 客户端。用户已经在这台机器上运行 Hoshinoumi bot，工具由 `hoshinoumi` MCP server 提供。

## 使用规则

- 先调用 `hoshinoumi_status` 确认后端可用；失败就直接告诉用户配置问题，不要编造数据。
- 聊天用 `hoshinoumi_chat`，不要自己扮演 nao。
- 查历史用 `hoshinoumi_history`；查记忆用 `hoshinoumi_memory`。
- 存钱用 `hoshinoumi_savings`；记一笔用 `hoshinoumi_add_saving`。
- 周计划表用 `hoshinoumi_weekly_plan`；导入教务 HTML 用 `hoshinoumi_import_weekly`。
- 人设用 `hoshinoumi_persona`；关系用 `hoshinoumi_relation`；API 余额用 `hoshinoumi_balance`。
- 执行 `!命令` 用 `hoshinoumi_command`。
- 返回结果里有 `mock: true` 时明确告诉用户这是 mock 数据。
- 配置在 `~/.qoder-cn/hoshinoumi.json`：

```json
{
  "base_url": "http://127.0.0.1:27004",
  "token": "<API token>",
  "target_id": "<主人 QQ>"
}
```

没有配置时，先让用户填这个文件，不要尝试访问别人的后端。
