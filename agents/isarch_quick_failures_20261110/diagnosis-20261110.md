# isarch 快速失败诊断（2026-11-10，仅诊断）

1. **译码 Poison（39 项）**：主要是未约束的特权前态触发 Sail 内部异常，并经 `arbitrary` 返回 Poison；应复用真实架构初态域约束并保留异常出处，不能靠换 tactic 修复；预计小至中，3–4 个文件，约 60–150 行及回归。
2. **浮点函数缺失（31 项）**：旧模型生成的 IR 仍引用 67 个无体 helper，当前 Isla 已按新模型架构删除旧分发器；应接回已有精确 Sail helper 并重新生成配套 IR，不能原样恢复近似分发器；预计中，6–8 个模型接线文件及生成 IR。
3. **没有合法编码（10 项）**：9 项确为 RV32 编码，BITYPE 则是本配置关闭实验扩展；应以编码域不可满足作为正常“不适用”结果，保留真正的内部错误；预计小，编码、收集器、摘要约 3 个文件，约 60–150 行及回归。
4. **未完成路径（22 项）**：全部逐项复现，均为非法／未实现前态触发 Sail 异常后的 Poison，数量精确对应 7 或 2；当前已有 ExecuteAs 续执行；与第 1 类共用前态域修复，另补异常诊断，预计额外 2–3 个文件、约 30–80 行。
5. **LOAD_FP panic（1 项）**：`word_width={1,2,4,8}` 在 IR 中退化为自由 `%i64`，负 width 进入 `zeros(8*width)`；应在执行前恢复模型指令参数域／编码域，保留 nat 不变量断言；预计中，入口与编码模块约 2 个文件、80–180 行及回归。

## 范围、路径与复现方式

- 工作树 `daf61c04`，分支 `fix/isarch-quick-failures`；未修改 Rust、Sail、配置或原始 IR，未做 Git 写操作。
- 本报告中的 `S/` 指 `<仓库根>/sail-riscv/model/`；引用的 10 份关键 Sail 文件与生成本批 IR 的模型快照逐字节相同，核对记录见 `source-audit.json`，没有另算哈希。
- `I` 指 `<仓库根>/.worktree/pathmerge-all-20261110/isla/rv64d.ir`；`C` 指 `<仓库根>/.worktree/pathmerge-cache-all-20261110/configs/`。
- 原始证据分别位于用户指定的两处 `runs/<clause>/`；本轮每次只运行一个 isarch，均 `-T 32 --path-merging`，无 execution limit、无 path cache，外层最多 280 秒。
- 构建：`RUSTFLAGS="-L $HOME/.local/opt/z3-official-1fd1d3613/lib -C link-arg=-Wl,-rpath,$HOME/.local/opt/z3-official-1fd1d3613/lib" CARGO_TARGET_DIR="$PWD/diag/build" TMPDIR="$PWD/diag" cargo build --release --bin isarch -j 16`。
- 构建日志 `build.log`；`ldd diag/build/release/isarch` 确认实际加载官方目录的 `libz3.so.5.3`。
- 通用复现：`python3 diag/reproduce.py CLAUSE --tactic qfaufbv --probe current_exception`；每个目录的 `command.json` 保存完整 argv 和 cwd，`result.json` 保存退出码和耗时，`isarch.log` 保存原始输出。
- 脚本实际调用：`diag/build/release/isarch -A I -C C/对应配置 --verbose -T 32 --path-merging --timeout 280s --smt-timeout 1m --tastic 策略 -D spr [探针] solve-state --clause=CLAUSE`，cwd 在 `diag/<clause>/<标签>/`。
- 本构建按用户要求未加 feature，`--smt-timeout` 不提供独立看门狗保证；每次均由外层进程时限兜住。所有生成物均在 `/data1/.../diag/`。

## 1. Poison：异常返回，不是 get-value 失败

### 报错位置与译码回环

