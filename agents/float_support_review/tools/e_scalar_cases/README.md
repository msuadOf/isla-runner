# E 阶段 RV64 标量非访存逐项验证

范围：`clause-matrix.md` 第 9–34 项去除 BF16 转换第 10、11 项和 RV32 专属第 27、28 项，加上第 47–73 项去除已有独立验证的第 49、51 项，共 **47 个 clause**。BF16、RV32 和向量由其他验证负责。这里的 50 个主实例每个 clause 至少有一个真实 32 位编码；额外 18 个状态实例只加强六个 `FMINM/FMAXM` clause 的 NaN 与零号角落。单条编码不代表同一类型化 clause 内其他子操作已覆盖。

受测固定件：RV64 IR SHA-256 `c9e1bfe29e75452568d61fc3b3407e707eb1bd7e48193e212495ec21b885bc75`；runner SHA-256 `bd362465a970a623b561680ae45e15d7ea0e28b4836dc2c439c3e981fc228425`；配置 SHA-256 `8247c8d467489111656f6953660670e96097a029fea458b660fe42579f86f987`。runner 取自 E 非访存隔离候选并在本轮复制为固定副本；GNU assembler/objdump 2.46 使用 `-march=rv64gcv_zfa_zfh_zfbfmin`。主实例 JSON SHA-256 `2a2f27170a6879bae543277c08beca3e754831165acfec1f7ed517bfed8c7412`；特殊实例 JSON SHA-256 `3f1a9c45d58aba37e6ea15b5c7d067283a082d2f4e0205e265639b439649e520`。

归档的 `scalar.objdump` 仅把 objdump 自动打印的本机产物路径头规范化为 `scalar.o`，机器码与指令行未改；规范化文件 SHA-256 `d0c30f9395521cb12bd612e3b4c936277d8413129209a5a04f0c084c0b9514c0`。生成脚本同样规范化此头，确保复跑结果不含本机路径。

## 结果

| 批次 | 实例 / clause | 结果 | 证据 |
|---|---:|---|---|
| 第一轮 | 50 / 47 | 43 PASS、7 FAIL | [原始输入](v1-cases.json)、[摘要](v1-summary.json)、[失败 stderr](v1-failures.json)、[成功证明](v1-proofs.json) |
| 修正预期后 | 50 / 47 | **50 PASS** | [主实例](scalar-cases.json)、[摘要](v2-summary.json)、[证明](v2-proofs.json) |
| NaN/零号加强 | 18 / 6 | **18 PASS** | [特殊实例](scalar-special-cases.json)、[摘要](special-summary.json)、[证明](special-proofs.json) |

第一轮七项失败均为测试预期错误：`FLI_{D,H,S}` 的汇编立即数写成 `0x10`，GNU as 将其理解为浮点数值 16.0，实际译码常数索引 `0x19`；修正为 `1.0` 后译码索引 `0x10`，编码及反汇编见 [汇编输入](scalar.s)和[objdump](scalar.objdump)。`FROUNDNX_{D,H,S}` 与 `FCVTMOD_W_D` 的结果及 fflags 原已吻合，漏写了 fflags 更新时 `mstatus.SD=1`，修正完整 `mstatus` 期望后通过。首轮输入和失败日志保留，不用第二轮替代其历史事实。

第二轮 50 项及加强批次 18 项的证明记录均为 `sat=true`、`difference_unsat=true`、`structural_ok=true`、`execute_result=Retire_Success`；每项 `zext_decode` 两条 SAT 完成路径同值、`zencdec_forwards` 一条、`zexecute` 一条。runner 逐项检查译码构造器及全部 tuple 字段、重编码等于输入编码，写回寄存器和完整 `fcsr`/`mstatus` 与独立预期的差异查询为 UNSAT。六个 `FMINM/FMAXM` 的主实例使用 rs1=qNaN，特殊实例覆盖 rs2=qNaN、rs2=sNaN（规范 NaN 和 NV）、`-0/+0` 顺序；三个格式均检查结果 boxing。

