# 标量浮点补充覆盖与状态迁移

日期：2026-09-26。范围为 RV64、FLEN64、非 BF16 的 49 个 scalar constructor：27 个 typed constructor（90 个 enum op）与 22 个 Zfa op。实施依据为已授权的 [修复架构](solve-fix-architecture.md)；原审计和历史缺口保留在 [标量审计](solve-audit-scalar.md)。本文只记录本轮补测；生产修复由状态与集成负责人处理。

## 实施

可重跑入口为 [generate.py](tools/solve_scalar_coverage/generate.py)。所有运行产物写入新建的仓库外目录，冻结 IR、配置、oracle、runner、生成器、输入 JSON、源码 hash catalog 和结果 manifest。成功与拒绝 runner 的共同调用方式是 `RUNNER IR CONFIG INPUT_JSON OUTPUT_JSON`；拒绝 runner 必须同时支持真实 bitword 的 `Decode_Illegal` 与执行的 `Illegal_Instruction`。

```sh
python3 agents/float_support_review/tools/solve_scalar_coverage/generate.py \
  --out "$SCALAR_RUN_DIR" --ir "$SCALAR_IR" --config "$SCALAR_CONFIG" \
  --oracle "$SCALAR_ORACLE" --positive-runner "$SCALAR_POSITIVE_RUNNER" \
  --negative-runner "$SCALAR_NEGATIVE_RUNNER" --run
```

`SCALAR_RUN_DIR` 必须不存在并位于仓库外。`--groups` 可指定逗号分隔的执行组；仍生成全套输入。每行 `case_id` 采用 SHA-256(`name` UTF-8) 的前 8 字节大端 u64，与统一 trace runner 协议一致。

历史 raw 静态输入包 basename 为 `isla-scalar-coverage-final-inputs-20260926`，manifest SHA-256 为 `dfbd50b6f58cfd8d38c01718678bbd48d85cb0c484743dd69deab44469d44df7`。5121 行输入 hash、数量、case_id、observe/expected 键集检查全部通过；另逐行核对471个历史样例的初态、机器字、constructor字段及非mstatus预期完全保持。该包生成后未统一执行，manifest 标 `PARTIAL`/各组 `NOT_RUN`；下表的动态结果来自明确列出的早期包。现行可接续包已完成FD配置及MISA分域，见文末“接续核验”；不得直接把本raw包当作最终官方输入。

| 组 | 条数 | 内容与独立预期 |
| --- | ---: | --- |
| `baseline` | 471 | 历史六组输入保持原样，生成另名迁移副本；仅按实际 FPR 写入或新增 flags 更新 `mstatus` 预期 |
| `rm-positive` | 630 | 63 个 RM op × 5 静态 RM 与 5 个 DYN/FRM 路由；有限精确运算独立求值 |
| `rm-negative` | 549 | 静态保留 RM 126、DYN 非法 FRM 189、FS=Off 112、misa.F=0 82、misa.D=0 40 |
| `minmax` | 312 | 4 操作 × 3 格式 × 26 输入对；IEEE/RISC-V 独立 min/max oracle，保留旧 flags |
| `numeric` | 1905 | 63 个数值 op；算术、FMA、SQRT、类型转换、ROUND，采用独立 Berkeley SoftFloat RISCV oracle |
| `dirty` | 448 | 112 op × FS Initial/Clean × old flags 为 0/全部置位；区分 FPR 写入、flags 新增与 flags 已含本次异常 |
| `boxing-registers` | 550 | 高编号 112、同 bank 源目的 alias 117、写 x0 34、读 x0 15、每源位置非法 boxing 108、FMV 原位搬运 2、负数 negate 12、比较 150 |
| `indices-vector` | 128 | FPR/GPR 各 32 编号读/写；默认 vector 快速访问配置 |
| `indices-scalar` | 128 | 相同编号矩阵，派生配置关闭 FPR/GPR vector 快速访问，覆盖逐寄存器分发 |
| 合计 | **5121** | 结果样例数量，不是源码 branch 数或全输入证明 |

新构造的成功数值/boxing/RM 组使用一致的 FS=Dirty、SD=1 初态；Initial/Clean 专项单独验证状态转换。`baseline` 不作该初态变换：其 471 条初始 `mstatus=0x6600` 全部保留，346 条写 FPR，其中 212 条候选 expected 从 SD=0 改为 SD=1，134 条旧 expected 已为 SD=1；其余 125 条 X 目的样例按是否新增 flags 判断，预期无需改变。每行 `state_migration` 保存 op、旧/新 expected、FPR 写入依据、newly-set flags 与源函数。

### 数值 flags 的范围

`numeric_flags.py` 按 63 个 op 分别检查可出现的五 flags；1905 条中，每个列为可能出现的 flag 都有真值见证，每个 flag 均有不置位见证。新加入 `max - negative_max` 与 `max / min_subnormal`，避免把减法/除法溢出只按同族推断。静态 RM0–4 除路由组外，还用于溢出、次正规、半整数及最大整数等可改变结果的边界。

该矩阵是包装层数值/flags 结果证据，不是 SoftFloat 内部算法分支证明。不会要求不可能的 flags 产生真见证：同格式 ADD/SUB 的微小精确结果仍是最小次正规数的整数倍，因此不产生 inexact underflow；SQRT 无 OF/UF/DZ；扩大浮点格式仅 sNaN 可产生 NV；整数到浮点没有 NV/DZ/UF；`FROUND` 抑制 NX，`FROUNDNX` 保留 NX。其它缺省不可产生项按对应 IEEE 运算域判断，不能用“没测到”替代不可达说明。

## 验证与证据

以下均为旧 IR `d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409` 的 **RESULT_PASS**：每行路径 SAT、结果差异 UNSAT、结构检查成功、返回寄存器等于独立 expected。它们不证明当前正在修改的 Sail 源码已由该 IR 实现，也不计作动态源码 branch PASS。

| 验证组 | 结果 | 外部证据目录 basename | 结果 JSON SHA-256 |
| --- | --- | --- | --- |
| RM合法 630 | 630/630 RESULT_PASS | `isla-scalar-rm-guards-20260926-v2` | `a9dfdfd792f4e6b777097befd1b41d9fa9137b16dbfc42299d54834f1e04f13a` |
| RM/guard拒绝 549 | 549/549 RESULT_PASS | 同上 | `00091d4be5c570df78adde17028b4aabcb47dc54dd3e19f474c904497f833c3d` |
| boxing/register 550 | 550/550 RESULT_PASS | `isla-scalar-coverage-d012-20260926-v1` | `a887fc4365acfe1b100835ed2aa4d553636ff989d2963510c5413656cdedd527` |
| vector寄存器128 | 128/128 RESULT_PASS | 同上 | `f1a7b7328ac2f3fe06a9d987b588b955b161f423de5bd3ab8fee7084a24e0b24` |
| scalar寄存器128 | 128/128 RESULT_PASS | 同上 | `1e4cb4be6beeee3a10687d321af47ac31c4e8a8acdfdcfe2e245fba2ba220a8b` |
| 重生minmax312 | 312/312 RESULT_PASS | `isla-scalar-coverage-d012-20260926-v2` | `d81e332f44a02d677f50a7ee4355d88294db659660c75ebaed22cf279879c057` |
| 数值1905 | 1905/1905 RESULT_PASS | 同上 | `021c666b86b36aa6ccd83e178db20a7900ec569c009b8423c32e935acdb8ddf6` |

合计 4202 个当前分组样例结果已验证。v1 的 `case_id` 采用当时的 group/name hash；v2 与现行生成器统一改为 name hash，case 的机器字、初态、预期未因该元数据变化而改变。早一版 numeric1785 的 PASS 证据仍保留为 `isla-scalar-numeric-20260926.b93cd3_e`，由当前1905包含，不重复累加。

配置 hash 为 `8247c8d467489111656f6953660670e96097a029fea458b660fe42579f86f987`。正向旧 runner hash 为 `bd362465a970a623b561680ae45e15d7ea0e28b4836dc2c439c3e981fc228425`；同时支持 decode/execute 非法的旧 runner hash 为 `7b3a086e208527ea2a0e4fe7c3cfa527be553f795177bd52377573aaaa259f89`。各包 manifest 保存实际配置（含派生 scalar-registers）、输入、runner 的完整 hash 和命令。

### 修复前的 dirty 红例

证据目录 basename `isla-scalar-dirty-red-20260926.e9sriqox`：`FADD.S f3,f1,f2`，输入 1.5 与 2.0，无异常；FS=Initial 的 `mstatus=0x2600` 应变为 `0x8000000000006600`，d012 实际仍为 `0x2600`。runner exit 101、差异 SAT，保留 cases、command、stdout/stderr。原因是旧 SYMBOLIC vector FPR setter 直接调用 `wF_from_vector`，绕开 `wF` 的 `dirty_fd_context()`；已交生产负责人修复。

该发现不通过改 expected 消除。`dirty` 448 条及历史471的候选迁移结果均等待新 IR；d012 不应被当成这些候选预期的通过版本。当前源码 setter 已出现 callback/dirty 等修复，但需要新 IR 与当前 runtime 联合复验。

## 源码 branch 分母与 trace 边界

[source_catalog.py](tools/solve_scalar_coverage/source_catalog.py) 按源码词法位置列 `if` 的 true/false、`match` 的各实际顶层 arm，保留文件 hash、行、列、offset。区分 49 个 constructor 与 94 个 `execute` 定义：BIN_RM/MADD 的 enum 在共同函数内分发，而同名其它 typed constructor 可有多个具体 op 定义。不能将 63 个 RM op 写成 63 个互异 `select_instr_or_fcsr_rm` 源码分支。

历史冻结输入包的源码 catalog 共200个唯一词法site、635个列示arm，含135个 if、64个 match 与1个 mapping；这是配置筛选前的清单，不是动态IR覆盖分母。其 SHA-256 为 `863d6ab5d5cb8a11fe15838e149e49e048783dc1405a511e1ff99bf832a1bccb`。随后补入39个 `assert` 的 holds/fails，现行工具列239site/713arm；旧清单保留为历史快照，不覆盖它的 hash 或输入。另列69个 `&`/`|` 词法候选，须核实 Bool 类型与实际 Jump 后才能加入控制边义务；其中 `accrue_fflags` 的位向量 OR 不可当短路边。

行/列按1起算，展示offset为Unicode codepoint；IR SourceLoc列按0起算，特别不能仅按行合并 FCLASS 同行的两个 if。全局去重key按固定字段顺序为 `file, source_sha256, token_start_byte, token_end_byte, kind, subcondition_ordinal`，token范围是UTF-8半开字节范围，序列化为无空白JSON后取SHA-256。普通site取关键词token；短路候选取实际operator token，kind为 `short_circuit_and/or`，ordinal为0；展示factor_index不参与hash。共享helper使用同一key去重，但每个clause、entry mode/config和arm的义务独立。

当前 catalog 同时列共享 helper 的源码条件，保留 SYMBOLIC/非 SYMBOLIC 的不同定义；这仍需与受测 IR 的配置、编译消除和 R3 SourceLoc 对齐。FLI 的 3×32 个 literal match arm、普通 min/max 的每操作6个 if、Zfa min/max 的每操作4个 if、FCVTMOD helper 的10个 if 均按实际 source site 分列，不用结果叶子数量替代 edge 数。FCLASS 实际调用 Sail 安装库的 `float/classify.sail`；该函数的10个 if、`float/common.sail` 的宽度 match 与模型 one-hot 的10个 mapping arm 也纳入带源码 hash 的 catalog。

固定 RV64、FLEN64、Ext_F/D 配置不能提供 Zfinx/Zhinx/Zdinx、RV32 双 GPR、FLEN128 或 Fatal rounding policy 的动态见证。类型限定的5位寄存器编号不可能产生 32 以外的下标；Zfa/Zfh 的 hartSupports 常量也不能通过伪造一个 misa 位关闭。具体 source site、编译配置依据与不可达说明见 [RM/guard清单](tools/solve_scalar_coverage/rm-source-sites.md) 与 [寄存器/库清单](tools/solve_scalar_coverage/register-source-sites.md)。后者列示的261个语义结果或索引项明确不直接计入 `source_arm` 分母，精确 if/match 臂使用 catalog。

`branch_ids` 是测试意图标签，**不是已观察 edge**。旧 runner 未提交 itrace，manifest 明确 `branch_status=not_instrumented`。集成负责人负责新成功/拒绝 runner 的实际 trace，使用同一受测 IR/config、同一 case_id 的 phase/terminal/path_signature 与 R3 SourceLoc catalog 关联。未观察 arm 必须补见证或给该版本约束下的不可达说明，不能直接置 PASS。

### 新 trace 绑定与全 PC 目录

[trace_binding.py](tools/solve_scalar_coverage/trace_binding.py) 复用既有 `solve_replay/audit.py` parser，独审结果、输入、每phase回调数量与实际终态块。输入 `case_id` 仍是name hash；R3 terminal metadata的 `case_id` 改为终态ID：SHA-256(`name + NUL + phase + NUL + decimal ordinal`)前8字节大端u64。结果 `trace_terminals` 与trace-map显式保存输入ID、终态ID、scope、phase、ordinal、status、path_signature和sampled。每个scope/终态ID唯一；decode可有多个终态，不能假设每phase只有一条。UNSAT/error/materialization-error终态的执行前缀不作为源码arm见证；sampled输出不证明全域完成。

最终CLI还须提供 `--run-summary --group`，默认读取 `<result>.init.json` 与 `<result>.trace-map.json`，也可用 `--initialization --trace-map` 显式指定。检查实际argv、输入/结果/trace/侧车hash、逐phase计数、runner/IR/config/runtime身份后，调用公共 [entry_contract.py](tools/solve_fix_integration/entry_contract.py) 核逐例actual R1与初始化合同。未提供摘要时仅标 `trace_only`、`source_witness_eligible=false`，不输出 `source_arm_observations`；旧c5 trace不能自动获得新R1门槛。通过后的范围仍为定向decode-first见证，官方encode-first整批收尾须另验。

共享合同接线后，真实runner侧车和Cargo feature证据确认 `serde_json` 启用了 `preserve_order`。`initialized_lets_sha256` 必须对读取后的原键序生成紧凑UTF-8 JSON，所有嵌套对象也不得排序。早先scalar夹具使用递归排序，即使顶层仅有一个let，内层 `value/concrete` 仍会改变摘要；共享校验修正后该夹具出现1 FAIL/1 ERROR。现已仅修正夹具的序列化顺序，36项工具测试重新全部通过；该次失败不是实际R1输入域失败。

[runtime_catalog](tools/solve_scalar_coverage/runtime_catalog/main.rs) 是一次性只读抽取器，依赖仓库外冻结runtime，遍历真实 `SharedState.functions` 的全部PC。输出绑定IR、config、snapshot manifest、抽取器源码和二进制hash，包含表达式AST、完整Debug指令、source、Jump方向、Goto和符号表。最终模式必须复用 `assertions_to_jumps`、公开 `install_solve_wrapper`，再 `initialize_architecture(...Optimistic,true)`；不复制wrapper实现。历史custom诊断使用model-init=false，不能冒充最终官方入口。

[runtime_binding.py](tools/solve_scalar_coverage/runtime_binding.py) 要求全PC连续、summary守恒，并将sidecar与R3的 **全部** Jump逐项比较function、PC、target、fallthrough、SourceLoc及完整指令。只允许将Debug的 `Name { id: N }` 按该sidecar符号表规范化为 `Name("z...")`，不放宽其它差异。原IR只作辅助诊断，禁止沿用未经核实的原IR PC。直接if可生成极性证书；有序match还要求同一scrutinee、明确不匹配AST、各测试之间的实际CFG链与最终源码arm entry，不能仅凭n-1条Jump猜最终臂。

早期绑定与拒绝性测试为 **19/19 PASS**，接续首轮为28/28；接入actual初始化门槛及共同freeze后，现行同一命令为 **36/36 PASS**：`python3 -m unittest discover -s agents/float_support_review/tools/solve_scalar_coverage -p 'test_*binding.py'`。覆盖错scope、错successor、漏终态、ID公式/冲突、UNSAT前缀、采样域、同行if区分、raw/runtime PC漂移、全Jump缺失、条件变化、快照hash不符等。现补实际decode回调须为正整数，允许1或3等真实路径数，并拒绝零回调和结果/终态计数漂移；三phase回调、结果trace-map与真实itrace终态须双向守恒。还拒绝旧runtime侧车重算hash后冒充新R1、缺actualR1的旧结果、被替换的trace argv及不同manifest冒充共同freeze。这是工具测试，未声明最终5121动态覆盖通过。

P1接口诊断目录basename为 `isla-scalar-runtime-catalog-20260926`。custom抽取2053函数、377025指令、25624Jump；加入P1断言变换及当时wrapper后为2054函数、378219指令、25921Jump，确有297个新增断言Jump。新R3 trace有25924Jump，全集合核验**失败**，差异准确为新wrapper PC2/5/7；P1冻结runtime仍是旧6指令wrapper，因此该失败证明禁止跨runtime拼接的校验有效。最终P2需重新冻结、构建和抽取，不沿用此目录作PASS。

源catalog还须与冻结 `model/`、`sail_lib/` 的manifest逐文件核hash，并同时匹配生成记录的source-manifest与IR hash。P1无完整Sail库manifest，不能替代最终版本绑定。[共享引用生成器](tools/solve_scalar_coverage/shared_references.py) 将六个BF16 clause涉及的共享FD helper列为引用，当前80条site引用不重复加入全局分母；`rF_BF16`特有boxing由BF16独审。固定配置拟排除清单现有38项和4项 `get_F/set_F` 候选，全部保留 `constraints_pending_final_ir`，assert和最终配置未核前不自动扣分母。

最终snapshot可一次冻结model、runtime与Sail库。显式 `--runtime-manifest` 与 `--snapshot-manifest` 的SHA完全相同时，要求manifest同时含非空 `isla/model/sail_lib`；若SHA不同，则仍须独立runtime的 `model_source_manifest_sha256` 与 `official_source_tree_sha256` 双重绑定。两种模式的runtime header hash均严格核对，不能用相似文件清单或同目录名替代同版本。

### 官方入口域迁移副本

[canonicalize.py](tools/solve_scalar_coverage/canonicalize.py) 从锁定hash的raw包生成另名候选包。5121行的pre/expected原先 `mstatus[35:32]=0`、MPP=00；RV64且hart支持S/U时仅将只读SXL/UXL字段设为2，即mask `0xf00000000` 内改成 `0xa00000000`。逐例 `entry_domain_migration` 记录原/新状态与变更位；FS、VS、SD、FRM、flags、其它mstatus位、寄存器号、机器字、字段和非mstatus预期不变。历史raw包及dirty红例不修改。

候选包basename `isla-scalar-official-domain-inputs-20260926`，manifest SHA-256为 `c0d07bb7a19cfa6579635f5a6748c468bad2668f8123d63abdb389614e677552`，5121行静态迁移检查通过，状态为GENERATED_NOT_RUN。保留name/input case ID，通过input包hash与run-id区分raw和canonical；每个trace主键还需区分配置。此包只表达候选输入，**不自动证明official域**：最终runner须用同IR探测S/U/H、真实模型初始化、完整R1约束，并实读记录cur_privilege、vtype、vl等默认状态。不能因某scalar指令没有读取某寄存器而跳过整组入口域约束。

## 2026-09-26 接续核验：现行输入、c5结构证据与迁移

现行输入包为 `isla-scalar-fd-entry-domains-20260926`，manifest SHA-256 为 `f5090e8648d0d2835c635851af9b65ac5ec462f2814815b5a20eb102031ea306`，状态仍为 `GENERATED_NOT_RUN`。已逐文件核验全部11组、5个fixed文件和raw诊断hash，逐例核验name→case_id、同配置ID唯一性及observe/expected键集；5121条均未在本轮执行。其父包 `isla-scalar-official-fd-complete-inputs-20260926` 已恢复旧配置被依赖的寄存器默认值，并显式补向量上下文；先前仅改SXL/UXL的候选不等于此包。

| 配置与域 | 条数 | 配置 SHA-256 | 用途 |
| --- | ---: | --- | --- |
| 原FD配置、默认MISA | 4871 | `20851fdbd5120066b5a0275d3780c255edb715b233fb31a2529b8e110ef723d0` | 满足真实R1和初始化校验后可作定向默认域见证 |
| 默认MISA、scalar寄存器访问 | 128 | `b0ffc776d4fff146c55868d4c5646ac2c16d108123779d8f261d24242b47cb7f` | 仅将 `__isla_vector_fpr/gpr` 从true改false，单列访问器配置义务 |
| 合法Foff：同时清F/D/V | 82 | `d3bfe08e4a1f55563a4760fe67ebaee082168aa46a868ca92e6fefbdd34fa8da` | `misa=0x8000000000141107`，canonical alternate |
| 合法Doff：同时清D/V | 40 | `ca4d75bd0bb1610f5bb6f43c6e313c70544f8b58a03c73f0436353e0443f58a7` | `misa=0x8000000000141127`，canonical alternate |

manifest的“4999默认”指默认MISA的前两行合计，不能全部写作同一官方FD配置。原122条非WARL输入留在 `raw-misa-diagnostics.json`，不计入5121，也不补默认/alternate控制臂。历史分域manifest的两个alternate组缺 `runner` 字段，执行时须明确选择negative runner；新精选包已显式记录。生成入口为 [canonicalize.py](tools/solve_scalar_coverage/canonicalize.py) 的 `--config --fill-vector-context --restore-legacy-defaults`，再以 [entry_domains.py](tools/solve_scalar_coverage/entry_domains.py) 的 `--input --out` 分域；已有冻结包直接复用。

旧c5结构目录 `isla-scalar-runtime-catalog-final-20260926` 已实核以下绑定：

- IR：`c5cbb0bbdaa9369b669aa7330531bfb1a0cf1ef7d905b071f14f510d10c7385c`；模型manifest：`128d59a5661c3efdba566682c58ee6733f4799d9afd19fa3c6a542d24d95f346`。
- runtime manifest：`6e00edd8ec17b627edcbfcd14dcdd50b4f3e6cd0ffeb11ca5343cf71a58fa084`；其515个冻结runtime文件逐项核hash一致。
- `official-fd.jsonl`：`91611fa7a4c0f0f52a8c52f4706c7eedf00231d931ceaa016ac848c351ef83e7`，2068函数、380542指令、25950 Jump，PC连续及摘要守恒核验通过。
- `source-catalog.json`：`9e00c0b085123449b05ac94f372c25e5c7f62f6165353fa3121ecca5faddc3f6`，239词法site/713arm/69短路候选。229site已有结构lowering，10site无精确anchor；`source-lowering.json` SHA为 `075663f4fd7507416745a239fe7239b3d097a089e0376780b6b510ae9cc3627d`。**实际trace全集相等仍待核验**，不能把结构证书中的runtime标记解释为动态PASS。

这10项分别为 `validDoubleRegs` 的3site、`rF_or_X_D`/`wF_or_X_D` 的内层各3site，以及非SYMBOLIC `accrue_fflags` 的1site。RV64、FPR能力及宏配置是排除候选依据；尤其 `validDoubleRegs` 外层恒false属于已折叠结果，不能把外层false也写成不可达。当前runtime含旧FmtVal，当前模型又已迁移min/max，本c5目录仅保留历史结构证据，新冻结必须重建。

接续静态审计产物目录为 `isla-scalar-resume-audit-20260926`；`resume-audit.json` SHA为 `847c3bff4dcd825a9b30fad3baaee9d6f829034bf1e66b64bd04efb678d54b7b`。其中共享control catalog含23个语义helper、112个encdec guard、1个RM mapping、81个短路候选；与69个scalar候选合并排除两处位向量OR后为148个Bool候选。既有factor提取只有8个candidate lowering，另140个frontier，均没有动态命中结论。

### 共享调用与极性仍缺的证据

`summarize_source_arms` 的全局命中及 `by_clause_phase_config` 只汇总已经看到的见证，尚不是49clause各自适用义务的分母。共享helper的同一global key只计一次，但每个clause、phase、配置与调用上下文仍需命中或明确推导；不能因某个scalar caller命中，就完成另一个scalar/BF16/vector caller。短路因素、encdec guard、生成的拒绝CFG及静态排除仍由独立表处理。

| c5共享因素 | 实际候选PC | 默认域/alternate的区别 |
| --- | --- | --- |
| `currentlyEnabled(Ext_F)`：support、MISA.F、FS | 210、222、234 | support在此能力配置固定true；MISA.F false只能由独立合法Foff域履行；FS两侧均需实际caller见证 |
| `currentlyEnabled(Ext_D)`：support、MISA.D、FS、FLEN | 249、261、273、283 | support/FLEN在此配置固定；MISA.D false属于Doff/Foff域；FS双侧须保留调用前提 |
| FPR/GPR vector/scalar访问 | 以对应配置的真实sidecar为准 | 128条scalar访问配置不能补原FD配置中已消除的另一访问器路径 |
| RM静态/DYN、保留编码和非法FRM | 绑定decode/encode/execute各phase | word的译码拒绝与执行拒绝分列，不能合成一个“非法”arm |

上表只记录源码与c5指令审查定位；true进入RHS、false跳过RHS返回false的极性仍需新runtime验证。PC234和283的RHS包含函数调用及异常处理，旧保守factor提取未接受它们，不能用“最后一个&”猜极性或补命中。最终RHS的 `currentlyEnabled(Ext_Zicsr)` 还有自己的调用与返回义务。

### min/max源码迁移的实核边界

