# v14.2 发布说明

- 发布时间：2026-11-09 13:41
- 上一个版本：v14.1
- 提交数：2

## 本次变更

- e90a32d fix: 发图闸门只堵了主路径，jieba 兜底仍在每条回复配图
- ba0bdd4 feat: 更新 .gitignore 文件，添加 dist/ 目录以排除打包文件；新增发布脚本以简化发布流程

## 升级步骤

```bash
git pull ./nao-14.2.bundle main
python3 scripts/preflight.py
python3 -m unittest discover -s tests
# 重启进程
```

## 回滚

```bash
git reset --hard v14.1
```