- `src/isarch/exec.rs:253` 的 `encdec_guard_roundtrip_ok` 将最终编码交给 `zext_decode`（32 位）或 `zext_decode_compressed`（16 位），检查返回的是原指令构造子，防止 execute 域中的参数越过真实译码守卫。
- 同文件 `:295` 对返回路径做 SAT 检查，`:315` 对 Poison／非具体返回报 `译码回环返回非具体值`。这段没有调用 `Model::get_val`。
- 具体前态来自同文件 `:2279` 起的最终模型具体化；因此模型选中了错误的前态域成员，会在独立译码中真实执行异常。
- 另一路 `zencdec_forwards 返回 Poison` 位于 `src/isarch/encoding.rs:71`，不是 `get-value` 的错误码。
- `I:384429` 的 `zext_decode` 调用 `zencdec_backwards`，检查 `have_exception`，异常则走 `arbitrary`。
- `isla-lib/src/executor.rs:3074` 实现 `Instr::Arbitrary`，`:3090` 在顶层返回 `Run::Finished(Val::Poison)`；`S/prelude/errors.sail:21` 的 `internal_error` 会抛出 `Error_internal_error`。

### 本轮实证

| clause | qfaufbv：退出码／秒／用例 | default：退出码／秒／用例 |
| --- | --- | --- |
| RTYPE | 1 / 41.278 / 0 | 0 / 57.016 / 10 |
| ADDIW | 1 / 4.376 / 0 | 0 / 3.672 / 1 |
| ITYPE | 1 / 41.109 / 0 | 0 / 42.102 / 5 |
| FMVH_X_D | 1 / 3.574 / 0 | 1 / 5.729 / 0 |

- 命令：`python3 diag/reproduce.py RTYPE --probe ext_decode --probe encdec_backwards --probe have_exception --probe current_exception --probe-function ext_decode`；default 对照只改 `--tactic default`。ADDIW、ITYPE 的完整命令见各自 `command.json`。
- `RTYPE/qfaufbv/isarch.log:12`：`Error_internal_error("extensions/cfi/zicfilp_regs.sail:31: Hypervisor extension not supported")`；`:13` 设置 `have_exception=true`；`:14–15` 两层 `Returning via arbitrary ... = poison`；`:81` 报译码回环错误。
- `ADDIW/qfaufbv/isarch.log:12` 明确记录 `Calling get_xLPE(["|VirtualSupervisor|"])`；随后同一 Sail 异常和 Poison。
- 固定输入对照：`python3 diag/reproduce.py ADDIW --label vs-qfaufbv --instruction-bits 0x0000001b --prestate cur_privilege=VirtualSupervisor --probe current_exception`，再只换 `--label vs-default --tactic default`。两次分别 1.167／1.068 秒退出 1，日志均捕获 `zicfilp_regs.sail:31`；固定机器字启动译码将 Poison 泛报为“返回依赖符号状态的值”，其底层异常与自由探索相同。这里固定非法前态只用于归因，不作为正式修法。
- `LPAD/qfaufbv` 40.326 秒退出 1；日志中的 `zicfilp_regs.sail:31/32` 异常后，由符号编码报 `zencdec_forwards 返回 Poison`。
- `FMVH_X_D/qfaufbv` 捕获的是 `core/types.sail:61` 的非法 XLEN 编码及 `core/sys_regs.sail:292/293` 的虚拟特权异常，不能把这两个 FMV 条目简单算成与 RTYPE 完全相同的译码错误。

### 共因与修法

- `isla-lib/src/config.rs:2734` 的 `initial_state_rv64_domain` 缺省为 false；本批配置没有开启它，`src/isarch_main.rs:835` 原样赋给 Target。
- `src/isarch/target.rs:1102` 因此跳过已有 `Rv64Domain` 限制：包括按实际 H 能力限制特权枚举、SXL/UXL 及 MPP 的合法值。
- 实际模型明确 `S/core/extensions.sail:71`：`hartSupports(Ext_H)=false`；但自由 `cur_privilege` 仍包含 `VirtualSupervisor/VirtualUser`。
- 译码时 `I:160990` 在比较当前机器字的 LPAD opcode **之前**求 `currentlyEnabled(Zicfilp)`，最终调用 `S/extensions/cfi/zicfilp_regs.sail:25` 的 `get_xLPE`，`:31/32` 对虚拟特权抛内部异常；所以普通 ADD 也会触发。
- 建议在 RV64 正常入口复用现有架构初态域，域值来自模型静态能力，而不是钉死运行态。文件：`src/isarch_main.rs`、`src/isarch/target.rs`、必要时 `isla-lib/src/config.rs` 的缺省策略。
- `src/isarch/exec.rs`／`src/isarch/encoding.rs` 应在异常传播时保留 `current_exception` 和源码出处，不能把 Poison 当正常完成或静默忽略。
- **Z3 判断**：没有 get-value 失败、模型缺字段或 tactic 不支持理论的证据；有完整 Sail throw→arbitrary→Poison 的正证据。default 只改变了见证选值，三个对照成功不证明排除了非法状态；FMVH 在 default 下仍失败。最新 Z3 可重测选值差异，但选值改变不能代替域修复。

