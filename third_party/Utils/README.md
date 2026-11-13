# Utils

通用的 C++ 工具库，提供 **I/O 输出、文件读写、时间处理与程序优雅退出** 等基础设施，供上位项目直接复用。

## 特性

- **统一输出**：控制台信息 / 错误 / 网络输出走同一套接口
- **文件与日志**：追加、覆写写文件，日志目录自动检查与创建
- **时间工具**：当前时间戳、时间差计算、格式化时间与日期字符串
- **优雅退出**：跨平台（Windows 控制台事件 / POSIX 信号）统一退出流程，支持注册停止回调
- **服务寻址**：`Message.h` 定义全局 `ServiceID` 枚举与名称转换
- **构建友好**：CMake 一键切换静态库 / 动态库，自动生成导出宏头文件，支持 `install` + `find_package`
- **开箱即用**：构建的同时自动把「公开头文件 + 生成的导出宏头」复制到库产物同级 `include/`，免安装即可直接引用

## 目录结构

```
Utils/
├─ CMakeLists.txt              # 构建脚本
├─ include/                    # 公开头文件（会被安装）
│  ├─ Message.h                # ServiceID 定义与名称转换
│  └─ Utils.h                  # 库主头文件
├─ source/                     # 实现（不安装）
│  └─ Utils.cpp
├─ tests/                      # 单元测试（CTest）
│  ├─ CMakeLists.txt
│  └─ main.cpp
├─ ports/                      # vcpkg 端口（上位工程 find_package 用）
│  └─ utils/
│     ├─ vcpkg.json            # 端口清单：包名 utils、版本、依赖
│     ├─ portfile.cmake        # 构建脚本：本地开发用工作区源码，发布用 GitHub 标签
│     ├─ usage                 # 安装后打印的使用说明
│     └─ LICENSE               # 随包安装的许可证
└─ cmake/
   └─ UtilsConfig.cmake.in     # 包配置模板，供 find_package 使用
```

## 环境要求

- C++17 及以上
- CMake 3.16 及以上
- 支持 MSVC / GCC / Clang

## 构建

```shell
# 配置（默认构建静态库）
cmake -S . -B build

# 构建动态库：追加 -DBUILD_SHARED_LIBS=ON
cmake -S . -B build -DBUILD_SHARED_LIBS=ON

# 编译（VS 等多配置生成器需指定 --config）
cmake --build build --config Release
```

### 构建 64 位（x64）版本

目标平台架构由 **CMake 生成器与工具链** 决定，`CMakeLists.txt` 本身无需改动，配置阶段选对平台即可。

**Visual Studio 生成器（默认 Win32，必须显式指定 x64）**

```powershell
cmake -S . -B build-x64 -G "Visual Studio 17 2022" -A x64
cmake --build build-x64 --config Release
```

- `-G` 请按本机安装的 VS 版本替换（如 `Visual Studio 16 2019`）；不写 `-A x64` 默认生成 Win32(x86)。
- 动态库再追加 `-DBUILD_SHARED_LIBS=ON`。
- 切换架构请使用**新的构建目录**（如 `build-x64`），不要复用旧的 `build`，否则会因生成器 / 平台不匹配报错。

**Ninja 生成器（需在 x64 开发者环境执行）**

```powershell
# 在 “x64 Native Tools Command Prompt for VS” 中执行
cmake -S . -B build-x64 -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build-x64
```

确保进入的是 `vcvars64.bat`（x64）而非 `vcvars32.bat`（x86）。

**MinGW-w64**

```powershell
cmake -S . -B build-x64 -G "MinGW Makefiles" `
  -DCMAKE_C_COMPILER=x86_64-w64-mingw32-gcc `
  -DCMAKE_CXX_COMPILER=x86_64-w64-mingw32-g++ `
  -DCMAKE_BUILD_TYPE=Release
