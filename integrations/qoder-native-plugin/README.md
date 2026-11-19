# Hoshinoumi for Qoder

Qoder 原生插件：Skill + `/nao` 命令 + MCP server。

## 安装

把整个目录作为 Qoder 插件安装（或打成 ZIP 导入）：

```text
.qoder-plugin/plugin.json
.mcp.json
runtime/server.cjs
skills/hoshinoumi/SKILL.md
commands/nao.md
```

## 配置

编辑 `~/.qoder-cn/hoshinoumi.json`：

```json
{
  "base_url": "http://127.0.0.1:27004",
  "token": "<Hoshinoumi API token>",
  "target_id": "<主人 QQ>"
}
```

也可以用环境变量 `HOSHINOUMI_QODER_CONFIG` 指向另一份配置。

## 工具

`hoshinoumi_chat` / `hoshinoumi_history` / `hoshinoumi_status` / `hoshinoumi_memory` /
`hoshinoumi_savings` / `hoshinoumi_add_saving` / `hoshinoumi_weekly_plan` /
`hoshinoumi_import_weekly` / `hoshinoumi_persona` / `hoshinoumi_relation` /
`hoshinoumi_balance` / `hoshinoumi_command`

## 调用

```text
/nao 今天怎么样？
/hoshinoumi 看一下我的存钱
```

或直接让 Qoder「用 Hoshinoumi 查一下关系」。
