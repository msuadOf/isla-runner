# `e9d69d2` 的 flags helper 定向复验

在模型 `e9d69d2f28586c089244c8e37ee4c904c5114458`、Isla `42000be47596ec088623881d03c0eadc5cf0ba27` 的新生成 IR 上，直接执行 `zaccrue_fflags`：五个逻辑入口各 60 组具体初态，合计 **300/300 通过**。每次执行均退出 0，独立 `oracle.py` 逐组重算完整 FCSR/mstatus 后态均退出 0；五份日志分别确认 qffp 下 seed17 拦截生效。此项只验固定值 helper 状态，不生成指令 JSON，也不签完整 Clause。

正式 [inputs](../inputs.model-e9d69d2-itrace.json) SHA-256 `eb830e77f6d31e88574e018ef08e1eb1d5f47f2e9369169d9fd4613877e6973a`，模型树为 `.worktree/sail-riscv-general-float-by-model-20261022`，该树在受测提交上干净。IR SHA-256：RV64 V128/default `661fd6e443a690f5b1c2a0ccfd1a5b84c908baba5e1b6cea786a1e0696a022ad`，V256 `76d658edb9bb92ade750161a9f782bb4f908aec9a2ff3951a82a1b476126dc71`，V512 `44657bfff823e33c66326cff0b7a6b27f4fd1715440653299462135fd9880006`，RV32 `c619a2b803ba719505118793d72bb906d74f85acb06d457f8dc687680fdc1e88`。默认与 V128 是同字节 alias，仍按第五逻辑入口单独执行。

实际执行的 Rust probe binary SHA-256 `ded63f435d89cfd84bac858f9eed8d382084c70c2c296c550bf3db98e606c7dd`，与上一批相同；正式 isarch `acda0dceb259205fe0c43a3785484ffcafbef26b3194de3b9f67ad38eccbcf7d` 只作来源绑定。配置、官方 Z3 与 seed 库哈希、CPU15、完整命令及每份日志哈希见 [result.json](runs/model-e9d69d2/result.json)，SHA-256 `a67da52b9801a7d181acce8156f7beb9113112aa36ed308dbc2304621db28b03`。对其中五组运行、seed 和 oracle 日志重新计算 SHA-256，全部吻合。

既有 300 例矩阵、Rust probe 与 oracle 未改：旧位已含新位、零 flags、首次及多位新增，交叉 FS Initial/Clean/Dirty、SD 0/1 和其他 mstatus 哨兵；RV32 检 SD31，RV64 检 SD63。`fdext_regs.sail` 在 e9 named 树与 214 树的 SHA-256 均为 `252002bb29d17da842bfacc2ac5733baec7eeada2d84dce29c233a1a8dafb3b5`。`run.py` 仅增加 e9 完整 commit 的精确版本门，SHA-256 `96deaef252d29659e38b47558d54bedb64e7b9082d81e124ad2cf9acff648620`；独立 Sol 已预签此一行差异。新 [dry-run 清单](dry-run.model-e9d69d2.json)退出 0，未覆盖旧 `21418d0` 或 `8ad5e8e` 结果目录。

此测试直接调用 helper，避免指令写 FPR 造成的 Dirty 掩盖 changed 假臂。两个 CSR callback 的次数与顺序仅从实际 IR 静态核对，未作动态事件观察；普通 Sail 版本在 changed 真臂另有 mstatus callback。人工 Ext_F 状态不代表所有初态可由完整指令到达，也不覆盖 Zfinx。独立 Sol 已在 [新版结果审查](../../review/acceptance/modele9-results-review.md)中从实际 old/incoming/初态重算 300 项，并核新 IR、配置、程序、seed 与归档哈希；该固定 helper 批次限定签收，无阻断。
