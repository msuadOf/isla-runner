# memory 分支独立审阅（2026-10-30）

## 独立结论

当前 memory 专项的方向合理：在现有 MemoryCallbacks 中增加字节数组、沿用 Sail 的 PMA/PMP 判断、按事件顺序输出内存状态，较好地保留了原结构。当前源码和所登记 IR 的文件哈希一致，不能继续沿用旧报告的“模型修改未进入 IR”结论。

但目前不能验收“JSON 是固定 Sail 模型可重放的具体见证”，更不能验收完整控制流覆盖。本轮在当前完整 IR 上独立确证两个会改变具体执行语义的 P1：符号地址绕过 concrete 内存快照；未约束 GPR 初值漏导出，导致现有重放前导改变 store 数据。另确证异常返回值仍包含 `Sym(...)`。这些不是单纯“覆盖未测”，也不是靠旧报告转述的结论。

本轮只读审阅、生成隔离证据和修改意见，未修生产代码、未提交、未移动分支。没有读取另一位审阅者的报告。

## 版本、方法与证据

受审根 `.worktree/runner-memory`：`31ef3b9a8aa3a9db4c03a1d99c191cadf1aadaef`；Isla：`bdd047bc67c357f3c6e9c4d34b5ec9daaf81ab57`；Sail-RISC-V：`c70482a73be2a67c5a89d88b1e6c2bbea224940c`。开始和结束均核对受审三个工作树无修改；原根的已有修改保留。

实际运行二进制为根目录 `isla/.worktrees/memory-consistency/target/release/isarch`，其源码工作树 HEAD 同为 `bdd047b` 且干净；SHA-256：`5fdffc71e8c7491fc482374add7f093a33ba5b3e949c485b290ddda8980d9d6f`。使用受审工作树的 `rv64d.ir`，SHA-256：`c65b26c8518042c67bfcb48c9feaf2a13a6eb7d741bc01ae8688d78c4370e5d9`；`LD_LIBRARY_PATH=/home/linuxbrew/.linuxbrew/opt/z3/lib`。本轮未重新构建二进制；源码适用性依据相同干净 HEAD、既有构建和新行为探针，不声称可复现构建证明。

独立核对 provenance 中四组 IR（RV64 V128/V256/V512、RV32）的全部路径哈希，每组 159 个模型文件的实际哈希均一致，见 [provenance-check.json](provenance-check.json)。这证明登记输入与当前文件一致；没有重新编译 IR，也没有证明全部 SYMBOLIC 替换与非 SYMBOLIC 模型等价。

7 次完整模型探针均使用单线程、内部 20 秒、外部 35 秒上限，均退出 0，共 14 条 JSON；没有执行预算采样配置。精确 argv、输入/二进制哈希、退出和耗时分别保存在每个探针目录的 `result.json`；原始 JSON 与日志均保留。入口为 [probe.py](probe.py)、[concrete_probe.py](concrete_probe.py)、[store_t1_probe.py](store_t1_probe.py)，汇总见 [evidence-summary.json](evidence-summary.json)。

14 条新 JSON 文本均经 GCC 和 Clang 汇编，并逐条与 JSON 机器编码比较，28/28 通过；[assembly.json](assembly.json) 记录工具版本、命令、编码及结果。[verify_evidence.py](verify_evidence.py) 对下述三个残留问题的证据做断言检查，退出 0。这是发现被复现，不是整项语义验收 PASS。本轮未运行 DUT、NEMU 或完整 Sail C 重放。

## P1-1：concrete 快照与数组没有统一，同一地址出现两个初值（已动态确证）

位置：受审 `isla/isla-lib/src/memory.rs:547` 的具体地址读直接访问 concrete 快照；`:579` 在数组回调启用时跳过符号地址与 concrete 区域重叠检查，最终进入符号读。`isla/src/isarch/memory_model.rs:62` 声明自由初始数组，`:115` 只约束读取等于该数组，未导入 concrete 初值。写侧 `memory.rs:641` 又统一写入符号数组，不更新 concrete 快照。

触发：配置 RAM `[0x80000000,0x80001000)` 为 concrete（MemoryBuilder 的 `add_zero_region`，全部初始为零），PMA 允许这段 RAM；执行 `amomax.d x3,x2,(x1)`，`x2=0`。仅比较“固定 x1”与“符号 x1”两种输入表达。

证据：

