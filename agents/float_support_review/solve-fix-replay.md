# 官方 solve 独立重放 lane

2026-09-26。消费端实现位于 [工具目录](tools/solve_replay/protocol.md)，只增加审计与 replay 工具，不改 Isla 生产执行器或独立内存工作树。Astra 审定的边界：完整初态下真实 word→decoder→execute；全部可满足终态逐路径证明 decoded、ret 与全 post 对残余辅助状态观察唯一，然后与官方记录比较。`trace_binding_complete` 只表示轨迹关联成立，不表示源码 branch 穷尽。

## 已实现

- `audit.py` 校验官方与 replay 双 manifest 的 IR/配置/二进制哈希、Isla 与 Sail 源文件逐文件/树哈希、初始化来源与运行时变换；核 JSON 的 case ID、终态/输出配额守恒、完整 pre/post、采样与错误、itrace 终态及实际 branch catalog/edge。`test-ins` 调用 `sail-riscv/test/assembly_text/check.py` 的 LLVM 接口，合法 Retire 必须重编码同 word；审核过的非法操作数组合另列，汇编文本失败仍排队做动态 replay。
- 隔离 Rust runner 由 `prepare_runner.py` 复制到仓库外目录或获批的 `isla/target/float-solve-evidence/<run>/replay-runner`，Cargo target 独立。一次进程只加载/初始化 IR 一次；复现官方 `assertions_to_jumps`、Optimistic 与 model register init，按完整快照装配位串/枚举/结构寄存器。每个物理 word 真实译码后执行全部 SAT 路径；Poison、采样、Unknown、可达错误和未导出的物理 PC/x0 读取均失败；Dead 单列。对原始 decoded/ret/全部 post 与同 model 具化值的任一差异求 SAT，要求 UNSAT。
- `run_batch.py` 消费同批 replay manifest，把所有 `gen` 与可构造的不可编码物理 word 负例放入一次 runner 调用，分别写静态审计、动态结果和缺口。`source_branch_closed` 保留待源码 site/arm 分母审核。

## 已验证的组件范围

- Python 合成负例和真实 itrace fixture **41/41 通过**。覆盖重复/孤儿 case ID、计数与 emitted/suppressed 不守恒、sampled 却 complete、缺 post、模型源码篡改、错误 edge、旧 FLI 文本及 tuple 字段顺序。R2 旧 case80 的 requested/decoded 打印顺序不同，规范化后值相等；故意改字段值仍失败。
- Rust runner 的残余辅助状态两例 **2/2 通过**：未约束观察值差异 SAT；独立未约束辅助存在但观察值固定时差异 UNSAT。
- P1 组件固定 IR SHA-256 `f5141217f2695fb53a0584c1bc7dfa059eac15df51c07ae3f02307099e4b4a61`、配置 `8247c8d467489111656f6953660670e96097a029fea458b660fe42579f86f987`。R3 compact `FLI_S` JSON 97 终态/96 gen，trace 97 块、25,924 catalog site、297,721 已走 edge 双向关联通过；96 条标准 ASM 重编码一致。单次 IR 初始化的 Rust 批重放 **96/96 通过**，96 条均为 1 decode/1 execute，墙钟 6.70 秒；输入 SHA-256 `af9f44cc00830c190f57fbb9467347fc8a0b64afa043856aca619d98cfaa9c06`，结果 `933cf6e3398c260dee7baad604f33f7181974b3931dea188ecce1559293e8dbf`。Python 对结果 decoded/ret/全 post 再核 96/96。该批次未提供完整独立生产源码 manifest，属于组件验证，不能记正式同源验收。
- [完整 102 寄存器 P1 FLI fixture](tools/solve_replay/fixtures/p1-fli-case80.json) 的正例通过；翻转预期 `fcsr` 的负例使批 runner 返回非零，并逐项报告 post 差异。R3 `FLI_S` 的不可编码 FS Off witness 以同 constructor 的已编码 word `32'hf010_0053` 在该完整初态重放，实际译码为 `ILLEGAL`、返回 `Illegal_Instruction` 且全 post 不变；[负例 fixture](tools/solve_replay/fixtures/p1-nonencodable-word.json)保留 guard 来源。此负例只覆盖该 P1 witness。