## 2. 浮点 helper：当前运行器与输入 IR 不配套

- 本轮 `F_BIN_RM_TYPE_D/qfaufbv` 42.123 秒退出 1；输出 JSON 的 diagnostics 同时包含缺失 `riscv_f64Add/Mul/Sub/Div`，最后显示哪一个受线程顺序影响。
- 当前报错出口：`isla-lib/src/executor.rs:1604` 的 `ExecError::NoFunction`；`isla-lib/src/error.rs:211` 格式化为 `Function ... does not exist`。
- `I:23807` 起共 **79** 个 `zriscv_*` 声明，只有 **12** 个函数体，缺失 **67** 个；完整名称见 `helper-inventory.json`。
- 这些 67 个名称与旧分发器接受的集合一致，包括 BF16；旧入口也要求 tuple 结构体的 flags/result 字段。缺失不是单独某个 helper 拼写变了。
- 历史 `origin/feat/float-support@1a1910e` 中，`isla-lib/src/primop/float.rs:539` 为 `softfloat_dispatch`，`isla-lib/src/executor.rs:1196` 挂接运行时调用。
- 可读历史提交：`3075fdbb`（增加约 1169 行专用原语）、`83d035ea`（执行器挂接 34 行）；另有同题重做提交 `e067e9db/81d89554`。
- 当前祖先链的 `e4e6835b` 已正式删除这套分发，提交说明明确“浮点 helper 经普通 Sail IR 函数体执行”；所以 daf61c04 **没有**旧分发，是设计迁移后的状态，不是新近漏注册一个名字。
- **不宜原样移植**：根仓 `agents/float_support_review/report.md:55` 起、`inventory-runtime.md:25` 起记录旧实现符号 rm 恒走 RNE、Eq 对 qNaN 的 NV 规则错误，以及 Div/FMA NX、OF/UF 的近似；原样恢复会违反本轮“不改标准行为、不屏蔽差异”的要求。
- 现有准确实现来源可读：模型提交 `d79d8b32`（当前 Isla `ir/provenance/manifest.json:3` 声明的配套模型）包含普通 Sail 函数体；本轮输入模型快照 `cbb4766f` 的 `model/riscv.sail_project:43` 仍只有旧接口，未接入这套函数体。
- 建议恢复配套模型中的 `model/extensions/FD/softfloat_symbolic{,_f16,_f32,_f64}.sail`、`model/core/ieee_fp_exceptions.sail`、`model/prelude/ieee_fp_primops.sail`、`model/core/softfloat_interface.sail` 与 `model/riscv.sail_project` 接线，再用匹配的 Sail／Isla 插件重新生成正式 IR。复用当前 `isla-lib/src/primop/float.rs` 的通用 FP 原语，避免重引专用 ISA 分发。
- 这需要按依赖和当前模型结构整合，不能承诺把历史模型整提交原样挑入就可编译；`scripts/regenerate_ir.py` 和现有 `test/softfloat_legacy/` 可作为后续验收入口。本轮未生成新 IR。

### V 浮点为什么没有同样的最终错误

