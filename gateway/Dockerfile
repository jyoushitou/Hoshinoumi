# Hoshinoumi（REC）gateway 镜像
# 构建上下文是项目根目录：
#   docker build -f gateway/Dockerfile -t hoshinoumi-gateway:20.0.0 .
# 部署机只 docker load / docker run，不在部署机编译 C++。

ARG BASE_IMAGE=ubuntu:24.04
FROM ${BASE_IMAGE} AS build

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential cmake ninja-build git curl zip unzip tar \
        pkg-config autoconf automake libtool python3 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# vcpkg：commonnet / utils 走本仓库的 overlay ports
RUN git clone --depth 1 https://github.com/microsoft/vcpkg.git /opt/vcpkg \
    && /opt/vcpkg/bootstrap-vcpkg.sh
ENV VCPKG_ROOT=/opt/vcpkg

WORKDIR /src
COPY third_party/NetWorkCommunication third_party/NetWorkCommunication
COPY third_party/Utils third_party/Utils
COPY gateway gateway

ENV VCPKG_OVERLAY_PORTS=/src/third_party/NetWorkCommunication/ports;/src/third_party/Utils/ports

RUN cmake -S gateway -B /build -G Ninja \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_TOOLCHAIN_FILE=/opt/vcpkg/scripts/buildsystems/vcpkg.cmake \
        -DVCPKG_TARGET_TRIPLET=x64-linux \
        -DVCPKG_OVERLAY_PORTS="/src/third_party/NetWorkCommunication/ports;/src/third_party/Utils/ports" \
    && cmake --build /build -j"$(nproc)"

ARG BASE_IMAGE=ubuntu:24.04
FROM ${BASE_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /build/rec_gateway /usr/local/bin/rec_gateway
# Utils / OpenSSL 若以 .so 形式产出，一起带上
COPY --from=build /opt/vcpkg/installed/x64-linux/lib /usr/local/lib
RUN ldconfig

RUN mkdir -p /app/config
COPY gateway/config.example.json /app/config/gateway.json

EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/rec_gateway", "--config", "/app/config/gateway.json"]
