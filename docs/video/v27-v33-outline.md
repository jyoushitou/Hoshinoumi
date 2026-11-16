# v27–v33 宣传片 · 分镜与旁白

> 成片源：[demo-v27-v33.html](demo-v27-v33.html)  
> 时长约 **3 分 20 秒**；16:9 全屏录屏。  
> 覆盖已完成 v27–v33，以及规划中的 v34–v37。

## 播放

```bash
docs/video/demo-v27-v33.html

# 从某场开始
...?scene=v33
...?scene=future34
```

```text
空格    暂停/继续
← / →   上一场/下一场
```

## 分镜

| # | 场景 | 时长 | 内容 |
|---|---|---|---|
| 00 | 开场 | 6.5s | 从注册表到六层接口；v27–v33 + v34–v37 |
| 01 | 路线 | 13s | 七个已完成版本 + 四个未来版本 |
| 02 | v27 | 12s | Manifest / Registry / MasterRegistry |
| 03 | v28 | 15s | 安装、审批、权限、错误、stop |
| 04 | v29 | 14s | ModelProvider、DeepSeek/豆包 native、env gate、静默阅读 |
| 05 | v30 | 12s | ModelRouter、fallback、停用回落 |
| 06 | v31 | 14s | MemoryStore / Retriever、BM25 native、动态 !help |
| 07 | v32 | 14s | MemoryRouter、cron suffix、多行命令 |
| 08 | v33 | 20s | Channel/Tool/Storage/Scheduler/Transport/Route 六层收口 |
| 09 | 边界 | 10s | 接口层不换核心；同进程插件不是沙箱 |
| 10 | v34 未来 | 14s | 学习规划：7 日列单表，节数可变 |
| 11 | v35 未来 | 16s | 推送/本机服务/IDE/命令收敛/Web/桌面/手机 |
| 12 | v36 未来 | 16s | QQ空间/运维/B站抖音/微信/通话/微服务/内容流 |
| 13 | v37 未来 | 14s | systemd/嵌入式/断网恢复/统计收尾 |
| 14 | 结尾 | 9s | v33.7.1.1 · 13105 tests · v34–v37 planned |

## 旁白要点

### 开场

```text
v27 到 v33，做的是同一件事：
把“她”从一个能聊的 QQ Bot，
拆成一套可以被替换、被扩展、但仍然稳定的后端。
```

### v27–v28

```text
v27 先定契约和注册表，不做 loader；
v28 才把安装、审批、权限、错误和 stop 接上。
核心 native 不实现 manifest，也不进入插件表。
```

### v29–v30

```text
v29 把 DeepSeek 和豆包包成 native provider，
再加一层蓝绿环境门禁；
v30 才允许第三方模型 provider 注册，
但默认仍走 native，失败/停用/无权限都回落。
```

### v31–v32

```text
v31 把记忆拆成 MemoryStore 和 Retriever，
BM25 仍是 native；
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

## 录屏

```text
浏览器 1920×1080 全屏
隐藏书签栏
OBS 16:9
开场停 1 秒再播放
v33 六层可多停 2 秒
```

## 素材边界

- 不展示真实 QQ 号、服务器 IP、API Key、数据库密码。
- v27–v33 是已完成；v34–v37 是规划，画面/旁白都明确标注 FUTURE。
- 不把 v33 的“六层接口”说成“六层功能全部插件化”。
