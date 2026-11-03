# 整数转换真实浮点输入定向结果

模型 `8ad5e8e9e0fc2a567a3b989a3738698f5c520bde`、Isla `42000be47596ec088623881d03c0eadc5cf0ba27` 的新 V128 IR `5ecea3717205dda77bc3cdbaf7a6b677415152e1f5cd09e541d0530519e25017` 上，隔离 direct runner 完成 819/819 helper、282/282 标量 FCVT、183/183 向量窄转换。各阶段程序退出 0；helper 核普通函数体、单条完成路径及返回 bits/五 flags 差异 UNSAT；真实指令核 32 位编码→译码→反编码、单条 `Retire_Success`、列明寄存器和 CSR 的 SAT/差异 UNSAT。[运行账](runs/rv64d-v128-attempt2/run.json)、[标量逐例结果](runs/rv64d-v128-attempt2/scalar-results.json)、[向量逐例结果](runs/rv64d-v128-attempt2/vector-results.json)保存原始证据。[独立动态审查](../../review/acceptance/conversions-review.md)限定签收：审查者从实际机器字、源寄存器及归档初态，用独立精确有理数算法重算 465 条真实指令的结果、flags、CSR 与列明寄存器保持，全部一致；另核 819 helper 日志次序、退出码、seed17 及 14 份归档哈希。

每条预期输入保留原始 FP 位串、RM、目标 bits 与 flags。独立 Berkeley SoftFloat RISC-V 专用 oracle 产生宽整数预期；六个窄结果再按目标范围饱和，overflow 真臂只返回 NV。独立审查者另以精确有理数解码与五 RM 重算 819 条预期。包括负 NaN、±Inf、可达有限上/下越界、源格式可精确表示的整数端点、范围内非精确、旧 flags、新 NV/NX、普通五 RM 和固定 RTZ。H 最大有限 `65504`，故 H→ui16 无正有限上溢；H→32/64 位整数的有限正越界也不可达，不用虚构输入代测。向量还核合法 H→i8/ui8 SEW8、活动/屏蔽 lane、`vl=0`、`vstart=1`、LMUL2 目的组及源组保持。

模型源清单 166 文件、Isla 源清单 1029 文件在运行前逐一核哈希；两个隔离程序均链接官方 Z3 `899cbc70affab963044e975c814fd549a605b5d7bef31b0fd65fb01421bf9970`，三个求解阶段各有真实 seed17 拦截日志。运行前 14 个脚本/fixture 文件已[冻结](frozen-inputs-attempt2/snapshot.json)；运行后归档副本与启动时、当前文件三方哈希一致，见[归档核对](runs/rv64d-v128-attempt2/input-archive-verification.json)。[正式输入关联](runs/rv64d-v128-attempt2/formal-input-binding.json)核对封存输入 `25a1a624cb5dcac76a2261c470e198c64a75b20259322a1c7ee5d0572b83ec24` 使用同一模型、Isla、V128 IR、官方 Z3 和 seed 拦截器。

启动时在根目录使用 CPU 7 编译两个隔离 runner，再在 CPU 9 调 `run.py`；PID、启动时间和输入哈希分别见 `build-launch.json`、`run-launch-attempt2.json`。`run.py` 的实际输入为：

```text
--ir agents/float_review_closure_20261102/validation/generation/model-8ad5e8e/rv64d_v128_e64/rv64d_v128_e64.ir
--ir-sha256 5ecea3717205dda77bc3cdbaf7a6b677415152e1f5cd09e541d0530519e25017
--config agents/float_support_review/tools/e_nonmem/inputs/rv64-e.toml
--config-sha256 8247c8d467489111656f6953660670e96097a029fea458b660fe42579f86f987
--helper-bin agents/float_review_closure_20261102/validation/conversions/target/release/float-closure-conversion-helpers
--instruction-bin agents/float_review_closure_20261102/validation/conversions/target/release/float-closure-conversion-instructions
--model-source agents/float_review_closure_20261102/validation/generation/model-8ad5e8e/source.json
--isla-source agents/float_review_closure_20261102/validation/generation/model-8ad5e8e/isla-tree.json
--generation-driver agents/float_review_closure_20261102/validation/generation/model-8ad5e8e/rv64d_v128_e64/driver.json
--seed-preload agents/branch_ablation_official_z3_20261102/bin/seed_control.so
--runner-build agents/float_review_closure_20261102/validation/conversions/runner-build.json
--model-commit 8ad5e8e9e0fc2a567a3b989a3738698f5c520bde
--isla-commit 42000be47596ec088623881d03c0eadc5cf0ba27
--z3-lib-sha256 899cbc70affab963044e975c814fd549a605b5d7bef31b0fd65fb01421bf9970
--seed-preload-sha256 8b26e6567f153ec28f35dfaddc15e9dfa3d53dcfa7fb1fe23d4922452bf429ae
--output agents/float_review_closure_20261102/validation/conversions/runs/rv64d-v128-attempt2
```

