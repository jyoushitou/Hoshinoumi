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

        /// @brief 调 GET /api/health；返回是否 2xx
        /// @param[out] detail 失败原因或状态摘要
        bool CheckHealth(std::string& detail) const;

    private:
        Config cfg_;
    };
} // namespace Gateway
