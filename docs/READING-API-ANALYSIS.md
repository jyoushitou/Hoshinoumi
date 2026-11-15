# 阅读接口分析（仅自有/授权流量）

> v24.5 交付物。目标不是抓站，而是分析**自己的账号、自己的客户端、自己有权访问的内容**，
> 用于自建客户端/本地阅读器。项目不内置书源，不绕过付费墙、DRM、验证码或风控。

## 允许 / 不允许

| 允许 | 不允许 |
|---|---|
| 自己的账号登录态 | 他人账号 / 共享账号 |
| 已购买或免费可读章节 | 付费墙后内容 |
| 记录 URL、参数、分页、状态码 | 保存 cookie/token 明文 |
| 复现自己已能发起的请求 | 破解签名、DRM、验证码 |
| 公开 Web/API 文档 | 笔趣阁等未授权转载站 |
| 导出脱敏 HAR | 下载/分发正文 |

## 工具

```text
mitmproxy / Charles / Proxyman
自有设备安装用户证书
HAR 导出
python3 scripts/sanitize_har.py own.har own.sanitized.har
```

脱敏脚本会：

- 删除 `Cookie` / `Authorization` / `Set-Cookie` / token 头
- 删除 URL 里的 token/key/sign 查询参数
- 删除响应正文，只保留 mime/大小
- 生成 `*.endpoints.json`：method / url / status / mime

## 交付物

```text
endpoint 列表：方法 / 路径 / 参数 / 分页 / 返回结构
鉴权流程：登录、刷新、失效（只记流程，不记 token）
限速与错误码：429 / 403 / 验证码
章节 URL 规律与目录分页
脱敏 HAR 样本（不含正文）
```

## 操作步骤

1. 只在自己的设备/模拟器上安装用户证书。
2. 登录自己的账号，只打开自己有权阅读的章节。
3. 导出 HAR。
4. 立即运行 `sanitize_har.py`，删除原始 HAR。
5. 检查 `endpoints.json` 是否含 token/QQ/手机号。
6. 把 endpoint/分页/错误码写进实现文档；不保存正文。

## 验收

```text
[ ] 用的自己的账号
[ ] 只访问已授权章节
[ ] HAR 已脱敏，无 cookie/token/正文
[ ] 能复现一条已授权请求
[ ] 不下载无权章节
[ ] 不向第三方分发正文
```

## 停止条件

```text
出现验证码 / 风控 / 封号风险 -> 停止
需要破解签名或 DRM -> 不做
目标是转载站 -> 不做
只能拿到付费墙后内容 -> 不做
```

## 与本地阅读的关系

网络受限时**不绕过**，提示用户把 TXT/EPUB 放进 `data/books/`，见 v24.6。
