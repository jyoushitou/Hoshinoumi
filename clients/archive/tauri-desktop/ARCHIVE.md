# Tauri 工程归档

状态：**已停用，仅保留参考**。

归档时间：2026-11-21

## 停用原因

```text
系统 WebView2 初始化失败：
HRESULT(0x8000FFFF) 灾难性故障
```

已尝试：

```text
MinGW → MSVC
UAC 开启
手动指定 WebView 数据目录
--disable-gpu
手动创建窗口
```

窗口能出现，但 WebView2 页面加载仍失败/闪退。

## 当前替代

```text
clients/electron/
Electron 内置 Chromium
```

## 保留内容

```text
src-tauri/  Rust 源码、配置、图标、Cargo.lock
README.md   Tauri 阶段说明
```

不要在新构建中继续使用本目录；仅作排查记录和历史参考。
