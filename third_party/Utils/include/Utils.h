/// @file        Utils.h
/// @brief       I/O、时间、优雅退出
/// @author      jyoushitou
/// @date        2026-09-16
/// @copyright   Copyright (c) 2026

// 防止重复包含
#pragma once

#include <functional>

#include "Message.h"

// 由 CMake 的 generate_export_header() 生成（构建目录或安装目录的 include/ 下），
// 静态库时 Utils_API 展开为空，动态库时展开为 __declspec(dllexport/dllimport)。
// 用引号包含属于有意为之：它不在源码树里，由构建系统提供。
#include "UtilsExport.h"

#include <string>
#include <atomic>

#ifdef _WIN32

#include <windows.h>

#endif

namespace Utils
{
    /// @brief      当前服务器ID
    /// @details    存储本服务进程的全局唯一ID
    /// @note       使用原子属性
    /// @warning    动态库场景必须带导出宏，否则使用方链接时找不到符号
    extern Utils_API std::atomic<ServiceID> serviceID;

    /// @namespace  Time
    /// @brief      时间工具子模块
    /// @details    提供当前时间与日期的格式化获取
    /// @note
    namespace Time
    {
        /// @brief 获得当前时间
        /// @details 获得当前时间
        /// @warning 获得的是time_t
        Utils_API time_t nowTime();

        /// @brief 计算时间差
        /// @details 计算时间戳到当前的时间差
        /// @param[in] oldtime 之前的时间戳
        /// @return 返回计算出来的时间
        Utils_API time_t computeTime(const time_t& oldtime);

        /// @brief      获取当前时间
        /// @details    返回当前时刻的格式化字符串
        /// @return     格式化后的时间字符串
        /// @warning    获得的是字符串格式
        Utils_API std::string getNowtime();

        /// @brief      获取当前日期
        /// @details    返回当前日期的格式化字符串
        /// @return     格式化后的日期字符串
        /// @note
        Utils_API std::string getNowDay();

    } // namespace Time

    /// @namespace  Exit
    /// @brief      退出子模块
    /// @details    统一管理程序的优雅退出流程
    /// @note
    namespace Exit
    {
        /// @brief      注册停止回调
        /// @details    注册退出时需要回调的停止服务函数
        /// @param[in] cb 停止服务的回调函数
        /// @note
        Utils_API void registerStopCallback(std::function<void()> cb);

        /// @brief      统一退出函数
        /// @details    执行优雅退出的完整流程
        /// @warning    应保证在退出过程中不被重复调用
        /// @note
        Utils_API void gracefulShutdown();

        /// @brief      信号处理函数
        /// @details    按键/信号触发时的处理逻辑
        /// @param[in] sig 信号编号
        /// @note
        Utils_API void onsignal();

        /// @brief      清理资源
        /// @details    释放退出过程中占用的资源
        /// @warning    TODO
        Utils_API void cleanUp();

        /// @brief      阻塞等待退出信号
        /// @details    阻塞当前线程直至收到退出信号
        /// @note
        Utils_API void waitExit();

        /// @brief      主动触发退出
        /// @details    由外部主动发起的退出请求
        /// @note
        Utils_API void recviceExit();
    } // namespace Exit

    /// @namespace  File
    /// @brief      文件子模块
    /// @details    负责日志与普通文件的读写
    /// @note
    namespace File
    {
        /// @brief      日志的写入路径
        /// @details    日志文件存放的目录
        /// @note       含 inline 的变量每个翻译单元各有一份，无需导出宏
        inline std::string logsdir = "logs";

        /// @brief      设置自定义的日志文件目录
        /// @details    修改日志文件存放目录
        /// @param[in] dir 日志目录路径
        /// @warning    须保证目录已存在或可创建
        /// @note
        Utils_API void setLogsDir(const std::string dir);

        /// @brief      检查日志目录
        /// @details    检查是否有logs文件夹，没有则创建
        /// @return     目录可用返回 true，否则返回 false
        /// @note
        Utils_API void createDir(std::string dir);

        /// @brief      追加写入文件
        /// @details    以追加方式向指定文件写入内容
        /// @param[in] addr 文件路径
        /// @param[in] msg  待写入内容
        /// @return     写入成功返回 true，否则返回 false
        /// @note
        Utils_API bool outFileAdd(const std::string addr, const std::string msg);
        /// @brief      覆写文件
        /// @details    以覆盖方式向指定文件写入内容
        /// @param[in] addr 文件路径
        /// @param[in] msg  待写入内容
        /// @return     写入成功返回 true，否则返回 false
        /// @note
        Utils_API bool outFileWirte(const std::string addr, const std::string msg);

        /// @brief      写入日志
        /// @details    将消息写入日志文件
        /// @param[in] msg 日志内容
        /// @note
        Utils_API void outLog(const std::string msg);
    } // namespace File

    /// @namespace  Out
    /// @brief      输出子模块
    /// @details    统一控制台与网络的输出接口
    /// @note
    namespace Out
    {
        /// @brief      输出信息
        /// @details    普通信息输出
        /// @param[in] msg 输出内容
        /// @note
        Utils_API void outMsg(const std::string msg);
        /// @brief      输出错误信息
        /// @details    错误信息输出
        /// @param[in] msg 输出内容
        /// @note
        Utils_API void outErr(const std::string msg);

        /// @brief      网络输出
        /// @details    网络部分输出
        /// @param[in] msg_id 消息全局唯一ID
        /// @param[in] msg 消息内容
        /// @warning
        /// @note
        Utils_API void outNetMsg(unsigned long long msg_id, std::string msg);
    } // namespace Out

    /// @namespace  String
    /// @brief      字符串子模块
    /// @details    提供字符串分词等相关工具
    /// @note
    namespace String
    {
        /// @brief      数据分词
        /// @details    按指定分隔符切分字符串，默认以 | 为区分
        /// @param[in] str  待切分的字符串
        /// @param[in] post 起始位置
        /// @param[in] c    分隔字符
        /// @return     切分后的字符串集合
        /// @warning    分隔符参数默认值存在书写问题，使用前请确认
        /// @note
        Utils_API std::vector<std::string> split(const std::string& str = "", const int& post = 0, const char& c = '|');
    } // namespace String

    /// @brief      初始化
    /// @details    初始化控制台，并注册退出相关的回调
    /// @warning    应在程序启动早期调用
    /// @note
    Utils_API void init();
} // namespace Utils