复核入口：

```sh
python3 -m unittest discover -s agents/float_support_review/tools/solve_replay -p 'test_*.py'
python3 agents/float_support_review/tools/solve_replay/prepare_runner.py --isla-lib "$RUN_DIR/stage/isla-lib" --output "$RUN_DIR/replay-runner"
CARGO_TARGET_DIR="$RUN_DIR/replay-runner/target" RUSTFLAGS="-L native=$Z3_PREFIX/lib -C link-arg=-Wl,-rpath,$Z3_PREFIX/lib" cargo build --locked --manifest-path "$RUN_DIR/replay-runner/Cargo.toml"
python3 agents/float_support_review/tools/solve_replay/run_batch.py "$RUN_DIR/replay-manifest.json" --runner "$RUN_DIR/replay-runner/target/debug/isla-float-solve-replay" --runner-source-manifest "$RUN_DIR/replay-runner/source-manifest.json" --output "$RUN_DIR/replay-audit" --timeout-seconds 7200
```

`RUN_DIR` 必须指向同批冻结快照，`Z3_PREFIX` 使用该批官方构建采用的 Z3 前缀。上述 P1 记录完成时，正式 77 项新 IR 批次尚未结束；后续 c5 批已结束但因 FmtVal 宽位输出缺陷转为诊断。最终新 IR、宽位修复及同 Model 缓存必须一起冻结，按新版 manifest 重建 runner 并全量重放。本轮没有正式 77 项全量 replay PASS；P1 和下列 c5 组件结果均不外推。

## 续接复核：MixedBits、高位和 decoder 纯读前提

本节是 2026-09-26 的 c5 组件记录；后续候选版本见下一节。

- 当前 Python **52/52**、Rust **7/7**。Rust 源 SHA-256 `519f86dce4a3fe8d1429e981e1bf9fc7ca9d367cea66d4ddba9beb47c294871b`；除了残余辅助状态两例，还覆盖普通 128 位 Bits、Concrete MixedBits、真实 Model 具化 Symbolic+Concrete MixedBits 的顺序与差异 UNSAT，以及 decoder 副作用负例。全局 let 的 `Monomorphize` 漏口由独审指出，新增负例先红后绿；没有修改生产执行器。
- c5 组件固定 IR `c5cbb0bbdaa9369b669aa7330531bfb1a0cf1ef7d905b071f14f510d10c7385c`、配置 `20851fdbd5120066b5a0275d3780c255edb715b233fb31a2529b8e110ef723d0`。隔离 runner 二进制 `e5d76348e9151482ca55073ce876df6eaec08ad18974b618654752c2047ee352`，依赖该旧批 `stage/isla-lib`；它未包含后续 FmtVal/Model 缓存修复，故只是 replay 消费端组件证据。
- [完整向量 fixture](tools/solve_replay/fixtures/replay-vector-high-half.json) 使用编码 `0x021111d7`，102 项 pre/post，配置默认 `misa`。`vr0=123456789abcdef0fedcba9876543210` 保持；`vr3=112233445566778840c0000040700000` 正确写回。先 SAT，再对 decoded/ret/全 post 的原始值与同 Model witness 差异证明 UNSAT。真实正例通过；分别令 `vr0` 或 `vr3` 的预期高 64 位重复低 64 位，Rust 与 Python 均拒绝。批 runner 按预期退出 101，结果 `[PASS, FAIL, FAIL]`；验证脚本退出 0。
- 初版扩展 fixture 把 FS=Initial 错写成预期 Dirty，得到明确 mstatus 差异。依 `accrue_fflags` 的 changed 条件及 `dirty_v_context` 修订：本例新 flags 为零，旧 fcsr=1 不变，因此 FS 保持 Initial、VS=Dirty、SD=1，预期 `mstatus=0x8000000a00002600`。此修订只更正测试预期。
- 两段式 decoder/execute 的辅助状态过近似经架构审查接受，前提已自动化：初始化前对实际 IR 的 decoder 调用闭包检查全局写/间接写/外部调用；执行中仅允许 decoder 的纯读事件；Dead 再验 UNSAT。c5 证书记录 **248 函数、566 调用、0 global/间接写、0 未分类 callee**，并绑定 IR/config/runner/源码哈希。纯 extern 共 29 种，配置常量仅 `sys_enable_experimental_extensions`；内部向量 init/update 的目标同样受 global 写检查。最终 IR 会重新生成并校验自己的证书。
- 77 项的大 trace 改为逐行消费，文件哈希改为 1 MiB 分块。真实 c5 FLI_S 的约 58 MiB trace 核得 **25,950 catalog、97 terminal、297,721 edge**，与 JSON 双向守恒；已有 scalar 消费者的 trace/runtime 接口测试 **14/14、12/12**。这只是轨迹关联证明，未关闭源码分支分母。

