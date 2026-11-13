# third_party

网关 v20 使用的 C++ 依赖源码，随仓库一起打包，保证 Docker 构建不依赖外部子模块。

| 目录 | 来源 | 用途 | 许可证 |
|---|---|---|---|
| `NetWorkCommunication/` | <https://github.com/jyoushitou/NetWorkCommunication> | CommonNet：Boost.Asio TCP + Boost.Beast HTTP | MIT |
| `Utils/` | <https://github.com/jyoushitou/Utils> | 日志 / 时间 / 优雅退出（CommonNet 的前置库） | MIT |

vcpkg 通过 overlay ports 使用它们：

```bash
vcpkg install commonnet \
  --overlay-ports=third_party/NetWorkCommunication/ports \
  --overlay-ports=third_party/Utils/ports
```

这里保留的是构建所需源码；`build/`、`.git/` 和二进制产物不提交。
