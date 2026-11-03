# `accrue_fflags` 定向状态验收

本目录的 Rust 辅助程序直接执行五份正式 IR 中的 `zaccrue_fflags`，避免整条浮点指令写目标 FPR 时独立置 Dirty，掩盖 `changed` 假臂。每份 IR 验 5 种旧/新 flags 组合 × FS Initial/Clean/Dirty × 初始 SD 0/1 × 其他 mstatus 位两种哨兵，共 60 个具体输入。逐例记录完整初始与后态 FCSR/mstatus、输入 flags、实际 xlen 和预期；RV32 在 64 位 mstatus 载体上检查 SD31，RV64 检查 SD63。

`oracle.py` 独立按普通 Sail `old | flags` 和条件 Dirty 语义核状态，核固定 case 名与值，并复核 Rust 的实际输出。普通版本在 changed 且 Ext_F 时通过 `dirty_fd_context_if_present` 额外调用 mstatus callback；最终 SYMBOLIC 版本只保留原两个 CSR callback。这两个版本的架构状态在本 Ext_F 配置下应相同，事件序列有上述已知差别。辅助程序从实际 IR 函数体静态核 `fflags` 后 `fcsr` 的两次 callback 调用和无 mstatus callback；callback 函数在 IR 中为空体，所以此项不宣称动态事件次数。

待主 agent 固定最终五 IR、Isla commit、正式 isarch、官方 Z3、seed17 拦截库及配置，并写入 `validation/inputs.<批次>.json` 后执行：

```sh
python3 agents/float_review_closure_20261102/validation/flags/run.py \
  --inputs agents/float_review_closure_20261102/validation/inputs.<批次>.json \
  --batch <批次> \
  --cpu 15 \
  --rv32-config .worktree/runner-float/isla/test/float_ir/rv32_fd.toml \
  --dry-run
```

核对 dry-run 清单后去掉 `--dry-run`。脚本验证模型/Isla 提交和全部已跟踪文件哈希、五 IR、两个配置、正式 isarch、官方 Z3 及 seed 库；独立编译并哈希 Rust probe binary，逐 IR 保存命令、输出、oracle 和 `fixed=17` 拦截日志。结果只证明上述具体 helper 输入与实际 IR 状态；指令调用者、其他扩展配置、符号输入域和完整 Clause 预算单独验收。
