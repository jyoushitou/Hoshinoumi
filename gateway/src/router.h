/// @file        router.h
/// @brief       网关路由（v20.0 先接 healthz / readyz）
/// @author      jyoushitou
/// @date        2026-11-13
/// @copyright   Copyright (c) 2026
#pragma once

#include "auth.h"
#include "backend.h"
#include "config.h"
#include "rate_limit.h"

#include "NetHttpServer.h"

#include <atomic>
#include <chrono>
#include <memory>
#include <mutex>
#include <string>
#include <unordered_map>

namespace Gateway
{
    /// @brief 极简路由
    /// @details 路由回调在 CommonNet 的 IO 线程执行，禁止阻塞；
    ///          readyz 的后端探活会丢到工作线程，再用 httpAsyncReplay 回包。
    class Router
    {
    public:
        explicit Router(Config cfg);

        /// @brief 启动时的后端等待状态（v20.6）
        struct ProbeState
        {
            std::atomic<bool> ready{false};
            std::atomic<bool> running{false};
        };

        /// @brief CommonNet HTTP 回调入口
        void Handle(const std::shared_ptr<Net::Server::HttpServer::HttpSession>& session,
                    const Net::Server::HttpServer::Url& url);

    private:
        void Health(const std::shared_ptr<Net::Server::HttpServer::HttpSession>& session,
                    const Net::Server::HttpServer::Url& url);
        void Ready(const std::shared_ptr<Net::Server::HttpServer::HttpSession>& session,
                   const Net::Server::HttpServer::Url& url);
        void Login(const std::shared_ptr<Net::Server::HttpServer::HttpSession>& session,
                   const Net::Server::HttpServer::Url& url);
        void Refresh(const std::shared_ptr<Net::Server::HttpServer::HttpSession>& session,
                     const Net::Server::HttpServer::Url& url);
        void StartProbe(bool fullCycle);
        bool Authenticate(const Net::Server::HttpServer::Url& url, Claims& claims);
        void Proxy(const std::shared_ptr<Net::Server::HttpServer::HttpSession>& session,
                   const Net::Server::HttpServer::Url& url,
                   const std::string& backendPath, const std::string& method,
                   const std::string& owner);
        void Audit(const std::string& owner, const std::string& path, int status,
                   long long costMs, const std::string& ip, const std::string& requestId);
        void NotFound(const std::shared_ptr<Net::Server::HttpServer::HttpSession>& session,
                      const Net::Server::HttpServer::Url& url);

        static std::string NextRequestId();

        Config cfg_;
        Auth auth_;
        BackendClient backend_;
        RateLimiter limiter_;
        std::shared_ptr<ProbeState> probe_;

        struct LoginState
        {
            int failures = 0;
            std::chrono::steady_clock::time_point lockedUntil{};
        };
        std::mutex loginMutex_;
        std::unordered_map<std::string, LoginState> loginStates_;

        static std::atomic<unsigned long long> requestSeq_;
    };
} // namespace Gateway
