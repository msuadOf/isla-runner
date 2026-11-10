# FLOAT-01 浮点向量抽样与编码域调查（2026-09-29）

## 范围与判定

本轮以 `isla/src/isarch/official_float77.txt` 的 77 个 RV64 非访存目标为分母：51 个标量、26 个向量。十个浮点访存目标和 RV32 限定编码不在本轮求解域内。`make solve` 默认排除浮点；下面的预检直接调用与 `solve-%` 相同的 `isarch solve-state --clause`，输出隔离在工作区 `.tmp/float-vector-sampling/`，没有覆盖现有 `isla/output/`。

验收必须同时具备：进程正常退出、最终 JSON 的终态账本无执行或物化错误、至少一个可编码 Retire 见证，以及成功见证对源码有效分支的覆盖核账。`summary.complete` 只说明本次执行账本的完整性；含抽样的运行仍标 `false`，不得改写为源码分支闭合。未生成最终 JSON 的超时只计诊断。

## 源码与理论路径规模

模型采用 VLEN=128、ELEN=64。若循环每个 lane 有一处独立且可满足的二路 `if`，不限制时，上界为 `2^n`：普通 SEW16、LMUL8 的 `n=64`，即 `2^64`；SEW32、LMUL8 的 `n=32`，即 `2^32`；SEW64、LMUL8 的 `n=16`，即 `2^16`。宽化结果 EMUL≤8 时，源 SEW16、LMUL4 仍有 `n=32`。这些是**条件上界**，不能直接当作本 IR 的实际路径数：大多数 SYMBOLIC 算术/FMA/BF16 lane 已改成 ITE 和一次 flags 累计，未在每个 lane fork；仍有 `FVFTYPE` slide、部分转换/估算等保留条件循环。

既有 73df 全编码入口两小时诊断的 6828 个实际 fork 中，2544 个来自先于固定 opcode 判定的全模型反向译码，1449 个来自 LMUL 判断，1305 个来自 `FVFTYPE` guard；该入口的主要成本不是单次 `2^32` lane 查询，详见[路径诊断](path-explosion-diagnosis-20260928.md)。本轮**直接 `zexecute`** 的 60 秒样本改用新 IR；`FVFTYPE` 将路径 fork 上限压到 5 后仍在 `get_start_element` 一条路径上累计 175 次 SMT 检查、活跃 55.6 秒，最慢单次 0.9 秒，因而单纯限制循环 fork 不能解决状态/合法性路径成本。

## 已实施的先决修复

- Sail `vext_fp_utils_insts.sail` 的普通 FP guard 现在拒绝 SEW=8，保留允许 INT8 的宽窄转换通用检查；普通 widening 算术使用新的局部 guard 拒绝 SEW=8。BF16 四个 clause 的两个后端都在断言前检查 SEW=16。这使直接 `execute` 对没有物理编码的宽度返回 Illegal，而不是触发 Sail 断言；原有合法编码入口不变。
- Isla 只对官方 77 个浮点 clause 的**终态见证**先做 FS/VS=Dirty 可满足性检查，可满足才选此见证；要求 FS/VS 关闭的执行路径保持原约束。非法执行路径的具体初态若无法编码，终态记 `non-encodable` 且不生成机器码；成功执行路径无法编码仍作为物化错误。零个可用输出不能凭 `non-encodable` 记完整。
- 这些修复没有固定执行前输入域，也没有把被抽样路径宣称为完整覆盖。Isla 原有 16 种 FS/VS 约束物化测试和本轮不相容路径测试均通过。

## 版本与验证

