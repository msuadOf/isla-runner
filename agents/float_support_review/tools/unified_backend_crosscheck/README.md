# P1 共用 helper 三方交叉验证

本目录提供两个 profile。[inputs.jsonl](inputs.jsonl) 是 83 条接线 smoke：归档 D 的 67 个不同 helper 各一例，加 16 个舍入、ROD、NaN、UF/NX、BF16 和整数边界例。[full-inputs.jsonl.gz](full-inputs.jsonl.gz) 是 17,586 条完整数值回归输入，覆盖同一 67 个 helper；解压后每行是相同协议的 JSON。`prepare.py` 从 [D 输入](../d_integration/d_runner/cases.tsv) 与 [定向输入](directed_cases.json) 生成 smoke；`prepare_full.py` 原样调用既有 f16/f32/f64、异常基础及边界用例生成器，按原格式记录来源，并生成完整清单。[input-manifest.json](input-manifest.json) 与 [full-input-manifest.json](full-input-manifest.json) 固定生成器、源文件、输入和 oracle 哈希。既有生成器存储的旧预期只用于来源核对，**不用于三方预期值**。

完整 profile 分布：smoke 83；f16 3039、f32 算术比较 570、f32 转换 3730、f32 边界 1134、f64 807；异常基础 2520、转换基础 2652、算术边界 1350、转换边界 1701。原隔离测试中三条 f16 未知包装、f32 的 48 条内部 ROD 普通候选及 18 条无对应现存 helper 的 signaling Eq 不属于 67 个生产入口，在本 profile 中单列来源后排除。所有 67 名称仍在完整清单内。每例保留具体 RM 与输入位串；完整 profile 含五种 RM、ROD、NaN、整数端点和最终最小正规数的 UF|NX。

三方定义如下：

1. `native` 是独立进程中的 Berkeley SoftFloat [oracle](../../oracle/README.md)。按每例 `oracle_argv` 执行一次原生操作，直接采集原生结果与五位 flags；不用共用 Sail 的 flags 公式，也不调用生产 C++ adapter。
2. `cpp` 必须调用真实生成模型的共用 Sail helper 体；数值 extern 由 P1 adapter 调到 SoftFloat。测试包装要给出进入共用体的运行或生成代码证据。原策略级 `softfloat_*` tuple 绑定不能充当此分支。
3. `isla` 必须调用同一 helper 的真实普通 IR 函数体，记录函数进入 trace、SAT、恰好一条完成路径；对 oracle 已规定的位和全部五 flags 求差异 UNSAT。

三方输出都以原始结果位串和 RISC-V 顺序五 flags 表示。C++/Isla 的完整结果位和五 flags 逐例相等，五 flags 又与 native 独立结果相等。`oracle_bits_rule=full` 要求三方结果位全等；`nan_canonical` 只屏蔽 native FP 原语未指定的 NaN payload，并要求共用 helper 输出清单中的 canonical 位串；`invalid_int_isa` 要求 native NV，且三方 **完整整数结果位** 全等。后者对应 `riscv_fNToI/U*` 的 ISA 饱和值，独立参考使用仓内 SoftFloat 的 RISCV specialization；只在更底层未指定 native primitive 候选内部才允许屏蔽。未标注的 native NaN 输出会拒绝比较，不能静默扩大屏蔽域。布尔比较、ROD、正常数值和 BF16 边界均对完整结果位比较。所有 16/32 位输出严格拒绝超宽高位。

## 准备与独立 oracle 检查

从仓库根目录运行，输出放入空的忽略目录：

```sh
python3 agents/float_support_review/tools/unified_backend_crosscheck/prepare.py \
  --d-cases agents/float_support_review/tools/d_integration/d_runner/cases.tsv \
  --directed agents/float_support_review/tools/unified_backend_crosscheck/directed_cases.json \
  --out .tmp/unified-backend-crosscheck/inputs-rebuilt
cmp agents/float_support_review/tools/unified_backend_crosscheck/inputs.jsonl \
  .tmp/unified-backend-crosscheck/inputs-rebuilt/inputs.jsonl
cmake -S agents/float_support_review/oracle \
  -B .tmp/unified-backend-crosscheck/oracle-build -DCMAKE_BUILD_TYPE=Release
cmake --build .tmp/unified-backend-crosscheck/oracle-build -j 8
python3 agents/float_support_review/tools/unified_backend_crosscheck/run.py \
  --inputs agents/float_support_review/tools/unified_backend_crosscheck/inputs.jsonl \
  --oracle-bin .tmp/unified-backend-crosscheck/oracle-build/oracle \
  --out .tmp/unified-backend-crosscheck/oracle-only --oracle-only
```

