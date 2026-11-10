# Sail-RISC-V：14 个建议 Commit 与逐文件改动

2026-10-16：本文件保留原14批提案及逐文件解释。实际已在独立worktree细化为23个提交，最终tree与原索引排除pyc后一致；现行提交/文件分配与验证见 [实际索引](commits-20261016.md)。

2026-10-15 重新核对当前 HEAD、gitlink、索引补丁及文件清单。HEAD 仍为 `4f2ac293654a02db26dac5055be7f93fd6e3141e`，分支 `feat/isla-workarounds`；163 个文件全部暂存，无未暂存或未跟踪内容。补丁 SHA-256 仍为 `47ce7fb311f727f6ff976a40206b7eeb448ca8876f8e700a98eb52a67fc86b69`，与 [2026-10-14 审阅](report.md)一致。

建议采用 14 个目的明确的提交，排除 12 个 `.pyc` 后覆盖全部 151 个路径，其中生产/构建/忽略规则 37 个，测试材料 114 个。数字是逻辑分组建议，尚未制作或构建逐层候选。C07 和 C12 继续细拆可成为 19 个；这里只采用 14 个便于讨论。

下列路径相对 `sail-riscv/`。`修改`/`新增` 指相对 HEAD 的状态。增删行是该文件当前完整补丁的统计；同一文件分到多批时，统计不表示每一批都收整份补丁。每行“本批变化”才是应抽取的范围。相同路径重复出现是有意按函数拆分。

## Commit 总表

| 批次 | 建议标题 | 涉及路径数（含共享文件） |
| --- | --- | --- |
| C01 | `chore(gitignore): 明确构建产物和测试缓存边界` | 1 |
| C02 | `fix(assembly): 修正 FLI 常量和 BF16 汇编文本` | 5 |
| C03 | `refactor(symbolic): 提供公共 ITE 和严格布尔接口` | 2 |
| C04 | `fix(FD): 恢复快速浮点寄存器访问的状态语义` | 5 |
| C05 | `fix(V): 补齐快速向量寄存器写回的 Dirty 和回调` | 3 |
| C06 | `perf(FD): 用位运算和 ITE 表达取负与 NaN unbox` | 6 |
| C07 | `perf(decoder): 显式匹配 AMO 和向量编码布局` | 13 |
| C08 | `feat(float): 共用 Sail 浮点与 IEEE 异常语义并接入 C++ 后端` | 78 |
| C09 | `refactor(FD): 复用纯 min/max 规则并迁移标量调用` | 12 |
| C10 | `fix(V): 区分普通浮点与整数转换的 SEW 合法域` | 11 |
| C11 | `perf(V): 用纯布尔条件与掩码接口减少辅助分叉` | 10 |
| C12 | `perf(V): 浮点 lane 计算改为纯结果和掩码合并` | 18 |
| C13 | `fix(bfloat16): 无活动元素时不累计标量转换异常` | 3 |
| C14 | `perf(bfloat16): 用纯转换和掩码合并执行四条向量路径` | 9 |

## C01 `chore(gitignore): 明确构建产物和测试缓存边界`

独立维护提交。已暂存 pyc 需要从未来候选中排除，新 ignore 不会自动取消其跟踪。

| 文件 | 状态及完整增删行 | 本批变化 |
| --- | --- | --- |
| [.gitignore](../../sail-riscv/.gitignore) | 修改 +34/−12 | 细化 build、Rust target、Python 缓存、虚拟环境、worktree 和编辑器产物规则；取消对所有隐藏目录的一概忽略。 |

## C02 `fix(assembly): 修正 FLI 常量和 BF16 汇编文本`

独立小修；与后面的执行语义提交共享三个生产文件，必须按 hunk 取。

| 文件 | 状态及完整增删行 | 本批变化 |
| --- | --- | --- |
| [model/extensions/FD/zfa_insts.sail](../../sail-riscv/model/extensions/FD/zfa_insts.sail) | 修改 +46/−58 | 新增 FLI 32 项常量文本 mapping，FLI.H/S/D 用标准立即数文字替代表索引；保留 H 格式不同索引的不同编码。仅收汇编相关 hunk。 |
| [model/extensions/bfloat16/zvfbfmin_insts.sail](../../sail-riscv/model/extensions/bfloat16/zvfbfmin_insts.sail) | 修改 +96/−4 | 修正两条 BF16 汇编 mapping 中多余的分隔符，不带 execute 改写。 |
| [model/extensions/bfloat16/zvfbfwma_insts.sail](../../sail-riscv/model/extensions/bfloat16/zvfbfwma_insts.sail) | 修改 +112/−6 | 为 VV/VF 汇编映射补齐寄存器间逗号及正确掩码分隔，不带执行语义变化。 |
| [test/assembly_text/README.md](../../sail-riscv/test/assembly_text/README.md) | 新增 +23/−0 | 说明实际 assembly 映射、FLI 往返及 LLVM 编码回归的运行方式与覆盖边界。 |
| [test/assembly_text/check.py](../../sail-riscv/test/assembly_text/check.py) | 新增 +182/−0 | 抽取生产汇编映射并构建小模型，检查 104 项文本/编码和 32 项 FLI 表索引往返。 |

## C03 `refactor(symbolic): 提供公共 ITE 和严格布尔接口`

后续 C04/C06/C07/C10/C11 的公共前件；仅提取新原语文件的通用部分。

| 文件 | 状态及完整增删行 | 本批变化 |
| --- | --- | --- |
| [model/prelude/ieee_fp_primops.sail](../../sail-riscv/model/prelude/ieee_fp_primops.sail) | 新增 +213/−0 | 先只加入通用 ite、strict_and_bool、strict_or_bool、isla_bool_to_bit 声明与普通 Sail 函数体。 |
| [model/riscv.sail_project](../../sail-riscv/model/riscv.sail_project) | 修改 +7/−0 | 在 prelude 注册公共原语文件；本提交的文件中仅有通用接口。 |

## C04 `fix(FD): 恢复快速浮点寄存器访问的状态语义`

依赖 C03；同一 fdext_regs 文件的 nan_unbox 留给 C06。

| 文件 | 状态及完整增删行 | 本批变化 |
| --- | --- | --- |
| [model/extensions/FD/fdext_regs.sail](../../sail-riscv/model/extensions/FD/fdext_regs.sail) | 修改 +41/−5 | get_F/get_F_bits 补 Ext_F 检查与表示转换；快速 setter 补表示转换、回调和 FS/SD Dirty；SYMBOLIC accrue_fflags 以 ITE 更新状态，flags 未变时不置 Dirty。排除 nan_unbox hunk。 |
| [test/symbolic_fp/solve_fd_state_equivalence.py](../../sail-riscv/test/symbolic_fp/solve_fd_state_equivalence.py) | 新增 +97/−0 | 独立验证 fflags 累计状态方程，覆盖 RV32/RV64、扩展域与 FS/SD；不单独证明 Sail 实现正确。 |
| [test/symbolic_fp/solve_fd_state_probe/Cargo.lock](../../sail-riscv/test/symbolic_fp/solve_fd_state_probe/Cargo.lock) | 新增 +1093/−0 | 固定 FD 状态 Rust probe 依赖解析。 |
| [test/symbolic_fp/solve_fd_state_probe/Cargo.toml](../../sail-riscv/test/symbolic_fp/solve_fd_state_probe/Cargo.toml) | 新增 +12/−0 | 定义 FD 状态 probe 入口与兄弟 Isla 依赖。 |
| [test/symbolic_fp/solve_fd_state_runner.rs](../../sail-riscv/test/symbolic_fp/solve_fd_state_runner.rs) | 新增 +417/−0 | 直接执行 FD 快速/普通读写及 flags 入口，比较寄存器、FS/SD、callback 等效果。 |

## C05 `fix(V): 补齐快速向量寄存器写回的 Dirty 和回调`

