/// @file        backend.cpp
/// @brief       后端客户端：TCP 8+4+body + typed protobuf InternalRequest/Response
#include "backend.h"

#include "api_contract.h"

#include "NetHttpClient.h"

#include "nao/v1/internal_v2.pb.h"

#include <google/protobuf/util/json_util.h>

#include <boost/asio/buffer.hpp>
#include <boost/asio/connect.hpp>
#include <boost/asio/io_context.hpp>
#include <boost/asio/ip/tcp.hpp>
#include <boost/asio/read.hpp>
#include <boost/asio/write.hpp>

#include <array>
#include <atomic>
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

        std::string NextRequestId()
        {
            static std::atomic<unsigned long long> seq{0};
            return "gw-be-" + std::to_string(++seq);
        }

        std::pair<std::string, std::map<std::string, std::string>> SplitQuery(const std::string& path)
        {
            std::map<std::string, std::string> query;
            const auto pos = path.find('?');
            if (pos == std::string::npos)
            {
                return {path, query};
            }
            const std::string clean = path.substr(0, pos);
            std::string raw = path.substr(pos + 1);
            std::size_t start = 0;
            while (start <= raw.size())
            {
                const auto end = raw.find('&', start);
                const std::string part = raw.substr(start, end == std::string::npos ? std::string::npos : end - start);
                const auto eq = part.find('=');
                if (eq != std::string::npos)
                {
                    query[part.substr(0, eq)] = part.substr(eq + 1);
                }
                else if (!part.empty())
                {
                    query[part] = "";
                }
                if (end == std::string::npos) break;
                start = end + 1;
            }
            return {clean, query};
        }

        bool FillParams(const std::string& body, google::protobuf::Struct& params)
        {
            if (body.empty())
            {
                return true;
            }
            const auto status = google::protobuf::util::JsonStringToMessage(body, &params);
            return status.ok();
        }

        std::string StructToJson(const google::protobuf::Struct& data)
        {
            std::string out;
            google::protobuf::util::JsonPrintOptions options;
            options.add_whitespace = false;
            options.always_print_fields_with_no_presence = false;
            const auto status = google::protobuf::util::MessageToJsonString(data, &out, options);
            return status.ok() ? out : "{}";
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
        Result result;
        const auto split = SplitQuery(path);
        const std::string cleanPath = split.first;

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

        try
        {
            nao::v1::InternalRequest request;
            const std::string rid = NextRequestId();
            request.set_request_id(rid);
            request.set_method(ApiMethodFor(method, cleanPath));
            request.set_path(InternalPathFor(cleanPath));
            request.set_http_method(method);
            request.set_user_id(owner);
            request.set_role("");
            if (!FillParams(body, *request.mutable_params()))
            {
                result.error = "invalid json params";
                return result;
            }
            for (const auto& [key, value] : split.second)
            {
                (*request.mutable_query())[key] = value;
            }

            std::string reqBody;
            if (!request.SerializeToString(&reqBody) || reqBody.size() > MAX_BODY)
            {
                result.error = "protobuf encode failed";
                return result;
            }

            std::array<unsigned char, 12> header{};
            header[0] = 'N'; header[1] = 'A'; header[2] = 'O'; header[3] = '1';
            header[4] = 1;
            header[5] = 1;
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
            nao::v1::InternalResponse response;
            if (!response.ParseFromString(respBody))
            {
                result.error = "bad protobuf response";
                return result;
            }
            result.status = static_cast<unsigned>(response.status());
            result.error = response.error();
            result.body = StructToJson(response.data());
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
