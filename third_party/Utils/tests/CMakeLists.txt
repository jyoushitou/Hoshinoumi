# 测试可执行文件：直接编译本目录下的测试源文件（当前为 main.cpp，自带 main()）
add_executable(UtilsTests ${CMAKE_CURRENT_SOURCE_DIR}/main.cpp)

# 同仓库内直接用别名目标，静态/动态库都适用
target_link_libraries(UtilsTests PRIVATE Utils::Utils Threads::Threads)

# 注册为 CTest 用例（enable_testing() 已在根 CMakeLists.txt 中调用）
add_test(NAME UtilsTests COMMAND UtilsTests)

# Windows 动态库场景：把 DLL 拷到 exe 同目录，保证 ctest 能直接运行
add_custom_command(TARGET UtilsTests POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
            $<TARGET_FILE:Utils> $<TARGET_FILE_DIR:UtilsTests>
)