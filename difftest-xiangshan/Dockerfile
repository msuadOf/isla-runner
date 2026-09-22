FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends python3 gcc-riscv64-linux-gnu binutils-riscv64-linux-gnu ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace/difftest-xiangshan
ENTRYPOINT ["/bin/bash"]
