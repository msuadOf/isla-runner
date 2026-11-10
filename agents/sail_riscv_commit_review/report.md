# Sail-RISC-V 现有改动的提交边界审阅

2026-10-16：用户授权后已在独立worktree实际完成23个更细的功能提交，原工作区保留；当前状态以 [实际提交/验证/文件索引](commits-20261016.md)为准。以下14批仍是历史提案，不是最终commit数量。

2026-10-15 接续：当前版本和完整暂存补丁哈希仍与本报告相同；新增 [逐 commit、逐文件说明](file-details.md)，覆盖151件非缓存文件、12件排除项及共享文件的hunk边界。以下功能检查仍是2026-10-14记录，本次未重跑。

日期：2026-10-14。结论：适合按目的拆分，不能直接提交整个现有索引。建议按下列 14 个单元审阅；这是供用户选择的方案，尚未实施拆分，也未证明每个中间候选独立构建通过。

## 受审状态

- 分支 `feat/isla-workarounds`，HEAD `4f2ac293654a02db26dac5055be7f93fd6e3141e`，等于父仓库 gitlink。该 HEAD 已包含 workaround 配置迁入及基准 IR 哈希绑定，不重复作为新批次。
- staged：163 文件，24 修改、139 新增，19,398 行新增/414 行删除；unstaged 与 untracked 均为空。新增行数包括三个 Rust lockfile 的 3,280 行，不全是生产逻辑。
- 分布：`.gitignore` 1、`c_emulator/` 8、`dependencies/` 1、`model/` 27、`test/` 126。测试中有 12 个 Python bytecode 文件；排除后待分类源码/文档/锁文件为151件。
- `git diff --cached --binary` SHA-256：`47ce7fb311f727f6ff976a40206b7eeb448ca8876f8e700a98eb52a67fc86b69`。未暂存 binary diff 为空。审阅前后复核上述边界。

本报告的代码路径均相对 `sail-riscv/`；父仓库证据链接使用对应相对路径。[文件清单与批次映射](inventory.json)覆盖163个路径；同一文件可属于多个提交，映射不等于已经形成补丁。

## 建议提交顺序与审核重点

### C01 `chore(gitignore): 明确构建产物和测试缓存边界`

仅 `.gitignore`：添加 Rust target、Python缓存、虚拟环境、编辑器文件，扩大根 build 目录匹配，取消原 `/.*/` 的隐藏目录一概忽略规则。

这是维护性调整，但取消 blanket ignore 会使以前隐藏的本地目录变得可见，需要确认这是期望。12个 `.pyc` 已经进入索引，新 ignore 不会自动使其退出索引；实际拆候选时应排除，原文件无需删除。Cargo.lock 为可复现依赖信息，不与缓存一起丢弃。

### C02 `fix(assembly): 修正 FLI 常量和 BF16 汇编文本`

范围：`FD/zfa_insts.sail` 的 FLI 声明、三处 assembly 映射和末尾32项常量表；`bfloat16/zvfbfmin_insts.sail` 两处多余分隔符；`bfloat16/zvfbfwma_insts.sail` 两处缺失逗号；加 `test/assembly_text/{README.md,check.py}`。

实际变化例如 FLI 从表索引打印为标准浮点立即数；BF16 正确输出寄存器分隔及可选 `v0.t`。H格式索引29的 `65536.0` 与30的 `inf` 虽得到相同值仍保留不同编码。本轮当前源码真实回归104/104文本和LLVM编码、32/32 FLI往返通过，是最适合优先提出的小提交。提交时只抽取这些 hunks，不带同文件的 min/max、BF16 执行逻辑。

### C03 `refactor(symbolic): 提供公共 ITE 和严格布尔接口`

从新增 `model/prelude/ieee_fp_primops.sail` 中先提取最后四组 `ite`、`strict_and_bool`、`strict_or_bool`、`isla_bool_to_bit` 声明/普通 Sail 函数体，以及 `model/riscv.sail_project` 的 prelude 文件注册。该中间版本只含通用部分，C08 再补入FP/RM声明，最终文件可保持当前内容。

这是函数级拆分的关键：C04的 `accrue_fflags`、C06的 NaN ITE、C07的 matcher 等使用这些接口；不能把依赖留在后面的浮点大提交。Isla 侧仍须有对应 c extern 支持；普通 C++ 使用 Sail 函数体。需要双模式类型检查及小接口生成/执行，当前未制作精确候选。也可将公共接口和相关修复合并，但不宜复制临时声明到各使用文件。

### C04 `fix(FD): 恢复快速浮点寄存器访问的状态语义`

`model/extensions/FD/fdext_regs.sail` 的 getter/setter 和 SYMBOLIC `accrue_fflags`，加 `solve_fd_state_runner.rs`、`solve_fd_state_probe/`、`solve_fd_state_equivalence.py`。排除该文件开头 `nan_unbox` hunk，归C06。依赖C03；若希望更细，可将 getter/setter 与 `accrue_fflags` 分成两个提交。

