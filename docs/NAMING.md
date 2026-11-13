# 项目命名：Hoshinoumi（REC）

## 正式写法

| 场景 | 写法 |
|---|---|
| 产品名 / 仓库名 / 服务名 | **Hoshinoumi** |
| 中文名 | **星之海** |
| 文档缩写 | **REC**（全大写） |
| 完整称呼 | **Hoshinoumi（REC）** |
| 角色名 | **友利奈绪**（不改） |

示例：

```text
Hoshinoumi（REC）· 友利奈绪 v19.5.7
Hoshinoumi 服务：hoshinoumi.service
发布包：hoshinoumi-v19.5.7.bundle
```

## 为什么是 Hoshinoumi

- 来自 preset 里的「星之海学园」，是**她所在的世界**，不是某个技术组件。
- 比「QQ 机器人」「NapCat + Python」更能覆盖现在的能力：记忆、情绪、多端、API。
- 角色仍然叫友利奈绪，**产品名和角色名分开**：以后换 persona，产品不用改名。

## 为什么文档缩写是 REC

REC 取「Record / 录制」：

- 她手里那台旧摄像机，一直在记录；
- 记忆、日记、对话历史都是「被录下来的东西」；
- 两个字母，适合放在表格、日志、版本页眉、图片角标里。

用法：

```text
正式：Hoshinoumi（REC）
正文首次出现：Hoshinoumi（REC，记录）
之后可写：REC
不要写：REC Bot、Hoshinoumi Bot
```

## 兼容边界（先不改的东西）

这些旧名字**暂时保留**，避免现有部署和 import 断裂：

| 旧名 | 处理 |
|---|---|
| 目录 `NapCat+Pyhon` | 暂留；服务路径仍指向它 |
| Python 包 `botv` | 暂留；作为内部命名空间 |
| 服务 `nao-bot` | 保留旧 unit；新增 `hoshinoumi.service` 可切换 |
| 发布物 `nao-v*` | 历史产物不改名；新打包逐步用 `hoshinoumi-v*` |

迁移顺序：先改可见品牌（README / 服务 / 版本输出 / 文档），再改目录和包名。
改包名时保留 `botv` 兼容层，不要一次性全仓替换。
