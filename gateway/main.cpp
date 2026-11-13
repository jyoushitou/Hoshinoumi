/// @file        main.cpp
/// @brief       Hoshinoumi（REC）网关入口（v21.0）
/// @author      jyoushitou
/// @date        2026-11-13
/// @copyright   Copyright (c) 2026

#include "config.h"
#include "router.h"

#include "NetHttpServer.h"
#include "Utils.h"

#include <boost/asio.hpp>

#include <cstdlib>
#include <exception>
#include <iostream>
#include <memory>
#include <string>
#include <thread>

namespace
{
std::string ParseConfigPath(int argc, char **argv)
{
    std::string path = "config/gateway.json";
    for (int i = 1; i < argc; ++i)
    {
        const std::string arg = argv[i];
        if (arg == "--config" && i + 1 < argc)
        {
            path = argv[++i];
        }
        else if (arg == "--help" || arg == "-h")
        {
            std::cout << "用法: rec_gateway [--config config/gateway.json]\n";
            std::exit(0);
        }
    }
    return path;
}
} // namespace

int main(int argc, char **argv)
{
    try
    {
        const std::string configPath = ParseConfigPath(argc, argv);
        const Gateway::Config cfg = Gateway::Config::Load(configPath);

        Utils::init();
        Utils::serviceID = RPCGateway;
        Utils::Out::outMsg("Hoshinoumi（REC）网关 v21.0.0");
        Utils::Out::outMsg("配置: " + cfg.Describe());

        boost::asio::io_context io;
        const auto address = boost::asio::ip::make_address(cfg.listenHost);
        const boost::asio::ip::tcp::endpoint epHttp(address, cfg.listenPort);
        const boost::asio::ip::tcp::endpoint epTcp(boost::asio::ip::tcp::v4(), 0);

        auto router = std::make_shared<Gateway::Router>(cfg);
        auto handler = std::make_shared<Net::Server::HttpServer::HttpHandleFunction>(
            [router](const std::shared_ptr<Net::Server::HttpServer::HttpSession> &session,
                     const Net::Server::HttpServer::Url &url) { router->Handle(session, url); });

        auto server = std::make_shared<Net::Server::HttpServer::HttpServer>(io, epTcp, epHttp, handler);
        server->setTrustProxy(false);

        std::weak_ptr<Net::Server::HttpServer::HttpServer> weakServer = server;
        Utils::Exit::registerStopCallback([weakServer]() {
            if (auto s = weakServer.lock())
            {
                s->stop();
            }
        });

        server->start();
        std::thread ioThread([&io]() {
            try
            {
                io.run();
            }
            catch (const std::exception &e)
            {
                Utils::Out::outErr(std::string("网关 IO 线程异常: ") + e.what());
            }
        });

        Utils::Out::outMsg("HTTP 监听 " + cfg.listenHost + ":" + std::to_string(cfg.listenPort));
        Utils::Exit::waitExit();

        Utils::Out::outMsg("网关正在退出...");
        server->stop();
        io.stop();
        ioThread.join();
        server.reset();
        Utils::Out::outMsg("网关已退出");
        return 0;
    }
    catch (const std::exception &e)
    {
        Utils::Out::outErr("网关启动失败: " + std::string(e.what()));
        return 1;
    }
}

