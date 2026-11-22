# 客户端署名

规则：**每个客户端/端全局署名一次**，不是每个页面。

| 端 | 署名位置 |
|---|---|
| 桌面 Vue / Electron | 设置页最底部 `POWERED BY JYOUSUITOU` |
| 手机浏览器 Web | 设置 → 关于 `POWERED BY JYOUSUITOU` |
| 手机套壳 App | 复用手机 Web 署名 |
| DSH 插件 | 设置模块最底部 `POWERED BY JYOUSUITOU` |
| VS Code 插件 | 设置页最底部 `POWERED BY JYOUSUITOU` |
| Qoder 插件 | plugin.json author / README |
| Qt / Android / HyperOS / EMUI | 实现时在各自关于页或全局 footer 署名 |
| CLI | `--version` / help footer 署名 |

规则：
- 有“关于”页面的端：放关于页。
- 没有关于页面的端：放设置页面最底部。
- 不再放全局 footer / 顶部水印 / 登录页水印。
