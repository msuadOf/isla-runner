FROM ubuntu:22.04
ARG APT_REPOSITORY
ARG APT_KEY
ARG SUBMIT_USER
ARG SUBMIT_UID
ARG SUBMIT_GID
ENV DEBIAN_FRONTEND=noninteractive
RUN printf '#!/bin/sh\nexit 101\n' > /usr/sbin/policy-rc.d && chmod 755 /usr/sbin/policy-rc.d \
    && apt-get update && apt-get install -y --no-install-recommends ca-certificates curl gnupg python3 tini \
    && curl --fail --show-error --location "$APT_KEY" -o /tmp/condor.key \
    && gpg --batch --dearmor --output /usr/share/keyrings/htcondor.gpg /tmp/condor.key \
    && printf 'deb [signed-by=/usr/share/keyrings/htcondor.gpg] %s jammy main\n' "$APT_REPOSITORY" > /etc/apt/sources.list.d/htcondor.list \
    && apt-get update && apt-get install -y --no-install-recommends htcondor \
    && groupadd -g "$SUBMIT_GID" "$SUBMIT_USER" \
    && useradd -m -u "$SUBMIT_UID" -g "$SUBMIT_GID" "$SUBMIT_USER" \
    && mkdir -p /var/lib/condor/execute /etc/condor/isla-auth /srv/isla /srv/submit \
    && rm -f /tmp/condor.key && rm -rf /var/lib/apt/lists/*
# 不依赖包内服务启动逻辑；运行时用 CONDOR_CONFIG 指定完整配置。
ENV CONDOR_CONFIG=/etc/condor/isla.conf
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/usr/sbin/condor_master", "-f"]
