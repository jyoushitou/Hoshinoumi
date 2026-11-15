/// @file        backend.cpp
/// @brief       后端客户端：HTTP/JSON（回滚）或 8+4+body TCP/protobuf（v26）
/// @author      jyoushitou
/// @date        2026-11-13
/// @copyright   Copyright (c) 2026

#include "backend.h"

#include "NetHttpClient.h"

#include <boost/asio/buffer.hpp>
#include <boost/asio/connect.hpp>
#include <boost/asio/io_context.hpp>
#include <boost/asio/ip/tcp.hpp>
#include <boost/asio/read.hpp>
#include <boost/asio/write.hpp>

#include <array>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <map>
#include <string>
#include <utility>
#include <vector>

namespace Gateway
{
    namespace
    {
        constexpr std::size_t MAX_BODY = 8 * 1024 * 1024;

        void PutVarint(std::string& out, std::uint64_t value)
        {
            while (true)
            {
                const auto b = static_cast<unsigned char>(value & 0x7F);
                value >>= 7;
                if (value != 0)
                {
                    out.push_back(static_cast<char>(b | 0x80));
                }
                else
                {
                    out.push_back(static_cast<char>(b));
                    return;
                }
            }
        }

        bool ReadVarint(const std::string& data, std::size_t& pos, std::uint64_t& value)
        {
            value = 0;
            int shift = 0;
            while (pos < data.size() && shift <= 63)
            {
                const auto b = static_cast<unsigned char>(data[pos++]);
                value |= static_cast<std::uint64_t>(b & 0x7F) << shift;
                if ((b & 0x80) == 0)
                {
                    return true;
                }
                shift += 7;
            }
            return false;
        }

        void PutStr(std::string& out, int field, const std::string& value)
        {
            PutVarint(out, static_cast<std::uint64_t>((field << 3) | 2));
            PutVarint(out, value.size());
            out.append(value);
        }

        void PutBytes(std::string& out, int field, const std::string& value)
        {
            PutStr(out, field, value);
        }

        struct Fields
        {
            std::map<int, std::string> strings;
            std::map<int, std::uint64_t> ints;
        };

        bool DecodeFields(const std::string& data, Fields& fields)
        {
            std::size_t pos = 0;
            while (pos < data.size())
            {
                std::uint64_t tag = 0;
                if (!ReadVarint(data, pos, tag))
                {
                    return false;
                }
                const int field = static_cast<int>(tag >> 3);
                const int wire = static_cast<int>(tag & 7);
                if (wire == 0)
                {
                    std::uint64_t v = 0;
                    if (!ReadVarint(data, pos, v))
                    {
                        return false;
                    }
                    fields.ints[field] = v;
                }
                else if (wire == 2)
                {
                    std::uint64_t len = 0;
                    if (!ReadVarint(data, pos, len) || len > data.size() - pos)
                    {
                        return false;
                    }
                    fields.strings[field] = data.substr(pos, static_cast<std::size_t>(len));
                    pos += static_cast<std::size_t>(len);
                }
                else if (wire == 1)
                {
                    if (pos + 8 > data.size()) return false;
                    pos += 8;
                }
                else if (wire == 5)
                {
                    if (pos + 4 > data.size()) return false;
                    pos += 4;
                }
                else
                {
                    return false;
                }
            }
            return true;
        }

        std::string NextRequestId()
        {
            static std::atomic<std::uint64_t> counter{0};
            const auto now = std::chrono::steady_clock::now().time_since_epoch();
            const auto us = std::chrono::duration_cast<std::chrono::microseconds>(now).count();
            return "gw-" + std::to_string(us) + "-" + std::to_string(counter.fetch_add(1));
        }

        std::string StringValue(const std::string& json)
        {
            std::string out;
            PutStr(out, 1, json);
            return out;
        }
    } // namespace

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
        if (cfg_.backendProtocol != "tcp")
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
                req.headers.emplace_back("X-User-Id", owner);
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

        Result result;
        try
        {
            std::string methodPath = path;
            if (methodPath == "/api/health")
            {
                methodPath = "/internal/health";
            }
            const std::string rid = NextRequestId();
            const std::string payload = StringValue(body.empty() ? "{}" : body);
            std::string reqBody;
            PutStr(reqBody, 1, rid);
            PutStr(reqBody, 2, methodPath);
            PutStr(reqBody, 3, owner);
            PutStr(reqBody, 4, "");
            PutBytes(reqBody, 5, payload);

            std::array<unsigned char, 12> header{};
            header[0] = 'N'; header[1] = 'A'; header[2] = 'O'; header[3] = '1';
            header[4] = 1; // version
            header[5] = 1; // request
            const auto len = static_cast<std::uint32_t>(reqBody.size());
            header[8] = static_cast<unsigned char>((len >> 24) & 0xFF);
            header[9] = static_cast<unsigned char>((len >> 16) & 0xFF);
            header[10] = static_cast<unsigned char>((len >> 8) & 0xFF);
            header[11] = static_cast<unsigned char>(len & 0xFF);

            boost::asio::io_context io;
            boost::asio::ip::tcp::socket socket(io);
            boost::asio::ip::tcp::resolver resolver(io);
            const auto endpoints = resolver.resolve(cfg_.backendTcpHost,
                                                    std::to_string(cfg_.backendTcpPort));
            boost::asio::connect(socket, endpoints);
            std::vector<boost::asio::const_buffer> out;
            out.emplace_back(boost::asio::buffer(header));
            out.emplace_back(boost::asio::buffer(reqBody));
            boost::asio::write(socket, out);

            std::array<unsigned char, 12> rh{};
            boost::asio::read(socket, boost::asio::buffer(rh));
            if (rh[0] != 'N' || rh[1] != 'A' || rh[2] != 'O' || rh[3] != '1' || rh[4] != 1)
            {
                result.error = "bad frame header";
                return result;
            }
            const std::uint32_t rlen = (static_cast<std::uint32_t>(rh[8]) << 24) |
                                       (static_cast<std::uint32_t>(rh[9]) << 16) |
                                       (static_cast<std::uint32_t>(rh[10]) << 8) |
                                       static_cast<std::uint32_t>(rh[11]);
            if (rlen > MAX_BODY)
            {
                result.error = "frame too large";
                return result;
            }
            std::string respBody(rlen, '\0');
            if (rlen > 0)
            {
                boost::asio::read(socket, boost::asio::buffer(respBody.data(), rlen));
            }
            Fields fields;
            if (!DecodeFields(respBody, fields))
            {
                result.error = "bad protobuf response";
                return result;
            }
            result.status = static_cast<unsigned>(fields.ints.count(2) ? fields.ints.at(2) : 200);
            result.error = fields.strings.count(3) ? fields.strings.at(3) : "";
            if (fields.strings.count(4))
            {
                Fields payloadFields;
                if (DecodeFields(fields.strings.at(4), payloadFields) &&
                    payloadFields.strings.count(1))
                {
                    result.body = payloadFields.strings.at(1);
                }
            }
            result.ok = result.status >= 200 && result.status < 300;
            if (!result.ok && result.error.empty())
            {
                result.error = "backend status=" + std::to_string(result.status);
            }
        }
        catch (const std::exception& e)
        {
            result.error = std::string("tcp backend failed: ") + e.what();
        }
        return result;
    }
} // namespace Gateway