快速读取补回 Ext_F guard 和寄存器表示转换；快速写回补回表示转换、写回callback、FS/SD Dirty。flags累计通过ITE选择状态，保留flags无变化时不触发Dirty的条件。此处含正确性修复和等价表达式改写，审核重点是回调次序、FS初态、RV32/RV64 SD位、F/Zfinx域。旧直接状态证据见[FD记录](../float_support_review/solve-fix-fd-state.md)，不转记为精确新候选PASS。

### C05 `fix(V): 补齐快速向量寄存器写回的 Dirty 和回调`

`model/extensions/V/vext_regs.sail` 两个快速setter，加 `solve_vpr_state_runner.rs` 和 `solve_vpr_state_probe/Cargo.toml`。快速写后执行 `dirty_v_context()`、`vreg_write_callback()`，恢复普通写臂副作用；与浮点数值后端无直接依赖。

可独立审阅、优先验证。覆盖VS Initial/Clean/Dirty、同值/异值、v0/v31及其他寄存器保持；旧48次直接调用结果见[VPR记录](../float_support_review/solve-fix-vpr-state.md)。其Rust runner依赖兄弟 `isla/isla-lib`，属于本工作区集成测试，独立 clone Sail-RISC-V不能直接运行。

### C06 `perf(FD): 用位运算和 ITE 表达取负与 NaN unbox`

`fext_insts.sail`、`dext_insts.sail`、`zfh_insts.sail` 的 `negate_*` 仅符号位 XOR；`fdext_regs.sail` 的 `nan_unbox` 内层从if变成 `ite(eq_anything(...))`。带 `solve_decoder_layout/` 中 negate fixture/runner；nan_unbox对应证据在[IR生成接续](../float_support_review/solve-fix-ir-generation.md)。依赖C03。

这些是降低数据分叉的等价改写，不是浮点运算实现。需要证明包括±0、NaN sign/payload在内的完整位串等价；不要宣称带来全指令求解收敛。`fext_insts.sail` 新增的两条旧helper缺陷注释应明确是文档，不能表述为已经修复旧helper；可随本批保留，或另归文档清理。

### C07 `perf(decoder): 显式匹配 AMO 和向量编码布局`

`A/zaamo_insts.sail` 的 AMO布局；`V/vext_arith_insts.sail` 的 VMVR/VEXT子字段membership和完整tuple布局；`V/vext_fp_insts.sail` 四组unary子字段matcher。测试为 `test/solve_amo_layout/`、`solve_mapping_matches/` 与 `solve_decoder_layout/` 的layout部分。依赖C03。

目的是先匹配整字固定字段和合法membership，减少不相关指令的符号译码分叉；普通分支及外层 `when` 需维持语义。建议内部按 AMO、VMVR/VEXT、FP unary 再拆三份，尤其AMO可独立接受。验证必须含非法opcode/子字段、E寄存器域、反解完整payload、重编码与真实 `when` guard调用顺序；小fixture的sentinel guard不替代生产guard。旧证据见[layout/negate](../float_support_review/solve-fix-decoder-layout-negate.md)、[mapping](../float_support_review/solve-fix-mapping-matches.md)。增加V文件行数会影响workaround，接入使用时需同步坐标。

### C08 `feat(float): 共用 Sail 浮点与 IEEE 异常语义并接入 C++ 后端`

这是主要依赖组，应一起评审：

- prelude文件剩余FP/RM原语声明；`core/ieee_fp_exceptions.sail` 的五异常事实与转换/ROD规则。
- `FD/softfloat_symbolic.sail`、`softfloat_symbolic_f16/f32/f64.sail` 的共用函数体；`core/softfloat_interface.sail` 移除67个接口的cpp直连映射；project相应注册。不含fp_minmax注册，留C09。
- `c_emulator/sail_softfloat*` 七件适配文件、emulator和model的CMake接线、SoftFloat CMake的TLS/公开ABI宏；旧 `riscv_softfloat` 仅为EXCLUDE_FROM_ALL测试oracle目标。
- `test/ieee_exceptions/`、`test/symbolic_fp/` 顶层格式/转换/类型复用测试、`test/rv32_fp/` 的适用部分；失效历史入口先修复或明确归档，不能直接把目录整包计为当前回归。

最终结构是C++调用SoftFloat求数值、Isla调用Z3 FP，而flags和RISC-V策略共用Sail。文件名/注释虽仍写 SYMBOLIC，共用体现已不只在SYMBOLIC生效；当前公共包装文件“保留C++ SoftFloat直连”等注释及早期测试期待需要更正。