[source_catalog.py](tools/solve_scalar_coverage/source_catalog.py) 已支持按显式 `--model-root --sail-library --out` 独立生成，旧快照缺 `fp_minmax.sail` 时保持原结果；旧c5目录重生hash与 `9e00…` 完全一致。新文件存在时列入4个纯helper，仅其两个格式match形成新词法site，ITE不虚构分支。若调用四helper但快照漏文件则拒绝。

[minmax_migration.py](tools/solve_scalar_coverage/minmax_migration.py) 核验了12个旧普通数值体在新非SYMBOLIC定义中逐字保留，并逐site检查SHA及UTF-8 token范围；迁移产物 `minmax-migration.json` SHA为 `0a3913599b843d46bf48095946b0ba61bafffcfc15f294bbafc6698c61228a0a`。当时工作树catalog为 `eaa051e5801f6267c4bde2730655b101f0b16ee0e6cc545773a52eb1029747f3`，241site/719arm。旧60个数值if保留在非SYMBOLIC定义中，新的SYMBOLIC局部体无控制site；两format match的实际保留/折叠等新IR再判。

四个FD指令文件SHA变化影响全部site：239旧key仅68保持，171必须重新绑定，新版本共173个不同key。即使源码key未变，也须重新核对runtime/IR/配置及真实trace。迁移表不转移旧见证，也不代替逐操作全结果位串/五flags等价；普通体保持、ITE等价、具体结果和源码控制覆盖是不同证据。

2026-09-27已对最终共同freeze重生静态证据。源码目录basename为 `isla-float-solve-fix-final-20260926.GThshy`，manifest为 `28fb65ee77e2c5e5c629c50b239a2e009337b47936b2fdbb897bf9c11bca055e`；新产物位于 `isla-directed-final-coverage-20260926/scalar/`，11个catalog源码文件均与冻结manifest逐hash相符。`source-catalog.json` 和 `minmax-migration.json` 分别保持上述 `eaa051…`、`0a3913…`。完整 `source-key-migration.json`（SHA `75dfe4f5e73617cbc466482d045f733c75622c181d4d34da29d53e4379332922`）以相同source/name/arguments及去注释后完全相同的声明token序列逐条对应239旧site：68个key相同、111个普通声明因文件SHA改变而更新key、60个数值if移入非SYMBOLIC；另列两个全新格式match。共享FD control及BF16引用也已按此freeze重生。汇总 `source-evidence.json` SHA为 `e97b29b9a9861f9c33f1b7c37f7c9981bb25c8797e3b22ecf86d3468f32d5ec6`，状态为 `SOURCE_FROZEN_IR_RUNTIME_AND_TRACE_PENDING`；尚未据此生成新lowering或动态覆盖结论，旧c5产物保持原样。

### 最小下一批

[select_resume_batch.py](tools/solve_scalar_coverage/select_resume_batch.py) 从锁定manifest选出未改内容的候选包 `isla-scalar-resume-selected-20260926`，manifest SHA为 `d961e5a65093244eed1120183f2e61e989aa582d523aae849a2412c61c28fd39`，仍为 `GENERATED_NOT_RUN`。

1. 先跑9条协议门槛：静态/DYN合法、静态RM译码拒绝、DYN-FRM执行拒绝、FSoff、合法Foff、合法Doff、FS Initial写FPR、scalar访问FPR31。按四配置及positive/negative runner分组。每行须有真实actual pre-state的R1 SAT及 `.init.json`，终态回调与trace双向守恒。
2. 新min/max IR冻结后跑36条：12操作分别用qNaN+数值、sNaN+数值、负零+正零，检查MIN/MINM差别、NV及零符号。它们是迁移门槛，未闭合全部数据结果或共享控制臂。
3. 门槛通过再跑完整5121，按source/phase/config/context缺口补定向见证。解析大trace须流式处理；三族共用一次分派后的各自输入，不重复整批扫描。

```sh
python3 agents/float_support_review/tools/solve_scalar_coverage/select_resume_batch.py \
  --input "$SCALAR_INPUT_PACKAGE" \
  --expected-manifest-sha256 f5090e8648d0d2835c635851af9b65ac5ec462f2814815b5a20eb102031ea306 \
  --out "$SCALAR_SELECTED_PACKAGE"
```

2026-09-27完整输入已整理为 `isla-directed-final-full-inputs-20260926/scalar/` 下四份标准 `run_suites.py` 清单：`default/suites.json` 4871条、`scalar-registers/suites.json` 128条、`f-off/suites.json` 82条、`d-off/suites.json` 40条。总体 `index.json` SHA为 `d0f66d3575ebd39eb303f0fe8dcedd605775f4414c788df9f0da4b7b20ce6de8`，列各配置与清单路径、完整hash、数量。11个输入JSON与4份配置全部按原字节复制，输入manifest `f509…` 及最终源码manifest `28fb…` 同样保留原字节；raw122未复制。负组统一为 `mixed_negative`，选择decode runner；scalar trace审核也已接受此kind。已用真实 `run_suites.resolve_input/RUNNER_KEY` 静态核验全5121条清单兼容性，工具测试仍为36/36通过。本准备动作未执行模型，运行结果须另记。

## 上述准备阶段的剩余（已由下节进度更新）

1. 等min/max与FmtVal等生产修改冻结，重建IR/runtime/sidecar，先完成上述9+36门槛，再重跑完整5121条，尤其dirty448及迁移471；保留旧输入和失败证据。
2. 将已完成的源码 site、共享寄存器/boxing、guard、库函数及固定配置排除依据，与新 IR 的实际保留/编译消除逐项对应。
3. 用真实 trace 闭合每个可达 source arm。若仍缺动态 edge，标待补证并补最小输入，不以当前4202条结果通过代替。

## 2026-09-27 最终冻结后的完整审计与 caller 收窄

本节覆盖前述“待新IR/待完整5121”的状态；历史输入、旧c5证据及原运行路径保留。受测版本为共同manifest `28fb65ee77e2c5e5c629c50b239a2e009337b47936b2fdbb897bf9c11bca055e`、IR `1dcc80812b8beaba49abaebf605e8090c2796b5930aefa36635b478c5f2b8180`。新审核产物根为 `isla/target/float-support-review/final-coverage/scalar/`。

### 实际运行与入口审核

完整11组 **5121例 / 14643终态** 已通过模型结果和严格trace审核：default 4871、scalar-registers 128、Foff 82、Doff 40。每组逐项验证实际runner/argv、输入/result/trace/init/trace-map哈希、R1实际初态SAT、源码manifest/IR/config/runtime绑定，以及 **25772个runtime Jump全部逐项相等**。终态与回调双向守恒，负例不得越过拒绝阶段。最终汇总 `full-audits.json` SHA为 `288ca03e66b956cbc7c6b4b82613b9de10fa1f7bd6c6fa16d6a1b5441202effe`；旧 `full-audits.partial.json` 作为进度快照保留，不能再据其文件名声称尚未审核完整批次。此结论不等于 caller 的全部源码分支闭合。

共享入口合同按 `serde_json` 的原键顺序计算完整 `initialized_lets` 紧凑UTF-8哈希；数值相同的32位指令十六进制拼写允许前导零变化，值变、负号和越界仍拒绝。使用 [audit_suite.py](tools/solve_scalar_coverage/audit_suite.py) 时只复用同版本只读sidecar，每个新组仍独立核验全部Jump和实际入口。

### 固定配置与类型域的 caller 证明

[caller_obligations.py](tools/solve_scalar_coverage/caller_obligations.py) 按实际根调用点保留 `(clause, phase, config SHA, root function:PC)`，不同caller的共享命中不能互相补证。49个scalar constructor的初始静态闭包每配置17035项只是过近似候选，不能拿它作为已经确认可达的分母。BF16通过独立六caller定义生成自己的331项表，并消费自身trace；没有转移scalar见证。

default的类型收窄阶段表 `default/caller-typed-cfg-v2.json` SHA为 `662cb1024b70538bae5ed64519cdfeacc6a3cc1f32f5e78ad482659abdf3f8f4`，保留所有原候选，当时分类为：

| 项目 | 数量 | 证据口径 |
| --- | ---: | --- |
| 此caller的实际source arm见证 | 2151 | 同clause/phase/config/rootPC |
| 固定CFG排除 | 14252 | 配置、无写/逃逸扫描、实际能力函数和常量def-use |
| 类型与实参CFG排除 | 624 | IR位宽、隐式尺寸、逐root调用上下文及冻结dependent type |
| 待证明 | 8 | FCLASS总分类最后else/assert共6项；两个D move断言 |

[fixed_cfg.py](tools/solve_scalar_coverage/fixed_cfg.py) 对内部FPR/GPR flag实扫全部runtime指令，仅发现8次直接Jump读取，无写或地址逃逸；对 `hartSupports` 直接解释同IR的确定CFG路径，证明F/D/Zicsr/S/U为true、Zfinx/Zdinx/H为false。[derived_cfg.py](tools/solve_scalar_coverage/derived_cfg.py) 只解释唯一且支配使用点的定义，对未知值保留未知，并绑定尺寸let与FCSR保留RM策略的IR初始化。最终 `default/fixed-cfg-v3.json` SHA为 `828b2a1c77e37e4b292c4447b677a7995ce8f9abe0e817a1067b0423c1a0d87b`，共114个恒方向Jump。`entry-invariants.json` SHA `7a8da62364138cf8febd0b4beee0cd7828802533abf9d096d5024f00ee3a6c61` 绑定原冻结三runner的构建、源码、入口合同与RV64寄存器列表，核实非Target初态覆盖只允许misa，内部flag/let不会被输入覆盖。

后续 `entry-invariants-v2.json`（SHA `a02a45f8770245aaa63e6a49f8faf087cb877f1b547a7eb6f0c3c6b47136d153`）补核冻结 `isla-lib/src/init.rs` 的初始化优先级：显式配置值在 `if initial_registers.get(id)` 分支写入，model register初始化只在else中执行，故模型flag=false默认不会覆盖配置true。新U/S与alternate runner通过 `integration/phase-purity-increment-binding.json`（SHA `640af0d934315e8bcd9edbad377548e45c1611a2d9bf7841166c44deb122dd6f`）所绑定的完整R1验证函数逐字相同证明，沿用同一非Target覆盖限制；动态见证仍各自核验新binary与实际trace。

[typed_callers.py](tools/solve_scalar_coverage/typed_callers.py) 保存176个实际类型调用上下文、162个根调用点。`Bits(N)` 只提供宽度，不能推出两个动态位串相等；格式不匹配臂按每个caller的实参分别排除。MINM/MAXM包装取返回payload宽度时，另核冻结Sail的dependent result type、成功生成manifest以及对应IR tuple结果类型。所有CFG/类型排除均检查不得与已有真实见证冲突。[refine_caller_candidates.py](tools/solve_scalar_coverage/refine_caller_candidates.py) 保留被裁候选和每项依据，不静默删分母。

### User / Supervisor 增量

[privilege_inputs.py](tools/solve_scalar_coverage/privilege_inputs.py) 从已审独立输入派生User/Supervisor各49条合法baseline、49条FSoff拒绝及4条FS Initial/Clean代表，共 **204例**。仅改变初态 `cur_privilege` 和name/id，指令、其余初态、全部独立expected保持。实际新runner已运行通过；6组 **416终态** 已完成与原批相同的完整审核，保存在 `privilege-audits/`。

`privilege-caller-witnesses.json` SHA为 `b8ccb5b3766ed2472d0212d3991cf7a7803ffc7f734d30b0317a453617666cd3`，逐例核实际R1绑定的枚举值确为 `User` / `Supervisor`，并为98个 `(privilege, clause)` 各保留自己的合法decode/encode/execute与FSoff decode拒绝见证；Machine命中没有复制到新特权态。此表覆盖所选代表及其实际source arms，不声称穷尽每个特权态的全部数值组合。

[privilege_dependencies.py](tools/solve_scalar_coverage/privilege_dependencies.py) 的 `privilege-inputs/fd-privilege-dependencies.json` SHA为 `8c171fe46dabb585f5f549140b7e798409c055d3485458cbc0bb77dbc2294837`。它按runtime形参实际剪出F/D/Zfinx/Zicsr四个启用切片：F/D依赖misa、FS、flen与固定Zicsr；没有读取cur_privilege或stateen。Zfinx的实际短路Jump在能力false后跳过stateen调用。SXL/UXL均为2；Virtual两态不从本批的非虚拟S/U见证推断可达性，另由公共R1负控负责。

### alternate caller 补齐与当前剩余

用户要求继续49×4显式caller义务；不能把Doff下仍可达的S/H遗漏项标签成域排除。[alternate_caller_inputs.py](tools/solve_scalar_coverage/alternate_caller_inputs.py) 已生成并完成88例最小增量：scalar-registers补47个合法caller、Foff补9个失能拒绝caller、Doff补32个合法S/H caller。Doff已有的H转换拒绝仅针对其中D转换操作，仍补同constructor的H sqrt合法代表。输入索引 `alternate-caller-inputs/index.json` SHA为 `6bebeccbd9ebd290f3961544802ccb5a618ae386cecb5cc56df8668ea88cc018`，保留其运行前GENERATED_NOT_RUN状态；实际88例/246终态已全部PASS并通过严格R1/trace/source/runtime审核，后续证据位于 `alternate-audits/`。Foff9条保留的旧name/branch_ids仅为源输入历史，当前FS=Dirty与misa失能事实及实际trace决定覆盖。

[caller_configuration_index.py](tools/solve_scalar_coverage/caller_configuration_index.py) 生成 `caller-config-index.json`，SHA为 `ff44e4d3310144cda2fd7e6bb6592cfdbd99ea982698ab0fd1b9a373cc271084`。该表具有49×4＝196个实际caller/config单元：default 4871、scalar-registers 175、Foff 91、Doff 72，共5209例/14889终态。每单元保留自身case ID、实际R1、终态阶段、source arm/context与审核hash；alternate可执行caller均有合法代表，Foff49caller均有实际译码拒绝代表，Doff的32个S/H caller均有合法代表。它不把选定拒绝代表外推成该constructor所有参数不可达，也不声称所有数值分支在每配置重做笛卡尔覆盖。加上独立User/Supervisor204例，当前scalar累计 **5413例 / 15305终态** 已完成结果及严格绑定审核。

当前仍须：把同体/typed配置前提与alternate实际caller代表联立；独立完成shared-control的guard/短路factor极性与caller绑定。上述8项及24个fle、9个固定源码site已有下述独审和实际返回见证。普通source241词法site或helper候选表的闭合不能覆盖shared-control。

本轮工具验证命令为 `python3 -m unittest discover -s agents/float_support_review/tools/solve_scalar_coverage -p 'test_*binding.py'`，**44/44通过**。新增负控覆盖跨caller/phase/config/root误绑定、内部配置写入和地址逃逸、错误Jump方向、非支配定义、未知布尔值，以及禁止由同宽推断同位值。

### 四配置 helper 同体前提

[configuration_equivalence.py](tools/solve_scalar_coverage/configuration_equivalence.py) 已生成 `configuration-helper-equivalence.json`，SHA为 `680e669f1d9be150259db0afb836ec016515e670087d0ca3231c0175bdd00b46`。四配置共有的119个类型helper完整函数体及162个实际根Call指令逐项一致；IR、runtime manifest、抽取器源码/二进制、初始化尺寸let同版。配置差异逐键限制为accessor的两个内部flag，或Foff/Doff的misa。

比较只按各自sidecar符号表解析Name ID；Primop地址仅在同进程有明确alias绑定时规范化，并保留完整运算、类型、Call旗标与alias集合。9个无alias的opaque reset Primop位于所比较helper图之外，未被判定语义相同。此证据支持共享类型/数值helper推理的同体前提；每配置的guard、访问路径、实际caller见证仍使用自身证据，不能把default动态命中复制到alternate。

### 33个无 lowering site 的独审与实际返回

独审 `domain-proofs/independent-20260927/review.json` 的SHA为 `6df48e91f5e7506b1f98f3684f65c871e2b8bd498155ec4878d74c93af4053ed`。独立重跑原两证书得到相同hash，并核实全模型中fle的15处源码引用是3个定义及12个ordinary调用；成功SYMBOLIC生成的完整调用闭包无旧fle定义/调用，12个对应执行调用均实际指向pure helper。因此24个fle词法site在该受测模型不发射/不调用。

另外9个site须分别处理：`rF_or_X_D`/`wF_or_X_D` 的6个X路径site及 `validDoubleRegs` 的2个内层site完整不可达；`validDoubleRegs` line220外层条件只有true臂固定不可达，false臂仍需实际正常调用。不能把这9项写成整个函数不可达。

[completed_valid_double.py](tools/solve_scalar_coverage/completed_valid_double.py) 生成 `default/valid-double-completed-calls.json`（SHA `01333f4ab897c433207cc9464434712c888ee68c8c7696df3a27a0d743219ffa`），绑定原baseline严格审核、trace、trace-map、完整runtime与独审证书，核实146个自身caller/phase的实际调用。每个终态均有依序的内部PC3异常检查false、PC7短路左因子false，以及调用点紧接Call后的异常检查false；完整函数CFG后缀赋 `return=true` 并正常End。这里的正常返回由真实调用点续行和完整CFG联合证明，没有虚构trace return事件；PC7也没有被误称为源码外层if的Jump。与独审的固定条件证明联立后，只给对应同case/context的外层false臂见证。

代表为 `baseline_migrated_fsgnj_d`，scope `F_BIN_F_TYPE_D`，输入ID `14946900138538009118`，decode终态ID `11885295524347169614`，状态 `decoded`，context `zext_decode:0 > zencdec_backwards:15075`。此组见证不替代其它配置或caller自己的调用证明。

### FCLASS / D move 八项闭合与 alternate 独立收窄

`domain-proofs/fclass-move-independent-20260927/review.json`（SHA `3cb9a5e897ce2f14031812a698fce557b727f6d92e4ad5cf906e07bc8fbc1f9c`）独立核对FCLASS六个真实谓词调用与同实参、对应Jump的完整false链，以及true路径只能正常End；错误实参、错误谓词和true路径回入false链的3个负控均被检出。16/32/64位的指数/尾数六分类互斥且完备反例查询再次全部UNSAT。两个D move的 `gteq`、短路、唯一赋值及断言handler也按实际runtime复核；固定只读xlen/flen均为64。

现行 `default/caller-domain-reviewed.json`（SHA `893b925404274c223c8f295417ea2d75d1fa2699f2660a14eb1055827f0d9c1e`）保留17035个历史静态候选，给出2151个本caller实际见证、14252个固定CFG排除、624个typed排除及8个独审排除，已lowering的普通source候选不再有pending。33个无lowering site及shared-control仍按各自证据单列；此表不声称全部源码控制已闭合。

三份alternate分别消费自己的sidecar、配置、原运行组及88例增量，重生 `caller-typed-cfg-v3.json`；每配置自己的114个恒方向Jump均完成二次常量传播收敛。其阶段计数如下，未观察候选仍保留，后续由入口拒绝域或显式数值等价关系继续处理：

| 配置 | 自有见证 | 固定CFG排除 | typed排除 | 待域/等价联立 |
| --- | ---: | ---: | ---: | ---: |
| scalar-registers | 949 | 6729 | 624 | 8733 |
| Foff | 0 | 14252 | 624 | 2159 |
| Doff | 514 | 14252 | 624 | 1645 |

命令与各步stdout保存在 `alternate-refinement-commands.json`。Foff的0表示普通source执行臂无见证，49caller的实际decode拒绝仍由196单元索引和共享guard证据承担。

### 读实参投影与首批共享因子

[accessor_read_equivalence.py](tools/solve_scalar_coverage/accessor_read_equivalence.py) 的 `accessor-read-equivalence-v2.json`（SHA `827e8b1771473cc6c628653d76cd43594717ad6d7aa908c1e2fa34c4f05e1c6d`）已完成128对 `get_F/get_F_bits/get_X/get_X_bits × 32索引` 的严格runtime CFG解释。64位寄存器值保持为不解释的独立符号，default与scalar访问器逐项返回同一个符号；X0返回绑定IR的zero_reg。证明核对FPRs/GPRs实际IR初始化索引、无runtime写入或地址逃逸、Rust vector primitive按 `regs[i]` 取值和实际配置flag差异；交换FPR槽0/1的负控被检出。当前状态为待独审的读数值投影，须与每个root的数值实参切片联立，不能扩到写回、回调或全部事件。

[shared_control_witnesses.py](tools/solve_scalar_coverage/shared_control_witnesses.py) 已消费独审 `vector/independent-predicate-review/shared-fd-control.json`（SHA `6b167bf2a0dafeaf68bb922d42659d0ce9c705f751e7ff0aabbaba61a2c8fbb3`）的5个短路因子，形成 `default/shared-control-owned-witnesses.json`（SHA `364fb34ef8eb4c55eee1dfc250a582649f42f63558f2a5b9e2d15c69d2ebe3b3`）。default原8组共827个按自身scope/phase/root/context去重的实际见证：RM有效性PC7与select PC11双向各45；F能力PC210 true为191、MISA.F PC222 true为191、FS PC234 true/false分别为178/87。调用点按本clause源码执行定义或mapping声明及实际Call定位，避免将其它指令探测归给当前caller。此表只给已观测精确绑定；固定侧、phase适用域、其它因子与完整guard语义仍单独审定。

### 访问器独审修订与数值前缀

上节v2为历史候选，现行读投影是 `accessor-read-equivalence-v4.json`，SHA `c61888aa9883a224dfb7d4d047ceb6f6f4d7b9d5a1603f1cb078ebbaf2afd8d8`。独审 `independent-accessor-read-review/review.json`（SHA `9b380a4c13a08a47b7d5b34a7cc212a141fdd3ed9724110686b4b5d6871a772d`）状态为 **PASS_READ_VALUE_PROJECTION_ONLY**：128对合法具体索引、全部64位寄存器值均满足相同返回值关系；X0固定为零。独审重生逐字一致，并核对两侧共677条实际解释路径、69/900个去重函数PC、两个配置的flag差异与冻结Rust具体索引primitive。

独审发现并修复两个工具前提漏检：v2未验证向量let最终临时复制及global绑定，v3未识别zero let无SourceLoc的尾赋值。v4分别以完整37/7语句白名单核对，交换FPR槽0/1、最终复制改成slot0更新f1、末尾追加无Loc的zero_reg=1三个负控均被拒绝。冻结IR的实际let经人工核实始终正确；旧v2/v3候选及负控保留，不能作为最终证书使用。

[numeric_prefix_equivalence.py](tools/solve_scalar_coverage/numeric_prefix_equivalence.py) 的 `numeric-prefix-equivalence-v3.json`（SHA `d47d4a909cef6954fa2b8e8f1903dda1b09fe442a1925243f7e0a9701bfcb0de`）已绑定v4及最终独审、entry-invariants-v2、各自fixed CFG/sidecar和共同版本。按每caller特化实际Kind dispatch，求前向可达与反向到root交集，得到162个root、2526个execute PC及28个callee的840个PC；四配置逐项同体，直接体系读仅FCSR。工具拒绝体系寄存器写、复合目的地、Ref逃逸及未知指令；读访问器与静态能力在证书边界处组合。

前缀证书仍为 **CONDITIONAL_NUMERIC_ARGUMENT_EQUIVALENCE_FOR_REVIEW**。其前提是两侧合法译码为相同constructor/fields、相关初态相等且各自能到达root；它不转移物理分支命中，不覆盖写回和事件。root后的读wrapper还须按getter读投影组合，不能把accessor内部不同路径称作数值域等价。scalar-registers原8733项pending中，rF/wF/wX/rX分别为4070/1883/1092/443项；这些源码索引臂仍有独立义务。

### 共享控制库存增补与当前分母

旧23 semantic/81 control-factor库存遗漏了实际guard依赖：haveHalfMin、Zfbfmin、Zvfh，以及后者的Zve32f→Zve32x→Zvl32b依赖。新 `shared-control-catalog-v2.json`（SHA `f1ad3580836947a274aaeb258f7134f312d0712ae0adf03588af553894967cc0`）为 **34 semantic、93 control factors、112 guards、1个RM mapping**；新增11个predicate和12个factor，旧global key全部保持。另修正6个guard表达式显示误含下一声明的`$[split op]`属性，key不变。

[shared_control_addendum.py](tools/solve_scalar_coverage/shared_control_addendum.py) 核实旧模式逐结构重生原 `25115d9f…` 库存，新模式逐字重生v2，全部源码SHA在共同manifest中；175条源码helper/扩展依赖均落到已列predicate，删除haveHalfMin的负控会失败。`control-inventory-addendum/review-input.json`（SHA `291f58ef9e55ed6ca1d865102fe58f5c68aa172981a47aa8d1ae2911beb103d6`）列11个新增predicate的actual SourceLoc指令候选。它没有把缺少SourceLoc的Goto/handler自动视为闭合，完整函数CFG仍交独审。

当前全部Bool词法候选表为 `control-inventory-addendum/all-factor-dispositions-v2.json`（SHA `de0b1bfcd7e6e75dacdd2283fea351d28a471b40cdd6d63f821c407be0114025`），旧148项及状态全部保留，新增12项待审，合计 **160项**；另列2个位向量OR，不纳入Bool短路。分类为23项已有独审极性/自身观测而域待闭合、24项fle整函数未发射、36项ordinary不在该构建、5项数值因子待审、60项encdec因子待审、12项新增依赖待审。旧148是旧库存版本的分母。

