# 客户端署名

规则：**每个客户端/端全局署名一次**，不是每个页面。

| 端 | 署名位置 |
|---|---|
| 桌面 Vue / Electron | 设置 → 关于 `POWERED BY JYOUSUITOU` |
| 手机浏览器 Web | 设置 → 关于 `POWERED BY JYOUSUITOU`（设计稿已加） |
| 手机套壳 App | 复用手机 Web 署名 |
| DSH 插件 | 设置模块 → 关于 `by jyoushitou` |
| VS Code 插件 | 设置页 → 关于 `by jyoushitou` |
| Qoder 插件 | plugin.json author / README |
| Qt / Android / HyperOS / EMUI | 实现时在各自关于页或全局 footer 署名 |
| CLI | `--version` / help footer 署名 |

设计稿：
- 手机设置页 → 关于：`Hoshinoumi v35.7 · POWERED BY JYOUSUITOU`。
- 不再放全局 footer / 顶部水印。
- 其他端同样放在各自设置/关于页。
