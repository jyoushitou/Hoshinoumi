# 实例数据导出 / 备份 / 迁移

目标：运行中的实例可以完整导出，换机器/换实例后快速恢复。

## 导出内容

```text
manifest.json
db（SQLite 备份 / MySQL dump）
data/
  stickers/
  attachments/
  appearance/
  books/
  personas/
  plugin-data/
config（脱敏，默认不含密钥）
checksums.txt
```

不导出：

```text
.venv
缓存 / tmp
日志归档（可选）
release keystore（单独离线备份）
```

## 归档格式

```text
instance-<id>-<version>-<timestamp>.hshbackup
zip（流式写入，不整包进内存）
```

`manifest.json`：

```text
schema_version
app_version
instance_id
created_at
db_backend
file_count
total_bytes
contains_secrets（默认 false）
sha256 per file
```

## 一致性

```text
SQLite：sqlite3 backup API，不直接 cp 正在写的库
MySQL：事务一致性 dump
文件：先写临时目录/快照，再打包
导出期间不阻塞聊天读取
```

## 安全

```text
仅 owner
一次性导出 token
下载链接短期有效
默认不导出 API key/token/密码
需要密钥时用口令加密，口令不进归档
```

## 导入 / 迁移

```text
1. 校验 manifest / schema_version / checksums
2. 检查磁盘空间
3. 停写或进入维护模式
4. 备份当前实例
5. 恢复 DB + data/
6. 启动自检
7. 失败回滚到导入前
```

不允许：

```text
路径穿越
覆盖不匹配 schema 的库
导入到非空实例时静默合并
```

## 命令

```bash
nao-run export --out instance.hshbackup
nao-run import --from instance.hshbackup --dry-run
nao-run import --from instance.hshbackup
```

## UI

```text
设置 → 信息 → 实例数据
  导出实例数据（进度 / 大小）
  导入实例数据（选择文件 / 校验 / 恢复）
```

## 版本

| 版本 | 内容 | 验收 |
|---|---|---|
| v35.9.3.2 | 导出 manifest / DB / data / checksums | 归档可解压、校验通过 |
| v35.9.3.3 | 导入校验 / 恢复 / 失败回滚 | 新实例可启动 |
| v35.9.3.4 | CLI + 设置页导出/导入进度 | 命令行与页面可用 |
| v35.9.3.5 | 实例迁移演练 / 大文件 / 断点 | 换机迁移通过 |