- `S/extensions/V/vext_fp_insts.sail:985` 的 VF_VADD 调 `fp_add`；`I:64443` 是普通 Sail `zfp_add`，`:64486` 调无体 `zriscv_f32Add`。它与 Rust 通用原语 `fp_add` 并不是同一个入口。
- 原 FVFTYPE 运行目录只有 `status.timeout.log`、没有最终 JSON；原命令没有开启 `-D s`。`src/isarch/exec.rs:2632` 的逐路径 NoFunction 日志受 `SYM_EXEC` 开关控制；最终 clause 错误要等 `:2669` 的全部工作结束。两小时被外层终止会遮住最终错误汇总，不能从缺少错误文本推断 V 已实现这些函数。
- 本轮定向实证：`python3 diag/reproduce.py FVFTYPE --label directed-vfadd-valid --seconds 120 --instruction-bits 0x02005057 --prestate cur_privilege=Machine --prestate 'mstatus={ bits = 0x0000000a00006600 }' --prestate 'vtype={ bits = 0x0000000000000010 }' --prestate vl=0x0000000000000001 --prestate vstart=0x0000000000000000 --probe fp_add --probe current_exception`。
- 这是单个活动 lane 的诊断输入，不是修复配置；其余正式自由探索不受影响。40.919 秒退出 1。
- `FVFTYPE/directed-vfadd-valid/isarch.log:10`：`Calling fp_add`；`:14`：`Function riscv_f32Add does not exist`，位置 `extensions/V/vext_fp_utils_insts.sail 184:11–184:40`；调用栈 `zexecute → zfp_add`。
- 另跑原自由形态：`python3 diag/reproduce.py FVFTYPE --label free-probe --seconds 120 --probe fp_add --probe get_num_elem --probe init_masked_result --probe current_exception`；120.417 秒被外层终止，窗口内没有调用 fp_add，已见 get_num_elem、Illegal_Instruction 路径及译码侧 zicfilp 异常。这证明本窗口先消耗在前序自由探索；不将 120 秒停点外推到原两小时的全部线程。
- 因此 V 的 helper 缺口相同；原两小时窗口是否已经在某条路径遇到同一缺失，原日志开关不足以回溯确认，不把这件事写成已证事实。

## 3. 无合法编码：逐项核对

| clause | Sail 编码条件与位置 | RV64 本配置结论 |
| --- | --- | --- |
| AES32ESMI | `S/extensions/K/zkn_insts.sail:90`：Zkne 且 `xlen==32` | 不适用 |
| AES32ESI | 同文件 `:110`：Zkne 且 `xlen==32` | 不适用 |
| AES32DSMI | 同文件 `:134`：Zknd 且 `xlen==32` | 不适用 |
| AES32DSI | 同文件 `:154`：Zknd 且 `xlen==32` | 不适用 |
| C_FLWSP | `S/extensions/FD/zcf_insts.sail:15`：Zcf | 不适用 |
| C_FSWSP | 同文件 `:31`：Zcf | 不适用 |
| C_FLW | 同文件 `:47`：Zcf | 不适用 |
| C_FSW | 同文件 `:65`：Zcf | 不适用 |
| C_JAL | `S/extensions/C/zca_insts.sail:143`：`xlen==32` 且 Zca | 不适用 |
| BITYPE | `S/extensions/Zibi/zibi_insts.sail:23`：Zibi，无 XLEN32 限制 | 仅本配置不适用 |

- Zcf 的共享静态条件在 `S/core/extensions.sail:204`：`config extensions.Zcf.supported & (xlen==32)`；四条各自 assembly 映射还明确 `when xlen==32`。
- BITYPE 的链：`S/extensions/Zibi/zibi_insts.sail:12` → `hartSupports(Zibi)`；`S/core/extensions.sail:75` → `sys_enable_experimental_extensions() & config extensions.Zibi.supported`。
- 本批 `C/riscv64_difftest.toml:77` 和 FD 配置 `:74` 均关闭 `sys_enable_experimental_extensions`。`I:11017` 保留这个运行时配置调用，后面的编译期 Zibi 支持为 true；故不是 RV32 专属，也不是位宽限制。
- 本轮 BITYPE 47.879 秒退出 1，`BITYPE/qfaufbv/isarch.log` 最后为 `Unreachable: 当前执行路径不存在合法机器编码`；其余九项的同类原始日志与上述静态条件吻合。
- 当前处理在 `src/isarch/exec.rs:2104`：完成路径非 Illegal 且 `encoding_paths` 返回空，`:2108` 记 `Unreachable`，使整个 clause 失败。
- 建议复用 `src/isarch/encoding.rs:108` 的正常／压缩编码域判定，在执行前判断整个 clause 的合法编码域是否为空；可证明为空时输出例如 `status=not-applicable, reason=no-encoding-in-current-config, gen=[]`，退出 0。
- 仅某条人工构造路径无编码时，计为编码域排除；不得把求解 Unknown、超时、Sail 内部异常也转换成“不适用”。摘要／CLI 消费处需明确区分“不适用”“完整完成”“partial”，文件 `src/isarch/encoding.rs`、`src/isarch/exec.rs`、`src/isarch/solve_summary.rs`。
- FMVH_X_D/FMVP_D_X 虽被原名单分到 Poison，编码也受 `S/extensions/FD/zfa_insts.sail:527/:546` 的 `in32BitMode()` 限制；`S/core/sys_regs.sail:296` 从当前特权的架构位判断，合法固定 RV64 域中不适用。
- 必须保留这个细节：自由非法前态的 UXL/SXL 可以伪造 32 位模式；不能只看主机 IR 名为 rv64 就在引擎写死 FMV 白名单。该模型不支持动态修改 SXL/UXL（`S/core/sys_regs.sail:219`），初始化为本机 XLEN（`:264/:265`）。