这些是列明编码和具体初态的定向验证，不是对同一 clause 全部 enum 成员、所有舍入模式或所有输入的穷尽证明。

## 复跑

`generate.py` 的独立预期由 Python `struct` 构造 S/H/D 位串，并直接给出整数、标志和 boxing；GNU as 生成真实编码，objdump 留证。`run_cases.py` 逐项保存原始输入、runner JSON 输出、stderr、摘要和四项输入哈希；失败时继续下一项。运行前将三个变量设为对应上方 SHA-256 的 runner、IR 和配置文件：

```sh
python3 agents/float_support_review/tools/e_scalar_cases/generate.py "$OUT"
python3 agents/float_support_review/tools/e_scalar_cases/run_cases.py \
  --binary "$RUNNER" --ir "$IR" --config "$CONFIG" \
  --cases agents/float_support_review/tools/e_scalar_cases/scalar-cases.json \
  --out "$OUT/results-v2"
python3 agents/float_support_review/tools/e_scalar_cases/run_cases.py \
  --binary "$RUNNER" --ir "$IR" --config "$CONFIG" \
  --cases agents/float_support_review/tools/e_scalar_cases/scalar-special-cases.json \
  --out "$OUT/results-special"
```

## 类型化 enum 与特殊域增补（2026-09-26）

[原始缺口清单](enum-gaps.md)保留了扩展前 90 个类型化 enum 中本目录仅 28 个已测的状态；[覆盖表](enum-coverage.md)逐项给出当前 90/90 个 enum 的源码映射、合法 RM、guard 和证明批次。新增 [enum 输入](enum-ops.json) 62/62 PASS（其中 FADD.S/D 在本目录重验）；原 50+18 项、首轮 43/7 历史证据未覆盖。

两份 enum 表的 `FCVT` 格式列统一按**源→目标**显示，例如 `FCVT_D_S` 为 S→D、`FCVT_W_D` 为 D→W；这只影响表格文字。当前缺口清单 SHA-256 `407827508500314fb793fb9ce2ea9a9aef2fd64dfb649d2bd7cb3011c748e404`，覆盖表 SHA-256 `8664c4641b9af054ca2792c121328e812705f6dd1cb3614a5f040039ae691d8f`。

新增批次及其精确输入、结果、逐项证明：

新增输入 SHA-256：enum `998349b62616662ae99f52dcbbca1969947a143ad5c1bde0b678f88125670cb1`，FLI `7e3e4b73970d5b60f29c2789d459c747eb7c049f7de55fb450d6f15ab523d436`，RM `39a1bbb014053da6c9ac58b2cfc75bc08ebedf41fb268aa97fb0a07ac7d25c51`，状态边界 `9b42c325de403917f4f8190e7a8279b512e8d506672b60b427adc55f47e9f25b`，负控 `29028e5e240295bc4b4fac2f0150bafc9ca3f848ca3219c32fd722b5ee648252`。正向 runner、IR、配置哈希沿用上文；隔离负控 runner 二进制 SHA-256 `7b3a086e208527ea2a0e4fe7c3cfa527be553f795177bd52377573aaaa259f89`，归档源码 SHA-256 `0b08a08400e5f9b470826a91c6fcca9b9fccb285ed91b1426f8467c44c307381`。

