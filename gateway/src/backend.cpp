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
        boost::asio::io_context io;
        Net::Client::Http::HttpClient client(io);

        Net::Client::Http::Request req;
        req.method = "GET";
        req.url = cfg_.backendBase + "/api/health";
        req.timeoutMs = cfg_.backendTimeoutMs;

        boost::system::error_code ec;
        const Net::Client::Http::Response resp = client.Send(req, ec);
        if (ec)
        {
            detail = "backend health failed: " + ec.message();
            return false;
        }
        if (resp.status < 200 || resp.status >= 300)
        {
            detail = "backend health status=" + std::to_string(resp.status);
            return false;
        }
        detail = "backend ok";
        return true;
    }
} // namespace Gateway
