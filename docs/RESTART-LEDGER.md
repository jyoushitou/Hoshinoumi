# 重启升级台账

> 规则：**v25 之后普通业务版本只切 worker；只有无法共存的变更才登记到这里。**  
> 每次需要重启 ingress / gateway / 整套服务的版本，必须在本表补一行，写清范围、原因、停机和回滚。

## 已登记

| 版本 | 重启范围 | 原因 | 停机 | 回滚 |
|---|---|---|---|---|
| v25 系列首次部署 | ingress + supervisor（一次性进程迁移） | 从旧的直连模式切到“ingress 持有 3001/27004 + worker Unix socket” | 首次启动窗口；之后 worker 热更 | 停 ingress，回旧直连进程 |
| v26.0–v26.6 | **不用于生产直连** | 内部 27004 从 HTTP 改 TCP 帧的过渡版本；直连模式会丢 v25 热更 | — | 回 v25.7.0 |
| **v26.7.1** | **ingress 重启一次 + gateway 重建** | 27004 从 HTTP 改为 8+4+body TCP L4；协议不兼容，旧 ingress 不能接新 worker | ingress 重启数秒；worker 蓝绿切换 | ingress 回 `--protocol http` + gateway `protocol=http` + v25.7 worker |
| **v33 → v35.4** | **整套后端**（ingress / supervisor / worker / nao-run；gateway 视当前协议） | schema 33→35（财务表），且启动入口 `run.py`→`nao-run`、systemd 入口变化；旧 worker 不能跨 schema 热更 | 维护窗口：停写 → migrate → 启动；预计数分钟 | 恢复 DB 备份 + data/personas；回旧代码/旧 schema；systemd 回旧入口 |
| 未来 schema 迁移 | backend + gateway（按迁移窗口） | `schema_version` 变更，旧代码不能读新表 | 维护窗口 | 备份 + 回旧 schema/旧版本 |

## 不算“整套重启”

这些只重启一个容器/进程，不登记为整套重启：

- 只改 gateway：`docker compose up -d gateway`
- 只改 ingress：重启 ingress，worker 不动
- 只改 worker：`prepare_worker` + supervisor，ingress/gateway/NapCat 不动

## 登记模板

```text
版本：
重启范围：ingress / gateway / backend / 整套
原因：
是否协议不兼容：
预计停机：
回滚步骤：
验证：
```

## 当前基线

```text
后端：v35.2.25.1（v35.4.x 客户端/进程名）
网关：v26.4.0
schema：35
ingress：TCP L4（3001 WS + 27004 帧）
进程名：nao-run
热更新：worker 蓝绿，ingress/gateway 稳定
```

## v33 → v35.4 冷重启步骤

```text
1. 备份数据库 / data / personas / 配置
2. 停 ingress、supervisor、worker、gateway
3. 更新代码 + pip install -r requirements.txt
4. python3 scripts/migrate.py --apply
5. python3 checks/env_check.py
6. systemctl daemon-reload
7. 启动 nao-run.service
8. 验证 /readyz schema=35，聊天/记忆/存钱/关系
```

> 这一步是 schema + 启动入口变更，不能只 `prepare_worker` + supervisor 热切。
