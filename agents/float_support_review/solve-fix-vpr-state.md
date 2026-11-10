# VPR 快速写回状态修复记录（2026-09-26）

本包是已获架构审查批准的最小 VPR 状态修复，与 [FD 状态包](solve-fix-fd-state.md) 分开记录。唯一生产改动是 `sail-riscv/model/extensions/V/vext_regs.sail` 中 SYMBOLIC 的 `set_V_bits`、`set_V` 快速写臂；不变更 rV/getter、普通写臂、非 SYMBOLIC 路径、V lane 运算或正式 IR/严格配置。

## 红例及根因

旧 d012 IR SHA-256 `d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409` 上，独立审查者用直接 helper wrapper 测 `zset_V_bits` 的 v0 同值写。初始 mstatus=`0x200`（VS=Initial）；普通路径完成后是 `0x8000000000000600`，快速路径却保持 `0x200`。旧 runner 的 fast-expected 条目 exit 101、fast-observed 与普通条目各 exit 0。wrapper 保持旧完整 IR 字节前缀且未替换函数体，原始输入、哈希、三份 TSV 与运行日志在仓库外 `isla-vpr-dirty-review-20260926/manifest.json`。这直接定位到快速写只调用 `wV_from_vector`，漏掉原 `wV` 随后的 Dirty 更新和写回回调。

## 实施与检查

- `set_V_bits` 快速臂现在依次调用原 `wV_from_vector(unsigned(vregidx_bits(i)), data, VPRs)`、`dirty_v_context()`、`vreg_write_callback(i, data)`。
- `set_V` 快速臂现在依次调用原 `wV_from_vector(r, v, VPRs)`、`dirty_v_context()`、`vreg_write_callback(vregno_to_vregidx(Vregno(r)), v)`。原始写入值及索引沿用 `wV`。VPR 的 Dirty 在回调前，与 FD FPR 的原写回次序不同。
- 没有新增前置 Ext_V assert；原 `wV` 也是先写，再由 `dirty_v_context` 断言 Ext_Zve32x。false/非 SYMBOLIC 仍调用原 `wV`。

当前 `vext_regs.sail` SHA-256 为 `6682f5ce387359c4d5a6873cf877e2f001231b4f38917b8721c89cdfd81f17d9`，旧文件为 `6a409189bc8b65a0eab68598684137cee4886d642f7703fb23ee8abfe54a9b5a`。在 `sail-riscv/model/` 用 P1 V128/E64 JSON（SHA-256 `89923ebff21718bb382df38bf246207cbb1eb5ae0cd314d078d87c0ab2b9f625`）分别运行带与不带 `-D SYMBOLIC` 的 `sail --strict-var --strict-bitvector --strict-exponentials --require-version 0.20.1 --all-modules --just-check riscv.sail_project`，两次均退出 0；memo 路径在仓库外。`git -C sail-riscv diff --check` 通过。

## P2 动态门槛

直接 runner 在 `sail-riscv/test/symbolic_fp/solve_vpr_state_runner.rs`，使用准确 BV5 索引和 BV128 寄存器值。它要求 `zset_V_bits`、`zset_V` 两个真实函数体齐全，分别测试 fast/normal、VS=Initial/Clean/Dirty、同值/异值、v0/v31；32 个 VPR 逐个设哨兵并确认目标写值及其余 31 个不变，同时检查 fcsr、f0 保持、mstatus 转为 VS=Dirty/SD=1，每次一条完成 SAT 路径。先以 `--legacy-bits-only` 对 P1 IR 运行同一 runner：普通写的 12 例全 PASS，首个快速写在 mstatus 检查取得旧 `0x200`、预期 `0x8000000000000600`，exit 101；仓库外 `isla-vpr-state-probe-p2/old-red.{command.json,stdout.log,stderr.log}` 固定 runner/IR/config 哈希。