第二版实验 IR 为 `e893e1277f7eb529972b8903d3445fd7f1d2b37ab8024112841c804dd922f4d9`，在 `sail-riscv@4f2ac293` 加未提交模型修改上用 Sail 0.20.1、插件 `c4eccb06…22f6`、RV64/V128/E64 配置 `89923ebf…625` 生成。现工作树 163 个 `.sail` 文件 SHA-256 清单位于 `.tmp/float-vector-sampling/source-manifest.json`（清单哈希 `0308003b…6eb15`）；本轮动过的四个 Sail 文件 SHA-256 分别为 `3bfca870…f1bd0`、`bdc27ae0…e4b6cb`、`423cdaef…29b6`、`d60ea577…91d5`。运行器为 `isla@31523ab` 加未提交修改的 release/ITRACE/smt-thread-interrupt 构建，SHA-256 `196809a4ccab23223e84d3645d3cd24d7eb0aab32e98702b31f63b47e52a81c8`；`exec.rs` SHA-256 `0b600118…60`，FD TOML 为 `20851fdb…723d0`。实验执行外限 60 秒、单路径 55 秒、单次 SMT 1 分钟、`-T 2`、`qfaufbv`。`sail` SYMBOLIC 和普通后端严格检查均退出 0；`isarch::exec::tests` 23/23，单独 FS/VS 16 组合 collector 测试通过；Rust `cargo fmt --all` 与两个子仓 `git diff --check` 通过。

| 目标/实验 | 结果 | 可以支持的结论 |
| --- | --- | --- |
| `VFMVFS`，第二版 IR，全局每分支 fork≤1 | 退出 0；8 终态＝3 Retire＋3 Illegal＋2 `non-encodable`，6 个 `gen`，`complete=true`，无抽样终态 | 普通移动的 SEW16/32/64 有可编码成功见证；不等于 26 向量或全部数据语义通过。 |
| `VFMVSF`，第二版 IR，同一配置 | 退出 0；20 终态＝12 Retire＋6 Illegal＋2 `non-encodable`，18 个 `gen`，`complete=true`，无抽样终态 | 首元素写入路径有 VL=0、1、2、16 等见证；尚需数值和完整状态复核。 |
| `FLI_S`，第一版 IR，同一终态见证修复 | 退出 0；32/32 Retire，`complete=true` | 标量编码见证未被新逻辑整体破坏；版本与第二版向量 IR 分列。 |
| `VFNCVTBF16_F_F_W`，第二版 IR，每路径 fork≤5 | 退出 1；15 终态＝4 Illegal＋11 无编码、0 Retire；2 条终态发生抽样，`complete=false` | 旧 SEW≠16 断言消失；此预算没有覆盖成功 lane。 |
| `FWVVTYPE`，第二版 IR，每路径 fork≤5 | 退出 1；14 终态＝7 Illegal＋7 无编码、0 Retire；2 条终态发生抽样，`complete=false` | widening SEW=8 断言未出现；此预算没有覆盖成功运算。 |
| `FVFTYPE`，第二版 IR，`vtype`/寄存器组/`vstart` 局部区域采样，随后追加 slide 循环区域 | 两次均 60 秒外限 124，无最终 JSON | 前导限制和 lane 限制均未使整目标收束。 |

第一版 IR `f643e111…508c5` 上的 BF16 每路径 fork≤5 曾暴露 `zvfbfmin_insts.sail:32` 断言；第二版不再出现。两版不能合并记为同一批 PASS。其它五个第一版代表目标仅有外限前缀日志，均不计完成。

第二版 IR 的 26 项矩阵采用同一 `max_forks_per_branch=1` 配置、8 路并行，每项 `-T 2`、60 秒外限且未开 ITRACE；完整逐项目标退出码、用时、版本哈希和有无最终 JSON 在 `.tmp/float-vector-sampling/matrix/summary.json`。结果为 **2 项退出 0 且有完整 JSON**（上表 `VFMVFS`、`VFMVSF`）、**24 项外限 124 且无最终 JSON**、0 项其它退出。外限前日志不能计算完成路径总量；这也不是正式 60 分钟预算的失败结论。局部采样试验与该完整域矩阵分列。

