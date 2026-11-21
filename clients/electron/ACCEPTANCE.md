# 桌面壳验收清单（v35.6）

## 启动

```powershell
cd integrations/web
pnpm build
cd ../../clients/electron
pnpm start
```

## 窗口

- [ ] 默认 1440×900
- [ ] 最小 1180×760，拖动缩放不压缩三栏
- [ ] 任务栏图标为 Hoshinoumi logo

## 路由

- [ ] /chat
- [ ] /home
- [ ] /memory
- [ ] /relation
- [ ] /savings
- [ ] /weekly
- [ ] /info
- [ ] /persona
- [ ] /commands
- [ ] /cron
- [ ] /logs
- [ ] /settings

## 托盘 / 小窗

- [ ] 托盘图标可见（可能在 ^ 溢出区）
- [ ] 左键显示/隐藏主窗口
- [ ] 右键菜单：打开主窗口 / 迷你窗口 / 设置 / 检查更新 / 回退上一版本 / 退出
- [ ] 迷你窗口默认关闭
- [ ] 设置启用后，迷你窗口 360×130、无边框、置顶

## 设置

- [ ] 后端入口保存后 API 请求使用新入口
- [ ] API 前缀生效
- [ ] 启动页保存后重载进入对应路由
- [ ] 更新源 URL 保存

## 兜底

- [ ] 前端加载失败时显示本地兜底页
- [ ] 兜底页可重新加载
- [ ] 渲染进程崩溃写入 shell.log 并回退

## 已知环境参数

```text
--no-sandbox
--disable-gpu
--disable-crash-reporter
--user-data-dir=<clients/electron/.electron-data>
```