cmake --build build-x64
```

**验证产物位数**

```powershell
dumpbin /headers build-x64\Release\Utils.lib | findstr machine
# 显示 machine (x64) 即为 64 位；(x86) 则是 32 位
```

> 多配置生成器（VS）务必带 `--config`（如 `--config Release`），否则默认走 Debug，产物位于 `build-x64\Debug\`。

主要产物（Windows + VS 生成器）：

| 产物             | 路径                                             |
| ---------------- | ------------------------------------------------ |
| 静态库           | `build/Release/Utils.lib`                        |
| 动态库           | `build/Release/Utils.dll` + `Utils.lib`          |
| 测试程序         | `build/tests/Release/UtilsTests.exe`             |
| 生成的导出宏头   | `build/include/UtilsExport.h`                    |
| 复制的公开头文件 | `build/include/Message.h`、`Utils.h`（构建时自动） |

> 构建完成后，`build/include/` 下即为「公开头文件 + 生成的 `UtilsExport.h`」一整套头，可直接连同库文件使用。

## 测试

```shell
cmake -S . -B build
cmake --build build --config Release
ctest --test-dir build -C Release --output-on-failure
```

## 安装与使用

```shell
cmake --install build --prefix out --config Release
```

在上位工程中通过包配置引入：

```cmake
find_package(Utils CONFIG REQUIRED)
target_link_libraries(your_app PRIVATE Utils::Utils)
```

同仓库联调也可直接源码引入：

```cmake
add_subdirectory(path/to/Utils)
target_link_libraries(your_app PRIVATE Utils::Utils)
```

## 通过 vcpkg 使用（推荐给上位工程）

本仓库内置了 vcpkg 端口（`ports/utils/`），装好之后**上位工程不需要再关心头文件路径和
`.lib` 路径，只写包名即可**：

```cmake
find_package(Utils CONFIG REQUIRED)
target_link_libraries(your_app PRIVATE Utils::Utils)
```

端口会按三元组自动选择链接方式，并自动带出 `Threads::Threads`、C++17 要求以及静态库所需
的 `Utils_STATIC_DEFINE` 宏——这正是它比「手动把 `Utils.lib` 拖进工程」更省事的地方，
Debug / Release 也不会再出现 ABI 混用。

### 1. 安装本包

```powershell
# 开发方式（端口就在源码仓库里）：直接拿当前工作区当源码，改完重装即生效，免 push 免联网
& $env:VCPKG_ROOT\vcpkg.exe install utils `
    --overlay-ports=D:\WebService_Project\Common_CPP\Utils\ports `
    --triplet x64-windows

# 正式方式：端口被单独发布成注册表后，从 GitHub 的 v1.0.0 标签构建
# （需先打好 v1.0.0 标签，并把下载到的 SHA512 填进 portfile.cmake）
& $env:VCPKG_ROOT\vcpkg.exe install utils --triplet x64-windows
```

- `--triplet x64-windows` 得到动态库，`--triplet x64-windows-static` 得到静态库。
- `ports/utils/portfile.cmake` 会自动判断：端口位于源码仓库内就用工作区源码，否则从
  GitHub 标签下载并校验 SHA512。
- 首次联网构建若报 SHA512 不匹配，vcpkg 会直接打印真实哈希值，复制进 portfile 即可。

### 2. 上位工程引用

上位工程用 `--overlay-ports`（或写进 `vcpkg-configuration.json`）指向本仓库的 `ports`
目录，然后在自己的 `CMakeLists.txt` 里 `find_package(Utils CONFIG REQUIRED)` 即可。

在 `CMakeLists.txt` 顶部指定 vcpkg 工具链（已有则忽略）：

```cmake
if(NOT DEFINED CMAKE_TOOLCHAIN_FILE AND DEFINED ENV{VCPKG_ROOT})
    set(CMAKE_TOOLCHAIN_FILE "$ENV{VCPKG_ROOT}/scripts/buildsystems/vcpkg.cmake"
        CACHE STRING "vcpkg toolchain")
