# Hoshinoumi Desktop

v35.6 Tauri 2 桌面套壳。

## 前置

```text
Node 20+ / pnpm
Rust 1.77+
WebView2 Runtime（Windows）
```

## 开发

```powershell
cd integrations/web
pnpm build
cd ../../clients/desktop/src-tauri
cargo run
```

前端构建产物：

```text
integrations/web/dist
```

Tauri 通过 `build.frontendDist` 直接加载，不复制第二套页面。

## 窗口

```text
1440 × 900 默认
最小 1180 × 760
无边框，自定义标题栏
```

## 当前阶段

```text
v35.6.0.0 壳骨架 / 窗口 / 标题栏 / 窗口控制
后续：托盘、路由设置、WebView2 固定运行时、兜底页
```

## 构建前置检查

```text
cargo check 需要能访问 crates.io
本轮网络更新 crates.io index 卡住，Rust 依赖编译尚未完成
工程文件与窗口配置已落盘
```
## Windows 工具链

```text
必须使用 stable-x86_64-pc-windows-msvc
工程内已有 rust-toolchain.toml 固定
需要 Visual Studio Build Tools（C++ 桌面开发）
不要用 windows-gnu，Tauri/WebView2 链接会失败
```
## 运行权限要求（重要）

Tauri/WebView2 必须在**普通权限（Medium Integrity）**下运行。

本机当前：

```text
EnableLUA=0（UAC 关闭）
所有管理员进程 High Integrity
cargo run 在 setup 阶段报 os error 5（拒绝访问）
```

处理：

```text
启用 UAC 并重启
→ 从普通权限终端 / VS Code 运行
→ 或在标准用户账户下运行
```

不要在管理员终端里直接 `cargo run`。
