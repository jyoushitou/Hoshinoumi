# `.hoshinoumi` 插件包规范

> v35.9.4 起，Hoshinoumi 插件包推荐使用 `.hoshinoumi`；同时兼容 `.zip`。

## 容器

```text
.hoshinoumi / .zip = ZIP 容器（推荐 .hoshinoumi）
MIME: application/vnd.hoshinoumi.plugin+zip（.zip 用 application/zip）
建议上限：20 MB
```

## 必需文件

```text
plugin.json       插件清单（必需）
entry.js          入口（按 plugin.json 声明）
assets/           图标、静态资源（可选）
signature.json    签名/校验信息（可选，正式分发建议必需）
```

## plugin.json

```json
{
  "id": "weather",
  "name": "天气",
  "version": "1.2.0",
  "apiVersion": 1,
  "entry": "entry.js",
  "permissions": ["network"],
  "description": "读天气",
  "author": "jyoushitou",
  "minAppVersion": "35.9.0.0"
}
```

## 安装规则

```text
网址导入：http(s) 指向 .hoshinoumi / .zip / plugin.json
本地导入：.hoshinoumi / .zip（单文件 plugin.json 仅开发调试）
安装后默认只读
write 权限逐项审批，owner 才能批准
校验失败 / 清单缺失 / 版本不兼容 → 拒绝安装
```

## 演示与实现

```text
手机设计稿：插件 → ＋ → 网址 / .hoshinoumi / .zip 文件
Web 设计稿：插件 → ＋ 安装插件 → 网址 / .hoshinoumi / .zip 文件
Vue/API：v35.9.4.2–.6
```

## 解析流程

```text
1. 校验后缀 .hoshinoumi / .zip，且文件不超过 20 MB
2. zipfile.is_zipfile 确认 ZIP
3. 拒绝绝对路径、..、反斜杠和超过 500 个文件
4. 解压总大小不超过 50 MB
5. 读取根目录 plugin.json（UTF-8 JSON）
6. 校验必需字段和 apiVersion
7. 校验 permissions 只含允许值
8. 校验 entry 存在且无路径穿越
9. 解压到 data/plugins/<id>/<version>，再原子切换
10. 安装后默认只读，写权限进入审批
```

参考实现：

```bash
python scripts/plugin_package.py inspect weather.hoshinoumi
python scripts/plugin_package.py extract weather.hoshinoumi data/plugins/weather
```

安全限制：

```text
禁止 symlink / 绝对路径 / .. / 反斜杠
拒绝未知权限和 apiVersion > 1
解压前先校验所有 entry，再 extractall
签名可选，正式分发建议增加 signature.json 校验
```