## 4. 全部 22 项 partial：停点与数量完整对应

本轮对 22 项全部加 `--probe current_exception` 顺序复现，均退出 0；没有把错误退出或超时混入下表。

| 条目集合 | 每项 unfinished | 捕获的 Sail 异常及每项次数 |
| --- | --- | --- |
| C_FLD、C_FLDSP、C_FSD、C_FSDSP、C_LBU、C_LD、C_LDSP、C_LH、C_LHU、C_LW、C_LWSP、C_SB、C_SD、C_SDSP、C_SH、C_SW、C_SWSP（17 项） | 7 | `core/types.sail:78` ×1；`:61` ×3；`sys/vmem.sail:209` ×3 |
| C_JALR、C_JR、JALR（3 项） | 2 | `extensions/cfi/zicfilp_regs.sail:31/:32` 各1 |
| ECALL | 2 | `extensions/I/base_insts.sail:566/:567` 各1 |
| FENCE | 2 | `core/sys_regs.sail:452/:453` 各1 |

- 第一组：`S/sys/sys_control.sail:11` 在 MPRV=1 时按 MPP 求有效特权；保留 MPP=2 落入 `S/core/types.sail:78` 的 `Invalid privilege level or virtual mode`。
- `S/core/sys_regs.sail:288` 按有效模式读取 SXL/UXL；全自由字段出现 `00` 时由 `S/core/types.sail:61` 抛 `architecture(0b00) is invalid`，出现 `11` 时经 `S/sys/vmem.sail:209` 抛 `RV128 not supported`。
- 后三组都由不支持 H 的配置中仍存在虚拟特权引起：分别停在 `get_xLPE`、ECALL 的特权分支、`is_fiom_active` 的特权分支；它们的具体函数不同，但初态域共因相同。
- 示例：`C_LD/qfaufbv/isarch.log:100` 起逐项记录上述 7 次异常，每次随后都有“返回值是Poison”；JSON `summary.unfinished-paths=7, errors=0, status=partial`。
- 本轮 C_LD 8.543 秒、57 条完成用例；ECALL 39.937 秒、3 条；FENCE 41.109 秒、27 条；JALR 5.328 秒、3 条。完整计数见 `run-summary.json`。
- `src/isarch/exec.rs:1836` 已识别 ExecuteAs，`:1843` 用 `LocalFrame::new_call` 保存续段，`:2670` 起循环执行续段；`:1860` 才把 `Finished(Poison)/Exit/Suspended` 计为未完成。
- 浮点压缩访存也不能套历史 ExecuteAs 缺口：例如 `S/extensions/FD/zcd_insts.sail` 的 C_FLD 直接调用 LOAD_FP 执行；本轮相同 7 个异常发生在后续访存语义。
- 修法与第 1 类共用：恢复按模型能力定义的完整初态域；不得直接清零 unfinished 计数，不得丢掉 Poison 路径后宣称 finished。另应让异常携带 `current_exception`、原始源码停点和路径身份，避免只报泛化 Poison 警告。

## 5. LOAD_FP：非法参数域穿过执行入口

