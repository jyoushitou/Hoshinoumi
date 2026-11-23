# v35.8.2.3 真机矩阵记录

## 环境

| 设备 | 系统 | API | WebView | App | 结果 |
|---|---|---|---|---|---|
| Android Emulator `sdk_gphone64_x86_64` | Android 15 | 35 | 124.0.6367.219 | 35.8.2 debug | ✅ |
| MuMu 模拟器 | Android 15 | 35 | 110.0.5481.154 | 35.8.2 release | 🟡 仅手工看到配置页，ADB 断开待复测 |

## 已验证

```text
安装 / 启动
离线配置页
WebView 主框架失败回配置页
后端 10.0.2.2 / 127.0.0.1 + adb reverse
Mock 登录后聊天列表
键盘打开时输入框贴键盘
```

## 未覆盖

```text
Android 10–14
刘海 / 挖孔
手势导航
平板
MuMu 当前连接
低版本 WebView 108 以下
```

## 结论

```text
2.3 不能标记完成
当前只有 Android 15 模拟器通过
剩余机型需要真机/模拟器逐个跑
```