原23 semantic的独审 `vector/independent-predicate-review/scalar-fd-predicates.json`（SHA `c5065ae74f3be51eda45dfa9c69b7376b35937984e1ebc6a18a9866589590b95`）只覆盖原子集。其21个短路因子的default自身绑定见 `default/shared-predicate-factor-owned-witnesses.json`（SHA `23357a779315a9f24da8f052768430b0b9bbb84007ef37093551919b73b88ae1`）；与首批5因子去重后，`default/shared-short-circuit-observations.json`（SHA `37fbdef17506d1204007c915fe98e4aea384f52bd4eda36b2b90f5a4e198eed2`）含23因子/46方向/1811个自身caller/context见证。新增依赖不自动继承这些见证。

### 精确guard的源码配置域候选

[guard_truth_domains.py](tools/solve_scalar_coverage/guard_truth_domains.py) 已生成 `guard-truth-domains.json`（SHA `0c0ac90485b4d9c033fee8c5c52e9cfdf4bca818fa96824a3e493cbbcc1f693b`）。每配置逐个绑定112个精确guard，以FS!=0、VS!=0、三个V能力结果和stateen的64种布尔组合穷举源码表达式；三个V能力保持全称未知，其余12个能力分别解释各配置的实际hartSupports路径。MISA与各自配置相等，XLEN/FLEN64由初始化let绑定；validDoubleRegs依赖Zdinx关闭、正常返回及其独审/四配置同体前提。

| 配置 | 源码条件为FS!=0的精确guard | 源码条件恒false的精确guard |
| --- | ---: | ---: |
| default | 112 | 0 |
| scalar-registers | 112 | 0 |
| Foff | 0 | 112 |
| Doff | 72 | 40 |

该表状态为 **SOURCE_TRUTH_DOMAINS_FOR_REVIEW_RUNTIME_GUARD_COMPOSITION_PENDING**。精确guard分别保留source key，因此Doff的H/S constructor中需D的转换编码仍为拒绝域。完整runtime predicate/guard正常返回、短路极性、声明到constructor fields/root路径的关系以及数值前缀独审尚须组合；当前不据此提升alternate覆盖状态。

[root_guard_domains.py](tools/solve_scalar_coverage/root_guard_domains.py) 的 `root-guard-domains.json`（SHA `3579acd1e1b225894da99b7108678e7a6d76f38194a9c7d0fc3f6459240bc421`）已按mapping的constructor参数位置与actual root SourceLoc所属execute声明完成源码对应。default/scalar的162个root均关联到FS!=0域，Foff全部拒绝，Doff为130个FS!=0、32个拒绝。32个仍可准入constructor中只有`F_UN_RM_FF_TYPE_H`含混合guard：`FCVT_H_D`和`FCVT_D_H`两声明拒绝，另3个操作保留。此表仍为源码关系候选，生成decoder/execute的Kind/op dispatch须另行独审；它不增加实际命中。

本轮现行工具实际运行完成，原44项绑定测试再次通过，新增/修改Python文件通过py_compile；没有新增模型动态执行，累计仍为5413例/15305终态。实施命令与产物hash记录见证据根的 `scalar-proof-extension-commands.json` 和 `scalar-root-guard-command.json`。

### 1dcc后续独审：当前40个短路因子

随后收到两份独审：`vector/independent-predicate-review/scalar-five-factors.json`（SHA `ef413a9673a014c9ce70b5a9268a4fd9ca7613cb5ca80ffa26cbc99f8bc61b22`）核实validDouble PC7、D move PC7556/7605、fcvtmod PC23/52的完整表达式与AND极性；`scalar-control-addendum.json`（SHA `22bfed41a2ad11c6f2947bc0a6e6d8107c9322a327e7d791f504663a797cdfd7`）核实新增11个predicate与12个因子，包含haveHalfMin两OR、V依赖链与实际能力路径。两份分别通过3/2个语义负控，不扩写旧23项证书。

消费原default八组已审核trace后，`default/five-factor-owned-witnesses.json`（SHA `8a467c0e360aecfbb7cfa10b726675316e188b08984f239eb0c8b347e45fa02a`）有58个自身见证；`default/control-addendum-owned-witnesses.json`（SHA `c5b200514c03f1f43f6ceab35a74a5360fa7182cc865ab460d2a99c1c3ebfb08`）有27个。D move直接execute分支按自身clause、execute phase、空顶层context与实际Jump所属声明区间绑定；2个拒绝性测试先红后绿，错caller/phase/嵌套context/文件/区间边界均不计命中。

合并表 `default/shared-short-circuit-observations-v2.json`（SHA `a51cf95296e56bc94881433e7397601db5c25edf5b4904d93059256955f7b5d3`）当前为 **40因子、80方向、1896个自身caller/context见证**。`default/all-factor-dispositions-v3.json`（SHA `ee7b9f67a609194e348d23bdc864bc49ca915f7d72bdcdd2f590dc20361ac8e6`）保留160项总分母：40项独审极性/实际观察但域待闭合，24项fle整函数不发射，36项ordinary不在该构建，60项encdec短路仍待完整guard独审。固定侧和未观测caller/phase仍有独立域义务；这次只重审已有trace，没有新模型执行，也没有将1dcc证据迁到下节的新IR。

## 2026-09-27 统一模型348147：新源码输入与全量严格审核

新证据独立位于 `isla/target/float-support-review/final-coverage/integration/p1-348147/scalar/`。IR为 `348147f833432008d559be0e673dbd45982148b0750cd4533c68589a55aac061`，候选源码manifest为 `1890f0a13d9dc877185c46bcf398ea0b2f12fbe3b0ee6802adb5de0a845f1ed9`；generation保留真实生成来源 `749c3c5b…`，经v7重包证明与候选源码及运行器manifest `28fb65ee…` 关联，不改写生成记录冒充同一个快照。

[prepare_source_catalogs.py](tools/solve_scalar_coverage/prepare_source_catalogs.py) 只用新冻结model和Sail库重生词法输入，对15个来源文件核验manifest SHA及每个global key的实际token字节范围：

| 产物 | SHA-256 | 范围 |
| --- | --- | --- |
| `source-catalog.json` | `4f07df5365b9a5673b8f9f5ea9a5bc1c75da48b152ef41f719a8324de5d0b003` | 49caller、94execute定义、178普通site：72if/66match/39assert/1mapping |
| `shared-control-catalog.json` | `e9af5d95f9d6c944e089cdac304de6e26772a2980a0506be39c42fa25818adc3` | 34predicate、112guard、93control factor、1 RM mapping |
| `shared-fd-references.json` | `338b3c0a0af7e39e40228b6545c3732139d4933aa32f4fa0a34ae7f663b17725` | 新版共享key引用输入 |
| `source-inputs.json` | `4e1cfe0a615068629e421a3fb9a1ab5f36374d68e9260208e9898a99c48b9d99` | 合并124个Bool词法候选，另列2个位向量OR；初始状态为待strict |

CLI新增显式 `--source-bridge`，`audit_suite.py` 同时支持独立 `--runtime-manifest`，省略时保持旧snapshot默认值。每个trace报告保存bridge实际文件SHA；bridge须由共享 `verify_source_snapshot` 重新执行验证。两个CLI透传/兼容测试先红后绿；连同共享bridge负控及原测试，本时点工具测试 **55/55 PASS**。

真实源码绑定正测 `source-binding-positive.json`（SHA `07fe37eb05d122e57327a9efee3f050a636418ea5b8094460a70eef33b35d504`）先通过，随后对该IR的新full结果做八套件审核：

| 新运行集合 | 输入例数 | 完整终态 | 严格审核 |
| --- | ---: | ---: | --- |
| default原八组 | 4871 | 14137 | PASS |
| scalar-registers/Foff/Doff原组 | 250 | 506 | PASS |
| 三alternate caller增量 | 88 | 246 | PASS |
| User/Supervisor增量 | 204 | 416 | PASS |
| 合计 | **5413** | **15305** | **PASS** |

`strict-audit-summary.json` SHA为 `2ece8fd68fbd8b7116074414a48363be26c729726f4874cba8030e158f8442e2`；逐组报告在 `strict-audits/`，完整argv、stdout/stderr与审核hash分别保存在汇总和 `strict-audit-logs/`。审核核对真实初始化R1、输入/结果/trace/侧车、runner/IR/config文件hash、终态守恒、实际runtime全Jump目录及新源码/bridge绑定。默认大组审核119.103秒；这是审核时间，不作新模型求解性能结论。

`source-binding-complete.json`（SHA `c68a206424a23b2935356c403b962c8d9fbbd3603c090e5f95dbeb0a23fdf4e3`）补核ordinary/shared-control共15个源码文件并关联全量strict汇总，完成初始source-inputs待绑定项。以上PASS限于新运行结果与完整证据链；**新版本源码分支闭合仍为false**。旧1dcc的静态排除、typed/caller域证明、predicate证书和实际edge见证均未转记，新catalog原SHA保持冻结。

## 2026-09-27 旧1dcc静态收尾：范围合同、guard观察与正常域候选

本节继续处理旧 `1dcc8081…` 的已有证据，没有新增模型执行，也没有修改上节348147的冻结结果。以下产物路径以 `isla/target/float-support-review/final-coverage/scalar/` 为根；`source_branch_closed` 仍为false。

### 条件数值前缀合同

数值前缀v3随后收到独审 `independent-numeric-prefix-review/review.json`（SHA `d5d47cee88a82e33de2d80a2a1eb34962ce1a0c98c92af883b4298c0fbf50999`），结论为 **PASS_CONDITIONAL_ROOT_ARGUMENT_EQUIVALENCE_ONLY**。配套 `defined-values-review.json`（SHA `7a0758a2e0e907c0e31bce9a720c862e52c627be826ad1766fbca042f656496b`）确认162个root和28个callee所选CFG均无环、局部值在每个前驱上先定义，异常控制初值绑定冻结LocalFrame的false；原四项负控均拒绝。

[prefix_contract.py](tools/solve_scalar_coverage/prefix_contract.py) 以外部批准的两个独审SHA为输入，实核candidate、IR、manifest、四配置sidecar/fixed CFG、getter投影独审及全部依赖哈希。输出 `numeric-prefix-contract.json`（SHA `c3edc1300be5a17150980115d30bb5e49a31a818e36350bbb489ad92e30cb07d`），仅导出 `conditional_root_arguments_equal`。合法同constructor/fields、相关初态相等、两侧各自到达root仍是前提；root后helper、返回、写回、事件和物理edge迁移没有因此闭合。5项范围/版本/未定义局部值测试先红后绿。上文“前缀待独审”保留为历史阶段，现以这份范围合同为准。

### 112个guard的局部合同及实际观察

正式独审 `vector/independent-predicate-review/scalar-encdec-guards.json`（SHA `ea01a58b6e9cfd9917a6b930ab6da992aa0c81ddc08fee85bf878371ed18fc09`）证明112个guard的224个阶段表达式与局部mapping结果、60个源短路因子的120个阶段lowering，并通过5项负控。decode拒绝只使当前mapping返回None；encode拒绝只跳过当前mapping继续匹配。旧初版未加强disposition的证书不再消费。

[guard_contract.py](tools/solve_scalar_coverage/guard_contract.py) 绑定正式独审SHA、实际IR/配置/sidecar、源token和mapping声明，逐项检查两个phase的完整性、guard结果Not极性、Goto链、短路常量及actual Call。输出 `encdec-guard-contract.json`（SHA `01d5ac7b61d24ec997e8993d82373362072f16e1d9109e1a9fe8f9c1807634ac`），状态为 **ACCEPTED_VERSION_BOUND_SCOPED_CONTRACT**，只签局部正常mapping结果。错clause/phase/source key/极性、缺phase、跨IR、范围升级、错局部链和不完整Bool表等10项测试通过。

[guard_witnesses.py](tools/solve_scalar_coverage/guard_witnesses.py) 消费原default八组strict审核，按精确mapping源site、实际edge、当前constructor、phase、配置及完整Call链归属。它直接识别encode顶层site，无须虚构外层Call；观察到的edge不冒充return事件。产物 `default/encdec-guard-owned-witnesses.json` SHA为 `93fbcbc2df2075214b712b8477ba441fdd02a7750f004d0b67ff430696c87faa`。

| 库存 | 实际自身观察 | 保留未观察 |
| --- | ---: | ---: |
| 448个guard阶段方向 | 336：decode接受112、decode拒绝112、encode接受112 | encode拒绝112 |
| 240个短路阶段方向 | 178，涉及全部60个源因子 | 62 |

本表每个scope/phase/context/edge保留一个实际终态，其原审核观察数分别为1190和640；6项归属测试覆盖错constructor、phase、调用栈、实际callee、配置和不完整终态。某个精确mapping被本constructor尝试，仍不自动证明其常量op与最终AST字段相等。

[merge_control_observations.py](tools/solve_scalar_coverage/merge_control_observations.py) 保留旧词法分母并合并上述因子。`default/shared-short-circuit-observations-v3.json`（SHA `f85b8d994f54ddf817adfa7eda40c8f5f797b745e4633fbf888e7d4b7f7e7e76`）为 **100个源因子、320个实际阶段方向、2074个自身见证**。`default/all-factor-dispositions-v4.json`（SHA `0ebc2c472bd0297963da48404dcacaf612a75c8043f034d2a0539f26bf84e924`）维持160项：40个非encdec与60个encdec有独审极性及观察但域待闭合，24个fle整函数未发射，36个ordinary不在该构建。旧v3的60项guard极性pending由本节明确更新；各caller/phase/config的分母仍需组合。

### 四配置条件正常guard域：候选已实施，独审待完成

[normal_guard_domains.py](tools/solve_scalar_coverage/normal_guard_domains.py) 直接组合已独审的19个Bool谓词、15个能力项和224份guard真值表；源码解释候选只作结果对照。它分别读取四份实际sidecar，重核11个函数的证明范围及runtime/初始化身份。普通相关函数比较完整body；`zhartSupports`只比较独审15个能力实际路径的并集。第一次整函数比较因另外两处无alias opaque primitive而拒绝，记录保留在 `normal-guard-domain-command.json`；这些PC不在所用能力路径中。修正后逐一显式记录比较PC，加入“选中opaque仍须拒绝”的负控，不能把相同指针文本当作语义等价。

`conditional-normal-guard-domains.json`（SHA `5d2a29e98a895a3574ff2ac024308acfcb5711e1ddcf83189f46b6599545525c`）为 **CONDITIONAL_NORMAL_GUARD_DOMAINS_FOR_INDEPENDENT_REVIEW**。实际成功命令及31.610秒、退出0记录在 `normal-guard-domain-command-v2.json`。每个配置仍有224个阶段guard和120个阶段因子：

| 配置 | 正常接受条件FS非零 | 正常接受条件恒false |
| --- | ---: | ---: |
| default | 224 | 0 |
| scalar-registers | 224 | 0 |
| Foff | 0 | 224 |
| Doff | 144 | 80 |

必要前提是实际已进入这个精确guard、正常求值完成、MISA为对应配置值、求值期间FS/VS原子稳定、XLEN/FLEN为64以及同状态同实参调用的Bool原子一致；stateen和三个V能力保留全称未知。validDoubleRegs使用正式独审的参数无关正常true结果，不借此重排寄存器列表。

default未观察方向的机器分类为：112个encode guard拒绝均需FS=0；62个短路方向中58个需FS=0、4个在列定正常前提下为空域。这些为空的方向仍待组合器独审；其余170个方向继续欠实际见证或额外可达域证明。本合同不排除异常出口，不证明任意输入能到guard，也不从Foff局部guard为false推得整个decoder/execute拒绝；default观察没有转给其它配置或privilege。

### 验证、可重跑边界与下一步

本轮新增范围消费器和组合器均按先红后绿实施。最终命令 `python3 -m unittest discover -s agents/float_support_review/tools/solve_scalar_coverage -p 'test_*.py'` 为 **85/85 PASS**。`scoped-contract-validation.json`（SHA `205c0c7e05634e9991a654be763fe7d8d9a5559fc4fe2b312f9266b00950a47a`）保存实际测试stdout/stderr、工具与产物SHA，并显式记录新增模型执行数为0。

`source-branch-worklist-v3.json`（SHA `c390b4b9b62bfac23c25bb3cca633f3e944bc0402fbe6d7cb4b395595d731229`）登记9类根因和34个输入，区分旧1dcc、新348147及未来IR；前两版清单保留。下一步依次为正常guard域独审、具体mapping/constructor fields与完整派发链、root后helper合同、访问器读写索引域、scalar RM mapping matches caller域，最后再聚合全部caller/phase/config/privilege义务。

新消费器通过显式输入和批准SHA复跑，输出默认拒绝覆盖历史文件。旧独审producer仍有1dcc的候选SHA、路径及计数前提；新IR须重新发现源声明/函数region、重生各sidecar并重跑producer与独审。不能只替换IR哈希或平移PC，也不能把现有348147的5413例strict通过改记为源码分支闭合。

### 正常guard域独审与严格消费完成

上述5d2a29候选随后通过独审 `independent-conditional-normal-guard-review/certificate.json`（SHA `56689fc5d8dfb854a51fa3221dfc52e02369af8a5711c532c620a18bc8123b9e`）。审查器直接递归求值已审表达式AST，逐状态核对结果、短路顺序和既有真值表，未以候选TableEvaluator作为唯一依据。每配置除原11个证明函数外，另复核MISA.F/D及mstatus.FS/VS四个完整getter；15项能力的实际路径并集为132个PC，两处opaque均在域外。57344个guard正常入口状态组合与7个独立负控通过。原审查器曾因自身预期结果标签 `mapping_word` 与实际 `mapping_encoding` 不符而失败，修正审查器后的记录与历史失败均由独审目录保留；候选及其producer没有改动。

[normal_guard_contract.py](tools/solve_scalar_coverage/normal_guard_contract.py) 以外部批准的独审SHA检查candidate、审查器和全部实际依赖，逐项匹配四配置source key/phase/方向域、getter完整范围、174个未观察义务及分母。输出 `conditional-normal-guard-contract.json`（SHA `b0b38a0fff67d20d78dcf11fd19e95fe495c62292051bcb591921de92cefdc36`），状态为 **ACCEPTED_VERSION_BOUND_SCOPED_CONTRACT**。该合同只导出 `conditional_normal_guard_values`：4个短路方向可在列定正常前提下判为空域，112个guard及58个短路FS=0方向仍需入口证明或实际见证，异常出口与整个派发链继续单列。

消费器新增7项测试，覆盖错IR/范围升级、削弱前提、配置/source key漂移、非空域误标false、缺getter审查和伪造空域方向。最终全工具 **92/92 PASS**；实际命令与产物SHA见 `normal-guard-contract-validation.json`（SHA `0ded9ed2b0f8de4199611dba91ca4c96ac978b30bdcdb81c703aecab79dcf7dd`）。现行机器根因表为 `source-branch-worklist-v4.json`（9类/36输入，SHA `6175e9663444c3821576e85f180f6cf5433193f7e9345ed5f55576507479a4fd`）。前述“组合器待独审”为历史状态；现已严格消费，`source_branch_closed=false`及无新增模型执行的边界保持。

## 2026-09-27 新56cc69：严格绑定、guard入口与正常域推进

本节新证据独立位于 `isla/target/float-support-review/final-coverage/integration/p1-56cc69/scalar/`。IR为 `56cc69a44ee1acdb4cadf40a992283aa2084e281e85fbe88ab10a3153d9956ac`，模型manifest为 `fdf105d19a9ac62f9c5036fbc80759adb7e9b500a51a34fcc4f886016329129e`，现行generation为 `9f01067ea8f2da31b37f5089e4c5870e47e8299f7622b9a456585a0648176a77`，v3 bridge为 `388f295c34f02f426a70899cb1960ff77ca176a3c5c60cb63adce2a85d8cc9c0`。运行器仍绑定runtime manifest `28fb65ee77e2c5e5c629c50b239a2e009337b47936b2fdbb897bf9c11bca055e`；旧1dcc/348147证书未迁移。

### 新源目录及5413例严格审核

新 [prepare_source_catalogs_v3.py](tools/solve_scalar_coverage/prepare_source_catalogs_v3.py)、[audit_suite_v3.py](tools/solve_scalar_coverage/audit_suite_v3.py) 显式调用v3 API及实际bridge verifier，核真实build/source/runtime/generation/IR；旧工具原字节保留。15份scalar source目录恰与348147同字节，这不迁移runtime证明。新源分母为49 constructor、94 execute、178 ordinary site（72 if/66 match/39 assert/1 mapping）、34 predicate、112 guard、93 control factor、1 RM；合并124 Bool候选，另2 BV OR。

| 套件 | 输入/完整终态 | 严格结果 |
| --- | ---: | --- |
| default原八组 | 4871/14137 | PASS |
| scalar-registers/Foff/Doff原组 | 128/384、82/82、40/40 | PASS |
| alternate caller增量 | 47/141、9/9、32/96 | PASS |
| User/Supervisor增量 | 204/416 | PASS |
| 合计 | **5413/15305** | **PASS** |

`strict-audit-summary.json` SHA `2aefd2701eac355244c37bde8bd43e6d7fa3d2f8e25d778ddd7876ab8d38f9ed`；实际argv、stdout/stderr及报告hash在汇总和 `strict-audit-logs/`。3并行，default审核92.964秒只作审核用时。`source-inputs.json` SHA `96173b2b0ff7237e7cf1abbe76734cb7adf34f31f8606f743d8043c2c88e9d34`；`source-binding-complete.json` SHA `133d3e75af98e8d09ad47d3fffa5a02ad3fc3f0f79a40f8030594b3abe343803`。八组均实算178 ordinary中144有runtime候选/34没有；候选存在不等于caller域闭合。

### 新guard构造点与自身实际观察

[guard_runtime_candidates.py](tools/solve_scalar_coverage/guard_runtime_candidates.py) 对四个actual sidecar重新发现112 guard×2phase、120 phase factor，完整遍历decoder的257函数Call闭包，49目标constructor共有112个Call、0漏盘点；每个构造Call均被自己的guard接受边支配。PC由新source/CFG发现，无旧PC平移。

[guard_candidate_witnesses.py](tools/solve_scalar_coverage/guard_candidate_witnesses.py) 用每配置新strict核精确mapping、constructor、phase及实际Call栈，并从真实R1提取FS/VS/MISA/privilege。

| 配置 | 实际入口 | guard观察/448方向 | factor观察/240方向 | observations SHA |
| --- | ---: | ---: | ---: | --- |
| default（含U/S） | 5075 | 336 | 178 | `0f0d3f14e887dbdfbc5759eacf13f6e3392d700f635591a5159f9ee605127708` |
| scalar-registers | 175 | 98 | 52 | `d17cf3f906d1d016195d5c9156835e9973a8ed40edf9440d84dfbf89c6dc05c3` |
| Foff | 91 | 91 | 37 | `0a189dfb607b57134623d84d3a5e04feb6ceba78fa20f1f423c8460e04882a8e` |
| Doff | 72 | 104 | 60 | `24982b09093f1382cb4f6898ca2c9746f98fdc1cb807622ac00bc7ec1826374c` |

文件名为 `guard-entry-observations-<配置>.json`。default的FS=0实际输入Machine112、User49、Supervisor49均在decode拒绝，encode/execute为0；这是有限输入事实，未推出任意word的整体拒绝。初次消费误用摘要字段 `suites` 的失败保留于 `guard-entry-observation-commands.json`；改读真实 `commands` 后成功记录于v2。

default独审 `independent-guard-entry-review/review.json` SHA `c7271a4b275837d0241d42f296c89e328d7f0f512669c8eab56e2c13fe1114d8`，结论 **PASS_STATIC_GUARDS_CONSTRUCTION_CUTS_AND_FORWARD_RETURN_IDENTITY**。独立raw IR/actual sidecar核224 guard、700真值组合、120 factor、112构造点完整CFG接受边支配；另核112 payload的449字段/90固定op、52 guard向量SSA，以及112条构造值经Some/unwrap/copy到正常返回的正向身份链，5负控通过。

[guard_entry_contract_v3.py](tools/solve_scalar_coverage/guard_entry_contract_v3.py) 严格消费外部批准hash，输出 `guard-entry-contract-default.json` SHA `f08309596d2fec3400661f53ee50ff2a24518534e12c696e088cc7bc14067e7d`，只签 **local_guard_construction_and_forward_identity_only**，关联default自身336/178方向观察。未签所有正常返回的反向来源完备、变量字段bit语义、整个拒绝链、跨phase状态、guard原子语义；三alternate不适用。误寻审查器文件名 `audit.py` 的初次失败保留，改读实际 `review.py` 后成功，见两个contract-command记录。

### 新34谓词、条件正常域及runner入口候选

[predicate_runtime_candidates.py](tools/solve_scalar_coverage/predicate_runtime_candidates.py) 每配置自己的sidecar重生19 Bool正常返回/30短路、15实际能力路径、4任意64位getter投影。扩展selector及return join动态发现；核源FS[14:13]/VS[10:9]/MISA.F[5]/D[3]与实际SSA、Full let初始化且不可写。validDouble正常End唯一前驱为literal true赋值，形参无读写；不排异常。四份 `predicate-candidates-*.json` 均待独审；default SHA `f17045176016e3f562a01e789a1856a880211424a08490cbc46027216d09d953`。

[normal_guard_candidates_v3.py](tools/solve_scalar_coverage/normal_guard_candidates_v3.py) 组合每配置自己的新predicate/guard/actual observations，64 Bool状态另与源AST解释交叉核。`conditional-normal-guard-candidates.json` SHA `0d6182a6987ee4bea2aad44b35a8bde6eff30c495ba692b255b99f808b08647f`，仍为待独审：default/scalar224phase正常接受均FS非零；Foff224均false；Doff144为FS非零/80为false。default未观察方向新算112 guard FS_zero、58 factor FS_zero、4 factor条件正常空。正常完成、固定本配置MISA/XLEN/FLEN、FS/VS稳定和同状态Bool一致仍是前提；未据此排异常或整个decoder。

