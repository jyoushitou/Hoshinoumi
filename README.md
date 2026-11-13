# Hoshinoumi（REC） v20.5

> 后端 **v20.5** · 网关 **v20.5**（Docker / 网关验证）· **已部署试运行**
> v19 与 v20.0–v20.4 已完成，当前在做 Docker 与网关验证。

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
![C++17](https://img.shields.io/badge/C%2B%2B-17-00599C)
![Boost.Asio](https://img.shields.io/badge/Boost.Asio%2FBeast-vcpkg-6D4C9F)
![CMake](https://img.shields.io/badge/CMake-3.20%2B-064F8C)
![Docker](https://img.shields.io/badge/Docker-compose-2496ED)
[![Database](https://img.shields.io/badge/Database-MySQL%20%7C%20SQLite-4479A1)](#)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-5C2D91)](#)
[![NapCat](https://img.shields.io/badge/NapCat-QQ-12B7F5)](#)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
![Backend](https://img.shields.io/badge/Backend-v20.5-yellow)
![Gateway](https://img.shields.io/badge/Gateway-v20.5-blue)
![Version](https://img.shields.io/badge/Version-v20.5-orange)
![Tests](https://img.shields.io/badge/Tests-969%20passing-brightgreen)

> **Hoshinoumi（REC，记录）** · 友利奈绪 · 星之海学园学生会室
>
> 一个以 QQ 为入口、带长期记忆与情绪状态的 AI 陪伴后端；支持多端 API、定时主动、语音、图像与小说阅读。
>
> 仓库：<https://github.com/jyoushitou/Hoshinoumi>
>
> 世界观取自原作结局之后：能力消失，回归普通生活；**乙坂有宇已经意外去世**。
> 提到他需要克制，可以打哑谜，但不能假装他还活着。

基于 **NapCat** 收 QQ 消息，**Python** 后端，**DeepSeek** 为主模型、**豆包** 兜底，
MySQL（连不上自动退 SQLite）存记忆与日志。图片由她自己一句话打标签，正文小说用**截图 + OCR** 还原。

---

## 项目介绍

### 一句话

这不是一个“接上模型就能聊天”的 QQ 机器人，而是一个**有长期记忆、有生活状态、会主动找人、能换人设**的陪伴后端。

它把“她”拆成几件可以各自维护的事：

| 层 | 管什么 |
|---|---|
| 人设 | 她是谁、怎么说话、在意什么 |
| 记忆 | 记得你说过什么、哪些事重要 |
| 生活 | 心情/精力/孤独、今天发生了什么 |
| 关系 | 认识多久、亲近还是疏远、有没有闹别扭 |
| 表达 | 分几条、隔多久、发文字还是语音/图 |
| 调度 | 什么时候主动、什么时候该安静 |
| 接口 | QQ、HTTP、网关、以后更多客户端 |

**模型只负责“这一句怎么说”**；上面那些东西不放在 prompt 里硬编，而是放在表和状态里，由代码在每次回复前组装。

### 它不是什么

| 不是 | 说明 |
|---|---|
| 不是通用客服/问答机器人 | 它没有“知识库问答”目标，回答首先服从人设和关系 |
| 不是多租户 SaaS | 当前单主人 `__owner__`；多用户是 v23 计划 |
| 不是公网即开即用 | 网关当前没有 JWT/限流/TLS；只适合本机/内网验证 |
| 不是“装完就懂你” | 记忆需要聊出来；人设需要调；它不会读心 |
| 不是无依赖一键包 | 读书要 Playwright/tesseract；语音要 edge-tts；模型要 API Key |
| 不是角色扮演框架 | 它只服务一个角色卡体系；换人是换 `personas/`，不是做平台 |

### 适合谁 / 不适合谁

**现在适合：**

| 人群 | 为什么适合 |
|---|---|
| 想长期养一个固定角色的个人用户 | 有长期记忆、关系、生活状态，不是一次性问答 |
| 有 Linux / Windows 基础，能跑 Python / Docker / MySQL 的人 | 需要自己部署、迁移、备份、看日志 |
| 喜欢二次元角色、愿意调人设和语气的人 | 人设外置在 `personas/`，可以改 |
| 单主人 / 小圈子自用 | 当前是 `__owner__` 单用户模型，不是多租户 |
| 想研究 AI 角色架构的开发者 | 分层、记忆、调度、网关、C++ 网关都有真实实现 |
| 有 QQ 小号 / NapCat 使用经验的人 | 需要自己承担平台风控和账号风险 |

**现在不适合：**

| 人群 | 为什么不适合 |
|---|---|
| 想“下载完就自动能用”的零基础用户 | 需要数据库、API Key、NapCat、端口配置 |
| 想要商业客服 / 知识库问答机器人的人 | 它优先服从人设和关系，不是客服 |
| 需要多租户 SaaS、高并发、合规审计的团队 | 多用户是 v23 计划；当前没有完整鉴权/限流 |
| 不能接受 QQ 平台风控 / 角色 IP 二创风险的人 | 这是自托管二创项目，不是官方产品 |
| 期待开箱即用的语音通话 / 手机 App / 桌面端的人 | 这些在 v34+ 计划里，当前还没做 |
| 不愿意维护数据库、备份、升级的人 | 长期记忆和角色状态都在数据库里 |
| 要求“零 bug、零配置、零运维”的人 | 项目还在快速迭代，边界和文档会变 |

一句话：

```text
想 10 分钟试一下 -> 不适合
想长期养一个角色，并且愿意自己维护 -> 适合
```

### 后面可能适合的人

这些要等对应版本完成，不是现在就能用：

| 版本/方向 | 可能的人群 |
|---|---|
| v21–v23 | 愿意自托管的小团队、家庭、朋友共用；需要 owner 鉴权和多用户隔离 |
| v24–v32 | 第三方开发者：写模型 provider、检索器、通道、工具、存储、调度、传输适配器 |
| v33 | 需要多端主动消息的人：QQ、Web、桌面、手机、嵌入式屏 |
| v34 | 用 DSH / Qoder / WorkBuddy 的开发者：希望 IDE 里也能调用同一个“她” |
| v35–v52 | 想要 Web / Linux 桌面 / Windows 桌面 / 手机 App / 嵌入式屏的人 |
| 长期 | 写作辅助、跑团/角色扮演、个人知识陪伴、AI 角色研究、小社区自托管 |

仍然不适合的方向：

- 大规模商业客服
- 需要官方 QQ 机器人合规资质的场景
- 不愿意自己维护服务器和数据的用户
- 把角色二创直接当官方 IP 商业售卖的团队

### 它解决什么问题

| 常见 QQ Bot | 这个项目 |
|---|---|
| 每次对话从零开始 | 30 轮对话 + 长期记忆 + 事实卡 + 关系里程碑 |
| 人设写死在 prompt 里 | 人设外置到 `personas/`，四个文件可换 |
| 只会被动回消息 | 定时/主动/空闲/日程四类事件，会自己找事做 |
| 回复永远一个语气 | 心情/精力/孤独/关系档位共同影响语气 |
| 所有消息一口气发 | 分条、延迟、连发合并、语音/贴图择时 |
| 出站散落各处 | 唯一出站口，锁/队列/断线补发/echo |
| 换模型要改代码 | 当前 DeepSeek/豆包是核心 native；后续暴露 ModelProvider 接口，新增模型可走插件，核心不强制插件化 |
| 没有观测 | `!status` `!stats` `!usage` `!db` `!hooks` 可看 |

### 设计理念

1. **记忆优先于 prompt**：能存表里的，不塞 prompt；能检索的，不靠模型“记住”。prompt 只放这次真正需要的信息。

2. **生活感来自状态，不来自随机话术**：心情/精力/孤独随时间漂移；生活事件写进记忆；主动消息有触发条件，不是随机骚扰。

3. **人格与代码分离**：角色卡是数据，不是代码。换人设不改 Python；`!persona` 下一句生效。

4. **所有发送只有一个出口**：并发下 WebSocket 帧会交错；出站层负责锁、队列、断线补发、echo 等待。业务不许直接 `ws.send`。

5. **聊天不排在后台任务后面**：读书/抓取/浓缩是 P2；聊天是 P0。她可以慢慢读书，但不能让回消息变慢。

6. **先做深，再做宽**：当前把单主人体验做完整；多用户、Web/桌面/手机、分层插件接口都在后续版本，不提前背复杂度。

7. **可观测、可降级、可回滚**：模型失败有兜底；OCR/语音缺依赖降级；迁移默认 dry-run；备份/回滚有文档。

8. **本地优先，公网最小暴露**：后端只监听本机；公网走独立网关；密钥不进 git；网关鉴权还没做，所以不吹“安全公网”。

### 一次典型的一天

> 下面是“她”的日常，不是固定脚本；时间/频率都可在 `!config` 和 `cron_tasks` 里调。

| 时段 | 她在做什么 |
|---|---|
| 早上 | 按起床规则发一条；看你昨晚有没有说话；心情低就少说两句 |
| 白天 | 回消息、记事情、偶尔主动搭话；群聊只接 @/允许的消息 |
| 午间 | 提醒午睡/叫起；你忙就安静，不刷屏 |
| 傍晚 | 提醒晚餐；把今天的生活事件写进记忆 |
| 深夜 | 催睡觉；你还不睡就再催一次；太晚不主动打扰 |
| 空闲 | 读书、抓章节、浓缩长对话、写日记；P2 优先级，不抢聊天 |
| 周日 | 复盘这一周；该记的记，该翻篇的翻篇 |

这些行为不是“定时发固定句子”，而是：**定时/事件触发 → 查状态和记忆 → 决定说不说 → 走统一出站**。

### 能力地图

| 域 | 能力 | 入口 |
|---|---|---|
| 对话 | 私聊/群聊、@、引用、命令 | QQ / `/api/chat` |
| 记忆 | 对话记忆、长期记忆、事实卡、关键词、浓缩 | `!memory` / `!memorybook` / `!event` |
| 关系 | 亲密度、档位、里程碑、摩擦/冷战/和好 | `!growth` / `!profile` |
| 生活 | 心情/精力/孤独、生活事件、日记 | 自动 / `!diary` |
| 表达 | 分条、延迟、语音、贴图、图片 | 自动 / `!voice` / `!img` |
| 阅读 | 番茄章节、OCR、书架、分享 | 自动 / `!diary` |
| 定时 | cron、日程、待办、提醒、钩子 | `!cron` / `!todo` / `!hooks` |
| 人设 | 角色卡切换、导出、占位符 | `!persona` / `scripts/export_persona.py` |
| 观测 | 状态、统计、用量、日志、DB | `!status` / `!stats` / `!usage` / `!log` / `!db` |
| 接口 | 本机 API、Bearer Token、内部接口、网关 | `/api/*` / `/internal/*` / `gateway/` |

### 适合谁

| 适合 | 不适合 |
|---|---|
| 想要一个“记得住、有脾气”的私人 QQ 陪伴 | 想要开箱即用的客服/知识库 |
| 愿意改人设、调参数、看日志 | 完全不想碰配置和命令行 |
| 有 Linux 小服务器/常开机器 | 只想白嫖公共 API、不准备 Key |
| 能接受“她有时候会闹别扭/说错话” | 要求 100% 事实准确、永不跑偏 |
| 想研究记忆/调度/出站怎么落地 | 想直接做多租户商业产品 |

### 项目边界

| 不做 | 原因 |
|---|---|
| 不做通用 Agent 平台 | 当前只服务一个角色/一个主人 |
| 不做公网 SaaS | 鉴权/限流/多用户还没做 |
| 不做模型训练/微调 | 只接 API |
| 不做“永远正确”的知识库 | 人设优先，事实其次；重要事实走 `facts` |
| 不保证 100% 不崩 | 有看门狗/降级/备份，但不是高可用系统 |
| 不隐藏限制 | README 的“已知限制”比宣传多 |

### 名字

| 名字 | 含义 |
|---|---|
| **Hoshinoumi** | 星之海；她所在的世界，不是某个技术组件 |
| **REC** | Record/录制；记忆、日记、对话都是“被录下来的东西” |
| **友利奈绪** | 角色名，不改；产品名和角色名分开 |
| **NapCat + Python** | 实现方式，不是产品名 |

### 怎么读这份 README

| 你是 | 先看 |
|---|---|
| 第一次来 | 这一节 → 特性一览 → 快速开始 |
| 要部署 | 快速开始 → 网关 → 附录 G 部署 Runbook |
| 要改人设 | 角色卡 → `personas/` |
| 要调行为 | 核心机制 → 配置项速查 → 附录 E |
| 要排障 | 附录 I 故障排查 → 日志/`!status` |
| 要参与开发 | 架构 → 目录布局 → 附录 H 测试地图 → `docs/versions/` |

---

## 技术栈

| 部分 | 技术 |
|---|---|
| **Python 后端** | Python 3.10+、asyncio、websockets（NapCat 通道）、aiohttp（HTTP API）、PyMySQL / SQLite、requests、Pillow、jieba、edge-tts、Playwright、tesseract |
| **C++ 网关（v20）** | C++17、Boost.Asio / Boost.Beast、CommonNet（NetWorkCommunication / Utils）、CMake 3.20+、vcpkg overlay ports |
| **存储** | MySQL 8（默认）/ SQLite（自动回退） |
| **部署** | Docker / docker compose、systemd、Windows / Linux |
| **外部服务** | NapCat（QQ 协议）、DeepSeek（主对话）、豆包 / 火山方舟（视觉）、ALAPI（搜图） |

> 网关是独立的 C++ 进程：`gateway/`；Python 后端是 `bot/`。两者只通过本机 HTTP 对接，后端不监听公网。

## 特性一览

| 能力 | 说明 |
|---|---|
| **可换角色** | 人设、生活模板、状态基线全在 `personas/<名字>/`，改文件就换人 |
| 说话像人 | 分条发送、按时段浮动延迟、语气受情绪影响 |
| 记得住 | 30 轮对话 + 长期记忆（BM25 + 关键词双路 RRF）+ 关系里程碑 |
| 有自己的生活 | 心情/精力/孤独随时间漂移，会写日记、会主动找你 |
| 会看图 | 多模态直接看，动图抽 24 帧拼网格 |
| 会说话 | edge-tts 语音，按心情和长度低频触发 |
| 会听 | 语音条转写（能转就转，不能就记一笔） |
| 会读小说 | 空闲时自己抓番茄章节（OCR 还原），攒够几章跟你分享 |
| 有摩擦 | 期待、失落、冷战、和好（24 小时自动恢复） |
| 能调参 | `!config` 改频率/概率，`!stats` 看今日数据，不用重启 |
| 跑得动 | 阻塞调用统一线程池（13 处），连接池复用 MySQL 连接 |
| 引用上下文 | 引用消息直接带原话；缓存未命中 2 秒超时，不卡 8 秒 |
| 定时更准 | 规则化起床/睡觉/晚餐；`今天 7:40 叫我` 只改当天；准点提醒预生成 |
| 会回忆 | 重记忆会自己冒出来（每天最多一次，心情差时不提旧伤口） |
| 能备份 | 每月 1 号 04:30 自动备份，保留 6 份；`!backup` 看清单/立即备份 |
| C++ 网关 | 用户自己的 CommonNet（Boost.Asio/Beast）；后端只监听本机，Docker 交付 |
| 查版本 | `!version` 看版本号、提交、运行时长 |

**969 条测试**（功能 932 + 环境/迁移 37），静态检查零未定义名字。

---

## 开发计划

**当前：v20.5 已部署试运行（Docker / 网关验证）**｜v19 与 v20.0–v20.4 已完成；下一站 v21 owner 鉴权。

> v18 已完成；当前 v19 试运行，试运行期间的问题统一记入 [v19 文档](docs/versions/v19.md)。

| 系列 | 主题 | 状态 | 文档 |
|---|---|---|---|
| v5 ~ v13 | 说话节奏 / 记忆 / 生活 / 感官 / 摩擦 | ✅ 已发布 | [versions/](docs/versions/) |
| v14 ~ v15 | 可换角色 / 调参与观测 | ✅ 已发布 | [v14.md](docs/versions/v14.md) |
| **v16** | **读小说（番茄 OCR + HTML 合并）** | ✅ 已发布 | [v16.md](docs/versions/v16.md) |
| v17 | 执行模型重构：阻塞池 → 事件/调度 → 出站层 → 主循环瘦身 | ✅ 已发布（v17.17） | [v17.md](docs/versions/v17.md) |
| v18 | 情感的深刻度：记忆分轻重、情绪跨天、时间与日志修复 | ✅ 已完成（v18.20.0） | [v18.md](docs/versions/v18.md) |
| v19 | 架构重构 + 对话同步底座：迁移单一入口、`conversation_messages`、`!history`、语音分段 | ✅ 已完成（v19.5.7） | [v19.md](docs/versions/v19.md) |
| v20 | 网关（一）核心：C++/CommonNet + REST↔后端 HTTP + Docker + 配置向导 | 🚧 v20.5 试运行（Docker/网关验证） | [v20.md](docs/versions/v20.md) |
| v21 | 网关（二）owner 鉴权：JWT/刷新/失败锁定 | 📋 已规划 | [v21.md](docs/versions/v21.md) |
| v22 | 网关（三）安全：限流/审计/TLS/`!gw` | 📋 已规划 | [v22.md](docs/versions/v22.md) |
| v23 | 多用户 + 亲密度下降/修复：users/roles + user_id 隔离 | 📋 已规划 | [v23.md](docs/versions/v23.md) |
| v24 | 插件接口实现 | 📋 已规划 | [v24.md](docs/versions/v24.md) |
| v25 | 模型层接口实现 | 📋 已规划 | [v25.md](docs/versions/v25.md) |
| v26 | 记忆层接口实现 | 📋 已规划 | [v26.md](docs/versions/v26.md) |
| v27 | 通道层接口实现 | 📋 已规划 | [v27.md](docs/versions/v27.md) |
| v28 | 工具层接口实现 | 📋 已规划 | [v28.md](docs/versions/v28.md) |
| v29 | 存储层接口实现 | 📋 已规划 | [v29.md](docs/versions/v29.md) |
| v30 | 调度层接口实现 | 📋 已规划 | [v30.md](docs/versions/v30.md) |
| v31 | 出站层接口实现 | 📋 已规划 | [v31.md](docs/versions/v31.md) |
| v32 | 默认链路选择实现 | 📋 已规划 | [v32.md](docs/versions/v32.md) |
| v33 | 多端推送：主动消息扇出到所有接入口 | 📋 已规划 | [v33.md](docs/versions/v33.md) |
| v34 | DSH / Qoder / WorkBuddy 插件：她成为你所有工具的记忆层 | 📋 已规划 | [v34.md](docs/versions/v34.md) |
| v35 | 电脑 Web：聊天 + 历史 + 功能面板 | 📋 已规划 | [v35.md](docs/versions/v35.md) |
| v36 | 桌面端（一）Linux：Tauri + Web UI | 📋 已规划 | [v36.md](docs/versions/v36.md) |
| v37 | 桌面端（二）Windows：Tauri + WebView2 | 📋 已规划 | [v37.md](docs/versions/v37.md) |
| v38 | 手机 App（Flutter）+ 推送通知 | 📋 已规划 | [v38.md](docs/versions/v38.md) |
| v39 | 手机 App 独立模式：后端不可达直连 DeepSeek，恢复立即同步 | 📋 已规划 | [v39.md](docs/versions/v39.md) |
| v40 | QQ 空间：发说说 + 只对熟人点赞/评论 | 📋 已规划 | [v40.md](docs/versions/v40.md) |
| v41 | 运维（一）bash 只读 | 📋 已规划 | [v41.md](docs/versions/v41.md) |
| v42 | 运维（二）agent | 📋 已规划 | [v42.md](docs/versions/v42.md) |
| v43 | 运维（三）有限写 | 📋 已规划 | [v43.md](docs/versions/v43.md) |
| v44 | 运维（四）可写体系 | 📋 已规划 | [v44.md](docs/versions/v44.md) |
| v45 | 视频（一）B 站 | 📋 已规划 | [v45.md](docs/versions/v45.md) |
| v46 | 视频（二）抖音 | 📋 已规划 | [v46.md](docs/versions/v46.md) |
| v47 | 微信接入（OpenClaw） | 📋 已规划 | [v47.md](docs/versions/v47.md) |
| v48 | 语音通话 | 📋 已规划 | [v48.md](docs/versions/v48.md) |
| v49 | 视频通话 | 📋 已规划 | [v49.md](docs/versions/v49.md) |
| v50 | 微服务接入：融进自有 Web，探网关 5 次 + 池复用 | 📋 已规划 | [v50.md](docs/versions/v50.md) |
| v51 | 常驻（后端）systemd / 看门狗 | 📋 已规划 | [v51.md](docs/versions/v51.md) |
| v52 | 嵌入式前端（Linux 后端）：树莓派/平板显示对话 | 📋 已规划 | [v52.md](docs/versions/v52.md) |

> **插件接口原则**：v24–v32 暴露的是各架构层的接口，不是把现有功能插件化。
> DeepSeek/豆包、BM25、QQ/NapCat、现有工具/命令、MySQL/SQLite、asyncio 调度、
> WebSocket 出站都保持核心 native；外部插件只能 extend / enhance / 显式 replace 路由，
> 禁用/卸载/失败时回退核心。
>
> **核心范围**：文档里所有 **vXXX 功能都是核心功能**，包括 v23 之前的聊天、记忆、
> 命令、定时、语音、视觉、读书、OCR、备份、主动消息，以及 v24–v32 的接口定义。
> v24–v32 本身不是插件，也不是功能实现；后续版本也不会用插件接口实现功能。
>
> **插件接口只给第三方做优化/性能扩展**：例如更快的模型 provider、外部向量检索、
> 自定义通道；核心实现始终保留。核心功能只能在启动前通过 `config/features.json`
> （或 `NAO_FEATURES`）关闭；没有对应开关的默认常开。插件管理器不能 disable/uninstall 核心功能。

> **约定**：每个大版本的**最后一个次版本**用来收尾修 bug 和技术债，不堆新功能。

> v17.11 起**MySQL 连不上会自动退 SQLite**；备份/恢复见 [docs/存储后端与备份.md](docs/存储后端与备份.md)。

> v17.12 起语音带**情绪与声线**：语气随心情变，声线跟角色卡走。


- **细到每个小版本**（`x.y.z` 级）的拆解与验收点：[ROADMAP.md](docs/ROADMAP.md)
- **数据库设计**（一表一职责）：[DB-DESIGN.md](docs/DB-DESIGN.md)
- **未排期需求**（A~E 组）：[V14-后续清单.md](docs/V14-后续清单.md)
- **v6 功能总表**（74 项封版）：[V6-功能.md](docs/V6-功能.md)

> 规矩：v6–v16 范围内的问题直接改代码；**超出范围的新需求先写进清单**，不直接动代码。

---

## 目录布局

```
项目根/
├── bot/            机器人代码（分层包）
├── gateway/        C++ 网关（v20，CommonNet + Docker）
├── tests/           功能测试（分模块 + 冒烟，932 条）
├── checks/          前置环境监测 + 迁移检查（37 条，与 bot 同级）
├── scripts/         迁移 / 打包 / 发布 / 自检脚本
├── docs/            版本计划、架构图、数据库设计、发布清单
├── personas/        角色卡（可换人设）
├── release/         打包与发布产物（不进版本库）
├── config.example.json   配置模板
├── config.local.json    真实配置（不进版本库）
└── run.py           启动入口
```

`release/` 里放所有交付物：

```
release/
  REC-v20.5.0-bundle.bundle  git 包（传服务器用）
  REC-v20.5.0-src.zip        源码包（给别人）
  REC-v20.5.0-full.zip       整包（带依赖，可选）
  REC-v20.5.0-exe[.exe]      单文件可执行（可选）
  REC-v20.5.0-docker.tar.gz  后端 Docker 镜像（可选）
  REC-v20.5.0-gateway-docker.tar.gz  网关 Docker 镜像
  REC-v20.5.0-SHA256SUMS.txt 校验和
  # v19.5.7 及更早的 REC-v19.5.7-* / nao-v* 产物保留，不删除
  # 历史 nao-v* / nao-bot-* 产物保留，不再由脚本生成
  old/                      历史包（保留最近 5 个，其余归档到这里）
```

一键跑测试：

```bash
python3 scripts/run_tests.py            # tests + checks
python3 scripts/run_tests.py --fast     # 只跑功能测试
```

---

## 架构

```
run.py → app.bootstrap → app.loop
                 │
  接入(WS/HTTP/定时) → 调度器 → 业务/能力层 → 基础层 → MySQL/SQLite
                 │
            唯一出站口 egress.outbound → ws.send
```

完整分层图、消息生命周期、调度器模型、已知架构债：

> **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** —— 架构图
> **[docs/ARCH-REVIEW.md](docs/ARCH-REVIEW.md)** —— 审查结论与修复顺序（v18.20，综合 6.2/10）

三条硬约束：

| 约束 | 违反的后果 |
|---|---|
| 所有发送只走 `egress.outbound` | 并发时帧交错（心跳插进气泡中间） |
| 阻塞调用只走 `run_blocking` | 卡住的请求永久占线程，池慢慢空 |
| P0 聊天不排队 | 读书/抓取时回消息变慢 |

---


> **新功能一律先进 `docs/versions/` 的开发计划，再按版本迭代。**
> 已发布版本冻结，bug 记进下一个版本的「遗留问题」。

> **启动/升级固定三步**：
>
> ```bash
> python3 scripts/migrate.py --apply   # 1. 迁移（首次/升级；幂等，没东西可迁也会跳过）
> python3 checks/env_check.py          # 2. 严格环境监测（任何 FAIL 都不启动）
> python3 run.py                       # 3. 启动
> ```
>
> 首次机器先 `python3 -m pip install -r requirements.txt`。完整升级/回滚：
> [v19 开发记录](docs/versions/v19.md)。

## 快速开始

### 环境要求

- Python 3.10+
- MySQL 8（25 张表 + 1 视图，见下文）
- NapCat（QQ 协议端，WebSocket 连到本机 3001）

### 首次配置（v16 起必做）

数据库信息和主人 QQ **不再写死在代码里**。

**方式一：配置文件（推荐）**

```bash
cp config.example.json config.local.json
vi config.local.json          # 填 master_qq 和 db.*
chmod 600 config.local.json
```

```json
{
  "master_qq": "123456789",
  "ws_port": 3001,
  "api_port": 27004,
  "db": {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "your_user",
    "password": "your_password",
    "name": "TomoriNaoBotData"
  }
}
```

**方式二：环境变量**

```bash
export NAO_MASTER_QQ=123456789
export NAO_DB_HOST=127.0.0.1
export NAO_DB_USER=your_user
export NAO_DB_PASS=your_password
export NAO_DB_NAME=TomoriNaoBotData
```

优先级：**环境变量 > config.local.json > 空默认值**。没配齐时启动会直接退出并列出缺哪几项。

### API 配置（先配这个）

最省事：运行交互向导，不用手写 SQL / 命令：

```bash
python3 scripts/configure_api.py
```

它会依次询问 DeepSeek、豆包方舟、ALAPI 密钥和视觉接入点；直接回车保留原值。密钥写数据库 `api_keys`，视觉接入点写 `config.local.json` 的 `vision` 段。

API 密钥读取顺序：**数据库 `api_keys` > 环境变量**；推荐环境变量，换机器不用改库。

| 用途 | 环境变量 | 必填 | 说明 |
|---|---|---|---|
| 主对话 DeepSeek | `DS_API_KEY` | 是 | DeepSeek 的 `sk-...` |
| 视觉 豆包/方舟 | `ARK_API_KEY` | 要视觉就填 | 方舟 **API Key**，不是 Access Key |
| 搜图 ALAPI | `ALAPI_TOKEN` | 否 | 没有就少一个搜图来源 |
| 视觉接入点 | `NAO_VISION_MODEL` | 否 | 推荐填 `ep-...` 接入点 ID；也可写 `config.local.json` 的 `vision.model` |
| 视觉地址 | `NAO_VISION_URL` | 否 | 默认 `https://ark.cn-beijing.volces.com/api/v3/chat/completions` |
| 专用视觉 key | `NAO_VISION_KEY` | 否 | 不填就用 `ARK_API_KEY` |
| 语音转写 | `NAO_ASR_URL` / `NAO_ASR_MODEL` | 否 | OpenAI 兼容的 `/audio/transcriptions` |

```bash
export DS_API_KEY=sk-...
export ARK_API_KEY=...
export ALAPI_TOKEN=...

# 方舟视觉接入点 ID（推荐）
export NAO_VISION_MODEL=ep-xxxxxxxx
```

systemd 用文件保存：

```ini
# /etc/systemd/system/hoshinoumi.service
EnvironmentFile=/home/jyoushitou/Hoshinoumi/.env
```

```bash
# .env
DS_API_KEY=sk-...
ARK_API_KEY=...
ALAPI_TOKEN=...
NAO_VISION_MODEL=ep-xxxxxxxx
```

> 密钥只走环境变量/数据库，**不要写进 `config.example.json`、README 或 git**。
> `config.local.json` 只放数据库/主人 QQ/视觉接入点等非密钥配置；`chmod 600 config.local.json`。

**其他配置走程序，不再堆环境变量：**

| 配置 | 放哪 |
|---|---|
| 数据库、主人 QQ、端口、视觉接入点 | `config.local.json` |
| 功能开关（vision/voice/reading/ocr/backup…） | `config/features.json` |
| 运行时概率/频率（`image_prob`、`voice_prob`…） | QQ 里 `!config` |
| 密钥状态 / 重载 | `!apikeys` / `!reload` |
| 环境是否检查过、哪些能力可用 | `data/env_report.json` + `!features` |

`config.local.json` 的视觉段：

```json
{
  "vision": {
    "model": "ep-xxxxxxxx",
    "url": "",
    "key": "",
    "fallback_model": ""
  }
}
```

`NAO_VISION_*` 环境变量优先；没有环境变量时才读这里的配置。

### 可选依赖（读书功能要用）

```bash
# 番茄正文 OCR（必需）
sudo apt install -y tesseract-ocr tesseract-ocr-chi-sim

# 无头浏览器（抓页面 + 截图）
python3 -m pip install --user --break-system-packages playwright
python3 -m playwright install chromium
# 缺系统库时：
sudo python3 -m playwright install-deps chromium
```

不装也能跑——读书功能自动降级成「浅层在读」（只有书名和进度）。

### 启动

**一键启动（推荐）**

```bash
python3 start.py
```

顺序固定：

```text
1. 数据库迁移（有迁移脚本时执行，幂等）
2. 第一次启动 / API 缺失时，运行 configure_api.py
3. 环境监测（checks/env_check.py）
4. 需要对外服务时启动网关（可选）
5. run.py
```

需要网关时：

```bash
python3 start.py --gateway
# 或 NAO_GATEWAY=1 python3 start.py
```

网关需要先有 `gateway/build/rec_gateway` 和 `config/gateway.json`；
本地只跑 bot 用 `python3 start.py --no-gateway` 即可。网关退出时会随
`run.py` 一起被回收。

**手动分步**

```bash
# 1. 数据库迁移（首次/升级都跑；幂等）
python3 scripts/migrate.py --apply

# 2. 交互配置 API（密钥 + 视觉接入点）
python3 scripts/configure_api.py

# 3. 严格环境监测（依赖 / 配置 / 时区 / 数据库 / 表结构 / 密钥 / 人设 / 视觉）
python3 checks/env_check.py

# 4. 可选：需要对外服务时先启动网关
./gateway/build/rec_gateway --config config/gateway.json &

# 5. 启动 bot
python3 run.py
```

预检逐项打勾，退出码 0 才算通过；任何 **FAIL** 都别启动。
环境监测会检查 API 密钥；缺失时直接提示运行 `python3 scripts/configure_api.py`。
**迁移必须先于启动**——新代码会查 `kind`、`target_id`，列不存在直接报 `Unknown column`。

### 停止

- **推荐**：QQ 里发 `!exit`
- 前台运行：`Ctrl-C` 一次（打印「[已中断]」，不吐栈）
- 后台 screen：`screen -S bot -X quit`

### 单实例

启动时自动抢 `.bot.lock`，已有实例在跑会直接退出并打印对方 PID。
锁由操作系统维护，进程死了自动释放。

---

## 网关（v20，可选）

v20 网关负责公网/多端入口，后端仍只监听 `127.0.0.1`。v20 还没有登录/JWT/限流，只适合本机或内网验证。

```bash
# 1. 配置后端地址 / 网关端口
python3 scripts/configure.py

# 2. 构建（开发机）
python3 scripts/build_gateway.py --version 20.0.0
# 或直接 Docker 构建
docker build -f gateway/Dockerfile -t hoshinoumi-gateway:20.0.0 .

# 3. 导出到部署机
# release/REC-v20.5.0-gateway-docker.tar.gz
docker load -i REC-v20.5.0-gateway-docker.tar.gz

# 4. 运行（必须 host 网络，后端只允许 127.0.0.1）
docker run -d --name hoshinoumi-gateway \
  --network host \
  -v "$PWD/config:/app/config:ro" \
  hoshinoumi-gateway:20.0.0

# 5. 健康检查
curl -s http://127.0.0.1:27005/healthz
curl -s http://127.0.0.1:27005/readyz
```

Docker Compose 一键起后端 + 网关：

```bash
cp .env.example .env      # 只填隐私项
docker compose -f docker-compose.release.yml up -d
```

说明：

- `.env` 只放数据库/主人 QQ/API Key 等隐私项，不进 git
- API Key 可用 `.env` 环境变量，或 `python3 scripts/configure_api.py`
- 网关配置在 `config/gateway.json`，由 `scripts/configure.py` 生成
- 后端地址只允许 `127.0.0.1` / `localhost`；不要给后端配公网地址
- v20 网关不替代 NapCat；NapCat 仍是 QQ 通道

## 角色卡：换一个人设（重点）

人设**不在代码里**，全部放在 `personas/<名字>/` 下。改文件就能换角色，不用动一行 Python。

### 目录结构

```
personas/nao/
├── prompt.txt       主提示词（含 {now}{tone} 等占位符）
├── supplement.txt   人设补充：她是谁、口癖、关系、边界、示例
├── life.txt         生活事件模板（# weight 0.25 分组，每组一行一条）
└── state.json       状态基线 {"mood":0.1,"energy":0.7,"lonely":0.15}
```

### 四个文件各管什么

| 文件 | 作用 | 改动效果 |
|---|---|---|
| `prompt.txt` | 主提示词：世界观、性格锚点、说话规则、分条机制 | 说话风格、价值观 |
| `supplement.txt` | 补充人设：口癖、称呼、日常习惯、软肋、示例对话 | 语气细节、关系感 |
| `life.txt` | 她「今天经历了什么」的模板（109 条，带权重） | 生活内容、日常话题 |
| `state.json` | 情绪基线（心情/精力/孤独） | 默认神态、活跃度 |

### 占位符必须保留

`prompt.txt` 里的这些占位符**一个都不能删**，否则渲染会报 `KeyError`：

| 占位符 | 内容 |
|---|---|
| `{now}` | 当前时间（含时段描述） |
| `{tone}` | 语气提示（情绪 + 天气） |
| `{profile}` | 他的画像 + 口头禅 + 关系里程碑 |
| `{relation}` | 关系档位 + 称呼建议 |
| `{timeline}` | 最近事件时间线 |
| `{events}` | 检索到的记忆 |
| `{current_dialogue}` | 最近 30 轮对话 |
| `{global_keywords}` | 关键词 |
| `{available_tags}` | 图库标签（600 个） |
| `{master_qq}` | 主人 QQ |
| `{digest}` | 她自己的浓缩记录（每 10 轮压一行） |
| `{reading}` | 她最近在看的小说 |

### 三种换卡方式

| 方式 | 命令 | 生效时机 | 持久化 |
|---|---|---|---|
| **运行时切换** | `!persona <名字>` | 下一句话 | ✅ 写 `personas/.active` |
| 环境变量 | `NAO_PERSONA=<名字> python3 run.py` | 启动时 | ❌ |
| 默认 | 无 | 用 `nao` | — |

优先级：**`!persona` > `.active` > `NAO_PERSONA` > `nao`**，每层都会检查目录是否存在，不存在就往下落。

### 自制一张卡

```bash
cp -r personas/nao personas/mychar
# 改 personas/mychar 下的四个文件
```

QQ 里发：

```
!persona mychar
```

她会回「✅ 已切换到「mychar」。下一句话就生效。」

### 导出当前人设

如果人设还在代码里（从老版本升上来），跑：

```bash
python3 scripts/export_persona.py
```

会把当前硬编码的提示词、补充、生活模板、状态基线**无损导出**成 `personas/nao/` 四件套。

### 注意

- `life.txt` 每组第一行是权重：`# weight 0.25`，下面每行一条模板
- 权重总和不必等于 1，程序会归一化
- `supplement.txt` 留空也可以，不影响启动
- 卡目录名不能以 `.` 开头（会被忽略）

---

## 命令（39 个，仅主人可用）

### 基础

| 命令 | 说明 |
|---|---|
| `!ping` | 测试是否在线 |
| `!status` | 详细状态（配置 / API / 记忆 / 定时） |
| `!uptime` | 运行时长 |
| `!usage` | 最近 10 次 token 用量 |
| `!help` | 命令列表 |
| `!exit` / `!quit` | 安全退出 |

### 记忆与关系

| 命令 | 说明 |
|---|---|
| `!memory [关键词]` | 检索记忆 |
| `!memorybook` | 记忆本：认识天数 / 关系 / 口头禅 / 最近记得的事 |
| `!growth` | 成长轨迹：关系进度条、一起经历过多少件事 |
| `!profile` | 他/她的画像 |
| `!event` | 查看/管理事件 |
| `!keywords` | 关键词 |
| `!clear` | 清理 |

### 媒体

| 命令 | 说明 |
|---|---|
| `!img` | 图库管理 |
| `!sticker` | 表情包 |
| `!acg` | 在线图源 |
| `!clip` | CLIP 状态（v8 起已停用，仅展示） |
| `!voice <文本>` | 合成一条语音 |

### 日常

| 命令 | 说明 |
|---|---|
| `!diary` | 今天的日记 |
| `!diary <日期>` | 指定日期 |
| `!diary list [天数]` | 最近几天概览 |
| `!diary raw <日期>` | 原始事件记录 |
| `!todo` | 待办 |
| `!task` | 定时任务 |

### 模式与运维

| 命令 | 说明 |
|---|---|
| `!code` | 代码模式（知识正确性优先，30 分钟无消息自动退出） |
| `!code off` | 手动退出 |
| `!persona [名字]` | 查看 / 切换角色卡 |
| `!config` | 列出可调参数 |
| `!config <参数> <值>` | 改一个参数，立即生效 |
| `!stats` | 今日统计：回复 / 配图 / 语音 / 群接话率 / 配图率 |
| `!set` | 设置项 |
| `!db` | 数据库信息 |
| `!log` | 日志 |
| `!apikeys` | 密钥管理 |
| `!reload` | 重载配置 |
| `!say` / `!sayg` | 以她的口吻说话（私聊 / 群聊） |

---

## 核心机制

### 1. 记忆系统

**三层结构**

| 层 | 存法 | 上限 |
|---|---|---|
| 对话记忆 | `user_memory` | 每人/每群最近 **30 轮** |
| 长期记忆 | `events` | life 60 / event 30 / promise 30 / profile 20 |
| 画像 | `events` 里 `kind='profile'` | 每字段一行，重写即覆盖 |

**检索不用 LIKE**

```
用户消息 → 分词 → BM25 排名 + 关键词命中排名 → RRF 融合 → top 5
```

- 候选池：这个对象最近 300 条记忆
- 两路都不命中 → 退回最近 3 条
- 读库失败 → 给「无」，不影响回复

**去重**：同一句话（去标点、转小写）7 天内重复只累加 `hit_count`，不新增行。

**分层预算**

| 层 | 预算 |
|---|---|
| 画像 | 120 字 |
| 最近对话 | 700 字（30 轮，从最新往回留） |
| 检索到的记忆 | 250 字 |
| 全局关键词 | 120 字 |
| 时间线 | 200 字 |

**长会话浓缩**：超过 30 轮后，溢出缓冲攒够 10 轮就压成一行，写进 `data/digests/<对象>.md`
（最多 20 行，每行 ≤40 字）。注入 prompt 的 `{digest}`。

### 2. 对话模型

- **主模型** DeepSeek（`deepseek-flash`），**兜底**豆包，都挂了返回傲娇短句（`Fallback` 标记，**不进记忆**）
- **超时分级**：普通聊天 20 秒，长文（日记 / 代码模式）40 秒
- **并发**：不同对象各一把锁，同时在飞的请求最多 5 个

### 3. 说话方式

**分条**：她写几行就发几条，代码只兜底「超过 10 行」。

```
今天好累啊
不想动了
（缩成一团）
      ↓ 三条独立消息，间隔 1.5~3.0 秒
```

**延迟**：按时段浮动，平方压低到短端。深夜慢、白天快，整体倍率可用 `!config delay_scale` 调。

**语气**：受 mood / energy / lonely 影响，也受关系档位影响（亲近才会损你）。

### 4. 她自己的生活（v9）

状态向量 `mood / energy / lonely` 随时间指数回归 + 孤独拉低心情基线。
每天生成「生活事件」（109 条模板），写进记忆，聊天时自然提起。

### 5. 读小说（v16）

**触发**：你空闲 ≥2 小时、不在深夜（01:00~07:00）、今天没读够 20 章。

**流程**

```
挑书（热榜 / 内置书单 / 你点名）
   ↓
抓章节 HTML → 正文有私有区字符？ → 截图 + tesseract OCR
   ↓
HTML 骨架 + OCR 补字（difflib 对齐）→ 合并正文
   ↓
AI 摘要（≤100 字）→ 记进度
   ↓ 攒够 3 个点
主动说一句（3 小时冷却）
```

**为什么这么做**：番茄把多数字符替换成私有区码点，靠自定义字体渲染，正文 54% 是乱码。
字体比对失败（字形被扰动，命中率 0.3%），所以改用截图 OCR——渲染出来的字是对的。

**成本**：每章 8~12 秒（浏览器 + OCR + 摘要），每天最多 20 章。

**你点名**：

```
去看看十日终焉呢     → 识别出书名 → 番茄搜索 → 开始追
《十日终焉》你去看看  → 同上
去看 <番茄链接> 这本   → 直接按链接追
```

### 6. 图片与语音

- **看图**：多模态直接看，不猜标签；动图抽 24 帧拼 4×6 网格
- **配图**：AI 给关键词 → 过闸门（30% 概率 / 10 分钟冷却 / 心情差减半）→ 搜图
- **语音**：8% 概率转语音 + 20 分钟冷却，长度 4~60 字

### 7. 摩擦（v13）

```
她说「早点睡」→ 记一次期待 → 8 小时没回应 → 失望
     ↓ 累计 3 次
   冷战 ── 24 小时自动结束
     ├─ 说「对不起」→ 立刻和好
     └─ 3 句话 → 和好
```

红线写死在代码：`COLD_WAR_MAX=24h`、`GRUDGE_LIMIT=1/周`、`DISAPPOINT_MAX=3`。

### 8. 调参与观测（v15）

```
!stats                   今日统计
!config                  列出可调参数
!config image_prob 0.2   改一个，立即生效
```

| 参数 | 默认 | 含义 |
|---|---|---|
| `group_base_prob` | 0.20 | 群里没被  的接话概率 |
| `group_mention_prob` | 0.75 | 被  时的回话概率 |
| `image_prob` | 0.30 | 配图概率 |
| `image_cooldown` | 600 | 配图间隔（秒） |
| `voice_prob` | 0.08 | 语音概率 |
| `lonely_threshold` | 0.45 | 孤独到多少主动开口 |
| `proactive_cap` | 3 | 每天主动上限 |
| `delay_scale` | 1.0 | 回复延迟倍率 |

存在 `data/tunables.json`，重启也记得。

---

## 运维

### 测试

```bash
python3 scripts/run_tests.py             # 969 条（tests 932 + checks 37）
python3 scripts/check_names.py            # 静态检查：未定义名字 / 先用后赋值
```

### 自检

```bash
python3 scripts/migrate.py --apply   # 迁移：建表 + 补列 + v18.17 events→memories + 场景
python3 checks/env_check.py          # 严格环境监测，任何 FAIL 都不启动
```

检查项：Python / 依赖 / 静态检查 / 环境变量 / 配置 / 能力 / 网络 / 数据库连接 /
必需表 / 全部表 / v18 表结构（memories/cron_tasks/reading_progress）/ API 密钥 / 人设 / 视觉。

如果 API 密钥或视觉接入点缺失，先运行 `python3 scripts/configure_api.py`，再重跑环境监测。

### 发布正式版

```bash
# 1. 提交改动
git add -A && git commit -m "..."

# 2. 预演（不改任何东西）
python3 scripts/release.py --version v16.1.0

# 3. 真发布
python3 scripts/release.py --version v16.1.0 --apply
```

脚本会：检查工作区 → 跑测试 → 打 tag `vX.Y.Z` → 移动 `正式版` → 打包 `release/REC-vX.Y.Z-bundle.bundle` → 生成 `docs/RELEASE-NOTES.md`。

源码包和完整 bundle 用一键打包：

```bash
python3 scripts/build_all.py --version 19.5.7 --skip full,exe,docker
# release/REC-v20.5.0-src.zip + release/REC-v20.5.0-bundle.bundle
```

> 命名声明：v19.5.7 之前已生成的 `nao-v*` / `nao-bot-*` 产物保留原样、不删除；
> 新脚本只生成 `REC-v*`。

**版本号必须三段式**（`v17.0.0`），两段会直接拒绝。

### 服务器部署 / 从 v18.4 升级

**先备份数据库**（迁移不可逆，回滚要靠它）：

```bash
cd ~/NapCat-Pyhon
mysqldump -h 127.0.0.1 -u 用户 -p 库名 > ~/nao-before-v20.5.0.sql
# 或 SQLite：sqlite3 data/nao.db ".backup '$HOME/nao-before-v20.5.0.db'"
```

取代码并迁移：

```bash
git fetch ./REC-v20.5.0-bundle.bundle main
git reset --hard FETCH_HEAD

python3 scripts/migrate.py --apply      # 建表 + 补列 + events→memories + 场景
python3 checks/env_check.py             # 严格监测（FAIL 不启动）
python3 run.py
```

systemd（新名字，旧 `nao-bot` unit 仍保留）：

```bash
sudo cp deploy/hoshinoumi.service /etc/systemd/system/hoshinoumi.service
sudo systemctl daemon-reload
sudo systemctl enable --now hoshinoumi
sudo systemctl status hoshinoumi
```

完整清单（依赖、systemd、验证、回滚）：[v19 开发记录](docs/versions/v19.md)；命名约定：[NAMING.md](docs/NAMING.md)。

### 打包（四种形式）

| 形式 | 命令 | 产物 |
|---|---|---|
| git bundle | `python3 scripts/release.py --apply` | `release/REC-vX.Y.Z-bundle.bundle` |
| 源码 zip | `python3 scripts/package.py` | 含依赖清单 |
| 可执行 | `python3 scripts/build_exe.py` | PyInstaller |
| Docker | `python3 scripts/build_docker.py` | 镜像 |

Docker 镜像里自带 Chromium，抓小说可用。

---

## 架构

```
bot/
├── core/       常量、运行时状态、锁、单实例、参数中心、统计
├── infra/      数据库连接与仓储（记忆 / 画像 / 密钥 / 日志 / AI 原文）
├── memory/     上下文、检索（BM25+RRF）、分层预算、时间线、浓缩
├── ai/         人设、角色卡加载、提示词、模型调用、工具调用、回复解析、视觉
├── chat/       入站解析、回复组装、发送、群聊节奏、通知事件、摩擦反馈
├── cmd/        39 个命令（注册表 + 各分类实现）
├── diary/      日记生成与存储
├── schedule/   定时任务、随机闲聊、空闲读书
├── image/      图库：存图、打标、检索、在线图源
├── speech/     语音合成（TTS）与转写（ASR）
├── life/       状态、生活事件、愿望、日程、关系、习惯、摩擦、读书、OCR
├── server/     HTTP API
└── app/        启动引导与主循环

personas/       角色卡（不进代码，可直接改）
scripts/        迁移 / 自检 / 发布 / 打包 / 探测
data/           运行时数据（tunables、digests、cookies、凭据）——不进版本库
```

---

## 版本历史

| 版本 | 主题 | 关键内容 |
|---|---|---|
| v5 | 重构 | 分层包、兼容 shim、单实例、断线重发 |
| v6 | 说话节奏 | 分条、延迟、群聊节奏、代码模式 |
| v7 | 记忆地基 | events 主表、去重、画像 |
| v8 | 检索 | BM25+RRF、分层预算、时间线、CLIP 停用 |
| v9 | 她自己的生活 | 状态向量、生活事件、日记、主动消息 |
| v10 | 关系与主动 | 亲密度、TODO、日程、承诺 |
| v11 | 感官 | 多模态看图、图片记忆、语音合成与转写 |
| v12 | 共同的东西 | 口头禅、里程碑、记忆本、撤回、戳一戳、天气 |
| v13 | 摩擦与成长 | 期待/冷战/和好、成长轨迹、称呼演化、工具调用 |
| v14 | 可换角色 | 人设卡片化、发图择时、主动自适应、 判断 |
| v14.1 | 会话延长 | 30 轮 + 浓缩记录、状态按人分 |
| v15 | 调参与观测 | `!config` / `!stats`、参数持久化 |
| v16 | 读小说 | 番茄抓取、字体加密实测、截图 OCR、HTML+OCR 合并 |
| v16.0.4 | 点名 | 无书名号识别、按书名搜索 |
| v17.0 | 并发基建 | 线程池 + 连接池 + `run_blocking` 统一阻塞入口；17 条行为基线 |
| v17.1 | 事件驱动 | 事件对象/注册表/三档队列/worker 池；四个执行器接管定时、主动、读书、日程 |
| v17.1.1 | 观测 | `!stats` 显示调度状态（队列/完成/失败/熔断） |
| v17.2 | 出站层 | 唯一出口 + 全局锁 + 3 秒合并 + 命令专用通道 |
| v17.3 | 主循环瘦身 | 接收循环 190→22 行；连发合并；runner 408→86 行 |
| v17.3.1 | 修 | `digests.lines` 撞 MySQL 保留字；建表单表失败不再中断 |
| v17.4 | 数据模型 | 21 张新表；迁移脚本 8 种 kind；六类读新表、四类双写 |
| v17.4.1 | 修 | 老库 `events` 无 `deleted_at` 列时迁移失败；`!exit` 要 Ctrl+C 才退 |
| v17.4.2 | 修 | 迁移脚本五类函数定义在 `sys.exit` 之后 → `NameError` |
| v17.4.3 | 修 | 迁移 rel/habit/reading 三类：主键重复、缺 phrase、缺 book_url |
| v17.5 | 日志 | TXT 按天切、保留 180 天（txt + DB 统一清理） |
| v17.6 | 定时 | `cron_tasks` 表 + 每任务一个 `call_at` 钩子 + 04:00 对账 |
| v17.7 | 定时入口 | `!cron` 命令；对话提取「明天七点叫我」；8 个场景迁进表 |
| v17.8 | 线程监护 | 线程池 3→5、连接池 5→6、一个监护线程看两个池 |
| v17.9 | 体验收尾 | 图片不再误报、表情正常对话、要求看书真读正文、语音后不撤文字 |
| v17.10 | 稳定性收尾 | 重启熔断 10 次 + 指数退避、重试上限 5、停写旧表 |
| v17.11 | 存储后端 | MySQL 优先、连不上自动退 SQLite；双方言适配 + 互导脚本 |
| v17.12 | 语音情绪 | 五档情绪参数 + 角色声纹文件 + `!voice` 调参/试听 |
| v17.13 | 对话质量 | 重复回复拦截、空语音过滤、贴图带上下文 |
| v17.14 | 解耦 | conn 配置注入、日志文件优先+异步刷库、db 降级为别名 |
| v17.15 | 解耦 | ai 不再 import life，改用 lifeport 注册表 |
| v17.16 | 收尾 | 命令层/HTTP 层零 SQL + server 补 11 条测试 |
| v17.17 | 部署 | `setup.py` 一条命令：依赖+建表+迁移+场景 |
| v18.0 | 时间与日志 | 日志目录回项目根、静默失败可见、时区按 CST |
| v18.1 | 视觉与定时 | 视觉模型真收图；定时钩子真实投递 |
| v18.2 | 记忆分量 | weight/tier 三档，检索按分量排序 |
| v18.3 | 事实卡 | 「没有早八」这类事实能记住并按人隔离 |
| v18.4 | 隐私 | 事实卡 subject/visibility，群聊不乱说 |
| v18.5 | 观测 | uptime 与元数据视图，不依赖 logs 表 |
| v18.6 | 引用 | 接收/处理解耦、200 条消息缓存、引用原话 |
| v18.7 | 时间调度 | 规则引擎、当天微调、call_at、看门狗、准点预生成 |
| v18.8 | 观测 | `!stats` 定时行、近 1 分钟完成数、引用计数 |
| v18.9 | 钩子 | 删 `!task`、新增 `!hooks`、旧 planner 链清理 |
| v18.10 | 分条 | 最多 4 气泡，超了合并相邻短句 |
| v18.11 | 情绪 | 情绪标签跨天保留，3/5 天半衰 |
| v18.12 | 回忆 | 重记忆每天最多冒一次，心情差时跳过 |
| v18.13 | 缓存 | 进程内 TTL：counts 5s、cron list 3s |
| v18.14 | 索引 | 索引清单脚本 + events/ai/facts 复合索引 |
| v18.15 | 可观测 | 双写失败计数、空回复原因 |
| v18.16 | 读书 | 按书落 reading_progress，不再反复读同一章 |
| v18.17 | 旧表 | events 迁 memories、旧表改名、写路径切换 |
| v18.18 | OCR | tesseract + 可选 PaddleOCR 双引擎 |
| v18.19 | 备份 | 每月 1 号 04:30，保留 6 份，`!backup` |
| v18.20 | 封版 | `!exit` 5 秒看门狗、全角命令归一化、18.20.0 |
| v19.0–v19.5 | 架构重构 | 功能清单/环境报告、conversation_messages、`!history`、语音分段、拆环、events 视图删除 |
| v19.5.7 | 视觉配置 | 支持 `config.local.json` 的 `vision.*` 回退 |

---

## 事件与调度（v17.1）

所有会触发动作的东西——聊天、定时、主动、读书、日程——最终都是同一种对象：

```python
Event(kind="idle_read", key="read:1:u1", fn=read_chapter,
      priority=Priority.IDLE, timeout=300, retries=1)
```

### 三档优先级

| 档位 | 用途 | 排队行为 |
|---|---|---|
| `P0_CHAT` | 聊天回复、命令 | 独占快车道，不排队 |
| `P1_EVENT` | 定时任务、主动消息、提醒 | 快车道，可等 |
| `P2_IDLE` | 读书、抓取、浓缩 | 慢车道，容量满时丢最旧 |

### 调度器结构

| 文件 | 作用 |
|---|---|
| `events/base.py` | `Event` + 三档优先级 |
| `events/registry.py` | `kind → handler` 注册（重复注册直接报错） |
| `scheduler/queue.py` | 三档队列 + 去重 + 容量（**只限空闲档**） |
| `scheduler/policy.py` | 超时 / 退避重试 / 熔断（按 kind 隔离） |
| `scheduler/workers.py` | 双车道 worker 池 |
| `scheduler/dispatcher.py` | 入口：`submit` / `stats` / `describe` |

### 已注册的事件

| kind | 档位 | 做什么 |
|---|---|---|
| `idle_tick` | P2 | 每 30 分钟判断该不该读书 |
| `idle_read` | P2 | 读一章（几百秒上限） |
| `idle_pick_book` | P2 | 没在追书时挑一本 |
| `proactive_tick` | P1 | 每 30 分钟掷骰决定要不要主动 |
| `proactive_say` | P1 | 真正生成并发送主动消息 |
| `schedule_scene` | P1 | 催起床/催睡觉/午睡/复盘等八个场景 |
| `agenda_remind` | P1 | 日程到点提醒 |
| `pending_nudge` | P1 | 待办到点回访 |

### 三条运行规则

| 规则 | 说明 |
|---|---|
| 超时不重试 | 卡住的任务重试只会更慢，直接放弃并计数 |
| 失败退避重试 | 2→4→8 秒，封顶 30 秒 |
| 连续失败熔断 | 同 kind 连续 3 次失败 → 停 1 小时，到期自动恢复 |

### 观测

```
!stats
📊 今日统计 ...
🧵 线程池：3 线程，排队 0
🗄️ 连接池：空闲 3/5，借出 2
⚙️ 调度：运行中 | 队列 1（聊天 0 / 定时 0 / 空闲 1）
   完成 128 | 失败 0 | 超时 0 | 重试 0
📤 出站：在线 | 已发 128 | 失败 0 | 入队 0（积压 0）
⌨️ 命令：23 次 | 平均 12.4 ms | 最慢 stats 45 ms
```

### 主循环瘦身效果

改造前，runner 每秒都在判断「要不要读书」，读书时还要排队等它跑完；
现在 tick 30 分钟醒一次，重活全在 worker 里，**聊天永远能插进来**。

---

## 出站层（v17.2）

所有发出去的东西都从一个口走：

```python
out = get_outbound()
await out.send("send_private_msg", params, label="私聊", kind="chat")
await out.send("get_msg", params, want_response=True)   # 等回包拿 message_id
await out.flush()                                        # 重连补发
```

### 为什么必须唯一

| 问题 | 以前 | 现在 |
|---|---|---|
| 并发发送 | 各处自己加锁，可能交错 | 一把全局锁，一次只发一帧 |
| 断线丢消息 | 各函数各自入队 | 统一入队 + `flush()` 补发 |
| 撤回要 id | 单独一套 echo 逻辑 | 同一个 `want_response` |
| 出问题排查 | 不知道谁发的 | `!stats` 按 kind 计数 |

### 三个配套件

| 文件 | 作用 |
|---|---|
| `egress/outbound.py` | 唯一出口（锁 / 入队 / echo / 计数） |
| `egress/merge.py` | 3 秒合并窗口：**只合定时消息**，聊天永不合并 |
| `cmd/channel.py` | 命令专用通道：不进调度队列、并发 2、超时 15 秒 |

### 合并规则

```
定时消息 A ─┐
定时消息 B ─┴─→ 3 秒窗口 → 一条气泡（"A\nB"）
聊天回复   ───→ 不合并，立刻发
图片/语音  ───→ 不合并，立刻发
```

**为什么聊天不合并**：聊天是「你问我答」，合并会破坏节奏；定时消息是「她主动说」，合成一条更自然。

### 命令为什么绕开队列

```
!stats  →  命令通道  →  立刻执行（人就在等）
读书    →  调度器队列 →  排队慢慢跑（能等）
```

**队列堆满时，命令照样秒回。**

---

## 连发合并（v17.3）

你连着发三句「在吗」「问你个事」「那个…」，她**只回一次**，但三句都看得到。

```
消息 A ─┐
消息 B ─┼→ 静默 0.6 秒 → 合并成 "A\nB\nC" → 回一次
消息 C ─┘        ↑
            最多等 2 秒（window）
```

| 参数 | 值 | 理由 |
|---|---|---|
| 防抖 | 0.6 秒 | 单条只多等这一点，相对 1.5–3 秒回复可忽略 |
| 窗口上限 | 2 秒 | 一直发也得在 2 秒内处理 |
| 单批上限 | 5 条 | 满了提前处理 |

**不合并的情况**：命令（`!` 开头）、群聊、代码模式、纯图片消息。开关：`NAO_BATCH_CHAT=0`。

### 顺带瘦身

| 文件 | 之前 | 现在 |
|---|---|---|
| `chat/handler.py` 接收循环 | 190 行 | 22 行 |
| `schedule/runner.py` | 408 行 | 86 行 |

主循环从「每秒醒一次」改成「30 秒心跳」——跨天、日记、生日、场景派发、日程检查全在 `minute_tick` 里。

---

## 并发与性能（v17.0）

以前所有同步调用（模型、浏览器、OCR、下载）都直接卡在事件循环上——抓小说时你发消息要等它跑完。

现在统一走 `run_blocking()`：

```python
r = await run_blocking(requests.post, url, json=payload, timeout=60, name="deepseek")
```

| 机制 | 参数 | 默认 | 说明 |
|---|---|---|---|
| 线程池 | `NAO_TASK_THREADS` | 3 | 阻塞调用并发数 |
| | `NAO_BLOCKING_TIMEOUT` | 120 | 默认超时（秒） |
| 连接池 | `NAO_DB_POOL_SIZE` | 5 | 复用 MySQL 连接（**≥ 线程池大小**） |
| | `NAO_DB_POOL_TIMEOUT` | 5.0 | 借连接超时，池满快速失败 |

看实时状态：

```
!stats
📊 今日统计 ...
🧵 线程池：3 线程，排队 0
🗄️ 连接池：空闲 3/5，借出 2，复用 47，超时 0
```

**怎么读这几个数**：

| 现象 | 说明 |
|---|---|
| 线程池排队持续 > 3 | 并发不够或任务卡住 |
| 连接池空闲长期 0 且借出等于容量 | 连接泄漏（有人没还） |
| 连接池超时 > 0 | 池太小或漏还 |

新增代码里**不允许再用裸 `asyncio.to_thread`**——有测试守卫（`test_no_raw_thread.py`）。

---

## 数据库表

表定义集中在 `bot/infra/schema.py`（现状表 + 未来纯表），全部 `CREATE TABLE IF NOT EXISTS`。

```bash
python3 scripts/init_db.py            # 看缺哪些表
python3 scripts/init_db.py --apply    # 建缺的（不会动已有表）
python3 checks/env_check.py --init-db   # 环境监测时自动建
```

**只建不存在的表，永不修改已有表结构**——加列/改类型仍走 `scripts/migrate_*.py`。

---

## 已知限制
| 限制 | 说明 |
|---|---|
| **番茄正文有 OCR 错字** | 约 5%（`神谨`→`神龛`），对摘要够用，逐字引用不可靠 |
| **起点抓不了** | 章节页对机房 IP + 未登录双重限制，已放弃 |
| **抖音未实现** | 规划在 v42，且只做看和转发，发评论不可行 |
| 群聊记忆按群号 | 同一个人在私聊和群里是两份记忆 |
| 语义检索靠关键词 | 无外网装不了 embedding，BM25 + 关键词双路 |
| 视觉/ASR 依赖外部接口 | 失败静默降级，不影响聊天 |
| 读书需要 tesseract | 没装就退化成浅层在读 |

---

## 配置项速查

| 环境变量 | 默认 | 说明 |
|---|---|---|
| `NAO_MASTER_QQ` | 空 | 主人 QQ（只有他能用命令） |
| `NAO_DB_HOST` / `NAO_DB_PORT` / `NAO_DB_USER` / `NAO_DB_PASS` / `NAO_DB_NAME` | 空 | 数据库 |
| `NAO_PERSONA` | `nao` | 用哪个角色卡 |
| `NAO_CITY` | 空 | 城市名，设了才查天气 |
| `NAO_READ_IDLE_HOURS` | `2` | 多久没说话才去读书 |
| `NAO_READ_DAILY_CHAPTERS` | `20` | 每天最多读几章 |
| `NAO_BOOK_URLS` | 内置三本 | 自定义书单：`名字&#124;url,名字&#124;url` |
| `NAO_OCR_LANG` | `chi_sim` | tesseract 语言包 |
| `NAO_NO_AUTOINSTALL` | 未设置 | 设 `1` 关闭启动时自动装包 |

完整清单见 [`docs/发布检查清单.md`](docs/发布检查清单.md)。

## 文档索引

| 文档 | 内容 |
|---|---|
| [`docs/README.md`](docs/README.md) | 文档总索引（版本 → 条目 → 状态） |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | 发布路线图：v17~v48 每个小版本的拆解与验收点 |
| [`docs/DB-DESIGN.md`](docs/DB-DESIGN.md) | 数据库设计（一表一职责） |
| [`docs/发布检查清单.md`](docs/发布检查清单.md) | 5 组检查项 + 环境变量表 + 发布流程 |
| [`docs/versions/`](docs/versions/) | 各版本设计文档（v6 ~ v48） |
| [`docs/V14-后续清单.md`](docs/V14-后续清单.md) | 未排期需求（A~E 组） |
| [`docs/V6-功能.md`](docs/V6-功能.md) | v6 时代的功能总表（74 项，封版） |
| [`docs/RELEASE-NOTES.md`](docs/RELEASE-NOTES.md) | 最近一次发布说明 |

## 联系方式

- 项目维护者：[jyoushitou](https://github.com/jyoushitou)
- 邮箱：[xzt98948364@outlook.com](mailto:xzt98948364@outlook.com)
- 博客地址：<https://jyoushitou.github.io/>
- 项目地址：<https://github.com/jyoushitou/Hoshinoumi>

## 开源协议与致谢

### 仓库代码许可

本项目自身代码采用 **MIT License** 开源，详见 [LICENSE](LICENSE)。

### 致谢

- **《Charlotte》**：角色「友利奈绪」与世界观原型；本项目是非官方同人 / 个人项目。
- **NapCat**：QQ 协议端。
- **DeepSeek / 豆包**：对话模型。
- **edge-tts**：语音合成。
- **tesseract / Playwright**：番茄小说截图与 OCR。
- 以及所有依赖库和测试工具的作者。

第三方组件遵循其各自许可证；本项目不包含《Charlotte》的官方素材。

## 附录 A · 当前状态与 v20.5 验证清单

| 项 | 当前事实 |
|---|---|
| 后端 | v20.5，`bot/`，Python 3.10+ |
| 网关 | v20.5，`gateway/`，C++17 + Boost.Asio/Beast |
| 阶段 | Docker 验证 + 网关验证，已部署试运行 |
| 前序 | v19 与 v20.0–v20.4 已完成 |
| 数据表 | 25 张表 + 1 个只读视图 `v_bot_meta` |
| 命令 | 39 个注册命令（`!task` 仅提示迁移） |
| 测试 | 969 条：功能 932 + 环境/迁移 37 |
| 账号 | 单主人 `__owner__`；多用户 v23 计划 |
| 后端鉴权 | `/api/*` 除 health 外要 Bearer Token；`/internal/*` 免鉴权 |
| 网关鉴权 | 无 JWT / 无按用户限流 / 无 TLS（v21/v22） |

### 验证清单

| 项 | 怎么验 | 通过标准 |
|---|---|---|
| Docker 构建 | `python3 scripts/build_docker.py --version 20.5.0` | 镜像构建成功 |
| 网关构建 | `python3 scripts/build_gateway.py --version 20.5.0` | 二进制/镜像生成 |
| 容器启动 | 按 `release/` 说明加载镜像后 `docker compose -f docker-compose.release.yml up -d` | 后端/网关都起来 |
| 网关存活 | `curl :27005/healthz` | 200 |
| 网关就绪 | `curl :27005/readyz` | 后端在 200；不在 503，起来后恢复 |
| 聊天 | `POST :27005/api/chat` | 返回与 QQ 内一致 |
| 历史/状态 | `GET :27005/api/history` / `/api/state` | 字段完整 |
| 重启 | `docker restart` / `!exit` 后重起 | 自动拉起 |
| 存储回退 | 停 MySQL 再启动 | 自动 SQLite |
| 单实例 | 起第二个进程 | 打印 PID 后退出 |

> 这是验证清单，不是“全部已通过”的声明。

---

## 附录 B · 命令全表（39 个）

> 全部命令仅主人可用；群聊里需要 @ 或命令前缀。`!task` 只保留迁移提示。

| 命令 | 用法 | 说明 |
|---|---|---|
| `!ping` | `!ping` | 在线测试 |
| `!status` | `!status [all]` | 运行状态、配置、API、记忆、定时 |
| `!uptime` | `!uptime` | 运行时长 |
| `!usage` | `!usage` | 最近 10 次 token 用量 |
| `!help` | `!help` | 命令列表 |
| `!version` | `!version` | 版本、提交、运行时长 |
| `!meta` | `!meta` | 元数据与运行时长视图 |
| `!exit` / `!quit` | `!exit` | 安全退出 |
| `!memory` | `!memory [uid]` | 看某个对象的对话记忆；不带参数看统计 |
| `!memorybook` | `!memorybook [uid]` | 记忆本：认识天数/关系/口头禅/最近记得的事 |
| `!growth` | `!growth` | 成长轨迹：关系进度、共同经历 |
| `!profile` | `!profile [uid]` / `!profile set ...` | 查看/写入画像 |
| `!event` | `!event [uid]` | 查看事件记忆 |
| `!keywords` | `!keywords` | 全局关键词 |
| `!clear` | `!clear [uid]` | 清对话记忆与事件（谨慎） |
| `!history` | `!history [n]` | 当前会话最近 n 条，默认 100、最多 100 |
| `!img` | `!img <关键词>` | 手动搜图并发送 |
| `!sticker` | `!sticker` | 表情包存档统计 |
| `!acg` | `!acg` | 拉一张二次元图 |
| `!clip` | `!clip` | CLIP 状态（已退役，只展示） |
| `!voice` | `!voice ...` | 声线查看/试听/调参/合成 |
| `!vision` | `!vision test` | 视觉自检（画测试图跑一遍） |
| `!diary` | `!diary [日期 / list / raw]` | 日记、列表、原始事件 |
| `!todo` | `!todo` / `!todo <文字>` / `!todo done <id>` | 日程/待办 |
| `!cron` | `!cron ...` | 定时消息管理 |
| `!hooks` | `!hooks` | 定时/主动/空闲/日程钩子状态 |
| `!backup` | `!backup [run / list]` | 备份清单 / 立即备份 |
| `!code` | `!code` / `!code off` | 代码模式开关（30 分钟无消息自动退） |
| `!persona` | `!persona [名字]` | 查看/切换角色卡 |
| `!config` | `!config` / `!config <参数> <值>` | 查看/修改运行时参数 |
| `!set` | `!set <键> <值>` | 修改设置项 |
| `!stats` | `!stats` | 今日回复/配图/语音/群接话率 |
| `!db` | `!db` | 数据库统计 |
| `!log` | `!log [行数]` | 最近日志 |
| `!apikeys` | `!apikeys` | API 密钥状态 |
| `!reload` | `!reload` | 重新加载密钥与记忆 |
| `!say` | `!say <内容>` | 以她的口吻回一句 |
| `!sayg` | `!sayg <群号> <内容>` | 在指定群说话 |
| `!task` | `!task` | 已移除；提示改用 `!cron` / `!hooks` |

---

## 附录 C · HTTP API 参考

### C.1 鉴权

| 路径 | 鉴权 | 说明 |
|---|---|---|
| `/api/health` | 无 | 存活检查 |
| `/api/*` 其他 | `Authorization: Bearer <API_SERVER_TOKEN>` | Token 首次启动生成，存 `api_keys` |
| `/internal/*` | 无 | 只给本机/网关；不要暴露公网 |

```bash
TOKEN=$(python3 - <<'PY'
import sys; sys.path.insert(0,'.')
from bot.infra.repo_key import get_api_key_from_db
print(get_api_key_from_db("API_SERVER_TOKEN") or "")
PY
)
curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:27004/api/status
```

### C.2 `POST /api/chat`

```json
{
  "message": "在吗",
  "target_id": "822891053",
  "keywords": ["可选"]
}
```

```json
{
  "success": true,
  "reply": "...",
  "target_id": "822891053"
}
```

- `message` 必填；`target_id` 必填（记忆隔离）。
- 失败：`{"error":"empty_message"|"missing_target_id"|"ai_call_failed", "message":"..."}`。
- 和 QQ 共享同一份记忆/人设。

### C.3 `POST /api/command`

```json
{"command": "status", "args": []}
```

只支持只读类命令（help/status/memory/sticker/keywords/apikeys/usage 等）；写操作命令不走 API。

### C.4 查询接口

| 路径 | 参数 | 返回 |
|---|---|---|
| `GET /api/status` | — | `status`、密钥布尔、统计、runtime |
| `GET /api/usage` | `limit`（1–100） | 最近调用 token |
| `GET /api/memory` | `target_id`（可选） | 某对象记录或全部对象概览 |
| `GET /api/logs` | `limit`（1–100） | 最近日志文本 |
| `GET /api/token` | — | Token 前缀、监听地址、端点列表 |

### C.5 内部接口

| 路径 | 参数 | 说明 |
|---|---|---|
| `GET /internal/history` | `target_id` 必填；`limit`（默认 100）、`before`、`user_id` | 读 `conversation_messages` |
| `POST /internal/chat` | 同 `/api/chat` | 网关转发用 |
| `GET /internal/state` | `user_id`（默认 `__owner__`） | 情绪/关系/书架摘要 |
| `GET /internal/cron` | `user_id` | 定时任务列表 |
| `GET /internal/diary` | `user_id`、`limit` | 最近日记 |
| `GET /internal/shelf` | `user_id` | 书架/阅读进度 |

### C.6 网关路由

| 网关路径 | 后端 |
|---|---|
| `/healthz` | 网关自身 |
| `/readyz` | 探测 `/api/health` |
| `/api/chat` | `/internal/chat` |
| `/api/history` | `/internal/history` |
| `/api/state` | `/internal/state` |
| `/api/cron` | `/internal/cron` |
| `/api/diary` | `/internal/diary` |
| `/api/shelf` | `/internal/shelf` |

网关当前不校验 Token，也不做限流；只适合本机/内网验证。

---

## 附录 D · 数据库字典（25 表 + 1 视图）

| 表 | 职责 | 关键列 |
|---|---|---|
| `targets` | 对象档案：私聊/群 | `target_id`、`kind`、`display_name`、`first_seen`、`last_seen` |
| `relations` | 关系值/档位 | `target_id`、`affinity`、`tier`、`since`、`daily_gain` |
| `conversation_messages` | 多端同步短期消息 | `user_id`、`target_id`、`thread_id`、`channel`、`role`、`message_id`、`meta` |
| `user_memory` | 对话记忆（每人/群 30 轮） | `target_id`、`user_msg`、`bot_msg`、`created_at` |
| `memories` | 长期记忆 | `target_id`、`kind`、`summary`、`tags`、`importance`、`weight`、`tier`、`dedupe_key` |
| `keywords` | 每对象关键词权重 | `target_id`、`keyword`、`weight` |
| `digests` | 长会话浓缩 | `target_id`、`day`、`content` |
| `facts` | 事实卡（槽位） | `target_id`、`slot`、`value`、`subject`、`visibility`、`polarity`、`valid_from`、`valid_until` |
| `bot_states` | 她的状态 | `target_id`、`mood`、`energy`、`lonely` |
| `friction_states` | 摩擦/冷战 | `target_id`、`expect_ts`、`disappoint`、`cold_ts`、`last_grudge` |
| `habits` | 口癖计数 | `target_id`、`phrase`、`count` |
| `diaries` | 日记 | `target_id`、`diary_date`、`content` |
| `reading_progress` | 阅读进度/书架 | `target_id`、`book_url`、`title`、`last_no`、`last_chapter` |
| `images` | 图库 | `md5_hash`、`file_path`、`tags` |
| `acg_images` | 二次元图缓存 | `md5_hash`、`image_data`、`tags`、`source_url`、`use_count` |
| `ai_raw_responses` | 原始模型返回/用量 | `model_name`、`raw_response_json`、`status`、`prompt_tokens`、`completion_tokens` |
| `ai_logs` | 调用日志 | `target_id`、`model`、`latency_ms`、`ok`、`err` |
| `logs` | 系统日志 | `level`、`message`、`created_at` |
| `ops_audit` | 运维审计 | `action`、`command`、`result`、`ok` |
| `cron_tasks` | 定时任务 | `target_id`、`schedule_type`、`at_time`、`weekdays`、`once_at`、`interval_min`、`rule`、`timing`、`next_ts` |
| `cron_overrides` | 某天覆盖 | `target_id`、`scene`、`day`、`at_time`、`skip` |
| `api_keys` | 密钥/Token | `key_name`、`key_value` |
| `global_keywords` | 全局关键词 | `keyword`、`weight` |
| `bot_meta` | 元数据 KV | `k`、`v` |
| `settings` | 运行时设置 KV | `k`、`v` |
| `v_bot_meta`（视图） | 元数据只读视图 | 由 `bot_meta` 派生 |

保留/清理：

| 数据 | 保留 |
|---|---|
| `conversation_messages` | 1 天 / 每对象 100 条；04:00 清理 |
| `logs` / TXT 日志 | 180 天 |
| `images` / `acg_images` | 按配置/手动清理 |
| 备份 | 每月 1 号 04:30，保留 6 份 |

---

## 附录 E · 环境变量全表

> 优先级：环境变量 > `config.local.json` > 默认值；API Key 反过来，DB `api_keys` 优先于环境变量。

| 变量 | 默认 | 作用 |
|---|---|---|
| `NAO_MASTER_QQ` | 空 | 主人 QQ |
| `NAO_WS_PORT` | 3001 | NapCat 连入端口 |
| `NAO_API_PORT` | 27004 | 后端 HTTP 端口 |
| `NAO_API_HOST` | 127.0.0.1 | 后端 HTTP 监听地址 |
| `NAO_DB_BACKEND` | auto | auto / mysql / sqlite |
| `NAO_DB_PATH` | data/nao.db | SQLite 文件 |
| `NAO_DB_HOST` | 空 | MySQL 地址 |
| `NAO_DB_PORT` | 3306 | MySQL 端口 |
| `NAO_DB_USER` | 空 | MySQL 用户 |
| `NAO_DB_PASS` | 空 | MySQL 密码 |
| `NAO_DB_NAME` | TomoriNaoBotData | MySQL 库名 |
| `NAO_DB_POOL_SIZE` | 5 | 连接池容量 |
| `NAO_DB_POOL_TIMEOUT` | 5.0 | 借连接超时 |
| `NAO_TASK_THREADS` | 3 | 阻塞线程池 |
| `NAO_BLOCKING_TIMEOUT` | 120 | 阻塞调用超时 |
| `NAO_FEATURES` | config/features.json | 功能清单 |
| `NAO_PERSONA` | nao | 角色卡 |
| `NAO_TZ` | Asia/Shanghai | 时区 |
| `NAO_CLOCK_OFFSET` | 0 | 时钟偏移（分钟） |
| `NAO_VERSION` | 空 | 覆盖版本号显示 |
| `NAO_GATEWAY` | 空 | `1` 时 start.py 启动网关 |
| `NAO_ASYNC_DISPATCH` | 1 | 消息异步分发 |
| `NAO_BATCH_CHAT` | 1 | 连发合并 |
| `NAO_LISTEN_HOST` | 0.0.0.0 | WebSocket 监听 |
| `NAO_LOG_DIR` | logs | TXT 日志目录 |
| `NAO_LOG_KEEP_DAYS` | 180 | 日志保留 |
| `NAO_LOG_TXT` | 1 | TXT 日志开关 |
| `NAO_MONITOR_INTERVAL` | 60 | 池监护间隔 |
| `NAO_CLIP` | 空 | CLIP 入口（已退役） |
| `NAO_VOICE` | zh-CN-XiaoxiaoNeural | TTS 音色 |
| `NAO_VISION_MODEL` | doubao-seed-2.1-lite-260915 | 视觉模型 |
| `NAO_VISION_URL` | 豆包方舟 URL | 视觉地址 |
| `NAO_VISION_KEY` | 空 | 专用视觉 key |
| `NAO_VISION_FALLBACK_MODEL` | deepseek-flash | 视觉降级 |
| `NAO_ASR_URL` | DeepSeek audio | 语音转写地址 |
| `NAO_ASR_MODEL` | whisper-1 | 转写模型 |
| `NAO_CITY` | 空 | 天气城市 |
| `NAO_READ_IDLE_HOURS` | 2 | 多久没说话去读书 |
| `NAO_READ_DAILY_CHAPTERS` | 20 | 每日章节上限 |
| `NAO_BOOK_URLS` | 内置三本 | 自定义书单 |
| `NAO_OCR_LANG` | chi_sim | OCR 语言 |
| `NAO_READ_IDLE_MINUTES` | 5 | 读书前宁静分钟 |
| `NAO_NO_AUTOINSTALL` | 空 | `1` 关闭自动装包 |

---

## 附录 F · 调度、事件与出站

### F.1 三档优先级

| 档 | 值 | 谁 |
|---|---|---|
| P0 聊天 | 0 | 聊天回复、命令；不排在模型后面 |
| P1 事件 | 1 | 定时、主动、提醒、通知 |
| P2 空闲 | 2 | 读书、抓取、浓缩、日记 |

- 快槽（EVENT）默认 1 个，慢槽（IDLE）默认 2 个；聊天走独立路径。
- 同 `kind:key` 未完成时不重复入队；超时取消；非超时失败按 `retries` 重试（上限 5）。
- 定时用 `loop.call_at` 逐项挂载；准点提醒预生成，绕过 3 秒合并。

### F.2 事件来源

| 来源 | 例子 | 进入方式 |
|---|---|---|
| QQ 消息 | 私聊/群聊/@/命令 | `chat.handler` |
| 定时 | cron_tasks、日程、待办 | `schedule` / `executors` |
| 主动 | 主动搭话、生活事件 | `executors/proactive.py` |
| 空闲 | 读书、浓缩、日记 | `executors/idle.py` |
| 提醒 | 准点、待办催办 | `executors/reminders.py` |
| HTTP | `/api/chat`、`/internal/chat` | `server` |

### F.3 出站四条保证

| 保证 | 做法 |
|---|---|
| 全局锁 | 同一时刻只有一个 `ws.send` |
| 断线入队 | 连接不可用不丢，重连补发 |
| echo 等待 | 撤回/取消息用同一出口，带超时 |
| 计数 | 按 kind 记成功/失败/入队/echo 超时 |

- 所有发送走 `bot.egress.outbound`；禁止业务直接 `ws.send`。
- 连发合并 0.6 秒防抖；命令同步执行，不排队。

### F.4 连发合并规则

- 同一对象 0.6 秒内的多条消息合并成一次上下文。
- 合并只影响“怎么理解”，不影响“怎么回”；回复仍分条。
- 准点提醒/命令不走合并，避免延迟。

---

## 附录 G · 部署 Runbook

### G.1 Linux systemd

```bash
sudo cp deploy/hoshinoumi.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now hoshinoumi
journalctl -u hoshinoumi -f
```

unit 里要改 `User`、`WorkingDirectory`、`ExecStart`；默认路径是 `/home/jyoushitou/NapCat-Pyhon`。旧 `nao-bot.service` 保留兼容。

### G.2 Docker（发布包）

```bash
docker load -i REC-v20.5.0-docker.tar.gz
docker load -i REC-v20.5.0-gateway-docker.tar.gz
cp .env.example .env && vi .env
docker compose -f docker-compose.release.yml up -d
docker compose -f docker-compose.release.yml logs -f
```

- 必须 `network_mode: host`：后端只监听 `127.0.0.1`。
- 数据挂载 `./data`、`./personas`、`./config`。
- 网关配置 `config/gateway.json` 只读挂载。

### G.3 Windows

```powershell
python -m pip install -r requirements.txt
python scripts\migrate.py --apply
python checks\env_check.py
python start.py
```

- 端口占用用 `netstat -ano | findstr 3001` 查。
- 建议用任务计划程序开机启动；生产仍推荐 Linux。

### G.4 升级

```bash
# 1. 备份
mysqldump ... > backup-$(date +%F).sql
# 2. 拉代码/解包
# 3. 迁移（幂等）
python3 scripts/migrate.py --apply
# 4. 预检
python3 checks/env_check.py
# 5. 重启
systemctl restart hoshinoumi
# 6. 验证
!version
!status
!stats
```

### G.5 回滚

- 代码回滚：`git checkout <上一个 tag>` 或解包上一版。
- 数据库：先停程序，恢复备份；**不要**在旧代码上跑新迁移后的库。
- 网关：回滚镜像 tag，配置不变。

### G.6 备份

- MySQL：`mysqldump --single-transaction`。
- SQLite：`sqlite3 data/nao.db ".backup ..."`，不要直接 `cp` 正在写的库。
- 自动备份：每月 1 号 04:30，保留 6 份。
- 换后端前必须备份；详见 [docs/存储后端与备份.md](docs/存储后端与备份.md)。

### G.7 日志与观测

| 项 | 位置/命令 |
|---|---|
| TXT 日志 | `logs/nao-YYYY-MM-DD.log` |
| DB 日志 | `logs` 表 |
| 最近日志 | `!log [行数]` |
| 数据库统计 | `!db` |
| 今日统计 | `!stats` |
| 网关 | `journalctl` / `docker logs`；`/healthz` `/readyz` |

---

## 附录 H · 测试地图

| 组 | 覆盖 |
|---|---|
| `test_chat` / `test_inbound` / `test_segments` | 入站解析、分条、引用上下文 |
| `test_memory` / `test_recall` / `test_facts` | 记忆检索、召回、事实卡 |
| `test_ai` / `test_vision` / `test_policy` | 模型、视觉、策略 |
| `test_schedule` / `test_cron` / `test_reminders` | 定时、cron、提醒 |
| `test_scheduler` / `test_workers` / `test_queue` | 调度器、worker、队列 |
| `test_outbound` / `test_egress_guard` / `test_merge` | 出站、锁、合并 |
| `test_server` / `test_api_key_env` | HTTP API、鉴权 |
| `test_ddl` / `test_schema` / `test_migrate_*` | 表结构、迁移 |
| `test_backup` / `test_restart` / `test_start` | 备份、重启、启动 |
| `test_quote_context` / `test_reply_quality` / `test_schedule_rules` | 回归 bug |

运行：

```bash
python3 scripts/run_tests.py          # tests + checks
python3 scripts/run_tests.py --fast   # 只跑 tests
python3 scripts/check_names.py        # 未定义名字
```

新增测试约定：

- 一个 bug 一条回归测试；测试名写清“什么场景”。
- 不依赖真实 NapCat/模型；用假 ws/假 provider。
- 涉及 DB 的测试用临时库/事务回滚，别写生产库。
- 改行为的提交必须同时改测试。

---

## 附录 I · 故障排查

| 现象 | 先看 | 处理 |
|---|---|---|
| `Unknown column` | 迁移日志 | `python3 scripts/migrate.py --apply` |
| MySQL 连不上 | 启动日志 `[存储]` | 修配置，或 `db.backend=sqlite` |
| NapCat 连不上 | `3001` 监听/防火墙 | NapCat 指向 `ws://host:3001` |
| `/api/*` 401 | 请求头 | `Authorization: Bearer <API_SERVER_TOKEN>` |
| `/internal/*` 401 | 不应发生 | 检查是否被网关加了鉴权 |
| 网关 `/readyz` 503 | 后端 `/api/health` | 先起后端；网关每 30 秒重试，最多 5 次 |
| 网关 502 | 后端地址/端口 | 检查 `config/gateway.json` 的 `backend.base` |
| 读书不工作 | `features.reading` / 依赖 | 装 Playwright/Chromium/tesseract |
| 语音没声 | edge-tts 网络/音色 | `!voice` 自检；看日志 |
| 回复很慢 | 模型/线程池 | `!usage`、`!stats`；看是否 P2 占满 |
| 重复回复 | 合并/去重 | 看 `test_reply_quality` 与日志 |
| 时间不对 | TZ | 设 `NAO_TZ=Asia/Shanghai` |
| 端口占用 | `netstat` | 改 `NAO_WS_PORT` / `NAO_API_PORT` |
| 测试改了 DB | 测试日志 | 停程序、备份后再恢复；不要直接 checkout 生产库 |

---

## 附录 J · 术语表

| 术语 | 含义 |
|---|---|
| NapCat | QQ 协议端，把 QQ 消息转成 OneBot WebSocket |
| OneBot v11 | NapCat 与 bot 之间的消息协议 |
| gateway | 本仓库的 C++ HTTP 网关，对外入口 |
| `user_id` | 账号/租户；当前固定 `__owner__` |
| `target_id` | 会话对象：私聊 QQ、群号、Web thread |
| `thread_id` | 多端同步的稳定会话 ID |
| P0/P1/P2 | 聊天/事件/空闲三档优先级 |
| egress | 唯一出站口 |
| BM25 / RRF | 关键词检索 / 倒数排名融合 |
| digest | 长会话浓缩行 |
| fact | 事实卡（槽位/值/可见性） |
| persona | 角色卡（prompt/supplement/life/state） |
| preflight | 启动前环境/依赖/数据库检查 |
| LITE | 历史计划里的轻量模式；当前未启用 |

---

## 写在最后

《Charlotte》大概是我真正意义上的启蒙番。TV 只有 13 集，这个长度每次想起来都觉得惋惜：明明还有那么多人的日常没来得及展开，明明故事还可以再慢一点。可也正因为短，它留白很多，才让人一直惦记。

喜欢友利奈绪，喜欢她明明很在意却偏要装得不在意，喜欢她把所有人的烂摊子都接过来，喜欢她拎着旧摄像机走在放学路上、嘴硬地说“随便你”。她不是完美的，她会别扭、会凶人、会在提到某个人的时候停半秒——但正是这些地方，让她像一个真的活着的人。

所以有了 Hoshinoumi。算是给“故事结束之后”补的一间学生会室：让她继续上学、开会、喂猫、弹琴，也让她在 QQ、Web、桌面和手机那边，记得你随口说过的话。

> 故事结束以后，她还在。