本批直接 runner 固定 **Qfaufbv**，测试配置为 `agents/float_support_review/tools/e_nonmem/inputs/rv64-e.toml`（SHA-256 `8247c8d467489111656f6953660670e96097a029fea458b660fe42579f86f987`）；正式全域输入使用另一份 FD 配置、**qffp** 和 `isarch solve-state`。因此本批是有限固定输入的 helper/指令定向证明，不算新 `isarch` JSON、完整 Clause、全部寄存器保持或全域数值 PASS。完整 77 Clause 的结果须另行签。

首次旧 806/264/168 fixture 的 `attempt1` 留在 `runs/rv64d-v128-attempt1/`：helper 实际 806/806 通过，但汇总脚本把末尾 `PASS 806 legacy SoftFloat cases` 又计为一条，误报 807 后提前停止，标量/向量未执行。旧 fixture 未随该批复制，不能以当前新版输入文件复现旧批。新版修正计数并补精确端点后另起 `attempt2`，旧批不计本报告完成数。

可提交的小型证据：本目录 `README.md`、`report.md`、四个 Python 脚本、两套 Cargo 模板、`fixture-manifest.json`、`oracle-rows.json`、`helpers.tsv`、`scalar-cases.json`、`vector-cases.json`、`runner-build.json`、`frozen-inputs-attempt2/` 及 `attempt2` 的 `run.json`、seed/ldd/阶段日志、scalar/vector 原始结果、`input-archive/`、归档核对和正式输入关联。`target/`（364 MiB）、两个可执行程序和 `attempt2/wrapped.ir`（15 MiB）是可重建运行产物，不纳入提交清单。父议题的源码/IR/动态阶段各由对应审查独立签收。

## 模型 `21418d0` 的同域复验

assembly 映射修复提交后，正式新输入 `validation/inputs.model-21418d0-itrace.json`（SHA-256 `44641223d4541b042a337c9adab6ac902f34d3af82f3835213f28b39cc247b19`）固定模型 `21418d0b0d4942fae20061ed580ee04aff4a8a61` 与新 V128 IR `5514e98ee5566dbbcfa4f6dbafa9dbb1851c72dce4b52ca0c0a95a1c7fafff4a`。复用同一已审 819/282/183 fixture 与两个隔离 runner，仅替换受测 IR 和模型源码清单；[新运行账](runs/rv64d-v128-model-21418d0-attempt1/run.json)记录 819/819 helper、282/282 标量、183/183 向量全部程序退出 0，标量/向量结果 SHA-256 分别为 `74c2a8e192e2896afc2d853c8b6ee8f1c4a60551a144c5c70641e5a1bad9cbb7`、`014b4f1059d8ec3187898d971ee11130fd2e2363a4ccde68eb4d1170146bb3e4`。模型 166 文件及 Isla 1021 个受清单约束文件逐个核哈希；三段求解各有 seed17 实际拦截。14 个输入文件在运行前[冻结](frozen-inputs-21418d0/snapshot.json)，运行后[归档并复核](runs/rv64d-v128-model-21418d0-attempt1/input-archive-verification.json)。[正式输入关联](runs/rv64d-v128-model-21418d0-attempt1/formal-input-binding.json)明确同模型/Isla/IR/官方Z3/seed、不同的 direct 配置/程序/Qfaufbv。[旧新版逐字段对照](runs/rv64d-v128-model-21418d0-attempt1/old-new-semantic-comparison.json)显示 819 helper 通过次序相同，282+183 真实指令的名称、机器字、观察寄存器、flags/状态、译码与完成证明字段均相同；仅耗时和来源日志另记。此新版动态结果已交独立审查，尚待其签收；旧 `8ad5e8e` 定向结论保留上节原版本。

## 模型 `e9d69d2` 的独立目录复验

候选 `e9d69d2f28586c089244c8e37ee4c904c5114458` 的正式封存输入为 `validation/inputs.model-e9d69d2-itrace.json`（SHA-256 `eb830e77f6d31e88574e018ef08e1eb1d5f47f2e9369169d9fd4613877e6973a`）；新 V128 IR SHA-256 为 `661fd6e443a690f5b1c2a0ccfd1a5b84c908baba5e1b6cea786a1e0696a022ad`。源码清单核对候选树 166 个模型文件，生成 driver 显示 exit 0、`source_unchanged=true`。候选相对 `21418d0` 只改变 `model/core/ieee_fp_exceptions.sail`；本批仍重新运行实际 IR，不沿用旧动态结果。

