# flags／饱和显式分支超时定位

## 结论

不是“一个 SMT 查询一直卡两小时”的统一问题，也不能统称路径爆炸。新官方 Z3、QFFP 下，实际调用观测把两项区分开：

- flags：恢复 `if changed` 后，新增的 flags 条件约束使后续求解明显变贵。前300秒仅完成255次查询，累计297.44秒，单次最长22.27秒；ITE版本完成6748次查询，累计44.16秒。主要观测为许多慢查询的成本累积，不是查询数量已超过ITE版本。
- f16→i16饱和：既增加分叉，又增加每次查询成本。旧IR在vl=1时仍先计算物理8个lane，再用mask选择结果，因此不活动的7个lane也在溢出条件上分叉。连续八次真实overflow fork已从执行器日志确认；ITE版本没有这些fork。前300秒已完成1668次查询，累计292.05秒，最长1.55秒；ITE版本1993次查询累计3.24秒完成。

这里的“求解变贵”不等于 Z3 算错；没有发现 SAT/UNSAT 错误的证据。300秒是本轮插桩诊断采样窗，正式Clause与SMT预算仍为7200秒。旧六次7200秒超时记录没有改动，也不因诊断采样替换。

## 控制条件与可信度

固定旧84次实验的冻结isarch（SHA `c9c5bb8b32289006b1af621f71f03537aecf4a1b0b9ed9b51bc68e573785e2f2`）、官方Z3 `1fd1d3613`、IR/config、QFFP、单线程及seed17。实验专用 LD_PRELOAD 仅包裹 `Z3_solver_check` 和 `Z3_solver_check_assumptions` 记录进入/退出。四臂命令、哈希和CPU见[启动记录](launch.json)，固定300秒原始统计见[首轮结果](first-300s.json)。没有改模型或生产默认配置。

| 项目 | 完成check次数 | check累计秒 | 最长已完成check秒 | JSON |
| --- | ---: | ---: | ---: | --- |
| flags A（ITE） | 6748 | 44.16 | 0.029 | finished，208条 |
| flags B（if） | 255 | 297.44 | 22.27 | 300秒未完 |
| sat A（ITE） | 1993 | 3.24 | 0.009 | finished，18条 |
| sat B（if） | 1668 | 292.05 | 1.55 | 300秒未完 |

check次数包含分支检查、具体化及终态求解，不能当fork数。没有逐路径完成事件接口，未将没有最终JSON误称为没有完成路径。

另开B原样长观测，启用已有 `-D f` 记录真实fork位置，最多7200秒；[后台启动](dump-launch.json)。fork日志会计算taint，改变额外开销，故该轮只用于定性定位及计数，不能把它与表中未开fork日志的耗时混算。A带同样fork日志的对照见[a-forks-launch.json](a-forks-launch.json)。

## flags 源码与条件

旧B仅把 `mstatus.bits = ite(changed, dirty.bits, mstatus.bits)` 改为 `if changed then mstatus.bits = dirty.bits`。`changed = old != (old | flags)`。真实fork日志指向 `extensions/FD/fdext_regs.sail 550:4-550:45`。函数是单次状态更新，没有由这一行引入循环。新条件涉及被执行指令产生的异常flags；本次首先走到包含浮点除法结果及其异常推导的约束，打印表达式可见 `fp.div`、`fp.abs`、`fp.leq` 和 `fp.lt`。额外约束不只影响该分支的两次SAT检查，还留在之后每次具体化/终态求解的上下文。

因此目前正确表述是：显式flags分支引入昂贵的浮点异常条件，单次与累计SMT成本显著上升。不能说新增成千上万分支已经被证实，也不能把22秒说成单次2小时。

## sat 的结构性原因

输入 `vtype=0x8`、`vl=1`、`vstart=0`，VLEN128／SEW16对应 `num_elem=8`。旧 `VFUNARY0` 实际IR顺序是：

1. 对i=0..7调用 `riscv_f16ToI16_pure`（IR行314091、另一RTZ调用314386）。
2. helper的 `jump overflow` 在IR行71536附近，源坐标 `vext_fp_utils_insts.sail:544`。
3. 计算以后才用mask选择值与flags，IR行314440附近 `ite(mask[i], lane_flags, 0)`。

所以vl=1没有阻止其余7lane的helper先运行。带fork日志记录连续8次该helper溢出分支，而且后续组合继续重复；这是实际fork，不是JSON条数。独立8个布尔条件理论上最多256种组合，当前日志只证明已观察到的分叉，不将256冒充完整跑出的路径数。

优先修正顺序：让显式mask分支支配lane运算，只在活动lane上做转换，再评估活动lane的overflow显式分支。它保留真实控制流，同时避免为不参与指令效果的lane组合求解。仅将helper恢复if、但保留eager旧循环，会把无关lane也展开。

## dump与重放限制

第一次使用 `Z3_solver_to_string`，加上本次全部临时assumptions，保存query文本。但带tactic solver已被预处理，文本包含模型转换器或内部临时声明；独立重放出现解析错误。第二次尝试 `Z3_benchmark_to_smtlib_string` 导出 `get_assertions`＋assumptions，同样发现内部声明不完整。两组日志即使最后打印sat也退出1，**全部重放结果无效，不拿耗时或sat作证据**。

这不影响对真实C API check进入/退出的计时证据。若继续需要独立重放，必须在 `Z3_solver_assert` 入口保存原始约束并管理引用，或用Isla原生checkpoint导出，不能把已预处理solver的文本当作可靠SMT-LIB。当前不为了dump改生产程序。

## 追加诊断

[sat-B-inactive-zero/command.json](sat-B-inactive-zero/command.json)保留旧B IR，只把每个向量寄存器高112位（不活动7lane）固定0、低16位保持符号化，判断不活动lane组合对超时的贡献。它改变输入域，只是诊断对照，不属于原84次消融或正式预算验收。

### 不活动lane固定0的控制结果（已完成）

保留旧B IR、相同seed17/QFFP/vl1/SEW16，仅对全部32个向量寄存器将高112bit固定0、低16bit保持符号化，完整自然生成22条JSON，summary=finished，errors/timeout/unfinished均0。真实overflow fork降为4次（跨原有指令/掩码路径），不再每条路径连续8个独立lane分叉。共2667次check，累计256.686秒，最长0.947秒。

启动器没有记录精确进程墙钟或wait返回码，因此不伪造exit0或精确wall；配置写入（紧邻launch前）到最终JSON写入约288.24秒，首末check窗口273.761秒，都与300秒采样内自然完成一致。完整结果与时间口径见[sat-B-inactive-zero/result.json](sat-B-inactive-zero/result.json)。

这个控制只去掉不活动lane的数值自由度，活动lane仍符号化，支持不活动lane组合是重要成本来源的因果方向。它缩小输入域，且启用fork日志，不能将其与广域B计算纯加速比；每次SMT仍明显比ITE慢，问题没有凭固定输入就完全修好。正式处理应修循环控制流以跳过不活动lane，不应生产默认固定这些值。
