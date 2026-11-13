#include "Utils.h"
#include <iostream>
#include <atomic>

// Utils::serviceID 由库本体（source/Utils.cpp）定义并导出，这里不再重复定义，
// 否则静态库链接会出现重复符号、动态库链接会出现 C4273 链接不一致。
// 测试里按需改值即可： Utils::serviceID = ServiceID::Test;

void testTime()
{
    std::cout << "===================" << std::endl;
    std::cout << "This test of time in Utils" << std::endl;
    std::cout << "===================" << std::endl;

    std::cout << std::endl << "Now time is " << Utils::Time::nowTime() << std::endl << std::endl;

    time_t nowTime = Utils::Time::nowTime();

    std::cout << std::endl << "Now time is " << Utils::Time::getNowtime() << std::endl << std::endl;

    std::cout << std::endl << "Now day is " << Utils::Time::getNowDay() << std::endl << std::endl;

    std::cout << std::endl << "last time is " << Utils::Time::computeTime(nowTime) << std::endl << std::endl;

    std::cout << "===================" << std::endl;
    std::cout << "time in Utils over" << std::endl;
    std::cout << "===================" << std::endl;
}

void testFile()
{
    std::cout << "===================" << std::endl;
    std::cout << "This test of file in Utils" << std::endl;
    std::cout << "===================" << std::endl;

    std::cout << "you can the dir ,in dir have TEST.txt" << std::endl;
    Utils::File::outFileAdd("TEST.txt", "测试");

    std::cout << "you can test create dir! enter you go to dir" << std::endl;
    std::string dir;
    std::cin >> dir;
    Utils::File::createDir(dir);

    std::cout << "you can test create log! enter you write log" << std::endl;

    std::string logs;
    std::cin >> logs;

    Utils::File::outLog(logs);

    std::cout << "===================" << std::endl;
    std::cout << "file in Utils over" << std::endl;
    std::cout << "===================" << std::endl;
}

void testOut()
{
    std::cout << "===================" << std::endl;
    std::cout << "This test of out in Utils" << std::endl;
    std::cout << "===================" << std::endl;

    std::cout << "you can test out msg! enter you test msg" << std::endl;
    std::string msg;
    std::cin >> msg;
    Utils::Out::outMsg(msg);

    std::cout << "you can test out error msg! enter you test msg" << std::endl;
    std::string msg1;
    std::cin >> msg1;
    Utils::Out::outErr(msg1);

    std::cout << "you can test out net msg! enter you test msg" << std::endl;
    std::string msg2;
    std::cin >> msg2;
    Utils::Out::outNetMsg(1, msg2);

    std::cout << "===================" << std::endl;
    std::cout << "out in Utils over" << std::endl;
    std::cout << "===================" << std::endl;
}

void testExit()
{
    std::cout << "===================" << std::endl;
    std::cout << "This test of exit in Utils" << std::endl;
    std::cout << "===================" << std::endl;

    Utils::Exit::registerStopCallback([]() { Utils::Out::outMsg("收到退出信号，开始清理资源..."); });

    // 主线程在此阻塞，直到收到系统退出信号或外部调用 recviceExit()
    Utils::Exit::waitExit();

    // 退出流程（waitExit 返回后触发，或手动调用）
    Utils::Exit::gracefulShutdown();

    std::cout << "===================" << std::endl;
    std::cout << "exit in Utils over" << std::endl;
    std::cout << "===================" << std::endl;
}

void testString()
{
    std::cout << "===================" << std::endl;
    std::cout << "This test of exit in Utils" << std::endl;
    std::cout << "===================" << std::endl;

    std::cout << "you can test split string!you enter you wang to split string"<<std::endl;
    std::string str;
    std::getline(std::cin,str);

    auto vec = Utils::String::split(str, 0, '|');

    std::cout << "you splited string :" << std::endl;

    for (auto i : vec)
    {
        std::cout<<i<<std::endl;
    }

    std::cout << "===================" << std::endl;
    std::cout << "exit in Utils over" << std::endl;
    std::cout << "===================" << std::endl;
}

/// @brief 程序的启动函数
/// @return 返回程序的执行码
int main()
{
    Utils::init();
    std::cout << "===================" << std::endl;
    std::cout << "This test of Utils" << std::endl;
    std::cout << "Init is over" << std::endl;
    std::cout << "===================" << std::endl;
    std::cout << "Go to you test?" << std::endl;
    while (1)
    {
        std::cout << "0.close Test" << std::endl;
        std::cout << "1.Test time" << std::endl;
        std::cout << "2.Test File" << std::endl;
        std::cout << "3.Test Out" << std::endl;
        std::cout << "4.Test Exit" << std::endl;
        std::cout << "5.Test string" << std::endl;
        int key = 0;
        std::cin >> key;
        switch (key)
        {
        case 0:
        {
            goto close;
        }
        case 1:
        {
            testTime();
            break;
        }
        case 2:
        {
            testFile();
            break;
        }
        case 3:
        {
            testOut();
            break;
        }
        case 4:
        {
            testExit();
            break;
        }
        case 5:{
            testString();
            break;
        }
        default:
        {
            continue;
        }
        }
    }
close:
    std::cout << "===================" << std::endl;
    std::cout << "Utils test over" << std::endl;
    std::cout << "===================" << std::endl;
    return 0;
}