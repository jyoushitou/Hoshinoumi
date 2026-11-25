/// @file        api_contract.cpp
/// @brief       公开 API → typed ApiMethod + /internal/* 契约
#include "api_contract.h"

namespace Gateway
{
    namespace
    {
        bool Starts(const std::string& value, const std::string& prefix)
        {
            return value.rfind(prefix, 0) == 0;
        }
    } // namespace

    nao::v1::ApiMethod ApiMethodFor(const std::string& httpMethod, const std::string& path)
    {
        if (Starts(path, "/api/auth") || path == "/api/login" || path == "/api/register" ||
            path == "/api/refresh")
        {
            return nao::v1::API_AUTH;
        }
        if (Starts(path, "/api/chat") || path == "/api/topic") return nao::v1::API_CHAT;
        if (Starts(path, "/api/history") || path == "/api/read-state") return nao::v1::API_HISTORY;
        if (path == "/api/state" || path == "/api/presence") return nao::v1::API_STATE;
        if (Starts(path, "/api/persona")) return nao::v1::API_PERSONA;
        if (Starts(path, "/api/savings") || path == "/api/balance") return nao::v1::API_SAVINGS;
        if (Starts(path, "/api/weekly-plan")) return nao::v1::API_WEEKLY;
        if (Starts(path, "/api/plan")) return nao::v1::API_PLAN;
        if (Starts(path, "/api/plugins")) return nao::v1::API_PLUGIN;
        if (path == "/api/health") return nao::v1::API_HEALTH;
        if (Starts(path, "/api/health/")) return nao::v1::API_HEALTH;
        if (Starts(path, "/api/push")) return nao::v1::API_PUSH;
        if (Starts(path, "/api/groups")) return nao::v1::API_GROUP;
        if (Starts(path, "/api/cron")) return nao::v1::API_CRON;
        if (Starts(path, "/api/tools")) return nao::v1::API_TOOL;
        if (Starts(path, "/api/endpoints")) return nao::v1::API_ENDPOINT;
        if (Starts(path, "/api/diary") || Starts(path, "/api/shelf") ||
            path == "/api/commands" || path == "/api/conversations" ||
            path == "/api/logs" || path == "/api/memory" || path == "/api/usage" ||
            path == "/api/status" || path == "/api/avatar" || path == "/api/token" ||
            path == "/api/relation" || path == "/api/reminders")
        {
            return nao::v1::API_QUERY;
        }
        if (httpMethod == "POST" && path == "/api/command") return nao::v1::API_COMMAND;
        return nao::v1::API_ADMIN;
    }

    std::string InternalPathFor(const std::string& path)
    {
        if (path == "/api/health") return "/internal/health";
        if (path.rfind("/api/", 0) == 0) return "/internal/" + path.substr(5);
        return path;
    }
} // namespace Gateway
