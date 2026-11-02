# flags 算术和饱和转换的路径数量级

## 口径

这里的“主路径”是 `zexecute` 的 `MultiRuntime` 任务：每次 `MultiForkSink::submit` 增加一条任务，任务运行及收集器返回后才算完成。收集器会独立调用编码映射执行器，其 `SingleForkSink` 分叉记为“辅助路径”。JSON `gen` 是编码与求解后写出的用例数；一条主路径可以写出多条用例。三者不能互换。

对照使用正式消融冻结的 A/B IR 和配置、官方 Z3 `1fd1d3613`、种子 17、`qffp`、单线程。实验执行器来自 `isla` 的 `09ffa91` 源码快照，仅在快照内加入路径事件；生产源码和输入未变。源码与二进制不主张与正式 `c9c5…` 二进制逐字节相同，但原始换库清单记录冻结时基于 `80231ce`，只有 tactic、opts 等文件为未提交修改；`09ffa91` 提交这些修改，相关 `exec.rs`、`executor.rs` 与冻结期同版。A 两项均自然退出 0、summary=finished。

## 主执行树的结构上界

| Clause | 完整 A 主路径 | B 新分支可影响的 A 路径 | B 主路径结构上界 | 可编码终态用例结构上界 |
| --- | ---: | ---: | ---: | ---: |
| `F_BIN_RM_TYPE_S` | 172 = 160 Retire + 12 Illegal | 160 Retire，各至多二分一次 | `12 + 160×2 = 332`（约 `10²`） | `48 + 160×2 = 368` |
| `VFUNARY0` | 13 = 12 Retire + 1 Illegal | 4 Retire，各至多八次二分 | `9 + 4×2⁸ = 1033`（约 `10³`） | `14 + 4×2⁸ = 1038` |

主路径 A 的总数由实验版 `initial_task + fork_child = run_return = task_done` 核实：flags 为 `1+171=172`，sat 为 `1+12=13`，全部 `Run::Finished`；[A 运行账](final-a-result.json)与 `final-flags-arithmetic-A/run.log`、`final-sat-A/run.log`。增强插桩加 `-D r` 的完整 A 再核返回类别：flags 为 160 Retire、12 Illegal，sat 为 12 Retire、1 Illegal，见 `aux-flags-arithmetic-A/run.log` 与 `aux-sat-A/run.log`。A 已完整穷尽；以上 B 上界是假设与 A 相同输入和其他控制逻辑，仅对恢复的分支放宽两个方向。它是固定配置下的控制流结构界，不声称全部组合可达。

flags 的 IR 差异仅为 `zaccrue_fflags`，在 `F_BIN_RM_TYPE_S` 成功算术后只调用一次。Sail `fext_insts.sail` 先选舍入模式；动态舍入模式非法时直接返回 Illegal，尚未计算四个操作、也未调用 `accrue_fflags`。因此 12 条主 Illegal 路径不受 `changed` 影响，160 条 Retire 各最多加一个二分点。A 生成的 208 个用例中 48 个 Illegal 是辅助编码把仍符号化的四种操作逐一枚举，不能把这 48 个都算作独立主路径。A 160 个 Retire 用例各操作 40 个；静态五种舍入模式每种四个基础状态，动态模式有五种合法 FCSR 舍入值与三种非法值，每种亦有四个基础状态，所以每操作 `5×4 + (5+3)×4 = 52` 个编码用例。

sat 的输入固定 `vtype=0x8`、`vl=1`、`vstart=0`、VLEN=128。`vtype` 给出 SEW16、LMUL1，`get_num_elem` 因而是 8。冻结 B IR 中 `VFUNARY0` 的 SYMBOLIC 循环对八个物理 lane 逐个执行 `riscv_f16ToI16_pure`，随后才用 mask 选择；因此 `vl=1` 仍可经过八个 overflow 判定。六个 `vfunary0` 操作中仅 `FV_CVT_X_F` 与 `FV_CVT_RTZ_X_F` 两臂调用该 helper；各有两条 A Retire 主路径，合计 4 条受影响。其他 8 条 Retire 和 1 条在操作匹配前返回的 Illegal 不受影响。八个 lane 是同一向量寄存器中独立的 16 位片段，固定合法寄存器索引与活动配置后可逐 lane 选择范围内或溢出值，故单个转换操作的 `2⁸=256` 是有构造性可达依据的局部控制序列；全 Clause 的 1033 是上界，仍须完整执行验证每个组合。

sat A 生成 18 个用例，六个操作各有两个 Retire、一个 Illegal。唯一的主 Illegal 路径在操作匹配前返回，辅助编码把六个仍符号化的操作枚举为六个用例；故 B 的可编码类上界比主树多 5。flags 同理多 `48−12=36`。这些“可编码类”不是执行器主路径，也不是已完成路径数。

## 辅助执行树与全系统上界

`encoding_paths` 在每条主路径进入收集器后调用 `zencdec_forwards`，必要时再调用 `zencdec_compressed_forwards`。这些映射通过 `start_single_with_timeout` 执行，有自己的初始任务、fork 和终态。增强插桩完整 A 实测：flags 辅助初始任务 1068、辅助 fork 244、辅助终态 1312，守恒 `1068+244=1312`；主 fork 171，合计 415，与旧 `-D f` 的 415 个位置日志一致。sat 辅助初始任务 347、辅助 fork 31、辅助终态 378，守恒 `347+31=378`；主 fork 12，合计 43，与旧 `-D f` 的 43 个位置日志一致。辅助初始任务还包括启动期求值，不能一律算成一条 Clause 的后继路径。

逐条主路径分组还能给出**多个执行树的累计任务上界**。两项 A 的启动阶段都先完成 272 条辅助任务，不属于某一条主路径。flags 的每条 Retire 主路径随后执行 4 条辅助初始任务、产生 1 个辅助 fork，共 5 条辅助终态；每条 Illegal 主路径执行 13 条辅助初始任务、产生 7 个辅助 fork，共 20 条辅助终态。sat 的每条 Retire 主路径是 `5+2=7` 条辅助终态，每条 Illegal 是 `15+7=22` 条。原始逐路径事件见 `aux-flags-arithmetic-A/run.log` 与 `aux-sat-A/run.log`；分组核账见 [aux-audit.json](aux-audit.json)。

这些 A 的辅助任务数不能直接推广为 B 的严格上界：收集器会对每个编码调用最终求解、将指令与寄存器取具体值，并根据所得编码调用汇编映射。B 的新增约束虽然缩小主路径的可行域，却可能改变具体化结果及后续辅助函数调用次数。若机械套用 A 的逐类数量，得到 flags 2444、sat 8551 条累计任务终态；这只是**固定辅助调用形状的条件性估算**，不是已证明的全系统路径上界，不用于解释两小时超时。可靠的固定配置主 Clause 控制流界是前述 332／1033；辅助树另报实测 fork 和终态，避免与主路径相加成一棵树。

两小时实测将给出主树在途/完成数。原旧 B 的 `-D f` 位置数 flags 655、sat 1038 混合主、辅助 fork；由于当时没有逐树任务事件，不能由它们推出完成路径数。增强短 B 对照将补充两类 fork 的实际比例。
