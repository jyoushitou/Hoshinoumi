cmake_minimum_required(VERSION 3.20)

project(rec_gateway VERSION 20.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# CommonNet：用户自己的 Boost.Asio 通讯库（vcpkg overlay port: commonnet）
find_package(CommonNet CONFIG REQUIRED)

# Boost.JSON 由 CommonNet 的 HTTP 组件带出，但显式声明便于阅读错误信息
find_package(Boost CONFIG REQUIRED COMPONENTS beast json)

add_executable(rec_gateway
    src/main.cpp
    src/config.cpp
    src/router.cpp
    src/backend.cpp
)

target_include_directories(rec_gateway PRIVATE src)

target_link_libraries(rec_gateway PRIVATE
    Common::Net::HttpServer
    Common::Net::HttpClient
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