外部证据目录名 `isla-replay-resume-20260926`：`high-half-purity-final/evidence.json` 保存命令、输入、结果和纯读证书哈希；输入 SHA-256 `b922b664345ddba2ec517f11afb0d80132d34fe4512b0e14dd656654b2bc260a`，结果 `6f82fb1a19a2264394a30352c04518fd0fe18424079328932c4b393cf0a5fcc6`，证书 `c1bc256a3506d3b7559afb63c39de528fa8eed21de646cf0098c9ccd7b74d8d5`。`purity-v2-tests-final.log` 的 SHA-256 为 `623390ca56686e0b373bc5a6c8609f0161da2a76a69ec7be5739ec22b4323590`。

完整高位正负控制命令：

```sh
python3 agents/float_support_review/tools/solve_replay/smoke_high_half.py \
  --binary "$RUN_DIR/replay-runner/target/debug/isla-float-solve-replay" \
  --ir "$RUN_DIR/stage/rv64d.ir" \
  --config "$RUN_DIR/stage/configs/riscv64_difftest_fd.toml" \
  --output "$RUN_DIR/replay-high-half-smoke"
```

## 2026-09-27：1dcc 候选与最终运行时同版组件

新候选 IR SHA-256 `1dcc80812b8beaba49abaebf605e8090c2796b5930aefa36635b478c5f2b8180`，冻结源 manifest `28fb65ee77e2c5e5c629c50b239a2e009337b47936b2fdbb897bf9c11bca055e`；组件配置仍为 `20851fdbd5120066b5a0275d3780c255edb715b233fb31a2529b8e110ef723d0`。隔离 runner 使用该冻结 `isla-lib`，包含 `primop.rs=6c6d5a42…`、`fmtval.rs=43806138…`、`smt.rs=3ce7310d…` 与 `ir.rs=d26e7923…`，未修改冻结源码。

新版 decoder 闭包实际新增 `eq_anything` 的 bv5 调用及 `strict_or_bool`；后者经源码复核才加入明确白名单。`strict_or_bool` 在 `binary_primops` 直接映射 `or_bool`，具体输入只做 Bool 化简，两个符号输入只定义 `Or` 值；没有 Frame、寄存器、内存、I/O 或额外 Assume。`eq_anything` 原已在白名单，其 bv5/MixedBits 路径只拼接并定义等式。先以新增前检测试得到“未审 strict_or_bool”失败，再补白名单；实际 dispatch 的四种 Bool 真值、四种符号输入组合 SAT、与 OR 差异 UNSAT及仅 SMT 事件均通过。Rust **9/9**；未分类外部调用仍被拒绝。

该 IR 自身的新证书为 **248 函数、568 调用、0 global/间接写、0 未分类 callee**；不能复用 c5 的 566 调用。`encdec_nreg_forwards`、`vext_vs1_backwards` 的显式函数体取代旧 `_infallible` 名称，调用数净增 2。runner 源 SHA-256 `41539ebb4314d96aa4942832a7837b171f508868d0d5ff6fbc5e80df81727f8f`，二进制 `74f34e9fbfc3fda4487e48d39f6d69a2c85012ccbe8783dbf9f41ec2e4fd3ac2`。

