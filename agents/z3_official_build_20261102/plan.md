# 编译官方最新Z3

用户要求官方最新commit已修复default，编译官方新版本。以2026-11-02查询到官方Z3Prover/z3 master head为准，记录完整SHA，独立检出和build/install目录，不修改现有fork main/旧构建/系统Z3/Isla或gitlinks。

流程：拉取官方head，核对enum-aware qffp/default修复及版本；CMake Release/Ninja编译shell、libz3和test-z3，安装独立prefix；fpa回归、历史枚举+FP最小例及flags-11原始query(default，显式7200秒预算)、API/模型回读及Isla独立副本FLEQ smoke。只在实际验证后记PASS，保留日志/配置/二进制/源码哈希；不做新的A/B性能比较，不自动替换生产链接或发布fork。