[runner_entry_candidates.py](tools/solve_scalar_coverage/runner_entry_candidates.py) 绑定真实3个runner build/source/binary及冻结executor/frame/register/IR，记录同一R1 `regs` 三phase只读借用、每次新LocalFrame及逐Register clone，decode值clone入encode、原值入execute。`runner-entry-candidates.json` SHA `56ec65c5ad20177db7ba810d86da4fcda907792679ae54a2548c87ca52ef5e9e`，逐input/result/strict核5413入口：4946核actual ctor/fields后encode，467在decode完整拒绝。仍待Rust/入口关系独审，有限字段值不能推广全mapping bit语义。word前导零及实际group kind为mixed_negative的两次初始失败保留；明确数值word比较和kind映射后v3命令通过。

### 新IR纯读复跑、测试与九类剩余义务

四配置×decoder/encoder对新IR、各自config和空case重新检查。旧checker四decoder均因新增 `strict_and_bool` 未审而退出101；encoder四组通过。首轮命令/日志留在 `phase-purity/index.json`。实读冻结primop实际dispatch与 `and_bool`，只操作Bool/SMT定义；在独立复制 `phase-purity/decoder-runner-v2/` 中只加入该已核纯原语，保留未知外部调用拒绝。新增测试先红（1 fail/1 pass）后绿，完整Rust **11/11 PASS**，并执行cargo fmt及独立构建。

最终 `phase-purity/index-v2.json` SHA `62310597c716cb666b858d7725ee88323cc82340b7065577161a699d35c3a5f6`：四decoder各257函数/582 calls，四encoder各164/204，global-writes/indirect-writes/unclassified-callees均0。新decoder source SHA `21a81fe44ea1762ab72015956675a579d86534b9cf8c3e4348bb5adb62e46919`、binary SHA `4a44690772cd41a447a7e571e55e1ad21ca828a192527ff7874ab5109c7b9443`，49 runtime源码、程序来源、argv与证书均绑定。空case动态新增0，不签异常不可达；纯读前提还须独审并与入口/guard域组合。

Python全工具命令 `python3 -m unittest discover -s agents/float_support_review/tools/solve_scalar_coverage -p 'test_*.py'` 本时点 **119/119 PASS**，`scalar-tools-validation.json` SHA `f4b5c5634ba2092a3a1512d75dbb44f1f39deba672f78ac2a2cab58782d7fb36`。新增getter、guard切断、R1归属和范围合同测试均先红后绿。

[source_branch_worklist_v5.py](tools/solve_scalar_coverage/source_branch_worklist_v5.py) 生成新56cc69机器清单 `source-branch-worklist-v5.json` SHA `a59f66faa8c38797518386b28f6cb20f951a33802e9e05cd116ab66f083c9d7a`（九类根因/20输入）。优先组合170个FS_zero方向；ordinary/caller/typed CFG、34无lowering项、余下因子、RM matches、root后119 helper、读写访问器及配置/特权态聚合全部继续未决。**当前source_branch_closed仍为false。**

### 目标constructor正常返回的逆向来源候选

[return_provenance_candidates.py](tools/solve_scalar_coverage/return_provenance_candidates.py) 从每个可达normal End的return0，沿完整CFG前驱追踪最近定义；声明杀死旧定义，缺值、循环、未知callee及不支持表达式均保留Unknown。来源格保留target/other Instruction构造、Some包装和Unknown；精确tag Unwrap透传来源，错tag路径按冻结executor错误出口处理，不根据branch值剪枝。实际IR的Instruction/option类型声明及bv32→Instruction签名与冻结executor/IR源码均绑定。

四配置分别新跑，均得到378个顶层构造来源：112个目标Call、266个其它Instruction构造，Unknown为0；目标来源集合恰好等于对应新guard候选盘点的112Call。每份保存2285次reaching-def查询及381项错tag unwrap记录。`return-provenance-candidates-default.json` SHA `5d48022c52de4d71d83e4ce26b808b3583243e2ea2594ff7c0a8adff1ff0133b`；scalar-registers `37d988fad30826aad063998c602b186b35fac6844cd80175e208a91513472147`；Foff `4335428d934107f65605fdf1220175dd8a304b5f71c7d3c7ace9efa692befdfd`；Doff `b4fcc635dfcb10a4c1722a401d1ffb0a1363cc8c7a9ab433d422137a814bc5ea`。

这些是待独审的正常返回来源上界，不证明路径可行、payload bit值或整个失败派发链；不能直接改写170个方向的覆盖状态。4项负控先红后绿，检查全前驱合并、未定义路径、未知callee及错tag。新增后全scalar工具 **123/123 PASS**；`scalar-tools-validation-v2.json` SHA `9e28244599bb6603c1840ed64687500ffe1ed5d4be2000bb3a9e6fb23e82d69d`。前述119测试记录保持为当时版本。

### 纯读检查范围修订：隐式异常let漏检

上述 `phase-purity/index-v2.json` 随后被独审发现实质漏检：checker只把Def::Register/Def::Let加入global集合，漏掉冻结LocalFrame初始化注入的 `current_exception`、`have_exception`、`throw_location`（以及初始化NULL常量）。实际decoder/encoder闭包内internal_error helper会写异常let，executor确实将这些赋值写入local_state.lets。因此前述八个“global-writes=0”只能描述该不完整checker的结果，**不能作为完整全局无写合同消费，当前退为FAIL_SCOPE/待修正复验**。原v2程序、结果、初版strict_and失败均保留，不覆盖。修订checker与独立审查继续完整盘点异常写及正常返回影响，不删异常路径，也不从架构寄存器不变擅自推出异常状态不变。

### 架构值保持与正常End无异常写：修正、独审及严格消费

v3完整global检查器补齐四个隐式名字，12项Rust测试通过；在真实56cc69 decoder上退出101，准确拒绝 `zinternal_errorzIozK:12` 的异常写。`phase-purity/implicit-globals-actual-rejection/report.json` 和 `phase-purity-scope-revision.json`（SHA `14a8822d7b3ab5ffe9e6d82643cf58f35dcdab6cffa67f8d4307c7af75cc11bb`）保留修订依据。v4进一步列举三项异常scratch写、拒绝架构寄存器/显式let/NULL/间接写；四decoder通过，但四encoder因纯原语 `zero_extend` 未入白名单失败，原v4程序、binary与索引保留。

新独立目录 `phase-purity/state-effects-runner-v5/` 补充encoder实际 `eq_bool`/`zero_extend` 调度验证，并拒绝所有被调用的abstract extern，即使外部名称在纯原语或config constant集合内。新测试先取得13通过/2失败，再修正为 **15/15 PASS**，cargo fmt与独立target构建完成。source SHA `2d635edd4e7647249ab748610d530aa338e7a30a6f6d3c8df15dbf3056c7d273`、binary SHA `50f7985d7c3922d44b5ab4755a263575f172c89f33a6e479648a09af4248b184`；四配置×两root重新实际parse/init检查 **8/8 PASS_SCOPED**，各decoder257函数/582callee，各encoder164/204，每个闭包均完整列出12处异常scratch写。没有新增模型输入。

首次v5索引 `state-effects-index-v5.json`（SHA `fb34bfea9de5932c3af949b4e16beb7cfdcd2123348b6152d560320d691f4820`）引用了补齐命名source hash字段前的manifest，严格独审为 **FAIL_MANIFEST_DIGEST_MISMATCH**。原索引保持原字节，修正索引 `state-effects-index-v5-manifest-corrected.json`（SHA `990cc9f21b4952a21ac3b9d9b0369475d28737d04ebf9f04237b4f08f65436a0`）明确保留该失败、绑定最终manifest `0659638efa21942fca0efe885d7ea45b55319c8a0f726848f4c2ba9e0f116efc`；8份实际证书、源码和binary均未改写。

独审 `independent-phase-purity-review/certificate.json`（SHA `7f60693560ae1733d76305313876378a3a76ef1725511f77d9e969f85241b648`）分开给出完整global纯度 **FAIL**、架构值保持 **PASS_SCOPED**、正常End无异常写 **PASS_CONDITIONAL**。独立有限fixedpoint保留未知分支两臂、Call间write-ever、Arbitrary返回到caller及可处理异常；6轮收敛，从have_exception=false的root结果只有 `(false,false,End)` 或 `(true,true,Arbitrary)`，没有写过异常scratch后仍到root End的路径。前提包括新LocalFrame的clear初始化、state.lets不覆盖隐式三项、无函数假设替换或局部shadow、精确IR/runtime及正常End；不签所有输入正常终止。v5附录独审 `v5-review.json`（SHA `29040146c8ca4f3d5d25257b085403d6ac250cc80f9a424c628fe596b1da0c60`）核91项文件依赖、全部8个闭包/callee及12写集合一致，另补Ref、arity、局部声明支配及opaque检查。

[phase_state_contract_v3.py](tools/solve_scalar_coverage/phase_state_contract_v3.py) 严格消费两份外部批准独审、修正index及全部实际依赖，逐配置/phase检查完整集合。`phase-state-contract.json` SHA `6ced618d84130dbdb366c0e1c51bcedaae4726109388792ef884406aa75d51f8` 导出架构值保持和列定正常End条件结论，**complete_global_purity=false**；4项消费器负控先红后绿。实际case仍须联立SAT、非Poison与正确Ctor/Bits返回类型，不能把条件结论推广到异常出口、全部参数或任意配置。

### 返回双向身份、449字段位语义及局部pattern拒绝已消费

新独审R1以6820节点有限方程图从所有normal End独立计算来源，得到378 origin（112目标、266其它）、Unknown0，与新default候选完全一致；8负控保留新增target返回、未知Instruction helper、未初始化、覆盖/声明杀定义及错tag行为。R2a从实际Struct/Field/Id/Primop及完整前驱追溯449字段：90固定op、359原始32bit输入切片，其中244freg、49reg、63RM mapper和3raw constantidx，unknown0。R2b逐mapper72输入/70接受，核RM101/110 matcher拒绝，全部681pattern原子和7840真值组合；356 matcher/value使用同输入slice，接受边支配构造，任一pattern失败只能取本mapping的None。

组合独审 `independent-return-provenance-review/review.json` SHA `dff841bd672841ccab7cb2bc699954a5cf9b7494adf4c58bb4fd22c84d320b48` 精确绑定default；R1/R2a/R2b SHA依次为 `414fe8c4d121ba075e3290644e09c5ed9733867bb6e4f246f3d50b3bb8b4f08a`、`7ca2b640f896b1e86403bf0f08f6fb823196d38efc27b4b8a902fd253187dca3`、`26aae633cc0e29197a3d488d4dc4326abd10fd955b8f2c32a712caaa408528ed`。[return_payload_contract_v3.py](tools/solve_scalar_coverage/return_payload_contract_v3.py) 消费它和同版forward合同，逐source site/constructor/Call PC对齐112条身份与payload，实际核依赖，5项负控通过。输出 `return-payload-contract-default.json` SHA `83874831a00203a7ece67a3bddefc8f909bb3b552dac03268e0d06c8c9417305`。

该合同关闭default目标正常返回来源的双向身份及这112个mapping的字段位语义/局部pattern拒绝缺口。局部None之后仍可继续后续mapping，因此整个decoder拒绝、任意word的可行成功路径集、跨phase状态、guard原子架构语义与三alternate仍须各自合同；不增加动态观察或源码闭合状态。

### 5413个真实runner入口与复制语义已消费

独审 `independent-runner-entry-review/certificate.json` SHA `72dd0a52f64cda85395be70b99e04c5d87c3e185e3e1ec2eba3eec639417dc82` 独立重建8套件20组的5413入口/15305完整终态，得到4946条实际decode后encode/execute及467条decode拒绝；核实际word、Ctor/fields、R1初态、trace终态身份与三runner build/source/binary，不调用producer的actual_entry。源码审查包含LocalFrame/Register/Val/UVal/B129/Bindings复制与当前frame Ref访问，v3四路径bridge实际重跑，13负控通过。

[runner_entry_contract_v3.py](tools/solve_scalar_coverage/runner_entry_contract_v3.py) 以独审index SHA `8c1e147df349302a095e07810fc908808d34c82c0c71c1da94b63b3001223191` 为外部批准入口，核197项独审依赖和精确规范化入口账，拒绝fields、FS初态、phase计数或分母漂移。输出 `runner-entry-contract.json` SHA `2000bd415c7ba6a49ff807259bd3d648f95818e370a9268a90a59e82aeed6356`，4项负控通过。它给出本次实际入口和同R1架构寄存器clone、decode值clone入encode/原值入execute的关系；phase内部保持、全返回语义与正常guard值域分别消费，不能省略其前提。

### 新数值helper与四库文件分母修订

新 `numeric-helper-inventory/index.json` 从49个源caller及实际zexecute重新盘点629个Call root；完整保守域为255内部函数、11外部callee、810Jump、1285Call。96个数值源root另列保守闭包，旧119函数只作对照，不能继续称新完整分母。3459项synthetic SourceLoc不能凭absence判not_lowered。

新增 `numeric-helper-inventory/library-factors/index.json`（SHA `272423061895863ea23b74897ae047c60a028846c80eac2b558240632b86715f`）为Sail库 `float/inf.sail`、`nan.sail`、`normal.sail`、`zero.sail` 的7因子建立补充catalog；每配置21个保守root-factor/42个LHS方向，原15文件catalog保留。`witness-candidates.json`（SHA `8e89294e807512f6e984e1c316b7d1d3bb03d8174db922127083a311cb1c908c`）仅列Machine且逐caller/root/连续Call链匹配：default39候选观察/3pending，scalar与Doff各12/30，Foff0/42。这些仍待独审，不签RHS正常值、异常出口或其它privilege；前述原93 control/124合并Bool统计不再代表补充库文件后的完整分母。

本轮完整Python命令 `python3 -m unittest discover -s agents/float_support_review/tools/solve_scalar_coverage -p 'test_*.py'` 为 **136/136 PASS**，实际日志、工具及合同SHA见 `scalar-tools-validation-v3.json`（SHA `02b2b203485303273021d679d5183ff29ff787b9e574018c16f4bf13906a3bb3`）。[source_branch_worklist_v6.py](tools/solve_scalar_coverage/source_branch_worklist_v6.py) 生成 `source-branch-worklist-v6.json`（九类/29输入，SHA `0f0a9089b2a16c58f339f02e50b1c8a8a97beaa7b1a406a1fe7818b5cf375d53`），保留v5历史并修订global纯度、default返回/payload及新增库分母状态。当前下一步是消费四配置predicate/正常域独审，再与default返回、phase及runner合同组合170个FS_zero方向；ordinary/34未发射项、RM/FRM、读写访问器、完整数值域及全配置特权态聚合均仍未闭合。

### 新库七因子、完整保守库存及正常域独审已消费

库因子及库存独审 `independent-library-factor7-review/index.json` SHA `b42044d9539cc939ad25249236d00ee0434b1a2f146611d6b24f5c80c57d6412` 分别绑定factor证书 `d884a73ebfdac52647610da33fea4d7637ad10936a1b56ecef5272e7d9f3e878` 和inventory证书 `5ba90e33ffa682e94038297d99d79c2e3981779d01c85bf2d7905a0e291d61e5`。独立重建全部629保守root/255函数/11extern/810Jump/1285Call，保留3459未解源码位置及2209无SourceLoc指令；47源文件v3重绑，49constructor的94完整execute定义均保留。库因子另外重建17个真实输入、51完整phase的Call/End栈与tag消费；13负控通过。

[library_factor_contract.py](tools/solve_scalar_coverage/library_factor_contract.py) 严格消费两份独审及完整依赖，输出 `library-factor7-contract.json` SHA `8043a0786ccb8c107343f4e884b6fb96ca4516bf09d841d0c117e2c8289de917`，5项TDD通过。完整LHS分母168，精确观察63（default39、scalar12、Doff12、Foff0），**105项pending保持，RHS签署数为0**。每个source/clause/phase/privilege/root/arm与自身终态匹配，不把库存视为全可达集合；default三个inf LHS false仍未静态排除。

四配置谓词/正常域独审现行 `independent-predicate-normal-domain-review/review-final-v6.json` SHA `c0eeb1af084bc1617b6e80c596478667061872fd8765ff22ee96f8f8cda96def`，每配置核19谓词、15能力、4任意64bit getter、224阶段guard、120阶段factor，以及15份strict audit中的1772个自身见证引用。v6逐arm输出精确状态索引、正常条件、实际观察及privilege；default/scalar/Foff/Doff未观察方向分别174/538/560/524。四负控v6 SHA `5a660a1dd7293e127b5998d706528d023685cbf41fb2bf805c48cf70033469ff`。此前v5证书声明checker `a8038e…`，消费时实际checker已变为 `569fee…`，严格拒绝；机器记录 `predicate-normal-contract-v5-review-rejection.json` 保留，改消费真实重跑的v6，未只替换旧hash。

[predicate_normal_contract_v3.py](tools/solve_scalar_coverage/predicate_normal_contract_v3.py) 消费批准v6/负控、各配置完整候选及实际依赖，另逐文件重核模型与Sail库快照。`predicate-normal-contract.json` SHA `d1f618b9e7cfe5b3b9b10d1deedb3d9a2d8a67adda178db76b7bf4cadee6e560`，6项测试通过；固定精确guard已到达、正常调用完成、各自MISA、XLEN/FLEN64、稳定状态原子及validDouble正常true等前提，保留异常与入口义务。

### 170个FS_zero方向的组合：仅audit先decode入口，官方分母不减项

[encode_entry_exclusions_v3.py](tools/solve_scalar_coverage/encode_entry_exclusions_v3.py) 将default已审112个target正常返回来源/guard接受支配、正常guard条件、phase架构值保持及runner的同R1复制关系组合，得到条件推导：先成功normal decode目标constructor要求FS非零，同R1进入encode后FS仍非零，故encode正常guard的FS_zero方向为空。组合再显式核所有被调函数从clear的fixedpoint结果仅有正常End或带异常写的Arbitrary，保留所有异常及normal求值前提。5项负控通过；default实际5075输入中4739进入encode（Machine4633、User53、Supervisor53），实际入口仅作一致性核对，不代替全域论证。

**该入口关系属于定向审核运行器的decode→encode→execute。官方冻结 `isla/src/isarch/exec.rs` 的wrapper顺序为encode→decode→execute，不能预设encode前已成功decode。** 因此112个encode guard拒绝和58个短路FS_zero方向只能在上述audit入口前提下候选排除，不能从官方全77源码分支分母删除；官方FS=0的non-encodable方向仍须自身处置或见证。此前“170个方向入口组合”的讨论均受此边界限制。

旧 `encode-entry-exclusion-candidates.json`（SHA `0b76cdbc08b59f2f95199d59c982c50ef028afbb19c28dfdc505ddb0fd972dc4`）已显式列出先成功decode前提，保持原字节。[encode_entry_scope_v4.py](tools/solve_scalar_coverage/encode_entry_scope_v4.py) 另生成 `encode-entry-audit-only-candidates.json` SHA `725b62082378fcb4d8c0d21df34a2c596f28baea31793154915356af86b64b1d`，明确 `applicable_to_official_encode_first_entry=false`、`official_source_branch_directions_removed=0`；170条audit候选、4条原正常恒空方向与170条官方开放义务分列。组合候选已交独审，当前不签全source闭合。

### 34个无runtime候选位置的新解释候选

[unlowered_source_candidates_v3.py](tools/solve_scalar_coverage/unlowered_source_candidates_v3.py) 对四配置重新消费自身strict审计、actual sidecar及实际v3 bridge，保留完整raw/actual函数和异常出口。`unlowered-source-candidates.json` SHA `a1642f95fc3803f2e48edef8535a431a3ba1afac5b1f29e65b4f10950283929d` 的34项分为：24个fle_S/D/H if（完整模型词法只有各自定义名，无其它引用，raw/actual无fn/val/Call）；validDouble的3项（RV64循环与外层selector消退，条件求值仍在）；rF_or_X_D/wF_or_X_D的6项（xlen>=64求值仍在，selector与RV32子树消退）；非SYMBOLIC accrue_fflags定义的1项（与生成命令显式-D SYMBOLIC冲突）。3项词法/预处理测试通过，全部模型文件按manifest重核。这些仍为待独审解释，不以absence直接关闭源site，也不推广到3459个synthetic源码位置。

### 34个精确源码站点消退已独审并消费

独审 `independent-runtime-site-retirement34-review/certificate.json` SHA `7cd6a73df4a297ae9804ca619e17c7f0e775bb25bbdac04b840e577f2ab67a76`、入口 `index.json` SHA `7afd21a253c60889fa92f4ddf9d6f2c3285e40acaba7aff3964a6f591a2d22e3` 对34个精确站点及四配置136项给出 **PASS_SCOPED**。它独立核各配置209个typed PC及377980个完整runtime PC，绑定324项依赖；实际重跑v3 bridge核291源码，15负控和3项边界测试通过。24/3/6/1分类守恒，条件求值、异常出口、callee和索引语义均没有因此关闭。

[unlowered_source_contract_v3.py](tools/solve_scalar_coverage/unlowered_source_contract_v3.py) 严格消费入口及所有实际依赖，输出 `unlowered-source-contract.json` SHA `570c846c2a0ec6dadc59a2f96cf166f0e8b3156972aa97233393c5f3b4ad2a9b`。原producer函数范围止于下一声明，独审正文止于函数闭括号；consumer逐字核对共同正文，尾部只允许空白/注释，并严格转换宏上下文dict/list格式，保持宏名、极性和顺序。最初边界/宏格式不匹配的失败日志保留，新增尾部代码和宏极性负控后 **6/6 PASS**。原178源站点仍在分母；34取得版本绑定无runtime分支处置，余144项仍待自身caller/方向合同。动态新增0，`source_branch_closed=false`。

### 174项入口组合独审及消费：官方170保持OPEN

独审 `independent-encode-entry-composition-review/certificate.json` SHA `d5cea499ab36f65ef23bf8159d5e84b451a69ae5db685a2c0b898a97ceb19622` 为 **PASS_SCOPED_AUDIT_ONLY**，逐项重核174个actual PC/方向、112个decode构造支配切点、FS原子、三audit runner和官方wrapper入口顺序；12测试及764文件绑定通过。170项仅允许 `directed_audit_successful_decode_then_encode_from_same_R1`，4项只允许全部正常guard前提；官方170 OPEN、减项0、完整phase/global纯度FAIL均明确保留。

[encode_entry_contract_v4.py](tools/solve_scalar_coverage/encode_entry_contract_v4.py) 严格消费独审和全部实际依赖，逐source key/phase/arm/mapping/正常域核对174项，输出 `encode-entry-audit-only-contract.json` SHA `3ced9efbc4dfab202188eb22a929540c3dd2c9b5549c7ab284546ca73bfe3243`。6项TDD覆盖官方减分母、错误方向、弱化前提、全纯度升级和虚构官方先decode。**这份合同不会关闭官方FS=0的non-encodable方向，也不会新增动态观察。**

### 剩余义务归并为五个共享根因

[source_branch_worklist_v7.py](tools/solve_scalar_coverage/source_branch_worklist_v7.py) 生成 `source-branch-worklist-v7.json` SHA `f96bfa2083bac17e03d5fa7b2710efc3806933527f727d7c759d42406af4841d`，5组/36输入；原九类到五组的映射守恒，旧清单保持原字节。每组分别记录可共享合同、剩余域、真正需要新增执行的目标及准入条件。

| 共享根因 | 下一份可复用合同 | 新动态输入的目标 |
| --- | --- | --- |
| 官方入口、配置拒绝与异常 | 从官方R1直接进入encode的guard/后续匹配/non-encodable终态关系；三alternate返回与forward各自独审 | default FS0的112 mapping constructor/op等价类，按官方入口合同合并后补实际拒绝见证；Foff/Doff仅补其可达缺口 |
| ordinary源码及caller域 | 144 runtime站点按完整函数、typed实例、execute根和参数域映射方向；34消退前提保留 | 完成共享域划分后，仅补未观察且不能判空的方向类 |
| RM/FRM与访问器有限域 | 3bit RM/FRM0..7、5bit索引0..31、六臂双向mapping、读写/旧值/x0/FS-SD/callback | 有限合同仍无法处置的真实execute/写回类；不把helper枚举转记实际execute观察 |
| 完整数值root后域 | 629root完整控制/参数/返回/异常/写回，七库因子的LHS/RHS分别证明 | 按helper/root/config的数值操作数类，仅补可达且缺自身观察的类；default3 inf候选独审前仍在105pending中 |
| 归属与守恒聚合 | source/phase/caller/root/config/privilege/arm无重无漏账；官方与audit入口分开 | 优先复用5413完整trace，最后补不能由同域合同或已有自身见证处置的归属缺口 |

已有FS0定向输入在decode拒绝，不能提供官方encode拒绝见证，因此官方入口是当前已确定需要新增执行的目标。其余组先推进函数/有限域合同，再按剩余可达等价类补输入，避免对每个pending行重复运行。`source_branch_closed=false` 保持。

### 三alternate返回合同及default三个inf条件域已消费

独审 `independent-alternate-return-payload-review/index.json` SHA `027ae27dc9b3b2bd40c03e7378d2193cde96ab77c6d7ed9c2e7073f28bc9f15e`、证书 SHA `64b03433c4b291d72f938a7457f3535333b0b27e3f8394322963e5b7d149e2a9` 分别对scalar-registers/Foff/Doff重算112 origin、449 payload字段、局部None、guard构造及forward。每配置核10个完整typed函数78920 PC、543全类型/2344签名、377980实际指令及101个let/1604 setup；64负控、2边界测试和92直接依赖通过。default证书仅作机制来源，不转移证明。