`ORACLE_ONLY` 仅表示参考程序接受全部输入；没有共用 C++ 或 Isla 结果，不构成 P1 PASS。运行报告保存 oracle 二进制与输入哈希。

完整 profile 的复现与独立参考检查：

```sh
python3 agents/float_support_review/tools/unified_backend_crosscheck/prepare_full.py \
  --repo . --oracle-bin .tmp/unified-backend-crosscheck/oracle-build/oracle \
  --smoke-inputs agents/float_support_review/tools/unified_backend_crosscheck/inputs.jsonl \
  --out .tmp/unified-backend-crosscheck/full-rebuilt
cmp agents/float_support_review/tools/unified_backend_crosscheck/full-inputs.jsonl.gz \
  .tmp/unified-backend-crosscheck/full-rebuilt/full-inputs.jsonl.gz
python3 agents/float_support_review/tools/unified_backend_crosscheck/run.py \
  --inputs agents/float_support_review/tools/unified_backend_crosscheck/full-inputs.jsonl.gz \
  --oracle-bin .tmp/unified-backend-crosscheck/oracle-build/oracle \
  --out .tmp/unified-backend-crosscheck/full-oracle-only --oracle-only
```

独立 oracle 对 17,586 行均可返回五 flags 与结果位；报告在忽略目录 `.tmp/unified-backend-crosscheck/full-oracle-v3/summary.json`，其自身状态明确为 `ORACLE_ONLY`。比较器的三条专门负控见 `test_protocol.py`，包括两个共用后端给出相同但错误的无效整数饱和值。

## 候选 runner 协议

模型集成者提供两个命令描述 JSON，例如：

```json
{"argv":["/path/to/runner","{inputs}","{oracle}","{output}","{ir}"]}
```

`run.py` 直接按数组执行，不经 shell；`{inputs}` 是本目录 JSONL，`{oracle}` 是本轮独立 native 结果 JSONL，`{output}` 是该后端须写出的 JSONL，`{ir}` 是真实统一模型 IR。命令描述还可含 `cwd`。必须把真实生成 C++ 模型和 adapter 构建命令、源/二进制 SHA，以及 Isla 的源快照/IR/运行时 SHA 附到该轮证据；命令描述只规定运行接口，不证明构建来源。

Isla 一侧可直接使用本目录 [run_isla.py](run_isla.py)：它只在证据目录复制候选 IR 并追加 67 个调用包装，不修改候选 IR 原件；用独立 native 结果构造求证目标，复制归档 D runner 并加全 Concrete MixedBits 规约和实际模型结果输出，从指定冻结 `isla-lib` 离线重建。归档 runner 对每例要求普通函数进入 trace、SAT、单完成路径和完整规定结果位/五 flags 差异 UNSAT。**输出 JSONL 的 `result_bits` 与 `flags` 取自实际 `Model::get_val` 打印的 `VALUE` 行，不能用 oracle 求证目标回填。**脚本只有在逐例 `PASS` 和 `VALUE` 数量、顺序全部正确后才写 JSONL；`<work>/summary.json` 留原始命令、wrapped IR、源码/运行时/二进制及日志哈希。可给 `--isla-command` 使用如下模板，`<冻结isla-lib>`由候选构建者填入：

```json
{"argv":["/usr/bin/python3","agents/float_support_review/tools/unified_backend_crosscheck/run_isla.py","--repo",".","--isla-lib","<冻结isla-lib>","--ir","{ir}","--inputs","{inputs}","--oracle","{oracle}","--output","{output}","--work","{output}.work"]}
```

C++ 一侧使用 [run_cpp.py](run_cpp.py) 和 [生成器](generate_cpp_runner.py)：必须从**同一冻结模型的真实生成头和源**逐名找到 67 个 `Model::zriscv_*` 公开声明与函数体，再生成直接调用全部方法的 runner；任一缺体即停，不能调用旧策略级 `softfloat_*` tuple 入口代替。若原完整 C++ 因 DCE 缺导出，应从**相同冻结 Sail 源**另生成显式保留 helper 的隔离 fixture，并单独记录新生成源哈希，不改正式全模型输入。runner 从真实 tuple `ztup0/ztup1` 输出 flags/位串，按声明位宽拒绝 16/32 位高位污染；`<work>/summary.json` 留方法签名、生成源、编译/执行命令和原始输出哈希。编译链接命令由候选构建者以 JSON 数组提供，使用 `{source}`、`{binary}`、`{header_dir}`、`{model_cpp}` 占位符；此处不猜已有完整模型的链接边界。可给 `--cpp-command` 使用：

