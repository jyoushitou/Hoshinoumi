/// @file        backend.h
/// @brief       后端 API 探活（用 CommonNet HttpClient）
/// @author      jyoushitou
/// @date        2026-11-13
/// @copyright   Copyright (c) 2026
#pragma once

#include "config.h"

#include <string>

namespace Gateway
{
    /// @brief 后端客户端
    /// @details v20.0 只做健康检查；v20.1 再补 chat/history 转发。
    class BackendClient
    {
    public:
        explicit BackendClient(Config cfg);

        /// @brief 一次后端请求结果
        struct Result
        {
            bool ok = false;
            unsigned status = 0;
            std::string body;
            std::string error;
        };

        /// @brief 调 GET /api/health；返回是否 2xx
        /// @param[out] detail 失败原因或状态摘要
        bool CheckHealth(std::string& detail) const;

        /// @brief 发一次 JSON 请求（同步，必须在工作线程调用）
        /// @param[in] owner 已鉴权的 owner；非空时写入 X-Owner-Id
        Result Request(const std::string& method, const std::string& path,
                       const std::string& body, const std::string& owner = "") const;

    private:
        Config cfg_;
    };
} // namespace Gateway
