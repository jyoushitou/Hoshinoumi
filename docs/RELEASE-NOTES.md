# v15.0 发布说明

- 发布时间：2026-11-09 14:25
- 上一个版本：v14.2
- 提交数：1

## 本次变更

- b2191ee feat: 添加可调参数功能，支持运行时修改并持久化；新增今日统计命令

## 升级步骤

```bash
git pull ./nao-15.0.bundle main
python3 scripts/preflight.py
python3 -m unittest discover -s tests
# 重启进程
```

## 回滚

```bash
git reset --hard v14.2
```
