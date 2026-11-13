# ─────────────────────────────────────────────────────────────────────────────
# Utils 的 vcpkg 端口
#
# 两种源码来源，自动判定：
#
# 1) 本地开发（本文件位于源码仓库的 ports/utils/ 下）：直接使用仓库工作区当源码，
#    改完代码重新 install 即可，免 push、免联网、免改 SHA512：
#
#       & $env:VCPKG_ROOT\vcpkg.exe install utils `
#           --overlay-ports=D:\WebService_Project\Common_CPP\Utils\ports `
#           --triplet x64-windows
#
# 2) 正式发布（把 ports/ 单独发布成 vcpkg 注册表时）：从 GitHub 的 v${VERSION}
#    标签拉取源码并校验 SHA512。
# ─────────────────────────────────────────────────────────────────────────────

# 端口目录的上一级若也是源码仓库根（存在 CMakeLists.txt），说明正在源码仓库内开发
get_filename_component(_utils_port_parent "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE)

if(EXISTS "${_utils_port_parent}/CMakeLists.txt")
    # ── 本地开发：直接用工作区源码 ─────────────────────────────────────────
    message(STATUS "utils: 使用本地源码树 ${_utils_port_parent}")
    set(SOURCE_PATH "${_utils_port_parent}")
else()
    # ── 正式路径：从 GitHub 拉取 ───────────────────────────────────────────
    # 注意 REF 必须整体加引号，否则 CMake 不会展开 ${VERSION}
    vcpkg_from_github(
        OUT_SOURCE_PATH SOURCE_PATH
        REPO jyoushitou/Utils
        REF "v${VERSION}"
        SHA512 00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
        HEAD_REF main
    )
    # 上面的 SHA512 是占位值，发布标签后按下面任一方式取真值：
    #   1) vcpkg install utils --overlay-ports=ports --triplet x64-windows
    #      下载后校验失败时，vcpkg 会直接打印「实际是 ...」的真实 SHA512，复制回来即可；
    #   2) 下载 https://github.com/jyoushitou/Utils/archive/refs/tags/v1.0.0.tar.gz
    #      自行计算 SHA512 填进来。
endif()


string(COMPARE EQUAL "${VCPKG_LIBRARY_LINKAGE}" "dynamic" BUILD_SHARED_LIBS)

# 端口只出库本体：测试与示例一律关闭
# （这两个变量由根 CMakeLists.txt 的 option() 声明，因取值写死为 OFF，
#   配置期不会真正读入，故用 MAYBE_UNUSED_VARIABLES 抑制 vcpkg 的未使用告警）
vcpkg_cmake_configure(
    SOURCE_PATH "${SOURCE_PATH}"
    OPTIONS
        -DBUILD_SHARED_LIBS=${BUILD_SHARED_LIBS}
        -DUTILS_BUILD_TESTS=OFF
        -DUTILS_BUILD_EXAMPLES=OFF
    MAYBE_UNUSED_VARIABLES
        UTILS_BUILD_TESTS
        UTILS_BUILD_EXAMPLES
)

vcpkg_cmake_install()

# 本工程把包配置装在 lib/cmake/Utils，vcpkg 要求统一合并到 share/utils/cmake，
# 否则 Debug 与 Release 两份配置会互相覆盖（即官方 post-build 检查报的那两条警告）。
# 该函数顺带修正配置里的前缀路径；因导出文件名是 UtilsConfig.cmake，vcpkg 会保留
# 原名不改成 utils-config.cmake，find_package(Utils) 依然可用。
vcpkg_cmake_config_fixup(CONFIG_PATH lib/cmake/Utils)

# 静态库三元组下没有 pdb，该命令会自动跳过
vcpkg_copy_pdbs()

# 清理 debug 侧多余的头文件与文档副本
file(REMOVE_RECURSE
    "${CURRENT_PACKAGES_DIR}/debug/include"
    "${CURRENT_PACKAGES_DIR}/debug/share"
)

# 安装端口自带的使用说明（vcpkg install 结束时会把它打印出来）
file(INSTALL "${CMAKE_CURRENT_LIST_DIR}/usage"
    DESTINATION "${CURRENT_PACKAGES_DIR}/share/${PORT}")

# 安装许可证：优先用端口目录自带的副本，保证把 ports/ 单独发布成注册表时也不缺文件
if(EXISTS "${CMAKE_CURRENT_LIST_DIR}/LICENSE")
    file(INSTALL "${CMAKE_CURRENT_LIST_DIR}/LICENSE"
        DESTINATION "${CURRENT_PACKAGES_DIR}/share/${PORT}" RENAME copyright)
else()
    vcpkg_install_copyright(FILE_LIST "${SOURCE_PATH}/LICENSE")
endif()
