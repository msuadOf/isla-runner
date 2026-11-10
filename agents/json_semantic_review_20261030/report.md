# float / memory 根版本的 JSON 与模型语义独立复审

## 结论

**两套版本都已具备有用的专项能力，但目前不能按“生成JSON覆盖所固定Sail-RISC-V源码的控制流语义”签收。** 浮点数值层与内存数组层的正面证据较强；当前主要障碍是源码/IR不一致、产物字段不一致，以及缺少可区分完整/采样/失败结果的覆盖合同。

本轮是主agent重新核对固定提交、独立构建二进制并运行新探针的只读审阅，没有修改生产源码或组件分支。受审根：float `bb9d271`，Isla `b0138b7`，模型 `18389a89`；memory `1731207`，Isla `47ac90c`，模型 `1fa93117`。manifest中的IR分别为aea104c8…、7c626989…，实际hash一致；根/子模块工作树在审阅前后均干净。[精确版本](versions.json)。

“支持”分成三项：能执行代表性模型语义；JSON能忠实描述该执行；生成集合能说明目标域内哪些控制流已覆盖/未覆盖。前两项的部分测试通过，不自动推出第三项。

## P1：memory的IR没有包含当前模型分支的两项修复

来源不是泛泛的“没有生成证明”，而是已找到明确语义差异。

当前模型`model/extensions/V/vext_utils_insts.sail:108-110`增加`valid_segment_group_without_overflow`，要求`reg + nf * 2^max(EMUL_pow,0) <= 32`，并由illegal_load调用。实际IR `isla/rv64d.ir:61514`的illegal_load仍只检查旧valid_segment，没有寄存器组越界检查。

新探针：固定M态、mstatus VS启用、vtype=e8/m1、vl=1、vstart=0、rs1=0x80000000；编码`0x22008f87`即`vlseg2e8.v v31, (x1)`。生成退出0，JSON为`Retire_Success`并发出2次读。当前模型中31+2>32，应为Illegal_Instruction。该输入不能作为当前源码的成功路径见证。

第二项：当前模型同文件314行`get_start_element() -> nat = unsigned(vstart)`采用越界vstart不陷阱策略；IR62041行仍返回result，62043起比较旧上界并返回Err。固定`vle8.v v1,(x1)`，vstart=0产生Retire_Success与1次读；改成0xffffffffffffffff，生成退出仍0，却输出Illegal_Instruction。按当前源模型这应为不执行活动元素的非陷阱路径。

证据：[寄存器组越界](probes/memory-vd31-nf2/result.json)、[越界vstart](probes/memory-vstart-oob/result.json)、[vstart零对照](probes/memory-vstart-zero/result.json)。JSON和命令均在相邻output/run.log中。

建议优先从1fa93117及固定Sail/插件/config重新生成memory IR，再用上述两探针做红绿复验；同步关联源码位置的workaround。仅更新父gitlink不会把新源码编译进现有IR。本问题阻止“JSON对应当前memory模型”的验收，但不否认数组内存模型自身的正确测试结果。

## P2：float的FLI汇编文本与机器编码不是同一条指令

源码`model/extensions/FD/zfa_insts.sail:70`使用`fli_constant_mnemonic`，749行起给出真实常量文本；索引16应为1.0。运行IR在344580附近仍调用`hex_bits_5_forwards`，将索引当作文本常量输出。

实际生成32条FLI_S。LLVM拒绝这些十六进制整数形式；GNU逐条接受6条、拒绝26条，接受的6条重新汇编后全部与JSON机器码不一致。例如：

```text
JSON test-ins:         fli.s f0, 0x10
JSON test-ins-encdec:   f0180053   # 索引16，对应1.0
GNU重新汇编:           f01c8053   # 索引25，对应16.0
```

证据：[逐条对照](fli-text-vs-encoding.json)、[LLVM原始错误](fli-llvm.log)、[生成JSON](probes/float-FLI_S/output/rv64_zFLI_S.json)。这证明float同样存在源码修复未进入运行IR的实例。

