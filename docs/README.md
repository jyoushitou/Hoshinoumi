# Hoshinoumi（REC）· 文档索引

> **当前事实：后端 v20.5，网关 v20.5（Docker / 网关验证）**（2026-11-13）
> 已部署试运行；v19 与 v20.0–v20.4 已完成。
>
> 这里只放“现在有效”的文档；开发计划单独维护，历史文档明确标注。
> 如果文档与代码冲突，以代码和测试为准，并回来改文档。

## 先读哪几篇

| 顺序 | 文档 | 为什么先读 |
|---|---|---|
| 1 | [../README.md](../README.md) | 项目是什么、怎么跑、命令、限制 |
| 2 | [ARCHITECTURE.md](ARCHITECTURE.md) | 分层、一条消息的生命周期 |
| 3 | [DB-DESIGN.md](DB-DESIGN.md) | 表职责、字段规范 |
| 4 | [DEVELOPMENT-CADENCE.md](DEVELOPMENT-CADENCE.md) | 每个版本的试运行/下版本启动/介绍视频节奏 |
| [PRESENTATION-QA.md](PRESENTATION-QA.md) | 项目分享的问答底稿、演示翻车预案、不能展示的信息 |
| [发布检查清单.md](发布检查清单.md) | 改完/发版前逐项过 |
| 5 | [存储后端与备份.md](存储后端与备份.md) | 换库/备份/恢复 |

## 当前有效文档

| 文档 | 内容 | 维护状态 |
|---|---|---|
| [../README.md](../README.md) | 总览、快速开始、命令、配置、限制 | ✅ 现行 |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 分层图、消息生命周期、调度/出站 | ✅ 现行（以实际代码为准） |
| [DB-DESIGN.md](DB-DESIGN.md) | 数据库设计与表职责 | ✅ 现行（DDL 以 `bot/infra/schema.py` 为准） |
| [存储后端与备份.md](存储后端与备份.md) | MySQL/SQLite 备份、恢复、换后端 | ✅ 现行 |
| [发布检查清单.md](发布检查清单.md) | 代码/环境/文档/打包/部署 5 组检查 | ✅ 现行 |
| [NAMING.md](NAMING.md) | 项目命名、缩写、兼容边界 | ✅ 现行 |
| [RELEASE-NOTES.md](RELEASE-NOTES.md) | 发布记录（含当前 v20.5） | 🕘 只追加，不改旧记录 |
| [gateway/README.md](../gateway/README.md) | C++ 网关构建/配置/Docker | ✅ 现行 |

## 开发计划（单独维护）

开发计划**不在这个索引里展开**，避免和事实文档混在一起：

| 入口 | 内容 |
|---|---|
| [ROADMAP.md](ROADMAP.md) | 全部大版本的总表、依赖、验收 |
| [versions/](versions/) | 每个大版本一个 `vN.md` |
| [HANDOFF.md](HANDOFF.md) | 交接用的当前状态/坑/下一步 |

> 规则：新功能先写进 `docs/versions/vN.md`；已发布版本冻结；bug 记进当前开发版本的「遗留问题」。

## 历史文档（保留，但不再代表当前事实）

| 文档 | 是什么 | 怎么读 |
|---|---|---|
| [V6-功能.md](V6-功能.md) | v6 的功能清单（74 项） | 历史需求池，不代表已实现 |
| [V14-后续清单.md](V14-后续清单.md) | v14 之后的 13 项后续需求 | 历史需求池 |
| [ARCH-REVIEW.md](ARCH-REVIEW.md) | v18.20 的架构审查（6.2/10） | 历史审查；问题可能已修 |
| [升级到v18.20.md](升级到v18.20.md) | 从 v18.4 升到 v18.20 的步骤 | 历史升级路径；新版本看 README |
| [RELEASE-NOTES.md](RELEASE-NOTES.md) | 发布记录 | 只追加，旧记录保留原文 |

## 文档维护约定

1. **事实文档**（README/ARCHITECTURE/DB-DESIGN/存储/发布清单）随代码改，版本号、表数、命令数、测试数必须同步。
2. **计划文档**（ROADMAP/versions/HANDOFF）只管“接下来做什么”，不抄当前事实。
3. **历史文档**只加日期和“历史”标注，不追着改内容；需要新事实就写新文档。
4. 改完文档跑一次 `git diff --check`，别留行尾空格/坏表格。

---

## 历史索引（v5/v6 时期，保留原文）

> 下面是旧版文档索引，保留是为了不丢历史；当前事实以上文为准。

> **当时：v19.5.7 试运行** → 试运行结束后进入 v20 网关（一）。


