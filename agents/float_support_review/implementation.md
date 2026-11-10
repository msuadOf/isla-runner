# 浮点分层实施记录

## 2026-09-26 启动

用户已确认 [实施计划](plan.md)，本轮开始按 A–E 顺序实施。启动时 Isla HEAD 为 `f4f8e4584a70588c66c9e7a6286cc20211618f18`，Sail-RISC-V HEAD 为 `f8ce8490981eac6396a31013180a2e718615757d`；两个主子模块工作树干净。父仓库 Isla gitlink 仍为 `85d7c70f163aa23febb2e94c541725acd11f70b5`，既有根仓库文档修改保留。旧正式 `isla/rv64d.ir` 的 SHA-256 为 `6fc39efd0f72b0ee8eae247d9965e680b6874f9954334c20d748b42c0987792c`。

工作包边界：A 的 Isla 通用接口由一名 Sol agent 独占；B–D 的 Sail 声明、共享异常和 RISC-V 包装由另一名 Sol agent 独占；BF16 指令文件由独立负责人处理；Luna 初筛 89 项 clause 表，主 agent 复核；Astra xhigh 审定通用接口、异常公式和阶段验收。内存议题在自己的 `isla/.worktrees/memory-consistency` 中实施，浮点主工作树不并行修改其文件。

当前仅已启动契约审查、清单初筛及 A/B/BF16 准备。尚无本轮代码、IR、配置或功能测试结果；下面按阶段追加实际命令、受测版本、结果和未通过项，不预记 PASS。

## B 阶段编译边界的隔离实验

预审曾担心 `isla-sail/sail_plugin_isla.ml` 的 `remove_extern_impls` 会删除带 C++/Lem extern 的同名函数体。用当前 Sail 0.20.1 与 Isla `f4f8e45` 在仓库外临时目录运行最小模型后修订此判断：`cpp`/`lem` 绑定加 `SYMBOLIC` 同名函数体时，Isla IR 同时有 `val zdemo_extern` 和 `fn zdemo_extern`，C++ 输出调用 `demo_cpp`。因此 B 阶段保留现有 C++/Lem 声明并增加符号函数体，不修改插件；67 个正式 helper 仍须在实际 IR 中逐名复核。隔离命令与产物由 Sail 工作包记录，本实验不是正式 helper 通过。

已在临时目录用 CMake 生成 `rv64d_v128_e64.json`，未写 Sail-RISC-V 工作树；正式 B–D 测试 IR 将显式使用该类 V128 配置。

## 并行准备与文件边界

- A：Isla `float.rs` 与 `smt.rs` 的通用接口由独立负责人 TDD；初始红灯为新接口缺注册、具体 BV 被拒、错 sort 触发 Z3 错误。当前定向测试阶段性通过，最终结果待记录。
- B：上述隔离实验证实双后端模式后，授权 Sail 工作包仅在计划分配文件中实现完整 quiet Eq 和不同名、只返回 bits 的加法演示；正式加法 flags 仍属 C。
- D 的 BF16 副作用：独立负责人在 `bfloat16/` 和新增定向 first_party 测试中先取红灯，再修标量 sNaN 于无活动 lane 提前累计 NV 的问题；完整数值和五 flags 仍待 D 验收。
- 89 项清单：Luna 初筛写入 [clause 矩阵](clause-matrix.md)，名称与 `FD_FLOAT` 一致、与 `MEMORY` 交集 10 项；XLEN、扩展及子操作仍须主 agent 对源码复核，全部标未测。

## A 阶段首轮测试与复核（进行中）

在 Isla `f4f8e45` 基线上，通用接口负责人仅修改 `isla-lib/src/primop/float.rs`、`isla-lib/src/smt.rs`。新增 4 个 `to_ieee`、4 个 `to_unsigned` 和一个 BF16 纯数值接口；旧 73 个注册名经主 agent 与 HEAD 集合对照均保留，当前共 82 个。先写测试得到缺注册、具体 BV 被拒及错 sort 导致 Z3 退出的红灯，随后实现类型和输入检查。

首轮命令与结果：`cargo fmt --package isla-lib` 完成；`cargo test -p isla-lib --lib primop::float` 报 30/30 通过；`git -C isla diff --check` 无报错。这只说明该测试筛选范围。Astra xhigh 独立复核又单独运行旧 `f32_add_basic`，复现 `solve_call` 未初始化 tactic 而退出 101；因此 **A 阶段尚未通过**。另需补 unsigned16/64、128 位高位非零、能区分五种 RM 的样本、通用 ITE 符号选择，以及 BF16 的 UNSAT 等价证明。负责人正按这些缺口继续 TDD，旧失败保留在此记录，修复后追加命令和结果。

89 项矩阵的名称顺序经主 agent 独立脚本与当前 `FD_FLOAT` 完全对齐，无缺名或重复；与 `MEMORY` 交集恰为 10 项。扩展/XLEN/enum 映射仍是静态复核材料，尚非功能覆盖。

### 独立 SoftFloat 参考工具

[oracle 工具](oracle/README.md)调用 Sail-RISC-V 随附的 Berkeley SoftFloat C API，固定 RISC-V specialization、舍入后 tininess 及 ROD 选项，逐次重置 flags 并输出完整结果位和五个标志。它不调用待测 Sail/Isla 异常公式。仓库外 CMake 构建成功，`smoke.py` 七组定向测试均通过；受测 Sail-RISC-V/SoftFloat 为 `f8ce849`，CMake 4.2.3、GCC/G++ 15.2.0、Python 3.13.9，oracle 二进制 SHA-256 为 `0bb63bc72889502ef6a36cb739589745987a0788eb73d57e0570815a3c228bc6`。可重复命令见工具 README。此结果只证明参考工具自身的定向样例，不代表共享异常库或指令通过；FCVTMOD、Recip7/Rsqrte7、窄整数包装和无序归约另选规范参考。

### B 最小调用链初轮结果

