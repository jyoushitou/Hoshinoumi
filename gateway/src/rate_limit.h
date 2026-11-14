/// @file        rate_limit.h
/// @brief       v22 令牌桶限流（每 IP 60 次/分钟）
/// @author      jyoushitou
/// @date        2026-11-14
/// @copyright   Copyright (c) 2026
#pragma once

#include <chrono>
#include <mutex>
#include <string>
#include <unordered_map>

namespace Gateway
{
    /// @brief 简单令牌桶
    /// @details 默认容量 60、每秒补 1 个；按 key（IP）独立。
    class RateLimiter
    {
    public:
        explicit RateLimiter(int capacity = 60, double refillPerSec = 1.0);

        /// @brief 尝试取一个令牌
        bool Allow(const std::string& key);

        /// @brief 当前剩余（整数，仅供响应头）
        int Remaining(const std::string& key);

    private:
        struct Bucket
        {
            double tokens = 0.0;
            std::chrono::steady_clock::time_point last{};
        };

        Bucket& Touch(const std::string& key);

        int capacity_;
        double refillPerSec_;
        std::mutex mutex_;
        std::unordered_map<std::string, Bucket> buckets_;
    };
} // namespace Gateway