根仓pipeline实际按test-ins-encdec生成`.4byte`，能绕过该文本错误；因此不将其扩大为“所有现有机器码重放失败”。但JSON作为文本与机器码应自洽，其他直接汇编test-ins的消费者会失败或静默换指令。建议统一重生当前模型IR并做文本→汇编→编码往返检查，不能仅复验数值helper。

## P2：两个分支的JSON都不声明控制流裁剪范围

MRET实测：float与memory各自不加采样配置时均4条，含Illegal_Instruction/Retire_Success；指定`max_forks_per_branch=0, on_limit_reached=concretize`后各1条，仅Retire_Success。四次退出均0。采样是用户显式配置的合法策略，本身不是错误；问题是产物没有记录自己只代表采样子集。

float JSON有path-signature，但没有sampled/truncated/预算/未完成终态统计；memory JSON连内部排序使用的path_signature也未导出。memory的skip字段只在编码guard拒绝时出现，不能代表其余丢失原因。比较证据见`probes/*-MRET-{unlimited,sampled}/result.json`与[采样配置](sampled.toml)。

因此仅从gen非空、条数、甚至退出0都不能确认模型路径覆盖完成。可选itrace/btrace可以用于覆盖核对，但当前JSON并没有自动关联完整源码分母与未完成结果。建议复用已有trace/branch-sites，不另建执行框架：把IR/配置hash、目标clause/源码分支范围、路径签名、采样/配额/超时/错误/编码过滤计数写入sidecar或JSON摘要。被裁剪或未完成时应明确标为partial。

另外，默认float的官方77名单仍有FS=VS=Dirty偏好（exec.rs:818起），会在可满足时选择该状态；它不覆盖显式相冲突的TOML，但不是全初态域枚举。vector workaround也明确有fork/region预算及输出配额。设计上应给出受测域，不能以任意代表值覆盖所有数据语义条件。

## P2：memory终值查询超时可进入gen，缺少机器可读的不完整标记

静态确认：`src/isarch/exec.rs:1605-1635`遇终值SMT超时时，保留ret_val，将指令/编码、初态与访存数组置空，设置仅存在于内部CollectedCase的materialization_timed_out。1003-1007的finalize_cases特意保留该条。最终AssemGenJsonItem不序列化这个标记，也不把该超时记入first_error，只记计数和日志。

这类条目只能说明“曾到达一个终态”，不能作为可执行JSON见证，尤其不能据此确认没有访存或访存内容为空。默认pipeline会按空指令/编码过滤，仍有无声少覆盖风险。本轮没有动态强制触发此时间盒；结论依据当前明确分支和序列化结构，不把它算作动态失败。

建议保留诊断信息但明确`status=incomplete`及原因，与可重放gen分开统计；计入批次partial。用户选择是否把partial变成退出非零，但覆盖验收不得把它算作正常见证。

## 覆盖域建议：SC失败分支目前被常用配置具体化掉

memory的difftest PMA配置`const_primops.match_reservation="true"`。同一固定`sc.d x3,x2,(x1)`，默认配置只生成1条带写事件的成功提交路径；仅将该配置改成`undefined : %bool`的测试副本后，生成2条：无写事件的reservation失败路径，以及有写事件的成功路径，均Retire_Success。

证据：[默认](probes/memory-sc-default/result.json)、[符号reservation](probes/memory-sc-symbolic/result.json)、[完整测试配置](memory-reservation-symbolic.toml)。这是明确的测试域选择，不是数组写回实现的错误；若目标包括LL/SC控制流，则应有成功/失败两档配置或批次，不能把当前默认JSON当作两档都覆盖。

## 本轮确认具备的专项能力