Sail 工作包保留原 `riscv_f32Eq` 的 C++/Lem extern，在 `SYMBOLIC` 分支补完整 quiet Eq 函数体；加法演示用独立 `demo_f32_add_bits`，没有给正式 `riscv_f32Add` 安装残缺 flags。新增通用原语声明、共享异常结构和项目顺序。隔离脚本 `test/symbolic_fp/check_stage_b.sh` 的 strict Sail 类型检查、IR 函数体/原语检查、C++ `softfloat_f32eq` 检查均退出 0；`run_stage_b.sh` 的 Isla 实际执行覆盖 Eq 的 qNaN、sNaN、正负零等五例、加法两例与 BF16 一例，未知 bits Eq 只有一条完成路径，`trace_functions` 记录进入普通 Eq 函数。全模型 `riscv.sail_project` strict 类型检查及独立 V128 IR 生成也退出 0；生成的 IR 中 `riscv_f32Eq` 有 val+fn，`riscv_f32Add` 仍只有 val。

这批产物使用 Isla `f4f8e45` 加 A 修改、Sail-RISC-V `f8ce849` 加 B 当时源码；共享异常库同时在继续编辑，全模型 IR 只对应其生成时快照。Astra 独立审查和脚本收尾仍待完成，故暂不把 B 标为阶段 PASS，也不将演示加法计作完整 helper。定向命令、生成 IR 的完整哈希和后续复核结果由 B 负责人补交。

### B gate 收尾

B 负责人增强独立 runner：8 组 f32 Eq（含有限相等/不等、正负零、qNaN、sNaN）及 2 组加法先对受限未知输入求 SAT，再对“结果或完整 flags 不等预期”求 UNSAT；未知 Eq、加法各只完成一条执行路径。Astra xhigh 在独立输出目录重跑 `test/symbolic_fp/check_stage_b.sh` 与 `run_stage_b.sh`，strict 类型检查、IR 结构、C++ `softfloat_f32eq` 接线和 Isla 实际执行均退出 0；8 组 Eq 又与独立 SoftFloat oracle 的结果和五 flags 逐项一致。小 IR SHA-256 为 `6b786506a79ca81f4d21677acb6467d00717105c56e958bded818643e6fad7ec`，正式 V128 全模型 IR 的首次生成快照 SHA-256 为 `5d5be7da023ecf36eb3a9fbb9bfdb31030358722e074a1ba9db071ac464ee7d9`。

**B 最小调用链门槛 PASS**，范围仅为 f32 quiet Eq、RNE 的独立 bits-only 加法与 BF16 类型/1.0 小式；C++ 只验证生成代码调用原 SoftFloat extern，Lem 未动态测试。完整加法 flags、其余 66 个外部 helper、全部 C/D 异常和正式 V128 IR 均未验收。生成的全模型 IR 早于共享异常库后续修改，不能拿该哈希作为 E 正式产物。

### A gate 收尾

负责人修复旧 `softfloat_tests::solve_call` 的 tactic 初始化后，原先单独失败的 `f32_add_basic` 变为 1/1 通过。补充 unsigned16/32/64/128 的实际结果、BF16 的 SAT→不等 UNSAT、f128 非零高位与 ±2^127 合法域往返、正负中点的五 RM、Bool/BV/FP/RM 符号 ITE 后，执行以下命令（工作目录 `isla/`）：

```sh
cargo test -q -p isla-lib --lib f32_add_basic -- --nocapture
cargo test -q -p isla-lib --lib primop::float::generic_float_tests -- --nocapture
cargo test -q -p isla-lib --lib primop::float::softfloat_tests -- --nocapture
cargo test -q -p isla-lib --lib primop::float
cargo fmt --package isla-lib --check
git diff --check
```

结果依次为 1/1、10/10、21/21、31/31 通过，格式和差分空白检查退出 0。Astra xhigh 独立重跑单独旧测试及通用测试并复核当前 diff，无阻断项。当前源码 SHA-256：`isla-lib/src/primop/float.rs` 为 `de257e37910d2b5c2312034183a44d3703e73a7b8895e496458326254b4716ba`，`isla-lib/src/smt.rs` 为 `968101d2aabab1ec160499c57b0ddf01e784982abbe770c3a89c68c1887fdea4`。**A 通用接口门槛 PASS；B–E、旧专用 helper flags 和正式 IR 均未因此通过。**

## BF16 VF 累计位置：定向红绿验证

负责人只改 `sail-riscv/model/extensions/bfloat16/zvfbfwma_insts.sail`、`test/first_party/CMakeLists.txt` 和新增 `test_bf16_wma_flags.S`。修复前真实 RV64 汇编测试在 `vl=0`、旧 `fflags=0` 时报 `FAILURE: 2`，CTest 退出 8；修复将标量源改为纯 `bf16_to_f32`，并仅在第一个活动 lane 中累计其 flags 一次。修复后新增测试和已有 NaN boxing 测试均通过（CTest 2/2，退出 0）。新测试覆盖无活动元素、全屏蔽、`vstart=vl`、活动元素、旧 flags 非零、跳过前缀 sNaN 及 VF/VV 行为。

本次构建使用 Sail 0.20.1 (`446fb477`)、Clang 22.1.8、Sail-RISC-V `f8ce849` 的 RV64 VLEN256 C++ 模拟器，配置 `rv64d_v256_e64.json` 的 SHA-256 为 `e28ac77273be6a31c544db6b196914dfb55b3b9fb72295ae7ef6cfc7b99dfc47`；测试 ELF SHA-256 为 `918863ec017c51732a294eddae17685929390d7f6af72f29dfcd054360ecedfa`，模拟器 SHA-256 为 `aa493777b7c0362abc98f7a38d5008b0e3ff1970831e65eeaff9633b22182631`。完整命令和适用范围见 [RESULTS](../../docs/RESULTS.md)。模拟器生成前另一工作包已修改 `riscv.sail_project`，生成后共享异常文件又变化；这些绿灯是上述产物的历史结果，当前联合源码与正式 V128 IR 须复验。