[新运行账](runs/rv64d-v128-model-e9d69d2-attempt2/run.json)记录 **819/819 helper、282/282 标量、183/183 向量**通过。fixture 检查、IR 包装和三个求解阶段均退出 0；三段 seed17 拦截成功，两个程序实际链接官方 Z3 `899cbc70affab963044e975c814fd549a605b5d7bef31b0fd65fb01421bf9970`。[运行前快照](frozen-inputs-e9d69d2/snapshot.json)的 14 个文件在运行后与[归档副本](runs/rv64d-v128-model-e9d69d2-attempt2/input-archive-verification.json)逐项哈希一致。13 个文件与旧 `21418d0` 冻结副本逐字相同；`run.py` 只适配新冻结目录的仓库根路径、显式候选模型树校验及路径记录。正式输入与 direct runner 的模型、Isla、V128 IR、官方 Z3、seed 一致；配置、程序和 tactic 不同，详见[关联记录](runs/rv64d-v128-model-e9d69d2-attempt2/formal-input-binding.json)。

[新旧逐字段对照](runs/rv64d-v128-model-e9d69d2-attempt2/old-new-semantic-comparison.json)以实际 `21418d0` 与 `e9d69d2` 输出比较，819 条 helper PASS 顺序一致，282+183 条真实指令除耗时外的全部结果字段一致。新标量结果 SHA-256 为 `060b013eee462f18e73f947c8d7e3c7e23232fb1af14f8ff81f7b42eb2cf3780`，向量为 `7e93d9f89289068c54bbef5c3db3ec641bc97967f19cce7fa6cfa7e6e5f41383`。首次启动因复制运行器后仓库根路径层级错误，在执行 fixture 前退出；[启动记录](run-launch-model-e9d69d2.json)和[失败日志](run-launch-model-e9d69d2.log)保留。修正后重新冻结并以[第二次启动记录](run-launch-model-e9d69d2-attempt2.json)运行，未改变 fixture、oracle、两个 Rust runner、配置或程序。[独立验收审查](../../review/acceptance/modele9-results-review.md)已限定签收新实际输出及来源。这是 fixed-input direct runner 结果，不代表正式 `isarch` JSON 或完整 Clause 预算。

## 收敛模型 `0f7b8fb` 的最终定向复验

封存输入 `validation/inputs.model-converged-0f7b8fb-itrace.json` SHA-256 为 `5147af93ecd9cfb5cd6c0607d8073fa997b608dc9993f8c81dee8e739f1e631e`，固定模型 `0f7b8fbc6724103f91f929ef6918f123df75d6c9`、Isla `42000be47596ec088623881d03c0eadc5cf0ba27`、V128 IR `0fb0897e028803155108ec59f8289d4f89bafa98deb063bfa7f016a3d29f0786`。新模型已恢复部分纯返回数据流；旧 e9 结果只作历史对照。本批实际重新运行固定的 819 helper、282 标量、183 向量用例。[运行账](runs/rv64d-v128-model-converged-0f7b8fb-attempt1/run.json)记录三组 **819/819、282/282、183/183** 通过，fixture 检查、包装和三组求解均退出 0，三个 seed17 拦截成功，两个程序实际链接官方 Z3。

[运行前冻结](frozen-inputs-converged-20261103/snapshot.json)的 14 个 fixture/runner 文件与已审 e9 attempt2 逐字相同，运行后与[归档副本](runs/rv64d-v128-model-converged-0f7b8fb-attempt1/input-archive-verification.json)逐项哈希一致。[正式输入关联](runs/rv64d-v128-model-converged-0f7b8fb-attempt1/formal-input-binding.json)核对相同模型、Isla、IR、官方 Z3 和 seed；direct runner 仍用独立配置、程序及固定 Qfaufbv，与正式 qffp `isarch` 不同。[e9→收敛版逐字段对照](runs/rv64d-v128-model-converged-0f7b8fb-attempt1/old-new-semantic-comparison.json)显示 819 条 helper PASS 顺序一致，465 条真实指令除耗时外的所有结果字段一致；标量结果 SHA-256 为 `7f6078af2196d8d9a41d526eb0339177a48b652e575a0fafbca6d4acfc81642a`，向量为 `e9e90b0bac48d5951dd7d8831fb5d230f641442d77ed150572820a568782b619`。这只签固定输入的 direct runner 数值、编码和列明状态范围，不计正式 `isarch` JSON 或完整 Clause 预算。[独立验收 Sol](../../review/acceptance/model-converged-results-review.md)已用实际机器字、观察寄存器与归档初态重算 465 条结果，并核 819 条 helper 顺序、来源、seed 和 14 份归档，限定签收本批。