```json
{"argv":["/usr/bin/python3","agents/float_support_review/tools/unified_backend_crosscheck/run_cpp.py","--inputs","{inputs}","--header","<同冻生成头>","--generated-cpp","<同冻生成源>","--build-command","<CPP链接命令JSON>","--output","{output}","--work","{output}.work"]}
```

每行输出须有 `id`、`helper`、`result_width`、`result_bits`、`flags` 和 `shared_body_entered:true`。Isla 行另须有 `ordinary_body_trace:true`、`sat:true`、`completed_paths:1`、`oracle_mismatch_unsat:true`；最后一项仅在 `nan_canonical` 中按指定 canonical 位与五 flags 构造差异，其余所有案例均对完整 native 位与五 flags 求差异 UNSAT。比较器拒绝缺例、多例、超宽位、五 flags 分歧以及版本命令失败。两个 runner 的输出只能来自实际候选执行；不得把 `native.jsonl` 复制为后端结果。

候选就绪后运行：

```sh
python3 agents/float_support_review/tools/unified_backend_crosscheck/run.py \
  --inputs agents/float_support_review/tools/unified_backend_crosscheck/inputs.jsonl \
  --oracle-bin <独立oracle二进制> --ir <统一候选IR> \
  --candidate-manifest <统一模型/工具链/运行时manifest> \
  --cpp-command <C++命令JSON> --isla-command <Isla命令JSON> \
  --out <空的证据目录>
```

先对 `inputs.jsonl` 跑接线 smoke；其命令与 runner 源版本固定后，把 `--inputs` 换成 `full-inputs.jsonl.gz` 在新空目录跑完整 profile。两次结果分别报告，不能把 smoke 的通过外推为完整 P1 数值验收。

本包覆盖 67 个现有 helper 的列定具体输入；不替代 97 个 typed FP 声明的闭包、TLS/环境、未知符号输入、完整 ISA 状态或 77 项整指令验收。

## P1 统一模型实测结果（2026-09-27）

隔离 patched Sail 对 v6 模型严格生成 IR `348147f8…`，v7 C++只补缺失的SoftFloat平台构建文件；`cpp-source-v7-bind.json` 已逐文件确认 Sail model 树与生成 IR 的 v6 相同。C++生成头、源中 67 个 `hart::Model::zriscv_*` 方法声明与函数体全齐，runner 直接调用这些普通体。首个C++运行因测试runner在 `model_init` 前漏装配置，`cpp-p1-v7-smoke/summary.json` 明确保留 `FAIL_EXECUTION`；修订runner从同build的 `rv64d_v128_e64.json` 去纯行注释并调用 `sail_config_set_string`，在新目录重建通过。

同源三方汇总在 `.tmp/unified-backend-crosscheck/triple-smoke-summary.json`（83例）与 `triple-full-summary.json`（17,586例），均为 `PASS_HELPER_TRIPLE_PROFILE`、逐项零差异。CPP输出来自实际生成模型tuple；Isla输出来自实际 `Model::get_val`，另有每例普通函数trace、SAT、单完成路径与结果位/五flags差异UNSAT；独立native oracle提供原生五flags。完整组按域分别为14,161例三方结果位全等、1,733例仅native NaN payload屏蔽且共用Sail canonical位核对、1,692例无效整数按RISCV specialization饱和值三方全位核对；全部五flags始终三方相等。

同一17,586输入下，CPP runner的构建/具体执行为1.689/0.064秒，Isla runner的构建/逐例SAT加差异UNSAT执行为18.725/47.140秒。两者验证工作量不同，不计算加速比。新 IR 上旧79接口闭包仍齐，277未知入口与原helper/估算/旧12体/legacy十组回归也已通过；入口见 `.tmp/unified-backend-crosscheck/helper-p1-closure.json` 和 `helper-p1-v7-all/reports/summary.json`。这些结论限于所列helper与具体输入；正式77条整指令及源码分支闭合另验。