## E 阶段只读预检

正式 RV64 IR 生成须显式使用 CMake 生成的 `rv64d_v128_e64.json`，不可用默认 `generated_isla_rv64d`（其为 VLEN256）。从 `sail-riscv/model` 调用当前 Isla Sail 插件及 Sail 0.20.1，带 `--strict-var --strict-bitvector --strict-exponentials`、四项 `--isla-preserve encdec_compressed_*`、独立 `--isla-output-dir` 和外部 memo 缓存，先生成候选而不覆盖 `isla/rv64d.ir`。D 阶段逐名核 67 个新函数体及 12 个旧函数体、实际进入记录，并在隔离候选禁用旧分发；E 才将正式删除分发、新 IR 与 79 份严格配置同批集成。

现有 [严格配置校验脚本](../v_symbolic_ir_workarounds/verify.py)读取正式 TOML，候选 IR 的哈希/源码坐标先在隔离候选配置中检查；正式集成后还需核对 67 个旧 V region 和 22 个注释锚点，并额外检查新 FD/共享源码受移动影响的区域，不能只替换哈希。RV32 限定的四项 Zcf 与两项 Zfa 需另备 `rv32d_v128_e64.json`、启用 F/D/Zcf/Zfa 的 RV32 配置及合法编码→译码→执行证据；现有 `isla/configs/riscv32.toml` 的 `rv_enable_fdext=false` 不可直接当验收配置。本节是命令/依赖预检，尚未生成正式候选或运行 E 测试。

## D 隔离候选启动

在三个格式文件和共享库停止并行写入后，使用 [D 快照工具](tools/README.md) 将 Isla `f4f8e45`、Sail-RISC-V `f8ce849` 的现有源码修改冻结在仓库外。manifest SHA-256 为 `04b63939dc8e3e35e375d928659c0ae815318a2f1b9e52fdd66351660996982e`；Isla 与 Sail-RISC-V 的 tracked patch SHA-256 分别为 `f9e8aae3c9ff9c3182c91aaafcfbabe7b3741c6be7f5df4d7f4c489bf9c83cd8`、`c290562890f14d7bdb0e332d09a28056f6b697da9b9cf0d8159ce91a2008be42`。两仓各建独立 detached worktree 并逐文件核哈希，未覆盖主源码或正式 IR。

首次全模型 V128 IR 生成约七分钟后退出 2：`--memo-z3-path` 错指已存在目录，Sail 报 `Is a directory`。尽管写出约15 MiB IR，此次**FAIL**，不作为D通过证据。已把参数改为外部缓存目录下的文件路径重跑；正式退出状态、IR哈希、67/12名称检查和禁旧分发动态结果待续记。

## E 访存与 RV32 静态交接

[集成审查](memory-integration.md)在正在变化的内存 worktree 特定快照上确认：89项中10个浮点访存 clause 含 `LOAD_FP`/`STORE_FP` 的H/W/D宽度组合；压缩浮点直接递归执行普通访存，整数压缩的 `ExecuteAs` 续执行修复不能替代其真实读写验证。RV32 `solve-state` 当前无条件 panic，内存数组若按 XLEN32 建立也与模型固定 BV64 物理内存请求不符；区域末端、无合法区域和Concrete写后读边界须由内存议题或联合候选处理。E 的六个RV32限定条目可先用完整RV32 IR的真实编码→反向译码→执行专用 harness 取得隔离证据，不能称公共RV32 CLI通过。全部是静态预检，尚无浮点访存或RV32功能PASS；联合内存源码稳定后重新核对时点与哈希。

## C/D 共享异常库阶段性证据

[精确异常契约](exception-contract.md)规定用原生 FP 定向邻点计算 NX、OF 和舍入后 UF，并对特殊输入单列 NV/DZ。Astra xhigh 用固定 RISC-V SoftFloat 核对关键 f32→f16 RNE 边界：`2^-14-2^-25` 最终为 `0x0400` 仍置 UF|NX；阈值 `U=2^-14-2^-26` 前/等/后点及正负×五 RM 共 80 项与契约相符。源码、探针命令和哈希见契约第 5 节。这是算法边界参考，不是 Isla 新模型功能 PASS。

共享库负责人先让 `ieee_add32_exceptions` 缺失触发严格 Sail 类型检查红灯，再实现 Eq/Lt 和 Add/Sub；第二批让 Mul/Div/Sqrt/FMA 缺失触发红灯，再扩至 f16/f32/f64。strict Sail 类型检查和隔离 IR 生成已通过，生成 IR 含普通共享函数体和原生 FP 调用。外置 Isla 执行 harness 首轮对 SoftFloat 做固定 630 加 seeded random 1800，共 2430 例：非 NaN 结果位及五 flags 的抽样模型值均一致。此轮仍只从每个具体输入的 SMT 公式取一个 SAT model，固定边界样例的“可能不同” UNSAT 检查正在补，因此暂记**抽样差分通过，C/D 验收未完成**。NaN 结果位由 ISA 包装负责，未用原生 ToIEEE payload 作逐位预期。

### 共享库差异证明强化

后续 [算术边界脚本](oracle/boundary_probe.py) 与 [转换边界脚本](oracle/conversion_boundary_probe.py) 已将独立审查构造的样例持久化。固定工具快照上，算术/比较基础 2538 例加阈值、NaN 参数位置和极大指数差 1350 例，共 **3888/3888**；转换/取整/BF16/ROD 基础 2652 例加边界 1701 例，共 **4353/4353**。每例由 SoftFloat oracle 给独立预期，Isla 先确认 SAT，再对五 flags 或非 NaN/有效域结果位不同求 UNSAT。BF16 测试曾把它误按 f16 分类为 NaN，导致部分结果位漏检；修成 BF16 exp8/fraction7 后重新运行，上述 4353 计数只采用修正后结果。Astra xhigh 复核 24 个浮点阈值与 6 个整数界限，并独立重跑；本轮结论只覆盖固定快照、具体输入和具体 RM。工具、IR、样例和结果哈希由两份脚本与本轮会话记录对应，当前动态源码仍在继续变化。