float：从实际根仓子模块源码构建。独立SoftFloat预期fixture在五份IR上helper合计1615/1615；FPR/FS/fcsr状态检查180/180；隔离Ext_F guard20/20，装配冲突检查通过，脚本22项退出均0。不是对所有输入/所有指令/当前Sail源码的等价证明。默认JSON新探针FLEQ_S16、FLI_S32、VFMVFS12、C_ADDI1退出0；FLEQ_S的输出包含fcsr NV置位/不置位两类。指令、完整前态/后态、编码及具体ret_val使用同一最终模型是正面能力。

memory：数组模型30/30测试通过，涵盖同址读写、重叠访问和判死区域等。新固定JSON探针ld/sd、c.ld、amoadd.d均退出0且可观察到正确事件；sd后内存等于写数据，ld的pre/post一致；AMO先读后写，示例0+1写回1；c.ld实际续执行到读事件。这证明有实际内存符号化能力，不是每次读都独立取fresh值。它不代表并发内存模型、多指令序列或所有PMA/PMP/fault域都已覆盖。

float C_ADDI虽然ret_val已具体化，仍返回ExecuteAs；本轮没有新增续执行逻辑，其后态只到首次zexecute终态。它不属于77个非访存浮点clause的退休证据，不能拿来声称完整压缩指令执行覆盖。memory则已经实现ExecuteAs续执行。

## 控制流分母不能由样例数代替

浮点模型使用纯helper和条件选择表达部分数值/flags语义，SMT表达式中的ITE可以同时表示多个条件域，但生成一个最终Model只给出其中一个取值；它们未必对应不同Isla fork。反之，不同路径也可能生成相同机器编码。因而JSON条数、不同编码数、helper调用数和源码分支覆盖是不同指标。需要结合实际编译模型的branch-sites/trace与数据语义条件，规定每一类目标如何由JSON见证；不能用“1615样例”或“77个clause各一条”替代该分母。该项为覆盖设计建议，不将表达式合并本身判成数值错误。

## 资源与未完成边界

新增FVFTYPE无定向限制探针使用单线程、内部路径预算30秒、外部45秒，最终外限124且没有最终JSON。该结果说明这次有限预算运行没有可用产物，不证明无限时间也不可解，也不作为与旧版本的性能回归对照。未运行全部77浮点clause、全向量访存与异常组合、硬件重放或完整源码分支覆盖。

本轮所有探针的根版本/IR/配置/二进制hash、命令/退出/JSON摘要见[all-probe-summary.json](all-probe-summary.json)及各probe的result.json。浮点完整脚本检查见[checks.json](float-numeric/checks.json)，数组测试见[memory-array-tests.log](memory-array-tests.log)。生成的临时wrapped IR已记录hash后删除，可由相同原IR/TSV/wrap.py重新生成；未删除源IR/输入/原工作区产物。

## 建议顺序

1. **先补源码→IR一致性**：memory将两个模型修复真正编入IR；float将FLI等已修改映射与当前模型同步，并固定工具链/配置/来源。重跑这里的明确负例。
2. **再补JSON结果合同**：标出完整/采样/未完成，关联trace与源码分支；修正FLI文本编码往返。不要混淆“到达终态”和“生成可重放见证”。
3. **按目标列控制流与数据语义分母**：浮点覆盖格式/舍入/NaN/Inf/zero/subnormal/flags和向量mask/vl/vstart；memory覆盖访问种类/宽度/对齐/跨界/PMA/PMP/fault/SC成功失败。只把真实可行且目标要求的条件列为分母；不要求枚举无穷初态。
4. **逐条绑定JSON和重放证据**：优先已发现的两memory反例、浮点FLI、AMO和SC两档，再扩大；只有对应最终模型、配置和受测版本一致时才记PASS。

据此，float可以评价为“数值执行与定向见证生成已较成熟，完整控制流覆盖未签收”；memory可以评价为“数组内存、事件与压缩访存续执行已有较好基础，但当前根版本IR落后于所固定模型，须先修这项语义错配”。不建议因为这些发现回退所有已合代码，也不建议把两套版本当前直接标成目标全部达成。