可独立形成候选；测试依赖兄弟 Isla。

| 文件 | 状态及完整增删行 | 本批变化 |
| --- | --- | --- |
| [model/extensions/V/vext_regs.sail](../../sail-riscv/model/extensions/V/vext_regs.sail) | 修改 +10/−2 | 两个快速向量 setter 在写值后补 dirty_v_context 与 vreg_write_callback，恢复普通写臂的状态副作用。 |
| [test/symbolic_fp/solve_vpr_state_probe/Cargo.toml](../../sail-riscv/test/symbolic_fp/solve_vpr_state_probe/Cargo.toml) | 新增 +12/−0 | 定义向量寄存器状态 probe 工程，引用兄弟 Isla。 |
| [test/symbolic_fp/solve_vpr_state_runner.rs](../../sail-riscv/test/symbolic_fp/solve_vpr_state_runner.rs) | 新增 +236/−0 | 直接比较快速/普通 VPR 写入的值、VS Dirty 与 callback 效果，覆盖寄存器和初始 VS 组合。 |

## C06 `perf(FD): 用位运算和 ITE 表达取负与 NaN unbox`

依赖 C03；需要位串级等价，包含 NaN payload/sign 和 ±0。

| 文件 | 状态及完整增删行 | 本批变化 |
| --- | --- | --- |
| [model/extensions/FD/dext_insts.sail](../../sail-riscv/model/extensions/FD/dext_insts.sail) | 修改 +5/−25 | negate_D 改为符号位 XOR，保留指数和尾数位串。 |
| [model/extensions/FD/fdext_regs.sail](../../sail-riscv/model/extensions/FD/fdext_regs.sail) | 修改 +41/−5 | nan_unbox 内层 if 改为 ite(eq_anything(...))，NaN-box 无效时仍返回 canonical NaN。 |
| [model/extensions/FD/fext_insts.sail](../../sail-riscv/model/extensions/FD/fext_insts.sail) | 修改 +5/−25 | negate_S 用符号位 XOR 取代 if；另有两条说明未调用旧比较 helper 缺陷的注释，这些缺陷并未在此修复。 |
| [model/extensions/FD/zfh_insts.sail](../../sail-riscv/model/extensions/FD/zfh_insts.sail) | 修改 +3/−23 | negate_H 改为符号位 XOR，保留指数和尾数位串。 |
| [test/symbolic_fp/solve_decoder_layout/build_negate_fixture.py](../../sail-riscv/test/symbolic_fp/solve_decoder_layout/build_negate_fixture.py) | 新增 +47/−0 | 从真实冻结源抽取旧新 H/S/D negate，构建位串等价探针。 |
| [test/symbolic_fp/solve_decoder_layout/negate_runner.rs](../../sail-riscv/test/symbolic_fp/solve_decoder_layout/negate_runner.rs) | 新增 +111/−0 | 用符号输入验证旧新 H/S/D 取负位串相等，包含 NaN 与 ±0。 |

## C07 `perf(decoder): 显式匹配 AMO 和向量编码布局`

依赖 C03；还可拆 AMO、VMVR/VEXT、FP unary 三个提交。外层生产 guard 仍需核验。

| 文件 | 状态及完整增删行 | 本批变化 |
| --- | --- | --- |
| [model/extensions/A/zaamo_insts.sail](../../sail-riscv/model/extensions/A/zaamo_insts.sail) | 修改 +57/−0 | 新增 SYMBOLIC AMO 完整 32 位布局、合法 op/width/E 寄存器 matcher；保持外层 amo_encoding_valid 守卫。 |
| [model/extensions/V/vext_arith_insts.sail](../../sail-riscv/model/extensions/V/vext_arith_insts.sail) | 修改 +127/−0 | 重写 SYMBOLIC encdec_nreg、vext_vs1 的匹配，并新增 VMVR/VEXT 完整编码布局；普通 mapping 保留。 |
| [model/extensions/V/vext_fp_insts.sail](../../sail-riscv/model/extensions/V/vext_fp_insts.sail) | 修改 +1459/−130 | 仅收 VFUNARY0/VFWUNARY0/VFNUNARY0/VFUNARY1 的 SYMBOLIC 子字段合法值 matcher；execute 新实现另归 C12。 |
| [test/solve_amo_layout/README.md](../../sail-riscv/test/solve_amo_layout/README.md) | 新增 +11/−0 | 说明 AMO 普通/E 两域布局与完整外层守卫探针的范围。 |
| [test/solve_amo_layout/build_fixture.py](../../sail-riscv/test/solve_amo_layout/build_fixture.py) | 新增 +121/−0 | 抽取生产新旧 AMO mapping，分别生成 E/non-E 小模型。 |
| [test/solve_amo_layout/check_ir.py](../../sail-riscv/test/solve_amo_layout/check_ir.py) | 新增 +46/−0 | 检查新 AMO matcher 不再分叉进入局部 mapping。 |
| [test/solve_amo_layout/runner.rs](../../sail-riscv/test/solve_amo_layout/runner.rs) | 新增 +152/−0 | 核验合法/非法固定字段、E 寄存器限制、payload 及编码往返等布局性质。 |
| [test/symbolic_fp/solve_decoder_layout/build_layout_candidate.py](../../sail-riscv/test/symbolic_fp/solve_decoder_layout/build_layout_candidate.py) | 新增 +38/−0 | 在外部目录渲染 SYMBOLIC 完整外层 mapping 候选。 |
| [test/symbolic_fp/solve_decoder_layout/build_layout_fixture.py](../../sail-riscv/test/symbolic_fp/solve_decoder_layout/build_layout_fixture.py) | 新增 +131/−0 | 生成完整 32 位 tuple mapping 小模型，检查布局与 matcher 的调用行为。 |
| [test/symbolic_fp/solve_decoder_layout/layout_runner.rs](../../sail-riscv/test/symbolic_fp/solve_decoder_layout/layout_runner.rs) | 新增 +167/−0 | 执行布局探针，检查输入匹配、payload、编码往返和分支性质。 |
| [test/symbolic_fp/solve_mapping_matches/README.md](../../sail-riscv/test/symbolic_fp/solve_mapping_matches/README.md) | 新增 +5/−0 | 说明 encdec_nreg/vext_vs1 的穷举、往返和外层 decoder 探针。 |
| [test/symbolic_fp/solve_mapping_matches/build_fixture.py](../../sail-riscv/test/symbolic_fp/solve_mapping_matches/build_fixture.py) | 新增 +88/−0 | 抽取新旧两个 V 子字段 mapping，并生成完整 32 位外层 decoder。 |
| [test/symbolic_fp/solve_mapping_matches/runner.rs](../../sail-riscv/test/symbolic_fp/solve_mapping_matches/runner.rs) | 新增 +162/−0 | 穷举 bits5 合法/非法域，检查新旧匹配、payload 和编码往返。 |

## C08 `feat(float): 共用 Sail 浮点与 IEEE 异常语义并接入 C++ 后端`

依赖 C03；数值由 C++/SoftFloat 或 Isla/Z3 FP 承担，flags 和 RISC-V 策略共用 Sail。需一起接入声明、函数体、adapter、TLS 和构建，并交付外部 Sail 编译器补丁。

