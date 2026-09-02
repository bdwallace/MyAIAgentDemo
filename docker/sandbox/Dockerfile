# 安全沙箱镜像：只有 Python + git，默认非 root。
# 基础层用本机已有的 redis:7-alpine（同是 Alpine，避免再拉 python 官方镜像）。
FROM docker.m.daocloud.io/library/redis:7-alpine

USER root
RUN sed -i 's#dl-cdn.alpinelinux.org#mirrors.aliyun.com#g' /etc/apk/repositories \
    && apk add --no-cache python3 git \
    && adduser -D -u 1001 -h /home/agent agent \
    && mkdir -p /workspace \
    && chown agent:agent /workspace \
    && rm -f /usr/local/bin/redis-server /usr/local/bin/redis-cli /usr/local/bin/redis-benchmark /usr/local/bin/redis-check-aof /usr/local/bin/redis-check-rdb

WORKDIR /workspace
USER agent