另做了一个未保留的 `get_start_element` 等价表达式试验：旧上界 `2^(3+vlen_exp−SEW_pow)` 对 Sail 允许的 14 个 VLEN 指数与 4 个 SEW 指数，逐项等于按 SEW3/4/5/6 选择的 `vlen`、`vlen/2`、`vlen/4`、`vlen/8`（56/56）。第三版实验 IR `68cdec3f…1e4b` 通过双后端严格检查；同样的 `FVFTYPE` 每路径 fork≤5、60/55 秒、T2、`qfaufbv` 对照仍外限124／无JSON。旧／新超时路径分别完成175／173次SMT检查，55.6／55.1秒活跃时间，均停在 `get_start_element`；这不足以支持性能收益，已从 Sail 工作树撤回此表达式改动。第三版 IR 只保留为失败对照，不进入下表完成数或当前源码版本。

BF16 另做未采用的 seed 试验：全局每路径 fork=0、终态可重现抽样、10秒外限，在64个 seed 中0条 Retire（48无编码、16 Illegal）。仅给 `zvfbfmin_insts.sail:28–30` 的非法 guard 加合法侧偏置后，同64个 seed 中 seed34 得到1条可编码 Retire，`vl=4`、`vstart=0`、SEW16，余63个仍为15 Illegal＋48无编码。该单条终态 `sampled=true`、`complete=false`，改成每路径 fork≤2 后又只得到1 Illegal＋3无编码；它证明局部方向偏置能到达活动 lane，**不证明抽样稳定、双侧覆盖或整 clause 跑通**。原始逐seed账本在工作区 `.tmp/float-vector-sampling/{seed-probe,seed-probe-bias}/summary.json`，没有接入生产 workaround。

为防止 guard 修复只消除断言而破坏合法指令，另从已有 E 阶段独立 runner 源在 `.tmp/float-vector-sampling/e-runner/` 构建当前 `isla-lib` 版本，输入为真实 32 位机器字与独立预期。使用**同一第二版 IR**、RV64 E 配置 `8247c8d…0ab2b` 复跑 BF16 三包（15＋10＋3）、普通向量 smoke（4）、向量基础／状态／扩展／RM 四包（22＋49＋227＋564），共 **894/894 条记录**（不同包可有重复输入）；八个进程均退出0，逐行 `structural_ok=true` 且 `difference_unsat=true`。runner SHA-256 `518232d7…5332e49`，逐包输入/输出哈希和计数见工作区 `.tmp/float-vector-sampling/e-runner/summary.json`。这是列定具体输入的编码、阶段和观察状态等价，不是未知输入求解完成或所有源码 branch 证明。

## 生成物与分支覆盖边界

第二版 IR 的两项成功目标已分别以 ITRACE 复跑：`VFMVFS` 的 JSON/trace 都有 8 个终态、6 个 `gen`；`VFMVSF` 都有 20 个终态、18 个 `gen`。按 clause 源码行区间聚合可编码 `gen` 的分支边，前者 7 个已观察分支位点中 4 个双向、3 个单向，后者 8 个中 5 个双向、3 个单向。各自 3 个单向位点是固定 clause 分派和成功路径断言，不能直接当作遗漏的有效 if/else。审计脚本、逐位点明细与原始 JSON/trace 位于 `.tmp/float-vector-sampling/VFMVFS-ir2-trace/` 和 `VFMVSF-ir2-trace/`。这仅核对已观察执行边，不能证明静态分母无遗漏，也不能推断所有源寄存器值、特殊浮点值和完整状态已覆盖。其余 24 个向量目标没有最终 JSON。

历史 56cc 的 57 个完成目标已有审计指出：BF16 两条向量 Retire 全是 `vl=0`，标量操作数值域很窄；这些问题不会因本轮进程退出或局部 fork 采样而自动消失，见[分支覆盖汇总](branch-coverage/SUMMARY.md)。需要按 clause、enum、合法 SEW、guard 正反、活动/屏蔽 lane 和源码分支边建立见证矩阵，再将源代码中配置上不可达的分支单列证明。当前 **26 个向量目标没有完成这项验收**，正式 77 项签收数不因此上调。

