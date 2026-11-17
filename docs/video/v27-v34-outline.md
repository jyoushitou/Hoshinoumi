# v27–v34 宣传片 · 分镜与旁白

> 成片源：[demo-v27-v34.html](demo-v27-v34.html)  
> 时长约 **6 分 17 秒**；统一深色 REC 控制台主题。  
> 已完成 v27–v34；规划 v35–v39。  
> 自包含，不依赖 `docs/video/assets`。

## 播放

```bash
docs/video/demo-v27-v34.html

# 从某场开始
...?scene=v33
...?scene=v34a
...?scene=future37
```

```text
空格    暂停/继续
← / →   上一场/下一场
```

## 分镜

| # | 场景 | 时长 | 内容 |
|---|---|---|---|
| 00 | 开场 | 8s | 从注册表到六层接口，再到她的计划 |
| 01 | 路线 | 16s | v27–v34 八个节点 + v35–v39 FUTURE |
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
| 16 | v34 学习规划 | 18s | study_plans 单表、7 日列、节数可变 |
| 17 | v34 情境 | 18s | owner_presence、reporter、TTL、隐私 |
| 18 | FUTURE v35 | 22s | 多端与客户端：IDE→聊天室→四端 |
| 19 | FUTURE v36 | 22s | 插件增强：API v2、hooks、前端插件 |
| 20 | FUTURE v37 | 22s | 情感增强：20 维、60 标签、人设卡 v2 |
| 21 | FUTURE v38 | 20s | 生态接入：QQ空间/运维/视频/微信/通话/内容流 |
| 22 | FUTURE v39 | 18s | 运维与嵌入式：systemd/树莓派/恢复 |
| 23 | 结尾 | 10s | v34.3.0.0 · 13134 tests |

## 旁白

### 开场

```text
v27 到 v34，做的是同一件事：
先把她拆成可替换的接口，
再用这些接口，做她自己的生活。
```

### v27–v28

```text
v27 先定 Manifest 和注册表，不做 loader。
name/author/layer/version，capability 用 model.x@1。
五个注册表按 command → events → life → ai → plugin 初始化。
v28 才把安装、审批、权限、错误和 stop 接上。
权限 0/1/2，默认 1；stop 跟随 worker。
```

### v29–v30

```text
v29 把 DeepSeek 和豆包包成 native provider，
再加蓝绿环境门禁；
自动阅读只入库，只有命令才回摘要。
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

### v34 学习规划

```text
v34 把学习规划做成一等能力。
一张 study_plans 表，一周一行；
周一到周日 7 列，每列 JSON 数组，每天节数可变。
不拆 items/events，不占 cron_tasks；
!plan 导入、查看、完成、跳过、顺延、统计。
```

### v34 主账号情境

```text
除了计划，她还知道你现在在做什么。
reporter 每 30 秒读前台应用和空闲时间，
只映射粗类：coding / meeting / video / gaming / reading / eating / away。
owner_presence TTL 5 分钟；unknown 不注入；
meeting/away 时主动消息静默。
默认不保存窗口标题；raw_title 要显式开关。
```

### 边界

```text
v27–v33 是接口层，不是把现有功能插件化。
核心 native 始终保留；
同进程插件不是沙箱，安装审核仍是边界。
```

### v35–v39

```text
v35：多端与客户端，先本机服务/IDE，再聊天室、Web、桌面、手机。
v36：插件增强，API v2 可以改完整功能，但不能拿走控制权。
v37：情感增强，20 维关系、60 标签、人设卡 v2，默认开启。
v38：生态接入，QQ空间、运维、B站/抖音、微信、通话、微服务、内容流。
v39：运维与嵌入式，systemd、树莓派/平板、断网恢复、统计收尾。
```

### 结尾

```text
v34 已经把计划和情境接上；
v35–v39 才是接下来的多端、生态和运维。
这些是计划，不是已实现。
```

## 视觉统一

```text
全片深色 #060a12 底
粉色主强调、蓝色次强调、青色状态
统一卡片 / 代码块 / 结论条
FUTURE 场景使用黄色 FUTURE 标签
v34 用绿色 DONE 标签
```

## 录屏

```text
浏览器 1920×1080 全屏
隐藏书签栏
OBS 16:9
开场停 1 秒再播放
v33 六层 / v34 / FUTURE 可多停 2 秒
```

## 素材边界

- 不展示真实 QQ 号、服务器 IP、API Key、数据库密码。
- v27–v34 已完成；v35–v39 是规划，画面/旁白都标 FUTURE。
- 不把“六层接口”说成“六层功能全部插件化”。
