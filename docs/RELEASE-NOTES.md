# v18.5.0 发布说明

- 发布时间：2026-11-12 15:55
- 上一个版本：v18.4.0
- 提交数：3

## 本次变更

- 308d166 feat: v18.5 补完 uptime 与元数据视图（L6）
- dcd83a3 feat: 更新 ROADMAP 和 v21 文档，添加插件接入模式配置说明
- 1a9f73c feat: Update versions v32 to v35 with new features and improvements

## 升级步骤

```bash
git pull ./nao-v18.5.0.bundle main
python3 scripts/preflight.py
python3 -m unittest discover -s tests
# 重启进程
```

## 回滚

```bash
git reset --hard v18.4.0
```
