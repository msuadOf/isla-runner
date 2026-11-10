# Sail-RISC-V 与 Isla 内存协同接纳审阅

2026-11-02。结论：**设计方向及主要结构可接受，当前整套实现需修改后接纳。** Isla 有两个本轮重现的 P1，会使初始内存或重放输入与配置、见证不一致；Sail-RISC-V 的非陷阱 vstart 策略还漏了全寄存器访存早退时的 vstart 清零。这些问题可以沿现有接口修正，不需要重写模型或执行器。

## 版本与方法

| 组件 | 基线 | 受审版本 | 专项范围 |
| --- | --- | --- | --- |
| Sail-RISC-V | `4f2ac293` | `feat/sail-riscv-memory-by-model-20261022@c70482a7` | 3提交、4个model文件及24份预算配置 |
| Isla | `f06371f` | `feat/memory-consistency@bdd047bc` | 13提交；数组内存、PMA/CSR、编码分片/守卫、IR及输出合同 |

Isla 基线已有 isarch、MemoryCallbacks、执行限制和内存事件，不能把相对上游 master 的全部开发历史当作本专项新增。用户明确要求按两个目录协同判断。本轮未修改生产源码、分支、索引、共享 target 或旧输出；只新增审阅材料并同步根仓状态文档。Isla 工作树已有 README、scripts/run.mk 修改，主要是官方 Z3 及策略入口，已保留。

直接阅读当前 diff、调用者、内存分派、最终模型和消费者汇编；旧审阅只作为定位线索。使用当前已有 Release 二进制重新运行有界探针，没有重新构建，不能把这些结果表述为可复现构建证明。版本、二进制哈希、动态库解析和 Z3 版本见 [versions.json](versions.json)；每个探针 result.json 保存实际 argv、配置/IR/二进制哈希、时间和退出。

## 必须先修的问题

### F1 — P1：同一 concrete 内存地址，具体读取与符号读取使用不同初值

位置：Isla `isla-lib/src/memory.rs:575-605`、`src/isarch/memory_model.rs:62-66,107-119`。

配置把 `[0x80000000,0x80001000)` 设为 concrete 零内存，PMA 允许访问；执行 `amomax.d x3,x2,(x1)`，x2=0。

- 固定 x1=`0x80000000`：读0，写0，见 [具体地址证据](amo-concrete-fixed/result.json)。
- x1符号化：同样选出 x1=`0x80000000` 的成功见证，却读 `0xffffffffffffffff`、写0，见 [符号地址证据](amo-concrete-symbolic/result.json)。

原因是数组回调声明自己约束符号读，跳过 concrete 重叠检查，但初始化数组时没有导入 concrete 内容。具体地址仍由 `read_concrete` 读取快照，符号地址则读自由数组。当前写入数组后再具体读，也可能回到旧快照。页表由 MemoryBuilder 构造为 concrete，存在同类风险；本轮没有实际运行符号页表反例。

这是执行允许了配置禁止的初始内存，不能仅归为覆盖不足。最小方向：保持 MemoryCallbacks/SeqMemory，把普通 RAM 的具体快照与数组初态及后续写入统一；设备后端继续按自身合同分派。增加同址具体/符号访问、concrete 写后读及预置页表回归。

### F2 — P1：未约束的 GPR 初值被过滤，新内存见证缺少必要输入

位置：Isla `src/isarch/target.rs:353-367,805-816`；消费者 `difftest-xiangshan/pipeline.py` 的 pre-memory 前导与 scalar_setup。

固定 `sd x6,0(x1)`、x1=`0x80000000`。本轮 JSON 的写事件和 post-memory 都要求0，却没有 x6 初值。当前消费端为首写自由初值生成 `li t1,0xa5; sb t1,...`，然后只恢复 JSON 中存在的 GPR。t1就是x6，payload实际写入 `0xa5`，而预期为0。

证据：[新JSON](store-free-t1/output/rv64_zSTORE.json)、[当前消费者生成的汇编](store-free-t1/replay.s)。这次验证了生成汇编的数据流，没有执行硬件。

