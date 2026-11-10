# 四个 BF16 write root 的 default helper 排除

补审 `shared-v-control-caller-candidates.json` 中四个实际 `zwrite_vreg` root（PC51343、51557、51836、52091）下的 8 项 `zwrite_vreg_default` PC70 双臂义务。原 BF371 与 V P2 证书保持冻结。

工具核默认 TOML、配置不可覆写入口证书及其 runner 文件，再扫描全部实际 sidecar 引用。`__isla_use_extra_ops=true` 的 10 处引用均为直接 Jump，没有写入或地址逃逸。从真实 `zwrite_vreg` CFG 重建递归调用闭包，证实目标 default helper 不在闭包；改为 false 的负控会到达 default helper。逐项保留 clause、phase、配置、root、source site、PC、taken 和 successor。

实际运行 18.852 秒，exit 0，stderr 空。证据位于 `isla/target/float-support-review/final-coverage/bf16/independent-write-default-cut-review/`；`certificate.json` SHA256 为 `3e676ee5139a1196f3a0f125672e4301e378f9d9a85e1b5c8f429e3bd7d39670`，`run.json` 保存完整命令。结论只适用于默认 FD，不适用于 default-lanes。
