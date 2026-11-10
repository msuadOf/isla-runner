# negate 与完整译码布局收敛包

日期：2026-09-27。A、B 局部实现和小 IR 验证 PASS；真实全模型新 IR、官方 77 项与实际完整 decoder 的 guard 调用顺序待集成人复验。本包未生成或拼接正式 IR，未修改配置、stage 和内存分支。

## 范围与冻结

基线为 Sail-RISC-V `f8ce8490981eac6396a31013180a2e718615757d` 加既有未提交内容，Isla `f4f8e4584a70588c66c9e7a6286cc20211618f18` 加既有未提交内容。Sail 版本为 0.20.1。全部工具、配置、源码、fixture、IR、runner 和日志哈希见[证据 manifest](../../isla/target/float-solve-evidence/decoder-layout-negate/manifest.json)；命令数组及工作目录亦在其中。证据仅存于 `isla/target/float-solve-evidence/decoder-layout-negate/`，测试源码仅存于 `sail-riscv/test/symbolic_fp/solve_decoder_layout/`。

| 包 | 生产差分 | 冻结前 SHA-256 | 修改后 SHA-256 |
| --- | --- | --- | --- |
| A/S | `fext_insts.sail` 的 `negate_S` 一行 | `d8a91126223008976795da636b1d904b6a4b7f779c765d495b07ded4dedf9b87` | `25c6616356bd851ed3e256775d885466082aee01a23f70804256df452bf77033` |
| A/D | `dext_insts.sail` 的 `negate_D` 一行 | `3fb3566c16fea04f6e81c01630827b23982f66ffe1c6638404e63464b7740122` | `50bd661e27f3b99f4cae79de6ca72bd397e032c8d435a8b604b9578ead3ced5c` |
| A/H | `zfh_insts.sail` 的 `negate_H` 一行 | `4d199c591407a5e4286e20e9513af268ce28109d8d33304d157c2da372ce8c2d` | `f5fc4443b2971eda60251d7250571395edafb5db62834a6902912d5e2b74a02b` |
| B | `vext_arith_insts.sail` 的两条完整 32 位 mapping 与专用 SYMBOLIC helper | `60c1f6f2ec6809bbba39151b44fbeeaa2a5c071d78b0f4ab44d6401ff768d927` | `144c38f3d6fe8854ca2cc9c133165ae08c48dd76fb89181781c091bb29c70d23` |

A 的每一处仅把 `if (sign == 0b0) then 0b1 else 0b0` 改成 `sign ^ 0b1`；`fsplit`、`fmake` 及调用顺序逐字保留。脚本对冻结原件和生产件作一次且仅一次的行替换断言。没有引入 `fp_neg` 或 SYMBOLIC 分体。

B 将 VMVRTYPE 和 VEXTTYPE 的完整 32 位布局分别放入 Sail 原生 tuple ↔ bits32 mapping。`backwards_matches` 对全部固定字段和既有 bits5 纯成员谓词使用 `eq_anything`、`strict_and_bool` 合并成单一 Bool；值函数仍按原切片、寄存器及成员映射重建。非法固定字段或 bits5 直接调用值函数仍为部分匹配失败。有限侧 `forwards_matches=true`；旧新完整 top 的生成 IR 对 VMVR/VEXT constructor 均返回 true、其他 constructor 返回 false，nreg raw 值不参与该判定。普通分支的原 mapping 整块逐字保留，两个 SYMBOLIC 条目的 constructor/payload 顺序和 `when` 全文亦逐字保留；[源码核对](../../isla/target/float-solve-evidence/decoder-layout-negate/layout-source-check.json)及[候选差分](../../isla/target/float-solve-evidence/decoder-layout-negate/layout-proposed.patch)可复核。

## 小模型与严格检查

A 的 builder 从三个真实冻结前件抽取旧 `fsplit/fmake/negate`，候选仅替换符号位一行，生成同一小 IR。Isla runner 对每条旧完成路径先查 SAT，再对完整结果 bits 的旧新差异查 UNSAT；H/S/D 旧函数各 2 路，候选各 1 路。候选与原始最高位 XOR 的全位差异均 UNSAT。每种格式另核正负零、带符号及 payload 的 qNaN/sNaN、最小非零值；60 行 PASS，无寄存器/内存事件、执行错误、未完成或采样。日志在[negate-runner.log](../../isla/target/float-solve-evidence/decoder-layout-negate/negate-runner.log)。

B 的 builder 从冻结 V 源提取已存在的两个 bits5 显式 mapping，在同一小 IR 对照旧完整 concat top 与候选 tuple top。Isla runner 逐 SAT 路径证明未知完整 32 位输入的构造器及所有 payload 差异 UNSAT，对照 wrapper 共 23 路；十个合法 VMVR/VEXT 编码另逐字段核预期。未知 bits5 且固定 funct3 为 `001` 时，旧 VMVR/VEXT 各 4 路、候选各 1 路；这是与 FVVMATYPE 共用 opcode `0x57` 的邻近字段负例。对无效固定字段及 bits5，旧新 top 与新布局直接 value 调用均为预期 `MatchFailure`。未知完整 i64 nreg 的旧新编码值关系有 4 条 SAT 路径，逐条完整 32 位差异 UNSAT；具体 raw `-1,0,1,2,3,4,7,8,9` 的 matches 与 fallback 编码另核。共 103 行 PASS；除预期的部分匹配失败外，无寄存器/内存事件、其他执行错误、未完成或采样。两个新完整布局 matcher 的生成 IR 各为 0 `jump`、0 `eq_bits`，结构见[IR 核对](../../isla/target/float-solve-evidence/decoder-layout-negate/layout-ir-structure.json)，日志见[layout-runner.log](../../isla/target/float-solve-evidence/decoder-layout-negate/layout-runner.log)。这里的 0 jump 指两个布局 helper 本体，外层 union mapping 仍有一次必要的 Bool 判别。

A 后、B 后均从 `sail-riscv/model/` 用 `--all-modules --strict-var --strict-bitvector --strict-exponentials --require-version 0.20.1 --just-check` 和 VLEN128/ELEN64 JSON，在普通及 `-D SYMBOLIC` 两模式检查完整模型，四次均退出 0；B 的 SYMBOLIC 日志含预期的部分 match 警告。`git diff --check` 对四个生产文件通过。B 的[完整 strict 日志](../../isla/target/float-solve-evidence/decoder-layout-negate/layout-typecheck.symbolic.log)与普通日志均在证据目录，配置 SHA-256、命令和退出状态见 manifest。

## 集成边界

本包的 B 对照使用真实 Sail 生成的小 IR；生产全模型的完整 `ext_decode`、`when` 运行时调用顺序及官方 77 项须由新全 IR 的集成人绑定新源码哈希复验。源级检查只证明两个 `when` 表达式和相对位置未改，不把小模型的 23 路写成真实全 decoder 验收。A/B 两包的源码哈希和证据分别列出，不复用冻结 1dcc 的 PASS。