共享库负责人另以真正未知的 f32 操作数和 RM 测 Add/Sub/Div/FMA，在各自有限离散约束内枚举 8/8/8/16 种组合，均先 SAT 后对预期关系取反求 UNSAT，每项只一条完成路径；耗时约 0.95/1.28/8.24/12.17 秒。该证据仅覆盖列出的有限域，不外推全部未知输入。完整 67 个 ISA 包装、正式 IR 和指令状态仍待 D/E 验收。

## f16 包装隔离交付

`softfloat_symbolic_f16.sail` 与原声明白名单 22/22 对齐；strict Sail、隔离 IR 中 22 个普通函数体、C++ Add extern 接线均通过。独立 SoftFloat 差分在补上 `-65520→f16` 的 i32/i64 RUP 固定回归后为 **3042/3042**：839 个固定、2200 个固定种子随机、3 个未知输入受限样例，完整结果位和五 flags 逐项 SAT→差异 UNSAT，均一条完成路径。Astra xhigh 独立重跑并核查 22 根函数的 56 个 Sail 调用闭包，无 Jump/goto 或闭包外 `riscv_*` 调用；隔离 IR SHA-256 为 `74634a7b0912951de12ff13c9a887582d9d4ab7409238586426082bc9b55c158`。**f16 的隔离 helper 差分在上述样例范围 PASS**；未知输入仅覆盖 Add、Eq、i32ToF16 三入口，不能写成22项全符号验收。统一禁用旧分发、正式IR及指令测试仍待 D/E。

## f32 包装隔离交付

`softfloat_symbolic_f32.sail` 的原外部 helper 共23项（含 B 已验 Eq32），隔离 IR 23/23 有普通函数体；完整 Sail 项目严格类型检查通过。f32→f16 的 ROD=6 曾在普通候选求值时违反公共 RM 解码器只接0–4的前置条件；修订为纯 ITE 先将编码6映射RTZ=1再求普通候选，ROD位与异常仍取共享派生函数。隔离 SoftFloat 差分算术/比较 **570/570**、转换/取整/ROD/BF16 **3734/3734**；Astra 另加 BF16阈值、整数边界和ROD候选 **1178/1178** 定向样例并独立重跑。每项完整结果位及五 flags 先 SAT 再差异 UNSAT；23 个未知输入入口各一条 SAT 完成路径。Astra 核对 23 根函数闭包含66个普通Sail函数，无Jump/goto或未定义 `riscv_*` 调用，修后隔离 IR SHA-256 为 `0862c9ba5f461f4148acec70996dd6178aacdb4ce18f4914cd635fecd631650f`。**f32 隔离 helper 在上述范围 PASS**；正式联合 IR、禁旧分发和指令状态仍待 D/E。

## f64 包装隔离交付

`softfloat_symbolic_f64.sail` 的原外部 helper 22/22 有普通函数体；f64→f32 的 ROD=6 在调用公共0–4 RM解码器前，先经纯ITE映射为RTZ普通候选，实际ROD位及异常由共享库生成。Astra要求补的负q/sNaN→四类整数、ROD正负特殊值、负i64边界及roundToInt正负半途五RM/exact开关都已进固定样例。Astra独立重建strict Sail、隔离IR与C++接线并重跑oracle，**807/807**个完整结果位及五flags样例（具体和受限未知输入）均先SAT再对差异求UNSAT；22个helper各一条路径且trace确认进入普通函数。22根函数传递闭包含62个普通Sail函数，无Jump/goto/assert/assume或缺失RISC-V调用；IR SHA-256 为 `6e020ba516c56c873ca199f3be18e46039706c708984007eb66d1065df5dceef`。**f64隔离helper在上述范围PASS**；C++仅检查生成代码的Eq/FMA两个绑定，未动态执行C++，正式IR和指令状态仍待D/E。

## D 完整 V128 隔离候选与 E 启动

两子仓源码冻结于仓库外独立 worktree；详细版本、命令、产物哈希、日志退出码与资源见外部运行记录 `D_RUN.md`，对应目录由本节命令中的输出路径确定。第一次 Sail 生成因 `--memo-z3-path` 误指向目录退出 2，其文件不计入验证；修正后生成退出 0，V128 候选 IR SHA-256 为 `c9e1bfe29e75452568d61fc3b3407e707eb1bd7e48193e212495ec21b885bc75`。`check_d_ir.py` 检查旧 79 声明/12 函数体、候选 88 声明/88 函数体：原 79 项全部有体，另有 9 个纯辅助。

隔离执行器先把旧分发命中变成 panic，后删除旧分发入口；两种状态下 67 项 RNE 具体样例均按独立 SoftFloat 的完整结果位与五 flags 通过，且有普通函数进入记录、一条完成路径。旧 IR 负例先命中 panic、删除后报 `NoFunction`，证明隔离负控制有效。删除后 277 项未知输入/RM 探针（含 ROD=6）逐项 SAT、普通函数进入、各一条完成路径；此项不证明全部未知域的数值等价。原有 12 个函数体通过 39 个特殊值/窄整数 smoke 及另 24 个窄整数范围样例，但 Recip7/Rsqrte7 六项的有限正值独立规范对照仍在补充，**D 全阶段暂不记 PASS**。主工作树的正式 IR、79 份严格配置和旧执行入口此时未切换。

独立参考已锁定 RISC-V V v1.0 public-review frozen 文本提交 `3570f998903f00352552b670f1f7b7334f0a144a`，估算操作位于 §13.9、§13.10；不称最终 ratified 版本。Astra 核查了四个 f32 规范结果，固定 Spike 源码提交 `204b88deda9bcb7537bc09ae5c320f691e8839ef` 的 API 已生成 350 项有限值候选，其中模型抽样值/flags 对照通过，SAT→差异 UNSAT 仍待 D 负责人完成。不会从待测 Sail 查表生成预期。

