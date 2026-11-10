# 内存正确性修复独立审阅

日期：2026-11-02。审阅者未参与本轮实现。基线为模型 `c70482a7`、Isla `bdd047bc`；本报告只评价本轮改动及其明确承诺的正确性合同。

## 接纳结论

**接纳本轮 F1–F5 正确性修复，未发现未关闭的 P1/P2。** 首轮独审指出的汇编/编码字段诊断缺口及随后发现的回环译码错误静默丢路径，均由最终 `exec.rs` SHA `2046fb3d…` 修复并复审。接纳依据包括源码控制流、四配置 IR/provenance 哈希、最终二进制下两条独立完整 IR 探针，以及下述最终集成和后态断言。结论限于本轮指定范围与已测配置，不宣称全指令域覆盖。

## 源码阶段发现

- **F5 输出诊断缺口，P2，审阅发现后已修复**：原 `src/isarch/exec.rs` 的 `try_get_assembly_name`、`try_get_assembly_encdec`、编码 `FmtVal::from_val` 报错出口未写 JSON incomplete 诊断；相邻 `encdec_guard_roundtrip_ok` 的 `Err(error)` 甚至未计错误，可能把丢失路径的摘要误标为 `finished`。最终 `exec.rs` SHA `2046fb3d…` 的四处出口均留下字段名、路径签名和符号返回值；回环 Err 再计入错误，摘要变 `partial`。静态复审了新 helper 的四个调用及原 `Ok(false)`/`Ok(None)` 正常过滤；新增非位向量回环错误回归实际检查 `partial`、1 条 incomplete 和空 `gen`。实施者报告 exec 定向 56/56，本审阅没有把该数字当作独立运行。

## 已独立核查的源码合同

- `process_vlre`/`process_vsre` 只在原有正常早退 `start_element >= nf * elem_per_reg` 前新增 `set_vstart(zeros())`，原有陷阱返回及其余循环未改。`vmtype.toml` 的半开 region 行号已对应新源码 `658:2–679:3`，仍只圈住 `process_vm` 的逐元素循环。
- `SeqMemory` 保存初始数组和当前数组；Concrete 非零快照逐字节写入初始数组，Concrete 零缺省通过读时对初始数组加条件约束。普通内存的具体读现在走数组回调，故与符号读、写后读共享当前数组。数组 `Store` 链的地址加法保持位向量回绕，路径 clone 保存当前数组变量。
- `Memory` 在 array 模式下仍将已确定的 Custom/Constrained 地址交给专属读分派；可能触及专属区但地址不唯一时明确报错并使路径不完整。跨专属边界访问按每个字节检查，包括 `u64::MAX → 0`。无专属区域时不增添此重叠检查。capability tag 仍被 `SeqMemory` 明确拒绝，符合本 RISC-V 求解入口原有约束。
- RV32/RV64 的 `x1..x31` 均进入必输出初态，`x0` 不进。返回值使用取出的最终求解模型递归具体化；必需访存地址/读值/写数据/独占结果求值失败走 incomplete，普通写的 Bool 仍为非必需字段。
- `Memory::write_byte` 安装数组回调后不会更新已声明数组。这是公开 API 的前置时序限制，但本轮生产调用链在 `MemoryBuilder` 完成所有预置后才调用 `install_seq_memory`，安装后无 `write_byte` 调用，故不是当前生产路径缺陷。后续若增加安装后预置，应先改此合同。

## 独立证据与边界

