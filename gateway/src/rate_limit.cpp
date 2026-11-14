/// @file        rate_limit.cpp
/// @brief       令牌桶限流实现
/// @author      jyoushitou
/// @date        2026-11-14
/// @copyright   Copyright (c) 2026

#include "rate_limit.h"

#include <algorithm>
#include <cmath>

namespace Gateway
{
    RateLimiter::RateLimiter(int capacity, double refillPerSec)
        : capacity_(std::max(1, capacity)), refillPerSec_(std::max(0.01, refillPerSec))
    {
    }

    RateLimiter::Bucket& RateLimiter::Touch(const std::string& key)
    {
        auto& b = buckets_[key];
        const auto now = std::chrono::steady_clock::now();
        if (b.last.time_since_epoch().count() == 0)
        {
            b.tokens = static_cast<double>(capacity_);
            b.last = now;
            return b;
        }
        const double elapsed = std::chrono::duration<double>(now - b.last).count();
        b.tokens = std::min<double>(capacity_, b.tokens + elapsed * refillPerSec_);
        b.last = now;
        return b;
    }

    bool RateLimiter::Allow(const std::string& key)
    {
        std::lock_guard<std::mutex> lock(mutex_);
        Bucket& b = Touch(key);
        if (b.tokens < 1.0)
        {
            return false;
        }
        b.tokens -= 1.0;
        return true;
    }

    int RateLimiter::Remaining(const std::string& key)
    {
        std::lock_guard<std::mutex> lock(mutex_);
        Bucket& b = Touch(key);
        return static_cast<int>(std::floor(b.tokens));
    }
} // namespace Gateway
