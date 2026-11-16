# v23–v30 宣传片 · 分镜与旁白

> 成片源：[demo-v23-v30.html](demo-v23-v30.html)  
> 时长约 **3 分 31 秒**；浏览器 16:9 全屏，OBS/录屏即可。  
> 参考：[demo-full.html](demo-full.html) 的舞台/分镜方式；本片独立，不覆盖旧片。

## 播放

```bash
# 直接打开
docs/video/demo-v23-v30.html

# 从某场开始
...?scene=v28
```

操作：

```text
空格    暂停/继续
← / →   上一场/下一场
```

## 分镜

| # | 场景 | 时长 | 内容 |
|---|---|---|---|
| 00 | 开场 | 6.5s | 从一本书到一套接口；v23–v30 |
| 01 | 路线 | 12s | 八个版本：隔离 / 读书 / 热更 / TCP / 注册表 / 运行时 / 契约 / 模型插件 |
| 02 | v23 | 14s | users / identities / user_id 隔离 |
| 03 | v24 | 12s | TXT/EPUB、全书连续 1000 字、reading_queue |
| 04 | v25 | 14s | ingress 3001/27004、current、prepare/health/drain |
| 05 | v26 | 14s | 3001 QQ、27004 8+4+body TCP、protobuf、internal.sock |
| 06 | v27 | 14s | PluginManifest / PluginRegistry / MasterRegistry |
| 07 | v28 | 18s | install→pending→approve、权限 0/1/2、stop 跟随 worker |
| 08 | v29 | 18s | ModelProvider、DeepSeek/豆包 native、env gate、静默阅读 |
| 09 | v30 | 16s | ModelRouter、model.<name>@1、异常/停用回落 native |
| 10 | Q&A 开场 | 6.5s | 部署真实踩坑，不是产品 FAQ |
| Q1 | prepare | 9s | No module named bot → v28.8.2 |
| Q2 | schema | 9s | plugin_* 0 张 ≠ 迁移失败；看 schema30 |
| Q3 | env gate | 9.5s | env_report 没 version → v29.4.1；重跑 env_check |
| Q4 | current | 10s | current 已切但 !version 旧 → 旧 WS 钉旧 worker；v29.4.2 SIGKILL |
| Q5 | cwd deleted | 9.5s | 运行中 prepare 同版本 → rmtree；v28.9.1 拒绝覆盖 |
| Q6 | reading | 9s | 自动阅读还发摘要 → 先查 !version/旧 worker；v29.4 只命令回复 |
| 11 | 结尾 | 10s | v30.2.0 · 10045 tests · v45 学习规划 |

## 部署 Q&A 旁白

### Q1 prepare 找不到 bot

```text
prepare_worker 报 No module named 'bot'，
plugin-lock 被跳过。
原因是脚本从 scripts/ 启动，sys.path 里没有项目根。
v28.8.2 把项目根插进 sys.path；
再跑 prepare，应该看到 plugin-lock.json 已写入。
```

### Q2 plugin 表 0 张

```text
迁移显示 plugin_* 表 0 张，不是失败。
[1/8] 建缺表时已经建过了，
[8/8] 再检查自然是 0 张。
确认 schema_version=30、六张 plugin_* 表存在即可。
```

### Q3 env_report 没有 version

```text
v29.3 起，新版本进蓝绿前必须有环境报告。
报告要有 version、未过期、config hash 匹配。
v29.4.1 才真正把 version 写进 preflight 报告；
更新后重跑 checks/env_check.py，再 prepare。
```

### Q4 current 已切，版本还是旧的

```text
current 指向 29.4.1，不代表 NapCat 已经连上新 worker。
旧 WebSocket 还钉在 28.9.1；旧进程收到 SIGTERM 但没退出。
v29.4.2 改成 SIGTERM 等 10 秒，仍存活就 SIGKILL；
旧连接断开，NapCat 重连 current，!version 才是新版本。
```

### Q5 cwd 被删

```text
worker 还在跑，又 prepare 同一个版本。
旧逻辑先 rmtree，把活进程的 cwd 删了；
/proc/PID/cwd 变成 (deleted)，internal.sock、worker.log 跟着消失。
v28.9.1 起检测 worker.pid 活进程，直接拒绝覆盖；
重刷必须用新版本号，或先停 worker。
```

### Q6 自动阅读还在发摘要

```text
先发 !version。
如果还是旧版本，说明旧 worker/旧 WS 还在服务，
不是 v29.4 没生效。
v29.4 规则：自动阅读只写 book_memory/进度；
只有 !book next / !book read 才回复摘要。
```

## 录屏建议

```text
浏览器 1920×1080 全屏
隐藏书签栏
OBS 录制 16:9
开场停 1 秒再播放
Q&A 段可手动 ←/→ 控制节奏
```

## 素材边界

- 不展示真实 QQ 号、服务器 IP、API Key、数据库密码。
- 截图中的聊天内容需先打码/替换。
- 本片只讲 v23–v30；v31 之后是计划，不混入“已实现”。