完整 102 寄存器高半部正例及 vr0/vr3 旧重复低 64 位负控制已按上节同命令形状重跑，仍为 `[PASS, FAIL, FAIL]`，验证脚本退出 0。外部证据目录名 `isla-replay-final-runtime-20260926`，`high-half/evidence.json` 绑定实际命令；结果 SHA-256 `acee1b259d404d86756322729c3f0cd30d66005f492644a804c824a578c4857c`，纯读证书 `a4c9dafd70a308e88932b47c25b0da8f218eefd68e40d74c8c1f4fb6dd6ff0ce`，9 项测试日志 `215103875cdc7e839480c63486003d51b25d76f93077ab6fc945e1ee94659529`。正式批次尚待严格配置、代表测试与 manifest，故这是新候选同版组件通过，仍不是 77 项全量 replay PASS。

覆盖 lane 的独立 reencode 另需 encoder 纯读前提。为此在同一外部证据目录建立 `encoder-purity-runner`：派生同一检查器，仅将静态 root 改为 `zencdec_forwards`，并在该辅助源码显式添加实际遇到的 `eq_bool`、`zero_extend`。两者经源码及架构复核只产生值/SMT 定义与临时可满足性查询，没有永久 Assert、Frame 或 I/O；实际 dispatch 的常量/符号差异 UNSAT、输入组合 SAT 及仅 SMT 事件定向 **1/1**。该辅助程序输入空 cases，只生成静态证书，不表示动态编码覆盖。`encoder-purity.json` 的 root 明确为 encoder，记录 **161 函数、201 调用、0 global/间接写、0 未分类 callee**；SHA-256 `0d2e5fe61c5ca1010d4f62c38a67835ff95370dd00d61b261b8a4ea288ed4154`，辅助源码 `37b3b92a99740cd1a38fff8ff2b07dadb619eb4b24f83a157aea3de8a20d5ced`，二进制 `d5deace5dee6f4e52ce8df9d81329d0b589e9f15923794509822c90336a6fb28`。其 source manifest 保留派生变换；正式 decoder runner 未增加这两项白名单。定向消费者仍须检查自己的动态错误、采样和完整状态，不能仅凭纯读证书认定执行完整。

## 2026-09-27：正式 1dcc 批次全部现有完整输出

正式批次 `isla/target/float-solve-evidence/official-1dcc-20260927-002314/` 最终为 **50 项自然完成、27 项超时、make=2**；超时项没有最终 JSON。三个增量 wave 精确覆盖全部 50 项现有完整输出：26 项/6,195 gen、20 项/6,153 gen、4 项/6,129 gen。每项目标先等待 `status.intime` 在 isarch 退出后落盘，再冻结 JSON/trace/log 哈希及当时 evidence manifest；最终与官方 `artifacts` 逐项核对，无重复或漏项。没有最终整批 replay manifest，因此没有 77 项全量 PASS。

| 已核范围 | 结果 |
| --- | --- |
| 全部 50 项完整输出 | 18,584 终态 = 12,903 Retire + 5,574 Illegal + 107 non-encodable；sampled=0、suppressed=0 |
| 全部生成记录 | **18,477/18,477** 真实 word→decoder→execute 一致；各条 1 SAT decode/execute，Dead=0，完整 AST/ret/102 项 post 的独立 Python 核对通过 |
| 标准汇编 | 18,076 条重汇编得到原 word；另 401 条经逐条源码 guard、word 字段、完整文本及 LLVM 原诊断确认非法寄存器组合，全部保留物理 word 参加上述 replay |
| 不可编码终态负例 | 83 条借用精确同 requested payload 的 gen word；24 条经辅助真实 encoder 生成同 payload word。原 witness 完整初态下 **107/107** 译码为 ILLEGAL、返回 Illegal、102 项 post 不变 |
| 纯读证书 | 正式 decoder 248 函数/568 调用；辅助 encoder 161/201；零全局/间接写、零未分类 callee，分别绑定实际 IR/配置/二进制/源码 |

汇总入口为批次根目录 `replay-aggregate-final.json`，SHA-256 `18fb2ee70b6a197c90f56d401fb6b53b69e88e9dbb8f985aa8cd63a9c4354795`。它独立核全部自然完成目标集合、每条原始 gen 内容、最终官方产物哈希、各波全部结果与补充负例。`completed-subset-pass=true`、`all-available-gen-replayed=true`，但 **`whole-run-complete=false`**；源码 branch 分母仍不从该结论推出。

### 序列化红绿修复