endif()
```

配置时把三元组与 overlay 端口一起传进去：

```powershell
cmake -S . -B build -G "Visual Studio 17 2022" -A x64 `
  -DCMAKE_TOOLCHAIN_FILE="$env:VCPKG_ROOT/scripts/buildsystems/vcpkg.cmake" `
  -DVCPKG_OVERLAY_PORTS="D:/WebService_Project/Common_CPP/Utils/ports" `
  -DVCPKG_TARGET_TRIPLET=x64-windows
```

> 用 `x64-windows-static`（静态 CRT）时，上位工程需同时声明 `CMAKE_MSVC_RUNTIME_LIBRARY`
> 为 `MultiThreaded$<$<CONFIG:Debug>:Debug>`，否则会出现 `RuntimeLibrary` 不匹配的链接错误；
> 用默认的 `x64-windows`（动态 CRT）则无需任何额外设置。

### 3. 怎么在 vcpkg 里“找”这个包

`utils` 不在 [vcpkg 官方端口库](https://github.com/microsoft/vcpkg/tree/master/ports) 里，
所以 `vcpkg search utils` 找不到它——它是**本仓库自带的端口（overlay port）**。查找方式是
带上 `--overlay-ports` 让 vcpkg 去看本仓库：

```powershell
# 在官方端口库 + 本仓库端口里搜索（加 --overlay-ports 才会出现 utils）
& $env:VCPKG_ROOT\vcpkg.exe search utils --overlay-ports=D:\WebService_Project\Common_CPP\Utils\ports

# 看本机装了哪些版本（x64-windows / x64-windows-static 各一行）
& $env:VCPKG_ROOT\vcpkg.exe list utils

# 看完整描述（list 默认截断长文本）
& $env:VCPKG_ROOT\vcpkg.exe list utils --x-full-desc

# 机器可读的 JSON 输出（版本号、ABI、状态一目了然）
& $env:VCPKG_ROOT\vcpkg.exe list utils --x-json
```

“找”的完整链条是：**ports 目录（端口位置）→ 端口名 `utils`（安装写这个）→
`find_package(Utils)`（CMake 写这个）**。上位工程只要记住后两个。

### 4. 日常更新：改了 Utils 代码后怎么让 vcpkg 里的包也更新

> 核心要点：vcpkg 判断“要不要重建”只看 **版本号 + ABI 哈希**，而 overlay 端口的源码是
> 你本地工作区，**改代码不会改变这两者**——所以直接重装、加 `--recurse`、加
> `--no-binarycaching` 单独用都不行，vcpkg 会认为“已安装/缓存里有”，直接跳过。

正确的更新三步（实测有效）：

```powershell
# 1) 先在源码仓库里构建，确认改动本身没问题
cmake --build build\build-x64 --config Release
ctest --test-dir build\build-x64 -C Release --output-on-failure

# 2) 卸载旧包（关键一步：让 vcpkg 忘掉“已安装”这个状态）
& $env:VCPKG_ROOT\vcpkg.exe remove utils --triplet x64-windows

# 3) 重新安装（必须带 --no-binarycaching，否则会从二进制缓存里恢复旧包）
& $env:VCPKG_ROOT\vcpkg.exe install utils --no-binarycaching `
    --overlay-ports=D:\WebService_Project\Common_CPP\Utils\ports --triplet x64-windows
```

第 3 步若省略 `--no-binarycaching`，日志会显示 `Restored 1 package(s) from ...archives`，
装回去的是**旧代码**——这是最容易踩的坑。静态库版本同理，把三元组换成
`x64-windows-static` 再走一遍 2、3 步。

**怎么确认真的更新了**：库里 `Utils::init()` 会打印版本号，上位工程运行时第一行就是它；
也可以在包里搜字符串确认：

```powershell
Select-String -Path "$env:VCPKG_ROOT\installed\x64-windows\bin\Utils.dll" -Pattern 'Utils version' -Encoding ascii
```

上位工程侧只需重新构建即可，CMake 不用重新配置（头文件与库路径没变）：

```powershell
cmake --build build --config Release
```

**改了版本号时**（比如发布 1.1.0）：同步改 `ports/utils/vcpkg.json` 的 `version`，并在
仓库打上 `v1.1.0` 标签，其它机器的 vcpkg 才会去拉新源码；只改 `port-version`
（`1.0.0#1` 的 `#1`）表示“上游源码没变、只是端口脚本改了”，不会重新下载源码。

### 5. 包名与用法速查

| 项目         | 值                                                           |
| ------------ | ------------------------------------------------------------ |
| 端口名       | `utils`                                                      |
| CMake 查找名 | `find_package(Utils CONFIG REQUIRED)`                        |
| 链接目标     | `Utils::Utils`                                               |
| 头文件       | `#include "Utils.h"`（自动带出 `Message.h`、`UtilsExport.h`） |
| 端口位置     | `ports/utils/`                                               |
| 依赖         | 仅 `Threads`（系统线程库），无第三方依赖                     |
| 更新命令     | `remove` 后 `install --no-binarycaching`（见上一节）         |

### 6. 为支持发包所做的改动（需要改动源码时请注意）

| 改动                                       | 原因                                                                                         |
| ------------------------------------------ | -------------------------------------------------------------------------------------------- |
| 公开头文件与含中文的源文件改为 **UTF-8 带 BOM** | 头文件含中文注释且无 BOM 时，MSVC 在 GBK 代码页下会解析错乱，甚至吞掉 `#include`，使用方一编译就报错 |
| 公开接口补上 `Utils_API` 导出宏（含 `Utils::serviceID`） | `CXX_VISIBILITY_PRESET hidden` + generate_export_header 的语义要求显式导出，否则动态库链接失败 |
| `DEBUG_POSTFIX` 置空，Debug / Release 产物同名 | vcpkg 按「同名」打包两种配置，加 `d` 后缀会导致包校验失败；两者由各自目录区分，不会混淆     |
| `init()` 打印库版本号（`UTILS_VERSION` 宏）  | 一眼确认上位工程链接到的到底是哪一版，排查“包没更新”时非常有用                             |

## 快速开始（示例）

下面是一个最小可用示例，涵盖初始化、输出、时间、日志与优雅退出：

```cpp
// demo.cpp
#include "Utils.h"   // 库主头文件（会自动包含 Message.h 与 UtilsExport.h）

int main()
{
    // 1) 初始化：搭建控制台并注册退出相关处理，应在程序早期调用
    Utils::init();

    // 2) 设置本进程的服务ID（全局唯一，供日志/寻址使用）
    Utils::serviceID = User;

    // 3) 统一输出（信息 / 错误 / 网络）
    Utils::Out::outMsg("服务启动");
    Utils::Out::outErr("这是一条错误提示");
    Utils::Out::outNetMsg(1001, "网络输出示例");   // 参数：消息ID + 内容

    // 4) 时间工具
    time_t t0 = Utils::Time::nowTime();                          // 当前时间戳
    Utils::Out::outMsg("当前时间：" + Utils::Time::getNowtime()); // 格式化时间
    Utils::Out::outMsg("当前日期：" + Utils::Time::getNowDay()); // 格式化日期
    // ... 业务处理 ...
    Utils::Out::outMsg("本次处理耗时(秒)：" + std::to_string(Utils::Time::computeTime(t0)));

    // 5) 文件与日志
    Utils::File::setLogsDir("logs");        // 自定义日志目录（默认即 "logs"）
    Utils::File::checkLogsDir();            // 目录不存在则创建
    Utils::File::outLog("写入一条日志");     // 写入日志文件
    Utils::File::outFileAdd("data.txt", "追加一行\n"); // 追加写文件
    Utils::File::outFileWirte("data.txt", "覆盖内容\n"); // 覆写文件

    // 6) 优雅退出：注册停止回调，阻塞等待退出信号
    Utils::Exit::registerStopCallback([](){
        Utils::Out::outMsg("收到退出信号，开始清理资源...");
    });

    // 主线程在此阻塞，直到收到系统退出信号或外部调用 recviceExit()
    Utils::Exit::waitExit();

    // 退出流程（waitExit 返回后触发，或手动调用）
    Utils::Exit::gracefulShutdown();
    return 0;
}
```

> 编译时请确保 `UtilsExport.h` 与 `Message.h`、`Utils.h` 在同一包含目录（构建后位于 `build/include/`）。

- 完整示例可以参考tests/main.cpp文件

## 直接使用头文件 + 库文件

不使用 CMake 时，手动把「公开头文件 + 生成的导出宏头 + 库文件」组合起来即可。

### 需要的文件

| 类别       | 来源                                                                                  |
| ---------- | ------------------------------------------------------------------------------------- |
| 公开头文件 | `include/Message.h`、`include/Utils.h`                                                |
| 导出宏头   | 构建目录 `build/include/UtilsExport.h`（或安装后的 `out/include/UtilsExport.h`）      |
| 库文件     | 静态库 `Utils.lib` / `libUtils.a`，或动态库 `Utils.dll` + `Utils.lib` / `libUtils.so` |

> 注意：`UtilsExport.h` 由 `generate_export_header` 生成，不在源码树里，必须从构建/安装目录取。
> 头文件里 `#include "UtilsExport.h"`，因此二者要在同一包含目录中。
>
> 省事做法：构建完成后 `build/include/` 已经同时包含「公开头文件 + 生成的 `UtilsExport.h`」一整套，
> 直接把这个目录整体拷到你的工程即可（见上面「主要产物」表）。

### 推荐目录摆放

```
myapp/
├─ include/                # 直接把 build/include 整个目录拷贝过来即可
│  ├─ Message.h
│  ├─ Utils.h
│  └─ UtilsExport.h        # 构建时自动生成于 build/include
├─ lib/
│  └─ Utils.lib            # 静态库；动态库再从 build/Release 补 Utils.dll
└─ src/
   └─ main.cpp
```

### MSVC 命令行示例（静态库）

```bat
cl /std:c++17 /EHsc /I include src\main.cpp /link lib\Utils.lib
```

### GCC / Clang 命令行示例（静态库）

```shell
g++ -std=c++17 -I include src/main.cpp -L lib -lUtils -pthread -o myapp
```

### 动态库注意事项

- **Windows**：程序运行时需能找到 `Utils.dll`，把它放到 exe 同目录或加入 `PATH`。
- **Linux**：运行时需能找到 `libUtils.so`，可通过 `-Wl,-rpath` 指定路径，或设置 `LD_LIBRARY_PATH`。
- 动态库使用方**不要**定义 `Utils_STATIC_DEFINE`；链接静态库时才需要该宏（CMake 会自动处理，手动引用时按静态库默认即可）。

## 模块速览

| 模块     | 命名空间        | 说明                              |
| -------- | --------------- | --------------------------------- |
| 服务标识 | `ServiceID`     | 服务全局唯一 ID 及名称转换        |
| 时间     | `Utils::Time`   | 时间戳、时间差、格式化时间 / 日期 |
| 退出     | `Utils::Exit`   | 优雅退出、停止回调、退出等待      |
| 文件     | `Utils::File`   | 文件读写、日志目录与日志写入      |
| 输出     | `Utils::Out`    | 控制台 / 错误 / 网络输出          |
| 字符串   | `Utils::String` | 字符串分词等工具                  |

## 许可证

本项目基于 [MIT License](LICENSE) 开源，版权所有 (c) 2026 ThornFireSky。
