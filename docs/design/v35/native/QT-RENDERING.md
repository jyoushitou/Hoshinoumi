# Qt 桌面渲染：DX11 / QRhi 与特效

## 结论

```text
Windows：Qt 6 QRhi D3D11（默认后端之一）
Linux：Vulkan / OpenGL（不能用 DX11）
```

DX11 不是“更多特效自动更省性能”，需要按帧率和 GPU 开销验收。

## Qt 6 渲染路径

```text
Qt Quick → QRhi → D3D11（Windows）
                → Vulkan / OpenGL（Linux）
```

可用：

```text
QSG_RHI_BACKEND=d3d11
QQuickWindow::setGraphicsApi(QSGRendererInterface::Direct3D11)
```

着色器：

```text
Qt Shader Baker（qsb）
ShaderEffect / MultiEffect
Qt Quick 3D
粒子 / 模糊 / 阴影 / 玻璃拟态
```

## 特效范围

```text
窗口进入/退出
聊天消息出现
小窗展开/收起
托盘弹窗
背景模糊 / 阴影
高光 / 渐变 / 轻量粒子
```

原则：

```text
动画优先 transform/opacity
避免每帧重建纹理
控制 overdraw
静态内容缓存
低端 GPU 自动降级
```

## 性能验收

```text
60Hz / 120Hz 帧率稳定
帧时间 p95 有上限
GPU 占用有上限
显存/内存有上限
关闭特效后可回退
```

具体数值在目标 Windows 机器和 Linux 机器实测，不把 DX11 指标套 Linux。

## 回退

```text
D3D11 初始化失败 → D3D12 / Vulkan / OpenGL
不支持硬件加速 → 软件回退并提示
不因为特效导致白屏或崩溃
```

## 版本

```text
v35.11.2.5 D3D11/QRhi 渲染与特效基础
v35.11.8.0 性能 / 包体 / 验收（包含特效降级）
```