E 集成人只在仓库外候选清理 Isla 旧专用实现并校验新 IR/严格配置后，才把执行器源码、新正式 IR 和匹配配置同批写回；另一负责人以外部 runner 验证 77 个 RV64 非访存 clause。独立 RV32 runner 已完成严格 Sail 类型检查，完整 probe IR 仍在生成。10 个访存 clause 仍依赖内存议题稳定实现与联合候选真实读写证据。上述 E 项此时均未获得指令级 PASS。

### D 独立参考与严格差异复验

[完整 D 运行记录](d-run.md)固定了两个子仓快照、Sail/Z3/SoftFloat/Spike 版本、生成命令、IR 与参考文件哈希、退出码和资源使用。其早期只取一个 SAT 模型的结果保留为历史；负责人随后改用同一删除旧分发的隔离候选，逐项先确认 SAT，再对“结果位或五 flags 任一不同”求 UNSAT。67 个原外部 helper 的独立 SoftFloat RNE 样例、350 个规范与 Spike 估算样例、1618 个覆盖全部128个正规查表索引及次正规各最高1位置的估算样例、420 个特殊值/符号样例，以及原有12个函数体的39个样例和另24个窄整数边界样例，均在对应清单上通过；每项还检查普通函数进入及一条完成路径。277 个未知输入/RM 探针只证明 SAT、普通函数进入和单路径，不证明任意输入的数值等价。六个 Recip7/Rsqrte7 的参考来自固定 RISC-V V v1.0 public-review frozen 文本及独立 Spike SoftFloat API；有限样例不是全输入形式化证明。Astra 独立核对 IR、runner、向量哈希及日志，并结合当前联合 Sail 源码的 BF16 真实指令复验，判定 **D 阶段 PASS（固定候选与列出的样例范围）**。这不代表 E 的新 Isla IR 完整指令通过。

E 独立候选已清理未调用的旧 Isla 专用实现与其21项依附测试，保留通用原语，并在仓库外完成新 IR 对79份严格配置、132个源码区域、22个注释锚点的校验。一次旧配置的结束列越过源码行尾，候选将其从第293行第7列修为第6列，详情待正式集成记录。清理前浮点模块31/31，清理后通用测试10/10；旧21项中20项含ISA结果/flags断言，需在最终候选用独立参考迁移回归。候选 `isla-lib` 全库253项中的 `smt::tests::get_multi_member_enum_const_after_checkpoint_replay` 因 Z3 enum sort 重名失败；同一测试在干净 `f4f8e45` 基线也失败，属于既有基线问题，完整测试套仍如实标 FAIL。正式主入口尚未切换。

### D 验收材料归档

[可复用验收源码与向量](tools/d_integration/README.md)已归档：runner、独立 Spike API 调用源码、350/1618/420 三组向量与生成器保持原哈希；三组用固定 Spike oracle 重生后逐字节一致。候选 IR、二进制与原始构建日志仍在仓库外。外部 Cargo 清单生成脚本的 `fmt --check`、离线 `check`、离线 `build` 均通过。

### 当前联合 Sail 源码的 BF16 真实指令复验

独立构建目录中的 RV64 C++ 模拟器及两条汇编 ELF 均成功生成；源码包含共享异常库与 BF16 活动元素修复。固定 V256 配置的 `first_party_rv64d_test_bf16_wma_flags.S` 和 `first_party_rv64d_test_bf16_nan_boxing.S` CTest 为 2/2、退出0；同一模拟器及 ELF 显式加载 V128 配置分别输出 `SUCCESS`、退出0。Sail 0.20.1，Sail-RISC-V HEAD `f8ce849` 加当前工作树修改；修复文件、共享库、项目文件、模拟器、两配置和两 ELF 的 SHA-256 以及完整命令与日志保存在仓库外复验记录。**当前联合 Sail 源码下这两条 BF16 C++ 指令测试通过**，仍不能代替新 Isla IR 的 BF16、mask/vstart 和全89项指令验收。

### E 候选的旧测试映射与 RV32 隔离入口

清理 Isla 旧专用实现时删除的21项依附测试中，一项只验证旧分发的私有名称/tuple 形状，已由 D 的旧IR缺体负控制替代；其余20项包含数值或五flags断言。E 集成人按原始输入用独立 SoftFloat 生成35条结果位/五flags向量，连同映射、生成器、runner和测试说明保存在 Isla 候选 `test/softfloat_legacy/`。在删除旧分发的 E 候选上，35/35先SAT、再对完整bits/五flags差异求UNSAT，并检查普通函数进入及单路径；正式主入口切换后仍须复验。`isla-lib` 的 Z3 enum 测试在干净 `f4f8e45`、独立 Cargo 目标目录和相同 Z3 4.16.0 下重编译仍报同名sort，因而完整套件为既有单项FAIL，不能记全库PASS。

RV32专用配置和完整IR在隔离目录生成。六个限定 clause 的真实16/32位编码经 `ext_decode` 或 `ext_decode_compressed` 反译与构造器/字段匹配；其中 `FMVH_X_D`、`FMVP_D_X` 在完整IR执行 `RETIRE_SUCCESS`，分别检查整数写回、双精度浮点写回与初始 `fflags=1` 保持。每项的两条可行路径均先SAT，再对写回位或任一flags不同求UNSAT；Astra核对 runner、validator及最终manifest哈希后认定**两项 Zfa 的隔离具体指令样例PASS**、四项 Zcf 的合法译码PASS。四项 Zcf真实访存与内存前后状态仍未测；公共 RV32 `solve-state` 仍会 panic，本隔离入口不证明它可用。

### E 正式浮点入口联合切换及首次回归