- 静态核对模型、workaround 及 Isla `memory.rs`、`memory_model.rs`、`target.rs`、`exec.rs` 相对指定基线的 diff 与调用上下文；`README.md`/`scripts/run.mk` 起点已有修改，后者不归本轮回归。
- 独立重算四组 provenance：manifest 的 4 artifact/5 个 IR 路径哈希都匹配安装文件；每配置 159 个源文件、合计 636 条哈希同时匹配当前模型和冻结快照；四配置哈希及 dirty patch SHA 都匹配，四组 `generation_exit_code=0`，默认 `rv64d.ir` 与 V128 副本逐字相同。manifest 明示模型基线 `c70482a7` 加 dirty patch；Sail 仅有版本字符串，工具源码树无 `.git`，不声称其完整 checkout 哈希已核实。
- 独立读取根级 `green-integration` 的 JSON：Concrete 固定地址和符号地址成功 AMO 的读值均为 `64'h0`，写事件与后态同源；`store-free-t1` 含完整 31 个 GPR。`model/green/result.json` 有 8/8 定向条件获接纳、8 份 `finished` 结果；前版 `red-v2` 仅 2/8，六个早退断言未通过。后态脚本在原 IR helper 函数体外加 wrapper，断言返回后 `vstart=0`；最终 `model/green-final/result.json` 用已安装 V128 IR 来源哈希和最终二进制重跑，8/8 `finished`、8/8 后态断言未过滤。
- **独立完整 IR 运行**：最终 v4 `isarch` SHA `ed4685e0…`、已安装 RV64 IR SHA `c0e4661a…`。在本报告目录 `.tmp/amo-concrete-symbolic-v4/` 限时运行符号地址 AMO（命令、配置 SHA、日志、结果见 `independent-check.json`）：1.87 秒、exit 0、`summary.finished`、4 条 gen；实际 Concrete 读值均为 0，31 个 GPR 齐全，返回值无 `Sym(`，必需访存字段非空，诊断数 0。另在 `.tmp/store-free-t1-v4/` 运行 `sd x6`：1.27 秒、exit 0、`finished`、1 条 gen；x6 初态等于写数据，生成的重放前导在 pre-memory 写完后恢复 x6。两次运行均使用生产 IR，检查记录为 8/8 与 6/6。它们验证定向行为，不代表全 Clause/全指令域覆盖。
- 最终 `final-build-inputs.json` 的二进制、manifest 及四个生产源码 SHA 与工作区实物均匹配；动态库解析为官方 Z3 `libz3.so.5.3`。主 agent 的最终全 Isla lib 日志显示 163/163 通过，`git diff --check` 对模型和 Isla 两个工作树均通过。根级 `final-integration/checks.json` 为 65/65，12 组共 19 条 gen；独立逐份读取 JSON 见 11 组 `finished`、1 组 `partial`。后者 `store-free-address` 的 `errors=1` 与此前定位的自由地址 store `SymbolicLength` 能力限制一致，3 条已生成见证保留；本次日志没有单独打印该错误种类，故不把其精确归因写成最终日志直接证明。正式 `make-final/result.json` 的 `solve-C_MUL` exit 0、`finished`、1 条 gen、零错误/超时；旧 `make-smoke` 的 MRET 仍是 `partial`、1 条 unfinished，不能混写为 PASS。这些全量测试与集成由主 agent 运行，本审阅独立核账结果和哈希，但不称为我亲自执行。
- 独立重算最终 19 条见证的汇编文本/编码多重集与先前 GREEN 19 条完全相同，并核对 `assembly.json` 的 38 个源文件 SHA 均匹配、GCC/Clang 编码检查 38/38 通过。最终诊断出口补丁没有改变这些见证的机器码。
- 基线已有 `Excluded` 区域对顶端回绕访问的漏判：`excluded_overlap` 与 `smt_excluded_constraint` 使用不回绕区间。此次改动未触及这两函数；它限制“所有区域均支持回绕”的泛化说法，但不构成本轮回归或五项修复的接纳阻断。

## 保留边界

- `Custom`/`Constrained` 与普通 RAM 均可能命中的符号地址会明确报路径错误，不会在同一回调内分裂并保留两种设备行为；这是已记录的能力边界，不应把这类路径算作已覆盖。array 模式的 capability tag 仍不支持。
- 未独立运行全部 163 项 lib 测试，也未跑全 MEMORY/向量 Clause 或硬件差异测试；独立动态证据是上述两条完整 IR 探针。Sail 工具链只有版本字符串和二进制哈希，源码快照没有 `.git`，无法证实其完整源码提交。
- `Memory::write_byte` 的安装后调用时序，以及基线已有 `Excluded` 顶端回绕漏判，均已在本报告说明。它们没有被本轮修复，也不应从本轮接纳结论推断为已解决。