[alternate_return_contract_v3.py](tools/solve_scalar_coverage/alternate_return_contract_v3.py) 逐配置核构造Call/完整source key/guard接受边/payload/局部None和全部实际依赖，5项TDD通过。输出 `return-payload-contract-alternates.json` SHA `33f5c0a9def8866dcb884349e6dde6c9fb49896b5f2b9f308d1085a8b475fdf5`，限定336配置mapping/1347字段；不签整个decoder拒绝、异常、官方encode-first、实际输入或跨phase保持。

default三个inf方向独审 `independent-classify-inf-domain-review/certificate.json` SHA `a5824ee1e68707699af16ea20f89b0e9f0cb1408ed88c1b761f14791e79f5c1e`，独立验证四个完整helper、159指令、八个保守Bool赋值及同decompose字段确定性；8项TDD、49文件依赖、v3源码重绑通过。精确范围为Machine/execute根6333、7529、8841到 `zfloat_is_inf` PC11的false→12方向；要求分类正常路径和同一bits输入，不要求FS非零或先decode，不扩RHS、异常、总性及其它caller/config。

[classify_inf_contract_v3.py](tools/solve_scalar_coverage/classify_inf_contract_v3.py) 严格消费该证与原library合同，把3项完整root/AST/source义务逐字对应原default pending集合，5项TDD通过。新 `classify-inf-three-contract.json` SHA `e286c26994a1ae19986c2e584efeb79e3a1a8dfb88ad3ca81f2d43f0d9ed9f9d`：整体168 LHS=63实际观察+3条件静态排除+102pending；default42=39观察+3条件排除；RHS签署0。旧library合同原字节保留，动态新增0。

### 官方FS0现成wave库存：修正新增执行判断，53方向待独审

上节v7“官方入口已确定需要新增执行”的判断过早，修订依据是现有官方wave尚未查询。实际冻结目录 `isla/target/float-solve-evidence/official-56cc-long-20260927-064348/` 的 `replay-wave-001-manifest.json` SHA `0bb5cd9fefed7ef4cafda627e8f15a5c0212fea9fcf4db337a9bc3514a1d3e65` 已含26完成目标、6230终态/6195gen及35个non-encodable；35项实际R1 FS均为0（User17/Machine15/Supervisor3），其中33项属scalar24个constructor。原判断及v7文件保留，以本节“先查已有官方证据、确缺后新增”为现行入口。

[official_encode_witnesses_v3.py](tools/solve_scalar_coverage/official_encode_witnesses_v3.py) 复用既有官方manifest/JSON/流式trace parser，逐文件核hash并完整扫描6,083,137,274字节trace，守恒全部6230终态。每个edge核实际catalog及sidecar Jump的PC/方向/SourceLoc；候选见证要求同constructor、encode phase、精确 `zisarch_solve_wrapper:1` context、自身FS0和原privilege。4项TDD通过，没有重新执行模型。

初版 `official-wave-encode-witness-candidates.json` SHA `bb2711ddcf6dae7dfe23da8e4214c4ea942a83c1cc21e1ea7fe03aded5b6c666` 的逐方向见证正确，但汇总时读取defaultdict使空方向也成为键，错误把观察数写为170。原件标 **FAIL_SUMMARY_COUNT_ONLY** 并保留。[official_encode_witness_summary_v4.py](tools/solve_scalar_coverage/official_encode_witness_summary_v4.py) 实核全部原文件依赖、按非空见证数组重算，3项TDD通过；更正 `official-wave-encode-witness-candidates-v2.json` SHA `85396597413087742f8a9e7c2d41872c3a9ebc580a3a0d65ad21d56125cc0657` 明确绑定历史失败，得到 **53方向候选=32guard+21短路LHS，56自身引用，117此wave未观察**。当前只交独审，official_directions_closed=0；117未观察不等于不可达或必须重跑，还应查其它完整官方代表。

现行五组清单 [source_branch_worklist_v8.py](tools/solve_scalar_coverage/source_branch_worklist_v8.py) 输出 `source-branch-worklist-v8.json` SHA `be5c67e316fd76ef08a7849699452cd0850748113e9cd1310cb954d043eaf275`（5组/41输入），明确修订v7的新增执行判断、三alternate待审状态和default3 inf计数。当前优先处理已有官方wave/完整代表、RM/访问器有限域、144ordinary caller域与完整root后语义，再补无法复用证据的可达等价类。

完整Python工具在34/174消费后为 **167/167 PASS**，`scalar-tools-validation-v5.json` SHA `981aae788acb2d9d847ca55db14d9b1457b779f36c9d3aa2af4a8d31bd7db995`；加入alternate/classify3/官方wave提取与计数修订后为 **184/184 PASS**，`scalar-tools-validation-v6.json` SHA `9de461dc100862b57455b29f4e4cbfd298ba8db4bb90a14cb1a4b2f180da5cb8`。两者均保存完整argv/stdout/stderr及工具/产物SHA；旧155记录 `scalar-tools-validation-v4.json` SHA `88491e375de7e941513a20f2a26abc48c33ce368e8cb0fef78925ad34d89f701` 保持历史适用范围。所有本节新增动态模型输入数仍为0。

### 完整官方D FMA代表的8方向增量候选

继续查询已有完整代表 `isla/target/float-solve-evidence/representatives-56cc-20260927-061428/replay-manifest-F_MADD_TYPE_D.json`（SHA `003666710974d5409a81b5645b77acde736d41ee9957702384ae060285e00867`），同IR/配置且1096完整终态/1092gen/4non-encodable。[official_encode_witnesses_v4.py](tools/solve_scalar_coverage/official_encode_witnesses_v4.py) 复用冻结v3逐edge扫描和v4汇总校验，完整核646,376,491字节trace；初版正式manifest仅有必需JSON/trace哈希，没有增量wave附加log/count字段，故首轮错误假设log存在而失败。原失败日志保留；新入口显式支持该正式schema，若附加log/count字段出现则要求完整配对，5项TDD通过，未改原manifest。

`official-representative-encode-witness-candidates.json` SHA `8d07cde4e720e5e1a8358c4182b34a1f2faf2742b35f7e6c16afa14b61aaa5c6` 得到F_MADD_TYPE_D的8个自身方向候选（4guard/4短路LHS），已交同组独审。与wave53组合无重为61候选，余109仅在所查完整官方证据中未观察；独审前仍不关闭官方分母。动态消费将使用新证书的官方实际观察声明，候选为保留静态方向身份而带入的旧audit `allowed_claim`/`intersection` 字段不会转成官方排除结论。

### 官方61自身方向已独审消费，109方向仍开放

wave独审 `independent-official-encode-fs0-witness-review/certificate.json` SHA `6a67fc294ce70a1305c455fd624fa94902c6dda771b5345e6314bf1777dd6ac4` 完整重建6230终态/32912166条edge，17项测试、870文件绑定通过。53项自身方向中32项guard拒绝，21项LHS包含20个AND false/RHS跳过及1个FLI_H内层OR false/RHS进入（`zencdec_forwards:12518`）；后者不证明RHS值方向。

[official_encode_contract_v3.py](tools/solve_scalar_coverage/official_encode_contract_v3.py) 的14项测试通过并重核所有依赖，输出 `official-wave-encode-observed-contract.json` SHA `ae83cdd16e83bf2be15d027256bcf78e22bbdc5202b804bba275904bceadd001`。消费器只输出独审新增的官方动态claim，保留source key、实际PC/方向/后继、phase/root及各见证真实privilege，不承袭旧audit静态排除字段。

D代表附证 `representative8-review.json` SHA `6cfe6a626b85fea684af95140a5d20839c2d40a0fc1da199c53ca4908e8039bd` 独立核1096终态身份守恒及4个完整non-encodable调用路径，5项测试、795文件绑定通过。新增8项为4guard与4个AND LHS；[official_encode_union_contract_v4.py](tools/solve_scalar_coverage/official_encode_union_contract_v4.py) 的8项测试通过，输出 `official-encode-observed-union-contract-v2.json` SHA `e0b19f5f42e0b9e6876042d1d2aee5a6c80930c5a6a8c8e542ba8d1ce1f059b1`。与wave精确键交集为0，现行170分母为 **61 OBSERVED（36guard/25LHS）+109 OPEN**，64引用/37自身终态；25LHS中24 AND跳过RHS、1 OR进入RHS。静态不可达减项、RHS签署和新增模型执行均为0，旧wave合同保持原字节。

### RM/FRM四配置有限域候选已提交独审

[rounding_domain_candidates_v3.py](tools/solve_scalar_coverage/rounding_domain_candidates_v3.py) 复用已审R2b的叶值/primitive解释、raw Types和actual typed/sidecar逐PC绑定。四配置各重新核10函数53181实际PC、六成员Sail/typed enum、6臂forward及forward_infallible、8种bits的backwards/backwards_infallible/matches/valid_rounding_mode，以及48种RM×FRM组合。实际不存在forwards_matches函数，raw fn/val、typed全集和sidecar均已核对。32位Fcsr getter的完整AST证明返回`bits[7..5]`，其余29位不进入本selector。

每配置完整377980 runtime指令及1910 setup指令均核`zfcsr_rm_reserved_behavior`无额外写入或地址逃逸；它由实际三指令let设为Illegal。RM_DYN只在FRM0..4返回对应Some，FRM5/6/7返回None；非DYN保持输入RM而不读FRM。backwards对5/6到MatchFailure，backwards_infallible对5/6会读取未初始化临时值，候选明确拒绝赋具体值，不能将其解释为返回RM_DYN或断言实际runtime必拒绝。

45个精确scalar caller/21个constructor逐配置绑定源表达式、typed局部参数和实际selector Call。组合180配置caller、8640有限输入，只到None后`Illegal_Instruction`的Unit构造边界，或Some后下一forward调用及其0..4输出；要求局部`have_exception=false`。true路径逐caller保留到Arbitrary，不签此前异常不可达及后续数值参数/结果/flags/写回。向量ROD专用6的实际`zexecute:27944→riscv_f32ToF16`、`:27955→riscv_f64ToF32`明确保留，不作全局rm<5归纳。

候选 `rounding-domain-candidates/candidates.json` SHA `97745a2061d318cd86b3037f4030a3f3493adc911eba0128c5feef7e1e9645ed` 已冻结交独审，当前 **CANDIDATE_PENDING_INDEPENDENT_REVIEW**，静态排除授权0。18项TDD通过；首轮producer在第二配置因局部变量遮蔽目录变量失败，`produce-development.log`原样保留；修正后四配置完整成功日志为`produce-development-v2.log`，未重写失败历史。

加入官方53/8消费及RM候选后完整Python工具为 **229/229 PASS**：`scalar-tools-validation-v7.json` SHA `f1989f5e52c22553aa222ab57f1550ee54553697c4b07890fab49606dd951a8a`，保存实际命令、日志、工具和产物SHA。五根因清单v9曾继承v8的旧pending文字及candidate子标签；现行 [source_branch_worklist_v10.py](tools/solve_scalar_coverage/source_branch_worklist_v10.py) 修正这些标签，保留v9历史，官方61/109数值不变。下一步消费RM独审，并检查新完成官方trace的自身runtime来源桥/调用链/source绑定；不同runtime或新IR不能仅换旧证据哈希后复用。全部本轮新增模型执行仍为0，`source_branch_closed=false`。


### RM正式合同与alternate九个inf条件域已消费

上节RM段落曾把全部setup分母写成1604，现修订为 **1910**；1604来自此前let-only范围，RM机器候选及独审始终核全部setup为1910。原机器候选未改，修订依据为 `rounding-domain-candidates/candidates.json` 和 `independent-rounding-domain-review/review.json`，不把旧文字作为PASS证据。

RM独审 `independent-rounding-domain-review/review.json` SHA `6107582e6101fe0e75ffa8a1939eb5eb61de708aa5f534617839a336b232f036`、index SHA `7bb80f5a3c7ff9a0ca9a1ae1279c77c06bddf19514ad1ad743c9180e0687cb75` 核四配置各10完整typed函数、45自身caller、48个RM×FRM输入及所有setup；12测试/11有效负控通过。[rounding_domain_contract_v3.py](tools/solve_scalar_coverage/rounding_domain_contract_v3.py) 的9测试通过，严格消费后输出 `rounding-domain-contract.json` SHA `f8cc28008bb18add681120999ad232ec6803d8792ae5f64e6a5761392872240d`。静态排除授权0，完整phase纯度仍false；backwards_infallible 5/6未初始化、have_exception=true路径、vector ROD6及数值结果/写回均保留原边界。

alternate inf独审 `independent-classify-inf-alternates-review/certificate.json` SHA `0974ad4d417b8b261a46659c8c503416e3f2418dcad97b0b8704efc71396f322`，由 [classify_inf_alternates_contract_v4.py](tools/solve_scalar_coverage/classify_inf_alternates_contract_v4.py) 严格消费（6测试通过），输出 `classify-inf-alternates-nine-contract.json` SHA `a2e83a013a006c8ee694619c44ba7c84bb4f25dbc7b6b5fde898b269817ab2c6`。三alternate各自Machine/execute root6333、7529、8841至float_is_inf PC11 false→12的九方向，在typed非Poison、正常分类调用及相同bits/decompose确定性前提下条件排除。default3原合同保持，现行库168 LHS为 **63观察+12条件静态排除+93pending**；RHS签署0，不推广其它root、privilege或异常域。

### sharedtrace23实际目录有限桥与自身见证提取

冻结输入 `official-sharedtrace23-candidates/inputs.json` SHA `343834a4ac90cdbd393d9fa866ca0a2838cb71402b3c95e919a4dea25f115910` 为23目标、9692终态、68 non-encodable、9,259,946,599 trace字节。IR仍为56cc69，runtime树为 `b298e3952fef0ffc866cb4b7ff7514fa188d69f7a5b1bf76500f42f17bba58a4`。新observer结构来源桥 `new-observer-bridge-review.json` SHA `309dc98ecb73a401b2b6c82f83b4c0513cd377b1500f9293dab4201df5183ef5` 只适用于新官方运行，不迁旧25910路径或旧61动态方向。

隔离目录 `official-sharedtrace23-candidates/catalog-build/runtime/` 复制517个官方源文件，原Cargo.lock字节保持，采用已审CFI目录抽取器。release/debug两次构建和目录导出均完成；原严格比较在 `zcheck_extension_param_constraints:22` 拒绝release alias变化，`catalog-binding-development.log` 保留。全量库存发现93处别名差异：87个unary（84 print_endline+3 print）和6个binary（3 print_string+2 print_bits+1 print_int）；另有9处PrimopReset进程地址变化。

[sharedtrace_primop_bridge_v1.py](tools/solve_scalar_coverage/sharedtrace_primop_bridge_v1.py) 严格核14个注册函数的arity、签名及去注释后正文均仅 `Ok(Val::Unit)`，只允许两个完整8/6成员别名集合。93处逐原IR extern、目的槽、完整SourceLoc、参数与返回Ty绑定；原IR PC与actual PC分别记录，不能假设insert_monomorphize前后PC一致。9个Reset按cancel_reservation×5、sys_enable_experimental_extensions×2、load_reservation×1、match_reservation×1绑定配置的Unit/Bool(false)/Unit/Bool(true)和Init值clone闭包，不以地址证明值。首次重复相同extern声明和第二次raw/actual总PC相等假设失败均保存；v3日志为成功产物。

`finite-primop-bridge.json` SHA `ba7dbec1dc53f0a6c6dbdea2343443d99580ed6dcd31a8a490249b416e3ea2b2` 与 `catalog-binding.json` SHA `e82f0da6377d4766d9ec8e3179d30449d66bdc0080ab00063311da6a86371f73` 已冻结交独审。旧/debug/release的2058函数、377980实际PC、25676 Jump逐非地址/非alias字段相等，4753依赖重hash；debug仅绑定自身结构，不证明release唯一分发。19项sharedtrace专项测试通过。23全trace自身提取正在执行，当前 **PENDING_INDEPENDENT_CALL_END_AND_SOURCE_REVIEW**，不拼装跨runtime闭合、不签RHS或静态不可达。新增模型执行仍0，`source_branch_closed=false`。


23目标现已全部完成提取，`official-sharedtrace23-candidates/candidates.json` SHA `265b385fdc50d1eb4632ee54d786af84d1bb9f90dfb4f76be52221c62f6f8be7`：9692完整终态、47,438,081边、9,259,946,599字节全量守恒，得到 **85自身方向候选=56guard+29LHS**（27 AND跳过RHS、2 OR进入RHS），85引用/56自身终态。85个源义务键全部位于旧109未观察键中，与旧61键交集为0；这里只比较源身份，不能据此把旧runtime61和新runtime85当作同一runtime已闭合146。新runtime自身仍有85个方向未在这23目标观察，完整Call/End与布尔来源独审仍在进行。

有限桥独审 `independent-sharedtrace23-source-review/runtime-bridge-review.json` SHA `0e3952ea4f20f021481bb6a28389495809139159fc91883c0f6f48752b7ce6b9` 已通过：独立重算全377980 PC、93 alias、14函数与9 typed Reset，4759依赖和9测试；独审自身首次raw/actual PC假设的失败也保留。五根因现行 [source_branch_worklist_v11.py](tools/solve_scalar_coverage/source_branch_worklist_v11.py) 生成 `source-branch-worklist-v11.json` SHA `e0a97d9c1334886430f60c933fec06bce2f3b5cf9b7c58d79477d99b1d882d0a`（5组/54输入），纳入RM正式合同、库12条件排除和新23候选/目录桥；旧v10保持。


### sharedtrace85已独审并严格消费

独审 `independent-sharedtrace23-source-review/certificate.json` SHA `60f65ec804f59beacb7c8d6beb17b102ab3bb3de7f1fe5f6900a911f7401d381` 完整重建全部68 non-encodable的Call/End及每个Jump，23完整trace计数与producer一致，17702文件绑定/19测试通过。首轮源码Bool规则未包含14处RHS为 `xlen >= 64` 的AND而严格拒绝，失败历史保留；独审以新局部规则识别该原子并证明RHS路径未执行，不签比较值。两OR分别为 `F_UN_X_TYPE_H:12382`、`F_UN_F_TYPE_H:12450`，均只签LHS false进入RHS。

[official_sharedtrace_contract_v5.py](tools/solve_scalar_coverage/official_sharedtrace_contract_v5.py) 的12测试通过，17704依赖逐文件重hash，输出 `official-sharedtrace23-observed-contract.json` SHA `72f3575c82c391b67a54b9ee83e771d0218fc67fb8e9022ea2209ed9b93ba251`。新runtime自身170方向为 **85 OBSERVED+85 OPEN**，56guard/29LHS、85引用/56终态；85全局source键与85caller方向键守恒，RHS签署0、静态减项0、旧见证迁移0。生成来源仍保留旧runtime manifest28fb65，实际执行另绑定b298e3/c42a1b及独审有限桥0e3952，未把生成runtime替换成执行runtime。

旧61和新85分别有自己的观察证书；两组均未观察的24个source键仅用于定位下一批，不授权跨runtime动态并集。[source_branch_worklist_v12.py](tools/solve_scalar_coverage/source_branch_worklist_v12.py) 保留两个runtime分组，继续访问器有限域、ordinary144 caller域、完整root后/RHS和归属聚合。四配置访问器typed准备 `accessor-domain-candidates/exports.json` SHA `7966220d507fd66205b5598227316a160a7feeeace631b203043014e05295ce3` 为16入口、70完整closure函数8438 PC并另导出execute；该准备没有域证明结论。解释器当时处于开发阶段；后续冻结候选和验证见下节，不把准备记录改记为已审合同。

### 访问器2056局部路径候选与四配置边界

`accessor-domain-candidates/candidates.json` SHA `918b5c3f767d53c4fde8e176d26dad39234d60e9cc171aa513684e3c88061120` 已冻结，状态为 **CANDIDATE_PENDING_INDEPENDENT_REVIEW**。四配置各16入口、450索引入口项、514完整局部路径，合计1800项/2056路径；每配置保守闭包70函数/8438 PC，实际caller库存511项。每配置H/S读取另保留64个boxing分区，完整高位全1时取原寄存器低位，否则分别返回H `0x7e00`、S `0x7fc00000`。

[accessor_bit_terms_v3.py](tools/solve_scalar_coverage/accessor_bit_terms_v3.py) 按位保留任意输入来源，未知位串相等生成关联原子，禁止默认为false。[accessor_finite_v3.py](tools/solve_scalar_coverage/accessor_finite_v3.py) 解释寄存器/结构体写、setup、vector访问、完整调用和顺序写；[accessor_domain_candidates_v3.py](tools/solve_scalar_coverage/accessor_domain_candidates_v3.py) 逐配置重新核source-v3、typed/sidecar全PC及F/GPR映射在377980 runtime和1910 setup PC无写/Ref。任意F/GPR数据和mstatus位限typed非Poison值，整数索引限0..31，bits索引限5位；未知分支只按H/S boxing两分区显式展开。

局部结果保持get_X(0)=0、set_X(0)无写；F及窄格式写数据/boxing后依次写F寄存器、mstatus、mstatus，FS13/14与SD63置1，其余61位保持任意原值。default与scalar-registers读结果一致，实际callback路径分别保留；配置的唯一函数路径数为173/344/173/173。`"mstatus"` 经long_csr_write_callback→csr_name_write_callback→csr_name_map_backwards完整解释，未进入parse_hex_bits；不推广到任意动态名称或其他callback实现。“所有call/primitive完整解释”只指2056条列定局部路径，闭包其余未进入指令仍只作库存。

冻结模型的 `hartSupports(F)=true`、`hartSupports(Zfinx)=false` 来自编译支持配置；Foff/Doff改MISA不能改变这两个能力值。因此Foff直接调用set_F仍写F与FS/SD，不能据此推出官方execute可达。首版测试错误期待Foff触发AssertionFailure，真实失败保存在 `accessor-tests-capability-assumption-failure.log`；修正该假设后14项专项通过，日志 `accessor-tests-green.log`。首轮producer将Sail库目录写为 `sail_lib/` 的失败保存在 `produce-development.log`，改为实际 `sail-lib/` 后 `produce-development-v2.log` 生成候选；原失败文件保留。

每配置511个caller的参数域、支配、入口可达性及异常组合仍待合成；候选静态排除授权0、RHS0、source_branch_closed=false、新增模型执行0。工具单测 **289/289 PASS**，`scalar-tools-validation-v9.json` SHA `f5a126c2838fe05ab136426c6ac6adc6e4db26c2e67ca27cc3faf2b8a692f099` 记录完整argv、20.308秒实际运行、日志SHA和受测工具/产物SHA。该验证不替代访问器独审。

[source_branch_worklist_v13.py](tools/solve_scalar_coverage/source_branch_worklist_v13.py) 生成 `source-branch-worklist-v13.json` SHA `e398ebba99f067db9325ae72a92803641adf8f6f33f681157fabbdbd4c5d84d4`（5组/59输入），新增访问器待审候选和v9验证引用；旧v12与两个runtime各自61/109、85/85的正式动态范围保持原字节。后续索引前件纳入v14，见文末。

### e6a独立三caller分类器条件合同

以下产物独立位于 `isla/target/float-support-review/final-coverage/integration/p1-e6a323/scalar/`，适用IR `e6a3232d3858412c8283a1f6a08c8e0404493197a46f6aeec645b8796497d27e`、default配置20851f、实际debug目录03a776及source-v4 cfd091。不修改或迁记前述56cc合同与168项库分母。

新候选 `classify-inf-candidate-v1.json` SHA `5c1ccca688063115082bbaea71730b9e3db2ff6d36e083c58bc33f9ff0882b53` 已自行重提取94源码定义、49caller和629实际root。独审 `independent-classify-inf-review/certificate.json` SHA `099c9ebe99b5a85eb4b3bcaa1847af645b771f39f820be1c6d52d841150b45f4` 重新核源token、完整helper关系、同bits原子确定性和八态保守域，并依赖新目录独审 `../independent-runtime-catalog-review/certificate.json` SHA `af75f09f743d6b59ed83ba768c772e42475079eee8a27318da2d38dbfb1d020a`。目录独审仅签debug实际typed目录/初始化；release alias、缺失原语诊断与完整执行闭包仍保留边界。

[classify_inf_e6a_contract_v1.py](tools/solve_scalar_coverage/classify_inf_e6a_contract_v1.py) 的10项TDD通过，逐项拒绝旧IR、其它privilege/root、缺失/重复/RHS义务、放松正常前提、迁旧claim、目录漂移、source未重算及依赖冲突/漂移；red/green及消费日志保存在 `classify-inf-contract-validation-v1/`。消费者实际重hash4301依赖，正式 `classify-inf-three-contract-v1.json` SHA `0b08b31460463976c2592e7066fa794eb8f2e649f4cca123e400b410734eae7d` 只签 **1个源站点/3个精确default-Machine调用义务**：execute PC6333/7529/8841对应S/D/H分类器，正常同bits调用域内 `zfloat_is_inf:11` LHS false→12不可达。

该合同要求zero/subnormal/normal正常false返回支配inf调用、typed非Poison同bits/decompose字段及正常原子确定性；不证明分类总性、RHS、其它caller/config、异常闭合或完整phase纯度。新增动态0、旧动态/静态迁移0、source_branch_closed=false。专项验证记录 `classify-inf-contract-validation-v1/validation.json` SHA `218ab6deb6b870d5d4bf0910d4f8a346b802c8a26e8696be4de48688ffcbbe68` 保留实际argv、工具/日志及合同哈希。

### 56cc四配置直接caller索引投影候选