| 批次 | 数量 | 结果 | 证据 |
|---|---:|---|---|
| 类型化 enum 缺口与 FADD.S/D | 62 | PASS | [输入](enum-ops.json)、[汇编](enum-ops.s)、[反汇编](enum-ops.objdump)、[摘要](enum-summary.json)、[证明](enum-proofs.json) |
| FLI H/S/D 全索引 | 96 | PASS | [输入](fli-table.json)、[反汇编](fli-table.objdump)、[摘要](fli-summary.json)、[证明](fli-proofs.json) |
| RM 路由及优先级 | 169 | PASS | [输入](rm-routes.json)、[反汇编](rm-routes.objdump)、[摘要](rm-v2-summary.json)、[证明](rm-v2-proofs.json) |
| FCVTMOD、NaN、boxing、分类、搬运 | 76 | PASS | [输入](state-edges.json)、[摘要](state-v2-summary.json)、[证明](state-v2-proofs.json) |
| 静态/动态 RM 负控 | 30 | PASS | [输入](negative-cases.json)、[反汇编](negative.objdump)、[证明](negative-proof.json) |

FLI 常数预期由 [生成脚本](generate_fli_table.py) 的独立数值表和 IEEE 打包构造；三格式各 32 个索引。H 索引 29 为 `+inf`，索引 31 为规范 NaN，输入 `fcsr=0x6a` 保留旧 flags 和 FRM。编码使用 `.insn 4` 的固定 FLI 字段，GNU objdump 将 96 条全反汇编为 `fli.*`。类型化 enum 编码由 GNU as 从助记符生成，结果由独立数值、boxing 和 flags 预期给出，绝不以 Sail 运行结果作 oracle。

RM 批次按 7 个执行族（ADD、MADD、SQRT、FP→X、X→FP、FROUND、FROUNDNX）×H/S/D 验证五个动态 FRM（105 项）；S 格式每族五个静态 RM 与故意不同的 FRM（35 项），H/D 每族各一个静态优先级实例（14 项）；另测 H←S、H←D、S←D 三个窄化方向的五个动态 FRM（15 项）。初始 `fcsr` 带旧 DZ，输出同时检查新 NX、旧 flags、FRM 和 `mstatus.SD`。独立 [RM 生成脚本](generate_rm_routes.py) 用有理数精确算术选择目标格式相邻浮点数；SQRT(2) 通过相邻值及中点的平方与 2 比较，不依赖待测 Sail 或近似浮点结果。第一次 RM 批次 [169/169 PASS](rm-v1-summary.json) 因 H←S 与 H←D 名称相同，已更正唯一命名并把 [第二轮 169/169](rm-v2-summary.json) 作为正式证据；原第一轮仍保留。

[状态边界](state-edges.json)覆盖 FCVTMOD 零、次正规、正/负分数、`2^31` 越界、`2^84`、NaN/∞及 NV 优先于 NX；原主实例另测 `2^32+3` 环绕。还覆盖三格式 quiet/ordered 比较的 qNaN/sNaN、H/S 非法 NaN boxing、FCLASS 十类别每格式、FMV H/S/D 高符号位与原位搬运。第一轮 [39/39 PASS](state-v1-summary.json) 后新增分类、搬运与 NV 优先样例，第二轮完整 76/76 PASS，两个批次都保留。

静态 RM 5/6 的 12 项负控在 `zext_decode` 得到 `ILLEGAL` 并返回原编码，译码阶段观察状态不变；动态 RM 编码 7 搭配 FRM 5/6/7 的 18 项，在 `zexecute` 返回 `Illegal_Instruction`，寄存器、`fcsr`、`mstatus` 不变。每项两条 SAT 译码路径；执行阶段拒绝各一条执行路径。隔离 [负控 runner 源码](negative_runner.rs) 基于原非法 runner，只新增对译码阶段 `ILLEGAL` 的明确检查及差异 UNSAT 检查；此测试没有把正向 runner 的失败退出记作 PASS。其可重建 Cargo 模板为 [negative_runner_Cargo.toml](negative_runner_Cargo.toml)，将 `ISLA_LIB_PATH` 替换为对应候选库的实际路径。当前配置对应 Sail `config/config.json.in` 的 `Fcsr_RM_Illegal` 行为。

新增证据仍是具体状态的定向测试；旧功能 helper 全符号/差分证据见 D 阶段。当前未宣称每 enum×全部 RM 或每条指令所有数值边界的穷尽证明。
