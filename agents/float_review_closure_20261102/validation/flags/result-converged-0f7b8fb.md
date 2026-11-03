# 最终收敛模型的 flags helper 定向复验

在模型 `0f7b8fbc6724103f91f929ef6918f123df75d6c9`、Isla `42000be47596ec088623881d03c0eadc5cf0ba27` 的新生成 IR 上，直接执行 `zaccrue_fflags`：五个逻辑入口各 60 组具体初态，合计 **300/300 通过**。每次运行均退出 0，独立 `oracle.py` 复算完整 FCSR/mstatus 后态均退出 0；五份日志分别确认 qffp 下 seed17 拦截生效。这是固定值 helper 状态验收，不生成指令 JSON，也不签完整 Clause。

正式 [inputs](../inputs.model-converged-0f7b8fb-itrace.json) SHA-256 `5147af93ecd9cfb5cd6c0607d8073fa997b608dc9993f8c81dee8e739f1e631e`，模型树 `.worktree/sail-riscv-float-converged-20261103` 在该提交上干净。IR SHA-256：RV64 V128/default `0fb0897e028803155108ec59f8289d4f89bafa98deb063bfa7f016a3d29f0786`，V256 `47ba73418d6dcb1b1e86db7680ce4df9508e7885a02096e25e213c2c3b2c05e1`，V512 `2bdea17d36c64545254f50cc5a6902e570a1fea682de3f7c062bf641a85a62a9`，RV32 `e17c4fe18552f8ce219b35f846c4c1a2c530dcad0ac9fc8f10d0da2604c3fa4e`。默认与 V128 为同字节 alias，仍单独执行第五逻辑入口。

实际 Rust probe binary SHA-256 `ded63f435d89cfd84bac858f9eed8d382084c70c2c296c550bf3db98e606c7dd`，未修改或重建测试逻辑；正式 isarch `acda0dceb259205fe0c43a3785484ffcafbef26b3194de3b9f67ad38eccbcf7d` 只绑定来源。官方 Z3、seed 库、配置 SHA、CPU15、完整命令及每份原始日志 SHA 见 [result.json](runs/model-converged-0f7b8fb/result.json)，该文件 SHA-256 为 `0b5cb0e6b07a9a985470b085c446ce65ece19d44777dc06f7ee90b12a6cb1151`。对五组运行、seed、oracle 日志重新计算 SHA-256，全部与账本一致。

既有 300 例矩阵和 oracle 未改：零 flags、旧位已含本次位、首次及多位新增，交叉 FS Initial/Clean/Dirty、初始 SD 0/1 和其他 mstatus 位哨兵；RV32 检 SD31，RV64 检 SD63。最终树 `fdext_regs.sail` SHA-256 `252002bb29d17da842bfacc2ac5733baec7eeada2d84dce29c233a1a8dafb3b5`，与 e9 逐字相同。`run.py` 仅增加最终完整提交的精确版本门，SHA-256 `2d79b3bca36b9db0eda8424c88129f53dc30016dc95c46bb80cf7bd0fda86026`，独立 Sol 已预签该一行差异。新 [dry-run 清单](dry-run.model-converged-0f7b8fb.json)退出 0；旧 8ad、214、e9 三批结果目录均保留原证据。

此测试直接调用 helper，避免指令写 FPR 的 Dirty 掩盖 changed 假臂。实际 IR 中两个 CSR callback 的次数与顺序只签静态调用合同，未观察动态事件；普通 Sail changed 真臂另有 mstatus callback。人工 Ext_F 初态不代表所有状态可由完整指令到达，也不覆盖 Zfinx。独立 Sol 已在 [最终结果审查](../../review/acceptance/model-converged-results-review.md)中从实际 old/incoming/初态复算 300 项，并核新 IR、配置、probe、源码、seed 与 oracle 归档；该固定 helper 批次限定签收，无阻断。
