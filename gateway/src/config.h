/// @file        config.h
/// @brief       网关配置（config/gateway.json）
/// @author      jyoushitou
/// @date        2026-11-13
/// @copyright   Copyright (c) 2026
#pragma once

#include <string>

namespace Gateway
{
    /// @brief 网关运行配置
    /// @details 只放网关自己的监听与后端地址；API 密钥仍由后端配置管理。
    struct Config
    {
        /// @brief HTTP 监听地址（默认只监听本机）
        std::string listenHost = "127.0.0.1";

        /// @brief HTTP 监听端口
        unsigned short listenPort = 27005;

        /// @brief 后端 API 基地址（v20 只允许 127.0.0.1 / localhost）
        std::string backendBase = "http://127.0.0.1:27004";

        /// @brief 调后端的超时（毫秒）
        int backendTimeoutMs = 5000;

        /// @brief 启动时是否等待后端（默认开启）
        bool startupWait = true;

        /// @brief 启动等待重试间隔（秒）
        int startupRetryIntervalSec = 30;

        /// @brief 一轮启动等待最多尝试次数
        int startupMaxAttempts = 5;

        /// @brief 日志级别（info / debug）
        std::string logLevel = "info";

        /// @brief 从 JSON 文件加载；文件不存在或字段非法时抛 std::runtime_error
        static Config Load(const std::string& path);

        /// @brief 校验配置（端口、地址、后端只允许本机）
        void Validate() const;

        /// @brief 打印一行配置摘要（不打印敏感信息）
        std::string Describe() const;
    };
} // namespace Gateway

