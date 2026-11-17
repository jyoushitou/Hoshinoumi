from pathlib import Path
p=Path("docs/versions/v35.md")
s=p.read_text(encoding="utf-8")

s=s.replace(
"| **v35.3.8.0** | 聊天页动画 | 消息进入/发送/滚动/未读过渡；默认关闭 | 动画可关，聊天不卡 |",
"| **v35.3.8.0** | 聊天页动画 | 消息进入/发送/滚动/未读过渡；默认关闭 | 动画可关，聊天不卡 |\n"
"| **v35.3.9.0** | 聊天媒体工具：图片/语音/贴纸/识图/搜图 | img/acg/voice/sticker/vision/clip；上传/预览 | 媒体能力可用 |\n"
"| **v35.3.9.1** | 聊天媒体动画 | 图片预览/语音波形/贴纸面板 | 动画可关 |"
)

s=s.replace(
"| **v35.5.5.1** | 人设页动画 | 卡切换/预览过渡 | 动画可关 |",
"| **v35.5.5.1** | 人设页动画 | 卡切换/预览过渡 | 动画可关 |\n"
"| **v35.5.6.0** | 信息页能力补全：账号/阅读/日记/网关/运维 | adduser/books/book/diary/gw/apikeys/log/db/usage/backup/update | 后端能力都有入口 |\n"
"| **v35.5.6.1** | 信息补全页动画 | 子页切换/危险确认/进度 | 动画可关 |"
)

s=s.replace(
"Web       v35.5.0.0–v35.5.5.1\nQt        v35.6.6.0–v35.6.10.1\nAndroid   v35.7.6.0–v35.7.10.1\nEMUI      v35.9.4.0–v35.9.8.1",
"Web       v35.5.0.0–v35.5.6.1\nQt        v35.6.6.0–v35.6.11.1\nAndroid   v35.7.6.0–v35.7.11.1\nEMUI      v35.9.4.0–v35.9.9.1"
)

old_catalog = """学习计划
```

页面目录（6 页）："""
new_catalog = """学习计划
账号/权限
阅读/书架
日记
网关/API 密钥
运维/诊断
```

### 后端能力覆盖矩阵

| 后端能力 | 入口 | 客户端位置 |
|---|---|---|
| 对话/历史/发送 | chat/history | 聊天 |
| 图片/搜图/ACG | img/acg | 聊天 > 媒体 |
| 语音/TTS | voice | 聊天 > 媒体 |
| 贴纸/表情包 | sticker | 聊天 > 媒体 |
| 识图/CLIP | vision/clip | 聊天 > 媒体 |
| 主动说/群说 | say/sayg | 聊天 > 高级 |
| 记忆/事件/记忆本 | memory/event/memorybook | 信息 > 记忆 |
| 关键词/清空 | keywords/clear | 信息 > 记忆（危险确认） |
| 画像/成长/关系 | profile/growth/relation | 信息 > 关系 |
| 定时/钩子/待办 | cron/hooks/todo | 信息 > 日程 |
| 阅读/书架 | books/book | 信息 > 阅读 |
| 日记 | diary | 信息 > 日记 |
| 配置/热加载/代码模式 | config/set/reload/code | 信息 > 设置 |
| 密钥/网关 | apikeys/gw | 信息 > 网络 |
| 账号/角色 | adduser | 信息 > 账号（owner） |
| 状态/统计/用量/日志/DB | status/stats/usage/log/db/meta/uptime | 信息 > 运维 |
| 备份/更新/退出 | backup/update/exit | 信息 > 系统（危险确认） |
| 插件 | plugin | 插件 |
| 路由 | route | 命令/信息 |
| 人设 | persona | 人设 |
| 学习计划 | plan | 信息 > 学习计划 |
| 情境 | doing/presence | 聊天顶部/信息 |
| 存钱 | saving | 存钱 |

规则：

```text
后端有的能力，客户端必须有入口
不能做的（如群管理）标注“桌面端/仅 owner”
危险操作二次确认
只读优先
```

页面目录（6 页）："""
if old_catalog not in s:
    raise SystemExit("catalog marker missing")
s=s.replace(old_catalog,new_catalog)
p.write_text(s,encoding="utf-8",newline="\n")
print("ok")
