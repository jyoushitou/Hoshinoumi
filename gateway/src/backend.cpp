/// @file        backend.cpp
/// @brief       后端 API 探活
/// @author      jyoushitou
/// @date        2026-11-13
/// @copyright   Copyright (c) 2026

#include "backend.h"

#include "NetHttpClient.h"

#include <boost/asio/io_context.hpp>

#include <utility>

namespace Gateway
{
    BackendClient::BackendClient(Config cfg) : cfg_(std::move(cfg))
    {
    }

    bool BackendClient::CheckHealth(std::string& detail) const
    {
        const Result result = Request("GET", "/api/health", "");
        if (!result.ok)
        {
            detail = result.error;
            return false;
        }
        detail = "backend ok";
        return true;
    }

    BackendClient::Result BackendClient::Request(const std::string& method,
                                                 const std::string& path,
                                                 const std::string& body,
                                                 const std::string& owner) const
    {
        boost::asio::io_context io;
        Net::Client::Http::HttpClient client(io);

        Net::Client::Http::Request req;
        req.method = method;
        req.url = cfg_.backendBase + path;
        req.body = body;
        req.timeoutMs = cfg_.backendTimeoutMs;
        if (!body.empty())
        {
            req.headers.emplace_back("Content-Type", "application/json");
        }
        if (!owner.empty())
        {
            req.headers.emplace_back("X-Owner-Id", owner);
        }

        boost::system::error_code ec;
        const Net::Client::Http::Response resp = client.Send(req, ec);
        Result result;
        if (ec)
        {
            result.error = "backend request failed: " + ec.message();
            return result;
        }
        result.status = resp.status;
        result.body = resp.body;
        result.ok = resp.status >= 200 && resp.status < 300;
        if (!result.ok)
        {
            result.error = "backend status=" + std::to_string(resp.status);
        }
        return result;
    }
} // namespace Gateway