集成人先在独立候选完成清理、旧数值回归和严格配置校验，随后把 Isla `float.rs` 的通用接口清理、`executor.rs` 旧专用分发删除、新 `rv64d.ir` 和79份严格配置及 `test/softfloat_legacy/` 同批复制到主工作树。正式 IR SHA-256 为 `c9e1bfe29e75452568d61fc3b3407e707eb1bd7e48193e212495ec21b885bc75`。官方严格验证脚本在主工作树通过79份配置、67个其关注的旧V源码region和22处锚点；额外候选检查覆盖全部132个region。旧 `vmsof_m.toml` 的结束位置 `(293,7)` 越过源文件第293行的合法末列，修为 `(293,6)` 后验证通过。`cargo fmt` 和三仓差分空白检查无误。

主 Isla 的 `cargo test -q -p isla-lib --lib primop::float` 为10/10；保存在 `test/softfloat_legacy/` 的35条独立 SoftFloat 旧断言迁移回归仍为35/35，逐项SAT→完整bits/五flags差异UNSAT、普通函数进入、单路径。当前通用模块10项是删除旧专用实现及其21项依附测试后的测试数；不能拿旧31/31直接标记当前源码的结果。主 `make solve-FCVT_S_BF16 THREADS=1 OUTER_TIMEOUT=60s SOLVE_TIMEOUT=55s SMT_TIMEOUT=30s TASTIC=qfaufbv` 退出0，日志有36条 `Retire_Success`；同资源参数的 `make solve-MRET` 退出0，三条 `Retire_Success` 可见。两个命令只证明其本次生成路径，FP smoke 不能代替 BF16 状态正确性或89项验收。主 `make solve-FLI_S` 尚未重跑，独立候选同IR/源码/配置时此项退出0。

普通 `make solve` 使用命令 `timeout --signal=TERM --kill-after=5s 60s make -j2 solve THREADS=1 OUTER_TIMEOUT=60s SOLVE_TIMEOUT=55s SMT_TIMEOUT=30s`，默认 `ACTIVE_ALL` 共220项且排除 FD_FLOAT 89项与 MEMORY 48项。外层65.05秒后退出137；本轮只启动九项，七项生成完成状态，另两项无完成状态。**整组未通过、剩余未测**；不把限时中七项的局部结果外推到220项。`isla-lib` 全库的既有 Z3 enum sort 重名失败同样持续记 FAIL。主入口新 IR 的77个RV64非访存、四个RV32 Zcf访存及其他访存项还在独立验收，E阶段未完成。

### E RV64 非访存 77 个 clause 的首批真实编码样例

[浮点/BF16/ROD及活动元素证据](tools/e_nonmem/RESULTS.md)在禁旧分发的完整 V128 IR 上保存35条证明记录、去重34个定向样例，覆盖10个 clause 的部分子操作；BF16 VF 标量 sNaN 的 `vl=0`、全 mask=0、`vstart>=vl`、活动lane、旧 flags 为0和非零，以及跳过向量前缀均有独立写回/flags预期。`VFNUNARY0` 明确实例化 f32→f16 与 f64→f32 两种 ROD 窄化。故意改错 FADD.S 写回的负控制使差异查询 SAT 并退出101。稳定 runner 二进制 SHA-256 为 `bd362465a970a623b561680ae45e15d7ea0e28b4836dc2c439c3e981fc228425`。

[其他向量20项](tools/e_vector_cases/README.md)以固定 runner 再验证22/22具体样例，包括两条 NX 定向样例；[其他标量47项](tools/e_scalar_cases/README.md)的主批50/50及 FMINM/FMAXM 的18/18额外 NaN/±0 状态样例通过。三包在相同 IR 哈希、配置及 runner 哈希下，每条样例均从真实机器编码进入 `zext_decode`，核反编码与 constructor/字段，`zexecute` 只一条 `Retire_Success` 路径；先确认SAT，再对目标写回及完整 `fcsr`/`mstatus` 等独立预期求差异UNSAT。标量首轮43/50、七项失败是 FLI 汇编立即数解释及 `mstatus.SD` 预期遗漏；原始输入和日志保留，修订预期后第二轮50/50通过。根目录独立核对三包 clause 集合为47+20+10、两两无重叠，恰等于[89项矩阵](clause-matrix.md)去掉10个MEMORY项和两项RV32限定Zfa后的77项，**77个RV64非访存clause各至少一个具体编码样例PASS**。

上述77项结果只证明所列子操作、RM/SEW/VL/LMUL及具体初态。一个类型化 clause 往往含多个子操作；特别 `VFNUNARY0` 的其余7个enum、向量其他宽度与mask/vstart组合仍未由“clause名已触达”自动通过。整体E目标仍有这些子操作、普通 `make solve` 完整回归、10个真实访存及公共RV32入口限制，不能记E全阶段PASS。

### E 浮点非访存子操作扩展

上节是77项各一具体样例的初版快照，后续各包在相同 V128 IR 与固定非访存runner上扩展：`VFNUNARY0` 的8个enum×合法SEW共20格逐项通过，另补五RM、ROD、整数越界、BF16舍入/NaN/活动状态和非法FRM定向例，累计129条成功记录及9条非法状态保持验证，见[重点包](tools/e_nonmem/RESULTS.md)。[FVVTYPE专属包](tools/e_fvvtype_cases/RESULTS.md)的9个enum×SEW16/32/64共27例及24个IEEE边界例通过，Astra独立核对输入/证明和负控制。其他向量包的80个enum×合法SEW 215格及四种固定编码×三SEW 12格在227条基础样例中通过；49条状态与564条RM路由例也已定向通过，Astra复核其预期来源、完整写回、flags、mstatus、mask/vstart辨识及最终证据一致性，见[向量证据](tools/e_vector_cases/README.md)。标量包初版50+18后又补齐类型化90/90个enum、FLI三格式96/96个索引、RM路由169/169、状态边界76/76及非法RM/FRM30/30条，所有证据与失败历史已固定归档，见[标量证据](tools/e_scalar_cases/README.md)。这些仍是列明输入域，不推断所有特殊值全域。