Arbitrary 过滤策略早于本分支，但新增具体化内存事件后，原策略不再满足自包含重放合同。分支已为相同原因补齐 FPR/VPR，却没有补齐 GPR。最小方向：在同一个最终 Model 输出执行所需 GPR 初值，或直接补齐完整架构初态；消费者在所有前导后恢复这些值。不能以“数据没有影响分支条件”推断“数据不影响指令结果”。

### F3 — P2：非陷阱 vstart 策略未补齐全寄存器访存的成功后态

位置：Sail-RISC-V `model/extensions/V/vext_mem_insts.sail:523-524,581-582`。

`process_vlre/process_vsre` 在 `start_element >= nf * elem_per_reg` 时直接返回 RETIRE_SUCCESS，跳过末尾的 `set_vstart(zeros())`。向量指令正常完成应将vstart归零。原早退代码已有此遗漏；本分支把 get_start_element 的越界陷阱删除后，全1这样的高位输入新增进入该成功出口，因此非陷阱策略的接续不能仅替换返回类型。

新增 [后态探针](probe_vstart_post.py) 使用生产IR的隔离副本，仅重命名两个helper并加wrapper，原函数体逐字保留，调用后断言vstart；生产IR未改。`vl1re8.v v1,(x1)`（`0x02808087`）及 `vs1r.v v1,(x1)`（`0x028080a7`），固定vstart全1：两个“最终等于0”断言均被过滤，两个“最终仍为全1”断言均通过并返回Retire_Success，无访存。方法及IR哈希见 [插桩记录](vstart-post-instrumentation.json)，各 `whole-*` 目录保留命令与结果。这证明后态遗漏，不只是缺少JSON字段。

最小方向：保留原早退结构，在两个正常退休早退出口先 `set_vstart(zeros())`；不应重新加回越界陷阱。补全evl边界及高位vstart的load/store后态回归。

### F4 — P2：异常返回值没有用最终 Model 具体化

位置：Isla `src/isarch/exec.rs:1530,2032`。

`ret_val.to_str` 在取得最终模型前执行，最终原样写JSON。本轮 [自由地址store](store-free-address/result.json) 的地址寄存器已具体化，异常却仍是 `Memory_Exception(...Sym(...))`。这妨碍异常地址成为可独立检查的 oracle。该旧缺口在当前受审版本仍存在，不能把当前 JSON 整体称为具体结果。

最小方向：复用 `Model::get_val` 递归具体化返回值，使用同一最终模型；符号形式仅保留为另有标识的诊断字段。

### F5 — P2：字段具体化错误仍会变成普通 gen 的空分量

位置：Isla `src/isarch/exec.rs:324,447,469,1980-2006`。

`fmt_val_str`、字节具体化及独占写结果查询用 `.ok()` 等方式吞掉求值错误；未知分量只记日志，条目仍进入 gen。最终 check_sat 超时退出 gen 的修复是正确的，但没有覆盖随后 ModelEval 的超时/错误。

这是静态核实的错误传播缺口，本轮没有动态触发字段超时。最小方向：helper 返回 Result；必需地址/data求值失败应进入 incomplete diagnostics，并反映在 summary。首写自由初值的 pre-memory:null 仍是合法表示，不能与求解失败混为一谈。

## 结构与合理性判断