| 文件 | 状态及完整增删行 | 本批变化 |
| --- | --- | --- |
| [c_emulator/CMakeLists.txt](../../sail-riscv/c_emulator/CMakeLists.txt) | 修改 +24/−2 | 生产 riscv_model 改连七件 sail_softfloat adapter，启用 WIDE/EXTRA；旧 riscv_softfloat.cpp/h 仅组成显式请求的 EXCLUDE_FROM_ALL oracle 目标。 |
| [c_emulator/sail_softfloat.cpp](../../sail-riscv/c_emulator/sail_softfloat.cpp) | 新增 +215/−0 | 实现 Sail FP/RM 原语的 SoftFloat 数值适配、位串转换、算术、比较、格式转换、整数转换与 BF16；调用作用域隔离 SoftFloat 环境。 |
| [c_emulator/sail_softfloat.h](../../sail-riscv/c_emulator/sail_softfloat.h) | 新增 +85/−0 | 声明主 adapter API，以及保存/恢复舍入、异常等 SoftFloat 环境的 Scope。 |
| [c_emulator/sail_softfloat_extra.cpp](../../sail-riscv/c_emulator/sail_softfloat_extra.cpp) | 新增 +112/−0 | 补齐零、NaN、无穷、取负、分类、余数、min/max、FP128 窄化等数值接口；用整数位分类处理 NaN 和有符号零。 |
| [c_emulator/sail_softfloat_extra.h](../../sail-riscv/c_emulator/sail_softfloat_extra.h) | 新增 +36/−0 | 声明 EXTRA 扩展接口，供主 adapter 头接入。 |
| [c_emulator/sail_softfloat_types.h](../../sail-riscv/c_emulator/sail_softfloat_types.h) | 新增 +19/−0 | 引入 SoftFloat 类型；要求 FAST_INT64/TLS ABI 宏一致；声明 FP/RM 的 Sail sort 相等接口。 |
| [c_emulator/sail_softfloat_wide.cpp](../../sail-riscv/c_emulator/sail_softfloat_wide.cpp) | 新增 +279/−0 | 用 GMP 与 SoftFloat 内部 roundPack 处理宽整数和浮点互转，支持超过宿主整数宽度的数值与 FP128。 |
| [c_emulator/sail_softfloat_wide.h](../../sail-riscv/c_emulator/sail_softfloat_wide.h) | 新增 +43/−0 | 声明 wide 命名空间中的有符号/无符号宽整数转换接口。 |
| [dependencies/softfloat/CMakeLists.txt](../../sail-riscv/dependencies/softfloat/CMakeLists.txt) | 修改 +12/−6 | 启用 C11，将 FAST_INT64 和 C/C++ 各自的 THREAD_LOCAL 宏公开传播，统一库与调用方的 TLS/ABI。 |
| [model/CMakeLists.txt](../../sail-riscv/model/CMakeLists.txt) | 修改 +4/−1 | 生成 C++ 改 include sail_softfloat_types.h/sail_softfloat.h；额外保留 ext_decode 和 execute 入口。 |
| [model/core/ieee_fp_exceptions.sail](../../sail-riscv/model/core/ieee_fp_exceptions.sail) | 新增 +957/−0 | 新增 IEEE 五异常事实、NaN/零/无穷分类、f16/f32/f64 算术/比较/转换异常公式及 ROD；复用 Sail 共享类型，f64 计算需要 FP128。 |
| [model/core/softfloat_interface.sail](../../sail-riscv/model/core/softfloat_interface.sail) | 修改 +68/−68 | 撤下 67 个策略级接口的 cpp 直连绑定，保留接口与 Lem 绑定，使普通 C++ 也进入共用 Sail 函数体。 |
| [model/extensions/FD/softfloat_symbolic.sail](../../sail-riscv/model/extensions/FD/softfloat_symbolic.sail) | 新增 +28/−0 | 新增共享异常位序到 RISC-V fflags 的转换、canonical NaN 常量与合法 RM 映射；文件名虽有 symbolic，当前函数体供两个后端共用。 |
| [model/extensions/FD/softfloat_symbolic_f16.sail](../../sail-riscv/model/extensions/FD/softfloat_symbolic_f16.sail) | 新增 +169/−0 | 新增 22 个 f16 算术、FMA、比较、舍入和整数/格式转换包装，组合数值原语与共用异常公式。 |
| [model/extensions/FD/softfloat_symbolic_f32.sail](../../sail-riscv/model/extensions/FD/softfloat_symbolic_f32.sail) | 新增 +192/−0 | 新增 23 个 f32 包装，包含整数转换、f16/f64/BF16 互转以及 ROD 窄化策略。 |
| [model/extensions/FD/softfloat_symbolic_f64.sail](../../sail-riscv/model/extensions/FD/softfloat_symbolic_f64.sail) | 新增 +174/−0 | 新增 22 个 f64 算术、比较和转换包装，异常计算复用 FP128 中间值。 |
| [model/prelude/ieee_fp_primops.sail](../../sail-riscv/model/prelude/ieee_fp_primops.sail) | 新增 +213/−0 | 在 C03 公共接口基础上补齐 FP16/32/64/128 与 RM 原语、分类、算术、转换以及 cpp adapter 名称绑定。 |
| [model/riscv.sail_project](../../sail-riscv/model/riscv.sail_project) | 修改 +7/−0 | 注册 IEEE 异常库及共用/f16/f32/f64 四份包装文件，暂不收 fp_minmax 注册。 |
| [test/ieee_exceptions/.gitignore](../../sail-riscv/test/ieee_exceptions/.gitignore) | 新增 +3/−0 | 忽略该隔离测试的缓存、求解缓存和构建输出。 |
| [test/ieee_exceptions/Cargo.lock](../../sail-riscv/test/ieee_exceptions/Cargo.lock) | 新增 +1094/−0 | 固定 IEEE 异常 Rust probe 的依赖解析结果。 |
| [test/ieee_exceptions/Cargo.toml](../../sail-riscv/test/ieee_exceptions/Cargo.toml) | 新增 +9/−0 | 定义 IEEE 异常 probe 包和对兄弟 Isla 的依赖。 |
| [test/ieee_exceptions/README.md](../../sail-riscv/test/ieee_exceptions/README.md) | 新增 +27/−0 | 说明独立 IEEE 异常小模型、SoftFloat oracle 对照和运行方式。 |
| [test/ieee_exceptions/build_ir.sh](../../sail-riscv/test/ieee_exceptions/build_ir.sh) | 新增 +29/−0 | 类型检查并生成 IEEE 异常探针 IR，保留所需入口。 |
| [test/ieee_exceptions/check.py](../../sail-riscv/test/ieee_exceptions/check.py) | 新增 +140/−0 | 生成 f16/f32/f64 定向及可选随机算术/比较样例，逐项对照 SoftFloat 数值与异常。 |
| [test/ieee_exceptions/check_conversions.py](../../sail-riscv/test/ieee_exceptions/check_conversions.py) | 新增 +113/−0 | 对照格式/整数转换及 ROD 的共享异常结果。 |
| [test/ieee_exceptions/ieee_exceptions.sail](../../sail-riscv/test/ieee_exceptions/ieee_exceptions.sail) | 新增 +509/−0 | 提供算术、比较、格式/整数转换与 BF16 异常探针入口，无架构寄存器状态。 |
| [test/ieee_exceptions/ieee_exceptions.sail_project](../../sail-riscv/test/ieee_exceptions/ieee_exceptions.sail_project) | 新增 +16/−0 | 声明异常探针依赖的 prelude、接口、异常公式和测试模块顺序。 |
| [test/ieee_exceptions/src/main.rs](../../sail-riscv/test/ieee_exceptions/src/main.rs) | 新增 +560/−0 | Isla IR 执行器：接收位串测试项，读取结果/异常并支持结果唯一性证明。 |
| [test/rv32_fp/cases.json](../../sail-riscv/test/rv32_fp/cases.json) | 新增 +8/−0 | 记录 FMVH_X_D、FMVP_D_X 及四条 RV32 压缩浮点访存的机器码、构造子与预期效果。 |
| [test/rv32_fp/probe.sail](../../sail-riscv/test/rv32_fp/probe.sail) | 新增 +32/−0 | 从真实 backwards decoder 进入 RV32 浮点指令，再执行，避免直接提供构造子掩盖译码缺口。 |
| [test/rv32_fp/riscv32_fp.toml](../../sail-riscv/test/rv32_fp/riscv32_fp.toml) | 新增 +107/−0 | 提供 RV32 F/D 隔离测试的架构与寄存器配置。 |
| [test/rv32_fp/run.sh](../../sail-riscv/test/rv32_fp/run.sh) | 新增 +83/−0 | 生成 RV32/V128 测试 IR，构建 runner、运行六项测试并记录 provenance；默认源码/plugin 仍指历史临时目录，需显式配置。 |
| [test/rv32_fp/runner.rs](../../sail-riscv/test/rv32_fp/runner.rs) | 新增 +170/−0 | 执行真实译码和指令效果核验，收集成功解码、寄存器/访存结果。 |
| [test/rv32_fp/test_results.py](../../sail-riscv/test/rv32_fp/test_results.py) | 新增 +34/−0 | 拒绝缺失实际 backwards decode 证据或不完整的测试结果。 |
| [test/solve_pure_compare/README.md](../../sail-riscv/test/solve_pure_compare/README.md) | 新增 +25/−0 | 说明 IEEE 分类/异常/饱和包装的纯比较性能回归与冻结旧对照合同。 |
| [test/solve_pure_compare/before-manifest.json](../../sail-riscv/test/solve_pure_compare/before-manifest.json) | 新增 +6/−0 | 记录三个旧对照模型文件的预期 SHA-256。 |
| [test/solve_pure_compare/before.patch](../../sail-riscv/test/solve_pure_compare/before.patch) | 新增 +291/−0 | 保存恢复旧分类/异常/包装表达式的反向补丁；当前输入恢复后不能满足原哈希，需处理版本失配。 |
| [test/solve_pure_compare/check_ir.py](../../sail-riscv/test/solve_pure_compare/check_ir.py) | 新增 +33/−0 | 检查新 helper 调用闭包不使用主动查询的位串比较，允许位宽分派。 |
| [test/solve_pure_compare/prepare.py](../../sail-riscv/test/solve_pure_compare/prepare.py) | 新增 +81/−0 | 从冻结旧源码与当前源码生成分类/异常/饱和的旧新小探针。 |
| [test/solve_pure_compare/restore_before.py](../../sail-riscv/test/solve_pure_compare/restore_before.py) | 新增 +28/−0 | 在外部目录应用旧对照补丁并校验哈希；当前哈希检查失败。 |
| [test/solve_pure_compare/run.py](../../sail-riscv/test/solve_pure_compare/run.py) | 新增 +46/−0 | 编译执行已准备的旧新比较探针，限制单项时间并保留结果。 |
| [test/solve_pure_compare/runner.rs](../../sail-riscv/test/solve_pure_compare/runner.rs) | 新增 +142/−0 | 执行小 IR 并核验满足性、等价关系与执行路径统计。 |
| [test/symbolic_fp/README.md](../../sail-riscv/test/symbolic_fp/README.md) | 新增 +49/−0 | 说明早期 Stage B 的 f32 比较和独立加法探针；部分 C++ 直连假设需要更新。 |
| [test/symbolic_fp/check_f16_wrapper.sh](../../sail-riscv/test/symbolic_fp/check_f16_wrapper.sh) | 新增 +50/−0 | 检查 22 个 f16 helper 的类型/IR/未知输入入口；末尾仍要求旧 softfloat_f16add C++ 直连，需迁移。 |
| [test/symbolic_fp/check_f64.sh](../../sail-riscv/test/symbolic_fp/check_f64.sh) | 新增 +42/−0 | 检查 22 个 f64 helper 与未知输入 IR；仍要求旧 softfloat_f64eq/muladd C++ 符号，需迁移。 |
| [test/symbolic_fp/check_stage_b.sh](../../sail-riscv/test/symbolic_fp/check_stage_b.sh) | 新增 +57/−0 | 生成 Stage B IR 并检查原语结构和 C++ 输出；末尾旧 softfloat_f32eq 期待需迁移。 |
| [test/symbolic_fp/f16_wrapper.sail](../../sail-riscv/test/symbolic_fp/f16_wrapper.sail) | 新增 +40/−0 | 提供 f16 生产包装的 C++/未知输入调用探针。 |
| [test/symbolic_fp/f16_wrapper.sail_project](../../sail-riscv/test/symbolic_fp/f16_wrapper.sail_project) | 新增 +20/−0 | 注册 f16 包装探针所需模型与测试模块。 |
| [test/symbolic_fp/f16_wrapper_cases.py](../../sail-riscv/test/symbolic_fp/f16_wrapper_cases.py) | 新增 +126/−0 | 为每个 f16 包装生成 SoftFloat 期望并执行差分。 |
| [test/symbolic_fp/f16_wrapper_probe.rs](../../sail-riscv/test/symbolic_fp/f16_wrapper_probe.rs) | 新增 +218/−0 | 运行 f16 helper，提取位串/flags 并核验唯一性。 |
| [test/symbolic_fp/f32_c.sail](../../sail-riscv/test/symbolic_fp/f32_c.sail) | 新增 +57/−0 | 以可被 IEEE runner 消费的入口调用生产 f32 包装，并提供 ROD 候选探针。 |
| [test/symbolic_fp/f32_c.sail_project](../../sail-riscv/test/symbolic_fp/f32_c.sail_project) | 新增 +21/−0 | 注册 f32 生产包装、异常库与未知输入探针。 |
| [test/symbolic_fp/f32_c_README.md](../../sail-riscv/test/symbolic_fp/f32_c_README.md) | 新增 +45/−0 | 说明 23 个 f32 helper 的数值/flags/路径验证与未覆盖的指令级状态。 |
| [test/symbolic_fp/f32_c_boundary_cases.py](../../sail-riscv/test/symbolic_fp/f32_c_boundary_cases.py) | 新增 +98/−0 | 生成 BF16/f32 次正规、正规、有限/无穷边界等定向样例。 |
| [test/symbolic_fp/f32_c_check.sh](../../sail-riscv/test/symbolic_fp/f32_c_check.sh) | 新增 +81/−0 | 严格类型检查并生成 IR，确认 23 个正式 helper 和未知输入探针都在。 |
| [test/symbolic_fp/f32_c_diff.py](../../sail-riscv/test/symbolic_fp/f32_c_diff.py) | 新增 +74/−0 | 将生产 f32 包装结果与独立 SoftFloat oracle 逐项比较。 |
| [test/symbolic_fp/f32_conversion_cases.py](../../sail-riscv/test/symbolic_fp/f32_conversion_cases.py) | 新增 +80/−0 | 生成全部 f32 转换 helper 的独立 SoftFloat 期望。 |
| [test/symbolic_fp/f32_conversion_probe.rs](../../sail-riscv/test/symbolic_fp/f32_conversion_probe.rs) | 新增 +144/−0 | 按行执行转换 helper，证明结果位串和 flags 唯一。 |
| [test/symbolic_fp/f32_conversion_run.sh](../../sail-riscv/test/symbolic_fp/f32_conversion_run.sh) | 新增 +21/−0 | 构建并运行 f32 转换 probe。 |
| [test/symbolic_fp/f32_unknown.sail](../../sail-riscv/test/symbolic_fp/f32_unknown.sail) | 新增 +148/−0 | 为每个 f32 helper 保留全部参数未知的调用入口，用于观察真实符号执行。 |
| [test/symbolic_fp/f64_README.md](../../sail-riscv/test/symbolic_fp/f64_README.md) | 新增 +34/−0 | 说明 f64 定向验证及父工作区 oracle 依赖；保留旧 C++ 直连的说明已过时。 |
| [test/symbolic_fp/f64_probe.sail](../../sail-riscv/test/symbolic_fp/f64_probe.sail) | 新增 +309/−0 | 保留 22 个生产 f64 helper 的具体/未知输入入口。 |
| [test/symbolic_fp/f64_probe.sail_project](../../sail-riscv/test/symbolic_fp/f64_probe.sail_project) | 新增 +20/−0 | 注册 f64 probe 与共用异常/包装模块。 |
| [test/symbolic_fp/generate_f64_cases.py](../../sail-riscv/test/symbolic_fp/generate_f64_cases.py) | 新增 +162/−0 | 从独立 SoftFloat oracle 生成可重放 f64 样例。 |
| [test/symbolic_fp/run_f16_wrapper.sh](../../sail-riscv/test/symbolic_fp/run_f16_wrapper.sh) | 新增 +22/−0 | 构建并运行 f16 Rust probe。 |
| [test/symbolic_fp/run_f64.rs](../../sail-riscv/test/symbolic_fp/run_f64.rs) | 新增 +185/−0 | 解析 f64 样例，执行正式 helper 并比较 flags 与结果位串。 |
| [test/symbolic_fp/run_f64.sh](../../sail-riscv/test/symbolic_fp/run_f64.sh) | 新增 +20/−0 | 构建并启动 f64 Rust runner。 |
| [test/symbolic_fp/run_stage_b.rs](../../sail-riscv/test/symbolic_fp/run_stage_b.rs) | 新增 +273/−0 | 执行 Stage B 小 IR，观察比较、加法和未知输入结果/路径。 |
| [test/symbolic_fp/run_stage_b.sh](../../sail-riscv/test/symbolic_fp/run_stage_b.sh) | 新增 +19/−0 | 构建并运行 Stage B Rust probe。 |
| [test/symbolic_fp/stage_b.sail](../../sail-riscv/test/symbolic_fp/stage_b.sail) | 新增 +46/−0 | 提供完整 f32 比较、独立数值加法、BF16 接口和未知输入入口；演示加法不作为完整架构异常实现。 |
| [test/symbolic_fp/stage_b.sail_project](../../sail-riscv/test/symbolic_fp/stage_b.sail_project) | 新增 +22/−0 | 注册 Stage B prelude、异常库、生产包装与探针。 |
| [test/symbolic_fp/type_reuse.sail](../../sail-riscv/test/symbolic_fp/type_reuse.sail) | 新增 +37/−0 | 探查共享异常类型到 RISC-V flags 位序转换，以及 f16/f32/f64 分类。 |
| [test/symbolic_fp/type_reuse.sail_project](../../sail-riscv/test/symbolic_fp/type_reuse.sail_project) | 新增 +19/−0 | 注册共享类型复用的独立小模型。 |
| [test/symbolic_fp/type_reuse/Cargo.lock](../../sail-riscv/test/symbolic_fp/type_reuse/Cargo.lock) | 新增 +1093/−0 | 固定共享类型复用 Rust probe 的依赖解析。 |
| [test/symbolic_fp/type_reuse/Cargo.toml](../../sail-riscv/test/symbolic_fp/type_reuse/Cargo.toml) | 新增 +8/−0 | 定义类型复用 probe 及兄弟 Isla 库依赖。 |
| [test/symbolic_fp/type_reuse/src/main.rs](../../sail-riscv/test/symbolic_fp/type_reuse/src/main.rs) | 新增 +173/−0 | 运行异常位序/分类 probe，并核验具体及未知输入结果。 |
| [test/symbolic_fp/type_reuse_README.md](../../sail-riscv/test/symbolic_fp/type_reuse_README.md) | 新增 +19/−0 | 说明复用 float_rounding_mode、float_bits、fp_exception_flags 的边界与命令。 |
| [test/symbolic_fp/type_reuse_run.sh](../../sail-riscv/test/symbolic_fp/type_reuse_run.sh) | 新增 +25/−0 | 严格检查、生成类型复用 IR 并运行 Rust probe。 |