- [amo-concrete-fixed/result.json](amo-concrete-fixed/result.json)：`x1=0x80000000`，read region=`concrete`，读值 `0`，随后写 `0`。
- [amo-concrete-symbolic/result.json](amo-concrete-symbolic/result.json)：存在同样 `x1=0x80000000`、`x2=0` 的 `Retire_Success`，read region=`default`，读值 `0xffffffffffffffff`，随后写 `0`。
- 两次运行使用同一 [concrete.toml](concrete.toml) 与同一机器编码 `0xa020b1af`。这不是 PMA/PMP 域差异，也不是允许任意 RAM 初值的配置：该区域明确配置为 concrete 零快照。

影响：符号执行增加了原配置不允许的初始内存和 AMOMAX 分支；JSON 若反向把这个读值写成 pre-memory，重放的是修改过的内存配置。页表预置同样由 MemoryBuilder 创建 `Region::Concrete`（`memory_builder.rs:332`），因此有同类风险；本轮没有把页表风险声称为已动态复现。具体地址“先写再读 concrete”还会读旧快照，这是源码可见的同根因，不另冒充端到端实验。

最小修改建议：保留 MemoryCallbacks/SeqMemory 结构，但让 concrete 普通内存与数组共用一份状态。建立数组时表达 concrete 范围的初始字节约束；具体读也通过当前数组读，写后读不能回到旧快照。Custom/MMIO 后端需明确区分并按地址分派，不能简单把所有设备快照强行视为普通 RAM。至少增加“同一地址具体/符号表达等价”“concrete 写后读”“预置页表的符号 PTE 地址”回归。

## P1-2：STORE 的 GPR 初值被漏导出，当前重放代码必然改变写数据（已动态确证）

位置：`isla/src/isarch/target.rs:363` 对模型中 Arbitrary 的寄存器跳过输出；`:805` 的必输出集合只有 FPR/VPR 和向量上下文，没有 GPR。随后 `exec.rs:1958` 一带的访存事件输出使用补全后的模型值，所以初态与已具体化事件的数据依赖不完整。

触发：固定 `sd x6,0(x1)`（`0x0060b023`）、`x1=0x80000000`、M 态，保持 x6 符号且不加数值约束。

证据：[store-free-t1/output/rv64_zSTORE.json](store-free-t1/output/rv64_zSTORE.json) 的 `isa-state` 无 x6，但 write data 和 post-memory 都为 0。调用受审根的 `difftest-xiangshan/pipeline.py::make_assembly` 得到 [replay.s](store-free-t1/replay.s)：前导为初始化 `pre-memory:null`，连续执行 `li t1,0xa5; sb t1,...`；之后只恢复 x1，未恢复 x6。`t1` 就是 x6，因此 payload 实际写入 `0xa5`，而期望为 0。

受审消费代码对应 `pipeline.py:377`（pre-memory 使用 t0/t1）、`:608`（只恢复 JSON 含有的 GPR）、`:781`（先 pre-memory，再 scalar_setup）。这段汇编的寄存器数据流足以确证重放输入错误；本轮未以硬件运行包装成新的 GOODTRAP/FAIL 结论。普通 x2 源 STORE 和 SC 探针也均漏 x2，见 [store-free-data](store-free-data/result.json)、[sc-free-data](sc-free-data/result.json)。

影响：数据未参与分支约束，不等于数据不影响结果。当前 JSON 会让正确 DUT 因错误输入与 post-memory 不符，或者被依赖复位值的重放偶然掩盖。

最小修改建议：在最终同一 Model 上补齐所有执行相关 GPR；最简单且一致的方案是输出完整架构初态。若保留精简字段，必须保留完整初态旁路供重放，并依据实际数据依赖决定必输出项，不能仅依据 SMT 是否显式解释变量。消费端按完整初态在所有前导之后恢复 GPR。回归必须使用 x5/x6 等前导 scratch 作为 store/AMO 源，不能只固定源值绕过此问题。

## P2-1：异常返回值仍为符号字符串，未与最终见证一致具体化（已动态确证）

位置：`isla/src/isarch/exec.rs:1530` 在取得最终 Model 之前直接 `ret_val.to_str(shared_state)`，`:2032` 原样写 JSON；没有对应 `model.get_val(ret_val)`。

证据：[store-free-address/result.json](store-free-address/result.json) 的两个 fault 用例具有不同具体 x1：`0x0000080040000000`、`0x0000080000000000`，但两条 `Memory_Exception` 的地址均为 `Sym(112)`。同一现象也出现在 AMOMAX 探针的访问异常和对齐异常中。