## 已有完整批次与长时卡点复核（2026-09-29，只读）

确实跑过所有 77 项的完整**启动与退出账本**，但从未有 77 份均完整结束的 JSON：d012 IR 的 90/80/15 秒批为 40 自然退出、36 外限、1 SMT 失败；1dcc IR 的 300/270/30 秒批为 50 自然退出、27 外限。56cc 的 1800 秒首批因并发资源压力中止，后续跨多个独立 stage 去重为 57/77 自然完成、剩 20 个向量；57 不是同一批全 77 完成。各自版本与命令见[全批审计](solve-audit-batch.md)和[官方批记录](solve-fix-official.md)。

对这 20 个旧版未完成目标，同一 73df 候选的 19 个目标各按完整符号输入、ITRACE、1800/1740/30 秒跑满外限；`FVFTYPE` 独立按 7200/7140/30 秒跑满。**20/20 均无最终 JSON**，没有新增可签收目标；[19 项退出表](../../isla/target/float-solve-evidence/num-elem-order-rm-eq-candidate-20260928/target19-exit-summary.json)、[20 项汇总](../../isla/target/float-solve-evidence/num-elem-order-rm-eq-candidate-20260928/target20-exit-summary.json)和[FVFTYPE 两小时审计](path-explosion-diagnosis-20260928.md)记录版本及外限。19 项超时前共打印 32,522 个局部终态：31,805 Illegal、639 Retire、78 无编码；这些不是完整路径集合。

本轮只读流扫了上述 19 份原日志（不重跑），共计 58,845 个实际 `FORK`。四个已在 73df IR 定位为反向译码的无源码位点合计 12,866 次（21.9%）；浮点变量宽度 guard 两个位点合计 9,542 次（16.2%）；`valid_reg_group` 的 LMUL 正负判断 3,917 次（6.7%），`get_start_element` 上界 2,334 次（4.0%）。按冻结 Sail 源中五个 FP clause 文件的 SYMBOLIC `foreach` 行区间匹配，仅 12 个 fork 直接落在这些区间；辅助函数及无源码位置的 fork 未包含在这 12 个内，故不能据此说 lane 没有成本。[逐项与聚合账本](../../.tmp/float-vector-sampling/full19-hotspots.json)保留脚本结果。19 项的领先热点以 guard、LMUL/寄存器组和译码为主，不能直接归因为每个 FP lane 的 `2^32` 展开。

单独的 `FVFTYPE` 两小时 v2 配对审计更精确：6,828 个 fork 中，反向译码 2,544、LMUL 判断 1,449、execute 非法 guard 1,305、vstart 上界 356、num_elem 合法集合至少 330；slide 循环区域只有 48。95,679 次已完成 SAT 检查累计 14,094.107 秒双 worker FFI，单次最大 CheckSat 4.398 秒、CheckSatAssuming 3.057 秒，已完成 FFI 占匹配 worker 窗口约 98%；最终仍无 JSON，峰值 RSS 约 7.5 GiB且无资源止损。这证明该**旧 FullEncoded32 入口**的主成本是大量分叉后反复做相对短的 SAT 检查。它不能直接外推到本轮 `e893` 的直接 `zexecute` 入口：后者 26 项只有 60 秒预检，除 `FVFTYPE` 定向日志外，尚无同等时长的逐位点统计。

## 下一步

1. 对 24 项外限目标逐个定局部 region 和采样 seed；成功 Retire、活动 lane 与 if/else 两侧均需来自可编码 JSON。预算只压重复 lane 分支，前导 guard 不盲目定值。
2. 对 `FVFTYPE` 等长路径定位累计 SMT 位点并做等价表达式实验；先以代表目标证明能在单项预算内自然结束，再铺开矩阵。
3. 两项已完成目标仍需物理译码、C++/Isla 回放、完整状态和源码分支静态分母核对；其余目标不能从“无断言”外推可用。
4. 当前正式主 `isla/rv64d.ir` 仍为 d012，实验 IR 与 Sail 源码变化尚未切换主 IR、重绑 79 份 workaround 或跑完整 `make solve-fd-nonmem`。旧 PASS 保留其版本限定。

