# ===================== 友利奈绪 QQ 机器人 =====================
# 构建：
#     docker build -t nao-bot:16.0.0 .
#     docker build --build-arg WITH_BROWSER=1 -t nao-bot:16.0.0-browser .
#
# 运行（推荐 host 网络，NapCat 和 MySQL 都按 IP 直连）：
#     docker run -d --name nao-bot --network host \
#       -e NAO_DB_HOST=your-db-host -e NAO_DB_PASS=your-password \
#       -v $PWD/data:/app/data -v $PWD/personas:/app/personas \
#       --restart unless-stopped nao-bot:16.0.0

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    TZ=Asia/Shanghai \
    DEBIAN_FRONTEND=noninteractive

# 时区 + Pillow/编译基础库
RUN apt-get update && apt-get install -y --no-install-recommends \
        tzdata ca-certificates \
        libjpeg62-turbo zlib1g libpng16-16 \
        gcc python3-dev \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先装依赖（利用层缓存）
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 可选：把 Chromium 也打进来（镜像会大 ~400MB）
ARG WITH_BROWSER=0
RUN if [ "$WITH_BROWSER" = "1" ]; then \
        pip install --no-cache-dir playwright fonttools brotli \
        && playwright install --with-deps chromium \
        && rm -rf /var/lib/apt/lists/*; \
    fi

# 业务代码
COPY . .

# 运行时数据（挂卷持久化）
RUN mkdir -p /app/data && chmod 700 /app/data

# 3001：NapCat 连进来的 WebSocket；60908：HTTP API
EXPOSE 3001 60908

HEALTHCHECK --interval=60s --timeout=5s --start-period=20s --retries=3 \
    CMD python3 -c "import socket,sys; s=socket.socket(); s.settimeout(3); \
sys.exit(0 if s.connect_ex(('127.0.0.1', 3001)) == 0 else 1)"

CMD ["python3", "run.py"]