影响：异常地址不再是自包含的具体 oracle；对返回值做分支聚类、异常地址核对或跨运行去重会遇到内部符号 ID。这一项本身未证明改变 store 的实际执行：目前消费者主要按异常类别分类，仍可能从其他字段恢复地址。它与上面两个直接改变执行输入的 P1 分开分级。

最小修改建议：取最终同一个 Model 后递归具体化返回值，再稳定序列化；保留符号形式只能作为另有标识的诊断字段。对异常地址、tuple/struct 和超过 64 位的返回载荷做实际值断言。

## P2-2：正常终值检查后的分量查询错误仍可漏入 gen（静态确证，未触发超时）

位置：`exec.rs:324` 的 `fmt_val_str` 使用 `.ok()` 吞掉具体化错误；`:447` 起的 `materialize_le_bytes` 同样以 `.ok()?` 吞掉 `model.get_var` 错误；独占写结果在 `:1980` 把所有非 Bool 成功结果归为 `None`。`:2005` 对未知分量只写日志，随后 `:2027` 仍生成正常 gen 项，且不增加 `model-query-timeouts/errors/unfinished-paths`。

新修复在“最终 check_sat 超时”时把案例放入 diagnostics、排除出 gen，这部分可接受；但 ModelEval 有独立超时错误（`isla-lib/src/smt.rs:1668`）。若该错误发生在上述事件字段查询中，当前通路会输出缺地址/缺值的普通 gen，而 summary 仍可能 finished。未知地址进一步导致 replay_memory 不建立该访问的 pre/post 字节，下游就少检查一次实际访存。

这是当前代码明确存在的错误传播缺口；本轮没有通过超时注入动态触发，不能报告“实际已有 N 条超时误算”。

最小修改建议：让这些 helper 返回 Result，区分允许的首写未知初值与必需见证分量求值失败。ModelEval 超时和不可具体化的地址/data 应进入 incomplete diagnostics，并使 summary partial。首写 pre-memory 的 null 可以继续保留，它表示自由初值，不能与求解失败复用同一含义。

## P2-3：加载、SC 和向量异常的寄存器后态尚不能由当前 JSON 验证（已核实能力缺口）

位置：`exec.rs:562` 的 AssemGenJsonItem 只有 `isa-state`、ret_val 和内存事件/前后内存，无寄存器后态。`target.rs:341` 查询的是 pre_state，而不是终态 frame.regs。

证据：新 LOAD 探针产生成功 read，但 JSON 没有 x2 最终值；SC 覆盖配置产生两个 `Retire_Success`，一条写、另一条无事件，却没有 x3 的 0/1 结果。模型 `extensions/A/zalrsc_insts.sail:76` 会写 SC 返回寄存器；向量 `extensions/V/vext_mem_insts.sail:68`、`:72` 会在逐元素执行时更新 vstart/目标寄存器，异常可保留部分更新。仅凭内存事件不能重建所有掩码、tail/prestart、fault-only-first 的寄存器效果。

reservation 边界也需明确：覆盖配置 `riscv64_memory_coverage.toml` 将 match_reservation 设为符号 bool，而 load/cancel_reservation 为空操作。它确实让 SC 成功/失败控制流都可见，这不是数组模型 bug；但它是外部平台响应抽象，不建立 LR→SC 地址/宽度/取消状态关系。JSON 没有记录 reservation 初始条件，当前 pipeline 无 LR 前导，不能据此称 SC 成功例可直接独立重放。默认 difftest 配置将 match_reservation=true 只选择成功域，属于配置域选择，不应冒充双结果覆盖。

最小修改建议：在同一最终 Model 输出相关完整前/后寄存器状态及显式外部平台条件。SC 的可重放见证应带准备 reservation 的序列/契约，或明确标记为仅平台响应假设下的语义案例。验收至少包含 LOAD/AMO 的 rd、SC 的 rd 与 reservation 两态、向量部分完成后的目标寄存器/vstart/vl。此项为能力缺口，没有仅凭缺字段断言 Sail 算错。

## P3：ExecuteAs 重建丢失路径身份和预算历史（静态核实）

位置：`exec.rs:1432` 的 continuation 仅存 instruction/checkpoint；`:2285` 用 `LocalFrame::new` 重建执行帧，未携带 `execution_limit_state/path_timing`；该状态属于 frame（`isla-lib/src/executor/frame.rs:173`），不在 SMT checkpoint 内。对照该文件 `:425` 的 `new_call` 会显式复制执行限制状态、寄存器和内存。