## 直接入口完整 trace 批次与卡点（2026-09-29）

已在隔离目录 `.tmp/float-full-trace-20260929/` 冻结 `e893e127…4d9` IR、`196809a4…a81c8` isarch、`20851fdb…723d0` FD 配置和运行脚本，运行 `make -f scripts/run.mk -o build-isarch -k -j4 solve-fd-nonmem THREADS=2 ITRACE=1 OUTER_TIMEOUT=300s SOLVE_TIMEOUT=270s SMT_TIMEOUT=30s TASTIC=qfaufbv`。本批**没有启用执行抽样**，77 项均启动且均取得进程退出回执；31 分 0.615 秒结束，make 退出 2（22 项外限）。内存可用量最低约 108.4 GiB，stage 进程 RSS 采样峰值约 6.0 GiB，未触资源止损，结束后无残留 stage 进程。冻结命令与哈希见[便携运行摘要](evidence/float-full-trace-20260929/campaign-summary.json)（SHA-256 `79cf2785…f8a2`），逐项目标的回执／JSON／trace 核账见[最终账本](evidence/float-full-trace-20260929/final-audit.json)（SHA-256 `59cd1509…3690`）；原始日志、trace 和进程回执留在上述 `.tmp/` 目录。

| 范围 | 进程与生成物 | 可支持的结论 |
| --- | --- | --- |
| 51 个标量 | 51/51 正常退出，1344 条 `gen` | 全部 JSON `summary.complete=true`；与旧 73df 标量结果数目相同，但仍需当前 IR 的源码语义分支与数值特例核账。 |
| 26 个向量 | `VFMERGE` 30、`VFMV` 34、`VFMVFS` 6、`VFMVSF` 18 条 `gen`；另 22 项各外限 124、无最终 JSON | 仅四项完成本次符号执行账本；22 项超时 trace 是残缺前缀，不能算完成。 |
| 全 77 项 | 55 项退出 0，22 项外限 124，0 项其它退出；1432 条 `gen` | 77 份日志与 trace、55 份最终 JSON；55 项 JSON 终态数、状态分布、case ID／签名与 trace 一一匹配，核账错误 0。正式源码语义覆盖未签。 |

本轮因外限而**跳过签收**的22项目标按源码族列出，均无最终JSON：基础向量 `FVFMATYPE`、`FVFMTYPE`、`FVFTYPE`、`FVVMATYPE`、`FVVMTYPE`、`FVVTYPE`；宽化向量 `FWFTYPE`、`FWVFMATYPE`、`FWVFTYPE`、`FWVTYPE`、`FWVVMATYPE`、`FWVVTYPE`；归约 `RFVVTYPE`、`RFWVVTYPE`；转换／估算／BF16 `VFNCVTBF16_F_F_W`、`VFNUNARY0`、`VFUNARY0`、`VFUNARY1`、`VFWCVTBF16_F_F_V`、`VFWMACCBF16_VF`、`VFWMACCBF16_VV`、`VFWUNARY0`。这些目标的局部热点已定位，但足以在预算内生成完整 JSON、同时覆盖有效分支的修复方法仍未确认；不把其 Retire 前缀或隔离抽样试验计作完成。浮点访存10项和RV32限定编码仍需其对应入口／内存链路，未纳入本77项运行域。