首两波旧 runner 实际完整 AST 的 SAT→witness 差异 UNSAT 和 ret/post 核验未报错，Python 字段比较却拒绝：官方 collector 的 `stable_instruction_text` 对名称只解码一次，replay 的 `to_str_fmt` 使用递归解码，把 tuple 字段类型中的 `%enum zrounding_mode` 改成 `%enum rounding_mode`。直接改用普通 `to_str` 仍有同问题，因此新增消费端 `instruction_text`，只按 collector 名称协议序列化已证唯一的具体 AST。没有删除字段、放宽比较或新增约束。

含 enum tuple 字段的定向测试先红后绿，Rust **10/10**；Python **54/54**。旧两波目录与旧 runner 均保留；复验结果位于 `replay-audit-wave-001-r02`、`replay-audit-wave-002-r02` 和 `replay-audit-wave-003`，受测 runner 源 SHA-256 `342ef3d5118b44ac1afbce7216cbb0529bbfe28afb04c3ce487b1b45cfab517a`，二进制 `12d497a799d04d03d4ab4f36b0fe72856088267ef1e58cdc7e1c09c1dc3c3132`。序列化测试红/绿日志 SHA-256 分别为 `23518f1471d55ef0093a3e0125d6006712825d4ab5bdb8b583f6a589912cc54f`、`e309a9574869e4fb5688db722229a8adaaec55deb4bdacbe50fd3a801aa58944`。

### 负例和非法汇编补证

24 个 non-encodable witness 的完整 requested 字段没有完全相同的现成 gen word。辅助工具 [negative_words.py](tools/solve_replay/negative_words.py) 保留原 collector/AST 哈希及原 102 项 pre；选取同 clause 已 Retire gen 的完整辅助 pre，显式记录 seed 和两份初态。按实际 IR 类型复原每个 Bits/Enum/Struct 字段，立即与原 requested 序列化串核等；真实 `encdec_forwards` 每条 SAT 路径证明 word 全 32 位唯一、跨路径同 word，辅助 pre 下真实 decoder 再证完整 AST 相同。随后以原 witness pre 和该 word 调用正式 replay runner。辅助初态不替代原 witness；此派生负例不称原 encode-first 路径重演。输入审计独立确认 24 个 seed 全为 Retire/decoded、双方 102 字段完整；结果位于 `replay-negative-encoder/`，encoder/原 pre decoder 结果 SHA-256 分别为 `7cd2ecb699b61739567711149c40d399c568af6c3328fc44955c36c38da3284d`、`e3c8acdf67c931381447015ccf023f54b0184fb78255d6bb4dcacbad462a2b55`。

401 条 LLVM 拒绝包括窄转换 126 条、宽转换 275 条。物理条件集合为 252 条 `vm=0 && vd=0` 及 149 条仅宽转换 `vd==vs2`；36 条 mask 重叠同时有同 base 重叠。`valid_rd_mask`、`illegal_fp_variable_width` 与 `valid_reg_overlap` 的冻结源 guard 逐项对应，文本字段逐项等于 word 字段。LLVM 在双违规时可先报告源重叠，最终按其实际诊断分类为 mask 234 条、源重叠 167 条。审核文件 `replay-audit-wave-003/illegal-operand-review.json` SHA-256 `ab1ba44e4d68cff089558d13ff75e190cfcff38b26aca54b97baaf27c9b68e57`，保留全部原诊断；原始静态 FAIL 保留，补证只关闭这些明确非法操作数组合，不豁免 Retire 或语法错误。

增量及最终核账命令（`RUN_DIR` 为上述批次目录）：

```sh
python3 agents/float_support_review/tools/solve_replay/prepare_wave.py "$RUN_DIR"
# 对准备出的每波manifest调用run_batch.py，增加--incremental，输出replay-audit-wave-NNN。
python3 agents/float_support_review/tools/solve_replay/aggregate_waves.py \
  "$RUN_DIR" "$RUN_DIR/replay-aggregate-final.json" \
  "$RUN_DIR/replay-audit-wave-001-r02" "$RUN_DIR/replay-audit-wave-002-r02" \
  "$RUN_DIR/replay-audit-wave-003"
```

重新生成汇总时须选新的输出文件名，工具拒绝覆盖历史证据。全 77 项仍需补足 27 项超时目标的完整生成与同合同全量回放。