当前固定 Sail 的 C 解码 ExecuteAs 返回之前没有访存/寄存器写入，故本轮没有发现重建初始寄存器/内存使当前 C 访存算错。问题限于压缩前段的 path-signature、累计 fork/采样/路径时间状态不进入续段；不能把最终签名解释成全程路径身份。首段 collector 已统计 sampled_paths，因此不能误说这会必然使整个 summary 漏标 partial。

建议复用已有保留状态的 frame 调用/续执行能力，至少传递 execution_limit_state 和 timing；不要另建平行执行器。若暂不修改，文档应明确续段签名和每段预算边界。

## 配置域、控制流和结果合同的其余结论

- 源码→IR：目前登记的输入哈希可核对，segment v31 组界与 vstart 修改所在模型文件已在 manifest 中；IR 旧错配问题不再作为本次缺陷。向量访存主体 `vext_mem_insts.sail` 保留掩码、元素/segment 顺序和异常返回的循环，没有用 SYMBOLIC 删除这些主体分支。SYMBOLIC 的 read_vreg/pack helper 是现有路径的替换实现，完整等价性未在本轮新测。
- 数组内存：普通符号 RAM 的逐字节 Select/Store、小端组合和路径 clone 结构合理；AMO 的读后写顺序由真实模型探针可见。exclusive Bool 钉 true 与当前 Sail write_ram 已提交事件的接口一致；SC 失败在发写事件之前分叉，不应仅凭钉 true 判定吞掉失败路径。混合后端的 P1 必须先修，现有数组单测不能代替这一边界。
- 地址/异常/PMA/PMP/页表：本次动态探针覆盖了已指定 PMA 域内成功、域外 AccessFault、AMO 地址对齐异常。默认测试配置钉 satp=0、开放 PMP、RAM-only PMA 和排除 MMIO，属于明确选择的环境域。它们不能支持“PMP 拒绝、页表各级/权限/A-D、MMIO、副作用均覆盖”的验收；不能把该域外未测直接归因于求解器漏分支。
- 采样/配额/错误：源码已将采样、配额截断、Poison/未完、执行/SMT 错误和待运行批次计入 summary；`model-coverage=not-measured` 避免把 finished 等同完整覆盖。编码守卫拒绝数单独输出而不自动 partial，可解释为只输出可编码域，但必须明确该域定义。`:1794` 回环执行 Err 只日志并丢弃，及汇编/编码 None 返回处仍未统一计入遗漏原因，建议与 P2-2 一并封闭收集出口。普通保留编码拒绝与内部执行失败不应合并。
- 批次：每批结束合并 items/diagnostics/summary 并写 pending_batches，已完成批不会被后来批覆盖为仅最后批。第一批被外部硬杀仍无新 JSON，计划期失败也不写本轮失败产物；若复用 output 目录，下游需要 run-id/目标清单防止使用旧文件。这是静态产物边界，本轮所有探针使用新目录，未构造旧产物污染。
- 终值超时：最终 check_sat 超时条目已退出 gen，避免旧版仅凭 Retire 文本误算。尚未封闭的是 P2-2 的字段 ModelEval 失败通路；本轮未运行盲目长时间超时搜索。
- 汇编：本轮新例的 GCC/Clang 和 JSON 编码一致；这只验收 14 条新例，不能外推全部 memory 指令、扩展或编码组合。

## 可接受能力与建议顺序

可接受：保留现有架构的专项支持方式；已具体固定的环境域中的符号 RAM 读写/AMO事件输出；SC 平台匹配真假两路的探索能力；输入来源哈希登记；终值 check_sat 超时诊断与 gen 分离；本轮 14 条汇编编码的一致性。

不能验收：含 concrete/预置页表混合后端的统一内存语义；当前所有 JSON 的自包含重放；内存加载和向量部分完成的寄存器后态 oracle；LR/SC reservation 状态关系；完整 Sail 控制流覆盖和完整硬件重放。

建议顺序：先修两个 P1，并在当前完整模型上重跑最小反例；随后修异常返回值和字段求值错误的结果合同；再补完整前/后态与 reservation 重放条件；最后完善 ExecuteAs 路径状态、批次运行身份，以及分离配置域的源码分支核账。无需为这些修复改写 Sail 访存主体或推翻 MemoryCallbacks 结构。