22 个超时向量目标的残缺日志累计 2635 次实际 fork、1422 个已记录终态前缀（544 Retire、738 Illegal、140 non-encodable），显示求解仍在推进，不能据此推断未结束路径或最终覆盖。逐位点统计见[便携运行摘要](evidence/float-full-trace-20260929/campaign-summary.json)：`get_start_element` 的 `vstart` 合法上界 486 次，`read_vmask` 的 vm 分支 286 次，`read_vreg_extra` 的 LMUL 正负 100 次，寄存器组重叠检查的两个位点合计 158 次。`FVFTYPE` slide 循环 24 次，`VFUNARY1` 估算循环 49 次且 Sail NaN／分类 helper 又多次分叉。**本轮直接 `zexecute` 入口的热点与旧 FullEncoded32 入口的反向译码热点不同。**本轮未开逐次 SMT FFI 耗时诊断，不能把 300 秒精确归给某一个查询；`RFWVVTYPE` 只有 29 次 fork 仍外限，说明仅压逐 lane 分叉不足以保证全目标完成。

SEW32、LMUL8 下若一个可满足的独立二路判断在 32 个 lane 逐次分叉，理论上界是 `2^32`；SEW16、LMUL8 对应 `2^64`。这不是本批各目标实际发生的路径数：许多 SYMBOLIC 算术主体用 ITE 合并 lane 选择，`FVVTYPE` 的 SYMBOLIC 循环没有逐 lane `if`；`FVFTYPE` slide 与 `VFUNARY1` 特殊分支仍有循环条件。不能以理论上界替代上述实际 fork 和 trace。

三个隔离试验已否定简单限制足以跑通目标的假设，均未合入正式 Sail/workaround：

- `FVFTYPE` 只限制 slide 循环每路径 fork≤1，以及额外限制 `vstart` 上界每路径 fork≤1，两档均 180 秒外限、无 JSON；追加全局分支≤1／前导与 slide 区域 0 次 fork 的既有候选，300 秒仍外限、无 JSON。其前缀有 5 条 Retire，但不能称为完整采样。
- 从普通后端复制 `FVVTYPE` 按活动 mask 才计算的执行体，在隔离模型生成 IR `f60a44b8…3584`，只在该循环设置 0 或 1 次 fork，两档均跑满 300 秒且无 JSON。1 次 fork 档前缀为 55 Retire／25 Illegal／1 non-encodable，trace 确认局部限制实际触发、mask 分支两侧出现；这种改写未证明收敛，未进入工作树源码。
- 原 IR 的 `VFUNARY1` 对估算循环与 Sail NaN helper 三处实际热点分别设置每路径 fork≤1，trace 记录 41 次局部限制触发，估算循环和 NaN 判断两侧均有 Retire 前缀；300 秒仍外限 124、无 JSON（17 Retire／25 Illegal／1 non-encodable）。未扩充为正式配置，也未据残缺前缀宣称语义覆盖。

另试图在隔离 FD 配置的 `[registers.defaults]` 固定 `vtype=SEW16/LMUL1`、`vl=1`、`vstart=0`、`fcsr=0`，但当前 `Target::setup_pre_state` 会对 `reg_list()` 中的已初始化寄存器重新符号化；其单测也明确验证覆盖行为。FVVTYPE 的 120 秒试验仍在 `assert_sew` 多处分支取边，外限124、无JSON，因此**这不是有效的固定状态分片试验**，不能用其结果否定真正的分片方案。下文旧 `agents/findings.md` 关于单靠 `registers.defaults` 具体化求解寄存器的记录已加当前版本修订。要实行分片，需在 `setup_pre_state` 后保证执行值与输出的 pre-state 变量同步，并逐片证明并集覆盖目标语义；本轮未实施。

因此这轮可确认的卡点是多处前导检查、部分真正的逐 lane 分支与符号 FP/向量状态计算共同累积；没有证据支持把 22 个超时目标统一归为 `2^32` 逐 lane 枚举。后续须逐目标先证明局部采样能自然结束并保留可编码活动 lane，再以静态源码分母核每个有效 if/else、enum、宽度和特殊值；仅有 `summary.complete` 或残缺 trace 都不足以签收“所有语义”。

### trace 与 Sail 循环结构复核

下表将超时日志的实际 fork 与 **仅已完成终态前缀**的 ITRACE 分支重复访问次数分列；[逐 PC 核账](evidence/float-full-trace-20260929/loop-trace-audit.json)保留访问次数与两侧见证。`最多访问`是单个已记录终态对同一 IR branch PC 的访问次数，证明循环反复执行；它不是完整目标的路径总数。

