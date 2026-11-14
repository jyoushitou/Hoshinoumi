/// @file        router.cpp
/// @brief       网关路由实现
/// @author      jyoushitou
/// @date        2026-11-13
/// @copyright   Copyright (c) 2026

#include "router.h"

#include "Utils.h"

#include <boost/json.hpp>

#include <chrono>
#include <stdexcept>
#include <thread>
#include <utility>

namespace Gateway
{
    std::atomic<unsigned long long> Router::requestSeq_{0};

    namespace
    {
        Net::Server::HttpServer::ResponseHeaders JsonHeaders(const std::string& requestId)
        {
            return {
                {"Content-Type", "application/json; charset=utf-8"},
                {"X-Request-Id", requestId},
                {"X-Gateway", "hoshinoumi-gateway/22.0.0"},
            };
        }
    } // namespace

    Router::Router(Config cfg)
        : cfg_(std::move(cfg)), auth_(cfg_), backend_(cfg_), probe_(std::make_shared<ProbeState>())
    {
        if (cfg_.startupWait)
        {
            StartProbe(true);  // 立即第 1 次；失败后 30s × 5
        }
    }

    std::string Router::NextRequestId()
    {
        return "gw-" + std::to_string(++requestSeq_);
    }

    void Router::Handle(const std::shared_ptr<Net::Server::HttpServer::HttpSession>& session,
                        const Net::Server::HttpServer::Url& url)
    {
        const auto started = std::chrono::steady_clock::now();
        auto cost_ms = [&started]()
        {
            return std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::steady_clock::now() - started).count();
        };

        if (url.target.rfind("/api/", 0) == 0)
        {
            const std::string ip = url.requestIP.empty() ? "0.0.0.0" : url.requestIP;
            if (!limiter_.Allow(ip))
            {
                const std::string rid = NextRequestId();
                Audit("", url.target, 429, cost_ms(), ip, rid);
                auto headers = JsonHeaders(rid);
                headers.emplace_back("X-RateLimit-Limit", "60");
                headers.emplace_back("X-RateLimit-Remaining", "0");
                headers.emplace_back("Retry-After", "1");
                session->httpReplay("{\"ok\":false,\"error\":\"rate_limited\"}",
                                    boost::beast::http::status::too_many_requests,
                                    headers);
                return;
            }
        }

        if (url.target == "/healthz")
        {
            Health(session, url);
            return;
        }
        if (url.target == "/readyz")
        {
            Ready(session, url);
            return;
        }
        if (url.target == "/api/login")
        {
            Login(session, url);
            return;
        }
        if (url.target == "/api/register")
        {
            Register(session, url);
            return;
        }
        if (url.target == "/api/refresh")
        {
            Refresh(session, url);
            return;
        }

        Claims claims;
        if (url.target.rfind("/api/", 0) == 0 && !Authenticate(url, claims))
        {
            const std::string rid = NextRequestId();
            Audit("", url.target, 401, cost_ms(),
                  url.requestIP.empty() ? "0.0.0.0" : url.requestIP, rid);
            session->httpReplay(R"({"ok":false,"error":"unauthorized"})",
                                boost::beast::http::status::unauthorized,
                                JsonHeaders(rid));
            return;
        }
        const std::string owner = claims.sub;

