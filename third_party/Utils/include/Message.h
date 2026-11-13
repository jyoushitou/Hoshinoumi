/// @brief       服务ID定义
/// @author      jyoushitou
/// @date        2026-09-16
/// @copyright   Copyright (c) 2026

// 防止重复包含
#pragma once

#include <string_view>

/// @brief      服务ID
/// @details    唯一的服务寻址标识，会写入消息头，两端必须一致
/// @note       显式赋值，禁止依赖默认递增
enum ServiceID : int
{
    Test = 0,         ///< 无效/未指定
    RPCGateway = 1,      ///< RPC网关服务：请求转发与路由
    SQL = 2,             ///< SQL数据库服务：数据持久化
    Registry = 3,        ///< 注册中心服务：服务发现与注册
    ConfigCenter = 4,    ///< 配置中心服务：统一配置管理
    MonitorService = 5,  ///< 监控服务：运行状态监控
    SecurityService = 6, ///< 安全服务：访问控制与安全防护
    CertService = 7,     ///< 证书服务：证书签发与管理
    TracingService = 8,  ///< 链路追踪服务：分布式链路追踪
    ServiceConsole = 9,  ///< 服务控制台：服务管理界面
    AdminConsole = 10,   ///< 管理控制台：后台管理界面
    User = 11,           ///< 用户服务：用户信息与认证
    Article = 12,        ///< 文章服务：文章内容管理
    Blog = 13,           ///< 博客服务：博客业务逻辑
    Image = 14,          ///< 图片服务：图片上传与处理
    Video = 15,          ///< 视频服务：视频上传与处理
    Search = 16,         ///< 搜索服务：全文检索
};

/// @brief      服务ID转名称
/// @details    仅用于日志与诊断
/// @param[in]  id 服务ID
/// @return     服务名称，无效/未知ID返回空
/// @warning    新增枚举值后必须在此补充 case
/// @note       编译期可求值，无堆分配
constexpr std::string_view ServiceName(ServiceID id) noexcept
{
    switch (id)
    {
    case Test:
        return "Test";
    case RPCGateway:
        return "RPCGateway";
    case SQL:
        return "SQL";
    case Registry:
        return "Registry";
    case ConfigCenter:
        return "ConfigCenter";
    case MonitorService:
        return "MonitorService";
    case SecurityService:
        return "SecurityService";
    case CertService:
        return "CertService";
    case TracingService:
        return "TracingService";
    case ServiceConsole:
        return "ServiceConsole";
    case AdminConsole:
        return "AdminConsole";
    case User:
        return "User";
    case Article:
        return "Article";
    case Blog:
        return "Blog";
    case Image:
        return "Image";
    case Video:
        return "Video";
    case Search:
        return "Search";
    }
    // 枚举已全覆盖；兜底返回以应对非法强转值
    return {};
}