P2 候选 IR SHA-256 `d86655a415441ad17533742b9d0ee726b43b64acaf2c0fc0754d27979c7859a9` 明确保留 `zset_V_bits`、`zset_V` 两体，模型快照的本文件哈希与上文一致。runner 用 P2 冻结 Isla 库外部重建，二进制 SHA-256 `ee038a235d2b578d994c26bca87e95fae32c3b8bc71ebe4ad1611e104be866ce`；RV64 E 配置 SHA-256 `8247c8d467489111656f6953660670e96097a029fea458b660fe42579f86f987`。完整运行 exit 0：24 组条件各调用两入口，共 48 次真实函数调用，均完成一条 SAT 路径，32 个 VPR、fcsr、f0 和 mstatus 全部符合预期。命令、三文件哈希与原始输出位于仓库外 `isla-vpr-state-probe-p2-final/p2.{command.json,stdout.log,stderr.log}`。独立审查者还把旧完整 IR 的同值写 wrapper 直接追加到 P2 IR：normal/fast 两臂现在均得到 `0x8000000000000600`，单条 SAT 路径与差异 UNSAT；交叉证据在仓库外 `isla-vpr-dirty-review-p2-20260926/manifest.json`。P2 仍属外部候选，正式主 IR/config 和全组回归另验。

最终额外保留四个旧 helper 体的完整 IR SHA-256 `c5cbb0bbdaa9369b669aa7330531bfb1a0cf1ef7d905b071f14f510d10c7385c` 与 P2 使用同一 Sail 源。以 MixedBits 冻结 Isla 库（`primop.rs` SHA-256 `6c6d5a4248d9874405bbc48f850f5c32b77e60f0762212244e1a173fa13f4a20`）重建 VPR direct runner，二进制 SHA-256 `75f9f4f66426a946f238337025be291b890690975c2cef222c95f085adfcaf9b`；对该 IR 再跑上述 48 次状态检查 exit 0。命令、IR/config/runner 哈希及原始输出在仓库外 `isla-vpr-state-probe-p2-mixedbits/final.{command.json,stdout.log,stderr.log}`。runner 对 BV128 值使用 `Model::get_val` 后直接以 B129 格式与预期比较，不调用 `FmtVal`、`BitVal::from_bv` 或 `Model::get_fmtval`；若最后只修 `fmtval.rs` 序列化，须先核最终库差异确实只在该文件，方可沿用此数值证据。

## 统一最终 IR/runtime 直接复验（2026-09-27）

以真实 Sail 生成的统一 IR SHA-256 `1dcc80812b8beaba49abaebf605e8090c2796b5930aefa36635b478c5f2b8180`、模型/运行时 manifest SHA-256 `28fb65ee77e2c5e5c629c50b239a2e009337b47936b2fdbb897bf9c11bca055e`，从冻结 `isla-lib` 重建 [direct runner](tools/solve_fix_helpers/run_direct_state.py)。运行时 `primop.rs`、`ir.rs`、`fmtval.rs`、`smt.rs` 的 SHA-256 分别为 `6c6d5a42…`、`d26e7923…`、`43806138…`、`3ce7310d…`；RV64 E 配置 SHA-256 `8247c8d4…`，VPR runner 二进制 SHA-256 `e43827be7188f94bceded3815d2842f90c8892fa1c0640f497f7122d760d48b9`。

`set_V_bits` 和 `set_V` 两个真实函数体在 fast/normal、VS Initial/Clean/Dirty、同值/异值、v0/v31 的 24 个组合下共执行 48 次，全部一条 SAT 完成路径；32 个 VPR、fcsr、f0、mstatus 的预期值全部匹配，exit 0。精确构建/执行命令、逐文件哈希及原始日志见 `isla/target/float-solve-evidence/direct-state-final-1dcc8081/reports/summary.json`（SHA-256 `1f6124fdb7d72322807ea5947551325f3ae0ec2322fb4508593f660ed627d314`）。此 direct 状态结论与正式整指令 77 项批次分开。
