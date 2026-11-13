/// @file        auth.cpp
/// @brief       HS256 JWT 签发与校验
/// @author      jyoushitou
/// @date        2026-11-13
/// @copyright   Copyright (c) 2026

#include "auth.h"

#include <boost/json.hpp>

#include <openssl/crypto.h>
#include <openssl/evp.h>
#include <openssl/hmac.h>

#include <algorithm>
#include <cctype>
#include <ctime>
#include <stdexcept>
#include <vector>

namespace Gateway
{
    namespace
    {
        constexpr char kBase64Url[] =
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";

        std::string Base64UrlEncode(const unsigned char* data, std::size_t len)
        {
            std::string out;
            out.reserve((len + 2) / 3 * 4);
            for (std::size_t i = 0; i < len; i += 3)
            {
                const unsigned int b0 = data[i];
                const unsigned int b1 = (i + 1 < len) ? data[i + 1] : 0;
                const unsigned int b2 = (i + 2 < len) ? data[i + 2] : 0;
                out.push_back(kBase64Url[b0 >> 2]);
                out.push_back(kBase64Url[((b0 & 0x03) << 4) | (b1 >> 4)]);
                if (i + 1 < len)
                {
                    out.push_back(kBase64Url[((b1 & 0x0F) << 2) | (b2 >> 6)]);
                }
                if (i + 2 < len)
                {
                    out.push_back(kBase64Url[b2 & 0x3F]);
                }
            }
            return out;
        }

        std::string Base64UrlEncode(const std::string& text)
        {
            return Base64UrlEncode(reinterpret_cast<const unsigned char*>(text.data()), text.size());
        }

        int Base64UrlValue(char c)
        {
            if (c >= 'A' && c <= 'Z') return c - 'A';
            if (c >= 'a' && c <= 'z') return c - 'a' + 26;
            if (c >= '0' && c <= '9') return c - '0' + 52;
            if (c == '-') return 62;
            if (c == '_') return 63;
            return -1;
        }

        std::string Base64UrlDecode(const std::string& text)
        {
            std::string out;
            int val = 0;
            int bits = -8;
            for (char c : text)
            {
                const int d = Base64UrlValue(c);
                if (d < 0) return {};
                val = (val << 6) | d;
                bits += 6;
                if (bits >= 0)
                {
                    out.push_back(static_cast<char>((val >> bits) & 0xFF));
                    bits -= 8;
                }
            }
            return out;
        }

        std::string HmacSha256(const std::string& key, const std::string& data)
        {
            unsigned char digest[EVP_MAX_MD_SIZE];
            unsigned int len = 0;
            if (HMAC(EVP_sha256(), key.data(), static_cast<int>(key.size()),
                     reinterpret_cast<const unsigned char*>(data.data()), data.size(),
                     digest, &len) == nullptr)
            {
                throw std::runtime_error("HMAC-SHA256 失败");
            }
            return std::string(reinterpret_cast<char*>(digest), len);
        }

        std::string Header()
        {
            return R"({"alg":"HS256","typ":"JWT"})";
        }
    } // namespace

    Auth::Auth(Config cfg) : cfg_(std::move(cfg))
    {
    }

    bool Auth::CheckSecret(const std::string& secret) const
    {
        if (cfg_.ownerSecret.empty() || secret.size() != cfg_.ownerSecret.size())
        {
            return false;
        }
        return CRYPTO_memcmp(secret.data(), cfg_.ownerSecret.data(), secret.size()) == 0;
    }

    std::string Auth::Issue(const std::string& type, int ttlSec) const
    {
        if (cfg_.ownerSecret.empty())
        {
            throw std::runtime_error("owner_secret 未配置");
        }
        boost::json::object payload;
        payload["sub"] = "owner";
        payload["role"] = "owner";
        payload["type"] = type;
        payload["iat"] = static_cast<std::int64_t>(std::time(nullptr));
        payload["exp"] = static_cast<std::int64_t>(std::time(nullptr)) + ttlSec;

        const std::string head = Base64UrlEncode(Header());
        const std::string body = Base64UrlEncode(boost::json::serialize(payload));
        const std::string signing = head + "." + body;
        const std::string sig = Base64UrlEncode(HmacSha256(cfg_.ownerSecret, signing));
        return signing + "." + sig;
    }

    std::string Auth::IssueAccess() const
    {
        return Issue("access", cfg_.accessTtlSec);
    }

    std::string Auth::IssueRefresh() const
    {
        return Issue("refresh", cfg_.refreshTtlSec);
    }

    bool Auth::Verify(const std::string& token, const std::string& type, Claims& claims) const
    {
        if (cfg_.ownerSecret.empty() || token.empty())
        {
            return false;
        }
        const auto p1 = token.find('.');
        const auto p2 = token.find('.', p1 == std::string::npos ? p1 : p1 + 1);
        if (p1 == std::string::npos || p2 == std::string::npos)
        {
            return false;
        }
        const std::string head = token.substr(0, p1);
        const std::string body = token.substr(p1 + 1, p2 - p1 - 1);
        const std::string sig = token.substr(p2 + 1);
        const std::string expect = HmacSha256(cfg_.ownerSecret, head + "." + body);
        const std::string actual = Base64UrlDecode(sig);
        if (actual.size() != expect.size() ||
            CRYPTO_memcmp(actual.data(), expect.data(), actual.size()) != 0)
        {
            return false;
        }

        try
        {
            const auto parsed = boost::json::parse(Base64UrlDecode(body));
            if (!parsed.is_object())
            {
                return false;
            }
            const auto& obj = parsed.as_object();
            claims.sub = std::string(obj.at("sub").as_string());
            claims.role = std::string(obj.at("role").as_string());
            claims.type = std::string(obj.at("type").as_string());
            claims.exp = obj.at("exp").as_int64();
        }
        catch (const std::exception&)
        {
            return false;
        }
        if (claims.type != type || claims.sub != "owner" || claims.role != "owner")
        {
            return false;
        }
        return claims.exp > static_cast<std::int64_t>(std::time(nullptr));
    }

    std::string Auth::Bearer(const std::string& headers)
    {
        std::string lower = headers;
        std::transform(lower.begin(), lower.end(), lower.begin(),
                       [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
        const std::string key = "authorization:";
        auto pos = lower.find(key);
        while (pos != std::string::npos)
        {
            auto end = headers.find("\r\n", pos);
            std::string line = headers.substr(pos + key.size(),
                                              end == std::string::npos ? std::string::npos
                                                                       : end - pos - key.size());
            auto first = line.find_first_not_of(" \t");
            if (first != std::string::npos)
            {
                line = line.substr(first);
                if (line.rfind("Bearer ", 0) == 0)
                {
                    return line.substr(7);
                }
                if (line.rfind("bearer ", 0) == 0)
                {
                    return line.substr(7);
                }
            }
            pos = lower.find(key, pos + key.size());
        }
        return {};
    }
} // namespace Gateway
