# v27–v33 宣传片 · 分镜与旁白

> 成片源：[demo-v27-v33.html](demo-v27-v33.html)  
> 时长约 **5 分 12 秒**；统一深色 REC 控制台主题。  
> 已完成 v27–v33；规划 v34–v37。  
> 全片不需要 `docs/video/assets`，自包含。

## 播放

```bash
docs/video/demo-v27-v33.html

# 从某场开始
...?scene=v33
...?scene=v33b
...?scene=future34
```

```text
空格    暂停/继续
← / →   上一场/下一场
```

## 分镜

| # | 场景 | 时长 | 内容 |
|---|---|---|---|
| 00 | 开场 | 8s | 从注册表到可替换底座；v33 + future |
| 01 | 路线 | 15s | v27–v33 八个节点 + v34–v37 |
| 02 | v27 Manifest | 14s | 身份、契约、capability @1 |
| 03 | v27 MasterRegistry | 13s | 5 个注册表顺序；核心不注册 |
| 04 | v28 安装 | 15s | 目录、hash、pending、approve |
| 05 | v28 运行时 | 16s | 权限三档、错误停用、stop |
| 06 | v29 契约 | 16s | ModelRequest/Reply/Provider；native |
| 07 | v29 边界 | 16s | env gate + 自动阅读静默 |
| 08 | v30 插件 | 14s | ModelRouter、fallback、停用回落 |
| 09 | v31 Store/Retriever | 15s | 记忆接口、BM25、user_id |
| 10 | v31 帮助 | 13s | 动态 !help / API |
| 11 | v32 记忆插件 | 14s | MemoryRouter、权限、回落 |
| 12 | v32 交互 | 15s | cron suffix、多行命令 |
| 13 | v33 六层 | 13s | Channel/Tool/Storage/Scheduler/Transport/Route |
| 14 | v33 规则 | 18s | native 默认、插件候选、收口统计 |
| 15 | 边界 | 11s | 接口层不换核心；同进程不是沙箱 |
| 16 | FUTURE v34 | 18s | 学习规划：7 日列单表，节数可变 |
| 17 | FUTURE v35 | 20s | 推送/本机服务/IDE/命令收敛/客户端 |
| 18 | FUTURE v36 | 20s | 生态接入 + 内容流 |
| 19 | FUTURE v37 | 18s | systemd/嵌入式/恢复/统计 |
| 20 | 结尾 | 10s | v33.7.1.1 · 13105 tests |

## 旁白

### 开场

```text
v27 到 v33，做的是同一件事：
把她从一个能聊的 QQ Bot，
拆成一套可以被替换、被扩展、但仍然稳定的后端。
```

### v27

```text
v27 先定 Manifest 和注册表，不做 loader。
name/author/layer/version，capability 用 model.x@1。
核心只支持 @1；要求 @2 直接拒绝，不降级。
五个注册表按 command → events → life → ai → plugin 初始化。
```

### v28

```text
v28 才把安装、审批、权限、错误和 stop 接上。
安装先复制到 plugins/<layer>/<name>/，hash 判断完整性，
默认 pending；approve 后才启用。
权限 0/1/2，默认 1；db 表级、file 路径级、network host 级。
stop 跟随 worker：cancel tasks → stop(5s) → unregister。
```

### v29–v30

```text
v29 把 DeepSeek 和豆包包成 native provider，
再加蓝绿环境门禁：
env_report 的版本、配置 hash、时效不匹配，拒绝 prepare 和切流。
自动阅读只入库，只有 !book next / !book read 才回摘要。
v30 才允许第三方模型 provider 注册；
失败、无权限、停用都回落 native。
```

### v31–v32

```text
v31 把记忆拆成 MemoryStore 和 Retriever，
BM25 仍是 native；所有接口强制 user_id。
帮助不再手写，!help 从 registry 动态生成。
v32 接第三方记忆实现，
同时补了钩子批量后缀和多行命令。
```

### v33

```text
v33 一次收口六层：
Channel、Tool、Storage、Scheduler、Transport、Route。
每层都是“契约 + native + 插件接入 + 失败回落”。
v33.7.1.1：13105 条测试，0 失败。
```

### 边界

```text
v27–v33 是接口层，不是把现有功能插件化。
核心 native 始终保留；
同进程插件不是沙箱，安装审核仍是边界。
```

### v34–v37

```text
v34：学习规划，一张 study_plans 表，7 个日列，节数可变。
v35：多端与客户端，推送、本机服务、IDE、Web/桌面/手机。
v36：生态接入，QQ空间、运维、B站/抖音、微信、通话、微服务、内容流。
v37：运维与嵌入式，systemd、树莓派/平板、断网恢复、统计收尾。
```

### 结尾

```text
v33 已经把接口铺完；
v34–v37 才是接下来的生活。
这些是计划，不是已实现。
```

## 视觉统一

```text
全片深色 #060a12 底
粉色主强调、蓝色次强调、青色状态
统一卡片 / 代码块 / 结论条
不再交替浅色场景
FUTURE 场景使用黄色 FUTURE 标签
```

## 录屏

```text
浏览器 1920×1080 全屏
隐藏书签栏
OBS 16:9
开场停 1 秒再播放
v33 六层 / FUTURE 可多停 2 秒
```

## 素材边界

- 不展示真实 QQ 号、服务器 IP、API Key、数据库密码。
- v27–v33 已完成；v34–v37 是规划，画面/旁白都标 FUTURE。
- 不把“六层接口”说成“六层功能全部插件化”。