## C09 `refactor(FD): 复用纯 min/max 规则并迁移标量调用`

依赖 C08；会影响普通 C++ 模型。旧双体源码检查需更新。

| 文件 | 状态及完整增删行 | 本批变化 |
| --- | --- | --- |
| [model/extensions/FD/dext_insts.sail](../../sail-riscv/model/extensions/FD/dext_insts.sail) | 修改 +5/−25 | FMIN_D/FMAX_D 改为共用 fp_min/max_pure。 |
| [model/extensions/FD/fext_insts.sail](../../sail-riscv/model/extensions/FD/fext_insts.sail) | 修改 +5/−25 | FMIN_S/FMAX_S 的重复 NaN、±0 和比较逻辑改为 fp_min/max_pure，仍由调用方累计 flags 和写回。 |
| [model/extensions/FD/fp_minmax.sail](../../sail-riscv/model/extensions/FD/fp_minmax.sail) | 新增 +57/−0 | 新增无状态 fp_min/max/minm/maxm_pure，返回 (flags,bits)，集中处理 NaN、sNaN 与 ±0。 |
| [model/extensions/FD/zfa_insts.sail](../../sail-riscv/model/extensions/FD/zfa_insts.sail) | 修改 +46/−58 | FMINM/FMAXM 的 H/S/D 六条执行改用 fp_minm/maxm_pure，任一 NaN 时返回 canonical NaN。 |
| [model/extensions/FD/zfh_insts.sail](../../sail-riscv/model/extensions/FD/zfh_insts.sail) | 修改 +3/−23 | FMIN_H/FMAX_H 改为共用 fp_min/max_pure。 |
| [model/extensions/V/vext_fp_utils_insts.sail](../../sail-riscv/model/extensions/V/vext_fp_utils_insts.sail) | 修改 +201/−35 | fp_min/fp_max 去掉重复值选择规则，调用新纯 helper，再保持原有 accrue_fflags 副作用。 |
| [model/riscv.sail_project](../../sail-riscv/model/riscv.sail_project) | 修改 +7/−0 | 在 FD 模块中注册 fp_minmax.sail，使标量和向量共用纯 min/max。 |
| [test/symbolic_fp/solve_scalar_minmax/build_probe.py](../../sail-riscv/test/symbolic_fp/solve_scalar_minmax/build_probe.py) | 新增 +178/−0 | 抽取冻结标量 min/max 旧值路径与新 helper，生成 H/S/D 定向样例。 |
| [test/symbolic_fp/solve_scalar_minmax/check_ir.py](../../sail-riscv/test/symbolic_fp/solve_scalar_minmax/check_ir.py) | 新增 +49/−0 | 检查四个 min/max 纯 helper 的专用相等及可接受的位宽分派 Jump。 |
| [test/symbolic_fp/solve_scalar_minmax/run.sh](../../sail-riscv/test/symbolic_fp/solve_scalar_minmax/run.sh) | 新增 +62/−0 | 组织精确旧快照/新 probe、IR 结构、runner 和定向结果检查。 |
| [test/symbolic_fp/solve_scalar_minmax/runner.rs](../../sail-riscv/test/symbolic_fp/solve_scalar_minmax/runner.rs) | 新增 +153/−0 | 执行 min/max 小 IR，检查结果、flags 与旧新等价。 |
| [test/symbolic_fp/solve_scalar_minmax/verify_source.py](../../sail-riscv/test/symbolic_fp/solve_scalar_minmax/verify_source.py) | 新增 +40/−0 | 校验普通 clause 和 V 定义与旧冻结源关系；仍要求 SYMBOLIC/ordinary 双体，当前统一实现不满足，需更新。 |