## 范围修订：独立内存分支不纳入本任务

2026-09-26 用户明确要求浮点任务只处理浮点支持，不修改、集成或继续调度 `isla/.worktrees/memory-consistency`。之前一轮把独立内存候选及浮点访存RAM样例并入E的验收叙述，容易误导；相关正向结论已从本议题状态、动态索引和全仓摘要撤回。原始内存worktree及仓库外实验产物不由本任务清理或回滚，但不计入浮点PASS。当前E验收以77个RV64非访存clause、两项RV32 Zfa非访存样例和浮点模型/IR/配置为准；10个访存clause仍标未验收，留待独立内存议题自行处理。

### 浮点官方入口非访存有界回归

从当前主 Isla 精确复制浮点源码、正式 V128 IR、79份严格配置及运行脚本到仓库外隔离目录，明确排除 `.worktrees`；主/副本共86个受测文件逐字节一致，IR SHA-256 `c9e1bfe29e75452568d61fc3b3407e707eb1bd7e48193e212495ec21b885bc75`。固定清单为 `FD_FLOAT` 89项扣除与`MEMORY`交集10项及RV32-only两项，共77个RV64非访存clause。`THREADS=2`、`OUTER_TIMEOUT=60s`、`SOLVE_TIMEOUT=50s`、`SMT_TIMEOUT=5s`、`TASTIC=qfaufbv`，首批八项逐项运行原 `make solve-X`，均退出0且有真实编码对应的 `Retire_Success` 路径：`FCVTMOD_W_D` 46/46完成/退休，`FCVT_BF16_S` 36/30完成/退休且6条Illegal，`FCVT_S_BF16` 39/36且3条Illegal，`FLEQ_D` 6/6、`FLEQ_H` 16/16、`FLEQ_S` 16/16、`FLI_D` 32/32、`FLI_H` 32/32。八项无Unknown/timeout；具体耗时/RSS及日志由独立批次证据保存。此结果只证明官方入口对所列配置和枚举路径可运行，不把退出0或退休数当成数值语义PASS；其余69项仍在同一冻结副本上有界执行。


## 2026-09-26 接续实施与类型复用调整（进行中）

用户再次授权按现有计划完成实现，并要求架构/语义由 Astra xhigh 审定、检索由 Luna 初筛、明确边界后由 Sol 实施。本轮复核确认 A–D 主体已存在于实际源码，不重新实现历史已完成项。随后用户要求 IEEE 层更多复用 Sail-RISC-V 已有类型体系；最终 IR 集成暂缓，先审查已有浮点类型、分解/分类函数、异常表示与新增共享层的重复，再确定实现边界。

- M09：四个未使用旧比较辅助的限制注释已补齐，并说明 quiet/signaling 选择及新旧返回元组顺序；只替换空白行，代码及行号不变，Astra 静态复核通过。
- BF16 新红例：旧正式 IR `c9e1bfe2…` 执行真实编码 `0xee80d257`、`vtype=0xb`（e16,m8）时，在 VF 路径合法性检查前触发 LMUL 断言，runner 退出 101。按已有 `illegal_fp_variable_width` 应返回 `Illegal_Instruction`。源码已将 VF 断言移至合法性 guard 后，保留 VV 原断言和此前 flags 修复；新 IR 及动态绿灯待完成，不能记修复验收 PASS。
- `smtperf` 测试修复：旧三参数宏调用在 `--features smtperf` 编译失败（退出 101）；补齐 `SourceLoc` 并使用真实 Z3 Context 后，`smtperf` 与 `smtperf,smt-thread-interrupt` 两组各 4/4 通过，格式化和差异空白检查通过。只改该测试，不改 SMT 求解语义。
- 官方批次继续沿用旧 IR 的冻结副本，结果与后续新 IR 分开记录。独立内存分支不在本轮范围。


### 类型复用审定与实施边界