| 目标与模型位点 | 300秒前实际 fork | trace 中的循环／表达式形态 | 判断 |
| --- | ---: | --- | --- |
| `FVFTYPE`，`vext_fp_insts.sail:1928–1950` slide 内 `if mask[i]` | 24 | 两条已记录 Retire 走到该 branch，最多16次访问；`1942` 的 slide 边界 `if i==0` 在同一终态中可走两侧 | 此分支确有逐 lane 路径增长；本轮只有两条 `vfslide1up.vf` Retire 前缀，不能外推其它 funct6 或完成路径数。 |
| `VFUNARY1`，`vext_fp_insts.sail:1694–1725` 估算／分类 `if mask[i]` | 49 | 22条 Retire 前缀访问该 branch 共106次、单条最多8次，12条同一终态走到两侧；Sail `float/nan.sail` 的 NaN／sNaN 判断各 fork 43次，`float/classify.sail` 再 fork 43次 | 这里的 mask 与特殊值判断在 lane 间重复，是真正需要局部采样的组合热点。 |
| `FVVTYPE`，`vext_fp_insts.sail:65–79` SYMBOLIC 循环 | 循环内 `funct6` 首个 match arm `:69` fork 10次；全目标134次 | 同一 match branch 在57条 Retire 前缀被访问304次、单条最多8次；源循环每 lane 算候选、用 ITE 合并 mask，没有逐 lane `if mask` | enum 分派会分叉，随后各 lane 重用已选 funct6；把这里说成每 lane 独立 `2^n` 路径不符 trace。重复的 FP 候选计算仍增加公式成本。 |
| `RFWVVTYPE`，`vext_fp_red_insts.sail:192–197` SYMBOLIC 归约 | 全目标仅29次，循环位置0次 | 12条 Retire 前缀共访问循环条件144次，单条最多33次；每次先算 `fp_widen_pure` 与 `fp_add_pure`，再用 ITE 选择累计值 | 这里不是 loop fork 爆炸，而是可能形成最长32个元素的连续 FP／ITE 公式链；本轮未记录逐次 SMT 耗时，公式成本的精确占比待诊断。 |

前导热点也不是同一种循环：`vext_utils_insts.sail:284–286` 检查 `vstart` 最大合法元素，22项共486次 fork；`vext_control.sail:514` 的 `read_vmask` 按指令 vm 选全1或读 v0，共286次；`:365` 将负 LMUL 折叠为单寄存器，共100次；`vext_utils_insts.sail:83–84` 检查源／目标组重叠，两位点158次。它们随上游 vtype、SEW、enum、寄存器选择的路径反复执行，形成交叉乘积。`init_masked_result` 的 SYMBOLIC 分支在 `__isla_use_extra_ops=true` 时调用 `isla_init_mask`，自身不逐 lane fork；不要把普通后端 `init_masked_result_default` 的多层 `if` 误算为本批热路径。完整批次的22项全部由外部300秒限制结束，日志未记录 panic、AssertionFailure、SymbolicLength 或 SMT timeout；资源止损未触发。因此“失败”是没有在预算内走完目标路径并写最终JSON，不是进程崩溃。

### 热路径的条件路径数（2026-09-29）

按本轮 VLEN128／ELEN64 和 `target.rs` 的合法向量状态域枚举，普通浮点指令排除 SEW8 后有15个合法 SEW／LMUL 组合。[可复算的15行数表](evidence/float-full-trace-20260929/theory-paths.json)记录每组最大活动 lane 数。固定一个合法组合、`vstart=0`、`vl=VLMAX`、`vm=0`，并选择不与v0重叠的合法源／目标寄存器时，v0 中各 lane 掩码位独立；下列计数只算循环里的掩码分支，不把前导、enum 和 FP helper 擅自相乘。