不能只提交新Sail函数体：保留cpp extern映射时C++仍绕过共用语义；先移除映射又不带adapter/构建接线则可能构建失败。TLS宏涉及SoftFloat声明/定义一致性，也应同批。FP128/宽整数支持是异常计算及公开原语合同的一部分，不能仅因ISA主要使用f16/f32/f64就删除。

**外部前置条件**：完整C++需要补丁版Sail C++ FP/RM lowering。补丁在父仓库 `agents/float_support_review/tools/unified_backend_p0/compiler.patch`，不是本次Sail-RISC-V暂存文件；构建入口与证据见[统一构建](../float_support_review/unified-backend-build.md)、[统一方案](../float_support_review/unified-backend-plan.md)。Sail-RISC-V commit不能单独固定此工具链或Isla实现。应先决定补丁的持久交付与工具链选择，再把本批称为可复现提交。

可以把未启用的声明/adapter先铺底、后切换，但必须逐层构建；不建议按f16/f32/f64机械切分，跨格式转换及异常公式互相依赖。历史67helper及17,586输入等限定证据可作为复验清单，本轮没有重新运行这些数值验证。

### C09 `refactor(FD): 复用纯 min/max 规则并迁移标量调用`

新增 `FD/fp_minmax.sail` 及project注册，替换H/S/D六条FMIN/FMAX、Zfa六条FMINM/FMAXM，替换V工具的fp_min/fp_max内部重复规则。依赖C08（`ieee_is_nan`和共用浮点接口）。与C02共用zfa文件、与C06共用三个标量文件，须按函数拆。

审核NaN/sNaN、±0、flags及返回元组次序；普通C++也改用新helper，不能写“普通后端不变”。`solve_scalar_minmax/verify_source.py` 仍要求SYMBOLIC/ordinary双体，当前生产已统一，因此源码检查器不适用；本轮通过HEAD控制输入复现首个结构断言 `('fext_insts.sail', 0)`，这不是旧冻结版本的语义对照。更新测试后再签本批。

### C10 `fix(V): 区分普通浮点与整数转换的 SEW 合法域`

`V/vext_fp_utils_insts.sail` 的 `valid_fp_standard_op`、`illegal_fp_standard_variable_width` 及相应调用：普通浮点/归约拒绝SEW8，保留允许INT8的宽窄转换。`vext_fp_insts.sail` 的普通/SYMBOLIC宽化调用调整，BF16四条execute增加SEW16检查、VF扩大LMUL断言放到Illegal guard之后。

这是合法性行为修正，须与C11的等价Bool改写分开判断。审核直接execute时非法状态是返回Illegal还是assert，以及SEW8合法转换未被误杀。依赖C03；精确拆法需普通与SYMBOLIC完整类型检查。`test/solve_fp_legality/` 当前只覆盖早期四函数等价替换，不能证明此批新增合法性语义。

### C11 `perf(V): 用纯布尔条件与掩码接口减少辅助分叉`

`vext_control.sail::assert_lmul_pow` 的option(int) membership；`vext_utils_insts.sail` 的valid_vtype/valid_rd_mask/valid_reg_group和SYMBOLIC init_masked_source；FP工具中的纯Bool条件和归约vstart等价表达式。依赖C03，若沿用当前含新标准合法性函数的版本则在C10之后。注意保持合法性变化属于C10，不掺在本批。

option(int)包裹后走通用相等接口是有意的符号执行结构选择，不是无意义包装；掩码快速接口需确认Isla实现存在及禁用开关的fallback。测试为 `test/solve_fp_legality/` 的更新后版本，LMUL/valid_reg_group已有候选证据及reduction相关IR核对。当前build_probe先因四函数外源码变化退出1，不能声称现行回归已过。

### C12 `perf(V): 浮点 lane 计算改为纯结果和掩码合并`

`vext_fp_utils_insts.sail` 的算术/比较/窄整数饱和/class纯helper；`vext_fp_insts.sail` 的算术、unary、move/merge SYMBOLIC execute；`vext_fp_vm_insts.sail` 两比较族；`vext_fp_red_insts.sail` 两归约族。依赖C08/C09及公共/合法性/掩码前件。

每lane生成 `(flags,bits)`，用mask选择值及flags贡献，最后统一累计；归约保持已有lane顺序与累积依赖。部分slide/special仍有控制流，不能声称所有向量数据分叉消失。测试包括 `solve_vector_lanes/`、`solve_vector_reduction/`、C07之外的FP实际decoder/replay核对。本轮4项结构检查中的3项覆盖这里，不能替代数值、状态、callback和完整模型验证。可进一步按普通算术/比较、unary、归约、move四提交；若用户希望减少提交数，可先作为一组，但不把“改写”写成“解决所有超时”。

### C13 `fix(bfloat16): 无活动元素时不累计标量转换异常`