> **协作规矩（2026-11 起）**
>
> 1. **任何新功能，先写进 `docs/versions/vN.md` 的开发计划**，不先写代码
> 2. 计划里写清：要做什么、验收标准、涉及文件、风险
> 3. 只在**当前版本号**内迭代；已发布版本冻结，不回头改
> 4. 一个功能一个功能做，每做完一个停下来确认
> 5. 新发现的 bug 记进**当前开发版本的**「遗留问题」，不往已发布版本塞
> 6. 版本号**只增不减**；不插入重排已发布的版本


| 版本 | 文档 | 内容 | 状态 |
|---|---|---|---|
| **v5** | 已归档 | **重构 + 修复**：7 条 bug（F 轨道）+ 拆分与抽象（R 轨道） | 已完成 |
| **v6+** | [V6-功能.md](V6-功能.md) | 74 项功能清单（按人味 / 记忆 / 生活 / 关系分组） | 待启动 |
| **v6 拆解** | 已归档 | 74 项 → **22 个可独立交付的功能单元**，含依赖图与推进顺序 | 已完成 |
| **v6~v13 路线图** | [ROADMAP.md](ROADMAP.md) | 版本主题、单元分配、验收与排期（当前以 ROADMAP 为准） | 现行 |
| **发布检查** | [发布检查清单.md](发布检查清单.md) | 每版必过的 5 组检查（代码 / 环境 / 文档 / 打包 / 部署） | 常用 |
| **命名** | [NAMING.md](NAMING.md) | Hoshinoumi（REC）的正式写法、缩写与兼容边界 | 现行 |
| **v14+ 后续** | [V14-后续清单.md](V14-后续清单.md) | 13 项后续需求（A~D 分组，v14+ 独立编号体系） | 待排期 |
| **单版计划** | [versions/](versions/) | 每版一个文件：[v6](versions/v6.md) · [v7](versions/v7.md) · [v8](versions/v8.md) · [v9](versions/v9.md) · [v10](versions/v10.md) · [v11](versions/v11.md) · [v12](versions/v12.md) · [v13](versions/v13.md) · [v14](versions/v14.md) | 方案稿 |

## 版本约定

- **超出 v6–v13 范围的新需求**：先写进 [V14-后续清单.md](V14-后续清单.md)，**不直接改代码**；明确指定后才做。
- **v5 只动结构 + 修已知缺陷**：不加新功能。
- **v6 才加功能**：人味、记忆、关系那一整套。
- **一个提交只做一件事**：修 bug 的提交不改结构，重构的提交不改行为。

## 先后顺序

```
v5：R0 冒烟 → F1~F7 修复 → R1 端口 → R2 斩环 → R3 模型 → R4 传输 → R5 命令 → R6 仓储 → 回归
                              ↓
v6：P1 会说话 → P2 说实话 → P2.5 长感官 → P3 有生活 → P4 记得住 → P4.5/4.6 关系 → P5 不散架 → P6 能力
```

## 已从 v6 移入 v5 的条目

| v6 编号 | 功能 | 移入 v5 |
|---|---|---|
| A2 | 兜底隔离 | F2 |
| A4 | 无动作省略 | F1 |
| A5 | 代码模式通道 | F3（同根） |
| D21 | 时间感知 | F7 |
| E30 | 图片链路 | F4 |

