# Hoshinoumi Logo

同一几何图形，两种导出：

| 用途 | 文件 | 颜色 |
|---|---|---|
| 文档 / README / 演示 | `docs/design/logo/hoshinoumi.svg` | 彩色渐变 |
| VS Code / 安装器 / 托盘 | `docs/design/logo/hoshinoumi-mono.svg` | `currentColor` 单色 |

形态：

```text
四芒星 + 轨道
```

规则：

```text
文档、演示图、README 使用彩色版
受平台主题限制的图标（VS Code、托盘、安装器）使用单色版
单色版必须用 currentColor
保持 1:1，不拉伸
不贴边，不加气泡/加号/文字
```

VS Code 扩展当前使用单色副本：

```text
integrations/vscode-plugin/media/nao.svg
```

改 Logo 时，先改两个源文件，再同步扩展副本。
