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
