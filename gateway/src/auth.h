/// @file        auth.h
/// @brief       v21 owner 鉴权：HS256 JWT + access/refresh
/// @author      jyoushitou
/// @date        2026-11-13
/// @copyright   Copyright (c) 2026
#pragma once

#include "config.h"

#include <cstdint>
#include <string>

namespace Gateway
{
    /// @brief JWT 中本项目用到的声明
    struct Claims
    {
        std::string sub;    ///< owner
        std::string role;   ///< owner
        std::string type;   ///< access / refresh
        std::int64_t exp = 0;
    };

    /// @brief 单 owner 鉴权
    /// @details 不查 users 表；secret 只从配置/环境读，日志不打印全文。
    class Auth
    {
    public:
        explicit Auth(Config cfg);

        /// @brief 校验登录 secret（常量时间比较）
        bool CheckSecret(const std::string& secret) const;

        /// @brief 签发 access token
        std::string IssueAccess() const;

        /// @brief 签发 refresh token（v21.1 使用）
        std::string IssueRefresh() const;

        /// @brief 校验 token 签名/过期/类型
        bool Verify(const std::string& token, const std::string& type, Claims& claims) const;

        /// @brief 从 Authorization: Bearer xxx 中取 token
        static std::string Bearer(const std::string& headers);

        int AccessTtl() const { return cfg_.accessTtlSec; }

    private:
        std::string Issue(const std::string& type, int ttlSec) const;

        Config cfg_;
    };
} // namespace Gateway