## C10 `fix(V): 区分普通浮点与整数转换的 SEW 合法域`

依赖 C03；这是合法域修复，须与 C11 等价 Bool 改写分开。下列七件 legality 测试是 C10/C11 共用准备材料，实际提交只收一次；目前未覆盖新增合法性行为，需补齐。

| 文件 | 状态及完整增删行 | 本批变化 |
| --- | --- | --- |
| [model/extensions/V/vext_fp_insts.sail](../../sail-riscv/model/extensions/V/vext_fp_insts.sail) | 修改 +1459/−130 | 普通及 SYMBOLIC 宽化算术改用标准宽化合法性 helper，区分算术与允许 INT8 的转换。 |
| [model/extensions/V/vext_fp_utils_insts.sail](../../sail-riscv/model/extensions/V/vext_fp_utils_insts.sail) | 修改 +201/−35 | 新增 valid_fp_standard_op / illegal_fp_standard_variable_width，普通算术/归约拒绝 SEW8，转换仍保留合法 INT8；相关调用改用标准合法域。 |
| [model/extensions/bfloat16/zvfbfmin_insts.sail](../../sail-riscv/model/extensions/bfloat16/zvfbfmin_insts.sail) | 修改 +96/−4 | BF16 两条转换 execute 增加 SEW=16 检查；非法状态经 Illegal guard 退出。 |
| [model/extensions/bfloat16/zvfbfwma_insts.sail](../../sail-riscv/model/extensions/bfloat16/zvfbfwma_insts.sail) | 修改 +112/−6 | VV/VF execute 增加 SEW=16 检查，VF 扩大 LMUL 断言移到 Illegal guard 之后。 |
| [test/solve_fp_legality/README.md](../../sail-riscv/test/solve_fp_legality/README.md) | 新增 +18/−0 | 说明旧四函数纯 Bool 等价探针；尚不覆盖后来新增的 SEW 合法域修复。 |
| [test/solve_fp_legality/before/vext_fp_utils_insts.sail](../../sail-riscv/test/solve_fp_legality/before/vext_fp_utils_insts.sail) | 新增 +764/−0 | 冻结旧 FP 工具源，供修改前后四函数对照；属于测试输入，不参与生产模型。 |
| [test/solve_fp_legality/before/vext_utils_insts.sail](../../sail-riscv/test/solve_fp_legality/before/vext_utils_insts.sail) | 新增 +728/−0 | 冻结旧向量工具源，供对照与范围检查；属于测试输入。 |
| [test/solve_fp_legality/build_probe.py](../../sail-riscv/test/solve_fp_legality/build_probe.py) | 新增 +100/−0 | 从旧/当前文件抽取四函数，要求其他源码完全相同；当前因后续改动而拒绝生成，需更新边界。 |
| [test/solve_fp_legality/check_ir.py](../../sail-riscv/test/solve_fp_legality/check_ir.py) | 新增 +40/−0 | 检查四个合法性 helper 可达 IR 为直线 Bool，避免数据比较触发分叉。 |
| [test/solve_fp_legality/run.py](../../sail-riscv/test/solve_fp_legality/run.py) | 新增 +109/−0 | 组织 probe 重建、编译、证明与逐步结果记录。 |
| [test/solve_fp_legality/runner.rs](../../sail-riscv/test/solve_fp_legality/runner.rs) | 新增 +124/−0 | 对任意原始输入证明旧新 Bool 结果及 vtype 状态相等；不能直接用于证明有意改变的合法域。 |