- 命令：`python3 diag/reproduce.py LOAD_FP --probe-function execute --probe current_exception`；`LOAD_FP/qfaufbv/result.json`：72.033 秒，退出 `-6`（SIGABRT）。
- `LOAD_FP/qfaufbv/isarch.log:18`：`nat invariant violated in zeros: ... equals -9223372036854775808`。
- 源码出口为 `isla-lib/src/primop.rs:163`；调用链 `zeros(:1290)` → `panic_if_negative_concretized_nat(:174)` → `panic_negative_nat_invariant`。
- 第二次定位：`python3 diag/reproduce.py LOAD_FP --label values --probe-all --probe-function vmem_read`；64.827 秒，仍 SIGABRT，日志 `:131` 明确 `Calling zeros(["v205"]) at sys/vmem_utils.sail 139:32–139:39`，`:142` 此次长度为 `-6647340350595573368`。
- 因此触发点是 `S/sys/vmem_utils.sail:139` 的 `var data : bits(8 * width) = zeros()`，不是浮点加法或 NaN 计算。
- `S/core/types.sail:398` 声明 `word_width={1,2,4,8}`；`S/extensions/FD/fext_insts.sail:269` 载荷采用该类型，但 `I:2914` 的 LOAD_FP 载荷最后一项只剩 `%i64`。
- `src/isarch/exec.rs:1628` 的 `symbolic_args_from_types` 直接复用 IR 类型造符号；`isla-lib/src/primop_util.rs:581` 将 `%i64` 声明成无范围的 64 位 BV。原 Sail 有限集合没有自动变成输入约束。
- LOAD_FP 执行只检查 `width<=flen_bytes`（`S/extensions/FD/fext_insts.sail:282`），负数也通过；合法性原本依赖真实译码，入口现在直接调用构造子 execute。
- `I:53047–53060` 明确执行 `8 * width`，经过带范围检查的 `%i→%i64`，再符号扩展回 `%i` 后交给 zeros。`isla-lib/src/primop.rs:341`、`:403` 的转换检查保证当前可继续分支没有窄化溢出。
- 因而首次触发的 **width=-1152921504606846976（-2^60）**，得到 **长度=-2^63**；第二次对应 **width=-830917543824446671**，乘 8 正好等于捕获的负长度。这两个 width 是依据受检转换链和日志长度反推，不声称调试器直接打印了完整 Ctor。
- 触发的是自由 `LOAD_FP` 构造子的非法 width 取值，**没有合法 FLH/FLW/FLD 机器编码**；同一日志里另一个线程输出的 `fld f0,0(x31)` 是独立的 width=8 路径，不能冒充 panic 的机器码。
- 机制：`zeros` 先尝试证明长度唯一，非唯一时抛 SymbolicLength；`isla-lib/src/executor/symbolic_length.rs:411` 从原生模型选候选并分叉重试，负候选变为唯一值后，`proven_symbolic_i128(:1251)` 正确具体化，nat 断言随即失败。
- 根因不是 nat 检查太严格，也不是 solver 把无符号正常长度误解成负数；上游丢失的有限类型约束让负数本来就可满足。
- 首选修法：在进入 zexecute 前复用 `encoding_paths`，把可编码的符号载荷／守卫约束带入执行，而不是等 `src/isarch/exec.rs:2089` 的收尾才检查；同时按第 1 类保持真实合法的前态域。
- 若现有编码接口不能完整承载某类 refinement，才考虑在 `isla-sail/jib_ir.ml`、`sail_plugin_isla.ml` 保留通用类型约束元数据；不应手写 LOAD_FP 专用的 `{2,4,8}` 重试顺序或局部兜底。
- GDB 尝试记录在 `LOAD_FP/gdb/isarch.log`：环境拒绝 `ptrace`，没有取得调试器现场；随后使用现有探针完成调用点定位，未为此修改源码。

## 后续修复验收建议与诊断边界

- 先写失败测试再修：无 H 的特权域、SXL/UXL/MPP 合法性、两种 tactic 下相同具体输入、空编码域“不适用”、合法／非法指令参数域，以及活动 V lane 的 helper 调用。
- 浮点复用现有 SoftFloat 独立向量回归，覆盖符号舍入、NaN、flags；不要仅测试“函数名能找到”。22 项 partial 需保留真实成功／陷阱结果，并确认非法前态不会进入执行，不能只验证退出码。
- 本轮没有运行正式 `make solve`，没有实现建议，没有声称全 347 clause 通过；未使用有序重试、PPN 规避、固定 x1、execution limit 或 workaround 文件。
- 41 份本轮运行记录见 `run-summary.json`（含 1 次 GDB 环境失败及 1 次定向参数类型错误，均保留，不算功能复现成功）；原始 103 项分类及错误行索引见 `original-failures.json`。本轮最长运行 120.417 秒。
- 全部 22 项未完成路径已逐项核实；其余大组采用源码、全组原始分类与代表复现，不把 3 个整数对照外推成全部 39 项换策略必然成功。
