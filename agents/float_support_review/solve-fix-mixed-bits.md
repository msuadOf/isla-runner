# MixedBits 通用 append 修复与验证

## 范围和实现

P2 `FVVMATYPE` 的真实译码路径在一秒诊断预算下每条执行 370–686 次 SMT 查询，SMT 占 active wall 80.2%–91.3%。固定 opcode/RM 位段经 `append(Symbolic, Bits)` 变成整体 `Symbolic(Concat)`，随后切片失去具体性。背景和独立200次比较探针见 [性能分析](solve-fix-performance.md) §15。

本次只把 `isla/isla-lib/src/primop.rs` 中 `Symbolic + 非空 Bits` 及反序的 `append` 返回值改为现成 `MixedBits` 两段，保持 MSB→LSB 顺序。`Symbolic+Symbolic`、`Bits+Bits` 继续原路径；已有 MixedBits 续接空 Bits 不再制造零宽段。`mixed_bits_slice(length=0)` 返回具体 `Bits(0)`，避免空段列表进入 SMT。

扩大 MixedBits 使用后，固定索引和长度在转换为 `u32` 前做检查；正长度越界直接触发内部不变量失败。零长切片先返回 Bits0，保留旧 Symbolic 分支对任意索引的零长语义。动态符号索引仍走原 SMT 路径。旧 Symbolic 对 `±2^32` 的强制类型转换也可能绕回有效位置，因此非法输入的诊断并非逐字等价；合法 Sail 索引才纳入等价门槛。`isla/isla-lib/src/ir.rs` 仅修正 MixedBits 注释。没有修改 Sail 模型、decoder、guard 顺序、RM 原语或运行态约束。

冻结源 SHA-256：`primop.rs` `6c6d5a4248d9874405bbc48f850f5c32b77e60f0762212244e1a173fa13f4a20`；`ir.rs` `d26e7923712ccf214b7b7dc47d817b66a49e70d11c8c7fdcb9ef171c832c2562`。

## 局部测试

先新增测试并确认原实现失败：预期两段 MixedBits，实际是整体 Symbolic；新增零长非法索引测试也先失败。随后修改生产代码。可重跑：

```sh
cd isla
cargo fmt --package isla-lib -- --check
cargo test -p isla-lib --lib primop::tests --quiet
```

结果为 67/67 PASS，日志在 `isla/target/float-solve-evidence/mixed-bits/primop-tests.log`。测试覆盖两种拼接顺序、空串、Mixed+Mixed、片段内与跨段/全宽/末端切片、I64/I128固定索引、动态128位有符号索引的完整合法0–12域、位访问、负与 `±2^32` 索引、越界、B64承载71位与B129承载135位、`eq_anything`、`smt_value`、`Model::get_val` 和 `FmtVal`。未知输入及完整拼接结果先 SAT，再对旧 Concat 的差异证 UNSAT；非零切片同样证差异 UNSAT。零长结果为具体 Bits0，不把 SMT BV0 传入求解器。`Model::get_val(MixedBits)` 的既有合同返回全 Concrete 的 MixedBits，并不自动合并成单个 Bits；旧外部 runner 若仅接受 Bits，需要在测试适配层合并段后再比较，不能把该类型不匹配当作数值差异。

整套 `isla-lib --lib` 在本工作树及旧 P2 冻结 stage 都于同一既有 `enumeration sort name is already declared` 中止，串行运行也一样；不能记为全库 PASS。两份日志分别在上述目录的 `isla-lib-tests-serial.log` 和 `isla-lib-old-stage-tests-serial.log`。

## 真实译码语义与成本对照

独立真实译码证据在 `isla/target/float-solve-evidence/mixed-bits/decoder-proof/`，其 `README.md`、`manifest.json` 和 `results.json` 给出重建、来源与日志。探针链接本次冻结 Isla 库，复用实际 `RV64::setup_pre_state`，在同一 solver checkpoint 下双向比较旧 Concat 和新 append 对完整返回构造器及全部 payload 的影响。C.ADD家族16位、FADD.S 32位与保留 opcode 32位共58组配对路径均先 SAT、差异 UNSAT，进程退出0；没有执行错误、未完成或架构寄存器写入。编码未知字段和明确常量见该目录 README；这属于这三种编码形状的译码证明，不覆盖全部指令执行域。初版更宽未知字段120秒未完成，未计入通过结果。

成本脚本为 [profile_ab.py](tools/mixed_bits/profile_ab.py)，同一 P2 IR `d86655a415441ad17533742b9d0ee726b43b64acaf2c0fc0754d27979c7859a9`、配置 `20851fdbd5120066b5a0275d3780c255edb715b233fb31a2529b8e110ef723d0`、完整符号输入域、2线程、SMT15秒、每路径诊断1秒、进程外限30秒；仅替换二进制。旧新 stage 源码除 `primop.rs` 和 `ir.rs` 外逐文件相同。重跑：

```sh
python3 agents/float_support_review/tools/mixed_bits/profile_ab.py \
  isla/target/float-solve-evidence/p2-vector-diagnostic-20260926/stage \
  isla/target/float-solve-evidence/mixed-bits/stage-new \
  isla/target/float-solve-evidence/mixed-bits/profile-ab
```

完整命令、二进制哈希与结果在 `isla/target/float-solve-evidence/mixed-bits/profile-ab/profile_ab.json`。旧二进制 `38fc91a6…` 在30秒内记录64条译码路径的一秒超时，调用363–678次/路径，SMT占80.4%–91.3%，3条编码阶段不可编码。新二进制 `80282416…` 在同预算记录161条执行阶段 Illegal、3条不可编码，未触发一秒路径超时统计；两次进程均因30秒外限退出124。**新日志没有路径超时统计不代表零SMT调用**，终态数量也不是穷尽性能比例或完整状态等价。路径统计含共享前缀，不按路径求和为CPU时间。正式77项、新IR和完整状态仍由集成批次复验。