        if (url.target.rfind("/api/chat", 0) == 0)
        {
            Proxy(session, url, "/internal/chat", "POST", owner);
            return;
        }
        if (url.target.rfind("/api/history", 0) == 0)
        {
            Proxy(session, url, "/internal/history", "GET", owner);
            return;
        }
        if (url.target.rfind("/api/state", 0) == 0)
        {
            Proxy(session, url, "/internal/state", "GET", owner);
            return;
        }
        if (url.target.rfind("/api/cron", 0) == 0)
        {
            Proxy(session, url, "/internal/cron", "GET", owner);
            return;
        }
        if (url.target.rfind("/api/diary", 0) == 0)
        {
            Proxy(session, url, "/internal/diary", "GET", owner);
            return;
        }
        if (url.target.rfind("/api/shelf", 0) == 0)
        {
            Proxy(session, url, "/internal/shelf", "GET", owner);
            return;
        }
        NotFound(session, url);
    }

    void Router::Health(const std::shared_ptr<Net::Server::HttpServer::HttpSession>& session,
                        const Net::Server::HttpServer::Url& url)
    {
        if (url.method != "GET")
        {
            session->httpReplay("{\"ok\":false,\"error\":\"method_not_allowed\"}",
                                boost::beast::http::status::method_not_allowed,
                                JsonHeaders(NextRequestId()));
            return;
        }
        boost::json::object body;
        body["ok"] = true;
        body["service"] = "hoshinoumi-gateway";
        body["version"] = "22.0.0";
        session->httpReplay(boost::json::serialize(body),
                            boost::beast::http::status::ok,
                            JsonHeaders(NextRequestId()));
    }

    void Router::StartProbe(bool fullCycle)
    {
        if (probe_->running.exchange(true))
        {
            return;  // 已有探测在跑，别叠加线程
        }

        const int maxAttempts = fullCycle ? cfg_.startupMaxAttempts : 1;
        const int intervalSec = cfg_.startupRetryIntervalSec;
        auto probe = probe_;
        BackendClient backend = backend_;
        std::thread([probe, backend, maxAttempts, intervalSec, fullCycle]()
                    {
                        for (int attempt = 1; attempt <= maxAttempts; ++attempt)
                        {
                            std::string detail;
                            const bool ok = backend.CheckHealth(detail);
                            if (ok)
                            {
                                probe->ready = true;
                                Utils::Out::outMsg("[网关] 后端探测成功，/readyz 可用");
                                break;
                            }
                            Utils::Out::outErr("[网关] 后端探测 " + std::to_string(attempt) +
                                               "/" + std::to_string(maxAttempts) +
                                               " 失败: " + detail);
                            if (attempt < maxAttempts)
                            {
                                std::this_thread::sleep_for(
                                    std::chrono::seconds(intervalSec));
                            }
                        }
                        if (!probe->ready.load())
                        {
                            probe->ready = false;
                            if (fullCycle)
                            {
                                Utils::Out::outErr("[网关] 启动等待结束，后端仍未就绪；"
                                                   "网关保持运行，/readyz 返回 503");
                            }
                        }
                        probe->running = false;
                    })
            .detach();
    }

    void Router::Ready(const std::shared_ptr<Net::Server::HttpServer::HttpSession>& session,
                       const Net::Server::HttpServer::Url& url)
    {
        if (url.method != "GET")
        {
            session->httpReplay("{\"ok\":false,\"error\":\"method_not_allowed\"}",
                                boost::beast::http::status::method_not_allowed,
                                JsonHeaders(NextRequestId()));
            return;
        }

        // v20.6：启动等待期间不阻塞 IO 线程，先回 503；后续请求再触发一次探测
        if (cfg_.startupWait && !probe_->ready.load())
        {
            StartProbe(false);
            boost::json::object body;
            body["ok"] = false;
            body["backend"] = probe_->running.load() ? "starting" : "not_ready";
            session->httpReplay(boost::json::serialize(body),
                                boost::beast::http::status::service_unavailable,
                                JsonHeaders(NextRequestId()));
            return;
        }

        const auto seq = url.seq;
        const std::string requestId = NextRequestId();
        BackendClient backend = backend_;
        auto probe = probe_;
        std::thread([session, seq, backend, requestId, probe]()
                    {
                        std::string detail;
                        const bool ok = backend.CheckHealth(detail);
                        probe->ready = ok;
                        boost::json::object body;
                        body["ok"] = ok;
                        body["backend"] = detail;
                        const auto status = ok ? boost::beast::http::status::ok
                                               : boost::beast::http::status::service_unavailable;
                        session->httpAsyncReplay(seq, boost::json::serialize(body), status,
                                                 JsonHeaders(requestId));
                    })
            .detach();
    }

    void Router::Audit(const std::string& owner, const std::string& path, int status,
                       long long costMs, const std::string& ip, const std::string& requestId)
    {
        BackendClient backend = backend_;
        std::thread([backend, owner, path, status, costMs, ip, requestId]()
                    {
                        boost::json::object body;
                        body["owner"] = owner;
                        body["path"] = path;
                        body["status"] = status;
                        body["cost_ms"] = costMs;
                        body["ip"] = ip;
                        body["request_id"] = requestId;
                        backend.Request("POST", "/internal/audit", boost::json::serialize(body), "");
                    })
            .detach();
    }

    void Router::Register(const std::shared_ptr<Net::Server::HttpServer::HttpSession>& session,
                          const Net::Server::HttpServer::Url& url)
    {
        if (url.method != "POST")
        {
            session->httpReplay("{\"ok\":false,\"error\":\"method_not_allowed\"}",
                                boost::beast::http::status::method_not_allowed,
                                JsonHeaders(NextRequestId()));
            return;
        }
        const auto result = backend_.Request("POST", "/internal/auth/register", url.body, "");
        const std::string rid = NextRequestId();
        Audit("", url.target, result.ok ? 200 : (result.status ? result.status : 503),
              0, url.requestIP.empty() ? "0.0.0.0" : url.requestIP, rid);
        if (result.ok)
        {
            session->httpReplay(result.body, boost::beast::http::status::ok, JsonHeaders(rid));
        }
        else
        {
            session->httpReplay(result.body.empty()
                                    ? "{\"ok\":false,\"error\":\"register_failed\"}"
                                    : result.body,
                                result.status >= 400 && result.status < 600
                                    ? static_cast<boost::beast::http::status>(result.status)
                                    : boost::beast::http::status::service_unavailable,
                                JsonHeaders(rid));
        }
    }

    void Router::Login(const std::shared_ptr<Net::Server::HttpServer::HttpSession>& session,
                       const Net::Server::HttpServer::Url& url)
    {
        if (url.method != "POST")
        {
            session->httpReplay("{\"ok\":false,\"error\":\"method_not_allowed\"}",
                                boost::beast::http::status::method_not_allowed,
                                JsonHeaders(NextRequestId()));
            return;
        }
        if (cfg_.ownerSecret.empty())
        {
            session->httpReplay("{\"ok\":false,\"error\":\"owner_secret_not_configured\"}",
                                boost::beast::http::status::service_unavailable,
                                JsonHeaders(NextRequestId()));
            return;
        }

        const std::string ip = url.requestIP.empty() ? "0.0.0.0" : url.requestIP;
        {
            std::lock_guard<std::mutex> lock(loginMutex_);
            const auto it = loginStates_.find(ip);
            const auto now = std::chrono::steady_clock::now();
            if (it != loginStates_.end() && it->second.lockedUntil > now)
            {
                const auto retry = std::chrono::duration_cast<std::chrono::seconds>(
                    it->second.lockedUntil - now).count();
                boost::json::object body;
                body["ok"] = false;
                body["error"] = "too_many_attempts";
                body["retry_after"] = retry;
                session->httpReplay(boost::json::serialize(body),
                                    boost::beast::http::status::too_many_requests,
                                    JsonHeaders(NextRequestId()));
                return;
            }
        }

        std::string secret;
        std::string userId;
        std::string password;
        try
        {
            const auto parsed = boost::json::parse(url.body);
            if (!parsed.is_object())
            {
                throw std::runtime_error("body");
            }
            const auto& obj = parsed.as_object();
            if (obj.contains("secret"))
            {
                secret = std::string(obj.at("secret").as_string());
            }
            if (obj.contains("user_id"))
            {
                userId = std::string(obj.at("user_id").as_string());
            }
            if (obj.contains("password"))
            {
                password = std::string(obj.at("password").as_string());
            }
        }
        catch (const std::exception&)
        {
            session->httpReplay("{\"ok\":false,\"error\":\"invalid_json\"}",
                                boost::beast::http::status::bad_request,
                                JsonHeaders(NextRequestId()));
            return;
        }

        if (!userId.empty())
        {
            boost::json::object req;
            req["user_id"] = userId;
            req["password"] = password;
            const auto result = backend_.Request("POST", "/internal/auth/verify",
                                                 boost::json::serialize(req), "");
            if (!result.ok)
            {
                Audit("", url.target, 401, 0, ip, NextRequestId());
                session->httpReplay("{\"ok\":false,\"error\":\"invalid_credentials\"}",
                                    boost::beast::http::status::unauthorized,
                                    JsonHeaders(NextRequestId()));
                return;
            }
            try
            {
                const auto parsed = boost::json::parse(result.body);
                const auto& data = parsed.as_object().at("data").as_object();
                const std::string sub = std::string(data.at("user_id").as_string());
                const std::string role = std::string(data.at("role").as_string());
                boost::json::object tokens;
                tokens["access"] = auth_.IssueAccess(sub, role);
                tokens["refresh"] = auth_.IssueRefresh(sub, role);
                tokens["token_type"] = "Bearer";
                tokens["expires_in"] = auth_.AccessTtl();
                tokens["user_id"] = sub;
                tokens["role"] = role;
                boost::json::object body;
                body["ok"] = true;
                body["data"] = tokens;
                Audit(sub, url.target, 200, 0, ip, NextRequestId());
                session->httpReplay(boost::json::serialize(body),
                                    boost::beast::http::status::ok,
                                    JsonHeaders(NextRequestId()));
                return;
            }
            catch (const std::exception&)
            {
                session->httpReplay("{\"ok\":false,\"error\":\"auth_failed\"}",
                                    boost::beast::http::status::bad_gateway,
                                    JsonHeaders(NextRequestId()));
                return;
            }
        }

        if (!auth_.CheckSecret(secret))
        {
            bool locked = false;
            {
                std::lock_guard<std::mutex> lock(loginMutex_);
                auto& st = loginStates_[ip];
                ++st.failures;
                if (st.failures >= 3)
                {
                    st.lockedUntil = std::chrono::steady_clock::now() +
                                     std::chrono::minutes(5);
                    locked = true;
                }
            }
            if (locked)
            {
                Utils::Out::outErr("[网关] 登录失败 3 次，IP " + ip + " 锁定 5 分钟");
            }
            Audit("", url.target, 401, 0, ip, NextRequestId());
            session->httpReplay("{\"ok\":false,\"error\":\"invalid_secret\"}",
                                boost::beast::http::status::unauthorized,
                                JsonHeaders(NextRequestId()));
            return;
        }

        {
            std::lock_guard<std::mutex> lock(loginMutex_);
            loginStates_.erase(ip);
        }

        try
        {
            boost::json::object data;
            data["access"] = auth_.IssueAccess("__owner__", "owner");
            data["refresh"] = auth_.IssueRefresh("__owner__", "owner");
            data["token_type"] = "Bearer";
            data["expires_in"] = auth_.AccessTtl();
            data["user_id"] = "__owner__";
            data["role"] = "owner";
            boost::json::object body;
            body["ok"] = true;
            body["data"] = data;
            Audit("__owner__", url.target, 200, 0, ip, NextRequestId());
            session->httpReplay(boost::json::serialize(body),
                                boost::beast::http::status::ok,
                                JsonHeaders(NextRequestId()));
        }
        catch (const std::exception& e)
        {
            Utils::Out::outErr(std::string("[网关] 签发 token 失败: ") + e.what());
            session->httpReplay("{\"ok\":false,\"error\":\"token_issue_failed\"}",
                                boost::beast::http::status::internal_server_error,
                                JsonHeaders(NextRequestId()));
        }
    }

    void Router::Refresh(const std::shared_ptr<Net::Server::HttpServer::HttpSession>& session,
                         const Net::Server::HttpServer::Url& url)
    {
        if (url.method != "POST")
        {
            session->httpReplay("{\"ok\":false,\"error\":\"method_not_allowed\"}",
                                boost::beast::http::status::method_not_allowed,
                                JsonHeaders(NextRequestId()));
            return;
        }

        std::string token = Auth::Bearer(url.headers);
        if (token.empty())
        {
            try
            {
                const auto parsed = boost::json::parse(url.body);
                if (parsed.is_object())
                {
                    token = std::string(parsed.as_object().at("refresh").as_string());
                }
            }
            catch (const std::exception&)
            {
            }
        }

        Claims claims;
        if (!auth_.Verify(token, "refresh", claims))
        {
            Audit("", url.target, 401, 0,
                  url.requestIP.empty() ? "0.0.0.0" : url.requestIP, NextRequestId());
            session->httpReplay("{\"ok\":false,\"error\":\"invalid_refresh\"}",
                                boost::beast::http::status::unauthorized,
                                JsonHeaders(NextRequestId()));
            return;
        }

        try
        {
            boost::json::object data;
            data["access"] = auth_.IssueAccess(claims.sub, claims.role);
            data["refresh"] = auth_.IssueRefresh(claims.sub, claims.role);
            data["token_type"] = "Bearer";
            data["expires_in"] = auth_.AccessTtl();
            data["user_id"] = claims.sub;
            data["role"] = claims.role;
            boost::json::object body;
            body["ok"] = true;
            body["data"] = data;
            Audit(claims.sub, url.target, 200, 0,
                  url.requestIP.empty() ? "0.0.0.0" : url.requestIP, NextRequestId());
            session->httpReplay(boost::json::serialize(body),
                                boost::beast::http::status::ok,
                                JsonHeaders(NextRequestId()));
        }
        catch (const std::exception& e)
        {
            Utils::Out::outErr(std::string("[网关] 刷新 token 失败: ") + e.what());
            session->httpReplay("{\"ok\":false,\"error\":\"token_issue_failed\"}",
                                boost::beast::http::status::internal_server_error,
                                JsonHeaders(NextRequestId()));
        }
    }

    bool Router::Authenticate(const Net::Server::HttpServer::Url& url, Claims& claims)
    {
        const std::string token = Auth::Bearer(url.headers);
        return auth_.Verify(token, "access", claims);
    }

    void Router::Proxy(const std::shared_ptr<Net::Server::HttpServer::HttpSession>& session,
                       const Net::Server::HttpServer::Url& url,
                       const std::string& backendPath, const std::string& method,
                       const std::string& owner)
    {
        if (url.method != method)
        {
            session->httpReplay("{\"ok\":false,\"error\":\"method_not_allowed\"}",
                                boost::beast::http::status::method_not_allowed,
                                JsonHeaders(NextRequestId()));
            return;
        }

        std::string path = backendPath;
        const auto query = url.target.find('?');
        if (query != std::string::npos)
        {
            path += url.target.substr(query);  // query 原样带过去，path 部分由路由决定
        }

        const auto seq = url.seq;
        const std::string requestId = NextRequestId();
        const std::string body = url.body;
        const std::string ip = url.requestIP.empty() ? "0.0.0.0" : url.requestIP;
        const std::string clientPath = url.target;
        const auto started = std::chrono::steady_clock::now();
        BackendClient backend = backend_;
        std::thread([session, seq, backend, path, method, body, owner, requestId, ip, started, clientPath]()
                    {
                        const auto result = backend.Request(method, path, body, owner);
                        boost::json::object out;
                        boost::beast::http::status status = boost::beast::http::status::ok;
                        auto audit = [&](int code)
                        {
                            boost::json::object entry;
                            entry["owner"] = owner;
                            entry["path"] = clientPath;
                            entry["status"] = code;
                            entry["cost_ms"] = std::chrono::duration_cast<std::chrono::milliseconds>(
                                std::chrono::steady_clock::now() - started).count();
                            entry["ip"] = ip;
                            entry["request_id"] = requestId;
                            backend.Request("POST", "/internal/audit",
                                            boost::json::serialize(entry), "");
                        };
                        if (result.ok)
                        {
                            try
                            {
                                const auto parsed = boost::json::parse(result.body);
                                if (parsed.is_object() && parsed.as_object().contains("ok"))
                                {
                                    audit(200);
                                    session->httpAsyncReplay(seq, result.body, status,
                                                             JsonHeaders(requestId));
                                    return;
                                }
                                out["ok"] = true;
                                out["data"] = parsed;
                            }
                            catch (const std::exception&)
                            {
                                out["ok"] = true;
                                out["data"] = result.body;
                            }
                        }
                        else
                        {
                            out["ok"] = false;
                            out["error"] = result.error;
                            if (result.status == 0)
                            {
                                status = boost::beast::http::status::service_unavailable;
                            }
                            else
                            {
                                status = (result.status >= 400 && result.status < 600)
                                             ? static_cast<boost::beast::http::status>(result.status)
                                             : boost::beast::http::status::bad_gateway;
                            }
                        }
                        audit(static_cast<int>(status));
                        session->httpAsyncReplay(seq, boost::json::serialize(out), status,
                                                 JsonHeaders(requestId));
                    })
            .detach();
    }

    void Router::NotFound(const std::shared_ptr<Net::Server::HttpServer::HttpSession>& session,
                          const Net::Server::HttpServer::Url& url)
    {
        boost::json::object body;
        body["ok"] = false;
        body["error"] = "not_found";
        body["path"] = url.target;
        session->httpReplay(boost::json::serialize(body),
                            boost::beast::http::status::not_found,
                            JsonHeaders(NextRequestId()));
    }
} // namespace Gateway


