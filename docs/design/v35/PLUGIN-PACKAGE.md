# `.houshinoumi` 插件包规范

> v35.9.4 起，Hoshinoumi 插件包推荐使用 `.houshinoumi`；同时兼容 `.zip`。

## 容器

```text
.houshinoumi / .zip = ZIP 容器（推荐 .houshinoumi）
MIME: application/vnd.houshinoumi.plugin+zip（.zip 用 application/zip）
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
网址导入：http(s) 指向 .houshinoumi / .zip / plugin.json
本地导入：.houshinoumi / .zip（单文件 plugin.json 仅开发调试）
安装后默认只读
write 权限逐项审批，owner 才能批准
校验失败 / 清单缺失 / 版本不兼容 → 拒绝安装
```

## 演示与实现

```text
手机设计稿：插件 → ＋ → 网址 / .houshinoumi / .zip 文件
Web 设计稿：插件 → ＋ 安装插件 → 网址 / .houshinoumi / .zip 文件
Vue/API：v35.9.4.2–.6
```