## C11 `perf(V): 用纯布尔条件与掩码接口减少辅助分叉`

依赖 C03/C10；共享 legality 测试列出是为了说明归属，不意味着重复新增。更新后可随 C10 或 C11 一次提交。

| 文件 | 状态及完整增删行 | 本批变化 |
| --- | --- | --- |
| [model/extensions/V/vext_control.sail](../../sail-riscv/model/extensions/V/vext_control.sail) | 修改 +9/−9 | assert_lmul_pow 从逐臂 match 改为 option(int) 相等与 strict Bool membership，仍只接受 -3..3。 |
| [model/extensions/V/vext_fp_utils_insts.sail](../../sail-riscv/model/extensions/V/vext_fp_utils_insts.sail) | 修改 +201/−35 | valid_fp_op/illegal_fp_normal 等改 strict Bool；归约用 eq_anything(vstart,zeros()) 表示同一零条件，宽化归约复用共同合法性。合法域改变留在 C10。 |
| [model/extensions/V/vext_utils_insts.sail](../../sail-riscv/model/extensions/V/vext_utils_insts.sail) | 修改 +46/−3 | valid_vtype/valid_rd_mask/valid_reg_group 改纯相等/Bool 表达；SYMBOLIC init_masked_source 接 isla_init_mask 快速分支，保留关闭开关的循环和普通版本。 |
| [test/solve_fp_legality/README.md](../../sail-riscv/test/solve_fp_legality/README.md) | 新增 +18/−0 | 说明旧四函数纯 Bool 等价探针；尚不覆盖后来新增的 SEW 合法域修复。 |
| [test/solve_fp_legality/before/vext_fp_utils_insts.sail](../../sail-riscv/test/solve_fp_legality/before/vext_fp_utils_insts.sail) | 新增 +764/−0 | 冻结旧 FP 工具源，供修改前后四函数对照；属于测试输入，不参与生产模型。 |
| [test/solve_fp_legality/before/vext_utils_insts.sail](../../sail-riscv/test/solve_fp_legality/before/vext_utils_insts.sail) | 新增 +728/−0 | 冻结旧向量工具源，供对照与范围检查；属于测试输入。 |
| [test/solve_fp_legality/build_probe.py](../../sail-riscv/test/solve_fp_legality/build_probe.py) | 新增 +100/−0 | 从旧/当前文件抽取四函数，要求其他源码完全相同；当前因后续改动而拒绝生成，需更新边界。 |
| [test/solve_fp_legality/check_ir.py](../../sail-riscv/test/solve_fp_legality/check_ir.py) | 新增 +40/−0 | 检查四个合法性 helper 可达 IR 为直线 Bool，避免数据比较触发分叉。 |
| [test/solve_fp_legality/run.py](../../sail-riscv/test/solve_fp_legality/run.py) | 新增 +109/−0 | 组织 probe 重建、编译、证明与逐步结果记录。 |
| [test/solve_fp_legality/runner.rs](../../sail-riscv/test/solve_fp_legality/runner.rs) | 新增 +124/−0 | 对任意原始输入证明旧新 Bool 结果及 vtype 状态相等；不能直接用于证明有意改变的合法域。 |

## C12 `perf(V): 浮点 lane 计算改为纯结果和掩码合并`

依赖 C08/C09/C10/C11；可细分算术/比较、unary、归约、move 四个提交。这里统一作为一个功能批次。