| 版本 | 计划 | 内容 | 状态 |
|---|---|---|---|
| **v16** | [versions/v16.md](versions/v16.md) | 空闲时自己读小说（番茄/起点，记进度、聊剧情） | 规划中 |
| **v17** | [versions/v17.md](versions/v17.md) | 执行模型重构（16 个次版本，v17.17.0 已发布） | ✅ 已发布 |
| **v18** | [versions/v18.md](versions/v18.md) | 情感的深刻度：记忆分量 → 事实卡 → 情绪跨天 …（21 个次版本，18.0–18.20） | ✅ 已完成（v18.20.0） |
| **v19** | [versions/v19.md](versions/v19.md) | 架构重构 + 对话同步底座：迁移单一入口、`conversation_messages`、`!history`、语音分段 | 🚧 试运行（v19.5.7） |
| **v20** | [versions/v20.md](versions/v20.md) | 网关（一）核心：C++/Drogon + REST↔gRPC 代理 | 规划中 |
| **v21** | [versions/v21.md](versions/v21.md) | 网关（二）owner 鉴权：JWT/刷新/失败锁定 | 规划中 |
| **v22** | [versions/v22.md](versions/v22.md) | 网关（三）安全：限流/审计/TLS/`!gw` | 规划中 |
| **v23** | [versions/v23.md](versions/v23.md) | 多用户 + 亲密度可骤降/负值/修复，归零降私聊回复 | 规划中 |
| **v24** | [versions/v24.md](versions/v24.md) | 插件接口实现 | 规划中 |
| **v25** | [versions/v25.md](versions/v25.md) | 模型层接口实现 | 规划中 |
| **v26** | [versions/v26.md](versions/v26.md) | 记忆层接口实现 | 规划中 |
| **v27** | [versions/v27.md](versions/v27.md) | 通道层接口实现 | 规划中 |
| **v28** | [versions/v28.md](versions/v28.md) | 工具层接口实现 | 规划中 |
| **v29** | [versions/v29.md](versions/v29.md) | 存储层接口实现 | 规划中 |
| **v30** | [versions/v30.md](versions/v30.md) | 调度层接口实现 | 规划中 |
| **v31** | [versions/v31.md](versions/v31.md) | 出站层接口实现 | 规划中 |
| **v32** | [versions/v32.md](versions/v32.md) | 默认链路选择实现 | 规划中 |
| **v33** | [versions/v33.md](versions/v33.md) | 多端推送：主动消息扇出到所有接入口 | 规划中 |
| **v34** | [versions/v34.md](versions/v34.md) | 本机服务化：常驻 / 自启 / 健康检查 | 规划中 |
| **v35** | [versions/v35.md](versions/v35.md) | DSH 插件：本机工具注册与调用 | 规划中 |
| **v36** | [versions/v36.md](versions/v36.md) | Qoder / WorkBuddy 插件与安装器 | 规划中 |
| **v37** | [versions/v37.md](versions/v37.md) | 电脑 Web：聊天 + 历史 + 功能面板 | 规划中 |
| **v38** | [versions/v38.md](versions/v38.md) | 桌面端（一）Linux：Tauri + Web UI | 规划中 |
| **v39** | [versions/v39.md](versions/v39.md) | 桌面端（二）Windows：Tauri + WebView2 | 规划中 |
| **v40** | [versions/v40.md](versions/v40.md) | 手机 App（Flutter）+ 推送通知 + 记账 | 规划中 |
| **v41** | [versions/v41.md](versions/v41.md) | 手机 App 独立模式：离线对话/记账，恢复立即同步 | 规划中 |
| **v42** | [versions/v42.md](versions/v42.md) | QQ 空间：发说说 + 只对熟人点赞/评论 | 规划中 |
| **v43** | [versions/v43.md](versions/v43.md) | 运维（一）bash 只读 | 规划中 |
| **v44** | [versions/v44.md](versions/v44.md) | 运维（二）agent | 规划中 |
| **v45** | [versions/v45.md](versions/v45.md) | 运维（三）有限写 | 规划中 |
| **v46** | [versions/v46.md](versions/v46.md) | 运维（四）可写体系 | 规划中 |
| **v47** | [versions/v47.md](versions/v47.md) | 视频（一）B 站 | 规划中 |
| **v48** | [versions/v48.md](versions/v48.md) | 视频（二）抖音 | 规划中 |
| **v49** | [versions/v49.md](versions/v49.md) | 微信接入（OpenClaw） | 规划中 |
| **v50** | [versions/v50.md](versions/v50.md) | 语音通话 | 规划中 |
| **v51** | [versions/v51.md](versions/v51.md) | 视频通话 | 规划中 |
| **v52** | [versions/v52.md](versions/v52.md) | 微服务接入：融进自有 Web，探网关 5 次 + 池复用 | 规划中 |
| **v53** | [versions/v53.md](versions/v53.md) | 常驻（后端）systemd / 看门狗 | 规划中 |
| **v54** | [versions/v54.md](versions/v54.md) | 嵌入式前端（Linux 后端）：树莓派/平板显示对话 | 规划中 |



> 文档里所有 vXXX 功能都是核心功能；v24–v32 本身是核心代码里的接口定义，
> 不是插件，也不是功能实现。
> 插件接口只给第三方做优化/性能扩展，后续版本不会用插件接口实现功能。
> 核心功能只能在启动前通过 `config/features.json` / `NAO_FEATURES` 关闭。

> 完整发布计划（次版本/小版本拆分）见 **[ROADMAP.md](ROADMAP.md)**。

> 数据库设计见 **[DB-DESIGN.md](DB-DESIGN.md)**（一表一职责）。
> 架构审查见 **[ARCH-REVIEW.md](ARCH-REVIEW.md)**（分层/环/巨石函数，含修复顺序）。
> 架构图见 **[ARCHITECTURE.md](ARCHITECTURE.md)**（分层/消息流/调度模型/架构债）。










