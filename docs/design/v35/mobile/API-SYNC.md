# v35.7 移动端交互 → 后端同步

规则：**设计演示里的增删改只做演示；真实 Vue 页面必须调后端并以后端返回为准。**

## 已存在 API

| 交互 | API | 说明 |
|---|---|---|
| 会话列表 | `GET /api/conversations` | 真实会话 |
| 历史消息 | `GET /api/history` | 进入会话加载 |
| 已读 | `POST /api/read` | 清列表/底栏未读 |
| 发送 | `POST /api/chat` | 成功后再回显 |
| 记忆列表 | `GET /api/memory` | 记忆筛选为前端展示 |
| 命令目录 | `GET /api/commands` | 51 条命令、分类、权限 |
| 命令执行 | `POST /api/command` | 参数校验，失败显示真实错误 |
| 关系 | `GET /api/relation` | 非 owner 隐藏页面 |
| 周计划读取 | `GET /api/weekly-plan?week=` | 按 ISO 周 |
| 周计划保存 | `POST /api/weekly-plan` | **整周保存**；新增/删除/切换完成后整周 POST |
| 定时任务列表 | `GET /api/cron` | 只读 |
| 定时任务新增/编辑/启停/删除/运行 | `/api/cron*` | 需要 CRUD，禁止只改本地 |
| 存钱读取 | 现有 `/api/savings*` | 总览/流水 |

## 需要补 API

| 交互 | 目标 API | 版本 |
|---|---|---|
| 提醒“稍后 / 知道了” | `/api/cron` 写操作 / ack | v35.7.1.1 |
| 周计划单节次增删改（可选优化） | `/api/weekly-plan/periods*` | v35.9.20.x |
| 存钱目标/账户/冻结/定期/基金写操作 | `/api/savings/*` | v35.9.1.6–.18 |
| 快捷栏自定义 | 仅客户端 local | 不同步 |
| 主题/外观 | 客户端 local | 不同步 |

## 验收

```text
删除节次 → POST 整周 → GET 刷新 → 该节次仍不存在
点“知道了”提醒 → 后端 ack → 刷新不再出现
所有写操作失败时显示错误，不伪造成功
刷新页面后状态仍以后端为准
```