| 文件 | 状态及完整增删行 | 本批变化 |
| --- | --- | --- |
| [model/extensions/V/vext_fp_insts.sail](../../sail-riscv/model/extensions/V/vext_fp_insts.sail) | 修改 +1459/−130 | 新增 SYMBOLIC 普通/宽化向量与标量算术、四类 unary、move/merge 执行体；每 lane 算候选与 flags，用 mask 合并，末尾统一累计。 |
| [model/extensions/V/vext_fp_red_insts.sail](../../sail-riscv/model/extensions/V/vext_fp_red_insts.sail) | 修改 +102/−0 | RFVVTYPE/RFWVVTYPE 新增 SYMBOLIC 归约：按原顺序计算候选，以 ITE 选择累加值和异常，最后累计 flags。 |
| [model/extensions/V/vext_fp_utils_insts.sail](../../sail-riscv/model/extensions/V/vext_fp_utils_insts.sail) | 修改 +201/−35 | 增加无 fcsr 副作用的算术/FMA/比较/宽化/class helper；SYMBOLIC 窄整数饱和包装改为纯比较与 ITE，交给调用方汇总 flags。 |
| [model/extensions/V/vext_fp_vm_insts.sail](../../sail-riscv/model/extensions/V/vext_fp_vm_insts.sail) | 修改 +97/−0 | FVVMTYPE/FVFMTYPE 新增 SYMBOLIC 纯比较与掩码结果选择，只有活动 lane 贡献异常。 |
| [test/symbolic_fp/solve_vector_lanes/build_helper_probe.py](../../sail-riscv/test/symbolic_fp/solve_vector_lanes/build_helper_probe.py) | 新增 +214/−0 | 从生产纯 helper 和旧实现生成 min/max、比较、分类、窄整数饱和等小探针。 |
| [test/symbolic_fp/solve_vector_lanes/build_runner.sh](../../sail-riscv/test/symbolic_fp/solve_vector_lanes/build_runner.sh) | 新增 +21/−0 | 用指定 Isla 库路径创建并构建外部 Rust runner 工程。 |
| [test/symbolic_fp/solve_vector_lanes/check_clauses.py](../../sail-riscv/test/symbolic_fp/solve_vector_lanes/check_clauses.py) | 新增 +30/−0 | 检查 12 个 SYMBOLIC 算术/比较 clause 无逐 lane mask 控制分支。 |
| [test/symbolic_fp/solve_vector_lanes/check_move_merge.py](../../sail-riscv/test/symbolic_fp/solve_vector_lanes/check_move_merge.py) | 新增 +15/−0 | 检查 VFMV/VFMERGE SYMBOLIC 分支使用掩码值选择。 |
| [test/symbolic_fp/solve_vector_lanes/check_pure_ir.py](../../sail-riscv/test/symbolic_fp/solve_vector_lanes/check_pure_ir.py) | 新增 +22/−0 | 检查分类/比较/饱和等纯 helper 的 IR 调用纯相等，避免主动求解比较。 |
| [test/symbolic_fp/solve_vector_lanes/check_unary_clauses.py](../../sail-riscv/test/symbolic_fp/solve_vector_lanes/check_unary_clauses.py) | 新增 +17/−0 | 检查四类转换/sqrt/class SYMBOLIC 循环及纯 class helper 存在。 |
| [test/symbolic_fp/solve_vector_lanes/move_probe.sail](../../sail-riscv/test/symbolic_fp/solve_vector_lanes/move_probe.sail) | 新增 +111/−0 | 构造旧循环与新选择式 move/merge，覆盖 vl/vstart/mask/旧目标等输入。 |
| [test/symbolic_fp/solve_vector_lanes/move_probe.sail_project](../../sail-riscv/test/symbolic_fp/solve_vector_lanes/move_probe.sail_project) | 新增 +11/−0 | 注册 move/merge 探针与公共接口。 |
| [test/symbolic_fp/solve_vector_lanes/run_helper_probe.sh](../../sail-riscv/test/symbolic_fp/solve_vector_lanes/run_helper_probe.sh) | 新增 +56/−0 | 编译并运行向量纯 helper 探针，保留结果和 IR 检查。 |
| [test/symbolic_fp/solve_vector_lanes/run_move_probe.sh](../../sail-riscv/test/symbolic_fp/solve_vector_lanes/run_move_probe.sh) | 新增 +31/−0 | 生成并运行 move/merge 新旧等价与边界样例。 |
| [test/symbolic_fp/solve_vector_lanes/runner.rs](../../sail-riscv/test/symbolic_fp/solve_vector_lanes/runner.rs) | 新增 +142/−0 | 执行向量 helper/move 小 IR，记录 SAT、等价和路径数。 |
| [test/symbolic_fp/solve_vector_lanes/validate_probe_log.py](../../sail-riscv/test/symbolic_fp/solve_vector_lanes/validate_probe_log.py) | 新增 +18/−0 | 要求完整且唯一的日志行、SAT/等价覆盖和新形式单路径，防止缺项被记成功。 |
| [test/symbolic_fp/solve_vector_reduction/prepare_cases.py](../../sail-riscv/test/symbolic_fp/solve_vector_reduction/prepare_cases.py) | 新增 +143/−0 | 从独立 oracle 套件准备全状态 RFVVTYPE/RFWVVTYPE 归约样例，含 masked sNaN 与非法 vstart。 |
| [test/symbolic_fp/solve_vector_reduction/run_cases.py](../../sail-riscv/test/symbolic_fp/solve_vector_reduction/run_cases.py) | 新增 +81/−0 | 通过真实 decode/execute 运行归约样例，比较完整状态并记录输入/IR 哈希。 |

## C13 `fix(bfloat16): 无活动元素时不累计标量转换异常`

普通后端正确性修复；可优先在旧普通模型上制作候选，无需先接完整 C08。合法性 guard 留 C10。

| 文件 | 状态及完整增删行 | 本批变化 |
| --- | --- | --- |
| [model/extensions/bfloat16/zvfbfwma_insts.sail](../../sail-riscv/model/extensions/bfloat16/zvfbfwma_insts.sail) | 修改 +112/−6 | 仅普通 VF 路径：标量 BF16 转 f32 改为纯转换，首次活动 lane 才累计标量异常，避免无活动元素时 sNaN 单独置 NV。 |
| [test/first_party/CMakeLists.txt](../../sail-riscv/test/first_party/CMakeLists.txt) | 修改 +1/−0 | 注册 test_bf16_wma_flags 第一方汇编测试。 |
| [test/first_party/src/test_bf16_wma_flags.S](../../sail-riscv/test/first_party/src/test_bf16_wma_flags.S) | 新增 +145/−0 | 检查 VF BF16 widening MAC 的 vl=0、全 mask、vstart=vl、活动 lane、旧 flags 及非法 SEW/LMUL 情形。 |

## C14 `perf(bfloat16): 用纯转换和掩码合并执行四条向量路径`

依赖 C08/C10/C11/C13 及既有向量选择接口；与 C13 分开可以单独回滚性能改写。

| 文件 | 状态及完整增删行 | 本批变化 |
| --- | --- | --- |
| [model/extensions/bfloat16/zfbfmin_utils.sail](../../sail-riscv/model/extensions/bfloat16/zfbfmin_utils.sail) | 修改 +9/−0 | 新增 SYMBOLIC bf16_to_f32 纯分类/ITE 实现，处理 sNaN 与 canonical NaN，并返回转换异常。 |
| [model/extensions/bfloat16/zvfbfmin_insts.sail](../../sail-riscv/model/extensions/bfloat16/zvfbfmin_insts.sail) | 修改 +96/−4 | 两条 BF16 SYMBOLIC 窄化/宽化转换改候选计算与掩码合并，只累计活动 lane 异常。 |
| [model/extensions/bfloat16/zvfbfwma_insts.sail](../../sail-riscv/model/extensions/bfloat16/zvfbfwma_insts.sail) | 修改 +112/−6 | VV/VF 两条 SYMBOLIC widening MAC 改纯转换/FMA、掩码结果选择及统一 flags 累计。 |
| [test/symbolic_fp/solve_bf16_lanes/check_clauses.py](../../sail-riscv/test/symbolic_fp/solve_bf16_lanes/check_clauses.py) | 新增 +29/−0 | 检查四个 BF16 SYMBOLIC 循环使用值选择而非逐 lane mask 分支。 |
| [test/symbolic_fp/solve_bf16_lanes/probe.sail](../../sail-riscv/test/symbolic_fp/solve_bf16_lanes/probe.sail) | 新增 +24/−0 | 保留旧 BF16 转换实现，与新纯转换做未知输入等价对照。 |
| [test/symbolic_fp/solve_bf16_lanes/probe.sail_project](../../sail-riscv/test/symbolic_fp/solve_bf16_lanes/probe.sail_project) | 新增 +13/−0 | 注册 BF16 小探针模块与生产转换工具。 |
| [test/symbolic_fp/solve_bf16_lanes/probe_defs.sail](../../sail-riscv/test/symbolic_fp/solve_bf16_lanes/probe_defs.sail) | 新增 +6/−0 | 提供独立 probe 的 flags 类型、NV 和 canonical NaN 基础定义。 |
| [test/symbolic_fp/solve_bf16_lanes/run.rs](../../sail-riscv/test/symbolic_fp/solve_bf16_lanes/run.rs) | 新增 +95/−0 | 执行 BF16 新旧转换及其等价探针，核对路径与结果。 |
| [test/symbolic_fp/solve_bf16_lanes/run.sh](../../sail-riscv/test/symbolic_fp/solve_bf16_lanes/run.sh) | 新增 +61/−0 | 类型检查、生成 BF16 probe IR、构建运行器并核验日志。 |

