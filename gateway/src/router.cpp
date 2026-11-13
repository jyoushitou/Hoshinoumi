/// @file        router.cpp
/// @brief       网关路由实现
/// @author      jyoushitou
/// @date        2026-11-13
/// @copyright   Copyright (c) 2026

#include "router.h"

#include <boost/json.hpp>

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

    Router::Router(Config cfg) : cfg_(std::move(cfg)), backend_(cfg_)
    {
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

        const auto seq = url.seq;
        const std::string requestId = NextRequestId();
        BackendClient backend = backend_;
        std::thread([session, seq, backend, requestId]()
                    {
                        std::string detail;
                        const bool ok = backend.CheckHealth(detail);
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
