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
                {"X-Gateway", "hoshinoumi-gateway/20.0.0"},
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
        if (url.target == "/api/refresh")
        {
            session->httpReplay(R"({"ok":false,"error":"not_implemented"})",
                                boost::beast::http::status::not_implemented,
                                JsonHeaders(NextRequestId()));
            return;
        }

        Claims claims;
        if (url.target.rfind("/api/", 0) == 0 && !Authenticate(url, claims))
        {
            session->httpReplay(R"({"ok":false,"error":"unauthorized"})",
                                boost::beast::http::status::unauthorized,
                                JsonHeaders(NextRequestId()));
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
        body["version"] = "20.0.0";
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

        std::string secret;
        try
        {
            const auto parsed = boost::json::parse(url.body);
            if (!parsed.is_object())
            {
                throw std::runtime_error("body");
            }
            secret = std::string(parsed.as_object().at("secret").as_string());
        }
        catch (const std::exception&)
        {
            session->httpReplay("{\"ok\":false,\"error\":\"invalid_json\"}",
                                boost::beast::http::status::bad_request,
                                JsonHeaders(NextRequestId()));
            return;
        }

        if (!auth_.CheckSecret(secret))
        {
            session->httpReplay("{\"ok\":false,\"error\":\"invalid_secret\"}",
                                boost::beast::http::status::unauthorized,
                                JsonHeaders(NextRequestId()));
            return;
        }

        try
        {
            boost::json::object data;
            data["access"] = auth_.IssueAccess();
            data["refresh"] = auth_.IssueRefresh();
            data["token_type"] = "Bearer";
            data["expires_in"] = auth_.AccessTtl();
            boost::json::object body;
            body["ok"] = true;
            body["data"] = data;
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
        BackendClient backend = backend_;
        std::thread([session, seq, backend, path, method, body, owner, requestId]()
                    {
                        const auto result = backend.Request(method, path, body, owner);
                        boost::json::object out;
                        boost::beast::http::status status = boost::beast::http::status::ok;
                        if (result.ok)
                        {
                            try
                            {
                                const auto parsed = boost::json::parse(result.body);
                                if (parsed.is_object() && parsed.as_object().contains("ok"))
                                {
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
                            status = (result.status >= 400 && result.status < 600)
                                         ? static_cast<boost::beast::http::status>(result.status)
                                         : boost::beast::http::status::bad_gateway;
                        }
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