返回56cc独立证据目录：`accessor-caller-indices-candidates-v1/candidates.json` SHA `8c4e2a024982da1410698430e968f035116d48b3bc36d31a6524011ccd933f37`。原访问器511 caller/config为全ISA库存（execute474、其它函数37）；与49个scalar clause的629个源码root按实际function/PC相交，得到每配置 **184个直接访问器调用、34个clause**，四配置共736项。其余15个scalar clause须沿自己的中间helper继续定位，不能把511项都解释成scalar动态测试分母。

[accessor_caller_indices_v1.py](tools/solve_scalar_coverage/accessor_caller_indices_v1.py) 逐项核实际Call及全部参数、索引的唯一Copy、原始execute参数无写/地址逃逸、索引无额外写/地址逃逸。所有索引都是 `Field(Unwrap(本constructor, 原始execute AST), 字段)`；union→constructor→payload struct字段、局部声明和callee形参三处均为Bits5。复用既有 `ir_function_rebinding/rebinding.py` 完整CFG支配算法，验证Decl支配Copy、Copy支配Call，不裁剪任何Jump。结论仅为正常typed非Poison本constructor且调用正常到达时，索引范围0..31；入口可达性、完整caller合同/状态/异常和source闭合仍未证明。

首轮完整CFG检查严格拒绝execute中的四个PrimopReset，失败日志 `produce.log` 和初版工具快照保留。冻结runtime `executor.rs` 的PrimopReset为调用reset、assign后 `pc += 1`；新版允许这个正常后继，保留错误退出，不解释或签署Reset值。针对正常后继及禁止从Reset推断索引的红绿例连同其它负控共 **9/9 PASS**，日志 `reset-red.log`、`reset-green.log`。四配置实际生成10.951秒、退出0，`produce-v2.log`、`run-v2.json` 保留命令与输出；864依赖重新核hash。候选仍 **CANDIDATE_PENDING_INDEPENDENT_REVIEW**，独立于2056局部路径候选，两者都未提前变成正式合同；静态排除、新增动态和完整caller闭合均0。

专项验证 `accessor-caller-indices-candidates-v1/validation.json` SHA `4afc884d92c87825113fdb489856503bdf250938391cade5c6731c7668bcea14`；完整工具测试更新为 **308/308 PASS**（22.665秒），`scalar-tools-validation-v10.json` SHA `3a6f6a3bb7b11df851cd7e3cf67845b79d775fc2e835a177e4808faef142d6fe` 记录新消费者/候选工具与日志、产物SHA。[source_branch_worklist_v14.py](tools/solve_scalar_coverage/source_branch_worklist_v14.py) 生成 `source-branch-worklist-v14.json` SHA `adef72368934ca6817719f867ff220fd331d1a2ab546ba5aa519b6a9451b540a`（5组/62输入），当时两个访问器候选待审；后续局部域独审见下节。e6a三排除仍保持独立IR合同，不并入56cc分母。

### 2056局部访问器合同已独审并严格消费

独审 `independent-accessor-domain-review/certificate.json` SHA `6b69f6a3bc5388ba112a00d97b0cddc80893481b10e1196ea28dadbc31b3811d` 已封存：独立高位优先位来源解释器不导入producer解释器，重算2056正常路径、521685个PC出现、27948个Call事件和2184次寄存器写，20个独立测试通过；22组primitive注册及具体语义、vector索引、let覆盖优先级、struct复制、callback、完整SourceLoc与嵌套地址逃逸均核实。source-v3纯audit重新通过，2464依赖封后重hash无漂移。

[accessor_domain_contract_v4.py](tools/solve_scalar_coverage/accessor_domain_contract_v4.py) 的10项消费负控通过；正式 `accessor-domain-contract-v4.json` SHA `ae16d1d908ba703e7b93618f4a5ab837763f5f43923b58e4f0a4ae0411076fa2` 实核2468依赖，严格绑定候选完整局部行/函数路径、配置/能力、保守目录和完整1910 setup。其正常局部索引/任意位来源、x0、H/S boxing、callback以及F→mstatus(FS)→mstatus(SD)写序合同已生效；runtime仍为28fb65，不迁新sharedtrace动态事实。专项 `accessor-contract-validation-v4/validation.json` SHA `4fe2b7f935c189448afa93e0b2555f74e0c3dd105de634c76ba2edc8a5a901a3` 保留red/green/消费日志及完整argv。

736项direct caller索引候选已另交独审，不由上述局部合同自动转正。其它6种直接入口 `rF_H/S/D`、`wF_H/S/D` 在629源root中实际共46项/22clause，其中33项来自前述未覆盖的15clause，另13项来自已部分覆盖的clause；全49clause的直接寄存器根应为184+46=230项，不能漏掉后13项。原70函数闭包包含这些helper不等于已经签其独立入口域。

现行 [source_branch_worklist_v15.py](tools/solve_scalar_coverage/source_branch_worklist_v15.py) 输出 `source-branch-worklist-v15.json` SHA `7be0214e9da15aee0422297bddeb917c8f35284b170edcb307fb2428fee5eff2`（5组/65输入），分列已审2056局部域与待审736索引前件；完整caller闭合、静态排除、RHS、新增动态均0，异常总性和source_branch_closed仍false。

### 六种直接F入口1024局部路径附证候选

