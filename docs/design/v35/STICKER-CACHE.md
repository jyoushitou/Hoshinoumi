# 表情包缓存规范（v35.8.1.6）

## 流程

```text
后端返回表情包目录 / 单条表情 URL
→ 客户端下载并保存本地
→ 发送时以图片附件发送
→ 发送前若本地缺失，重新下载并缓存
```

不支持：

```text
只发远程 URL 不落盘
把表情包当文字
把 SVG/可执行文件当表情
```

## 本地结构

```text
sticker_cache
  id
  remote_url
  sha256
  mime
  bytes
  file_path
  created_at
  last_used_at
```

文件目录：

```text
Android：files/stickers/<sha256>.<ext>
Web：IndexedDB / Cache Storage
Qt：QStandardPaths CacheLocation/stickers
HarmonyOS：files/stickers
```

## 发送

```text
1. 查本地缓存
2. 有 → 直接作为图片附件发送
3. 没有 → 下载、校验、写缓存、再发送
4. 发送成功后更新 last_used_at
5. 下载失败 → 回退远程 URL（不写坏缓存）
```

## 30 天清理

```text
每天或启动后异步执行一次
删除 last_used_at 超过 30 天的表情文件
保留：收藏 / 正在发送 / 最近使用
清理失败不阻塞聊天
```

再次使用：

```text
缓存缺失 → 重新下载
重新下载成功 → 恢复缓存并更新 last_used_at
```

## 体积上限

```text
单文件大小上限
缓存总大小上限（如 200MB）
超限按 last_used_at 从旧到新淘汰
```

## 验收

```text
断网时已缓存表情可发送
未缓存表情断网时明确失败
30 天未用会清理
再次使用会重新缓存
发送的是本地图片附件，不是远程 URL 文字
```