## 不进入提交的 12 个文件

以下都是新增 Python 字节码缓存；保留工作区文件，实际制作候选时不收录。Cargo.lock 不属于这类缓存。

- `test/assembly_text/__pycache__/check.cpython-313.pyc`
- `test/solve_amo_layout/__pycache__/build_fixture.cpython-313.pyc`
- `test/solve_pure_compare/__pycache__/check_ir.cpython-313.pyc`
- `test/solve_pure_compare/__pycache__/prepare.cpython-313.pyc`
- `test/solve_pure_compare/__pycache__/restore_before.cpython-313.pyc`
- `test/solve_pure_compare/__pycache__/run.cpython-313.pyc`
- `test/symbolic_fp/__pycache__/f16_wrapper_cases.cpython-313.pyc`
- `test/symbolic_fp/__pycache__/f32_c_diff.cpython-313.pyc`
- `test/symbolic_fp/solve_scalar_minmax/__pycache__/build_probe.cpython-313.pyc`
- `test/symbolic_fp/solve_scalar_minmax/__pycache__/check_ir.cpython-313.pyc`
- `test/symbolic_fp/solve_scalar_minmax/__pycache__/verify_source.cpython-313.pyc`
- `test/symbolic_fp/solve_vector_lanes/__pycache__/build_helper_probe.cpython-313.pyc`

## 需要按函数拆开的文件

| 文件 | 批次及边界 |
| --- | --- | --- |
| `model/extensions/FD/dext_insts.sail` | C06：negate_D 改为符号位 XOR，保留指数和尾数位串。；C09：FMIN_D/FMAX_D 改为共用 fp_min/max_pure。 |
| `model/extensions/FD/fdext_regs.sail` | C04：get_F/get_F_bits 补 Ext_F 检查与表示转换；快速 setter 补表示转换、回调和 FS/SD Dirty；SYMBOLIC accrue_fflags 以 ITE 更新状态，flags 未变时不置 Dirty。排除 nan_unbox hunk。；C06：nan_unbox 内层 if 改为 ite(eq_anything(...))，NaN-box 无效时仍返回 canonical NaN。 |
| `model/extensions/FD/fext_insts.sail` | C06：negate_S 用符号位 XOR 取代 if；另有两条说明未调用旧比较 helper 缺陷的注释，这些缺陷并未在此修复。；C09：FMIN_S/FMAX_S 的重复 NaN、±0 和比较逻辑改为 fp_min/max_pure，仍由调用方累计 flags 和写回。 |
| `model/extensions/FD/zfa_insts.sail` | C02：新增 FLI 32 项常量文本 mapping，FLI.H/S/D 用标准立即数文字替代表索引；保留 H 格式不同索引的不同编码。仅收汇编相关 hunk。；C09：FMINM/FMAXM 的 H/S/D 六条执行改用 fp_minm/maxm_pure，任一 NaN 时返回 canonical NaN。 |
| `model/extensions/FD/zfh_insts.sail` | C06：negate_H 改为符号位 XOR，保留指数和尾数位串。；C09：FMIN_H/FMAX_H 改为共用 fp_min/max_pure。 |
| `model/extensions/V/vext_fp_insts.sail` | C07：仅收 VFUNARY0/VFWUNARY0/VFNUNARY0/VFUNARY1 的 SYMBOLIC 子字段合法值 matcher；execute 新实现另归 C12。；C10：普通及 SYMBOLIC 宽化算术改用标准宽化合法性 helper，区分算术与允许 INT8 的转换。；C12：新增 SYMBOLIC 普通/宽化向量与标量算术、四类 unary、move/merge 执行体；每 lane 算候选与 flags，用 mask 合并，末尾统一累计。 |
| `model/extensions/V/vext_fp_utils_insts.sail` | C09：fp_min/fp_max 去掉重复值选择规则，调用新纯 helper，再保持原有 accrue_fflags 副作用。；C10：新增 valid_fp_standard_op / illegal_fp_standard_variable_width，普通算术/归约拒绝 SEW8，转换仍保留合法 INT8；相关调用改用标准合法域。；C11：valid_fp_op/illegal_fp_normal 等改 strict Bool；归约用 eq_anything(vstart,zeros()) 表示同一零条件，宽化归约复用共同合法性。合法域改变留在 C10。；C12：增加无 fcsr 副作用的算术/FMA/比较/宽化/class helper；SYMBOLIC 窄整数饱和包装改为纯比较与 ITE，交给调用方汇总 flags。 |
| `model/extensions/bfloat16/zvfbfmin_insts.sail` | C02：修正两条 BF16 汇编 mapping 中多余的分隔符，不带 execute 改写。；C10：BF16 两条转换 execute 增加 SEW=16 检查；非法状态经 Illegal guard 退出。；C14：两条 BF16 SYMBOLIC 窄化/宽化转换改候选计算与掩码合并，只累计活动 lane 异常。 |
| `model/extensions/bfloat16/zvfbfwma_insts.sail` | C02：为 VV/VF 汇编映射补齐寄存器间逗号及正确掩码分隔，不带执行语义变化。；C10：VV/VF execute 增加 SEW=16 检查，VF 扩大 LMUL 断言移到 Illegal guard 之后。；C13：仅普通 VF 路径：标量 BF16 转 f32 改为纯转换，首次活动 lane 才累计标量异常，避免无活动元素时 sNaN 单独置 NV。；C14：VV/VF 两条 SYMBOLIC widening MAC 改纯转换/FMA、掩码结果选择及统一 flags 累计。 |
| `model/prelude/ieee_fp_primops.sail` | C03：先只加入通用 ite、strict_and_bool、strict_or_bool、isla_bool_to_bit 声明与普通 Sail 函数体。；C08：在 C03 公共接口基础上补齐 FP16/32/64/128 与 RM 原语、分类、算术、转换以及 cpp adapter 名称绑定。 |
| `model/riscv.sail_project` | C03：在 prelude 注册公共原语文件；本提交的文件中仅有通用接口。；C08：注册 IEEE 异常库及共用/f16/f32/f64 四份包装文件，暂不收 fp_minmax 注册。；C09：在 FD 模块中注册 fp_minmax.sail，使标量和向量共用纯 min/max。 |

## 提交前待办与验证边界

- 2026-10-15 只重新核对版本/完整补丁及阅读源码、测试入口，未重跑 2026-10-14 的功能检查。补丁一致允许引用其有限结果，但不能称为每个中间 commit 已验证。
- 2026-10-14 的汇编 104 文本/编码与 32 FLI 往返通过；4 项 lane 源码结构检查通过。这些不覆盖全模型数值、状态、硬件或端到端性能。
- 旧合法性 fixture、纯比较旧对照恢复与 min/max 双体检查不适配当前源；需修复测试入口/版本合同，再对精确候选验证。特别是三个格式/Stage B 的 C++ 检查仍要求旧 SoftFloat 直连。
- C08 的 C++ 构建依赖父仓库 `agents/float_support_review/tools/unified_backend_p0/compiler.patch`；该补丁不在本次 Sail-RISC-V 暂存范围内，独立提交不能固定完整工具链。Isla 原语及部分 oracle/runner 也属于工作区集成依赖。
- 当前受影响 workaround 源码坐标存在失配；接入生成 IR 前按 [IR 流程](../../specs/ir-workflow.md)核对实际 region，不能只改 IR 哈希。
- 当前空白检查有 EOF 空行及 before.patch 上下文空白告警；冻结补丁不能直接 trim，须保留恢复与哈希合同。
- 实际拆分应从固定 HEAD 的隔离候选逐批构建，保留原索引/工作树；最后核对 151 个路径及剩余补丁。源码提交、Isla 消费版本及父 gitlink 更新按 [Git 边界](../../GIT.md)分别处理。

详细历史检查见 [report.md](report.md) 与 [checks.json](checks.json)；完整机器清单见 [inventory.json](inventory.json)。