`accessor-direct-f-candidates-v5/candidates.json` SHA `6ad2f17fbff4d0b41becd7c842e59319d2a0d3cd44cc42008a25def3e8dcf1a4` 已冻结为 **CANDIDATE_PENDING_INDEPENDENT_REVIEW**。[accessor_direct_f_candidates_v5.py](tools/solve_scalar_coverage/accessor_direct_f_candidates_v5.py) 从 `rF_H/S/D`、`wF_H/S/D` 本身直接解释四配置全部0..31索引，任意数据位/mstatus与H/S boxing完整两分区保持。每配置6入口、192索引项、256完整局部路径，合计768项/**1024路径**；返回/写回仅复用既有公式检查器，实际入口始终是本直接F函数。

每条实际函数路径均精确匹配已审2056合同中的内部函数路径，并显式记录旧合同路径ID；这种对应只作为附证前件，不自动签六个新入口合同。每配置的46个直接scalar调用另重算AST索引投影、完整CFG唯一赋值支配和typed字段域，合计184个配置caller前件；22个clause中15个此前没有落入184 direct root集合。两候选的direct root集合合计230/配置、覆盖49clause，但完整caller可达、状态和异常关系仍待各自合成。

4项专项TDD通过：H两boxing域、S写序、D不分区，以及未知入口/越界/Bool索引拒绝。生成退出0、22.662秒、2472依赖重hash；同目录 `run.json`、`produce.log`、red/green日志保留。验证 `validation.json` SHA `b258e0b13baad2120a49d4f5d4fe3455566ed5b6c7b0a1a53238a0937cfbe336`；候选已交架构安排后续独审，当前不增加正式合同计数、source方向或任何动态观察。

### 736索引及直接F附证均已正式消费

`independent-accessor-caller-indices-review/certificate.json` SHA `6a05f6d8e59b1254f2880376039d9a6d838da1973daf6abb3bd6449145603e46` 独立采用节点删除算法，核完整52823 PC CFG、每配置368个cut及参数不能重新声明；15项测试、2497依赖通过。[accessor_caller_indices_contract_v2.py](tools/solve_scalar_coverage/accessor_caller_indices_contract_v2.py) 的8项测试通过，2500依赖重hash，输出 `accessor-caller-indices-contract-v2.json` SHA `0e51a90cd99aeee4246950b36cb6a4f76bc95a058b740105aeaf6d789745fe51`。仅签四配置736个条件Bits5前件；全ISA库存另327 caller/config仍未由此处理，完整caller可达/状态/异常均未签。

六入口独审 `independent-accessor-direct-f-review/certificate.json` SHA `e06640332befe95e1c47e93363afebfd27f12578eb1ca48c8ea685553a76685e` 独立重建旧调用树，检查每条完整连续子树、Call事件区间与全部写；wrapper前后缀纯、同参数同入口状态、直接返回callee结果。10项新增测试及15项既有索引算法测试通过，2517依赖重hash；每配置46个新索引/92 cut，与旧736精确键交集0。候选沿用旧16入口前提的措辞不改原件，新合同明确消费独审 `new_entry_premises`。

[accessor_direct_f_contract_v6.py](tools/solve_scalar_coverage/accessor_direct_f_contract_v6.py) 的8项测试通过，输出 `accessor-direct-f-contract-v6.json` SHA `4b1a2b21f9f6382218a94e38175f4f9e1b982f6a38127ef4dea4e114f39bfefa`，2523依赖实际重hash。与旧两个合同合计 **22入口、2568索引入口项、3080局部路径、920条件索引前件**；230 direct root/config和49clause并集仅作库存，完整caller闭合仍0。专项验证分别在 `accessor-caller-indices-contract-validation-v2/validation.json`（SHA `68f687fe45f4169b5e039befd88a84f2da76618fa0d3f2e8e6ac1919b6971a55`）和 `accessor-direct-f-contract-validation-v6/validation.json`（SHA `a21592e6acbb17813a2f6b45e38033f6f3f18a8fc0cde7c078888caf9f0e8229`），均保存完整argv与red/green日志。该组没有新增模型执行，不签完整caller/RHS/异常总性。

### alternate41与direct52按自身入口正式消费

alternate独审 `independent-alternate-classify41-review/certificate.json` SHA `d6a21107d11fa5f76543aed77a4457fd67840c46e68579d7535f1c164df6e0d3` 对父任务新增的 **26输入/78完整终态** 核436602指令、19074 Call/End和69309边，得到41自身LHS方向：scalar-registers27、Doff14。41引用对应21个不同execute终态。[alternate_classify41_contract_v5.py](tools/solve_scalar_coverage/alternate_classify41_contract_v5.py) 的10项测试通过，352依赖实际重hash，输出 `alternate-classify41-observed-contract-v5.json` SHA `97a6ead3d4bcc6eeea94b40e113017861fb1f425aeaa1e37ab88f16a3ee615f1`；此阶段168项为104观察/12条件/52pending。consumer没有执行模型，但该证据的实际新增输入不可写成0。

direct独审 `independent-direct-classify52-review/certificate.json` SHA `2dbb4aac2f489387d2659dc8bb018c7b91b5a4d452f6f89ee08a9f69995eef35` 只授权 `accepted_directions`，index SHA `6d8956e51fe5453294a1f9fbdabd91bcfd45a3736428d09fbff5f1985b1e4e94` 强制联立source/delivery与LHS局部声明两个附证（SHA分别 `d4d13acfbe7424c12b8b9a73279ce4495fa26a7ba3173974e0390e363535a92b`、`756d68f2d54246b837e74c6d9ac2ed192d2478182d682d9b256df7f77f1ff7fe`）。独审45项测试/37负控、638依赖核验通过；52=Foff39+Doff D13，24个typed构造子直接execute输入、24个完整终态、128次真实LHS出现。此前compact24与full24为同组输入重复运行，只计24唯一输入。

[direct_classify52_contract_v6.py](tools/solve_scalar_coverage/direct_classify52_contract_v6.py) 严格消费上述入口及两个附证，12项测试通过；首轮消费者错误要求全部调用上下文深度2，实际nan位于snan/qnan第三层，失败 `tdd-green.log` 保留，按两条实际完整上下文修正后的 `tdd-green-v2.log` 通过。正式 `direct-classify52-entry-separated-contract-v6.json` SHA `63409fabbb445a0a1adf083495146378fc6a668a4e1e548db41ae863094d9ac3` 重hash974依赖，明确新执行由父证据提供，consumer执行0。验证 `direct-classify52-contract-validation-v6/validation.json` SHA `6d4e5bdb6354eedc8c3a3da6a942a4a4085d64a60738ffb42f3b4a7775db7e16` 保存实际命令、耗时及日志。

168个列定库LHS按入口如下；不把direct证据迁记到decode-first或官方入口。

| 配置 | decode-first自身观察 | direct-execute自身观察 | 条件排除 | 原decode-first仍未观察 |
| --- | ---: | ---: | ---: | ---: |
| default | 39 | 0 | 3 | 0 |
| scalar-registers | 39 | 0 | 3 | 0 |
| Doff | 26 | 13 | 3 | 13 |
| Foff | 0 | 39 | 3 | 39 |
| 合计 | 104 | 52 | 12 | 52 |

此表仅处置七个库因子的列定LHS义务；RHS签署0、原入口迁移0，完整源码分母、官方可达、异常总性及 `source_branch_closed` 均未完成。旧63/12原证与阶段104/12/52合同保持原字节。

### 工具全集360与分支清单v16

实际命令 `python3 -m unittest discover -s agents/float_support_review/tools/solve_scalar_coverage -p 'test_*.py'` 共 **360/360 PASS**。`scalar-tools-validation-v11.json` SHA `309f374a4b3f6f9f17ce19ec692110431b531572d82207e7585595f3cdd3bf38` 记录wall 49.205秒、unittest 41.186秒、退出0、日志与工具运行前后SHA零漂移，并绑定本节五个新正式合同及独立e6a三条件合同。后续v16清单生成器不在该次受测工具快照内；它以实际运行及依赖核验单独验证。

[source_branch_worklist_v16.py](tools/solve_scalar_coverage/source_branch_worklist_v16.py) 输出 `source-branch-worklist-v16.json` SHA `ed3c90610186773cb5afca7d0c292ae36e61d3dfcf634f00a071d70e3010a701`（5根因/75输入）。清单纳入3080局部路径、920条件索引及库168按入口分列，明确两份新动态证据有50唯一输入，consumer模型执行0；旧5413/15305台账保持原边界。旧官方runtime61/109与sharedtrace自身85/85分别版本绑定，e6a不并入56cc分母。

下一关键路径调整为：使用已冻结 `source-ast-full/attempt-006` 完整ordinary/SYMBOLIC原生树，重新选择49族outer constructor根，建立完整callee/global/mapping/raw→typed反向scope义务表，再按自身前提消费已有合同。旧629 source-location root及144 ordinary待办保留为旧库存，不代表完整原生分母；不因3080局部路径或168项LHS表继续扩签完整caller/RHS/source。

### native完整树选根准备与共享抽取器接入

`source-ast-full/exporter-package-v2/manifest.json` SHA `d7a292daf17fd9d6fd46a9c7f05b8fd36864f802016a066f7d9207bacf137f3e` 及 `independent-exporter-v2-review/review.json` SHA `e42ec7094bb812e4065c339a04c9611ccb24deb734363b8a2007ea52599f5001` 限定为结构发现及pending库存。完整树为 `attempt-006`；catalog004只作导航，其节点path双射无独审，不用于本标量选根。

只读遍历ordinary与SYMBOLIC的全部DEF/FCL/MCL实际语法，两域各得到 **49构造子族、94条execute clause、112条decode mapping、112条encode mapping**。636个phase-root保留所有同族条款、实际definition结构路径、unit索引与整条语法hash；没有从旧629 Call/source位置库存选根。准备 `native-source-inventory-v1/outer-root-discovery-preparation.json` SHA `1ca20492b7280481b2e5ebaf1cefd54b462dad739729aff61feff493e57d9f84`，实际27.464秒，仅root定位，没有生成caller图。

完整raw原生树另找到94个function和112个mapping根。首轮未将typed相对文件名联立冻结 `inputs.project`，636项均保持pending，准备原件SHA `3aaba97dcc4637870a16a9584f3b5001221332cad03442f58d8e1fd35d7105f9` 保留；v2按冻结项目根及source_aliases还原路径，所有636项各有一个相同声明字节范围的raw候选，`outer-root-raw-identity-preparation-v2.json` SHA `00095c1a49264c41357d2d9e73933a3b282c36f81d242482da12446bdbe4cf93`。只绑定根声明身份候选，不签宏域、lowering、参数/guard或完整raw→typed反向scope。

[本族runner](tools/solve_scalar_coverage/native_scalar_inventory_v1.py) 改接BF owner维护的 `native_semantic_dependencies_v5.py` 公共API，旧extractor遗漏E_ref/x0及lexp依赖的问题由共享入口统一修复、统一独审；scalar不发布独立schema底层分叉。公共schema census将原生语法与typed annotation分列，对全部constructor给分类、依据及零出现，return/assume/sizeof/constraint/type条件等不因旧固定control列表而丢弃。族层保留所有同名private/public目标及真实mapping方向声明，call-site Env module不当作target module证明；extern将分别统计call occurrence和unique声明。

本族根/应用规则11项测试通过，`native-source-inventory-v1/shared-api-green.log`；共享API正在冻结，全图正式产物尚未生成。以上没有新增模型执行、动态迁移或静态排除，完整源码分母与 `source_branch_closed` 均仍false。

### native v1历史版本与v2完整原生应用候选

上节是公共API冻结前的准备状态。后续v1实际使用共享v6生成 `native-source-inventory-v1/native-root-source-inventory.json` SHA `1fb3537468c24acbe4e33b04e8682e468fc6da2c7f05c19ad538b07079acd634`，174.397秒退出0、658依赖。其引用路径含公共v6的虚拟 `pattern_body` 等结构；v1原件冻结保留，不用来签raw引用投影，也不改写为v8结果。此前prototype测试与快照同目录保留。

现行 [native_scalar_inventory_v2.py](tools/solve_scalar_coverage/native_scalar_inventory_v2.py) 使用公共 `native_semantic_dependencies_v8.py` SHA `dde355e6fa7e1ba445043f4312273885aa5338345b38817a2823ae28e5e36ba1`。共享v8检查全部实际引用路径的kind、name、location，保留return/ref/assignment、Nexp_if/NC_and/or及完整declaration schema义务；本族不维护第二套底层抽取器。`native-source-inventory-v2/native-root-source-inventory.json` SHA `af7784eb600e59ce7008ecf2775d16475b3aedc7c26499fb1672046ae7f36874`，174.011秒退出0，661依赖实际重hash。专项验证 `native-source-inventory-v2/validation.json` SHA `415ee9b156ebf29cdc2a8224e7ca366f1cfc1067933add01bb3fec7dc9f39a2e`；本族应用10测试、入口域5测试通过。公共v8独审尚未消费，状态仅为结构生成通过、语义与完整分母待审。

| 原生候选项目 | ordinary C++ | symbolic Isla |
| --- | ---: | ---: |
| reached units | 1293 | 1301 |
| syntax节点 | 89494 | 90566 |
| typed annotation节点 | 343548 | 350366 |
| schema构造器（含零出现）/实际tag | 278/142 | 278/142 |
| extern调用出现/唯一extern声明 | 1163/138 | 1581/142 |
| global依赖边 | 351 | 428 |
| additional semantic义务 | 300 | 274 |
| type条件义务 | 1401 | 1505 |
| 实际引用路径核验 | 647 | 731 |
| config/entry/phase/D义务 | 1176 | 1176 |

两backend各保持49族、112 encode/112 decode/94 execute根；`F_MADD_TYPE_D` 的四条encdec根索引121、122、123、124全部保留，ordinary definition7762、symbolic definition7851。全树dispatcher原有788项仅为完整定义导航；selected constructor根不等于完整phase入口。源目标module归属、extern实际实现、初态和异常总性继续OPEN。

入口D由 [native_entry_domains_v1.py](tools/solve_scalar_coverage/native_entry_domains_v1.py) 显式分列四配置×两入口×三phase×49族。official encode-first从typed目标constructor全部参数和实际初态起，decode只取实际encode成功image及同phase state，保留nonencodable；audit decode-first从原word及初态起，不借官方image。当前这些是关系规格，`PENDING_ENTRY_SPECIFIC_INITIAL_STATE_BINDING` 未解除；不能从requested=decoded事后校验反推decode根预筛，也未排除任何前缀、后缀或ILLEGAL/default。

上游输入live核验仍为 **FAIL：454/457匹配**。三个漂移文件位于 `agents/float_support_review/tools/solve_source_ast_catalog/`：`plan.md`、`freeze_exporter.py`、`README.md`；已核固定漂移集合及历史/当前SHA，并消费冻结tool-source-snapshot映射和provenance annex。`input-recheck.json` SHA `b895101348978a464943f2d9ac2f7c6f7d7c9df72809a64189a3d7db1edcd11c`、annex SHA `aa5ae909df07b8fa85c4695ca40713e96d0204a19595b4990fa9ea5e15f842e6` 只提供 **PASS_HASH_BINDINGS_ONLY**；没有新build或完整producer链PASS，也未把live失败翻绿。

### raw完整scope反向事件候选

[native_raw_scope_binding_v1.py](tools/solve_scalar_coverage/native_raw_scope_binding_v1.py) 复用公共 `native_raw_scope_shared_v3.py` SHA `be1b981229d799907d1943e0256049bea1835c8d6cbc6e416f1cf751b538de05`，从实际raw树重生全部5083 scopes，逐项与共享检查SHA `b1e5d6c673d89bb2cbe7a4905bd39990e919fa3764b6c98c5d9b7cf16c8ea5ff` 相等。函数从实际typed pattern提取位置，其它unit用声明位置；全部reached unit无重无漏保留。生成 `native-raw-scope-binding-v1/raw-scope-bindings.json` SHA `c0bd21384a5b4d9877d10ac9f7076bd1e5cf876927f0a3ba3f0d5f0412a80948`，44.551秒退出0、668依赖、1243唯一raw scopes。

| 反向scope项目 | ordinary C++ | symbolic Isla |
| --- | ---: | ---: |
| name及pattern/声明位置精确关联 | 1230 | 1236 |
| raw类型及compiler generator来源候选 | 63 | 65 |
| 保留的raw事件出现 | 1408 | 1483 |
| 同unit、同位置、同kind的typed候选 | 371 | 445 |
| typed投影或类型作用待核 | 1037 | 1038 |
| 删除未匹配事件 | 0 | 0 |

每个使用scope保留完整raw子树hash、tag计数及source事件，每个原生根另列reached raw scopes。来源候选不代表生成语义证明；同位置kind关联也不证明求值顺序、lowering、runtime或entry可达。特别是raw infix token位置可能小于typed布尔表达式位置，不能猜测或删除未配token；scattered/when投影、位串operator及Generated lowering继续列为OPEN。继承1176×2入口域义务，没有把保守全局reached集合直接当作可执行scalar分母。

4项TDD通过，red/green、完整argv及produce日志保存在该目录；验证 `validation.json` SHA `7f4e45241bc8a4fd8ed2619daba48d0bdac567e86dac7803bb2620a9708cf1f8` 记录实际依赖重hash和事件守恒。公共raw组件独审尚未消费；新增模型执行、动态迁移、静态排除均0，`source_branch_closed=false`、`denominator_complete=false`。

### 完整dispatcher顺序与2352入口域的结构联立

[native_dispatcher_domains_v1.py](tools/solve_scalar_coverage/native_dispatcher_domains_v1.py) 使用共享 `native_dispatcher_order_v1.py` SHA `a8f32ebb37a525f3dd8b93f66b48f578939d04e8888bbf42f86ec5b3696d36df`，重新遍历两份完整typed树，与共享BF候选中的全部dispatcher逐项相等。每backend为392 forwards、392 backwards、395 execute、1 ext_decode，全部原生clause的matcher/guard/value实际path及hash保留；公共mapping方向按冻结 `rewrites.ml:realize_mappings` 选择matcher侧guard。

`native-dispatcher-domains-v1/ordered-entry-domains.json` SHA `f8ffaff6b433b9583c84777b74dce099d7e85719cab69b41d72083684744327c` 实际105.324秒退出0、670依赖。每backend1176域分别引用对应完整dispatcher和次序SHA，全部j的域规格为 **D且前缀[0,j)所有候选正常失败**；异常是独立终态，不能当作正常reject继续。selected scalar根只用于定位，不裁剪前缀或后缀；同constructor不同enum仍保持独立候选。guard前infallible参数绑定属matcher求值义务，value体只在matcher成功和guard真后求值。

6项TDD检查全列表及终尾守恒、同constructor多条款、方向错配、缺失/重复根、入口关系保持与顺序篡改；验证 `native-dispatcher-domains-v1/validation.json` SHA `2d0c9f7ec528bbf4acc8f265f2d0e3599c5a25cf1be92f49067b69ba7e3b2338`。公共组件独审和source→实际lowered次序桥仍OPEN；全部2352个D的实际entry初态、encode image、同phase状态尚待证明。完整列表不把其它CPU body无条件计入scalar执行分母；静态排除、动态迁移及新增模型执行仍0。

独立入口调查 `source-ast-full/independent-dispatcher-boundary-review/review.json` SHA `5e3d1c1fb68a523c7a923085e83b9d4602a6b084d7f0e22d1ef56a24667099cb`、报告SHA `2f599a8cbba6ae2957e0989fb6a3ad263eb6e43f34789e99f871f26c3d2402c9` 已核F_UN_TYPE_X_S mapping118/119与F_MADD_TYPE_D mapping121..124，确认encode/execute仍做同ctor子op检查、direct FCLASS不继承mapping guard、requested==decoded仅是事后校验。实际execute IR末尾是剩余C_ILLEGAL解包；共享源候选的通用no-match描述不能当作实际默认行为证明。本节只关联其边界发现，不把该调查升级为完整entry域、分母或动态覆盖证书。

### 工具全集395与分支清单v17

实际命令 `python3 -m unittest discover -s agents/float_support_review/tools/solve_scalar_coverage -p 'test_*.py'` 为 **395/395 PASS**。`scalar-tools-validation-v12.json` SHA `abdf13628742cd21d4af3678ff8fd01d5d2190c017d2f3781a81bfbdfec4ae95` 保存wall36.125秒、unittest30.818秒、完整argv、日志和运行前后工具SHA，漂移0。该快照包含native v1/v2、入口D、raw scope和dispatcher应用；后加v17生成器按实际运行及输入核验另验证，未声称其属于先前工具快照。

[source_branch_worklist_v17.py](tools/solve_scalar_coverage/source_branch_worklist_v17.py) 输出 `source-branch-worklist-v17.json` SHA `79505279042af4161383ace301f32fe390b485fce44ba14b286667e5205ded95`（5根因/86输入）。独立列原生结构候选计数、raw未配义务和2352个完整dispatcher入口规格；旧5413/15305台账、3080局部路径/920前件、168库LHS按入口分列均保持原边界。新增模型执行、动态迁移、静态排除和完整caller闭合均0。

v17冻结时公共机制证尚未消费。随后收到v8独审 `source-ast-full/independent-shared-closure-checker-review/certificate.json` SHA `ea9e5d80441cc4db5a6a88d90d12904313439f02ac91fe2578e286ff38e654cf`，manifest SHA `8851ca4b728691908da5f3e35669439c195282fa96be8a5df9d213378ff82f01`；其21生产测试、32独立负控及全unit原树引用路径通过，许可仅为冻结表达式引用/schema/目标extern库存机制。本族根/raw实例、type来源层、D/dispatcher及完整source闭合均不在证书范围；v17当时的待消费标志保留，后续联立须另附新记录。

### raw投影v2：保全旧事件并细化808项每backend

[native_raw_scope_binding_v2.py](tools/solve_scalar_coverage/native_raw_scope_binding_v2.py) 改用公共 `native_raw_projection_v3.py` SHA `39b5dfbab17b5589601104197590165a7565d75c52d7ed067aeb012b766e962e`，保留raw scope v3和native图v2原字节。共享投影检查全部5083 scope实际子树hash，按scattered clause来源、raw when到typed双侧guard及真实infix token/operand gap建立候选；本族只检查完整旧事件集合及unit绑定守恒，没有新增解析特例。

`native-raw-scope-binding-v2/raw-scope-bindings.json` SHA `9a8404ccf3c23a91532b8200e615a9e867f354732c2a3f3d621d94a1069dbace` 实际87.183秒退出0、674依赖。ordinary 1408与symbolic 1483个旧事件的unit/scope/raw node/kind集合完全相等，所有unit绑定与1243 scope并集保持；每backend新增 **234 Bool infix、7 typed bits operator、112 when双侧投影、455 scattered clause投影**，合计808候选。唯一source身份为1179/1253，只是结构身份，不是已证明执行分母。

| raw投影状态 | ordinary C++ | symbolic Isla |
| --- | ---: | ---: |
| 历史v1未配事件 | 1037 | 1038 |
| 当前仍pending | 229 | 230 |
| 其中E_sizeof | 29 | 29 |
| 其中E_config | 94 | 94 |
| 其中E_assign | 106 | 107 |
| 未配事件删除 | 0 | 0 |

当前pending涉及float_decompose等sizeof、94个初始化config表达式，以及wF/wX等赋值lowering；需要公共type/config与实际赋值来源层继续核查，未当作纯类型或无控制自动排除。5项TDD拒绝遗漏、重复和身份/kind错配，并允许一条raw guard对应两个typed节点。专项 `native-raw-scope-binding-v2/validation.json` SHA `a4227d2a46850c54d56a0dcd414c5cbef537dfb39f773bab5e9e6c1139b100f1` 保存日志、argv、计数与依赖重hash。投影语义、原生生成来源及族实例独审仍OPEN，source与完整caller/RHS闭合仍0。

### v8共享机制证的限定关联

公共 `shared_native_review_consumer_v1.py` SHA `9213aed640caa89d9d4289a55c5eab18d6884516cc840eb43f57406baa4c51a7` 由共同owner维护；其4测试包括六个范围标志的升级拒绝。本族实际调用 `consume_shared_review()`，重核certificate/report/evidence-manifest的全部SHA、bytes及56依赖，与共享正式产物SHA `d9261ca6d56efc001e4c62e4b4093a12b8026a0a677d63a2e3ec5492c514e796` 全字段相等，再联立scalar native v2图的实际API SHA。

关联 `native-shared-core-review-association-v1.json` SHA `f19f4f1eecd3f24cc9c219f6221d52ce0ce6b48aad5d5b0dd10e544eab3dfc60` 只记录 **ACCEPTED_SHARED_MECHANISM_REVIEW_REFERENCE_ONLY**：冻结表达式引用、schema和target extern库存机制。`family_root_raw_application_reviewed`、`dispatcher_domain_reviewed`、`native_type_dependency_extension_reviewed`、完整依赖/source/分母闭合均为false。本族保守graph仍可能含extern覆盖的Sail body，module实际可见性仍待证；同API和全树路径检查不替代族实例审查。

### dispatcher v2修订未证状态假设

上文native graph v2及dispatcher v1中“D与所有先前失败”的固定状态简写，以及audit的“同phase状态”，均为当时未证规格，**现在撤回这两种简化**。此前没有据其排除分支或签闭合。当前 [native_dispatcher_domains_v2.py](tools/solve_scalar_coverage/native_dispatcher_domains_v2.py) 使用公共 `native_dispatcher_order_v2.py` SHA `c5eea687314b6f8a933498a09d1ec487ae67b5d03eb23f27a0cda0b385e3839e`，保持v1实际源组件全部相同，以带状态的正常拒绝关系连接有序候选：

```text
R_0(w, σ) = D(w, σ)
R_(j+1)(w, σ') = ∃σ. R_j(w, σ) ∧ RejectNormally_j(w, σ, σ')
```

matcher/binder/guard失败可能改变状态；异常带其结果状态结束该路径。未证明pure、total及state-preserving之前，`pure_boolean_prefix_simplification_permitted=false`。value体在matcher/binder成功与guard真后使用实际中间状态，不能复用最初σ求全部guard。

official入口规格连续传递encode输出状态给decode、decode输出状态给execute；audit每个phase从同一份初始regs/lets启动新frame，encode和execute复用实际decoded值，前phase的frame状态不传递。共享状态关系附证SHA `1458a4d930286959d697054332400b2d72991bc82d0dd4bf3236852cac8aebb3` 的runner源依据已绑定；其942个BF有限case未迁入scalar，不能收窄广义source域。ordinary后端实际状态对应及本族初始化/phase gate仍待证明。

`native-dispatcher-domains-v2/ordered-entry-domains.json` SHA `eea19ff9d5473d760e59e68061ad99c49c3e9d4ff5b1030a39e91f0db52f588f` 实际90.610秒退出0、711依赖。两backend各1176个D及obligation身份全部重算，另保存历史D与历史ID；392/392/395/1完整源次序及所有前后缀保持。默认出口明确改为实际lowered terminal/constructor consumer待证，不再用通用MatchFailure文字代替真实execute末尾。6项TDD覆盖audit reset、official连续状态、拒绝递推、同ctor多根、ID修订与未知入口拒绝；模型执行、静态排除及跨入口迁移均0。

专项 `native-dispatcher-domains-v2/validation.json` SHA `96de9c208f383f60a42ed1046895d73156a8f2d6f0c15e785d5d4b5312e0167d` 核全部D/id已变化、仍唯一且未许可纯布尔简化。随后工具全集 **406/406 PASS**，`scalar-tools-validation-v13.json` SHA `17375f27acf045c754ce8a402d7a3dd0f82dd36617a71bf741991e03be5061e6`，wall36.887秒、unittest32.187秒，工具前后SHA零漂移。

[source_branch_worklist_v18.py](tools/solve_scalar_coverage/source_branch_worklist_v18.py) 实际生成 `source-branch-worklist-v18.json` SHA `ad73b2e2ff177a66650532e60153a6b81094bde02f8dd6f108dd5180a95c45ec`（5根因/94输入），纳入raw229/230、core有限机制证和stateful dispatcher v2；完整source与分母仍false。独审输入 `native-application-review-input-v1.json` SHA `eac3cf07dcdc6ef4bd5c8d417517c7e829a5bc592d03aecbbe17dec1f57ff5d7` 绑定17直接输入、761实际重hash依赖、三个完整producer argv及历史修订。已交架构指定独审，只请求根/物理身份/守恒及R_j域对象结构；实际D语义、初始化/跨backend/IR桥、type与229/230未配义务仍OPEN。

### type层独立增量附件

公共type准备 `source-ast-full/type-dependency-preparation-v2/manifest.json` SHA `3e7e2b5e7723d02f2fb1e5daeb252b8d05906942328fa486a4caeba8ed47be7e`、API SHA `15cb38ec762cae392bc797b26f303f0597a0f1e16090c9d42eb8696d6f0ecdf3` 已冻结为待审候选，15公共测试通过。两份全unit附件SHA分别为 `d96e59cc6084ea98db756fca7cac5f9fd4e0a7503cc80dd226603133df8f61fe`、`3f40fec8d6f17ed34766f63360ff5ca90682b013a814b680d183d8d556a410c6`，覆盖完整6372/6410 unit。

[native_type_attachment_v1.py](tools/solve_scalar_coverage/native_type_attachment_v1.py) 只按原有reached unit ID和backend、definition key、unit index、kind、name完整元数据联立附件，原core图及审查快照不改写。`native-type-attachment-v1/type-unit-attachments.json` SHA `967b31f80a68ab7961d3d20357c6bd1872de6c4499b6d9af7c627a3b17a4b1a5`，实际19.083秒退出0、683依赖；每个root引用其原reached集合对应的附件registry。

| type附件项目 | ordinary C++ | symbolic Isla |
| --- | ---: | ---: |
| 原生unit精确联立 | 1293 | 1301 |
| 唯一reference IDs | 55007 | 55819 |
| 唯一obligation IDs | 1567 | 1579 |
| 保守transitive declaration IDs | 221 | 221 |
| 本选集runtime rewrite候选unit | 0 | 0 |

最后一行仅报告共享附件在本选集的候选数，不证明运行依赖完备。类型/约束声明前件不当作runtime caller；sizeof/constraint/config/undefined/outcome的actual target及运行桥仍pending，raw229/230不减项。5项本族TDD通过，严格拒绝漏unit、重复、原生元数据变化及范围升级；专项验证 `native-type-attachment-v1/validation.json` SHA `7e8f9efbc68bad73caa78020ce19651b8308c559b7ad29beca1a581e02b57adc`。此前406全集属于增量前快照，本增量独立5测试，未再次声称执行411全集。

增量清单 `source-branch-worklist-v18-type-addendum-v1.json` SHA `6252ea1390938cdc48befad5ac86714d7a2df355e6edb073d725bc9d3d206748` 联立原v18、本type候选/验证和原独审index；当前原生图/raw/dispatcher的独审范围保持原快照，新type待公共独审及族应用增量核验。下一步还包括公共raw setter来源桥、本族实际D/初态与跨backend/IR关系；完整source、分母、RHS和异常总性仍未完成。

### type有限证正式消费与setter来源候选

公共type独审证 `source-ast-full/independent-native-type-dependencies-review/certificate.json` SHA `7ecdf0bc3adcf4f05a5fc40cb1db3695f7b0cb767c61aff5e74bf2e72f04b34e` 后续已由统一consumer消费，正式产物 `shared-native-type-declaration-inventory-reviewed-v1.json` SHA `2bc5e03c20fec2d42b347d455af03588dedbef6e039bca17072f18ef9dc4c4a6`。上节待审是历史状态。本族 [native_type_contract_v1.py](tools/solve_scalar_coverage/native_type_contract_v1.py) 重核公共consumer，逐行联立1293/1301单位附件及实际声明AST；本选集各关联公共批准13条measure中的**10条**，只作精确构建前件。

`native-type-contract-v1/type-identity-measure-contract.json` SHA `3cab2c52c6a3f43f19ffe772b996bdfa98380cad13e57fdd96132b185989c78c`，16.726秒、733依赖，6项TDD通过；`validation.json` SHA `b76e83a0129334c03be09439c0701f22dbd60b2501b08e4ea520604936fbba9d`。全部runtime caller保留，删除及branch排除均0；不能按同名helper删caller，config/undefined/outcome实际bridge仍OPEN。

[native_setter_attachment_v1.py](tools/solve_scalar_coverage/native_setter_attachment_v1.py) 使用公共setter准备v2，按完整unit/raw scope/node/kind与物理范围核对原pending E_assign的精确集合。`native-setter-attachment-v1/setter-joined-raw-scope-bindings.json` SHA `7425105b4c675e566497c0627d3b9c244dc4c20467d38212addd47c8592afdcf`，9.004秒、732依赖；保全1408/1483事件，仅将106/107项赋值来源关联唯一typed E_app候选。候选pending从229/230降至123/123，均29 sizeof与94 config；setter独审许可仍待，runtime/branch许可增量0。5项TDD通过，专项 `validation.json` SHA `fd5d8cd601c3e6fe56138679541be30ce9ee668a97b76137977b88979929713c`。原独审17项输入快照不变，新增量未混入其审查范围。

### 原生义务registry及旧证据逐项迁移准备

[native_legacy_identity_v1.py](tools/solve_scalar_coverage/native_legacy_identity_v1.py) 将既有全局token身份表中的全部 `scalar` 前缀owner去重，得到311旧key；只取owner=`scalar`会漏掉93控制因子和7库因子。258项与使用scope中事件的raw file、definition index、完整source hash/range、kind及真实AST路径逐项相等；其中149关键词节点、109infix token。scattered路径取公共投影的 `raw_clause_ast_path`，未盲拼DEF_scattered路径。其余53项原样保留为未匹配，不能按缺席判不可达。

`native-legacy-identity-v1/legacy-identities-and-native-obligations.json` SHA `3921c5a9d55aeba65f441bdc6e98251ee771704b4ab11cf0c843ce8c580a6ffd`，19.687秒、784依赖；8项TDD通过，验证SHA `47f7c8e46caa317b770f645bf1ee5c78e8aaf18089338a436dc8cd4278a9b8d7`。同时按原unit、root及修订D保留全部已知原生义务：

| registry层 | ordinary C++ | symbolic Isla |
| --- | ---: | ---: |
| typed site / 原有arm标签 | 1274 / 2186 | 1283 / 2202 |
| additional semantic义务 | 300 | 274 |
| type条件义务 | 1401 | 1505 |
| raw事件出现 | 1408 | 1483 |
| phase roots / entry D | 318 / 1176 | 318 / 1176 |

这些层有重叠，typed arm标签也包含尚待语义化的mapping合同；**不能相加为唯一运行分支分母**。registry用D→selected root→reached unit关系保留候选，不宣称整个笛卡尔积均可执行。完整dispatcher前缀、后缀及异常终尾继续引用stateful v2，未只按selected ctor裁剪。上述节点、额外义务和source/runtime关系仍需逐项证明。

[native_evidence_migration_v1.py](tools/solve_scalar_coverage/native_evidence_migration_v1.py) 另输出 `native-evidence-migration-v1/legacy-evidence-migration-preparation.json` SHA `7de846b25458a82d16416415001fc2bba0ac0b98bb84110edbdf9917438d7b58`；实际1.652秒、6项TDD，专项验证SHA `95a39e84b731d1d6d3972cbd14efcfb24160a9542456288e7bad8c5957f3eb8d`。逐条保存原合同selection path、附加配置后的义务hash、source身份状态及候选D引用；本步骤只重hash直接旧合同文件，未重跑旧consumer及其大规模trace依赖，因此只签引用守恒。

| 原有证据组 | 原有结论与剩余 | 向新原生branch正式迁移 / 待迁引用 |
| --- | --- | ---: |
| 旧runtime官方170方向 | 61 observed、109 open | 0 / 170 |
| sharedtrace runtime官方170方向 | 85 observed、85 open | 0 / 170 |
| 库decode-first 168 LHS | 104 observed、52 open、12条件静态 | 0 / 168 |
| 库direct-execute自身方向 | 52 observed；不替代decode-first的52 open | 0 / 52 |
| 34旧site的四配置限定处置 | 136配置/site对；不签通用不可达 | 0 / 136 |

696是分组保留的**证据引用数**，不是去重的branch分母。库direct入口在现行2352 D中没有对应域，明确空关联；没有偷配audit域。53未匹配key中24属于旧整函数未发射site，旧136静态引用中96指向这些site；其它40虽有raw身份也未升级静态许可。两个官方runtime仍分开记账，RHS、完整caller、异常总性及完整源码闭合均未新增许可。

官方两组各有112个 `encdec_when` key不在原1259项全局身份表，58个LHS key已有精确raw候选。独立请求 `native-legacy-identity-v1/shared-encdec-when-extension-request.json` SHA `7b6a7484c020cbb0ad40852d8238718447de3682774621c59c7538fedd202fc5` 已交公共owner：包含112精确旧key及两backend各112实际MCL_when导航，只请求增量token来源核对，原1259表不改写。即使token补齐，branch极性、actual D/初态、IR顺序与执行关系仍须另证。

### config来源候选增量：raw未配29/29

公共配置准备 `source-ast-full/configuration-source-projection-preparation-v2/candidate.json` SHA `17c852c70a61fc998a5cccf84b4e7ff1ed8c83fd0813c8d3358e6abbad6c44f8`，manifest SHA `3c17e62edd0d7a01ffa11059f52f0ad82754a1845bc1d0a1001430cbb3d34408`，仍为待审候选。公共层按原E_config根及E_field链恢复完整点分键；ordinary未传配置，保留94个runtime E_config；SYMBOLIC按冻结Yojson配置关联90个literal和4个enum，actual IR桥仍OPEN。

[native_config_attachment_v1.py](tools/solve_scalar_coverage/native_config_attachment_v1.py) 在setter附件后附加本族94/94项来源候选，逐条核对unit/scope/node/kind及原根token物理范围；原1408/1483事件、全部unit与scope保持不变。`native-config-attachment-v1/configuration-joined-raw-scope-bindings.json` SHA `72ce485e4bf8839cc4a6d8c132f4ef69c73609c09b0fe18cc55f8846ecfff1cb`，9.096秒、755依赖，5项TDD；专项 `validation.json` SHA `9c18c2ea85e8dcf33482ec71aa9be43845ffedcd8a6554872da9ed0a732995fb`。

候选唯一source身份1379/1454，未配事件29/29均为sizeof。历史229/230→setter后123/123→config后29/29是候选来源细化过程，**不是覆盖增量**；setter106/107和config94/94的正式来源许可仍分别待审。没有把ordinary residual config改称编译期常量，也未把SYMBOLIC literal来源关联当作初态、actual D或分支不可达证明。上节registry与迁移准备保持其冻结setter快照；本配置附件不改变原生事件身份、节点或D集合。

### 工具全集441与清单v19

实际命令 `python3 -m unittest discover -s agents/float_support_review/tools/solve_scalar_coverage -p 'test_*.py'` 为 **441/441 PASS**；wall31.498秒、unittest26.992秒，工具前后SHA无漂移。`scalar-tools-validation-v14.json` SHA `9f9e1ca6631c64345a118da91e4db42a0121e150d7e664064715466dac88417e` 绑定日志、argv及本次完整工具快照。与406快照相比新增type附件5、type消费6、setter5、旧身份8、证据迁移准备6、config5项测试；未新增模型执行。

[source_branch_worklist_v19.py](tools/solve_scalar_coverage/source_branch_worklist_v19.py) 生成 `source-branch-worklist-v19.json` SHA `9fb80552ca40d0c4fa5b69ec9d9d9f3edcd4234bab3f443493851b097b7610b2`（5根因、109直接输入全部重hash）。v19纳入type有限证、setter/config候选29/29、原生分层registry和696分组待迁引用；原生族17项独审仍引用冻结v1快照。生成器在441测试快照之后加入，只通过本次实际运行和引用核验，不冒称计入441测试。

当前完整运行branch分母尚未确定；`source_branch_closed=false`、`denominator_complete=false`。下一步依次核共享sizeof/when token来源及族实例独审，补实际D/初态/backend、source→IR的分支极性和异常关系，再逐组消费旧证并更新迁后remaining。旧observed和静态处置保留原范围，未因本轮来源候选而删义务或合并不同runtime。

### v19后增量：sizeof部分来源、族实例与setter有限证

公共sizeof候选 `source-ast-full/sizeof-source-projection-preparation-v1/candidate.json` SHA `334b22360180adf5c00cc553ff3a1abbcc0fe76ea43e9a9e626a97c64be365d2` 后续由 [native_sizeof_attachment_v1.py](tools/solve_scalar_coverage/native_sizeof_attachment_v1.py) 附加。本族27/27个raw ATyp_var关联实际`__size` overload产生的`__id`或`bitvector_length`调用；仅保留来源候选，`local_binder_resolution_proven=false`、actual IR与branch仍OPEN。另2/2个flen/regidx_bit_width alias未配，原raw行完整保留。

`native-sizeof-attachment-v1/sizeof-joined-raw-scope-bindings.json` SHA `e99690454b01ef2d3e09697ed01c0de2173712aa171b8ff7d364d0253c8c5dfe`，9.287秒、769依赖、5项TDD；专项验证SHA `67293722a120c2ee9ab2be5cdafbf385cf93c6b875f6d583b79ebdfe8e37ad4b`。原1408/1483事件不变，候选source身份1406/1481、未配2/2；不能把未配只剩2项解释为仅剩2条分支。

本族独立审查 `independent-native-root-raw-dispatcher-review/certificate.json` SHA `bc7d579c53dd1d9ab21e90a4097a4f6e3f2b96522389e171fd4c68d8fd53aedd` 已通过限定范围：17输入/761依赖前后零漂移，636物理根联立、2776 typed link回树、1243 scope及全部raw事件守恒，完整392/392/395/1 dispatcher与2352有状态结构域。25测试含21实际突变，34精确IR边界事实重核；其证书不含type/setter/config/sizeof后续增量，actual D/init/backend/module/effect/完整IR桥及branch分母仍OPEN。direct ctor入口明确不属于2352域，固定σ旧描述维持撤回。

setter公共正式产物 `shared-native-setter-source-identity-reviewed-v1.json` SHA `4342fe34a7bf65feaaaa4fb29e395ffa3f4f204b55c8e306ef9a7914e66f8966` 消费来源独证 `bc031a1c927f9a3a956b5f550932299e38ad78f04352ca8acd5fa00d21a2a82e`。本族 [native_review_contract_v1.py](tools/solve_scalar_coverage/native_review_contract_v1.py) 重跑统一setter consumer并逐完整候选行/hash联立106/107许可，同时重核族实例证书与证据清单。产物 `native-review-contract-v1/native-application-and-setter-source-reviewed.json` SHA `b49a764b73073c86fe668a1315c86d4d72a8dc3228f0ce3fc7e5aa4c21791c1d`，18.361秒、931依赖、6项TDD。新许可为原生族结构应用及setter来源身份；callee效果、运行分母、动态与静态排除均未升级。config94/94和sizeof27/27仍待独审，原2/2 alias未配。

53旧未匹配key另查完整5083 raw scopes，导航增量 `native-legacy-identity-v1/unmatched53-full-raw-navigation-addendum-v1.json` SHA `46a883141af5836b80e44349157be6f4083e4592b9090fcf445fb5277353d928`：52项具有精确原树路径但不在本选scope集，其中fle_H/S/D各16（各8 if、8短路token），get_F/set_F各2；另1项是float_class_onehot_bits的DEF_mapdef声明关键词，需要声明→实际全部clause关系，不能当作单条clause branch。该调查只细分未匹配原因，不签不可达或新增处置；原311/258/53及696待迁引用保持其冻结版本。

随后按原生流中的精确definition偏移重新读取该DEF_mapdef，导航 `native-legacy-identity-v1/mapping-declaration-ten-clauses-addendum-v1.json` SHA `b9fb31d4716cad404ed4f934e3a3a4d1482f4d69875ae829ec6c051738254402` 联立实际MD_mapping完整10条列表、各scope真实path/AST hash以及每backend10 typed unit。它提供此前1个声明的全部条款导航，仍未证明mapping方向、matcher/arm或entry域；不把旧单site视为一条运行分支，也不改写53未配历史。

### 112 when来源候选与696引用的身份增量

公共 `shared-additional-encdec-when-raw-identity-v1.json` SHA `ceddd5c376fe09d38e61fa9830b0c8acef41da5f1e6bd9ae2265ebd8af94e553` 已生成112个精确额外when token身份候选，与原1259物理token交集0，尚待独审。[native_when_attachment_v1.py](tools/solve_scalar_coverage/native_when_attachment_v1.py) 按每backend实际unit/raw scope/node及raw_clause路径联立mapping、guard、when三者完整AST hash；全部224绑定对应448个typed双侧guard链接，未用近似位置归属。

`native-when-attachment-v1/additional-when-identities-and-migration.json` SHA `9c25b961612883c9714620b7230df046fb78d2333586a859de8b475fbcf4064b`，9.432秒、948依赖、5项TDD；专项验证SHA `44eb61cc67790ba309705d7e45962e8afc2349b628bf741de01fa429b18a7d73`。在原696证据引用中，两个official runtime的224个guard引用由缺身份变为when来源候选；其余376个原raw候选和96个未在selected scope的静态引用原样保持。原runtime/config/entry/caller及候选D不变，正式branch迁移仍0、待迁仍696。

旧scalar前缀311键与新112键合为423个待处理旧source key，其中370具有raw事件候选、52在完整raw但不属于当前selected scope，另1声明有全部10 clause导航。三类身份关系不同，不能合并成branch覆盖率。旧1259表、311关联、v18/v19清单和各阶段失败记录均保留原字节。

### 当前清单v20与457测试快照

sizeof、有限审证消费和when附件加入后，工具全集再次实际执行 **457/457 PASS**，wall31.463秒、unittest27.148秒，工具前后SHA零漂移。`scalar-tools-validation-v15.json` SHA `7ea7298edf02eb4220755789468560c12a5bb18f9068e3bb63f2924ac0bc9b85` 绑定完整命令、日志与工具快照。

[source_branch_worklist_v20.py](tools/solve_scalar_coverage/source_branch_worklist_v20.py) 实际生成 `source-branch-worklist-v20.json` SHA `ace3bd57e92755a2d43c381848e35530ba6ef3a54a2614c9e29659ed8a71a85b`（5根因、120直接输入全部重hash）。本清单生成器在457快照后加入，未声称另行执行包含它的新全集。族实例与setter正式消费专项验证 `native-review-contract-v1/validation.json` SHA `e72d29dcc1b6a97b1f913c6d2951edbfe1e2e46e28a641895e295b247de6608a` 纳入同一清单。

当前已签范围是原生族结构、type身份/measure构建前件和106/107 setter来源身份；config94/94、sizeof27/27及112 when来源仍为待审候选，另2/2 alias未配。原生运行分母仍未确定，全部696分组旧证引用尚未正式迁移到原生branch。下一步必须补实际D/初态/backend/module/extern及source→IR极性、顺序和异常关系，再按原入口/runtime消费证据；`source_branch_closed`、`denominator_complete`、完整caller/RHS和异常总性仍未闭合。

### v20后config与局部sizeof正式来源消费

公共来源产物随后冻结：`shared-native-configuration-source-identity-reviewed-v1.json` SHA `99c5cce2564700897a95f15e66864b2f0d26fd82ca84f393b525aa4a454d7105` 消费独证 `72268417d51d9055575a0ca2fdc4352b0a8e371920eee8c1086b08e86fef79af`；`shared-native-sizeof-source-identity-reviewed-v1.json` SHA `85f1fce63c3e9ad5d8399ed6fa1acbba6a17276e7db6d7ed439bb45d3dce387a` 消费独证 `a92afdbb2be1fd38158c85fd751e3e0b63ecc7c3635e934eef9f58e3de6e2e9b`。上节v20的待审标志为其冻结时状态。

[native_projection_review_contract_v1.py](tools/solve_scalar_coverage/native_projection_review_contract_v1.py) 实际重跑公共 `consume('config'|'sizeof', reviewdir)`，与共享正式产物全字段相等；本族逐候选整行digest及全字段核对94/94配置、27/27局部sizeof来源许可，保留2/2 alias原pending行。新产物 `native-projection-review-contract-v1/config-sizeof-source-identities-reviewed.json` SHA `36f3e32c480d0e2a7921295a9d81600daa25b0402680cc9a02e798d6f6b34510`，16.741秒、999依赖实际重hash，6项TDD通过。

配置与sizeof正式许可仅限准确来源身份及已导出配置值；ordinary94 residual E_config、SYMBOLIC90literal/4enum与原始范围保持。局部binder、实际IR、D/init/backend与完整运行分母仍OPEN，新增动态/静态排除及696旧引用的branch迁移仍0。457全集是此消费者加入前的冻结快照，本增量单独6测试，不冒称已执行463全集。

### when正式身份与完整typed站点反向关联

前述config/sizeof正式消费专项验证 `native-projection-review-contract-v1/validation.json` SHA `a2d3480b81b8bc8216403546bf96f8f14a7806fe7f9e7fb0496624bace5a383d` 绑定6项测试与冻结产物。随后公共when正式身份 `shared-additional-encdec-when-raw-identity-reviewed-v1.json` SHA `2c97aab04c269a83a8ca96821aa2ce23c8fd1b37220dc1749a03cea47ef4bad6` 接入独证 `e316b165b009f6eccd09bbf741624573d7d13580a2d00276c359e0276dd5abf2`。

[native_when_review_contract_v1.py](tools/solve_scalar_coverage/native_when_review_contract_v1.py) 重跑公共consumer，逐候选完整行hash与来源整树核对112 key、224 backend绑定和448 typed双侧guard。`native-when-review-contract-v1/additional-when-identities-reviewed.json` SHA `5a107f0c677149cbc0ff1e4de030ca2f84c9a11553f8e83d9805c28174c2a706`，11.591秒、1043依赖重核、6项TDD；专项验证SHA `fea6b6d228ee49606c06f3d4d5625d8a71be21131257aa9f1deddc8089bf2b2d`。696旧引用中224 when来源身份正式、376原raw候选、96不属selected scope；branch迁移仍0，待迁696。原3项live路径FAIL完整保留。

[native_reverse_sources_v1.py](tools/solve_scalar_coverage/native_reverse_sources_v1.py) 保全ordinary1274、symbolic1283个typed站点，按同unit与完整AST路径反查raw事件；已有node_id必须相等。实际schema中when链接仅含node/path，短路节点以`@And_bool/@Or_bool`表示、raw链接保留`E_app`及准确布尔类别；两类均增加专项负控。最初两次生成因这两项schema差异失败，日志 `native-reverse-sources-v1/generation.log` 和 `generation-attempt2.log` 保留，第三次生成成功。

冻结 `native-reverse-sources-v1/typed-site-reverse-sources.json` SHA `f34c38538be7e8501568c5fac250dd61f5443c10459b685ef975294eec908c06`，38.574秒、1211依赖、10项TDD；专项验证SHA `b93070e26077c471e04b29ad2936ae473ba347af5402de57e898848f5fb1f833`。两个backend分别1261/1270个站点有直接raw链接，余13/13完整保留实际node/unit SHA、definition/path、父表达式和准确raw来源导航。2557个站点不是最终运行branch分母。

反向缺口每域为10个`E_if`、2个`E_exit`和1个`E_match`。其中每域flen、fregidx_to_regidx、wF_S、rF、num_of_vector_support与BF16正式来源包的backend/unit/node及完整AST相等，共复用10节点来源；rF和enum的共4节点另按原证书实际重验局部后端域。enum仍要求同一vector_support类型、五合法成员、非Poison且实参正常求值；rF仅证明抵达literal-false断言后的局部控制，caller/index/FS/扩展域未解除。两后端异常形式仍分别保留，不扩签其他生成节点。

### 16个新增来源候选，独立保留float_classify

[native_additional_origins_v1.py](tools/solve_scalar_coverage/native_additional_origins_v1.py) 对反向包剩余16节点增加来源候选：每域zreg、regidx_bit_width、wX的条件来自准确raw `base_E_enabled` 的4/5两臂；wF_H及三个execute实例来自 `ext_d_supported` 的8/4两臂。完整条件物理范围、公开Nexp_if、literal顺序及实际ancestor实例化相互核对；regidx_bit_width是直接sizeof，未虚构parent调用。

两个backend的float_classify均独立关联准确raw `assert(false, "float_classify internal logic error")`、完整typed `[E_assert,E_exit]` 顺序及unit实参。仅建立来源候选，未借rF审证赋予终态或不可达许可。冻结编译器type_check的sizeof展开、implicit实参和false-assert附加exit三段规则随包绑定。

`native-additional-origins-v1/additional-native-origin-candidates.json` SHA `3aea3d9f001a60a1f7ee2e9ad715a1a1c335179bc8d3ea6e80d2f151e60b164b`，12.193秒、1214依赖、8项真实节点负控；专项验证SHA `e6f43f9eb03e7c00cf7b938d2b5d831ec3b88f1d5d198c3b49ff44660ef2a172`。这16项仍待独审；此前10来源、4局部后端关系与2/2 alias待配历史分别保留。完整source→IR、D/init/backend、caller、RHS、异常总性和696旧引用迁移均未因此闭合。

### v21清单与487测试快照

上述消费者及来源候选冻结后，工具全集实际执行 **487/487 PASS**，wall33.823秒、unittest29.104秒，工具前后SHA无漂移。`scalar-tools-validation-v16.json` SHA `3dbf1c09e05becbbcaa968baabf6045324a2f12cc2a673ff1e631d5abf37688e` 绑定完整命令、日志和工具快照。

[source_branch_worklist_v21.py](tools/solve_scalar_coverage/source_branch_worklist_v21.py) 生成 `source-branch-worklist-v21.json` SHA `b437c56fd6724ebde6991247fd203573969410edf16dbf384dd3a6508eb1c243`，5根因、131直接输入全部重hash；生成器已在487测试的工具SHA快照内，本身通过本次实际生成与引用核验。v21正式接入config/sizeof/when来源许可、全typed反向关联与16新增来源候选。完整运行分母、actual D与所有696旧branch引用的正式迁移继续OPEN，未新增模型执行。

### v21后四named sizeof与16生成来源正式消费

公共named sizeof来源证 `361a5abd53689269818253c5b2b545ab745ecac47e8519b7c5a51ba06f43e9e1` 已由公共consumer消费，正式包 `shared-native-named-sizeof-source-identity-reviewed-v1.json` SHA `cdf9e3e3e97d80b6b3c4e54a6eac27e8aafcf0b910df2d5e9edfe2f6e04044b6`。[native_named_sizeof_contract_v1.py](tools/solve_scalar_coverage/native_named_sizeof_contract_v1.py) 重跑公共consumer并复用vector已冻结的准确join；本族每域flen/regidx_bit_width两个alias完整来源附接，原1408/1483 raw事件全部保留，selected raw待配归零。

`native-named-sizeof-contract-v1/named-sizeof-source-identities-reviewed.json` SHA `66ca1c507d34a0d2f42ca0314e736c290291aae61fbbfc7681151af70c864c3c`，13.928秒、1036依赖重核；复用join的6项测试实际通过，专项validation SHA `54f05241e664a0f70579476b04ccecf37db799f07119aeb0fcbf352bff6b16ec`。四个nested控制另与原反向包实际AST逐完整字段核对，`nested-controls-reverse-crosscheck.json` SHA `6498000171c5a8b92b5aaa9e581fe497a8d94a8aa01840f605a677f2ea4320b5`。这不改变旧反向包基于36f3输入时13/13无direct raw link的历史快照，也不签config折叠、module或IR关系。

16新增来源独证 `independent-additional-native-origins-review-v1/certificate.json` SHA `256243b663267a831cc7c6338cc640feb27abb6b7a6ec0aa85230d03c1f7f711`，审查正文SHA `5e51cf44768dc1498f5ad1066991265a48f0a5accfd37b92f56a09fe28615b6c`。[native_additional_origin_contract_v1.py](tools/solve_scalar_coverage/native_additional_origin_contract_v1.py) 只消费`signed_origins`的16项准确签名，按backend/unit/node、definition/path、完整node hash与审查行索引联立；22文件清单及1220独审依赖重新核验。完整泛型约束、nan_box外层times8重化以及classify原始`[assert(false,msg); undefined]`与typed`[E_assert,E_exit(unit)]`上下文均保留。

正式产物 `native-additional-origin-contract-v1/additional-origins-reviewed.json` SHA `5ac7fdc8077f3fa9860cd0aaaf4b5a62d7b98050458ffc26523be1d279db494c`，13.682秒、1240依赖、6项TDD；validation SHA `baf61aafe286c995f4b7c22171473c44e4428db2455e767beee38794354ade38`。2557 typed站点与原26反向节点完整保留，26列定生成来源现在均有正式证、来源待审0。仍仅原4节点有带前提的局部backend关系；新增14类型重化和2 classify exit不获得运行、backend桥或静态排除权限。

### 五旧消费者复产与696引用的原生节点导航

`native-legacy-consumer-recheck-v1/commands.json` 记录五个旧消费者的实际完整重跑命令，每组输出与原合同逐字节一致；汇总validation SHA `454657705fcf8725e722fd8cf7fc40984b9ff18c4ef83e575ffcc818b543b2f0`。旧official runtime核897依赖、26.204秒；sharedtrace official核17704依赖、72.748秒；library decode-first核352依赖、1.592秒；direct execute核974依赖、2.800秒；version-bound unlowered核338依赖、1.372秒。这里重跑的是证据消费者，没有新增模型执行，也未声称重新运行旧独审checker。

[native_evidence_nodes_v1.py](tools/solve_scalar_coverage/native_evidence_nodes_v1.py) 进一步联立复产合同、原696引用及准确raw scope/node/backend/unit，产物 `native-evidence-nodes-v1/legacy-consumers-and-native-nodes.json` SHA `864d94a2f71388e7a99ce84948af52dc9e4796bf59ab0f0c4a6cda417a14098f`，13.098秒、1273依赖、8项TDD；validation SHA `2f66c7f9757b9d0263f58defa8c6ea933312528e55c44da6f473fc8059e8ba0f`。600旧引用具有1876原生节点引用（ordinary940/symbolic936），96 selected外引用完整保留；1876是多对多引用数，不是唯一branch数。

mapping双侧guard均保留，ordinary对应关系不继承Isla动态证据，same-clause/phase保守root关联仍未证明可达。各runtime/config/入口继续分列，原生arm与IR极性、RHS、caller、实际D及异常总性均未补齐；正式branch迁移0、待迁696。

### actual initial331证与本族74类型义务

公共证 `source-ast-full/independent-native-type-dependencies-review/initial-pass-annex-v2/certificate.json` SHA `6e1a8245946c54fe783db7ddcd348fd0f4e24af72dff9534695a7a7479e12505` 仅签331项实际initial literal，公共正式消费包SHA `68c21ced853cdde4b8e53c61bc6b7f33a14cfb95033051b520438cf8db8e277f`。[native_initial_pass_contract_v1.py](tools/solve_scalar_coverage/native_initial_pass_contract_v1.py) 实际重跑公共consume并核全文相等，再以同unit的obligation/reference、definition完整path、原type节点hash及准确alias声明联立本族74项。

`native-initial-pass-contract-v1/initial-pass-type-obligations-reviewed.json` SHA `32fa81661500a9f9bc6dd679f42e887ae4ec5dbf8b94ab554b6037bdebeff748`，42.983秒、1769依赖、7项TDD；validation SHA `a690b5258069e7e2617787b6728dfde01e3a0a49acbe31ba6f714e9b144779eb`。其余257公共literal及两个zbkb pending不在本族selected义务交集；两pending保留完整非literal行，未冒用另行assert后缀证。ordinary没有literal转移，BF的10个E_if仍保留；完整未导出Env、module可见性、actual IR、完整分母和696运行branch迁移继续OPEN。

随后父级另行消费zbkb v3后缀来源证 `745f7f2fcce995965ddd43e13f513339f3bce697f65146b2d78dcba4c912c24e`，公共产物SHA `5741ba5a1fe714d116bcc108dab388df1deef6995f0c2f7265a53599708038c0`。本族以两个准确obligation ID核ordinary1567/symbolic1579个selected类型义务，交集均为空，补充导航 `native-initial-pass-contract-v1/zbkb-source-review-empty-intersection.json` SHA `a469dbd65d201c35cab3a9502a67518f0d9031406436ad92af4cd35f4aaef737`。因此不新增scalar来源义务；v2中的原literal映射仍OPEN，v3签的是assert-false后缀被exit替换的来源关系。这份空交集导航没有重跑v3公共consumer，不签zbkb运行不可达。

### v22清单与508测试快照

本轮工具全集实际执行 **508/508 PASS**，wall34.420秒、unittest29.206秒，工具前后SHA零漂移。`scalar-tools-validation-v17.json` SHA `d90e1e3bebe9f9dc8999d28c36837841fa3181aa0b2e73187c1ebf335a44f628` 绑定完整argv、日志及工具快照；vector共用named join的6项测试单独记录，不混入508。

[source_branch_worklist_v22.py](tools/solve_scalar_coverage/source_branch_worklist_v22.py) 实际生成 `source-branch-worklist-v22.json` SHA `06878acb421caacfcd89ee4f9632f5258cb1faf870667b1161e0ef57c0f26ebd`，5根因、143直接输入全部重hash。v22生成器在508工具快照内；本轮新增源码身份及initial类型前件、五旧消费者实际复产和600引用的1876节点导航均已接入。其后zbkb空交集导航另存，没有修改v22或旧证。

下一步继续7库因子actual native操作数与已审实际IR的局部LHS极性和顺序关系，再按runtime/config/入口推进正式迁移。selected raw来源pending0、26列定来源已审和74 initial literal均不代表完整运行分母；`native_runtime_branch_denominator=null`，全部696旧引用的branch迁移仍0。

### 唯一剩余语义义务表v1

[native_remaining_obligations_v1.py](tools/solve_scalar_coverage/native_remaining_obligations_v1.py) 将当前剩余证明任务按`category / gate / 完整semantic subject`去重。不同backend、入口、配置及constructor保留；同callee聚合为要求逐上下文证明的全称任务，全部原始caller/root出现仍保留。每项列明冻结输入的完整JSON路径及整行SHA、已有有限许可、未过门槛、具体下一步及owner。

`native-remaining-obligations-v1/remaining-semantic-obligations.json` SHA `b53ee0fc2045a348ad870257b55b9cc6cfe010983f78e7e5721cbeef03aa0dcd`，31.887秒、2444依赖。6项新增TDD通过；它们在508全集快照之后，单独记录。验证按完整路径重新读取17376个出现并重核整行SHA，10个直接输入重hash，全部696引用的反向剩余任务映射非空；validation SHA `0e6b6a2d86972982eb4d9a9ca85ab12b9fd76ae67745b0427a0eeb63520f5445`。供统一索引消费的小manifest SHA `b1aa10809ac59b6ddb8ef118963ba87991a3bbacf40cdf41964e8cfc19663a20`。

| 层 | 任务记录 | 保留的未过门槛 |
| --- | ---: | --- |
| source | 721 | 668项mapping来源方向，以及53个旧source key的selected集合外关系；包括96旧证引用的来源去向。 |
| typed | 3482 | 3480个准确类型/效果节点及两个后端的module、overload、extern依赖闭包；74 initial仅保留其准确许可。 |
| IR | 2557 | 实际后端节点、arm极性、求值顺序及正常/异常域；原4局部关系按原前提保留。 |
| caller | 2594 | 每unit的完整调用实参域、root路径、RHS正常性、效果与异常；不同上下文不自动共用证明。 |
| D | 2356 | 2352项有状态结构域的实际入口/初态/后端关系，加4项准确direct入口域；direct未并入encode/decode源域。 |

共11710条是跨层语义任务记录，**不能相加解释为运行branch分母**。包中完整保留2891 raw出现、2557 typed站点、636 root及全部有状态D、696旧引用（含96 selected外项）的映射。已有raw来源pending0、26来源正式、74 initial literal及五旧consumer复产均只作对应前件；旧branch迁移仍0。7库LHS局部桥是此表已有IR任务的下一步，不另增加覆盖计数。

### 七库actual native操作数与局部IR桥候选

[native_library_lhs_bridge_v1.py](tools/solve_scalar_coverage/native_library_lhs_bridge_v1.py) 从准确旧source key、raw scope/node和typed link读取两后端七函数的完整实际AST。它核单参数、float_bits结构pattern的字段/binder、嵌套let及最终返回值，保留完整binder来源；特殊`And_bool`必须与普通`and_bool`调用分开。全部14节点与原生site路径、node ID、完整AST hash相等，规范化后的LHS/RHS完整操作数与旧七库源表达式相等。

SYMBOLIC的四配置逐一读取实际完整IR函数，用新native操作数调用冻结旧独审的`static_lowering`函数，重建28份完整SSA/正常CFG；结果与`library-factor7-contract.json`中的局部证全字段相等。绑定ANF特殊短路规则及JIB完整`C.eager_control_flow`条件分支，实际局部CFG自身核对LHS条件定义、false短路赋值、true进入RHS及join。此次没有重跑动态checker或模型。

候选 `native-library-lhs-bridge-v1/native-library-lhs-bridge-candidate.json` SHA `340f1e56e3e734275394e76997d1a6aad9ada5a5c4dde10476da656d7bc54a49`，71.353秒、2520依赖；8项TDD通过，覆盖操作数交换、普通函数冒充特殊短路、field/binder变异、未绑定变量、额外block效果及错误owner。专项validation SHA `bb155ad562f650d5bf14b8211f1d1b919a91e73325357eda84922fbef6acc3c3`，manifest SHA `537b8a070d9f772676a2740ada2d112e3929bdc8d632eb64e0893a8e2768210b`。这8项同样不混入此前508全集。

新桥已交独审，状态为**候选**。完整Env/module与callee绑定、caller可达、RHS正常真值、异常总性及ordinary CPP后端关系仍OPEN；ordinary七节点仅来源对应。原14个IR剩余任务只增加候选附件，未改写唯一剩余表，也未迁移696旧branch证据。

### 七库候选与旧168/52引用的精确附接准备

[native_library_migration_attachment_v1.py](tools/solve_scalar_coverage/native_library_migration_attachment_v1.py) 从两个原冻结合同重新读取220条完整证据行，恢复原配置字段后逐项核`legacy_row_sha256`。实际runtime manifest、sidecar在原合同依赖中的完整哈希、config/IR、source key、symbolic unit/node、PC、taken及successor均精确联立。decode-first按原arm全字段检查；direct的52引用内128次实际出现分别核配置、入口、phase、privilege、root call、函数和方向，没有用一条代表替代其它出现。

`native-library-migration-attachment-v1/library-legacy-lhs-candidate-attachments.json` SHA `0d3c8d58b8bf9ccba34531dfddcfe312b9ccfe0ebaef44b360564a1ad55e64f1`，19.365秒、3356依赖重hash、6项新增TDD；专项validation SHA `9231cc2213358a0115860c89c688a02d9c1eff5dfe861fbe21cfb2c8d03e82ce`，manifest SHA `603f883c031ea599460d43bd3259f6bb35f8ec3a9afa655c85fa3567d6682c67`。220附接与476原索引未变引用的集合恰为原696；原完整行和全部direct出现保留在附件中。

本附件仍为候选消费准备。decode-first原104已观测、12条件静态、52未观测与direct自身52已观测分别保持；原340f七库候选及唯一剩余表未改写。actual D/初态、Env/module/callee、caller、RHS和异常门槛未因此通过，原生branch迁移0、剩696。新增6项测试单独记录，不混入此前508全集。

### Env v2 公共严格消费

[native_env_review_consumer.py](tools/solve_fix_integration/native_env_review_consumer.py) 提供 `consume(certificate_path, root)`，消费独证 `c185ed2699bc95dbbe0d97a110e636290c35dfa804d83fcf3b9dfa441ca300c0`。正式公共产物 `shared-native-environment-resolution-reviewed-v1.json` SHA `01e156b053b54f7babb485bef51c6c33df75e34f0e70858067ec62dddbf29af8`，实际254.737秒、1039个唯一文件重hash。810候选依赖、1035独审文件及全部组件核对；两后端6807/7060完整query逐digest及准确DEF_val候选重核，55584/57975原始出现逐完整AST owner/node/path和selection/join原行联立。

2340/2384组只用于导航，完整query对象仍由冻结大表SHA、完整query key及整行hash绑定；原始出现全部保留。两侧各13组union binding变体、各2个未typed loop-measure节点及其它完整未查询语法库存均保留。许可仅为prebackend、skip_initial阶段保存节点Env的公开API查询及准确声明候选；声明来源/body、module、local binder、caller、IR、运行与完整分母未升级。DEF_val的pre Env及item.loc/module未直接导出的边界、历史live三漂移FAIL均保留，v3未纳入。

16项TDD与7项完整实际索引／证书变异负控通过，包括删除完整query、抹掉13组union变体及证书权限升级。证据 `environment-resolution-consumption-validation-v1/validation.json` SHA `d53685cf39276ce18dc408c6cd0fd3dacd9b0840d35abef0a8cc01a6e03bfadb`，manifest SHA `1a90f16802f86ed2eebc7e880b4b3e98d3db5796e62c73c55a6cf0f5862c002e`。本节属于公共消费，不表示scalar已逐调用边附接Env，也不混入此前508个scalar工具测试。

### 七库局部桥独证与正式消费

上文340f“候选”是产生时状态；后续独证 `independent-native-library-lhs-bridge-review-v1/certificate.json` SHA `14727e530ec7c8a4d74e4db876a191f29a9e74f46631877265798f1ec5862591` 已通过8项producer、8项独立测试及24项实际输入负控，并复演完整候选逐字相同。独审核14函数完整raw/typed树、局部binder及调用求值事件，四配置28个局部SSA关系、540PC与56条件路径；单次record initializer、LHS先于Jump及RHS仅true求值分别保留。原z escaping检查失败记录保留。

[native_library_lhs_contract_v1.py](tools/solve_scalar_coverage/native_library_lhs_contract_v1.py) 按证书及2550独审文件、2520候选依赖严格消费，并重新联立完整函数、binder、准确typed link、配置/header、SSA路径、源码调用与实际SSA求值顺序。正式 `native-library-lhs-contract-v1/native-library-lhs-bridge-reviewed.json` SHA `f26614211b9679b2d69949b62940eb2c65c3f963ab68b70eca760548aeef8406`，21.672秒、2554唯一依赖；10项新增真实记录TDD通过，测试计数单列。

本轮七库validation SHA `c624670a96e30e8c9312f489fb41fe43c3e2a37ef1be3834b8f8aa37b0ac324a`，manifest SHA `7390d5d10dfbbff753c7f9af9fe24f2bd01138378232d2e4bfd4577a6b135090`，均在上述 `native-library-lhs-contract-v1/` 目录。完整实际argv、工具/证书/输出SHA、TDD红绿日志随包保存。

许可仅是准确七库原生操作数与局部正常LHS控制关系。ordinary七节点仍只是来源对应；Env/module/callee、caller、RHS值、异常总性、完整runtime和CPP后端关系仍OPEN。原14个IR任务完整行及ID保留，不自动销项；ANF/JIB的eager与短路条件均完整保留，不泛化任意配置。220旧引用附件仍另行待审，本证明确未审该附件；696 branch迁移仍0，source分母及所有完整闭合标志仍false。此轮无新编译、模型或solve运行。
