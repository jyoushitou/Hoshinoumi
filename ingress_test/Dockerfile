FROM docker.m.daocloud.io/library/python:3.13-slim
RUN pip install -q aiohttp websockets -i https://pypi.tuna.tsinghua.edu.cn/simple
WORKDIR /src
COPY bot /src/bot
COPY ingress_test/fake_unix_worker.py /src/fake_unix_worker.py
COPY ingress_test/ingress_integration.py /src/ingress_integration.py
COPY ingress_test/bluegreen_integration.py /src/bluegreen_integration.py
COPY scripts/nao_supervisor.py /src/scripts/nao_supervisor.py
CMD ["python", "bluegreen_integration.py"]
