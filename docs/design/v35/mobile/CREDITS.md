# 客户端署名

规则：**每个客户端/端全局署名一次**，不是每个页面。

| 端 | 署名位置 |
|---|---|
| 桌面 Vue / Electron | AppShell 右下角全局 `POWERED BY JYOUSUITOU` |
| 手机浏览器 Web | MobileShell 顶部、登录弹窗底部 |
| 手机套壳 App | 复用手机 Web 署名 |
| DSH 插件 | 顶部栏 `by jyoushitou` |
| VS Code 插件 | 侧边栏标题栏 `by jyoushitou` |
| Qoder 插件 | plugin.json author / README |
| Qt / Android / HyperOS / EMUI | 实现时在各自关于页或全局 footer 署名 |
| CLI | `--version` / help footer 署名 |

设计稿：
- 六屏总览 / 逐页细稿 / 交互演示各保留一处端级署名。
- 不在每个页面重复放署名。