| SEW／LMUL | 最多活动 lane (n) | `FVFTYPE` slide 的独立 mask 分支 (2^n) | `VFUNARY1` 只按「不活动／sNaN／qNaN」三种可行控制选择 (3^n) | `vm=1` 时连续活动区间数 |
| --- | ---: | ---: | ---: | ---: |
| 16／1 | 8 | 256 | 6,561 | 37 |
| 64／8 | 16 | 65,536 | 43,046,721 | 137 |
| 16／4 或 32／8 | 32 | 4,294,967,296 | 1,853,020,188,851,841 | 529 |
| 16／8 | 64 | 18,446,744,073,709,551,616 | 3,433,683,820,292,512,484,657,849,089,281 | 2,081 |

`FVFTYPE` 的 slide arm 在 `vext_fp_insts.sail:1927–1951` 对每个活动 lane 执行 `if mask[i]`，无首个活动 lane 的提前返回。例如 SEW16／LMUL8 可取 `vtype` 低位 `0x0b`、`vl=64`、`vstart=0`、`vm=0`、合法不重叠的 `vs2=v8`／`vd=v16`；此时 v0 的64个mask位可分别取0或1，单就掩码分支已有 (2^{64}) 条可行控制序列。SEW32／LMUL8 同理为 `2^32`，并非从已观察 fork 数倒推。`vm=1` 时没有独立v0位，mask只是一段连续活动区间，最多 (1+n(n+1)/2) 种序列；`vl` 和 `vstart` 不应再与 `2^n` 机械相乘，因为它们只是改变哪些 lane 可活动。

`VFUNARY1` 的 `VRSQRT7`／`VREC7` arm 在 `vext_fp_insts.sail:1693–1726` 同样逐 lane 判断 mask；活动 lane 再进入 `vext_fp_utils_insts.sail:629–674,733–783` 的浮点分类／估算。sNaN 与 qNaN 至少走不同类别及 flag 分支，所以单按「不活动／sNaN／qNaN」已有 (3^n) 个独立选择。`VRSQRT7` 的 `match float_classify(v)`列出10个可行类别；若所有类别都保留独立控制路径，仅 mask＋类别的组合是 (11^n)，在 (n=32) 约 (2.11×10^{33})、(n=64) 约 (4.46×10^{66})。这是**条件性的类别组合量级**，不是经穷举证明的最终 JSON 条数：`recip7` 内还有舍入条件、128项表索引，编译器／SMT 可合并或剪去某些路径，也可能增加分叉。无论按保守的 (3^n) 还是更细的类别数，这一 arm 比 slide 更致命。

另外两处表面相似的 SYMBOLIC `if mask[i]` 不能按 (2^n) 算：`VFWUNARY0:991–1060` 和 `VFNUNARY0:1335–1413` 仅在选中的 SEW8 非法转换 arm 中进入该循环，遇到**第一个活动 lane 即返回 Illegal**。分支序列只由「第一个活动 lane 在哪里，或完全没有活动 lane」区分，最多 (n+1) 种；合法宽化 EMUL≤8 时该子域 (n≤64)，所以最多65种。两目标的其它路径仍可能昂贵，但这两个 loop 不是指数爆炸源。

其余 SYMBOLIC 主体如 `FVVTYPE`、`FVVMTYPE`、BF16 算术与 `RFVVTYPE`／`RFWVVTYPE` 用 ITE 选择 lane 值或 flags，没有逐 lane mask fork。`FVVTYPE` 的9种 `funct6` 是同一条指令字段，首次分派后各 lane 重用该选择，不能写成 (9^n)。归约尤其值得单列：`RFWVVTYPE` 每 lane 构造一次 `fp_widen_pure` 和一次依赖前一累计值的 `fp_add_pure`，最大64个活动 lane 可形成128个顺序相关的 FP 运算项，路径数量却不随 lane 按二路指数增长。它在基线仅29次fork仍跑满300秒，说明存在与路径数不同的公式／SMT成本；本轮没有逐查询计时，无法给出这部分的精确时间分摊。
