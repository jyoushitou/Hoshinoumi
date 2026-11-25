/// @file        api_contract.h
/// @brief       网关 → worker 的逐接口内部契约
#pragma once

#include "nao/v1/internal_v2.pb.h"

#include <string>

namespace Gateway
{
    /// @brief 依据 HTTP 方法和公开路径选择 typed ApiMethod
    nao::v1::ApiMethod ApiMethodFor(const std::string& httpMethod, const std::string& path);

    /// @brief 公开路径 → 逐接口 /internal/* 路径
    std::string InternalPathFor(const std::string& path);
} // namespace Gateway