| 改动 | 判断与理由 |
| --- | --- |
| segment寄存器组界 | 可接受。保留EMUL×NFIELDS≤8检查，新增 `reg + NFIELDS×ceil(EMUL)≤32`；普通/strided/indexed load/store沿用原合法性辅助函数，indexed按数据组EMUL检查。store增加vs3参数有直接必要性。 |
| vstart非陷阱策略 | 方向合理，需补F3。保留高位越界值导致无活动元素的行为，未把vstart固定为代表值。共享helper返回nat后，16个调用点作接口接续，未重写向量执行主体，但两个全寄存器访存早退漏清零。它不是对所有实现必须采取相同行为的声明，也不是只影响内存指令。 |
| 数组内存 | 抽象位置合理。通过既有MemoryCallbacks安装字节Select/Store模型，按路径Clone保存当前数组符号；PMA/PMP/异常仍由Sail执行。问题在F1边界，修复无需另建执行器。 |
| PMA与CSR | 配置解析放config、RISC-V注入放Target；符号值在同一solver声明并在checkpoint前注入。沿用Sail原PMA匹配和CSR逻辑，没有在Rust里重写PMA/PMP算法。配置选择的satp/PMP/FS/VS域应作为受测域理解。 |
| 128位比较 | 8个通用位向量比较primop及IR加载期替换有明确的i128表示问题依据；没有把AMO整条指令搬进primop。该判断不等于验证所有129位以上有符号具体值能力。 |
| 值提示及编码分片 | 可作为显式定向探索工具。执行仍回到现有模型及编码守卫；固定操作数字段是配置选择的子域，不能把每片完成视作全模型覆盖。 |
| IR与预算 | 当前配套一致。四配置各159个model文件、5个IR路径及生成配置哈希全部匹配；79份预算、130个region及22处注释锚点有效。79份基准IR哈希告警符合既有strict=false约定。 |

ExecuteAs已能续执行压缩访存，本轮C_LD得到实际read事件；但续段使用LocalFrame::new并重装初态，没有复用已有new_call保存路径身份、预算与累计时间。这是后续宜沿原接口收敛的结构问题；当前模型压缩前段无访存/寄存器写入，未据此断言本轮压缩访存数据错误。

成功LOAD/AMO的rd、SC返回寄存器和向量部分完成后的寄存器后态仍不在JSON中；SC覆盖配置只是符号化外部reservation匹配响应，并未建立完整LR→SC关系。这些是验收范围限制；不能从已有内存事件推导全指令后态或SC独立重放已验收。

## 本轮验证与限制

命令入口：`python3 agents/coordinated_memory_review_20261102/probe.py`。证据核对：`python3 agents/coordinated_memory_review_20261102/verify_evidence.py`。每个result.json保留精确命令，可在全新目录复跑。

最终9个主探针退出0，共16条JSON：AMOMAX concrete/符号地址两组、store源未约束、store地址未约束、segment越界、vstart最大/零、SC外部响应两路、压缩load。两项P1与符号返回值问题重现；segment越界返回Illegal且无读、vstart最大退休且无读、vstart零退休且一次读、SC有写/无写两路及压缩访存符合指定行为。

其中8个summary为finished，自由地址store为partial/errors=1。另开 `store-free-address-debug` 诊断复跑（退出0、3条JSON，未计入上述16条）确认一条路径停在 `sys/vmem_utils.sail:224` 的SymbolicLength/subrange_internal；错误被summary正确记录。其余完成路径足以复现符号异常返回值，但不能把该指令标为全路径通过。本轮未定位这个动态宽度能力限制由哪个历史提交引入。

另有F3的4次隔离IR后态断言实验：2次零值断言被过滤、2次全1断言通过，各次退出0。此处退出0/summary.finished不代表零值性质通过，必须检查assertion-filtered-paths和生成条目。命令入口：`python3 agents/coordinated_memory_review_20261102/probe_vstart_post.py`；临时IR位于根仓`.tmp/coordinated_memory_review_20261102/`，脚本可重建。

最初三个向量探针错误地使用了VS=Off的输入，固定编码在启动译码时被拒绝，退出1。原日志保留在不带 `-vs-enabled` 后缀的目录；明确设置VS使能后，在带后缀的新目录重新运行。初次失败不记为模型回归，也不静默覆盖。

IR及配置核对见 [provenance-check.json](provenance-check.json)、[workaround-check.log](workaround-check.log)。本轮未重新生成IR、未重新构建工具、未全量类型检查/单测/Clause回归、未运行硬件或全后态对照。没有用16条样本签收完整覆盖。

**接纳建议：保留当前模型/回调/Target分层，先修F1和F2，补F3清零并闭合F4/F5结果合同后接纳整套。** Sail-RISC-V三提交的方向可以保留，但不能漏掉新成功域的后态；不能把未修的Isla重放能力标为通过。后续涉及源码生成IR时同步provenance和预算坐标，再重跑这些最小反例。