`zvfbfwma_insts.sail` 普通VF路径将scalar BF16转f32改为纯转换，首次活动lane才累计scalar flags；加 `test/first_party/src/test_bf16_wma_flags.S` 及CMake注册。将vl=0、全mask、vstart=vl、一个活动lane、旧NX保留及SEW/LMUL负例与C14分开评审。C10负责guard hunks。

这是普通后端可见的正确性修复：标量sNaN在没有active lane时不应单独产生NV。可在未接完整共用浮点后端的普通模型上形成小候选，优先价值较高。旧Isla float-only分支已有相关IR修复，但不代表本Sail源提交已完成；仍需用精确Sail候选构建并运行测试。

### C14 `perf(bfloat16): 用纯转换和掩码合并执行四条向量路径`

`zfbfmin_utils.sail` 的SYMBOLIC bf16_to_f32，以及zvfbfmin/zvfbfwma四个SYMBOLIC execute，搭配 `solve_bf16_lanes/`。依赖C08/C10/C11/C13及已有向量选择原语；C02的assembly、C10的guard、C13的普通异常修复不得重复收纳。

审核活跃元素、sNaN、旧flags和目标向量保持；本轮源码结构检查通过，数值/整指令证据仍按旧冻结版本理解。与C13合并可减少提交，但会失去单独回滚性能改写而保留普通后端修复的便利。

## 本轮实际检查与证据适用范围

详见[机器可读检查摘要](checks.json)，这里只列结论；原始日志留在仓库外审阅输出目录，没有修改生产文件。

| 当前命令/检查 | 本轮结果 | 解释 |
| --- | --- | --- |
| `python3 -B sail-riscv/test/assembly_text/check.py <外部输出>` | PASS | 104文本/LLVM编码，32FLI往返；不是完整模型执行 |
| `solve_vector_lanes/{check_clauses,check_unary_clauses,check_move_merge}.py` | 3项退出0 | 只查源码结构 |
| `solve_bf16_lanes/check_clauses.py` | 退出0 | 只查源码结构 |
| `test/solve_fp_legality/build_probe.py <外部输出>` | 退出1 | 现行文件超出旧四函数变化范围；fixture版本失配 |
| `test/solve_pure_compare/restore_before.py <外部输出>` | 退出1 | patch应用后旧core哈希不匹配；不能重建声明的旧对照 |
| `solve_scalar_minmax/verify_source.py <HEAD控制快照>` | 退出1 | 当前源码无其要求的双体；控制快照仅用于触达结构断言 |
| `python3 -B agents/v_symbolic_ir_workarounds/verify.py` | 退出1 | mvvtype/vexttype/vmvrtype/vvtype/vxtype等坐标或锚点失配；另有79配置哈希warning |
| `git -C sail-riscv diff --cached --check` | 退出2 | 7份新增Sail文件EOF空行，以及before.patch内空格上下文被外层diff识为尾空格 |

`strict=false` 的IR哈希warning按[现行流程](../../specs/ir-workflow.md)允许继续，但源码坐标失配须单独核对。不是要求所有模型源commit同步77/79配置哈希；只有相关源码变化时核对实际受影响region。生产源码集成发布前应附同源IR/配置核对结果。

测试准备问题还包括：RV32脚本默认指向某次历史临时candidate/plugin（虽可环境覆盖）；部分stage B README/脚本仍要求C++生成 `softfloat_f32eq`，与当前移除cpp直连不符；Cargo测试依赖兄弟Isla、部分oracle源码在父仓库。需明确本工作区集成测试合同及版本选择，不能把测试目录随便搬入独立上游后称可运行。before.patch是冻结证据，不能为消除空白警告直接trim而破坏其重建/hash合同，应选择保真表达或限定处理并重验。

## 如何实际形成可审阅提交

用户选择后，可从固定HEAD建立隔离分支/工作树，保留原索引与源文件；按上面hunk边界逐层形成候选，再做类型检查、该批相关回归和必要构建。候选测试必须使用候选源码/工具版本，不能默认读回原dirty工作区。最后核最终tree与原索引（明确排除pyc和批准的整理）及所保留剩余补丁，避免遗漏。

优先审阅C02、C05、C13；C03之后可审C04/C06/C07。C08是需要用户决定工具链与共用语义方向的大批次；后续C09/C12/C14沿它推进。C10涉及合法域修正，应独立核语义，C11按等价优化核证。测试源码随所属修复提交，失效历史脚本先修订或明确归档。

Sail-RISC-V源码提交完成不等于更新父gitlink，更不等于重新生成Isla自带IR。根据[Git边界](../../GIT.md)，最终应先有可获取的子仓提交，再有消费它的Isla/IR与配置提交，最后显式更新父gitlink。此次没有检查远端可获取性、push、创建提交、切分索引或运行完整求解/硬件验收。