两名 Astra 已审定[类型映射](type-reuse-review.md)和[架构取舍](type-reuse-architecture.md)，并将调整写入[计划](plan.md#2026-09-26-接续调整复用已有-sail-类型)。本轮复用已有 `fp_exception_flags`、`float_bits`/`float_decompose` 和内建 `float_rounding_mode`，替换新增 record、按格式重复分类和重复 RM 别名；原始数值计算、异常公式及 ROD 保持原职责。共享 flags 与 ISA flags 位序不同，保留唯一转换边界。既有原语绑定出口不裁剪，BF16 不按 binary16 解码。

最小严格编译探针通过，三个真正未知 bits16/32/64 分类入口均 SAT、单完成路径。该结果只证明复用接口可编译及探针不新增数据分叉；实际类型迁移、32种 flags 组合和完整新 IR 的验收由后续记录给出，不能从探针外推。


### 类型复用候选与定向动态门槛

模型严格检查退出0；Astra逐操作对照确认58个保留函数及34处异常构造表达式只做已授权的表示转换，三个格式包装一致，190条Sail绑定保留。冻结165份模型文件生成V128候选退出0，候选IR SHA-256为 `361980eac11c52d06d940a552b0b6144777461f47d104315ea7df86e088f67cd`。去除SourceLoc并对自动参数名做保持同一性的重命名后，120个浮点函数及 `zexecute` 有变化；后者变化仅为BF16 VF合法性检查/断言顺序。其它函数差异由编译生成参数名变化解释。

类型专包32种flags组合、每格式12分类特值和1个未知输入均通过；固定算术738例和转换/ROD 2652例的差异UNSAT检查通过：五flags全检，共享IEEE层跳过NaN结果位，转换组另跳过NV时FP→int的未指定结果位；ISA规范NaN和无效整数返回仍由完整包装门槛检查。新完整候选的BF16 LMUL专包10例退出0，修前断言红例现按预期返回非法指令，并检查状态保持；合法m4边界仍通过。当前Sail源码重建C++后，两项既有BF16测试在V128均SUCCESS、V256 CTest 2/2通过；该C++组不含新LMUL8编码，不混同两组覆盖。

完整候选helper、277未知入口、非访存指令和严格配置验收仍在进行；上述通过不代表正式IR已切换或E全阶段完成。


### 首个类型复用候选的未知输入性能门槛（未通过，暂停切换）

`361980ea…` 候选已完成24组、1509条具体状态样例，覆盖77个RV64非访存clause；67个helper及估算/旧体具体样例也通过。但277未知入口首组f16前5个Add舍入样例耗时约325秒，远慢于D历史同runner的90项约5.47秒；该性能信号不能由具体样例PASS抵消，正式IR未切换。

Astra审定先做外部单因素A/B：保留 `fp_exception_flags`、泛型分类及所有异常公式，仅将 ITE/OR 构造换为五个Bool转bit后拼接、getter换固定bit读取、ISA出口直接反序。32组合语义、未知域与SAT门槛不变；独立复测旧候选与新候选以确认因果。只有资源门槛恢复且语义验证通过，才应用进一步优化并重生正式候选，详见[架构审定](type-reuse-architecture.md)。


### 表达式B对照与局部表示C候选

同一最小D项目、同一unknown runner及 `f16Add_rm3` 输入：首方案A为67.28秒，直接位拼接方案B为48.38秒，均SAT、单路径。独立旧完整IR同入口为5.04秒（包含完整IR解析）。B仅改善约1.39倍，未恢复原有资源表现，不应用主模型、不生成其正式全IR。

按Astra进一步审定，继续外部C对照：复用 `float_bits`/`float_decompose` 和内建RM，内部异常公式保留局部五Bool事实结构，仅在结果边界转换为既有 `fp_exception_flags` 再映射RISC-V flags。用户要求是更多复用已有体系，并不要求所有内部中间值都打包成位串；是否采用C仍以同形旧基线及未知输入测量为准。此阶段主模型与正式IR尚未切换。


### C1 类型复用边界收敛

C0保持泛型分类/native RM和异常公式，仅内部保留五Bool事实，`f16Add_rm3` 小IR同runner为0.05秒；C1进一步在最终出口转换成既有 `fp_exception_flags` 后映射ISA，仍为0.05秒。C1同形小IR全部90个f16未知入口为90/90、SAT/单路径/trace通过，wall0.61秒；32种异常组合及36分类/3未知分类探针亦通过。对比支持中间异常事实反复位串化是本轮回退因素，不据此断言具体Z3内部热点。

最终实现采用C1：局部事实构造命名 `ieee_exception_facts`，共享库负责 `ieee_pack_shared_flags`，FD包装只负责RISC-V位序转换。保留泛型 `float_bits`/`float_decompose` 和内建RM复用。首个A候选与B方案留作实验记录，未进入正式IR。最终全模型候选仍须重生并跑277未知入口及指令回归，不能以小IR90项代替。


C1主模型严格检查、类型专包与隔离异常差分已完成：类型IR `66f5cda3f7d3823703627be9562e46a70186f723276861511e8b0cdfe6461d04`，异常IR `b33b8f4f1f4ae6a95061aac56dcba94026b084ecc2530f44622aef1e0f07ed41`，共享源码 `d80c4aabcc40f6c0de5aad439aab24a012de51a98ec1a3669ff4a52a781c9bf6`。32+36+3合同、738算术、2652转换/ROD分别通过；Astra已独立核对日志/哈希。共享层差分仍跳过未指定NaN位及NV的FP→int返回位，ISA返回策略由最终完整包装/指令验收补齐。这些结果属于现行C1，区别于先前A候选的同数量历史批次。


### 最终完整C1候选 d0123541 的验收

冻结165份模型文件的manifest为 `1458881ee1154470f33c7c5d1f4ec103fea60c4cddf7cf72e76ea56509700450`，与当前源码逐文件一致；Sail生成退出0，V128最终候选IR为 `d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409`。Astra独立归一检查：原2052函数变为2049（新增12、删除15），仅70个浮点函数及BF16局部execute发生预期变化，其余类型/全局/保留声明不变。

最终候选优先重跑277个未知入口：f16 90/90、f32 96/96、f64 91/91均SAT、普通函数trace、单完成路径，分别5.25/5.31/5.25秒；首候选A的耗时回退未在最终C1完整IR复现。67个原外部helper、估算350+1618+420、旧12体39+24及35条legacy全部完成对应SAT→完整结果位/五flags差异UNSAT门槛。静态闭包152函数，无缺体/throw/assert，唯一分支入口为已知位宽选择的float_decompose。

BF16 LMUL专包10/10在此最终IR通过；候选79严格配置、132源码region和22锚点检查通过。剩余非访存矩阵和主树同批切换结果见后续，不将尚未执行的正式入口写为PASS。


最终非访存矩阵24组1509/1509、clause集合77/77通过，摘要SHA-256为 `9f4fccb7c3fb973afbee2dd491e4c56f2135d556b35f6ad590f957628d7396f5`；Astra逐项核对输入输出、SAT/差异UNSAT及版本绑定后放行。主 `isla/rv64d.ir` 与79份配置已同批切为 `d0123541…`，切换后通用浮点测试10/10通过，`make solve-MRET` 和 `make solve-FCVT_S_BF16` smoke均退出0，分别记录3/36条Retire及1/3条非法路径。主入口精确参数/退出码和配置复核见[最终IR记录](ir-refresh.md)。

本轮完成的是现有实施计划范围内的类型复用收敛、已确认缺陷修复及上述定向门槛；普通make solve全组、旧官方77的超时项、公共RV32入口和10访存不宣布通过。全库既有Z3 enum失败未改。已有未提交修改保留，未提交代码、未移动gitlink、未进入或集成独立内存worktree。
