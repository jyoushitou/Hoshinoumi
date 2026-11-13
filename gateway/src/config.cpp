/// @file        config.cpp
/// @brief       网关配置加载与校验
/// @author      jyoushitou
/// @date        2026-11-13
/// @copyright   Copyright (c) 2026

#include "config.h"

#include <boost/json.hpp>

#include <cstdlib>
#include <fstream>
#include <sstream>
#include <stdexcept>

namespace Gateway
{
    namespace
    {
        std::string ReadFile(const std::string& path)
        {
            std::ifstream in(path);
            if (!in)
            {
                throw std::runtime_error("读不到配置文件: " + path);
            }
            std::ostringstream ss;
            ss << in.rdbuf();
            std::string text = ss.str();
            // Windows 编辑器/PowerShell 常带 UTF-8 BOM；Boost.JSON 不吃 BOM
            if (text.size() >= 3 &&
                static_cast<unsigned char>(text[0]) == 0xEF &&
                static_cast<unsigned char>(text[1]) == 0xBB &&
                static_cast<unsigned char>(text[2]) == 0xBF)
            {
                text.erase(0, 3);
            }
            return text;
        }

        std::string GetString(const boost::json::object& obj, const char* key, const std::string& fallback)
        {
            const auto* value = obj.if_contains(key);
            if (value == nullptr)
            {
                return fallback;
            }
            if (!value->is_string())
            {
                throw std::runtime_error(std::string("配置字段不是字符串: ") + key);
            }
            return std::string(value->as_string().c_str());
        }

        int GetInt(const boost::json::object& obj, const char* key, int fallback)
        {
            const auto* value = obj.if_contains(key);
            if (value == nullptr)
            {
                return fallback;
            }
            if (!value->is_int64())
            {
                throw std::runtime_error(std::string("配置字段不是整数: ") + key);
            }
            return static_cast<int>(value->as_int64());
        }

        bool GetBool(const boost::json::object& obj, const char* key, bool fallback)
        {
            const auto* value = obj.if_contains(key);
            if (value == nullptr)
            {
                return fallback;
            }
            if (!value->is_bool())
            {
                throw std::runtime_error(std::string("配置字段不是布尔值: ") + key);
            }
            return value->as_bool();
        }
    } // namespace

    Config Config::Load(const std::string& path)
    {
        const std::string text = ReadFile(path);
        boost::json::value root;
        try
        {
            root = boost::json::parse(text);
        }
        catch (const std::exception& e)
        {
            throw std::runtime_error(std::string("配置文件不是合法 JSON: ") + e.what());
        }
        if (!root.is_object())
        {
            throw std::runtime_error("配置文件顶层必须是对象");
        }

        const auto& obj = root.as_object();
        Config cfg;
        if (const auto* listen = obj.if_contains("listen"); listen != nullptr && listen->is_object())
        {
            const auto& l = listen->as_object();
            cfg.listenHost = GetString(l, "host", cfg.listenHost);
            cfg.listenPort = static_cast<unsigned short>(GetInt(l, "port", cfg.listenPort));
        }
        if (const auto* backend = obj.if_contains("backend"); backend != nullptr && backend->is_object())
        {
            const auto& b = backend->as_object();
            cfg.backendBase = GetString(b, "base", cfg.backendBase);
            cfg.backendTimeoutMs = GetInt(b, "timeout_ms", cfg.backendTimeoutMs);
            cfg.startupWait = GetBool(b, "startup_wait", cfg.startupWait);
            cfg.startupRetryIntervalSec = GetInt(b, "startup_retry_interval_sec",
                                                cfg.startupRetryIntervalSec);
            cfg.startupMaxAttempts = GetInt(b, "startup_max_attempts",
                                            cfg.startupMaxAttempts);
        }
        if (const auto* auth = obj.if_contains("auth"); auth != nullptr && auth->is_object())
        {
            const auto& a = auth->as_object();
            cfg.ownerSecret = GetString(a, "secret", cfg.ownerSecret);
            cfg.accessTtlSec = GetInt(a, "access_ttl_sec", cfg.accessTtlSec);
            cfg.refreshTtlSec = GetInt(a, "refresh_ttl_sec", cfg.refreshTtlSec);
        }
        if (const char* envSecret = std::getenv("NAO_GATEWAY_OWNER_SECRET");
            envSecret != nullptr && *envSecret != '\0')
        {
            cfg.ownerSecret = envSecret;
        }
        cfg.logLevel = GetString(obj, "log_level", cfg.logLevel);
        cfg.Validate();
        return cfg;
    }

    void Config::Validate() const
    {
        if (listenHost.empty())
        {
            throw std::runtime_error("listen.host 不能为空");
        }
        if (listenPort == 0)
        {
            throw std::runtime_error("listen.port 必须在 1..65535");
        }
        if (backendTimeoutMs <= 0)
        {
            throw std::runtime_error("backend.timeout_ms 必须大于 0");
        }
        if (startupRetryIntervalSec <= 0 || startupRetryIntervalSec > 3600)
        {
            throw std::runtime_error("backend.startup_retry_interval_sec 必须在 1..3600");
        }
        if (startupMaxAttempts <= 0 || startupMaxAttempts > 100)
        {
            throw std::runtime_error("backend.startup_max_attempts 必须在 1..100");
        }
        if (accessTtlSec < 60 || accessTtlSec > 604800)
        {
            throw std::runtime_error("auth.access_ttl_sec 必须在 60..604800");
        }
        if (refreshTtlSec < 300 || refreshTtlSec > 31536000)
        {
            throw std::runtime_error("auth.refresh_ttl_sec 必须在 300..31536000");
        }
        if (logLevel != "info" && logLevel != "debug")
        {
            throw std::runtime_error("log_level 只支持 info / debug");
        }

        // v20 硬规则：后端只允许本机，避免网关绕过内网边界
        const bool loopback = backendBase.rfind("http://127.0.0.1:", 0) == 0 ||
                              backendBase.rfind("http://localhost:", 0) == 0;
        if (!loopback)
        {
            throw std::runtime_error("backend.base 只允许 http://127.0.0.1:... 或 http://localhost:...");
        }
        if (!backendBase.empty() && backendBase.back() == '/')
        {
            throw std::runtime_error("backend.base 末尾不要带 /");
        }
    }

    std::string Config::Describe() const
    {
        return "listen=" + listenHost + ":" + std::to_string(listenPort) +
               " backend=" + backendBase +
               " timeout_ms=" + std::to_string(backendTimeoutMs) +
               " startup_wait=" + (startupWait ? "true" : "false") +
               " startup_interval=" + std::to_string(startupRetryIntervalSec) + "s" +
               " startup_attempts=" + std::to_string(startupMaxAttempts) +
               " auth=" + (ownerSecret.empty() ? "off" : "on") +
               " access_ttl=" + std::to_string(accessTtlSec) + "s" +
               " log_level=" + logLevel;
    }
} // namespace Gateway
