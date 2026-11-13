cmake_minimum_required(VERSION 3.20)

project(rec_gateway VERSION 21.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# CommonNet：用户自己的 Boost.Asio 通讯库（vcpkg overlay port: commonnet）
find_package(CommonNet CONFIG REQUIRED)

# HS256 JWT 直接使用 OpenSSL HMAC
find_package(OpenSSL REQUIRED)

add_executable(rec_gateway
    main.cpp
    src/config.cpp
    src/router.cpp
    src/backend.cpp
    src/auth.cpp
)

target_include_directories(rec_gateway PRIVATE src)

target_link_libraries(rec_gateway PRIVATE
    Common::Net::HttpServer
    Common::Net::HttpClient
    OpenSSL::Crypto
)

# CommonNet 的 Windows 实现用了 AcceptEx / GetAcceptExSockaddrs
if(WIN32)
    target_link_libraries(rec_gateway PRIVATE ws2_32 mswsock)
endif()

if(MSVC)
    target_compile_options(rec_gateway PRIVATE /utf-8 /W4)
else()
    target_compile_options(rec_gateway PRIVATE -Wall -Wextra)
endif()

install(TARGETS rec_gateway RUNTIME DESTINATION bin)

