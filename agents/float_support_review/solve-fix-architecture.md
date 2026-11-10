# 77 项 solve 修复的架构与验收边界

日期：2026-09-26。状态：实施契约；不是新一轮功能 PASS。

本轮继续已获用户授权的浮点议题。实施顺序见 [计划](plan.md)，事实依据为 [总审计](solve-audit.md)、[方法](solve-audit-method.md)、[批次](solve-audit-batch.md)、[标量](solve-audit-scalar.md)、[向量](solve-audit-vector.md)、[BF16](solve-audit-bf16.md) 和 [日志语义](solve-audit-log-semantics.md)。七份历史审计保留，不用本方案改写其受测版本和失败。

## 1. 基线、目标与证据口径

当前正式输入为 d012 IR：`d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409`。Isla HEAD 为 `f4f8e4584a70588c66c9e7a6286cc20211618f18`，Sail-RISC-V HEAD 为 `f8ce8490981eac6396a31013180a2e718615757d`；两者工作树已有修改，HEAD 不能代替源码 manifest。

规范集合为 `FD_FLOAT - MEMORY - {FMVH_X_D, FMVP_D_X}` 的77项。普通 `make solve` 排除浮点，不是这77项的验收入口。新增 `solve-fd-nonmem` 只提供明确集合及正确总数，继承各目标原有配置；不借入口改动扩大默认集合、变更全局限额或进入独立内存分支。

旧官方批为40项退出0、36项外层超时、1项退出1；41份JSON共3474条，全部缺少 fcsr，无法据其独立重放浮点状态。全日志62次执行错误中，61次是 flags 累计处 SMT timeout，另1次是路径超时。12项目标未观察到合法退休。这些事实说明本轮必须同时修复性能、状态、账本和证据链；不能只延长超时。

完成表至少包含五个独立字段：任务是否正常收尾、合法 Retire 数、错误与未完成路径、采样/限额、source site/arm 闭合。达到全部门槛才可写本轮77项完成；该表始终不表示所有数据输入和循环组合的形式化穷尽证明。

## 2. 输入域与 decode 契约

### 2.1 保持符号域

官方路径保持 constructor 字段、整数/浮点/向量寄存器、fcsr、mstatus、privilege、vl/vstart/vtype/vcsr 的既定符号入口。沿用现有 V 类型合法化：合法 SEW/LMUL/ELEN 组合及 `vl <= VLMAX`，或独立的 vill 编码与 vl=0。不得把 FS/VS、FRM、LMUL、mask/tail 或寄存器编号固定成方便值来取得结束。

完整输出时对未约束符号取一个 witness 是序列化工作，不是新增执行前置条件；所有字段须使用同一个终态 Model。固定状态的测试用于给出具体分支和数据例，不替代该官方符号域。

### 静态处理器能力的必要合法化

后续源码审查确认：`core/extensions.sail` 的 `hartSupports(Ext_H)=false`，正式d012 IR同样为false；reset为Machine，MRET使用virt=0，SRET仅User/Supervisor，trap目的为Machine/Supervisor。枚举类型虽然含VirtualUser/VirtualSupervisor，这两个值不属于本模型支持的真实机器状态。不能让R2把人为注入虚拟态的 `internal_error` 静默当成功，也不能据此只允许Machine。

RV64 `core/sys_regs.sail` 259–266根据静态S/U支持将SXL/UXL初始化为2或0；`legalize_mstatus` 219–221明确不支持动态改变二者。当前将整个mstatus新符号化会引入0/3等无法由该模型合法设置的架构宽度，U/S路径可在 `architecture_bits` 失败。旧TOML `mstatus=0x6600`本身抹去了这些只读字段，不能用它作为能力来源。

已审定最小修正：复用现有IR函数执行接口，以同IR/lets、空RegisterBindings、独立fresh solver分别探测 `hartSupports(Ext_S/U/H)`；每项必须唯一 `Finished(Val::Bool)`，没有寄存器依赖、采样、异常或Unknown，否则停止并报告，不猜默认值。当前scope只需要这三个静态bool。按能力保留Machine、支持U时User、支持S时Supervisor，以及H支持时对应虚拟模式；RV64约束SXL=支持S?2:0、UXL=支持U?2:0，并核对模型xlen为64。其它mstatus位包括FS/VS Off仍符号。能力值、IR hash及来源写domain manifest。

TDD分别证明当前User/Supervisor/Machine可满足、两虚拟模式不可满足，FS/VS Off可满足且不被固定，其他可变位可取不同值；关闭S/U的fixture只排除对应模式并将对应只读XLEN字段设0。该修正是经源码证明的处理器静态边界，不是为性能任意取一个方便运行态。

默认非浮点入口随后暴露的MRET域问题也按源码单独审定：MPP的保留编码`10`在reset、trap写入和CSR `have_nominal_privLevel`合法化中均不可产生，而MRET直接将它送入 `privLevel_bits(..., virt=0)` 会触发内部错误。因此只排除MPP[12:11]=`10`，保留`00/01/11`；不一并固定MPV或套用整套WARL掩码，也不根据S/U开关排除reset仍可能保存的MPP=0。新增约束与三合法值SAT/保留值UNSAT测试写入domain manifest。

### 2.2 明确三个阶段

优先复用现有 `zencdec_forwards`、`zext_decode`、`zexecute`，在一个符号 wrapper 和同一 frame/solver/checkpoint 内完成以下顺序：

1. requested constructor 经模型编码关系得到符号 word。
2. 用同一初态对 word 调用真实 `ext_decode`，保留 decoded constructor。
3. 执行实际 decoded 值，记录架构返回及终态寄存器。

不得在执行前先取 model 把 word 或寄存器具体化；不得先直接 execute 再仅靠反向编码声称译码合法。保持 requested、word、decoded 三者关系供验证；译码返回 ILLEGAL 进入模型的正常非法指令语义。

**编码关系自身含 currentlyEnabled/SEW 等守卫。**因此 requested constructor 全域中的部分状态会在 encode 阶段 MatchFailure，尚未进入 decoder。这一类必须单列 `non-encodable-constructor`，不能计为 decode Illegal、Retire、Dead 或静默删除。只有失败位置和已审 mapping guard 能解释该边界时，才列为预期输入域排除；嵌套 helper 的意外匹配失败不能按阶段一概豁免。具体识别同时要求当前函数为 encoder、PC 指向运行时 catalog 确认的唯一末尾默认 `Exit(MatchFailure)`、requested 属于已审77集合且有对应 mapping arm/SourceLoc；每个新IR重新确认，不能硬编码d012坐标。该分类只表示模型编码关系在此初态无像，不能证明编码guard本身正确。原始机器字在扩展关闭/非法 SEW 等状态下的真实译码负例由定向 word 测试另证；成功decode与requested参数的关系须在符号路径验证，不能仅比较一个model，当前不预设允许alias。

此最小路线明确公开 constructor 工具入口的局限，不把它扩大为任意32位字的穷举器。若实现无法保留阶段和失败来源，先补账本再启用 wrapper，不能用 post-state 反向规避初态 decode 守卫。

## 3. 终态与错误账本

复用 collector 的锁建立每次运行唯一递增的 `case-id`。`TaskId` 会被 fork 继承，64位 path signature 也可能碰撞，均不能单独用作唯一关联键。保留签名供排序/路径比较，JSON、itrace、终态账本使用同一 case-id。

| 终态 | 必需处理 | 能否作为合法指令通过 |
| --- | --- | --- |
| Finished + Retire | SAT、完整物化、执行后状态、编码及结果证据均成立 | 是，限本 witness |
| Finished + Illegal_Instruction | 正常架构拒绝；核对来源、前后状态和不应有的副作用 | 否；可覆盖非法分支 |
| encode MatchFailure | 记录 phase、function、SourceLoc 和输入域；区分已审 guard 拒绝与异常匹配失败 | 否 |
| execute MatchFailure / AssertionFailure | 保存路径与错误；合法域内发生即阻断，不能静默 | 否 |
| Dead / UNSAT | 明确记录排除原因；只有对应查询与域完整时可用作不可达证据 | 否 |
| Timeout、Smt、Z3Unknown、类型/缺函数/位宽/边界错误 | 全部进入错误计数与上行失败，保留首错及完整列表 | 否 |
| Poison、Exit、Suspended、无Model、空/失败物化 | 记录不能生成可接受完成结果；不能用空字段交付 | 否 |
| 路径配额、深度/loop/fork限额、采样、外层杀死 | 记录动作、位置、预算、已调度/丢弃/剩余任务；明确不完整范围 | 否，需单列 |

所有错误都须影响摘要，而不是仅接收 Timeout/Smt。可恢复的输入边界与运行器内部不变量分开：后者遵守 `isla/AGENTS.md` 直接 panic，不用 catch_unwind 包住 Model 构造后静默填空。即使进程未能正常收尾，外层 batch 也须记录退出状态与部分账本，不能因为缺最终JSON丢失整个目标。

配额与采样状态不由退出码隐藏。若命令语义允许“生成样本后正常收尾”，摘要仍须明确 sampled/incomplete；官方验收单独审查相应范围，不能把它写为全域自然穷尽。summary 与所有 terminal 的计数须一致，重复或丢失关联键应使验证失败。

## 4. 可重放的状态与元数据

保留旧字段的兼容读取，采用 additive schema/version；原稀疏 `isa-state` 如保留，不能被称为完整状态。新的完整 pre/post 至少覆盖 RV64 x1–31、f0–31、vr0–31、fcsr、mstatus、cur_privilege、vl/vstart/vtype/vcsr，并记录实际执行触及的其他架构状态。x0 是固定零，不能 symbolization；PC 若进入本执行/重放契约，则需明示取值与更新语义，不能从配置臆造。

pre 从执行前保存的 PreStateCtx 取值，post 从终态 frame 的 RegisterBindings 取值，禁止复用 entry regs 冒充 post。开启 Model completion 后必须一次物化同一 witness 的全部状态，保留32/64/128位宽、结构字段和原始 flags；错误向上传播，不能警告后省略必要寄存器。新字段至少能还原 FRM、旧/新 FFLAGS、FS/VS/SD 和 privilege。

运行 manifest 记录实际扩展集合、VLEN/ELEN/XLEN、配置与源码差异 hash、IR和转换后IR坐标表hash、执行器二进制hash、Sail/Z3/汇编器版本、完整命令及预算。删除把 `arch.ext` 硬写 IMACFD 当实际能力的做法；实际配置常量和运行态 enabled 状态须能区分。

重放检查对全部完成记录验证编码、pre-state、ret_val 与 post-state。合法标准汇编另经汇编器重编码；编码合法性负例或不能用标准文本表达的非法寄存器重叠样例，可用原始 word 重放并明确分类，不把汇编器拒绝所有非法 word 都叫语法错误。

重放初始化须与实际运行manifest一致。当前官方先 `assertions_to_jumps`，再以 `Optimistic` 和默认 `use_model_reg_init=true` 初始化；只复制 `Optimistic` 而遗漏assert改写会隐去失败域，只沿用历史E runner的 `use_model_reg_init=false`也不是同一入口。重放须显式暴露并拒绝可达AssertionFailure，不能靠补默认初值解释差异。

经运行器设计与架构共同审定，完整目标pre-state之外的辅助初始化可以保留残余符号分支，不机械要求执行器零fork；条件是完整枚举全部终态，并在**每个SAT路径证明观察结果唯一**。最小实现为：先SAT，保留原始decoded或ret及全部post的Val；在同一Model取得具体值；再对所有 `eq_anything(original, concrete)` 的合取取反查询，必须UNSAT。随后将已证唯一的decoded全部参数、ret与完整post逐项和记录比较。只比较每路径一个model的值不满足此门槛，因为仍可能隐藏同路径另一辅助取值的差异。任一差异SAT、Unknown、Poison、错误、采样或截断均失败；Dead仅按已证明UNSAT单列，不当成功witness。辅助域同结果/可变化的正负fixture与初始化参数进入重放证据。

## 5. flags 性能与寄存器副作用

`accrue_fflags` 旧逻辑只在新 flags 改变时更新 fcsr 并标记浮点上下文 Dirty，最后两次 fflags/fcsr callback 总会发生。不能无条件调用有副作用的 dirty 函数来消除分叉：flags 未变时 FS/SD 必须保留。

已审定的最小性能边界：仅 SYMBOLIC 路径把相同架构状态关系写成 ITE，非 SYMBOLIC 路径保留原条件和实际 C++ callback 行为。当前 SYMBOLIC `csr_full_write_callback` Sail体为纯 `()`，FD配置也将其设为常量 primop；因此允许该空调用事件及同值寄存器写次数变化，但须记录该差异，不能宣称新旧 trace 逐事件等价。末尾 fflags/fcsr callbacks 保留；不能将此特例推广到未知或有外部效果的 callback。

状态等价域包括旧 fcsr 全位、FRM、五 flags、完整 mstatus、Ext_F/Ext_Zfinx 条件，以及 flags 未变/改变、FS各状态、原SD两态。原函数在需要dirty时进行的扩展不变量检查仍须保持相应条件；不能因为合法默认配置恰好成立就删除所有配置下的检查。

### P1暴露的隐式SMT查询与纯比较修正

P1虽已把flags控制分支改为ITE，真实sqrt诊断仍在 `changed = old != f` 超时。Isla `neq_bits` 使用 `binary_primop!`，调用 `try_concretize_bool_exp` 主动做反向与正向两次SAT查询；因此“没有Jump”不等于“没有中间SMT查询”。现有 `eq_anything` 对符号值只构造Eq表达式，`not_bool`也只构造Not，二者可表达相同位串关系而不触发这项优化。

批准FD owner仅将SYMBOLIC `changed` 写成 `not_bool(eq_anything(old, f))`，完整状态/assert域、callback及非SYMBOLIC体保持。先用真实Sail小IR核对显式generic equality没有重新降为 `eq_bits/neq_bits`，再复跑完整fcsr/mstatus/flags等价及真实sqrt失败。该修正不改全局比较原语，也不为求解速度改变输入域。

后续纯lane与归约也有相同数据依赖：归约下一lane接收上一步计算出的FP `sum`，widen/FMA接收转换结果。已另行批准单一owner修改 `core/ieee_fp_exceptions.sail` 现有五个classifier的exp/mant等值，以及add/sub/sqrt/FMA的sign等值；仍复用 `float_bits/float_decompose`。同owner仅修改 `softfloat_symbolic_f16/f32/f64.sail` 饱和结果选择的sign等值。全部显式使用 `eq_anything/not_bool`；RM枚举比较、异常算法、五Bool flags表示、共享flags出口和公共 `common.sail`不变。V owner对其SYMBOLIC纯helper中的±0、NV位、class字段、窄整数溢出/方向同样处理，min/max继续调用共享 `ieee_is_nan`，不新增重复NaN分类器。BF16 owner仅修改SYMBOLIC宽化helper的exp/mant/quiet-bit三个谓词。

上述仅限已审纯数据谓词，不批量替换架构合法性guard或普通后端；本轮新lane的active mask判断也保持现状，若后续真实诊断证明该处成为问题再单独审定。各owner保存修改前的生产源对照，验证未知输入的完整结果/flags关系、生成IR的实际原语、单路径性质；最终277未知helper入口及指令状态套件须绑定新候选。P1旧定向PASS及之前源码hash保留为历史，不能因代数等价直接迁移为新版本动态PASS。

实际编译还暴露Sail singleton Bool使FMA外层 `eq_anything` 或Bool ITE类型不匹配；`eq_bool`在Isla同样走主动SAT，不能换回它。获准用既有strict Bool表达等价XOR：`(p && !c) || (!p && c)`，实际代码使用 `strict_and_bool/strict_or_bool/not_bool`，不新增helper。三格式仍须核生成IR未回降成 `eq_bool` 或Jump，并证明完整invalid关系。

已确认的 FPR 快速写入问题纳入同一 `fdext_regs.sail` owner：SYMBOLIC `set_F_bits/set_F` 直接 `wF_from_vector` 跳过普通 `wF` 的写回 callback、Ext_F 检查和 Dirty 更新。必须恢复普通写入的架构副作用并保持同一目标寄存器、boxing及非目标值，先用初始 FS 非 Dirty、无新异常的写入建立红例。这不是通过预置 mstatus Dirty 解决的性能问题。VPR 同类问题由向量专题核实、补红例并移交明确 owner 后实施。

同一owner顺带恢复两个 fast getter 与 `rF` 的既有契约：仅 `__isla_vector_fpr=true` 臂先检查 Ext_F，再对原索引的 `rF_from_vector` 返回值调用 `fregval_from_freg`；普通臂不变，读操作不增加Dirty、callback或写入。正常F配置用f0/f31哨兵与完整无写状态核对；F=false直接helper负例须在支持配置为false的真实源fixture中比较，不能把清misa.F误当编译配置hartSupportsF=false。

VPR的同类遗漏已由完整d012 IR直接helper红例确认，不能靠指令末尾 `set_vstart` 的Dirty掩盖：同值 `set_V_bits(v0, old_v0)`，初mstatus=0x200，普通臂输出0x8000000000000600，fast臂仍0x200。主 agent 分配 `vext_regs.sail` 单一owner恢复两个fast setter：先原 `wV_from_vector`，再 `dirty_v_context()`，最后 `vreg_write_callback`，与普通wV一致；VPR的Dirty在callback之前，不能照搬FPR顺序。索引与原写入值不变，false/非SYMBOLIC保持；普通rV没有扩展assert，getter不额外增加检查。新IR还需验证v0/v31、同值写、VS Initial/Clean、其他mstatus/fcsr和非目标寄存器不变。

### 第二阶段：纯lane计算和活动flags聚合

性能专题已用真实Sail `riscv_f16Add`、未知输入/旧目标/flags/mask的小IR证明2/4/8lane由4/16/256路径变为1，全部旧路径先SAT、输出差异UNSAT；这允许派发生产实现，不代表生产指令全通过。

第一包由单一owner写三个V文件：`vext_fp_utils_insts.sail` 新增纯 `(bits_fflags, result)` 接口，`vext_fp_insts.sail` 仅FVVTYPE/FVVMATYPE/FWVVTYPE/FWVVMATYPE/FWVTYPE/FVFTYPE/FVFMATYPE/FWVFTYPE/FWVFMATYPE/FWFTYPE十个clause，`vext_fp_vm_insts.sail` 仅FVVMTYPE/FVFMTYPE。合法性、格式、寄存器组与opcode选择保持；不同时计算所有enum运算。每lane只运行已选定且total无副作用的纯helper，结果用既有 `vector_select_masked(mask, initial, candidate)` 合并，flags为 `OR_i(ite(active_i, flags_i, 0))`，在原最终写回前一次 `accrue_fflags`。widen须合并所有输入转换NV与运算flags后才屏蔽；min/max保原NaN、±0、quiet NV优先，gt/ge保NV时false，不能靠布尔取反误收NaN。纯接口不读写fcsr，RM显式传入；非SYMBOLIC原逐lane副作用保持。

聚合等价性由flags单调OR保证，且专题已对8个任意lane flags/active位、完整fcsr/mstatus、XLEN32/64及四种F/Zfinx配置证明最终状态与断言域等价。SYMBOLIC事件次数有意变化，原有callback空体边界仍适用。全inactive时flags增量为0，不应新增FS Dirty；向量尾部 `set_vstart` 的VS Dirty语义独立保留。

第二包为BF16四clause，单一owner写 `zvfbfmin_insts.sail`、`zvfbfwma_insts.sail`、`zfbfmin_utils.sail`。后者现有 `bf16_to_f32`虽纯但有数据分支，SYMBOLIC改为strict isnan/snan及值ITE：NV条件是NaN且mantissa bit6=0，值为NaN时规范f32 NaN、其它位串为 `v @ zeros(16)`。非NaN含inf/subnormal的旧fmake与此完全相同。VV合并两源转换和FMA flags；VF保外层标量读取、scalar flags只在active lane贡献，重复OR是幂等，非SYMBOLIC首活动callback逻辑保留。旧LMUL guard修复和标准assembly不能回退。先用全部BF16位串或未知BV16差异证明与单路径IR验证纯化，再跑mask/首活动/FMA融合/OF/UF/完整目标组例。

第三包为顺序归约，单一owner写 `vext_fp_red_insts.sail` 两clause及共享 `vext_utils_insts.sail::init_masked_source`。保留vl=0早退的原位置，不读seed、不写目标、不清vstart；其余保持i递增的 `candidate=pure(sum,src[i]); sum=ite(active,candidate,sum)`，不重排树。vl>0而全mask仍写原seed，不能把eager算出的sNaN规范化污染未选中sum。widen每步转换NV与运算flags共同屏蔽。mask helper只在原assert、get_start错误分支和real_num_elem计算之后，为SYMBOLIC且extra_ops开启增加 `isla_init_mask` 返回，原false/非SYMBOLIC循环保留。专题已取得2/4lane顺序归约全部旧路径差异UNSAT及2/4/8/64位source mask关系证明；生产还须顺序辨识、全mask seed、非法start和真实调用验证。

各包从P1冻结快照后开始，纯tuple签名由第一包owner交接，不能多人写同一文件。首包许可并未自动包含unary转换、Recip7/Rsqrte7、move/merge与guard短路优化；其后实际批准范围与独立证明如下，不能把后续许可回写成首包已验收。

### 后续明确批准的转换、分类与move/merge

普通V owner已获许可追加 `VFUNARY0/VFWUNARY0/VFNUNARY0`，仅将原无副作用转换改成纯tuple和masked flags累计。六个窄整数adapter按原32位结果饱和：signed溢出是结果不等于低D位sign-extend，极值由原bit31选择；unsigned溢出是高位非零。溢出时flags替换为NV，不与原flags相OR。该代数关系已对任意32位结果和五flags作差异UNSAT证明，生产helper仍须绑定实际源码与新IR验证。

原SEW=8不支持格式的 `Illegal_Instruction` 位于活动lane内，不能无条件提升到外层。允许以原SEW/opcode条件选回原loop，或在同一guard下证明mask非零后拒绝；全inactive必须继续原目标写回/清vstart。支持格式分支中的类型补齐占位值必须由外层互斥条件证明不可达，不作为未知输入的fallback。

`VFUNARY1` 只批准sqrt与class纯化；Recip7/Rsqrte7继续原loop。class复用 `float_bits/float_decompose` 与strict Bool，bits9..0依次是qNaN、sNaN、正inf、正normal、正subnormal、正零、负零、负subnormal、负normal、负inf，再zero-extend到SEW，flags为0。验收要求三格式未知输入与旧分类差异UNSAT、单路径及十类别位序；sqrt另核inactive负数/sNaN的flags被屏蔽。FVFTYPE的slide两项同样保留原有依赖索引loop，不由普通FP纯化顺带重写。

`VFMV` 使用原 `init_masked_result` 与标量广播作 `vector_select_masked`。`VFMERGE` 保留原start错误、SEW/LMUL guards及现有fractional `real_num_elem=num_elem/(0-LMUL_pow)`；先用原vm选择vs2或scalar，再以 `isla_init_mask` 的body mask在candidate与原vd间选择。该旧real公式与常见的幂公式不同，本轮不暗改；合法 `vl<=VLMAX` 域的差异由end裁剪，独立公式已验证三个fractional指数。非SYMBOLIC原loop保留，均不新增flags。最终新IR验证后由集成人移除两目标原整调用树采样assignment，同步退役配置与验证清单，并核dry-run无execution limits及运行summary采样为零。

## 6. 标准汇编修复

FLI 在 Zfa 源模型内新增共用 `bits(5) <-> string` 的32项双向 mapping，H/S/D 都使用它。index1使用 `min`，index30使用 `inf`，index31使用 `nan`；index29使用 `65536.0`，即使 H 中29和30都产生正无穷也保留不同文本和编码，不能按最终浮点值去重。

BF16转换修正多余分隔逗号，两个 MACC 修正源操作数之间空格为标准逗号；只改源 assembly mapping。测试从当前源映射构建最小 Sail fixture，先观察旧失败，再验证96条FLI和四条BF16指令各两种mask形态的真实正向文本与 LLVM 重编码。FLI literal mapping 另验 index→token→index 双向。Sail 0.20.1 将整条 `assembly_backwards` 标记为 not executable；专题测试进一步发现 `assembly_backwards_matches` 虽能编译，生成C仅为 `sail_match_failure`，两者都不能报解析PASS。保留该工具限制证据，以真实打印、独立LLVM重编码和literal mapping双向作为可执行门槛，不手写 parser 冒充模型逆向执行。全模型 strict check 另跑。尽量保留行数减少无关锚点漂移，但最终 strict workaround 仍按新IR/source坐标完整核对，不能因行数未变省略检查。

## 7. 源分支闭合与断言

机器表每行包含 clause、function、source file/span、site-id、arm/factor、配置前提、IR/source hash、case-id、输入、预期、动态证据、结果及状态。先固定分母，再接观察数据；一个 enum×SEW 的样例组合不是源码分支分母。

覆盖范围包括 match 各arm、if 两臂、合法性 guard 及必要的独立条件、loop 不进入/进入/继续/退出，以及首活动、屏蔽、前缀/尾部和目标组策略。循环不要求枚举所有lane排列；无分叉的 FP ITE 数据选择由位级结果/flags证明，不能拿 executor fork 计数衡量它。

动态 edge 只在确定执行了该边时记录，区分“只到达 site”“fork 两边 SAT 并已调度”“完成且结果验证”。具体 Bool、单侧 SAT 也须记录实际边。重入/递归维护调用上下文；路径在 Jump 结束没有后继时不能猜走向。R3复用 itrace 保存 terminal metadata，与JSON共用case-id；coverage工具只消费证据，不自行补造缺失轨迹。

乐观 assert 会过滤 false 域，零 AssertionFailure 不证明不变量。完整审计复用 `assertions_to_jumps`/`--fork-assertions` 显式暴露两臂，保存变换后 SharedState.functions 的 function/PC/SourceLoc catalog；不能拿原始IR文本PC对照变换后运行。如果assert来自已审前置条件，`pre && !assert` 的 UNSAT 可证明其非法臂不可达；SAT需解释并修复或明确入口域。失败 assertion 的轨迹和终态必须保留。

统一状态为：`result_verified`（有结果，无动态绑定）、`observed`（仅到达/边）、`covered_verified`（边与结果关联）、`unreachable_proved`（配置推导/UNSAT）、`unobserved`、`incomplete`、`failed`。分支闭合只能接受 covered_verified 与 unreachable_proved；source数据策略另有数值证明时在该行注明证据种类，不声称执行器曾走不存在的 ITE 分叉。

### 7.1 全局分母、共享helper和编译域

scalar、vector、BF16各包的词法catalog是候选，不能直接将各自site/arm数量相加。全局去重键为 `(规范仓库相对source路径, source SHA-256, UTF-8 token起止byte offset, kind, 同位置子条件ordinal)`；行列用于展示，单一行号不能区分同一行的多个条件。source hash或代码位置改变时生成新键，旧→新语义迁移单独记录，不用旧trace挂到新源码。

每个site保存所属函数/clause、完整source span、语法种类、arm标签、编译条件及审核状态。各包另以 `(clause, entry_mode, config/domain hash, site_id, arm)` 引用义务。共享FD/V helper只在全局表计一次；在某clause观察到它的arm不能自动满足另一clause的调用域。通用纯helper的证明可以复用，但须给出实际调用满足其前提的证据，不重复声称新动态观察。

复合条件中的实际短路 `&/|`另列factor义务，不能仅以最外if的两臂代替。统一kind为 `short_circuit_and/short_circuit_or`，token span取物理operator的半开UTF8 byte区间；该token已唯一，所以global key的 `subcondition_ordinal=0`，扫描顺序仅作展示 `factor_index`。正式分类须由Bool类型及IR降低确认，位串OR不能误计控制分支。末rhs可能只计算Bool再return，并无独立Jump；这时用已走前缀、输入参数与最终返回关系证明rhs值，不虚构边。此要求不扩为MC/DC全部组合。

本轮正式IR控制分母只包含SYMBOLIC实际编译域及本77项入口相关函数；非SYMBOLIC标 `out_of_build` 并给预处理/manifest依据，C++编译回归另记。固定实现开关的不可达臂须由实际初始化值及无写回证明；不能仅引用默认注释。`execute`全局分发中其他指令的arm不属于这77条的指令语义分母，encoder/decoder的相关mapping守卫则按阶段列入。

foreach的零次/进入/继续/退出保留四项控制义务；用同一调用上下文内条件的首次与后续命中解释，不能把一次false既计零次又计循环结束。已固定容器长度至少8时，vl=0只意味着mask无贡献，不证明foreach零次；其零次分支按类型/配置不可达证明处理。

### 7.2 SourceLoc关联与正确分支方向

R3的runtime catalog与edge首先证明记录确实来自本IR。源码span与IR SourceLoc重叠只能生成映射候选，不能直接把 `taken=true` 解释为源码if的true：短路求值可能产生多个Jump，编译器可反转条件，assert转换也会增加handler。

每条可接受的源码arm映射须包含：运行时function/PC与条件表达式、target/fallthrough、源码条件/arm、极性或所需edge序列，以及审核该关系的依据。跨helper/重入必须用完整调用上下文，只有调度没有后继或终态不能算结果验证。复杂短路guard可由支配关系和有序edge组证明进入最终then/else；不能用其中任意一个中间Jump代替整个guard结果。

编译后成为纯ITE或 `vector_select_masked` 的数据策略另建证明表，记录选值谓词的两类可行输入与完整值/flags关系；它们不是executor控制分支。P2把旧mask if放到非SYMBOLIC或替成pure选择时，保存旧义务到新数据策略的迁移依据，正式SYMBOLIC分母按当前源码重新生成。静态消除的控制臂用类型/配置/前置条件证明，不用“没在trace见到”当不可达。

最终交付同时给全局去重site/arm闭合表、逐clause适用义务及数据策略表。trace结构校验通过只能叫 `trace_binding_complete`；只有各适用arm获得结果关联或不可达证明，才能写 `source_branch_closed`。未闭合、超时和仅结果证明逐行保留，不能用整包PASS覆盖。

### 7.3 定向证据与官方域的对应

历史E套件及raw-state诊断保留原输入、初始化方式和结论。最终用来闭合official source义务的定向runner必须与官方采用相同assert改写、model register initialization与配置，并逐例核R1域：支持的privilege、SXL/UXL、MPP以及vtype/vl。固定某个合法初态可作该臂witness；注入域外状态只能证明诊断入口行为，不能算正式域命中。若为旧例增加canonical域版本，使用独立run-id和输入包hash形成新case键，原case名称/局部ID可以保留；逐例记录 `entry_domain_migration`、转换理由与预期变化，不能静默重写历史输入。

已确认的例子是旧向量 `illegal-vill` 输入使用 `vill | SEW32` 且vl=1，违反官方canonical vill仅bit63且vl=0的约束。canonical vill使 `get_sew()==8`；普通FP mapping仅允许16/32/64，所以其execute `valid_vtype=false` 臂在正式入口被encoder/decoder排除。`VFWUNARY0` 的两项整数到FP与 `VFNUNARY0` 的四项FP到整数转换允许SEW8，是可到execute Illegal的六个例外，须按实际enum单列。旧mstatus `0x600/0x6000` 等缺少支持S/U模型的只读XLEN字段，也不能直接挂到official域；完整helper全位关系证明仍可使用这些raw状态。

## 8. 文件边界、集成和资源

各实现 owner 以 [本轮计划](plan.md) 的 P/R1/R2/R3/A/C/B/I 表为准。设计由 Astra xhigh 审定；明确边界后 Sol 实现，Luna 只做可复核初筛。主 agent 负责跨包接口、写入权交接、状态文档和最终复核。覆盖工具不修改生产运行器；正式IR和严格配置只由集成人写。禁止进入或整合独立内存worktree。

R1先交“同Model完整pre/post”接口；R2定义case-id/phase/terminal schema；R3消费该标识并导出坐标表与edge；C各包据此关联其证据。当前已冻结的接口见 [运行器设计](solve-fix-runtime-design.md)：R1 `solve_pre_state_complete(model, shared)` 与 `solve_post_state(regs, model, shared)` 返回原 BTreeMap；R3 `ItraceTerminalMetadata { scope, case_id, status, phase, path_signature }`，scope 为 clause，键由运行标识、scope 与 case-id 组成。assert转换、wrapper与运行器IR插入的所有坐标变化须在最终catalog反映。现有 target 测试若先有红项，先记录原状，不用整合内存分支或扩大target职责掩盖预存失败。

资源采用先诊断再冻结批次：三类代表先90s/80s/15s、2线程；新77批建议300s/270s/30s、每目标2线程、最多4目标并发。共享主机内存/负载不允许时下调并发。只有明确慢查询或路径证据支持才给剩余目标600s/540s/60s复跑；每一轮保留独立输出和manifest，不覆盖旧失败。性能比较必须同候选输入、同资源和可比负载，不能拿旧 c9 与 d012 的不同预算直接比较。

`vfmerge/vfmv` 现有顶层 `max_forks_per_branch=1` 在 regions=None 时作用整个调用树，局部 region_fork_limits 不会收窄它。集成人须删去无必要采样或按真正热点定义范围，并同步注释、scope与命中计数；保留采样就报告其范围。源码arm补证和所有动态路径穷尽是不同验收对象，任何前者证据都不能抹去后者的截断事实。

每个包交接实际差分、命令、版本/hash、红绿结果、剩余缺口；源码/IR/关键配置变化后旧 PASS 降为待复验。全模型的67 helper、异常位序、既有差分及77定向集合在最终候选上重跑必要门槛，随后官方77、全部完成记录重放和branch表闭合。不以单元测试替代公共入口。

### 旧样例状态预期的迁移

FPR 快速写入修正后，旧1509/433样例中“无新flags写FPR却保留SD=0”的预期不再成立。保留原始输入、原expected和d012结果作为历史；候选复验生成独立副本，只按下列实际副作用更新expected，附每行 old→new、clause、触发函数/source和新置flags依据：

- 任一成功 `wF/set_F` 写入，包括同值写入、没有新flags，置 FS=Dirty、SD=1；其它 mstatus 位保持。
- `accrue_fflags` 只有新五flags相对旧值新增置位且 Ext_F 时，才置 FS=Dirty、SD=1。旧flags已包含本次异常时不能推断发生新的Dirty更新。
- `wV/set_V`、`set_vstart` 或 `write_vcsr` 实际调用 `dirty_v_context` 时，置 VS=Dirty、SD=1。当前向量FP成功路径尾部 `set_vstart(0)` 本身无条件Dirty，即使 vl=0、全mask或原vstart已经0，也不能只按“没有活动lane”推断 VS 不变。
- guard提前拒绝且没有执行任何写入时保留原态；按实际clause路径判断，不按“标量/向量”一刀切。其它结果位、非目标寄存器、FRM与flags预期不得随本修复漂移。

禁止把所有初始mstatus改成Dirty/SD1来消除这些差异。新包的Initial/Clean状态矩阵与旧输入互补；若新批修改某输入以加入新覆盖，应另建case-id并注明新例，不能覆盖旧例。

## 9. 仍须在实现交接时冻结的细节

- R2 wrapper 采用运行器临时IR的优先实现已写入 [运行器设计](solve-fix-runtime-design.md)，保留同solver和阶段失败来源；如遇现有IR API无法表达，再由Astra复核替代，不新增指令专用数值分发。
- R2/R3 terminal接口已冻结，assert失败handler识别与catalog序列化由实现红绿测试核实；独立owner动共享接口前先交接。
- P的完整ITE公式及配置不变量条件已在 [性能与状态设计](solve-fix-performance.md) 审定，实施者仍须交全状态等价与真实负载证据，不得只交较快的查询。
- VPR快速写入是否遗漏VS/SD与callback由向量源码和红例审定，确认后修最小范围并纳入新IR复验。
- 每个未观察arm的最小见证或不可达证明由scalar/vector/BF16负责人给出，不能以本节仍列待决为由提前写完成。

这些是实施交接项，不构成新增用户确认环节。主 agent 在既有授权内协调并持续推进，最终对未闭合项如实报告。

## 10. 本轮独立实现复核

- **汇编映射**：三源文件修改按第6节边界；复核者另用IEEE位域和有理数还原H/S/D的FLI常量，32个token唯一，96索引语义一致（H29的特殊溢出和30的inf分别保留）。重新调用LLVM22.1.8后，104条结果逐word核opcode/funct/rd/rs/vm，与真实打印文本一致。外部证据目录标识 `isla-architecture-review-20260926` 的 `assembly-report.json`，文本SHA为 `d75d9ae0096437b85f1784f6a91ac5cb2cc9e184d74729cf3f8620fe10548cfc`；受审zfa源SHA为 `804b002f96e7be22f6fd3173a143b545d7802f4979b5d68f65280b947f186ca0`。整条Sail逆向仍按第6节列工具限制。后续P2改同文件数值部分后最终候选须重新strict检查。
- **FPR getter前置检查**：从旧源SHA `b71d9da2208ab0591ea676b52fd9280ab455faace1250980d157ef2e5562f948` 与新源 `393abf4daf6ad5fc190517dcd4cd93df955a51cb029bb86e3eba899902588301` 逐定义抽取实际rF/rF_bits/get_F/get_F_bits到Sail C fixture。F=false时旧两getter普通臂均assert退出1，fast臂均错误继续退出0；新两getter的两模式全部assert退出1。外部目录标识 `isla-getter-guard-review-20260926` 保存 `run.py`、`report.json`、八份fixture与编译/执行日志。fixture将底层vectorread替为常量sentinel，只证明前置检查恢复；真实FPR索引/数值及无写由P1全IR验证，不能把该probe称全IR F禁用指令通过。
- **VPR Dirty红例**：外部目录标识 `isla-vpr-dirty-review-20260926` 保存完整d012字节前缀加独立wrapper的IR、三份输入和日志、runner/IR hash及命令。wrapper只设置fast开关、mstatus=0x200，调用真实 `set_V_bits(v0, old_v0)`并返回mstatus，不调用set_vstart。普通臂期望Dirty为SAT/差异UNSAT；fast臂对同一期望差异SAT退出101，观察预期改为旧0x200后SAT/差异UNSAT。原始失败保留，新IR绿例由实施者追加。
- **C1类型复用剩余项核对**：复核当时共享库/public包装hash分别为 `d80c4aabcc40f6c0de5aad439aab24a012de51a98ec1a3669ff4a52a781c9bf6` / `ee9ba560fb4acb70ed664593da95a52657dfef9bd6643ed830a1d4a4d5b0a881`。额外RM别名0、190个native声明、五泛型分类、内部Bool record和共享flags出口/ISA反序均已落实，未发现原C1必做生产项遗漏；四个canonical NaN包装是原审定明确延后项。Isla executor/float注册无RISC-V helper名称分发。后续第5节纯比较改动会改变共享源hash，P2新IR须复验277未知入口及既定类型/flags/配置门槛，不能迁移旧PASS；机器核对记录为 `isla-architecture-review-20260926/type-report.json`。
- **P2生产源码静态复核**：逐项核对BF16四clause的转换/FMA flags，普通V的操作数顺序、FMA符号、widen各源flags、NaN比较、六窄化adapter与class位序，归约递增sum、vl零早退和全mask原seed，以及move/merge两层选择，均符合本契约。此为静态结论，完整指令仍待P2 IR复验。另对六个V文件的非SYMBOLIC预处理结果与Sail-RISC-V HEAD比对，除 `vext_fp_utils_insts.sail` 新增两行说明注释外，忽略空白后原代码全部一致；证据 `isla-architecture-review-20260926/p2-static-review.json` 绑定各源码hash。不能据此替代C++运行回归。
- **VPR写入补丁复核**：冻结源 `vext_regs.sail` SHA为 `6682f5ce387359c4d5a6873cf877e2f001231b4f38917b8721c89cdfd81f17d9`，两个fast setter均按原写入→VS Dirty→callback排序，bits入口原索引、no入口转换索引均正确；普通臂及非SYMBOLIC代码保持。完整P2 IR `d86655a415441ad17533742b9d0ee726b43b64acaf2c0fc0754d27979c7859a9` 独立复验已接续旧d012红例：保留原IR字节前缀，仅追加与旧probe逐字相同的wrapper，normal/fast两份输入也逐字相同；无set_vstart，同值写v0、mstatus=0x200，两者均得到完整mstatus=0x8000000000000600，单路径先SAT、差异UNSAT、退出0。旧fast相同期望退出101的原始红证据保留。新证据目录标识 `isla-vpr-dirty-review-p2-20260926`，含 `run.py/manifest.json`、输入及日志，probe IR SHA为 `3962013d6e77750b7b13af6b22cdb681ccd5df0dca4a4dcbdffbe79abd184319`。该独立probe只观察mstatus，完整VPR/fcsr/非目标矩阵由FD实施包另记，不能互相替代范围。
- **R1合法域实现复核**：实际 `target.rs` 使用同IR/lets、空寄存器、唯一具体Bool静态探测，拒绝fork/采样/寄存器内存事件和非SAT；特权、SXL/UXL、MPP约束均按第2节最小边界。34项单测和FLI_S/MRET局部联调由实现包记录；新增小IR `Exp::Undefined(Ty::Bool)` 能力结果负例后35/35通过，实际因非具体Bool失败，没有model具化。新源hash为 `d9779a183f228da58f536e89491178293542f2cf55efd6574d68d9da4f0b0804`。77项与独立重放仍待最终候选，不能从局部summary推导全组通过。
- **纯比较真实FP红绿归因**：同冻结P1依赖和同一小IR中，未知f16/f32 sqrt(RNE)的flags判零仅分别使用旧 `neq_bits` 与新generic equality。旧两入口均22秒外限退出124，新两入口分别0.107/0.108秒、单路径SAT并退出0；IR核对四入口实际原语不同。证据 `isla-fp-equality-query-probe-20260926/report.json`，小IR SHA为 `da62c60b0a4b5d772452af95977e5bea5c8e859fc69996981a19c79e00a416e8`。此单轮控制实验确认中间查询来源，不是完整FD状态等价或77项性能验收。
- **纯比较与V1冻结复核**：core冻结为 `6a53eb013721787194a4fb370974e785fd0751f35f9d6cb66bb360ff82d6faeb` 后，五classifier字段关系和FMA strict XOR再次静态核对通过；四文件真实旧新抽取的27入口比较覆盖三格式分类、12种算术及12种整数转换，未知数据和RM0–4先SAT再完整结果/flags差异UNSAT，详见 [纯比较实施](solve-fix-pure-compare.md)。V utils冻结为 `8a642a1d4c317e7908f4a0951e14835a555792716b9997165c0ebd919998379d` 后，class十位序、quiet位、窄化溢出/方向/NV替换均复核正确；共享新core下49入口及12纯IR函数原语检查见 [V lane实施](solve-fix-vector-lanes.md) 和独立 `isla-vector-helper-final-independent-20260926/report.json`。这些小IR门槛放行最终集成；完整主IR与77项仍待后续证据。

### P2运行时分支与输入域的独立复核

BF16专题的P2词法catalog绑定IR `d86655a415441ad17533742b9d0ee726b43b64acaf2c0fc0754d27979c7859a9`、生成manifest `128d59a5661c3efdba566682c58ee6733f4799d9afd19fa3c6a542d24d95f346`。独立证书从实际 `assertions_to_jumps`、公开official wrapper及 `Optimistic/model_init=true` 的SharedState目录重新读取，而非模拟PC重排。外部目录标识 `isla-bf16-lowering-independent-p2-fd-20260926` 保存脚本及证书；其FD配置为 `20851fdbd5120066b5a0275d3780c255edb715b233fb31a2529b8e110ef723d0`，证书SHA为 `90f86a33f7910d593a1bf2458944d332328ed79a2bcd6ed00609d483bb7b6154`。

该证书确认13个短路token的25种实际lowering（4个扩展因子、5个execute因子、4个mapping因子的四种正逆向函数），以及8个assert的原Goto、四指令handler、恢复PC和实际eq16/lteq3条件。三个BF静态hartSupports恒true，可排各自能力false因子；四个loop的条件为 `i > num_elem-1`，首次false进入、后续false继续、后续true退出。P2的VLEN128与成功译码SEW16使 `num_elem >= 8`，首次true即零次循环不可达；vl=0不能作为零次命中。SEW assert失败排除仅适用成功译码至相应BF clause、其间未改vtype的入口；LMUL assert由前置 `illegal_fp_variable_width=false` 蕴含 `valid_eew_emul=true` 证明。此为极性及指定不可达关系，不是动态case覆盖。

共享调用义务还有更强前提：Wma的末项 `currentlyEnabled(Zfbfmin)` 仅在 `Zvfbfmin=true` 后执行；后者蕴含 `Zve32f=true`，再蕴含 `currentlyEnabled(F)=true`。相关当前启用检查只读misa/mstatus和静态能力，两次F检查之间没有写入；固定Zfbfmin能力为true，故VV/VF此调用域的Zfbfmin disabled不可达。标量caller的同一全局site仍保留disabled义务，不能全局删掉。

源码if映射也收紧：单一Jump且condition为Id不足以说明source true极性。保守证书须核实际条件定义，或证明taken/fallthrough分别进入互斥then/else的首条语义指令；Decl不算执行arm，不能穿过另一个未解释Jump或跨界调用再猜所属arm。复杂和隐式else保留frontier，直到有明确CFG及join证明。

独立逐例预检已检查scalar5121、vector2532、BF926候选的mstatus只读XLEN/MPP；vector/BF全部显式vtype/vl满足VLEN128/ELEN64的R1条件，canonical vill分别28/4例。原scalar5121候选全部未指定vtype/vl，因此仅SXL/UXL迁移尚不能证明完整official域；实施包另建显式合法上下文版本，旧输入保留。FD配置的实际初始化侧车显示cur_privilege/vtype/vl/vstart/fcsr尚未初始化，不能把model_init=true当作这些字段已取默认Machine/零。旧E配置则实际初始化Machine，须按各自配置区分。最终FD定向包显式记录Machine及新增向量上下文的见证选择，再由runner验证完整域。上述预检保留FS/VS Dirty且SD0样本，R1未新增SD关联。

### 后续候选的生成及通用表示边界

P2的实际生成消除了源中仍保留但生产调用已改走纯helper的四个旧接口：f16/f32到I16/Ui16。最终生成应显式 `--isla-preserve` 历史79 helper和直接状态验证需要的get/set接口，以真实Sail产物运行原277入口门槛。保留未调用接口不扩大77项的控制分母，也不恢复名称专用executor分发。不得在旧IR后附定义冒充正式生成；新IR/runtime/hash变更后重绑目录、严格配置并复跑相应门槛，P2证据保留为前驱。

性能专题进一步定位编码常量丢失：`append(Symbolic, Bits)` 的整体SMT表示使固定opcode切片仍为Symbolic，decoder比较反复查询SMT。真实小IR将同一unknown25与固定7位opcode分别用原append和现成MixedBits输入，200次相同比较由200次SMT查询降至0，输出差异UNSAT；外部标识 `isla-mixed-encoding-probe-20260926`。正式P2的64条一秒路径诊断有370–686次查询、SMT占80.2–91.3%，不能相加为进程CPU，也不是最终77完成证据。

主agent另分配单一owner按TDD实施最小通用候选：仅Symbolic与非空Bits的两种append顺序复用现有MSB→LSB MixedBits段；Symbolic+Symbolic及Bits+Bits保持原行为。必要配套是零长slice返回零长Bits，避免现有MixedBits空段结果；空追加、跨段/全宽/末端及动态索引、位访问、SMT出口和超过本地BV宽度须以原Concat关系核对。未知输入先SAT、完整差异UNSAT后才放行。该许可不包含Sail guard重排，不固定状态、不跳过真实decoder；此前纯FP比较包的局部边界仍保持，新包独立记录。

退役VFMERGE/VFMV配置的旧loop不存在时，不把采样区迁到pure select并声称原预算继续有效。官方目标已不加载这两份限制；历史配置单列原IR/源码归属，验证清单据实区分active与archived。其它仍使用的整数区域按实际函数/IR迁移，不能仅检坐标存在；例如fixed-rounding的sticky生成表达式区域只有neq_bits原语、没有Jump，历史bias注释须据实修订，不为本轮浮点任务移动到新的有效Jump而改变整数行为。

### 完整候选、运行器与测试域的后续审定

完整候选 `c5cbb0bbdaa9369b669aa7330531bfb1a0cf1ef7d905b071f14f510d10c7385c` 已真实生成；追加preserve恢复4个旧接口，模型生成manifest仍为 `128d59a5…`。外部目录标识 `isla-bf16-lowering-independent-p2-full-fd-20260926` 的证书重新读取full IR实际SharedState，13因素/25lowering、8assert、3能力排除、4loop的结构核验通过；主证书SHA为 `a37b1d0b6c3f474bd9f3dfbfd3dab2e4a1db8375dce131dc3eb10f9913f35016`。共享overlap末项的返回链另以 `overlap-certificate.json`（`0a96e97d…`）核对。它们仍绑定旧运行器快照，后续MixedBits或格式化修改后须新建证据，不转写为最终动态覆盖。

同目录 `wma-enabled-certificate.json`（`9cd8b2ce455f70ee53d26c96982732c80adcb3e6e935238e10a5a2c606b031aa`）把前述Wma蕴涵写为机读证明：按实际Bool CFG枚举5个抽象输入的32种组合，PC1335的末项Zfbfmin检查一旦抵达就返回true。两次F检查的函数只读misa/mstatus和固定能力，其间没有寄存器写。enabled动态义务仍需同terminal、同Ext_Zvfbfwma调用上下文的PC1332 true→1335边及正常返回；此调用disabled静态排除。不能把这一结论用于标量caller，也没有为末rhs虚构Jump。

**misa域以实际配置划分。** `core/sys_regs.sail::legalize_misa` 在本配置允许写misa，并强制D依赖F、V依赖F和D；hartSupports是另一层静态支持。当前官方目标按本计划保留既有符号状态清单，misa未主动符号化，固定初始化为FD配置的 `0x800000000034112f`。这限定本批官方证据的域，不能声称已覆盖所有可写misa状态。旧仅清F的 `0x800000000034110f` 仍保D/V，旧仅清D的 `0x8000000000341127` 仍保V，均保留为raw诊断，不算官方或合法canonical见证。新增合法Foff清F/D/V为 `0x8000000000141107`，Doff清D/V为 `0x8000000000141127`。各专题统一使用只修改 `registers.defaults.misa` 的派生TOML，逐case绑定实际配置hash，分别记默认、合法alternate、raw义务；能力配置不变，R1的特权与向量状态合法性仍须满足。

**MixedBits局部放行。** 最终primop源SHA `6c6d5a4248d9874405bbc48f850f5c32b77e60f0762212244e1a173fa13f4a20` 已复核：零长slice在索引转换前返回，非零固定slice用checked转换及范围检查，subrange不接受high<low，空追加不产生零宽段。合法索引域的未知输入与原Concat比较为差异UNSAT；非法输入的严格拒绝不能表述为与旧截断cast逐结果等价。67项局部测试及真实16/32位decoder的58对双向完整AST关系见[实施记录](solve-fix-mixed-bits.md)和[性能记录](solve-fix-performance.md)。decoder探针采用公开R1约束，但为Optimistic/model_init=false且未转换assert；结论只限该探针表示等价，不代替official初始化、终态与全组门槛。

**全宽输出修复边界。** 后续独审确认 `fmtval.rs::BitVal::from_bv` 先 `lower_u64` 再逐位右移会丢失B129高位，debug在移位达到64时还会panic；Symbolic的 `Exp::Bits(Vec<bool>)` 出口不经过此缺陷，因此旧局部绿结果不足以排除此问题。批准单一owner仅将该函数改为复用现有 `BV::to_vec()` 后 `Self::concrete`，保持LSB-first、宽度和全确定mask；BV的B129右移128实现会保留最高tag。先做0/1/63/64/65/128/129位、高低半不同、tag和Mixed宽Concrete段出口的debug/release红绿，再冻结运行器并复验。零宽的其它现行API契约不在此包扩展。已开始的旧stage保留诊断，不能因格式化补丁很小而沿用完整输出PASS。

### 标量 MIN/MAX 的最小纯数据化合同

本项接续同一77项调通授权；实施与测试结论另见 [标量 min/max 记录](solve-fix-scalar-minmax.md)。本节写明实施边界，尚不表示完整新IR或正式求解通过。c5生成快照与此前诊断保持原样，新模型与运行器全部冻结后统一重生成IR。

当前 H/S/D 的 MIN、MAX、MINM、MAXM 共12个 execute 数值体仍通过数据 `if` 链处理 NaN、正负零和 quiet 比较。V 的 `fp_min_pure`、`fp_max_pure` 已具备三格式的完整 `(bits_fflags, bits('m))` 关系；本项复用这两个函数，不另建浮点类型、分类器或 executor 分发。由于 `FD_core` 不依赖 V，将两定义逐字移入新增 `extensions/FD/fp_minmax.sail`，以 `SYMBOLIC` 包围，并在 `FD_core` 的三个 `softfloat_symbolic_f*` 文件之后加载；V 保持原调用名。

新增 `fp_minm_pure`、`fp_maxm_pure` 先调用相应 min/max，再以 `strict_or_bool(ieee_is_nan(a), ieee_is_nan(b))` 和位串 ITE 选择 canonical NaN。其 quiet 比较 flags 原样返回：任何 sNaN 设置 NV，只有 qNaN 不新增 NV；MIN/MAX 单边 NaN 返回另一操作数，MINM/MAXM 任一 NaN 返回 canonical NaN。正负零分别满足 min 选负零、max 选正零。使用既有 `bits_fflags`、`bits('m)`、`ieee_is_nan`、`canonical_NaN`、`riscv_f*Lt_quiet`、strict Bool 与 `eq_anything`，不引入数据 `eq_bits`/`neq_bits` 中间查询。

生产写入边界为 FD 的 `fext_insts.sail`、`dext_insts.sail`、`zfh_insts.sail`、`zfa_insts.sail`，新增 `fp_minmax.sail`，project 文件，以及 V utils 中被迁移的两个定义。仅在12处原读取完成之后将数值体拆成 SYMBOLIC 纯调用及原普通体；原 mapping 守卫、寄存器读取顺序、NaN boxing、`accrue_fflags`、原 `F_or_X_*`/`F_*` 写回及 Retire 顺序均保持。尤其不能把普通 MIN/MAX 的 `F_or_X_*` 改为只访问 FPR，也不能为优化固定寄存器、FS/FRM 或其他初态。非 SYMBOLIC 数值体与修改前工作树逐字保存，不以 HEAD 覆盖已有修改。

验收分为三层：

- 小IR从修改前真实标量数值体以及实际 `fle_H/S/D`、NaN/零分类与所需拆分函数提取 oracle；不得用简化分类 stub 代替后声称真实旧标量已验证。12组未知输入逐旧完成路径先证明 SAT，再证明完整结果位串与全部五flags的差异 UNSAT；新版各一个可完成路径，无 Unknown、错误或采样。原 `fle_*` 实际采用位域小于等于关系，局部变量名中的 `lt` 不能当作语义依据；MIN 原用 `fle(a,b)` 选 a，MAX 原用 `fle(b,a)` 选 a，新V helper统一用 `lt(a,b)`。必须由全位关系证明包含等值、NaN和正负零的选择变化，不能只比数值大小。
- 定向值覆盖两侧正负 qNaN/sNaN、双 NaN payload、两种顺序的正负零、同号零、相等非零、无穷与次正规；检查 NV 及其余四flags。完整模型 SYMBOLIC/普通 strict typecheck、普通12体保持，以及被迁移V的49项 helper 门槛复跑。
- 集成后绑定新IR、源码和运行器，全状态具体重放须核非目标寄存器、fcsr、FS/SD、原字段和 Illegal 无写；正式77项中的相关目标仍按原完整符号域与预算独立验收。小IR的单路径和等价不能替代这一步。

旧源码 `if` 数据策略不再属于新 SYMBOLIC 控制分母。覆盖负责人保留旧site与证据，通过逐操作的全位/flags证明登记迁移至新 ITE 数据策略；新 `fp_minmax.sail` 的格式 match 等控制义务按实际生成IR和静态类型重新判定。不得把迁移旧helper后的行号变化直接挂到旧trace。

### 最终分母与 MISA 域的统一交付格式

全局 source 表与逐 clause 义务沿用第7节的 token-span 去重键。最终结果至少区分以下证据域；域标签、实际配置hash与初始化sidecar是每条证据键的一部分：

| 域 | 状态来源与可接受用途 |
| --- | --- |
| `official-default` | 实际 FD TOML 初始化的 `misa=0x800000000034112f`，其余为已审 R1 符号域。只有这一域用于77项目标的正常收尾、Retire、错误、采样和官方分支闭合统计。 |
| `canonical-alternate` | 只改 TOML `registers.defaults.misa` 的合法派生配置，Foff 为 `0x8000000000141107`，Doff 为 `0x8000000000141127`；保留 R1 其余约束。其结果单独履行该 alternate 域的可写 MISA 行为义务。 |
| `raw-override` | 保留旧仅清 F 或 D 等违反 D⇒F、V⇒F∧D 的原输入及原配置来源。仅用于回归诊断与无前提 helper 等价，不能补 official 或 canonical 的控制臂。 |

默认域内固定 MISA 导致的某一 arm 不可达，须用实际初始化及本调用期间无 MISA 写入证明；不能称该能力在处理器上永远不可改。反过来，alternate 域可达不使同一个 arm 在默认域变为“尚未覆盖”。全局 source site 仍只计一次，默认/alternate 的适用义务分别列出，不能相加为新的source总数，也不能用 alternate 命中冒充默认命中。

上述三项分类描述MISA来源。既有 `__isla_use_extra_ops`、FPR/VPR快速开关的对照配置另带 `configuration-alternate` 维度及完整配置hash；它们与MISA分类正交，不因MISA仍是默认值就等同official配置。官方固定开关的不可达证明和另配置的动态结果分别保留。

历史 scalar5121 包曾含4999个默认值、82个仅清F和40个仅清D值；该计数只是该历史输入包的分域，不是最终新包数量。122条原例保留为 raw，新 canonical 例使用独立 run-id/input-hash 或明确新ID，并记录字段来源及预期变化；不能静默改原JSON。向量/BF16的任何 MISA override 也应用同一规则。源码分支闭合表与普通C++回归、纯ITE等价表分别报告实际证据种类，不以任一计数取代其他门槛。

### 完整状态物化的 Model 局部缓存合同

恢复后的性能诊断在完整 VFMVFS 域观察到255终态、`execute_all` 约17.934秒；两worker累计 collector 区间23.302秒不能与进程墙钟相加。157648次 ModelEval累计14.729秒，真实Z3 FFI约0.251秒，其余主要来自每次调用的超时包装；三轮完整pre/pre/post约12.273秒。此证据允许在诊断副本试验同一Model内的成功具体结果复用，不批准修改全局求解超时、check_sat、状态范围或输出数量。

`Model` 持有借用的Solver及引用计数Z3 model，符号表在该借用期间保持；但不能笼统称Z3 model完全不可变。`model_completion=true` 会为原未解释符号补值，`get_ast` 的宽BV取片和enum tester内部也使用true，另一个 `get_exp` 可能使先前的 `Arbitrary` 获得具体解释。因此候选仅对本 `Model::get_var(Sym)` 成功返回的具体 `ModelVal::Exp(Bits64/Bits/Bool/Enum)` 缓存原typed值的clone；`Arbitrary`、所有错误和Timeout均不缓存。具体解释一旦确定不会由补全改写；complete标志切换仍保守清空缓存。新Model各有新缓存，`get_exp` 保持原实现，不共用跨Model、跨solver或全局缓存。

缓存不得转换成宿主u64或格式化字符串，必须保持enum类型/成员、全部位宽、LSB-first位序及MixedBits消费者原行为。测试须包括：重复具体求值一致且减少真实调用；Bool/enum/64及129位；`Arbitrary→get_exp补全→get_var` 无陈旧结果；complete false/true切换；新Model隔离；错误/超时不缓存；Mixed消费者与原出口全位一致。独立性能副本与原版比较全部完整pre/post/结果，不能只比相同计数。通过后才由单一runtime owner实施最小生产改动并冻结，新77批重建，旧已跑批次仍保留诊断状态。

### 定向域检查和两段式重放的必要前提

定向runner可在独立solver中直接调用公开 `RV64::setup_pre_state`，将实际初始化及case覆盖后的具体值递归绑定到R1的相应符号值，并要求SAT。当前R1额外状态约束只涉及 `cur_privilege/mstatus/vtype/vl`，四项必须显式具体，不得先用Model任意补值再称原输入；其它具体pre-state字段同样全部绑定。实际测试仍从原actual寄存器执行。此证据绑定target源码、IR、配置、lets与初始化sidecar；以后R1增加受约束字段须扩展证明，不能沿用旧四字段结论。固定MISA须与实际配置逐位一致，按上节区分默认、alternate、raw。

具体word的两段式重放先执行 `ext_decode`、再以同完整pre和已证明的具体AST独立执行 `execute`；丢去decoder辅助约束只在decoder只读且无外部副作用时构成保守过近似。decode阶段仅允许 `Smt/Fork/Function/ReadReg` 事件，其它事件全部拒绝，并继续禁止未导出的PC/物理x0读取。由于 `_TLB` 和let等赋值可能不留寄存器事件，最终IR还需绑定一份直接调用闭包静态证书：所有global赋值为0、未知callee为0，外部调用逐项属于已审纯原语或固定config常量。证书不合或IR改变立即失效。每个SAT decode/execute终态都须先SAT再完整观测差异UNSAT和expected比对；Dead只有已证不可行过滤可排除，不允许把采样或未完成归为Dead。该流程验证具体结果，仍不称为正式encode-first符号路径的重演。

### 两个纯 mapping 成员谓词的合并

新诊断将 FVVMATYPE 的完整trace按完全相同文本前缀建立trie，再识别同一前缀下已观察到不同后继的分叉。1008个 decoder 分叉中，`encdec_nreg_forwards_matches` 的四个位点各88个，`vext_vs1_backwards_matches` 的四个位点各88个，共704个；这些纯成员检查在外层最终排除错误编码之前按未知5位字段逐值分叉。该数是已观察前缀分叉，不是CPU比例，也不是完整符号域的分叉总数。仅合并后端execute合法性Bool不能消除这些decoder前缀，因此本轮优先实施两个有直接证据的纯mapping谓词。

生产范围仅 `extensions/V/vext_arith_insts.sail` 的两个mapping定义。SYMBOLIC使用Sail已有 `val name : A <-> B` 及显式 `forwards/backwards/forwards_matches/backwards_matches` 接口；标准库的hex_bits/spc已采用该接口。真实最小Sail→Isla fixture已确认外层mapping能继续使用它，所需infallible接口由编译器生成。普通后端保留原mapping逐字，指令clause、guards、映射顺序和外层decoder保持。

| mapping | 保持的值关系 | 合并的总Bool |
| --- | --- | --- |
| `encdec_nreg : bits(5) <-> {1,2,4,8}` | `0→1, 1→2, 3→4, 7→8` 及原反表 | bits5侧 `forwards_matches` 为四个generic等值的strict OR；有限int侧matches为true。 |
| `vext_vs1 : vextfunct6 <-> bits(5)` | 既有六个enum到 `6,7,4,5,2,3` 及原反表 | bits5侧 `backwards_matches` 为六个generic等值的strict OR；enum侧matches为true。 |

成员谓词仅依赖完整5位输入，全部32种值均有定义；不存在原短路所保护的状态读取、assert、除法、索引或副作用。值函数仍使用原match关系，无效bits直接调用值函数继续MatchFailure，不能用任意默认枚举/整数补成总函数。泛型等值使用 `eq_anything`，strict OR使用已有primop；不建立任何mapping名的executor专用分发。

局部门槛为：32个bits输入的成员真假穷举一致、全部有效值正反映射及有限类型roundtrip一致、无效值函数仍失败；未知bits旧各完成路径先SAT再Bool差异UNSAT，新成员谓词各一个路径且无数据Jump/`eq_bits`；纯函数事件无寄存器读写/内存/Abstract/采样；真实外层小mapping的未知完整AST/payload关系，以及完整模型双模式strict检查。最终还须在新全IR上复验真实decoder和77项，保留旧c5诊断。局部门槛完成即可先冻结模型供IR生成，Rust物化缓存的独立冻结不应阻塞Sail编译。

`get_num_elem`、`assert_lmul_pow`、`assert_sew` 及execute guard的顺序本包不改。虽有若干总Bool可写成strict组合，本轮尚无足够证据表明其收益值得同时扩大模型差分；特别不能仅依据VLEN128下assert不可达就改变其它配置的错误顺序。

### 本轮组件独审与模型冻结

本节只记录本轮组件放行，正式77项、全状态重放和源码分支闭合仍需绑定新候选运行。此前c5批次受旧FmtVal宽位缺陷影响，保持诊断状态。

- **标量 min/max：** 已核12个普通执行体逐字保留、V原两个纯helper逐字迁移，旧oracle来自冻结前的真实标量代码及实际`fle_*`定义。实施包的12个旧函数共1566条SAT路径，逐条完整bits及五flags差异UNSAT；12个新函数各一条路径，288个定向pairs与原49项V helper回归通过。独立复跑最终36入口全部通过；外部证据标识为`isla-scalar-minmax-independent-om37ra7c`。新helper SHA为`b7f7017fa2b0801f0f3618ddd1c7457075d06a572a2bd8e873d653528580997b`，详见[实施记录](solve-fix-scalar-minmax.md)。文本IR检查已改为识别真实小写`jump`，并追溯条件别名至宽度分派；旧搜索`Jump(`的初稿不能作为无分叉证据。
- **两个mapping：** 生产`vext_arith_insts.sail` SHA为`60c1f6f2ec6809bbba39151b44fbeeaa2a5c071d78b0f4ab44d6401ff768d927`。独立逆除两个新增SYMBOLIC包装后，整文件与冻结前驱逐字相同；复核manifest的19项artifact哈希并重跑runner，退出0、294项PASS。旧未知bits5成员谓词分别5/7路径，新各1路径，完整Bool差异UNSAT；synthetic完整32位/16位decoder分别41/2路径差异UNSAT。独审证据标识`isla-mapping-independent-ryx6292b`，manifest SHA为`8a63041047c01f498202d19194e35170f149bea4efce8bcb34339052b4f06dbc`。见[mapping记录](solve-fix-mapping-matches.md)。该结论允许冻结模型生成新IR，真实全模型decoder仍单独验证。
- **FmtVal：** `fmtval.rs` SHA为`43806138bf1f3981b198bdd1f35a611d650dac49cbef9537912a9ed6df7a679e`。独审核最小改动为`Self::concrete(bv.to_vec())`，debug/release各两项边界组合测试通过；另逐profile验证B64的2145例、B129的8515例以及旧红新绿六例。旧红binary初始构建来源缺失的限制保留，后补红探针独立记录构建argv与依赖哈希。见[全宽输出记录](solve-fix-fmtval.md)。
- **Model缓存：** `smt.rs` SHA为`3ce7310d87a71cdd29381966f495450bfb8baab35f1a52e6638bebbaaa2d122f`。独审核成功具体typed值clone缓存、completion切换清空、新Model隔离以及`get_ast(...)?`先于插入，所有Err均不能进入缓存。独立验证多个Model共享handle后的补全、Arbitrary至Concrete转换、129位/enum稳定及clone修改隔离；`get_exp/get_finite`仍按原FFI路径。debug/release/thread-interrupt各3项通过；跳过三项既有Z3 enum sort重名测试后的260项通过不能写为全库PASS。Timeout不缓存为结构证明，未作动态Timeout PASS。见[缓存记录](solve-fix-model-cache.md)。

普通后端另做依赖隔离：以各包冻结前驱为基准，消除SYMBOLIC条件后，四个FD指令文件、V utils、V arithmetic共六个整文件的token序列一致；六个前驱源码哈希均与c5模型manifest `128d59a5…` 的相应条目一致。新增`fp_minmax.sail`普通模式为空，project的唯一新增项正是该空helper。前后普通文本、源哈希及检查结果保存在外部证据`isla-ordinary-dependency-review-ibxa_85a`。结合完整模型普通/SYMBOLIC strict检查通过，本轮两包没有新增普通C++执行实现；旧C++动态结果维持原版本归属，以此依赖隔离说明其适用范围，不把旧PASS改写成新源码哈希下的动态复验。

有限整数侧`encdec_nreg_backwards_matches=true`的合同限于Sail声明的`{1,2,4,8}`输入域；IR的`%i64`已擦除该细化类型，不能把向此函数注入任意宿主整数的raw调用也宣称与旧成员检查等价。官方浮点decoder的未知5位字段使用另一侧bits5总成员谓词；真实decoder对照仍需确认外层调用关系。enum侧同样使用真实六成员Sail枚举域，不接受伪造enum tag。

对该边界补做了实际全IR与公共入口的只读核验，证据标识为`isla-nreg-erased-domain-499jzuzj`：

1. **Sail合法域：** 原生mapping的整数反向matches逐一检查1/2/4/8，新显式函数直接true；合法有限域内相同。旧小fixture保留该成员函数时，越域整数可返回false，而新函数返回true，故不声称raw等价。局部294项中的108个无效值检查是bits5侧value函数，不覆盖擦除后的任意整数。
2. **公共构造器的raw域：** `isla/src/isarch/exec.rs::symbolic_args_from_types`与`isla/src/isarch/mod.rs::generate_symbolic_value`按IR类型调用通用`symbolic`。`primop_util.rs::symbolic_from_typedefs`把`Ty::I64`变为未附加范围约束的64位SMT位串，VMVRTYPE的nreg确实没有恢复`{1,2,4,8}`细化。不能用Sail源类型推断这些raw输入不可达；当前VMVRTYPE又不在77项名单中，其solve入口为`constructor-diagnostic`。
3. **本批实际可调用接口：** c5与新`1dcc8081…`全IR中，`zencdec_nreg_backwards_matches`的声明、函数体和调用出现次数都为0；未用接口被Sail消除。实际两编码器`zencdec_forwards`及其`_infallible`直接调用整数value函数`zencdec_nreg_backwards`。删除SourceLoc并按位置重命名函数形参后，三个完整函数正文逐字相同（分别43、31454、31451行）；指令、调用、局部名、跳转均保留。整数value函数本来就只检查1/2/4，其余raw整数走0b00111的末臂，此行为没有由本包改变。

因此当前冻结IR和77项无需为不可调用的有限侧成员接口重生成。今后若扩展preserve清单或把该成员函数公开为raw接口，须恢复完整原成员关系或明确其输入合同，并新增对应验证；此结论不为该未来扩展预先放行，也不修订现有公共构造器的细化擦除行为。

真实decoder定向复核采用audit-only同Symtab旧闭包克隆：读取旧c5与新IR，核共享类型、全局初始值和extern签名兼容，仅对完整旧直接调用闭包的函数引用加前缀。两侧共享正式初始化与公开R1状态，采用`assertions_to_jumps`及`Optimistic/model_init=true`。首组固定合法VV/VF编码的其他字段、保留`bits[19:15]`为同一未知5位输入，双方向逐可达SAT路径证明完整constructor及全部payload差异UNSAT；不固定特权、vtype、FS/VS。静态纯读闭包与动态事件限制共同拒绝隐性global赋值、未知callee和副作用。该probe的固定编码范围会明示，不能代替全decoder或全77项覆盖。

### 1dcc 最终证书与真实 decoder 复核结果

最终静态证书绑定IR `1dcc80812b8beaba49abaebf605e8090c2796b5930aefa36635b478c5f2b8180`、模型及运行器manifest `28fb65ee77e2c5e5c629c50b239a2e009337b47936b2fdbb897bf9c11bca055e`。可复现工具已保留在 [证书工具目录](tools/solve_architecture_certificates/README.md)，本轮产物位于 `isla/target/float-solve-evidence/architecture-certificates/final-20260926T160822Z/`。

| 证书 | 最终 SHA-256 | 适用结论 |
| --- | --- | --- |
| BF 控制与断言 | `507ea7ea375e16c99d884a17cd0ad64d7a1c767949aaa9fd2299fdc3c04920cf` | 13个site、25种实际lowering，8个assert、3个能力常量和4个loop的结构关系 |
| Wma enabled | `7397253c0d373e88720c34833d6a9eaeb707e69e93ba5ea61883c76cff708390` | Wma特定调用上下文内末项Zfbfmin disabled不可达；不适用于标量caller |
| overlap | `d0230dc0e1d45a9f2aab17c54fad71e246d881c2df69ee7109d9d7226f08c3ad` | 真实返回链及其条件；不代替caller×config动态覆盖 |

命令与输入清单 SHA 为 `095f9a159f10b7bef8774700ec8e7f426aa9145c429c1e7474917303e3847d6a`。独审逐项核对全部输入、冻结源及工具哈希，另在证据标识 `isla-final-cert-independent-t8_r96z2` 重跑三脚本，均退出0且输出逐字相同。这些结论承接前述极性与指定不可达关系，不把未命中的其它分支改记为已覆盖。

真实decoder双向证明已完成，证据目录为 `isla/target/float-solve-evidence/mapping-decoder-1dcc-20260927-lxm85ubv/`，`final-proof.json` SHA 为 `3fd93f281e41df689d00370514ec669951c4bfe926d1e4240df3b094194d6b5e`。runner源及binary SHA分别为 `488c16264aaf2cd9b369197fbe9bf92adce61d4c9426cff5eb405201c1b77742` 与 `89b4d9e8002effb6945b856f7830f7ec862a43bd213ea9adc67e5878a1c46b69`。

| 固定形状 | 方向 | 外层 SAT 路径 / 配对关系 | 自然退出 |
| --- | --- | ---: | --- |
| vfmacc_vv | 旧→新 | 315 / 315 | 0 |
| vfmacc_vv | 新→旧 | 270 / 315 | 0 |
| vfwmacc_vf | 旧→新 | 360 / 360 | 0 |
| vfwmacc_vf | 新→旧 | 360 / 360 | 0 |

四组全部 accepted，无Timeout、无Dead，每个SAT配对的完整constructor与payload差异UNSAT。两侧248函数闭包在同一Symtab中对照，Files按路径合并后重映射，旧克隆逆序列化恒等；唯一排除的旧Bool/BV5 tuple不被decoder或初始化引用。四个精确mapping成员函数均真实到达，目标FVVMATYPE和FWVFMATYPE构造器均实际出现。型别检查递归验证constructor、完整struct字段集合、enum及BV sort，并拒绝任意深度Poison；不能单独依赖`eq_anything`对Struct只遍历一侧以及空List/Poison兼容行为。Rust 7项、Python 6项检查通过。此前v3外层超时仍保留失败，本轮每方向独立120秒顺序执行；未缩小未知5位或R1架构状态域。

上述证据放行两个bits5成员谓词在明确固定浮点形状中的真实decoder等价；它不宣称全32位decoder或77项已穷尽。1dcc全77已自然结束50项、外层超时27项，完整重放与源码分支审计继续，不能把组件证明替代整体验收。

### 后续性能实现与标量分母裁定

[negate与完整布局实现](solve-fix-decoder-layout-negate.md)已按本议题授权落地：H/S/D `new_sign`各只改为最高位异或，旧未知两路径与新单路径的完整bits差异UNSAT；两条VMVR/VEXT纯完整布局采用现有tuple、寄存器及有限枚举，ordinary mapping和两处`when`逐字保留。独审初轮分别重跑60/86项，后续B补至103项，包含完整未知i64 nreg的四条SAT编码值关系差异UNSAT。最终manifest SHA为`aa0ee0923c69ff20c7cc0aa78e00da57993453fd822c2a141ecb2f4219409462`，B后的普通/SYMBOLIC完整strict均退出0。新全IR必须再核实际mapping guard调用位置/顺序，并对FVVMATYPE与F_MADD_D以相同预算比较，局部路径减少不替代正式27个超时目标完成。

1dcc标量24个旧`fle_*`词法site和9个配置前沿另完成独审。复跑[域证书工具](tools/solve_scalar_domain_proofs/README.md)后，两原证书输出逐字相同；独立裁定存于`isla/target/float-support-review/final-coverage/scalar/domain-proofs/independent-20260927/review.json`，SHA为`6df48e91f5e7506b1f98f3684f65c871e2b8bd498155ec4878d74c93af4053ed`。24个旧site仅有普通后端的12个调用，真实SYMBOLIC全IR和1081函数execute闭包无该定义/调用，十二个替代纯helper调用均按source site对上，故列为本版本未发射/未调用。9个固定site中，6个F/X双精度访问器X路径与2个`validDoubleRegs`内层site在固定能力域不可达；外层line220只有true被排除，false仍需完整调用正常返回的动态见证。不能把整个`validDoubleRegs`函数或这些site在其它配置一并排除。这一裁定仅用于冻结1dcc，不沿用于新共用CPP的源码分母。

上述`validDoubleRegs`见证随后补齐：同默认FD配置的146次实际完整调用均观察PC3异常检查false、PC7短路因子false以及立即返回调用者后的正常异常检查。完整静态后缀经PC8赋false、PC9跳到15，最终PC18赋return=true、PC19 End；独立复跑提取工具后输出逐字一致。证书`scalar/default/valid-double-completed-calls.json` SHA为`01333f4ab897c433207cc9464434712c888ee68c8c7696df3a27a0d743219ffa`。它可履行各自caller、phase、配置的源码外层false臂，不能把PC7命名为完整if或虚构return trace事件。

FCLASS与D move的剩余8项也完成指定域独审：H/S/D三个实际FCLASS调用分别为bits16/32/64；六个分类谓词消费同一个实参，各相邻Jump消费对应返回Bool，前五项false才会到inf。三份精确exp/mant分类互斥完备式独立复跑均UNSAT；逐一核实各true臂只能到正常End、不能回入类别假链，故各caller末项inf的false与最终assert失败共6项不可达。另两条D move的真实`xlen>=64 & flen>=64`短路、合并值与assert handler链在只读global lets均为64时恒真，两个失败臂不可达。独审另有错实参、错Jump结果及真臂回入假链三项负控，均被拒绝。

独立审查与可重跑检查源码位于`isla/target/float-support-review/final-coverage/scalar/domain-proofs/fclass-move-independent-20260927/`，`review.json` SHA为`3cb9a5e897ce2f14031812a698fce557b727f6d92e4ad5cf906e07bc8fbc1f9c`。所消费8项证书SHA为`95c177f88399964ce8325b6197e3c515926dc791f482e29195d68fc37a102ebc`。全部结论仍绑定1dcc IR、28fb source manifest与aa069实际sidecar，只放行列定caller-arm，不能泛化其它caller或新IR。

V的两个constructor另完成86项枚举控制排除独审。真实IR的`fvffunct6`全部13成员和`vfunary1`全部4成员与源mapping清单一致，实际字段Decl为对应Enum且参数在整个`zexecute`中只定义一次。独立保守解释只传播当前调用帧明确声明的局部Enum/Bool，重新Decl清除旧值，全局状态、未知调用返回与整数运算均为top；逐PC汇合仅保留全部入边相同常量，循环达到不动点。核对实际切片不存在局部引用逃逸后，该更保守图仍排除列定86项root或方向，且无实际见证冲突。候选工具独立复跑输出逐字相同，候选SHA为`0b887777dc661da5e5743cb52718bba74a761df32f4891114170f77c0082baea`。

对应审查为`isla/target/float-support-review/final-coverage/vector/independent-enum-outer-review/review.json`，SHA为`8b40f7a847a8b32f8c622d05286e83a06eccd9d6992d7e2a83c36f291882a07f`。其中数值wrapper义务66项属于这86项的子集，不能重复计数；仅对FVFTYPE/VFUNARY1的具体caller义务生效，不泛化任意enum接口或把全source表标闭合。

### 348147 统一 IR 的布局 guard 静态复核

统一模型真实生成IR SHA为`348147f833432008d559be0e673dbd45982148b0750cd4533c68589a55aac061`。在`zencdec_backwards`及其infallible版本中，VMVRTYPE/VEXTTYPE四处guard各50条生成指令，删除SourceLoc、按出现序重命名局部变量并把目标PC相对化后，与1dcc逐字相同，外部异常出口均实际指向`arbitrary`。两个完整decoder各378处instruction构造顺序亦逐项相同，VMVR/VEXT分别保持第225/231零基索引。

真实顺序为：完整布局matcher为false则直接返回None；为true先做纯value解码和tuple取字段，再执行原`(Zve32x && SEW<=32) || (Zve64x && SEW<=64)`。两个enabled调用、各自短路的get_sew、阈值32/64、异常检查和最终构造都保留；不能误写成只有Zve32x一臂，或声称value解码在when之后。两个完整matcher本体仍各0 jump、0 eq_bits。

证据目录`isla/target/float-solve-evidence/decoder-layout-negate/full-ir-348147-review/`，`review.json` SHA为`8d545f0d6729428254acbe5195b48449555b94afdc1826aeb5a68177c6ac18ab`。这只放行完整生成IR的布局/guard静态门槛；运行时sidecar、新IR同预算性能、77项全终态及状态重放另验。v6遗漏CPP平台源码的构建问题不改变此次Sail源与IR，其来源修订见[统一后端计划](unified-backend-plan.md)。

### BF共享V控制的补充独审

1dcc的22个短路site及1个overlap-if已完成机械独审：22个条件唯一def均支配对应Jump，21个lhs的SourceLoc按实际源码字节核对，余一项追溯`valid_sew`别名链；370条具体witness逐共有字段、scope/phase/config及root context核对。生产工具独立复跑输出逐字一致，放行145条短路actual与10条既审overlap actual。证据`isla/target/float-support-review/final-coverage/bf16/shortcircuit-proofs/independent-20260927/independent-review.json` SHA `9bf0ae835e4ad4deeef36b3b497d816c9fc140b76790f0b8506657b2a026d047`。

8个`write_vreg_default` cut另用独立证书证明：默认`__isla_use_extra_ops=true`、四个真实write root、10个不可变flag引用和wrapper/callee闭包共同排除该路径；flag=false负控实际可到默认分支。证书`bf16/independent-write-default-cut-review/certificate.json` SHA `3e676ee5139a1196f3a0f125672e4301e378f9d9a85e1b5c8f429e3bd7d39670`。这没有借用原371项typed forwarding结论扩大范围。

另73个caller参数义务中的70个域排除已分两包独审：32个能力/状态域及38个typed/overlap域。后者SHA `794f93c009e04ba14e1b7d9bc43905a1ee0a3fd5354f213b13244b3c8c17775c`，重新核四个BF decoder仅接受SEW16、同寄存器execute、canonical R1的vill对应SEW8及vtype无写。3个确实可达的Illegal前沿继续要求真实见证，未用静态域证书删除。以上证据均只绑定1dcc，迁往348147必须重新绑定并验证。

### 348147 同预算诊断与下一轮最小修改

两个真实代表在原outer/solve/SMT=300/270/30秒、每目标2 worker、完整decoder/R1/trace下仍以124结束，没有最终JSON。FVVMATYPE日志为0 Retire、4014 Illegal、3 non-encodable；F_MADD_TYPE_D为2826 Retire、633 Illegal、4 non-encodable。FMA完整trace只有2825 Retire，外限附近少1条，原差异保留。详细逐版本口径、精确前缀与合同见`isla/target/float-solve-evidence/unified-performance-review/review.md`，不能把局部终态数改称完成数。

此前修复的真实效果已确认：VMVR/VEXT外层成员分叉从1263降至0，D取负分叉从2539降至0。新V全部已完成execute仍处于前置Illegal域，没有`read_vreg/read_vmask/init_masked_result`或FP数值前沿；mask后续与RM检查仍分别产生1788/2184实际FORK。新D的AMO成员匹配仍3840实际FORK，动态RM为4788。新旧并行批次规模不同，没有据这些计数声称加速倍数。

根代理按既有授权批准两个小包继续实施、独审后合批冻结：

- **V纯合法性闭包：** 仅`vext_utils_insts.sail`的`valid_vtype/valid_rd_mask`及`vext_fp_utils_insts.sail`的`valid_fp_op/illegal_fp_normal`四函数。四者在完整typed域total、只读，使用已有strict Bool与`eq_anything`，寄存器索引复用`vregidx_bits`，普通与SYMBOLIC共用定义。旧新证明覆盖完整vtype、vd/vm、四SEW及全部8个RM；不删SEW=8或RM非法值。调用点后续`valid_reg_group`短路、LMUL/长度/断言、guard与execute次序均保留。
- **AMO完整格式matcher：** 仅`extensions/A/zaamo_insts.sail`的编码布局。完整bits32域包含固定opcode、十个op、五个width与三寄存器的E配置约束；`encdec_reg`不能当作恒true。value字段及顺序、非法value失败、全部正反向payload须证明一致；`amo_encoding_valid`含保留的Fatal域，只能在格式成功、value解码后按原when调用。opcode不匹配但携带Fatal字段的输入不得提前触发Fatal。访存execute与独立内存工作树不属于本包。

两包均要求真实旧源生成结构红例、旧新完整域证明、普通/SYMBOLIC严格检查及新全IR控制关系复核。它们目前为实施中，不能预写性能PASS；LMUL形状消费与动态RM枚举value继续单列，不用延长预算或缩小输入域代替修复。

AMO正向编码另有raw整数擦除边界：旧348147的`width_enc_wide_forwards`对1/2/4/8分别返回000/001/010/011，对其余全部`%i64`值返回100，不仅仅是Sail有限域中的16。实际完整`encdec_forwards`在AMO块先调用`amo_encoding_valid`，其异常/false分支处理后才调用width value；旧完整IR未发射`width_enc_wide_forwards_matches`及`encdec_forwards_matches`。新布局不能额外增加raw width成员拒绝，也不能只用有限typed tuple证明冒充完整公共IR关系。增补合同绑定旧真实IR片段，见`isla/target/float-solve-evidence/unified-performance-review/amo-raw-forward-addendum.json`，SHA `c110e1f489b13229887f534e266b4c44a02f4efb8450a58f56eab10504ece105`；实现包须验证未知完整i64正向返回/异常关系及guard先后，额外preserve的小IR matches接口须单列范围。

### 性能对照预算与完整验收预算

300/270/30秒（outer/solve/SMT）是本轮同条件性能对照，用户没有把300秒规定为最终验收上限。该参数继续用于旧新代表比较，历史超时保持失败。全77的验收要求是完整输入域下自然完成、输出守恒、无未解释错误及完整重放/源码分支闭合，不能因达到自设对照时限而结束任务。

后续候选若已证明冗余分叉消失或减少，并在新trace中进入合法数值前沿、可将剩余工作归因于有限输入分支且日志没有新的错误，可另开更长的完整运行。届时按目标的实际进度、分叉前沿、日志体量与机器资源明确配置outer/solve时限、并行度及证据目录；SMT保护的调整亦须另有慢查询证据，不能顺带取消watchdog。更长运行保持全部输入、R1、完整decoder、全部日志和状态，不采用采样或跳过未完成目标。

两种运行分别记账：同预算代表支持性能差分，更长完整批支持自然收敛验收。增加预算本身不是优化证据；发生timeout、unknown、Dead、缺JSON或守恒缺口的目标继续列未通过。本条沿用既有用户授权，无需再次请求实施或运行许可；具体更长批的数值预算将在新的代表trace审定后记录，不预先把当前348147的超时改为通过。

### V四函数组件放行

上述V包已完成实施与独审，源码`vext_utils_insts.sail` SHA为`72d1b65b7fc0d5e01337536c24feeac57324bf1015a6639937b9d594de0e49a9`，`vext_fp_utils_insts.sail` SHA为`7986553706b63fe3b9a24f39360328d3619a0ec0aa21ea3e4c49890fc746a797`。除四个指定函数及其解释注释，整文件相对编辑前驱不变；真实348147四个旧函数与小IR旧函数在去SourceLoc及单元参数名后逐字相同。

独立从源码重建并重放旧新关系，四SEW共60条旧SAT路径的四Bool结果及vtype状态差异均UNSAT。另补独立新实现域检查：每个SEW恰1条SAT路径，bits64/5/1/3四输入保持独立、没有Assert或Fork约束，SMT定义无环；全部返回逐一对独立四Bool规格及状态关系证明差异UNSAT。将实际IR的mask函数故意改为恒true，负控exit101并报告对应规格差异。新六函数闭包零Jump/goto、零主动位串相等查询；普通CPP共享strict发射、syntax检查及两模式strict均通过。

证据`isla/target/float-solve-evidence/fp-legality-20260927/independent-review/review.json` SHA `42f923e58f7751254bbb78c243efa3e00eb519710b836450a6a13da21d69c3fa`，状态`PASS_COMPONENT_ONLY`。这放行合批生成，不代表新完整IR、其它调用者的整体执行或300秒代表已通过；后续集成仍核源区域、R1、guard与Illegal两臂。

### AMO完整布局组件放行

AMO包随后完成实施与独审，`extensions/A/zaamo_insts.sail` SHA为`f381d25cbb7a8126e55114d021130dfdb690ebdc3fdf96afb5eb625adcffd0ac`。实际guard与op mapping前缀、ordinary clause及包含整个execute的后缀相对348147冻结源逐字不变，只改SYMBOLIC布局。独立重建runner并重放，非E/E两模式分别209/212行结果与实施证据逐字一致；整个bits32布局接受域、完整constructor/payload关系均已核对。将新op matcher改恒true的真实IR负控因非法op进入部分value而报MatchFailure并退出-6，审查器正确拒绝，没有把它记作差异SAT。

正向值关系另独立展开旧top encoder与新top→layout，七个自由typed payload的原helper实参及调用顺序、七次concat所得无解释表达式完全相同。size保持任意raw `%i64`；旧新四个op/width value helper在去SourceLoc后均与348147真实全IR逐字相同。由该结构组合补齐固定payload的raw size动态测试范围，保留旧size非1/2/4/8全部fallback100；不能把额外preserve的小IR matches接口称为生产全IR既有接口。

独审报告位于`isla/target/float-solve-evidence/amo-layout-20260927/independent-review/review.json`，SHA `def637826c946f9defdf7532fdf8302deb2038a94ca8e2ba8e78e9880ac4ac63`；对应说明SHA `0d64315d54385eb5d3b427a146712bc1306e187248700a594bd2c0c3d521c7ab`。报告状态为`PASS_COMPONENT_ONLY`，绑定实施manifest `3278ca95d8cbca260ef4f23229f647507e7ff74eb920d69ae626f258a93b0b7c`。小fixture的guard只是特定AMOCAS/size/寄存器组合的sentinel，不模拟真实扩展开关、XLEN、全部odd与reserved_behavior/Fatal；没有据此放行真实guard语义。

该结论允许V4与AMO合批冻结、并行生成下一版完整IR/CPP。新完整IR必须再验证真实`amo_encoding_valid`及异常出口、两个backwards decoder的matcher→部分value→when顺序、guard false后的fallthrough、其余constructor顺序，以及forward中真实guard及异常/false处理位于layout/width value之前；新完整matcher闭包亦须保持零Jump与零主动eq_bits。只有这些门槛和运行绑定齐备后才进入正式验收；生成阶段不切换主IR。同预算性能、全77自然完成与源码分支闭合均另验。

### 1dcc 的V数值宽度与合法宽度补审

28个root的37项数值宽度义务已独立审查：25项m16、9项get-scalar断言失败和3项scalar64臂，可在默认FD、P2合法译码constructor/fields、phase内vtype与内部flag不变、实际到达root的前提下排除。证据为`isla/target/float-support-review/final-coverage/vector/independent-numeric-width-review/widening-getscalar-review.json`，SHA `d130e1cebfa66aacce678cf287cff31aca6ce2ede45351e227dcd572dd783877`。审查重算173个未裁剪CFG支配关系，8项测试包含7项有效负控；producer复跑结果与候选逐字一致。

该审查收窄原候选的理由：没有采用“任意一次widening即可证明其它参数同m”的泛化。实际证书分别追溯转换返回32/64、negate切片和拼接、`read_vreg`按2×SEW切片及真实dispatch参数；`same_m_contract_used=false`。未知参数仍为unknown，例如RFWVVTYPE的op1，未补造约束。它是37个精确caller义务的条件排除，不证明raw全域、实际动态见证或V总表闭合。

另22个root各两个合法宽度site的44项排除已签独立证书，`vector/independent-valid-fp-width-review/certificate.json` SHA `ecabb90463fa5c9d237aa5d339340270501dffd6d9879deccdb9661fc6631af6`，与上段同属`final-coverage/`根。审查重新计算decoder宽度固定点、三阶段vtype无写闭包、实际首参get_sew的SSA来源与支配关系，以及execute分派前缀无状态操作和helper闭包的唯一目标调用。SEW×全部8个RM在真实typed CFG上核验，极性、SEW_new、FRM、SEW4、SEW128五项负控全部检出。

两包均仅绑定旧1dcc/default/R1及同一已译码输入。覆盖表按精确义务键分别消费并去重，不将各包相对于旧前沿的算术数字相加作为总数；两证书的`source_branch_closed`仍为false，不能转记348147或下一V4/AMO候选。

### 56cc 完整生成IR的V4与AMO结构门槛

下一候选已从931文件的完整冻结源码成功生成IR与CPP。stage为`isla/target/float-solve-evidence/unified-backend-build/model-v4-amo-20260927/`，`model-build.json` SHA `d6b825afde5af170332f79e9136f73db936e583fd8dbc1ae0806c61b05547259`；IR SHA `56cc69a44ee1acdb4cadf40a992283aa2084e281e85fbe88ab10a3153d9956ac`。主IR仍未切换，生成成功不代表77项验收成功。

V4完整IR证书为`isla/target/float-solve-evidence/fp-legality-20260927/full-ir-review/review.json`，SHA `afa7d1131679cf8f026bfe9d62e12d954e489e31a96bf0091b18ea66a86af687`。四函数及其签名与已独审小IR同形，真实六函数纯闭包零Jump；17个外部直接caller、整个`zexecute`、139个let/register初始化块和183个寄存器声明均与348147保持相同结构。全模型共有函数的执行逻辑变化恰为四个V函数及四个完整encdec入口；新加六个AMO布局helper，删除原op/width matcher，两旧matcher原caller均恰为两个完整backwards decoder。

源码移动也改变16处诊断位置参数；证书逐一核旧新冻结源码对应行相同后才按诊断坐标比较。其中AMO assert位置从67移动到124，`internal_error`的`__LINE__`从127移动到184；这些字面量变化被明确记录，没有全局抹去字符串或整数。两个比较器负控分别改变实际mask常量和execute调用目标，均保留差异。

AMO完整门槛见`isla/target/float-solve-evidence/amo-layout-20260927/independent-review/full-ir-review/gate-review.json`，SHA `cd6090cf64299f9f75419bf768ac30e378885d3cf9d1384c98608a1f9273d0d6`。真实guard的38函数闭包、相关let和保护签名保持同形，六个新helper与已审RV64组件一致；四个完整encoder/decoder去掉AMO区后重编号全部非AMO指令和跳转，逐项相同。56个抽象CFG场景覆盖完整格式真假组合、guard false/true/exception、七个自由payload和raw size，另两个接线负控均被拒绝。该证明使用真实guard与真实IR，不使用小fixture sentinel。

新两个backwards入口中实际顺序为matcher PC3737→部分value PC3742→真实guard PC3759；两个forward入口保持真实guard PC2434→layout value PC2441。严格region迁移、源目录绑定及实际运行仍为后续门槛：初次迁移因旧`valid_rd_mask`短路分支已消失而主动失败，不能以源码平移或仅换hash处理。

对此只授权退役`vexttype.toml`的原`region_fork_limits[0]`，文件`extensions/V/vext_utils_insts.sail`范围46:2–46:25、预算1。旧d012的`valid_rd_mask`与348147在去Loc/局部重命名后逐字同形，区域恰对应一个短路Jump；新整个函数及旧/新源码区域均零Jump、零monomorphize，并由V4全域证书证明结果相同。原配置、原表、三个IR、源码和两级V4证书一起绑定在`isla/target/float-solve-evidence/fp-legality-20260927/strict-region-retirement/certificate.json`，SHA `72e53ee25337720e50538a70ef9954a3d229bc01b559ad4a4c172431f1edc4fb`。

退役只删除这一表，不映射到strict返回位置，也不归档整个VEXTTYPE配置。77个active及2个旧archived配置不变；active region由130减为129，旧archived region仍2，新增retired region单列1。其余129项仍需原来的源码片段、IR分支函数/位置/极性核对，strict、全局fork预算和on-limit处理不变。初次FAIL保留，最终配置diff与迁移记录另审；该证书不能用作通用“找不到region则跳过”的许可。

最终配置独审已通过，证书`strict-region-retirement/final-config-review.json` SHA `0ab220295a38c393344752b710bbf985d9c2e4ff70e139b33ebab11efea72e8f`，与上段证据同根。独立重算79份配置的完整TOML投影，仅允许IR哈希、31项坐标及已签的一项退役；129区域的冻结源片段和真实IR Jump函数/相对位置/极性均相同，22个源码锚点有效。由此放行两代表，不把strict配置中的历史采样预算带进本轮正式全输入运行。

### 56cc代表结果与全77长批预算

同300/270/30秒、每目标2 worker、完整R1/decoder/ITRACE的代表运行位于`isla/target/float-solve-evidence/representatives-56cc-20260927-061428/`。F_MADD_TYPE_D约86.50秒自然退出0，1096终态为840 Retire、252 Illegal、4 non-encodable，产生1092条gen。FVVMATYPE仍外限124，但完整3409终态中已有53 Retire、3353 Illegal、3 non-encodable；log与trace的case/status/phase/signature逐项一致，无缺尾或重复。这些是两个目标的结果，不作为全77通过。

V的388个完整终态已进入`read_vreg/read_vmask/init_masked_result`，53个退休终态实际调用数值helper和写回，foreach每例执行4或8次body并有一次exit；其中51个f16、2个f32，尚无f64退休证据。已改四函数和AMO旧matcher冗余分叉均为0；V的6802个实际fork主要包括LMUL shape 2739、聚合Illegal判断2268、寄存器组587/69及vstart335。没有据此删除承担实际shape职责的LMUL逻辑。两个完整日志未发现panic、执行error、unknown、Dead、watchdog或SMT timeout，没有timeout-smt产物。

代表性能独审已冻结为该运行目录下`independent-performance-review/review.json`，SHA `b47106b038db565d0417fa5e4a0c142e93baf4fdce48324237d36086acc6fc20`。它重新核对515个Isla源文件、163个模型源文件、实际binary/IR和严格配置证书，逐case的日志与trace无孤立记录、重复、缺尾或字段差异。终态路径时间含共享祖先，不能累加为总CPU时间；本轮没有循环、LMUL、RM、SMT的分段耗时或剩余队列总量，也不能排除外限时尚有SMT调用在运行。

这些观察符合前述扩大自然收敛预算条件。下一独立56cc全77批使用outer **1800秒**、solve **1740秒**、SMT **30秒**，8个目标并行、每目标2 worker；SMT thread_interrupt、全输入/R1、完整decoder及ITRACE保持，不使用目标采样config。决策时机器128 CPU、可用内存约152GiB、数据盘剩余约2.1TiB，适合该并行度。此为6倍探索上限，不是已证明足够的完成时间；所有77重新运行并独立记账，逐自然完成目标继续完整重放。超时、unknown、Dead、缺JSON或守恒失败仍列未完成，不据部分退休路径补PASS。

长批runner已在`isla/target/float-solve-evidence/official-56cc-long-20260927-064348/`启动，先构建冻结的同源release再执行原77目标；预检`issues=[]`，manifest已固定上述参数及`qfaufbv`。实际make起止和逐目标结果以后续批次账本为准，不把runner启动写作目标完成。

### 56cc长批资源失败后的预算修订

上述8目标并行判断随后被实际内存增长推翻：长批中已观察单个isarch占用约17–28GiB，主机可用内存降至约22GiB、15GiB交换空间已满。`FVFTYPE`退出137，多个向量目标退出15且没有最终JSON；这些是异常退出，不能记成超时或PASS。已要求批次owner停止该stage的新目标调度并按确切进程归属收束活动实例，保留自然完成、异常退出和人为中断的独立记录。

当前只授权下一独立运行采用 **1个目标、每目标2 worker**，预算仍1800/1740/30秒，全输入/R1/decoder/ITRACE不变；先重跑FVFTYPE并每5秒采集RSS、VmHWM、MemAvailable。并行度恢复须依据实际峰值和余量，不能从空闲时内存直接外推。单目标仍可能持续增长，此设置不保证完成。

架构核查记录在该长批目录`architecture-resource-diagnosis/snapshot.json`。会话和用户cgroup的`oom/oom_kill`计数均为0，内核日志无读取权限，因此尚不能认定137的来源为内核OOM。退出15亦须核实际进程和运行器来源。源码另确认`run_ctrl_c.mk`使用全局`pkill -f target/release/isarch`，可能影响其它同名运行；已交独立owner修为本recipe的精确子进程清理并补真实信号测试，未据该风险认定它就是本轮失败原因。原失败stage保留，新运行使用冻结后的清理脚本。

后续只读独审`independent-memory-review/review.json` SHA `9575d5cd6bc240d6964d3a9b2b45c10ea2eef95f0a9b158094a7362d7a21360d`确认本机实际`timeout`是uutils 0.8.0：子进程exit(15)和SIGTERM都包装为15，旧日志无法区分；真实链接Z3的默认error handler对三个已探测错误码均exit1。冻结源码中无界任务队列持有Frame/Checkpoint、itrace前缀在freeze/unfreeze深拷贝、终态物化结果保留到全任务结束，后台文本队列也无界；本轮尚未测出各项占用比例。后续结构共享方案只设计、不实施，等待单目标采样和复制计数证据。

清理修复先验证了更小的本地trap方案。实际uutils可清理普通或直接忽略TERM的child，但当child先退出、grandchild忽略TERM时，timeout返回124后留下grandchild，`kill-after`不能再收束；精确探针见`isla/target/float-solve-evidence/solve-process-cleanup-20260927/timeout-probe.json`。因此只授权一个本目标监督器：保护未回收的timeout leader，清理其专属进程组，保留原timeout argv与退出分类；不扫描其它运行、不建立通用注册框架。手动清理要求明确PID并核对本cwd及进程身份，真实兄弟/异目录同名进程负控仍须通过。

修复已实现并经架构实际复跑10项信号/进程测试通过。该证据目录`architecture-review/review.json` SHA `306ce57fa41b3af5548fc18c4c0cee473cc70f37229b365266eb58b4bdec849c`重算原510文件，仅`run.mk/run_ctrl_c.mk`改变，其余508文件包括全部Rust仍同字节；新增`solve_process.py`与测试另列。正常timeout返回0/7/15/124保持，监督器受外部INT/TERM则分别返回130/143并记录原子进程wait结果；主动脱离进程组的子孙和对监督器的SIGKILL不在合同内。该证书只放行新批运行脚本，不证明原异常退出的原因或单目标收敛。

下一单目标诊断位于`isla/target/float-solve-evidence/fvftype-j1-56cc-20260927-084800/`，仍使用56cc、全输入、2 worker和完整trace。FVFTYPE运行697.15秒后因资源压力主动停止，RSS/HWM达到125,275,944KiB（约119.5GiB），仅生成4801 Illegal及3 non-encodable终态、没有Retire和最终JSON。监督器明确记录外部TERM、子timeout最终SIGKILL、只清理自身进程组，最终143；这不是自然超时或完整目标结果。52个资源采样从运行约7分18秒后开始，早期峰值轨迹缺失须保留；后续诊断必须从启动前采样，并自动执行RSS 96GiB或主机MemAvailable 48GiB的停止阈值，避免等待人工轮次造成超限。

单目标结果推翻“仅降并发即可跑完”的设想。已授权仅在`itrace.rs`实现三处观察序列的不可变前缀共享，`executor.rs/frame.rs`仅适配读取API和测试；不改变调度、求解域、SMT、collector或writer。复制计数、真实Frame父子独立、前向输出逐字一致及析构门槛先验证，再冻结新运行时做同目标资源对照。此时仍不能宣称它解决全部内存增长。

实施包已冻结于`isla/target/float-solve-evidence/itrace-sharing-20260927/`，manifest SHA `b1fef6f2a0ff927989e906e440e1fd8f3e1faec8f9fdb41a3efdc37ce4c44e66`。72项itrace与2项IR缓存集成门槛通过，4096条前缀克隆64次的record复制由262144降为0，Backtrace元素复制由2097152降为0；首次追加亦无payload复制。full/compact输出与冻结旧Vec渲染器逐字相同，真实Frame共享与独立追加、10万chunk小栈析构和并发读取均列入测试。生产executor/frame执行逻辑保持同字节；独立语义审查及实际RSS对照仍待完成。

独审随后冻结于原长批目录`independent-memory-review/trace-sharing-independent-review/review.json`，SHA `7a36af3573e2b8ec6cb4c23ee9f13125e34a20926adfbbb6e82a90f255ffddec`，放行组件语义。三份完整源码及24包产物逐项绑定，executor/frame生产逐字同编辑前驱，itrace生产改动限于存储、reader和compact统计；旧Vec参考renderer的526/539个token均与前驱一致，字符串未归一化。72+2原门槛独立复跑通过，另外30,000次随机操作、非Clone元素边界及24轮8线程深链小栈同步析构通过；递归析构和逆序负控均被拒绝。该证书不签完整新runtime/release或RSS收益，实际资源对照仍按前述单目标自动止损合同运行。

新运行`isla/target/float-solve-evidence/fvftype-sharedtrace-j1-56cc-20260927-080749/`随后完成预算对照，实际make于00:27:12Z启动，binary SHA `0c73a17e6cf289b0b0827b2526bdb862c781fd8ff9dcd2751fc298c8c1b7cce3`。FVFTYPE仍外限124，监督器耗时1805.04秒，无外部停止或资源阈值触发；局部25,010终态为17 Retire、24,990 Illegal及3 non-encodable，无最终JSON，trace约28.924GB。监测从spawn前开始，345个采样点的峰值RSS为36,453,884KiB（约34.8GiB），最低MemAvailable为110,846,708KiB（约105.7GiB）。相对于旧单目标697秒达到119.5GiB并人为停止，已看到实际资源改善；自然收敛仍失败，不把17条退休补为目标PASS。

最终只读对照记录为该运行`performance-observation-final/review.json` SHA `92aa2a42ea685490aa25e0465e46fada0d92cb0df29a7fb4fe800f4ac34d655d`。完整log有71,468条location FORK，25,010终态与trace五元组逐项守恒；146,336,129条edge的invalid计数为0，trace尾完整。日志未发现panic、执行error、SMT timeout、unsat或采样模式；外限停止和未生成JSON仍是本目标失败事实。没有原子停机任务清单，未签精确剩余任务或时间预测。

同一运行23分45秒的固定log前缀已有57,105条location FORK，其中`assert_lmul_pow`为38,815、FVFTYPE外层Illegal聚合为16,003。源catalog核到这些真实函数/PC，剩余队列无现成计数；创建减已报告终态不能当精确队列或ETA。LMUL的具体形状和后续fractional LMUL效果不能删除；下一候选先审纯caller聚合是否可由strict Bool保持相同返回域，保留原形状求值和断言位置。其余未完目标可用同冻结runtime、j1×2及既定资源保护继续，优先旧版本已自然完成且新批未启动的目标，不因一个FVFTYPE阻塞全部51项。

最小caller实施界限已审定，依据该运行`architecture-frontier-review/review.md` SHA `bb1970f98e4be9e0a72182822064a9dfbddf4c1e00f17d5e996677816a89d275`。唯一生产文件为`sail-riscv/model/extensions/V/vext_fp_insts.sail`，仅改SYMBOLIC的FVFTYPE两处表达式：slide overlap用`strict_and_bool`组合对funct6及两个寄存器位串的`eq_anything`；四个Illegal因子用嵌套`strict_or_bool`聚合，仍由原最终if区分Illegal和合法续体。实际旧IR中间caller分叉为PC29117、29126、29134、29142，最终PC29154必须保留。普通clause、其它caller、全局`valid_reg_group`及所有mapping保持。

当前caller的LMUL已经由原getter/assert限定为[-3,3]，组大小为1/2/4/8，额外求值的`valid_reg_group`在此域内纯且总；不能将结论推广到该函数任意int公共域。`get_num_elem`仍在guard之前，内部LMUL/SEW/VLEN断言、pow及长度具体化全部原位置。小IR先证明完整typed旧新Bool及状态/异常关系、实际中间caller分叉消退和普通/SYMBOLIC严格检查；独审放行后才生成同源完整IR/CPP并重新绑定配置和重放。strict提前计算其它因子可能增加内部成本，性能不预设通过，不在这一步顺带改NaN unbox或LMUL。

组件已获独审放行，证书`isla/target/float-solve-evidence/fvftype-caller-pure-20260927/independent-review/certificate.json` SHA `e4631adb5e7c5a3ef211e0dea48ffbf03dd6b7bfa319f08248f8ede4d2c2b965`，状态仅为`PASS_COMPONENT_ONLY_FOR_FULL_MODEL_BUILD`。独立重跑364个typed形状、1,040条旧新SAT路径的Bool/state差异UNSAT；364个新guard入口各一条无Fork、无非平凡Assert/UF路径，560项Isla与516项CPP边界通过。旧guard四数据Jump降为零，boundary最终Illegal/正常的一条仍在；LMUL七条、SEW四条及group内部一条保留。整文件2,697行不变，除两表达式外逐字一致，主动`eq_bits`注入负控被拒绝。旧PC29126的16,003次fork中仍包含必须保留的合法性区分，不能全算作预期节省；新完整IR及实际性能另验。

同源完整模型随后构建成功，新IR为`e6a3232d3858412c8283a1f6a08c8e0404493197a46f6aeec645b8796497d27e`，931文件输入manifest SHA `c1534a220c04cedf3a75144c7fa3d68cd171d59c89bd7e4156cff09fff056560`。同目录`independent-full-ir-review/certificate.json` SHA `dcb524a9f634c9e62b6718cc710641ceaeb08d2ce59795f1beb1a0f4a56dd179`核对2,057函数，规范化后仅`execute`改变；29,113行前缀及23,004行后缀分别同形，32行新guard与已签小IR逐条接线，最终true进入Illegal、false进入正常续体。普通CPP、头、schema及SoftFloat与56cc逐字相同。初审两段独立变量归一化未充分约束跨区段身份，随后`cross-boundary-review.json` SHA `9590c21787c0d440ef915c100dfd0a6d7b82493562a52a7e4227cc358663bf55`以同一双向映射贯穿前后段：前缀12,260名延续到全函数22,494名，9个实际跨区输入与唯一中段unit结果保持；6项替换、拆名和合并负控均拒绝。完整结构门已通过。strict/source最终独审`independent-strict-source-review/certificate.json` SHA `7681cf6bb212c93d1013a84adc69151ef9cb4c573c806ec23bac23fb01d5464e`绑定v2 freeze `4a855f8536106e6257c81a8458366f9072dc405477940b2516bf1d4d54c90287`，核1,176依赖及13负控，允许新候选进入既定资源保护下的实际对照。独审纠正原报告的overlap口径：129个保留region中127实际非空，`vxtype.toml`的`region_fork_limits[7]/[8]`在56cc和e6a都未选中任何指令，不能再称129全部有效。运行器真实selector排除严格包围范围的位置，旧新实际422引用完全等价；producer overlap的470含48个此类排除。两处历史无效限制原样保留、新增退役0；若要让其生效须另审语义变更，不在本次迁移静默修坐标。实际运行、性能和重放仍另验。

新sharedtrace家族流水随后完成23个此前未启动目标。跨stage索引`isla/target/float-solve-evidence/single-family-queue-20260927-014615/aggregate-completed-56cc.json` SHA `fb6cb9158efb5256da7fd580bf27fe3f2cb47595210a9e8176b78a5ca7237b93`精确去重为50/77自然完成：旧批26、已审D代表1及新23互不重叠。它不是单次全77运行或语义PASS；新23继续用新observer逐条重放。剩余27先按H/S FMA、H/S/D BIN_RM、VFMERGE/VFMV顺序，以同56cc、j1×2、1800/1740/30及既定资源保护继续；较大FVFTYPE另等新候选完整验证。第二队列随后完成前五项（H/S FMA及H/S/D BIN_RM），跨stage自然库存升为55/77；VFMERGE和VFMV在这一checkpoint尚未计入。前五条索引逐字封存于`fvftype-caller-pure-20260927/architecture-live-observations/20260927T031414Z/family-second-five.checkpoint.jsonl`（同证据根），SHA `ad0413294f522665404b399e0e8e1648899817eeecacdd7fdd5af080a628f313`；原队列索引继续追加，不能把现时路径当冻结五条来源。自然结束与后续重放分别报告。

新增两BF16转换在消费时被输入审计拒绝：runner及完整trace均通过，窄化126条、宽化265条LLVM拒绝操作数记录尚缺逐条非法守卫证据，合391条。拒绝发生在prepare阶段，尚未执行相应1,119及1,308输入的双后端重放；既非数值反例，也不能因solve退出0而忽略。修复仅补冻结56cc源码下原word、文本、真实Illegal返回及mask重叠/宽化同base守卫审核，汇编器拒绝本身不构成ISA非法证明。原失败日志保留，补审与后续完整重放分别签收。随后独审`unified-backend-cpp-replay/sharedtrace-incremental-56cc69-20260927/independent-bf16-illegal-operands-review/certificate.json`（位于`isla/target/float-solve-evidence/`）SHA `25d0d16a88c8fae523fdff206bff83020c3e787c69aa87ad499081414d54215f`逐条核391个原word、文本、requested/decoded AST和真实Illegal返回；窄126全为mask重叠，宽265为157同base诊断及108mask诊断，其中18条两个guard均真。独立LLVM391次诊断逐字一致，未匹配及额外记录0，16项负控拒绝；仅放行这391条汇编类别证据，2,427条完整重放仍另签。

止损时另发现手动入口的解释器依赖：PATH中的miniconda Python 3.13.9缺`os.pidfd_open`，系统`/usr/bin/python3`两项pidfd接口均存在；旧10测试及make使用系统解释器，未覆盖显式`python3 script.py`绕过shebang的调用。该入口主动拒绝，没有退回全局清理。已安排单独兼容修复：执行任何run/kill前固定重启到系统解释器，并用两实际解释器组合验证；不放宽目标进程身份，也不引入不安全的PID发送替代。

兼容修复随后通过12项测试，架构另重跑四种解释器启动/停止组合及错误脚本、缺各pidfd接口负控。证据`solve-process-cleanup-20260927/python-compat/architecture-review.json` SHA `f3216c10870c0d8bd1cd0ca21cfb4ced5f625707842c2654ec58ad1daad4b3f7`；新`solve_process.py` SHA `48aedd3ed6a8e5d0f6c16fcd9ba265d236cd87a32551a904a608f071deafaf4b`。重启在创建child和发送信号前完成，argv、cwd与环境保持，仍先打开pidfd再核精确归属；系统解释器或pidfd不可用时明确失败。

### 隐式异常变量的纯读审查修订

新四配置decode/encode纯读独审发现，原checker只登记IR的`Def::Register/Def::Let`，漏掉`LocalFrame::new`注入的`HAVE_EXCEPTION/CURRENT_EXCEPTION/THROW_LOCATION`。真实闭包含三个`internal_error`特化及`reserved_behavior`的12处写；调用栈只恢复局部vars，不恢复lets，`Arbitrary`可返回Poison后继续执行，因此不能把这些写直接归为永不返回的路径。完整闭包“所有let零写”的结论必须降格，原FAIL和版本留存。

相同漏项影响已签双后端重放的纯读前提；既有数值、102架构字段、8初始化let和15aux逐项匹配仍是实际结果，但不能由它们推出三个异常临时变量沿途未写。正常End域可另按完整CFG、实际exception guard与跨调用write-ever固定点证明；这类证明不能删除`Arbitrary`续体或handled异常路径，旧IR亦不能自动迁用。

已授权重放owner在新隔离observer快照中仅为`frame.rs`增加`tracetool`门控的只读指令trace借用接口，并令隔离runner启用该feature。生产与原候选不改，getter及编译feature的来源差分另记。原准备记录曾将三包的观察阶段写为decode/encode；实际冻结runner调用的是`ext_decode`和`execute`，现据源码及组级独审更正。每phase记录三个异常变量的typed初末值和沿途实际写点/次数，写后恢复也须检出；完整opcode与Loc及未知间接目标继续严格核对。18,584历史输入、1,096新D代表及6,230新长批输出均不抽样。长批中的13个encoder来源负例在此是decode/execute重放输入，真实encoder观察须消费专项证据，不能由三包替代。

正常域固定点证书随后完成，位于`isla/target/float-support-review/final-coverage/integration/p1-56cc69/scalar/independent-phase-purity-review/certificate.json`，SHA `7f60693560ae1733d76305313876378a3a76ef1725511f77d9e969f85241b648`。它保留未知条件双边、真实exception guard、所有Call和Arbitrary续体及跨调用write-ever；初始have_exception=false时，正常End必无隐式异常写，异常Arbitrary域仍单列。三个scratch的读取初始化、shadow与特殊原语作用也已核查，完整闭包纯读状态仍为FAIL。

重放独审已消费该限定证明，重新核对实际runner初始have_exception=false、无shadow、SAT及Finished非Poison的Ctor/Bits返回。消费证书`.tmp/unified-backend-cpp-replay-independent-official-wave001-56cc69/normal-return-consumption.json` SHA `4cbc8ca93539128681c8358055b20c29d43026ef2f0ebdfb5b9df65d0a54e521`绑定6401文件；历史348147/56cc各18,584记录、新D的1,096记录与长批6,230记录恢复为正常返回限定的重放结论。它不签异常路径，亦不替代新observer逐记录观察。

D组observer已完成1,096输入，独审核对2,192 phase及19,715,227条指令访问，三个scratch初末相等且沿途零写，完整旧新Isla字段一致。证书`isla/target/float-solve-evidence/replay-scratch-observer-20260927/independent-review/official-d-1096.json` SHA `2464f2535a292cb4a627ef71db99a0a03cad516fb4e8584da362e8e5e3a04740`绑定summary与41文件index，只签observer观察及不扰动门槛，CPP逐值独审另列。实际单worker峰值约208MiB。因此余下两包允许改为4个独立worker、每片CPP1：完整Model保持独立进程，各片输出独立，原记录键不重编号，聚合时输入必须恰分区一次且重复、缺失或错误一律失败。单worker是原资源保守策略，非语义前提；新调度另记manifest，不覆盖旧计划。与单目标solve共用主机资源保护，仍逐phase释放且不采样。

长批6,230输入随后完成同一观察门槛，12,460个decode/execute phase、212,000,423条指令访问，三个scratch沿途写0且完整旧新Isla字段一致。组证书`official-wave001-6230.json` SHA `b5d3df2c764375b70ec5ad4d9aade5c654c88e267d99cfdc56b9e97c9d5ca079`及聚合附证`official-wave001-6230-merged.json` SHA `772b44728a857a1c440d8ed7494c940c2e6a3b3ed8b35948811a768ea205047d`与D证书同目录，重核2,280文件及7片报告；历史18,584包仍以其最终证据为准。

三包最终观察证书已封存，同目录`certificate.json` SHA `9adba11b135b3e754eaf7c46dad41b51138a3dc0c2071de42ff7a4da0d647365`；2,806文件最终绑定索引SHA `36a5d3c9ddbb8d9ffb39a53a5165690ccffc78f05e3bf29f97a3d1f4494618f1`。总25,910原输入、51,820个decode/execute phase、779,354,630指令访问，三个scratch初末值相等且沿途写0，完整旧新Isla语义字段一致。13个encoder专项补证`encoder13-review.json` SHA `b49d5c3fa269a62066c960eb9dd105c64b53d7971ea852a32903a90ab6a01972`另签26 phase、261,802访问，不计入三包。四worker退出及来源核验通过；旧协调器转接exit1、未保存原outer raw日志的限制仍记录。CPP逐值结论独立，完整闭包12写、未完成77及源码未闭合状态保留。

新sharedtrace runtime到旧observer的精确来源桥未通过，证据`isla/target/float-solve-evidence/itrace-sharing-20260927/independent-runtime-observer-bridge/old-observer-bridge-fail.json` SHA `f25f1838a9903fa2df2420d077f9df895872fa8bf19f3feaf2e6350c01a94a7a`。阻断是旧observer独立Cargo.lock实际解析到较新的num-bigint、num-traits、crossbeam、libc及serde_json；不是发现了数值反例，旧重放保持原适用范围。已授权从真实新stage复制隔离snapshot，仅增加同一只读getter及根Cargo.toml的runner bin；现有三项依赖根package本已具备，根锁保持逐字不变，以`--locked`构建。新序列API要求getter返回引用数组，runner只做对应借用迭代适配，payload不克隆且每phase释放。未来新官方输出必须由新冻结observer逐条实际重放，不把旧25,910结果换hash迁移，也不为该无关变化重复旧输入。

该新observer已完成来源桥独审，`new-observer-bridge-review.json` SHA `309dc98ecb73a401b2b6c82f83b4c0513cd377b1500f9293dab4201df5183ef5`与前段FAIL同目录。517/518源等集核验、根锁150解析节点及实际229外部依赖一致，差分仅根bin、getter及借用适配；20测试和73 smoke通过，146 phase及1,672,168访问的完整结果除elapsed逐项相同。隔离目录产生的`ISLA_VERSION`字符串不同，证书明确只签绑定的原始56cc IR，不签`.irx`缓存相容。未来记录仍逐条重放，旧25,910及源码动态见证不迁移。新sharedtrace家族23组随后完成独立全phase核验，`replay-scratch-observer-20260927/sharedtrace-independent-review/family23-certificate.json`（同证据根）SHA `dc88188a2f5c7667520c5d2878769e3f73d81e5561c51725ab4ac4fd2d0177b2`绑定9,692输入、19,384个decode/execute phase与260,610,144次指令访问，三个scratch初末typed值一致、沿途写0，全部ID恰好一次。辅助encoder13另为26 phase、186,986访问；20,447文件最终索引SHA `71362e02e6e8e5a8a6d9406b983a2bb7bd104b4362af68cf2fe36491dc2f7aee`。两BF16的2,427输入已在新目录实际完整重放，并消费391条精确assembly证；原两prepare失败与先封的21组证书保留。该独审签scratch观察和记录完整性，CPP逐值由另一证书签，不扩为源码闭合。

旧26个自然完成目标所属official stage与新solve另有来源对照附证`old26-new-solve-source-comparison.json` SHA `e7e881b7ee0a87d96230a8603625d3ae05d3797d83b4a8447d36a21b9bb182ba`，同目录。双方515/517文件，根锁、features、IR及FD配置同；已核差分仅三份trace/test源码、两清理mk及新增监督器与测试。因此旧26保留原runtime、结果hash和重放适用范围，后续表中与新运行分列，不能将它们称为新binary实际跑过。

### 56cc源码合同的当前收口边界

新BF短路剩余47项已完成独审，`bf16/independent-rhs-static47-review/certificate.json` SHA `1bcb196431dbc217840e126514b0471e0f2f280307044b09af34282bdb1fc9ff`（相对于上节`integration/p1-56cc69/`）。其中15个overlap及8个write在绑定caller域排除，4个decode及20个encode仅在正常phase条件下排除。47项与已签139个动态方向互斥，合为当前186项；无条件全源码排除为0。附证`return-dependency-review.json` SHA `52628de2a6b5be5d8599b9a9ca544d1dc66acb9b637c35a24470898602e740c7`补上结果相等但copy来源链切断的真实IR负控，不能只凭返回值相同接受错误来源。

当前归约Err2另以新IR重新核对两个实际caller。`vector/independent-reduction-err2-current-review/certificate.json` SHA `23ade870f800029f89b8103aa1a94dc3ffbe685e26e64b8fd0d21112b02b4fb8`只签RFVVTYPE的Call37578与RFWVVTYPE的Call37828正常返回后的Err方向排除。实际get_sew全部8值中0..3正常得到Ok0，4..7保留assert Exit；完整helper正常End仅由两处Ok构造抵达。动态新增为0，不证明无异常或终止。

四配置scalar谓词及正常域最终独审为`scalar/independent-predicate-normal-domain-review/review-final-v6.json` SHA `c0eeb1af084bc1617b6e80c596478667061872fd8765ff22ee96f8f8cda96def`。每配置分别核19个正常谓词、15条固定能力路径、30个短路因子、4个64位getter、224个phase guard及120个phase因子；1,772个实际见证按本配置、本phase、本privilege和实际PC复核。v5在消费时因checker-hash门不符被拒绝，原证据保留；v6冻结实际checker并增加精确source site、trace边及逐arm条件和见证状态，四项当前负控被拒绝。结论要求guard实际到达、调用正常返回、该配置MISA及XLEN/FLEN64、求值期间原子稳定；异常和入口关系独立列项，未观察方向不补成动态覆盖。

后续优先复用共享合同。BF旧40键仅作历史跟踪，当前4个execute root经`illegal_fp_variable_width`调用`valid_fp_op/valid_rd_mask`的8个callee-instance才是当前集成义务；按实际typed实参、V4全域、正常返回和caller聚合极性验收，不为strict Bool中间值发明source branch。向量配置flag候选必须证明实际初始化覆盖优先级、SSA读取、所签phase闭包无写/Ref/Reset/特殊原语作用及root支配gate，不能由源码默认值加文本搜索认定固定。以上限定证书按精确键消费，均不表示全部源码或77目标已闭合。

BF八调用随后通过独审，`bf16/independent-v4-call-integration-review/review.json` SHA `e833094953c48d18a14194ebbf04c8422f825e8fd51563450c5553c24a9e7e2f`提供8个稳定key及逐项前提。独立核全部8个vsew及4个assert退出、64种mask和32种fp合法性组合、16种helper聚合及caller正常/异常极性，13测试含11有效负控。12函数479指令的局部作用核对不等于full-phase纯读，也不签LMUL、EEW或overlap的总性；新增branch、动态见证及全源码排除均为0。

标量34个未发射普通site在四配置完成限定独审，`scalar/independent-runtime-site-retirement34-review/certificate.json` SHA `7cd6a73df4a297ae9804ca619e17c7f0e775bb25bbdac04b840e577f2ab67a76`。每配置完整209个选定typed PC与全377,980个runtime PC核对、15负控通过，324依赖冻结后零漂移；34源site的136配置配对只签对应版本无runtime branch。`currentlyEnabled/Arbitrary`、r/w断言失败、实际活跃accrue宏分支、无loc及synthetic义务均保留。

另一组170个encode FS0方向只能在定向audit的“先成功decode，再从同R1克隆encode”入口域排除；官方wrapper实际为encode→decode→execute，FS0的non-encodable方向仍须保留。producer已另产明确audit-only候选，官方source方向删除数为0。审查和消费不得把此入口条件省略，不能以定向工具未执行某方向裁掉官方全输入义务。

该audit限定组合已独审封存于`scalar/independent-encode-entry-composition-review/certificate.json`，SHA `d5cea499ab36f65ef23bf8159d5e84b451a69ae5db685a2c0b898a97ceb19622`；170个audit-only正常入口排除与4个条件正常空方向分开，12测试通过、764绑定零漂移。官方170方向继续OPEN，完整phase纯读仍FAIL，动态新增0。

官方encode-first的直接观察随后单独补齐53个方向，证书`scalar/independent-official-encode-fs0-witness-review/certificate.json` SHA `6a67fc294ce70a1305c455fd624fa94902c6dda771b5345e6314bf1777dd6ac4`。它完整重核旧26目标的6,230终态及32,912,166条边，56见证引用对应33个唯一终态，实际栈由官方wrapper PC1到encoder末尾MatchFailure PC31276。53项为32个guard方向及21个短路LHS；其中20个AND跳过RHS，1个FLI_H内层OR进入RHS，后者不签RHS的值。剩余117在该包未观察，继续OPEN；这次只消费实际动态方向，不以audit入口排除删官方分母。

D代表另补8个直接方向，同目录`representative8-review.json` SHA `6cfe6a626b85fea684af95140a5d20839c2d40a0fc1da199c53ca4908e8039bd`完整重核1,096终态和3,418,976条边，4个实际non-encodable路径支持4个guard及4个AND LHS方向。与wave53精确键交集为零，合为61个直接方向、剩余109 OPEN。两组独立证据保留，静态分母删除为0，未升级RHS。


向量`get_num_elem`局部24项随后完成限定独审，`vector/independent-get-num-elem24-review/certificate.json` SHA `24cb812e4b12199fe46357e0823cc5d4fd8ecf80e8c16cfae58e8da8a4ecb90f`。实际50条指令中前置两个断言的正常返回支配目标比较；完整整数域证明、同一SEW/vlen值链及28条正常嵌套路径通过，7测试和9负控通过。仅允许当前default的24个精确fails方向与typed/参数算术附证联立排除；24个holds和全部前置异常保留，未限制root实参，不证明入口正常、全域终止或全部源码闭合。


四配置RM/FRM局部合同随后通过独审，`scalar/independent-rounding-domain-review/review.json` SHA `6107582e6101fe0e75ffa8a1939eb5eb61de708aa5f534617839a336b232f036`。每配置45个caller、21个clause，合8,640正常输入组合与2,160异常组合；12测试含11负控通过。实际top-level let的const_primops优先级、四配置无reserved-policy覆盖，以及377,980条runtime与1,910条setup/config无相关写或引用逃逸均已核。结论只到have_exception=false下None→Illegal_Instruction构造或Some→forward 0..4；true保留Arbitrary，backwards_infallible(5/6)确有未初始化读取，不赋成DYN或声称runtime拒绝，两处ROD6保留。无新增动态或静态排除授权，官方encode不能借audit成功decode前提。

BF官方encode另补4个精确caller方向，`bf16/independent-official-encode-fs0-review/certificate.json` SHA `38fb11907728aa4119444005a96ab6096d48acda917fb3d0b1471a25ab261b24`。两个旧终态各549条边完整重建至MatchFailure，5测试通过；4义务为2 guard及2个共享FS site的LHS方向，共3个global source site。与scalar61的所选global/caller集合无交集，选定caller方向并集65；scalar170分母剩109和BF186 RHS账保持各自范围，不用65跨账相减。新增运行、静态排除和RHS升级均为0。


三个alternate配置的FCLASS inf LHS另完成9个精确Machine caller独审，`scalar/independent-classify-inf-alternates-review/certificate.json` SHA `0974ad4d417b8b261a46659c8c503416e3f2418dcad97b0b8704efc71396f322`。各配置分别重验source-v3及629 roots，核159指令的局部确定性、同一bits的classifier/helper关系、8个Bool和false支配；臂反转、source span漂移及root参数错接负控拒绝。旧default3证书未改；新证仅允许typed非Poison正常调用域的9项LHS方向，RHS、异常、其它caller及动态增量均未授权。


Recip7/Rsqrt7的45项宽度/索引合同独审为`vector/independent-estimate-width45-review/certificate.json` SHA `e8dfa0ef976e420ff79d149096f0e65918823003ce17bbe56f6035afd75f92f3`，只签24固定格式、18 CLZ/unsigned边界及3个recip sub=false返回方向。独立解释器核6个实际root、31函数未剪枝闭包和15上下文，6测试及26负控通过；值宽从实际`read_vreg`正常成员及caller保存的SEW经`__id/eq`守卫取得，不从Decl伪造位宽或假定vtype跨调用保持。新增动态0，源码未闭合。


### e6a 实际对照的阶段性观察

新FVFTYPE于03:01:33Z启动，stage为`isla/target/float-solve-evidence/fvftype-caller-e6a-prepared-20260927/`。03:14:14Z的固定完整行前缀记录`fvftype-caller-pure-20260927/architecture-live-observations/20260927T031414Z/review.json` SHA `02cad3d9c3b46e578ad3ebeb2bef1d93d2563e2dd601963d585ce784153461d9`观察9 Retire、5,457 Illegal、3 non-encodable，峰RSS约16.9GiB。32,323条location FORK中LMUL断言16,122、最终Illegal guard 3,459；无已记录panic/SMT timeout等匹配，仍无完成结论。日志与资源前缀不是原子任务快照，不给剩余队列或ETA。

同目录`first-eight-terminal-review.json` SHA `258caac9698551c89a0b8896301967cf3821c2ecc59957f09d12a1c52ed541ff`固定首8完整终态及真实25,672条branch catalog。优化区实际catalog只保留PC29144，case3–8各通过该边进入Illegal，旧四条中间数据Jump不再存在；各7条LMUL已执行边不能直接叫7次SMT fork。无源码位置17420等实际属于`encdec_vfunary0_vs1_backwards_matches`，17582等属于`encdec_vfwunary0_vs1_backwards_matches`，不能误归到LMUL。比旧sharedtrace更早出现少量Retire，但分支调度和同时运行负载不同，尚不能宣称总收敛改善。下一步仅并行研究保持断言位置与异常关系的shape延迟、局部形状复用及上述mapping谓词，实施另按精确合同放行。

向量799个已有trace的源码语义随后补审通过，`vector/independent-typed-source-semantics799-review/certificate.json` SHA `01486cdff259d57740ba3be1eaf71a64c211ad7fa6648eef904acb813ca5d3cf`。5个site/12个源臂的operand、唯一SSA、实际比较及Not/Jump极性与源谓词独立对应；89个既有完整phase重核1,684,051指令并与原输入、返回链和逐claim身份联立，7测试及11负控通过。消费表用独立状态记录这799项，原87项保持；无新模型执行。结构与边的存在性本身不含源码谓词语义，不能跳过该门槛。


### 原生 Sail 源码目录的实施合同

BF分母词法v1独审发现private声明遗漏、foreach重复及bits运算误算短路。v3修订的限定证书为`bf16/independent-full-source-denominator-review/review.json` SHA `bbe7c86df8ed46f6fe2eefe5ddde7c21ca2c8a4072b42f127e6ebd90bf5e8b65`：223文件、172实际root、164整声明身份及列明修订可用，120个未解析声明、159个未认型operator和76个runtime leaf仍OPEN。该证不是完整795项分母证明。

同版本原生AST探针已验证两预处理域的类型和源码位置，`source-ast-probe/delivery.json` SHA `64e4d6ecdfe9da6dafe840dc0c2c1e8488ac5ef571e7c76c562f90fc38e499f4`。用户已授权完成原议题的全部分支审计，下一实现直接复用冻结Sail parser及target插件，不修改编译器安装或生产模型。实施owner独占`agents/float_support_review/tools/solve_source_ast_catalog/`及新的`integration/p1-56cc69/source-ast-full/`，初版以56cc冻结源和实际库为输入，e6a另建版本。

1. **physical/raw层：** 独立进程调用同版本`Initial_check.parse_file`，逐一解析冻结model与Sail库的实际文件；保留private包装、scattered声明、mapping两侧pattern/guard、编译pragma、全部表达式和位置树。注释/字符串由原生lexer处理。不得在已设宏进程再次运行共享全局状态的preprocessor。文件全集须来自实际构建输入和项目/include来源，不能由旧795表反推。
2. **typed层：** 普通及SYMBOLIC各独立进程，复用真实项目、变量、defines、库及配置；插件使用`skip_initial_rewrite=true`、空backend rewrites，在`pre_rewrites_hook`导出真实typed结构、定义/子节点角色与顺序、类型种类、callee及完整SourceLoc。记录它已经过descatter和配置处理；不得称为原始parser AST。private须联立同模块同id的`DEF_val`，不能因函数体被改成Public而丢失。
3. **完整遍历：** raw与typed的每种DEF、funcl/pattern、mapping左右guard、if/match、loop/foreach、assert/try、let/assignment、outcome、module及生成节点均有明确处理。编译器构造子清单与遍历覆盖联立，未知种类或无法遍历子节点明确拒绝完整性门；不得用忽略型通配分支。类型未解析与无物理位置的节点另表保留。Bool短路用真实And_bool/Or_bool及类型识别；and_vec/or_vec属于数据表达，不生成短路臂。
4. **source/typed对账：** key绑定源文件SHA、原始byte span、节点kind及结构路径；位置的Range/Generated/Unique/Hint树完整保留。descatter、合成val和类型展开允许一对多/多对一，只通过有具体来源的关系表联立，不仅按名称或相近行匹配。raw未进入某typed域的节点必须标明宏排除、生成/变换来源或OPEN，不能因未lower而删除源码。普通CPP域和各Isla配置/入口分别记账。
5. **调用与分母：** 用真实typed语法及环境区分callee、union constructor、类型名和内建形式，保留未解析项。按当前constructor/phase的真实clause或mapping arm起点求调用闭包，不把整个全局execute散列函数当每个root的入口。与现有172root、795词法site及既有证据逐键对账，差异列入新增、重复、数据表达、非活动域或未决；旧证书不改。最终分母完整性须在解析全集、语法遍历、宏域、source对应及调用边分类全部可解释之后单独独审，不能由导出成功推出。
6. **验证与交付：** 除已测private/注释/两类运算符/多行mapping，再覆盖nested comment、同名模块私有函数、scattered多臂、loop/foreach、try/assert、配置消退与多层位置节点；每类遗漏/错误归属的真实负控应使完整性门失败。绑定实际编译器/库/插件、全部输入与命令、两域输出和来源关系。先生成可审的新目录并给出与旧表差异，独审通过后消费方才更新分母或状态；此步骤不自动授予新的动态覆盖或静态不可达结论。


### 56cc后续完整重放与剩余运行

第二队列完成VFMV后，跨stage唯一自然完成为56/77、剩21，实际索引`isla/target/float-solve-evidence/single-family-queue-20260927-020959/aggregate-completed-56cc.json` SHA `b099be75847f47ae2858be58518970e5494157cf28553d608c86bb635312133e`。上文50及55项均保留为当时checkpoint，不能与新库存重复相加。旧26、D代表、新23和第二队列6各自按原runtime/日志及重放证据记账。

新23目标的9,692输入（9,624 gen、55 direct、13 derived）已完成CPP数值及AST/ret/102字段独审；总证`.tmp/unified-backend-cpp-replay-independent-sharedtrace-family-56cc69/final-audit.json` SHA `12a39845bf2e0ab8a2b1eca46255de4cacd595c4fb13efa054564f4537aec39d`与上述`dc88188a…`全phase证联立。两BF16的391条LLVM拒绝均有独立Sail guard证据，汇编器拒绝本身不作为ISA非法证明；原prepare失败仍保留。

第二队列原七目标中六个完成：H/S FMA、H/S/D BIN_RM及VFMV。32,795输入（32,772 gen、7 direct、16 derived）已完整重放，65,590 phase、661,435,785访问的scratch观察和CPP逐值均通过；`.tmp/unified-backend-cpp-replay-independent-sharedtrace-continuation-vfmv-56cc69/six-complete-one-timeout-audit.json` SHA `ae9fe916a260f685be161be6b5251c0deae6e9de08bda18ed87d21276713826c`。VFMERGE原外限124、无JSON且无完整配对，因此原七目标批次仍非全PASS。

VFMERGE原30分钟终态为6,312 Retire、21,172 Illegal及3 non-encodable；最后100条均Retire、后15分钟RSS平台约4.8GiB。实际最后5,000终态窗口未出现新的LMUL fork，晚期主要在SEW32的nan_unbox两臂，不能以LMUL候选代替该目标的运行预算。独立frontier证据位于原stage的`architecture-vfmerge-frontier-review/`，recommendation SHA `626981d263e8d9fa4236b8e6624d6a90091243e8ba7199ce279991219da0368c`；没有原子剩余队列或2小时完成保证。

据该实际资源证据，后续独立VFMERGE stage允许outer/solve/SMT为7200/7140/30秒，同时另一j1队列按RFVVTYPE、RFWVVTYPE、VFUNARY1顺序继续原预算。两者保持56cc冻结runtime、全输入、R1、完整trace及各2 worker，总并发最多2目标。每5秒从spawn前监测，RSS达到96GiB或主机MemAvailable降至48GiB时精确停止对应监督器；不清理无关进程。预算扩大与代码变化分开记账，不把新stage的结果覆盖原超时。 实际新stage为`isla/target/float-solve-evidence/vfmerge-2h-56cc-20260927-c/`，于03:56:47 UTC启动；另一队列`single-family-queue-20260927-035801/`（同证据根）已启动首项RFVVTYPE。04:18 UTC两者RSS分别4,915,260及20,890,204KiB，主机MemAvailable约123,299,660KiB，尚无新自然完成；此为运行中快照，不作最终性能结论。

### e6a对照结束与下一优化边界

上述03:14固定前缀随后到达30分钟外限，实际1805.23秒、124、无最终JSON。`fvftype-caller-e6a-prepared-20260927/evidence/fvftype-partial-trace-audit.json`（相对`isla/target/float-solve-evidence/`）SHA `d25388f214c761fcffe5e6b40aa62e1cc59c43f8929dbebfb6eb88811903b4a0`记录31 Retire、14,106 Illegal及3 non-encodable，共14,140终态；17,025,686,964字节trace含85,694,666边、invalid 0，日志与trace终态五元组双向守恒。345次资源采样峰RSS 32,320,264KiB（约30.8GiB）、最低MemAvailable 114,588,560KiB。两版均未自然完成，不能由17增至31 Retire签总收敛改善。

运行形状复核已确认现有eq恒值证明、Jump双SAT及分支约束避免同一路径同谓词重复fork。通用值缓存不能直接替代形状转换：symbolic `i128_to_i64`采用Extract(63,0)，concrete用`try_from`可能Overflow，传播`2^63`会改变错误行为；不能整移`get_num_elem`或跳过其断言。下一优化分成局部Sail membership组件，完成独审后合批构建：

- `assert_lmul_pow`保留完整整数成功集合-3..3、原失败断言及其`47:10–47:23`位置。因Sail generic整数相等受到singleton约束，候选复用已有`option(int)`包装，以七个`eq_anything`和六个`strict_or_bool`构成一个最终Jump。源层不新建类型，但实际IR新增单态union `zoptionzIizK`，必须列入结构审查。当前组件在`lmul-membership-probe-20260927/`，manifest SHA `c466d2eb1e581f6ec4bce6684f6d5b18c6549f3b6f30034d2b9298ddd27309f5`；组件测试不能代替完整模型构建及真实收敛。
- 四组unary mapping只改SYMBOLIC纯backwards matcher，保留forwards/backwards value原表和顺序，普通mapping不变；非法bits5仍为MatchFailure，外层guard与constructor不重排。合法码数量分别6、7、8、4，验收包含32码全枚举、全部enum、未知bits5单路径关系、真实完整decoder调用顺序。旧IR共25个matcher Jump，固定日志仅观察23个位置，不将后者扩称全25实际观察。

新e6a observer来源桥已独审通过，`unified-backend-cpp-replay/sharedtrace-e6a-source-bridge-20260927/independent-review/certificate.json`（同证据根）SHA `82c65038dcc1eed6859b7d1d37a7597ba9d2519b0cfbc54321a5950a709cff7c`。517源中IR及77 TOML精确78变化、439不变；该证只签原始e6a来源与runtime，不签`.irx`、初始化实际值或完整witness。原63条稀疏fixture必须从真实执行前保存pre-state，同一SAT终态Model一次物化完整pre/post/AST/ret及位宽，并保留全部已有具体初值；不能补零、借旧post或加方便初态。原6条decode-only与新增execute义务分列，初始化和数值重放另行独审。

### 原生AST完整结构导出与分母消费的两道门

全模型`source-ast-full/attempt-005/`已实际完成ordinary原cpp域与symbolic原isla域导出，分别exit 0、19.19/20.39秒，输出509,208,388及528,297,412字节。该状态尚未冻结为完整分母PASS。223个物理Sail文件中222个原生解析成功；冻结库`instr_kinds.sail`第64行的原始语法错误保留。两域成功openat、pre_initial项目文件及物理库存联立显示该文件均未选中，因此selected_raw_parse_pass为true、physical_raw_parse_pass为false；不能从typed中未出现便删除失败，也不能把物理库存等同实际编译输入。

第一道门签有限exporter包：真实target名称、原argv及前置hook转调、完整输入与工具链、构造子schema和遍历覆盖、两域全树及结构索引、selected-file证、完整位置树与负控。raw/typed索引保留defs、clauses、pattern、mapping、expr及所有控制子节点的原树路径；未知构造子或未遍历字段须使该门失败。private在typed合成val与函数体间联立。pattern application等尚无环境分类的记录保留OPEN，不阻塞交付已经完整序列化的语法结构。

第二道门在此结构上建立各真实clause/mapping root的源码分母：与172 root、795旧词法项逐键对账，处理callee/constructor/类型名、模块、宏域、配置消退、Generated/Hint来源和一多/多一关系。coverage可先使用原生结构替换regex发现与建立待审记录；有限exporter证不允许静默删除旧source/caller、增加动态覆盖、签静态排除或将denominator_complete置true。完整分母须待selected域解析、遍历、调用与source关系全部解释后单独独审，避免长期停在探针或补词法规则阶段。


### 局部优化已审与VFMERGE自然完成

LMUL独审已封存，`lmul-membership-probe-20260927/independent-review/certificate.json`（相对`isla/target/float-solve-evidence/`）SHA `543ed0fe122dcb68abb4d8e5c23640b92a9ff441c66548adf120a245ae2e9bb7`，515文件绑定。无界Int两关系及实际128位10分区查询UNSAT、34 Isla与54 GMP边界、5类真实可编译源突变通过；原公开整数断言及位置精确保留。`option(int)`实际lowering和同Some payload递归相等已核。Poison仍Type error但非法内部诊断可不同，证书不签任意raw Val等价。生产owner已按候选完整源SHA `e44e35062374bc718228c4f93f59959dd52a010b9b3810e986b63a8ee0a2ac75`最小应用。

四unary独审证`unary-membership-probe-20260927/independent-architecture-review/certificate.json`（同证据根）SHA `bdef07275b7da250fdd9822367d9f890dc3fb643bcf409578474b797781cfad1`绑定897文件，producer manifest `cde5f8341507d31792ae73a19ef514775e7fd128154aa5014955af4c9636b9fe`、候选源 `2417a6bc3751b3716e485c4a9381d50f6d23bc95996540c20a5f00f8e5f576e6`。438实际Isla/Z3检查独立重跑、128完整bits5与25enum、全部非法部分value、6检查器测试和实际错误membership突变拒绝通过。独立完整IR核25→0 matcher Jump、2057→2049函数，删除8个generated infallible wrapper；双decoder各4处值callee改成部分backwards，完整指令及guard顺序保持，同bits实参且matcher false/前置跳过不能抵达value。其它2042函数去真实位置和局部变量alpha后同形。

该unary候选实际增加110源行，生产中允许如实移动位置；实际SYMBOLIC execute的18条assert诊断移位已按原完整源行核，整源中34条跨普通/SYMBOLIC assert迁移由生产journal另列。不能称诊断字节不变或伪造旧Loc。组件只签声明的bits5/enum域，不签foreign enum、Poison或已删除内部IR符号的公共API兼容。生产owner已精确应用四mapping；IR owner接续以两文件差分冻结931输入，普通CPP/完整IR、129 active region实际selector（127有效、2历史空）及来源另验，旧d012归档配置维持原字节。两组件不等待无关e6a回放完成才进入合批构建。 随后两源生产ordinary/SYMBOLIC strict均实际exit 0，分别187.5/194.7秒；931文件在检查期间稳定，相对e6a仅两源变化、其它929不变。`lmul-unary-production-20260927/handoff.json`（同证据根）SHA `a96417fdc428242d5a42bce7469371aba593ba626a5d4ddd85842b3265eedfd2`已交IR owner开始完整构建；组件及strict PASS不替代新完整模型结果。

新VFMERGE独立stage最终自然exit 0，2359.20秒（39分19秒），30,603终态与最终JSON、日志和完整trace五元组守恒；215,491,497条边、invalid 0，峰RSS约4.81GiB。冻结`vfmerge-2h-56cc-20260927-c/replay-manifest-VFMERGE.json`（同证据根）SHA `6c5749ca13d2c9b400fa9ec8f11a9cdb530d5fc65f26640bac34dba6435456e3`；这是延长预算后的自然完成，不是LMUL或unary优化收益，原30分钟失败保留，完整双后端语义重放待审。新唯一库存`vfmerge-2h-56cc-20260927-c/evidence/aggregate-completed-56cc.json` SHA `d0d0988aa949eedaaa60f9ac12afc2ff7d04b6a89559a10372032d68f968b05d`为57/77、余20，不覆盖旧56索引。

RFVVTYPE原1800秒stage实际1803.64秒、child wait 124、无外信号/资源止损且无JSON；局部361 Retire、30,417 Illegal和3 non-encodable，峰RSS 24,310,220KiB。证据`single-56cc-20260927-035801-01-rfvvtype/evidence/RFVVTYPE-timeout-audit.json` SHA `2097f8a6db195ea7587606bf929c2dcf4c9b2168d0a265821a1fd9c5ba341b68`；其剩余前沿、资源趋势须实际复核后决定长预算，不给ETA。RFWVVTYPE后接VFUNARY1顺序继续。VFMERGE释放的另一个slot已于04:48:14 UTC启动`vfwmaccbf16-vv-2h-56cc-20260927/`，固定BF16格式/单操作作为下一候选，7200/7140/30、全输入及原96/48GiB阈值；不保证更快或完成，30分钟固定快照另审。

### 原生结构和局部源码合同的后续交付

原生exporter v1有限独审`source-ast-full/independent-exporter-review/review.json`（相对`isla/target/float-support-review/final-coverage/integration/p1-56cc69/`）SHA `603bf10e98dd105e9e79102405e64ea19927cef316f671b230d51613875f7964`已通过，绑定包manifest `829172d2fa0ced16cc241758314803d06165df8c0701afb3f55ca9b2b4e28dd3`。raw/ordinary/symbolic分别6673/7893/7997 defs，独立遍历10,917,131构造子/record节点，200/201 selected源均解析成功；物理库存instr_kinds失败保留。只签完整语法payload与公开type AST结构，catalog003派生path索引仅hash绑定，opaque annotation及遗漏的overloaded来源属性不升为语义已分类。coverage已实际接原生结构替换词法发现；后续v2公开注解补件单独冻结，不改v1证。完整分母仍OPEN。

向量账本已将799、197、969及1068既有trace的源码语义分别独审消费，当前v13 index SHA `2a4f85e34911a5444fc1f2bb3c232a8ca82e3dfcc792b345320e381d9a860068`，source observed 3120、结构待语义1844、pending1877；这不是新增模型执行或静态删除，源码仍未闭合。各跨版本消费保持精确不相交桥；getter/LMUL正常返回只在同一次目标frame内使用，不借循环另一次返回或整phase状态稳定。

标量访问器四配置局部合同已独审，`scalar/independent-accessor-domain-review/certificate.json` SHA `6b69f6a3bc5388ba112a00d97b0cddc80893481b10e1196ea28dadbc31b3811d`。独立解释器核1800入口、2056完整正常路径与所有位来源/写序，20测试和2464绑定通过；每配置511 caller仍仅库存，不能以局部helper合同自动删除caller方向。

FCLASS alternate新增41方向证`scalar/independent-alternate-classify41-review/certificate.json` SHA `d6a21107d11fa5f76543aed77a4457fd67840c46e68579d7535f1c164df6e0d3`重核26实际输入/78 phase，只签scalar-registers27和Doff14个自身LHS，未借default动态。剩余Foff H/S/D及Doff D的52个direct execute源码义务不能由decode/encode guard删除：已授权独立typed-constructor direct-execute入口，保真实MISA/R1及初态、另给新caseID和完整trace，对既有分类预期复验。该入口补源码helper实际方向，不能宣称从官方encode-first可达；官方77验收与decode-first审计仍各自独立。


RFWVVTYPE后续也在原30分钟预算外限124，无外信号或资源止损、无JSON；局部1,382 Retire、24,608 Illegal及3 non-encodable，峰RSS 13,392,668KiB。`single-56cc-20260927-035801-02-rfwvvtype/evidence/RFWVVTYPE-timeout-audit.json`（相对`isla/target/float-solve-evidence/`）SHA `7d95387fb68d19185264975767ea6e6a8752431a4dee56f633528c423e195fca`尚未完整核残缺trace；原队列已继续VFUNARY1。RFVV/RFWVV晚期工作与内存趋势单独复核，以决定下一空位长预算，不能由局部Retire计数推已覆盖全部分支。


原63稀疏输入随后已由新e6a物化器实际执行完成，并通过数值独审；`unified-backend-cpp-replay/sharedtrace-e6a-source-bridge-20260927/independent-cpp-initialization-review/minimal63-initialization-replay-review.json`（同证据根）SHA `9048138ceee31428118ce03100dd469a26a2bcf23619f24cbea035f4a8d750ab`绑定1421文件。原约束、预期、AST/ret及102字段、五配置实际初始化的8let/15aux均核；43 Retire、14执行Illegal、6原Decode_Illegal分列，另新增6个ILLEGAL execute不合并原入口。126正常phase scratch零写和各次残余观察唯一性有实际记录；v2来源/显示组件桥另审，关键FVFTYPE26条原权威输入另行实际回放，不以63条代替全部变化域。


新e6a原63的v2实际构建身份和全阶段附证随后通过，`unified-backend-cpp-replay/sharedtrace-e6a-replay-20260927/independent-witness-v2-review/certificate.json` SHA `9ff1bcbf4bc9207dbd1f7cb8b4966ac1f14c2973352c0e7f6fac2e4880c664c6`（同证据根）绑定2673文件。520实际源码只含Cargo新增bin和两源适配，fresh features/依赖/原生库均核；63输入126 phase、1,547,479访问独立重跑逐字段相同，257实际decoder函数体同字节，12潜在scratch写仍保留。该附证联立数值/init证，不把正常实际零写扩大为所有异常闭包纯读。

关键FVFTYPE26条原有输入也已实际重放并数值独审，`sharedtrace-e6a-source-bridge-20260927/independent-cpp-initialization-review/fvftype26-initialization-replay-review.json`（相对`isla/target/float-solve-evidence/unified-backend-cpp-replay/`）SHA `d695af760eb4185a2373bc4fd2c8e56e1c56fb650ff22dea47c38b731da89de9`。14 Retire、8执行Illegal、4 Decode_Illegal及新增4 ILLEGAL execute分别记录；52 phase、984,119访问scratch零写，原26整行对象和全部AST/ret/102字段核对。v3元数据适配的实际身份附证仍单独验收，不能据定向26条称官方FVFTYPE有完整JSON。

RF/RFW后10分钟RSS均持续增长，分别约3.51/1.99GiB，不能称平台。RFW末1000终态有15 Retire、最后一条Retire后仅2终态，RF末1000仅3 Retire；两次panic/SMT timeout/Z3Unknown计数均0。局部日志无PATH_RESULT时间戳，不能算这十分钟的终态速率或剩余队列。按当前实际余量与既定自动阈值，下一空slot批准优先RFWVVTYPE独立7200/7140/30秒；新合批FVFTYPE若已通过完整结构及strict/source门，可由主调度优先安排。所有30分钟失败保持，新长预算运行在30分钟另封前沿/资源checkpoint，预算收益与代码收益分开。


对上段预算建议的后续实证修订：RFW trace末尾实际case25991（日志最终前2条）在`zexecute` PC37791、`vext_fp_red_insts.sail:174`走`vl==0`的Retire早退，没有read_vreg或FP运算。因此最后Retire不能证明数值归约的晚期工作，末500中唯一Retire也属于此例；仅凭其余Retire计数不能推数值进展。主调度仍允许下一空位在新候选未全门就绪时运行旧56cc RFW两小时全域诊断，依据限于资源可控和目标未完成，VL保持完全符号、自动阈值不变；新候选就绪则优先。该决策不宣称数值收尾或两小时足够。

BF16 VV WMACC独立两小时运行的固定约30分钟checkpoint（1861.38秒）为695 Retire、17,116 Illegal及3 non-encodable，末100含7 Retire；峰RSS 7,195,636KiB、当时MemAvailable 117,403,928KiB，panic/Z3Unknown/SMT timeout均0，仍无JSON且继续运行。`vfwmaccbf16-vv-2h-56cc-20260927/evidence/checkpoint-030m.json`（同证据根）SHA `ac590901c884e1462913834f3daf17adff18cdc4de6b9d273fceab4db5a2aa53`只签固定前缀与资源观察，Retire是否经过数值路径另核，不能给ETA或完成结论。


新合批source快照已冻结于`unified-backend-model/20260927-lmul-unary-prebuild/source-manifest.json`（相对`isla/target/float-solve-evidence/`），SHA `a2eeba26f0cc7dbb3dad56bb86d7b3b62b33a8d7e51a78fe79d20cb3205539ae`，全931输入与生产handoff相符。新IR生成后，IR owner先用真实`selects_ir_location`作只读预核：129 region的旧新422个引用、127非空及2个历史空集合均同，所列源片段/函数/kind/位置无差异。此时完整CPP与新候选/独审尚未全部完成，预核不能提前写最终迁移PASS；完整IR结构与strict/source分别独审。


上述e6a两组最终数值/初始化封包已完成：`unified-backend-cpp-replay/sharedtrace-e6a-source-bridge-20260927/independent-cpp-initialization-review/certificate.json`（相对`isla/target/float-solve-evidence/`）SHA `0d414d7643952fd199cefa4d80632233754633782cd3154fc4424d0fb785f6ca`，5215当前文件绑定。五配置89唯一输入（63+26）分别为57 Retire、22执行Illegal、10原Decode_Illegal；后10个新增execute另记，178 phase/2,531,598访问scratch零写。v2/v3真实身份桥及各phase序列均与数值证联立，8let/15aux、完整AST/ret/102字段通过。它是这89条定向输入的最终限定证，官方FVFTYPE无完整JSON、全77和源码未闭合状态不变。

原生exporter v2增量有限证也已封存，`source-ast-full/independent-exporter-v2-review/review.json`（相对`isla/target/float-support-review/final-coverage/integration/p1-56cc69/`）SHA `e42ec7094bb812e4065c339a04c9611ccb24deb734363b8a2007ea52599f5001`，绑定包manifest `d7a292daf17fd9d6fd46a9c7f05b8fd36864f802016a066f7d9207bacf137f3e`及v1证。增补pattern/lexp应用分类、uannot和实例化，剥精确新增字段后两域原AST逐记录相同；138包文件、457输入、6测试和3真实fixture负控通过。global namespace分类仍不能证明目标module/visibility，相关关系保持OPEN，不能自动删除source/caller或宣称完整分母。

### 441c完整构建与两道独审通过

LMUL与四unary的合批候选IR已冻结为`441c145b0d27c1978d273c09ff561300c3c52244437df40cc75182665715f47c`。`unified-backend-build/model-lmul-unary-20260927/independent-full-ir-review/certificate.json`（相对`isla/target/float-solve-evidence/`）SHA `37609239f77f39f50f66ae1956d057c34990ea5f49e6dba21b10942af36e6612`通过完整结构独审：931源仅两文件变化；2057→2049函数、8 wrapper删除及新增`option(int)`单态类型均为组件所需；双decoder调用顺序与same-bits条件保持。普通C++在列明LMUL和7个新增option helper之外，8,826,947个token经统一双向alpha关系保持，25,104个全局对象的声明、初始化、使用和释放身份贯穿核对。16项测试通过。该证不签性能、正式求解完成或新的数值回归。

同构建下`independent-strict-source-review/certificate.json` SHA `2ba9c52160385f58ac00edcb1394daf46a54141bfd6231a16ac81246263a1313`通过另一独审。实际完整Rust selector执行6,536,043次，129 region保持422个精确引用，127非空、2历史空；source/function/kind/真实Loc均保持，77 active TOML只迁移IR hash，d012两个归档配置原字节不动。3735绑定文件、3测试、12负控及6实际边界通过，来源桥独立重跑相同。可运行441c包据此交主调度；既有56cc/e6a动态结果仍绑定各自原版本。新67 helper的CPP/Z3/原SoftFloat flags三方回归在`helper-crosscheck-441c-20260927/`另跑，83及17,586条既有输入须实际消费，不将旧回归PASS改hash沿用。

上述新回归随后实际完成并独审通过：同构建`helper-crosscheck-441c-20260927/independent-review/certificate.json` SHA `3f197c8fee1178fdb9df58e4ceac4312de084d2e225848e178f2075bc74463e1`，83+17,586输入三方无差异。独立CPP/原生oracle复跑及Isla精确tuple对象门的17,669个返回均通过；完整字段键、Bits5 flags、Bool或Bits16/32/64结果逐一校验，拒绝Poison/List。15测试及3815文件封后重hash无漂移；source-manifest `628e3169…`和candidate-freeze `683bde37…`分别绑定，不能混称同一metadata。范围仍仅67列定helper输入，不签decoder AST、全部typed输入、源码分母或全77；详见[新版三方回归专题](unified-backend-crosscheck.md)。

### VFMERGE汇编器拒绝的逐项补证

新自然完成VFMERGE首次prepare及独立collect均因汇编器拒绝失败，原日志保留。完整重做30,600个gen word的LLVM诊断发现7,615拒绝；首例`vfmerge.vfm v0,v5,f16,v0`的word为`0x5c585057`。每条须用实际Sail规则核验，不能以LLVM拒绝或旧BF16例外作为ISA非法依据。

`vfmerge-2h-56cc-20260927-c/stage/independent-illegal-operands-review/certificate.json`（相对`isla/target/float-solve-evidence/`）SHA `f900c97b72c28159fed5eb973667f1a304703baff1760a9c6e39809372ee8f9f`已通过限定独审。7,615条的word、AST、汇编、vd0、完整102项pre=post、R1及原Illegal终态逐一绑定；30,603个PATH_RESULT与JSON守恒，并联立完整215,491,497条trace边审计。12组测试含50个篡改负控和非零vd控制，实际LLVM消费1正4负。`reviewed-illegal.json` SHA `dd7beb8cdd3038134c6ae3c3861e49e290e8d275bba6ccbaf34958a5da941898`只允许本次精确记录，已交重放方保留原完整30,603输入重跑。静态合同限于正常到达guard时vd0充分拒绝；各例可能先由其它guard拒绝，不签逐例动态经过vd0，也不提前签双后端全量回放PASS。

### 下一合批优化的精确边界

剩余20项继续求解；两个正式slot运行期间不新增官方目标。下一轮只在冻结441c副本准备两个局部组件，组件证齐后由同一生产owner合批应用和完整构建。其顺序依据旧56cc实际分叉位置，不能提前算成441c性能收益。

- **两个归约合法性helper：** `illegal_fp_reduction`与`illegal_fp_widening_reduction`在旧RF/RFW日志分别有22,384及23,195次FORK。候选仅将纯Bool聚合改为已有strict Bool，优先普通/SYMBOLIC共用源，保持实际求值顺序。验收覆盖typed非Poison的任意vtype/vstart、完整SEW、全部8个RM、RFW任意EEW及实际elen域；eager新增读取须纯且total，并保留异常初态，不能以默认`have_exception=false`删义务。`get_num_elem`、caller最终guard、SEW断言、VL0与循环均不改。证据目录`reduction-legality-pure-probe-20260927/`；BF的`illegal_fp_variable_width`及其11 caller暂不并入。
- **nan_unbox内层数据选择：** 仅`fdext_regs.sail::nan_unbox`内层high全ones选择改成现有`ite`，外层`n==m`仍短路，避免空high slice。公共域为`m∈{16,32,64,128}`且`n>=m`、n无上限；须证明任意`n>m`的切片和canonical纯且total，实际用例含n=128/256/257及更宽值、m全四种。两后端共用同一体，不新建类型或原语，不改F读、FLEN、扩展guard或NaN位定义。证据目录`nan-unbox-ite-probe-20260927/`，当前完整隔离IR已生成，生产尚未应用；Poison和畸形raw Val不并入typed等价。

`recip7`指数收尾的逐字段BV ite候选已有只读报告，旧VFUNARY1对应1,143次FORK，随后overflow内部另89次。第一项仍须保format、CLZ、断言、sub normalize、idx及中间量的原顺序，只eager执行总性的1/2位移和拼接；三wrapper的两次recip调用不能按NaN分类删去。该候选留下一批隔离实现，不为合并同文件更多变化延后当前两个小组件。报告`vfunary1-next-optimization-review-20260927/report.json` SHA `29e3bc534f4185d4f574c92ffbcbce5f05d765713042544c2f5728bf83b1e702`，20个helper旧新去位置IR相同仅证明候选依据仍适用，未签优化等价或收益。

nan_unbox随后已通过完整组件独审，`nan-unbox-ite-probe-20260927/independent-review/certificate.json` SHA `55d32438b1f0debbfc386a50b6792f46a6a299d1fa12439d1c336c36bc10b81c`（同证据根）。候选源`dc8bdf1c20e4aa0522e77c5b7e48b2c24fb2913f18a50a3be258243bc9513851`仅第50行改变；10个无界n关系、6个真实helper解释、完整2049函数结构及3567声明核对通过。29符号形状、Isla/C++各1580个旧新具体检查、20测试和5个实际负控通过，12条普通/SYMBOLIC独立再生成命令及517 runtime来源联立。证书仅`PASS_COMPONENT_ONLY`，不包含下一生产批的全模型普通strict/C++重构建或官方整指令运行。生产仍待归约新组件证齐后同owner合批。

### 原生闭包检查器缺口与旧表身份的限定证

BF原生图v4的`free_references`漏掉`E_ref`：SYMBOLIC GPRs/FPRs/VPRs内共96个引用没有全部形成寄存器依赖，实际global x0未进入原reached955。因此名字未解析为0不证明完整闭包，旧v4不得签全集。共享实施由BF工具owner负责，scalar/vector只接各自真实root；新版本必须按完整compiler schema明确区分控制义务、依赖和非控制节点，覆盖Ref/lexp读写、局部binder、return/assume/constraint/sizeof、类型层条件及映射四向调用。未知tag或新字段须明确拒绝完整性。初版v5又发现mapping root_constructor继承BF白名单会丢scalar/vector构造子、非exp/lexp的默认结构分类不足以证明已审，继续以v6修订并保留v5字节；独审沿`source-ast-full/independent-shared-closure-checker-review/`进行。模块/visibility、extern目标、generated节点与真实caller域仍需各自证据，不由语法计数替代。

旧1,259条词法记录到raw精确身份已独审：`independent-global-native-token-identity-review/certificate.json`（相对`isla/target/float-support-review/final-coverage/integration/p1-56cc69/`）SHA `c2e3a645a56595633ff390bc2d6090e1936a2042921f2b7aa2c143e03b39c775`，15测试、638文件绑定及6673 definitions/596,024位置遍历通过。413 infix token三元组、815 keyword起点、28 mapping guard间隔及3 pattern/body等号分隔符精确唯一；最后3项只是定义分隔符，不授予分支极性。历史457项live输入中的plan、打包脚本及README三项漂移仍明确FAIL，原冻结snapshot和457 SHA映射可绑定，不授予新的producer chain完整性许可。此证只修旧表身份，新增动态、静态排除、caller闭合和完整分母均为0；当前主线继续完整schema与三族真实root分母。

### 归约候选新增求解器失败点的修订

最初strict聚合候选的理想Bool等价不足以放行。`isla/isla-lib/src/primop.rs`的`binary_primop!`将符号`eq_int/gteq/lteq`交给`try_concretize_bool_exp`，其中Unknown会安全保留符号值，但`SmtResult::Error`会传播`ExecError::Smt`；`isla/isla-lib/src/smt.rs::check_sat_with`实际将thread-interrupt timeout转成该Error。旧helper在具体vill=1时直接返回true，新eager调用`assert_vstart(0)`或EEW比较会在原跳过域新增主动查询和可见超时错误。因此初版`16d5246d…`隔离源保留为未通过完整运行合同，不进入生产，不能用Unknown fallback解释timeout。

经独审确认的下一候选仍仅两个helper：normal用`eq_anything(vstart, zeros())`代替`unsigned(vstart)==0`；复用`valid_fp_op(8, rm_3b)`判RM，因为`sew_bitsize={8,16,32,64}`全域的范围检查恒真，具体代表8的整数比较无主动查询。这里必须证明符号SEW在完整类型域下的关系，不只跑四个具体样本。widen复用normal后，保留`| not(EEW >= 8 & EEW <= elen)`原短路，任意Sail整数不窄化；两次EEW比较只在旧vtype有效、vstart为0且RM有效的原域执行，内部顺序不改。预期normal 2→0 Jump、widen 4→2 Jump，须以实际IR核实。验收允许减少旧查询和改变求解调度，不宣称timeout逐字等价；要求完整Sail返回、架构和隐式异常state关系相同，且不新增旧短路域的主动查询或模型失败点。若不能满足此小边界，下一生产批先只收已证nan_unbox。

### 三族完整入口与dispatcher分母合同

原生selected constructor根的调用闭包只是一部分语义分母。`model/postlude/decode_ext.sail::ext_decode`委托整张`encdec`有序选择；即使最终得到目标constructor，也可能已执行其它条目的matcher和guard，目标条目失败后还可能继续选择后缀或最终ILLEGAL。BF、标量和向量必须使用相同的入口合同，不能将各自constructor根计数当完整decode分母。

1. 每项root身份包含backend、配置、entry、constructor、phase和明确输入域D。官方encode→decode→execute、审计decode-first与typed-constructor direct execute分别记账，已有direct FCLASS证不能改称官方可达。
2. 官方D由原typed constructor的全部允许参数和实际初态建立；decode域是实际encode成功的image并携带该phase的实际状态，非encodable终态保留。审计D采用其原word约束和初态，不借官方encode image收窄。有限实际输入观察和家族全域静态合同不混写。
3. 从真实backend的`ext_decode`入口保留dispatcher，再按原生mapping顺序给每候选j建立`D ∧ 此前候选全部失败`条件。matcher求值、guard失败、成功value体和拒绝/默认路径分别列义务；目标候选失败后仍可执行的后缀也保留。生成IR可重排判断，其实际callee、控制及源码来源须另联立，不拿源顺序文本代替真实运行关系。
4. 原生位模式及typed guard可在精确域下产生排除证；被尝试的matcher自身可执行控制仍计入分母，只有body不可达不能删除matcher。每项排除绑定源、IR、域、顺序和独立证明hash；无证项保留OPEN。不需要把已证互斥的其它CPU execute body并入浮点范围。
5. encode和execute的constructor dispatch也保留真实入口到selected root的关系。其它constructor body可由标签互斥证明排除，但dispatcher的拒绝与默认路径不能按目标输出反推删除。跨入口消费动态或静态结论须有独立域包含证明。
6. 共享checker负责完整schema、依赖及有序选择机制，三族owner分别生成各自root/dispatcher应用；底层不复制词法规则。组件机制通过不自动关闭各族完整分母，已有132等根数保持库存口径。

### 编译前件与可执行分支的最终范围

本审计要完整解释目标入口的Sail分支及其实际生成控制，不要求证明整个Sail编译器，也不把每个AST构造子都变成动态分支。原生结构仍完整遍历；下面的角色必须由精确源路径、本次backend/配置和实际构建证据确定，未分类项保留OPEN。

| 角色 | 纳入内容 | 验收方式 |
| --- | --- | --- |
| 可执行控制 | 目标入口域内的if、match/mapping选择、短路、loop、assert、try及对应拒绝/异常路径；类型或undefined重写实际生成的控制 | 源及生成来源、caller/域/顺序明确；动态证或精确域内静态排除，不按最终constructor反推删除 |
| 运行数据与依赖 | 调用、读写、return/assume、显式`E_sizeof`/`E_constraint`的类型或配置依赖、实际undefined helper及outcome实例化 | 每个实际节点和target依赖有来源；只有其中确实产生控制的部分分配分支方向，不给每个数据节点凭空加branch |
| 编译和声明前件 | 仅用于类型检查的signature/constraint、已由本次构建替换的配置、实际target已消除的measure及其表达式、非运行注解 | 列明真实声明和配置来源，绑定选中target及消除/常量替换证据；不要求动态覆盖，不把其中的`E_app`当运行调用 |
| 初始化运行域 | 常量替换后仍保留并实际执行的config/let/register初始化表达式 | 联立实际初始化顺序和被测配置；其中的运行控制单独记，不笼统称全部config都是编译期 |
| 未决 | 不能确定是否重化、target选择不明、依赖没有来源或模块绑定歧义 | 保留准确节点和原因，阻止相应完整性结论；不以schema枚举成功或旧表零pending替代 |

`Nexp_if`、`NC_and/or`、`ATyp_if`等类型层形式不能仅凭tag计入运行分母。仅当它们经`sizeof`、constraint表达式或本次backend转换重化，并在实际模型产生控制，才联立该控制；纯类型用途作为允许输入域和静态排除证明的前件保留。`L_undef`本身是值来源，但选中target的undefined rewrite可能调用生成函数，因此必须建立真实生成依赖；不能作为普通无依赖literal忽略，也不能直接给每个literal两个branch。`DEF_measure`/`Rec_measure`在已核target消除时只保编译前件；若实际rewrite将它保留或转为运行检查，则按真实产物纳入运行域。outcome只解析实际选中实例化及目标callee，其余实体通过构建选择关系解释，不追成整个编译器的语义证明。

共享机制的最终闭合清单为：

1. 冻结raw/typed/实际构建输入及selected文件关系完整；物理解析失败、宏排除和Generated节点逐项有状态。
2. 所有实际相关节点的子结构被访问，未知tag/字段拒绝；表达式、lvalue、binder、register ref和实际callee/target override都有精确或明确保守依赖，未解决歧义不能当已精确解析。
3. 三族各自按上一节实际入口域建立dispatcher和root关系；默认、失败、前后候选不遗漏，纯constructor组件与整入口分开。
4. 可执行控制、运行数据依赖、初始化、编译前件及未决逐节点分列；类型条件、measure等不按tag数量自动扩充动态分母，实际重化控制也不能遗漏。
5. mapping生成函数、undefined/outcome转换和无物理位置节点与实际IR有来源关系；仅hash绑定而没有语义映射的项仍OPEN。
6. 每个源分支方向有精确谓词/极性、caller和配置域；动态观察、静态排除及未决守恒。来源完整与覆盖完成分开审，三族的全分母结论只能在自己的应用层交付后签署。

实施边界现拆为共享v8表达式/extern核心、独立`native_type_dependencies.py`及测试、三族root/dispatcher应用、各族raw/source关系；一个文件一个owner。type/decl辅助由coverage owner实施并单独独审，核心、dispatcher及BF应用分别由既有reviewer负责。新增辅助不要求BF owner为每个声明类别再次串行重写已冻结版本，旧v4/v5/v6/v7失败或局部证仍保留原状态。

### BF16两小时外限与441c新正式运行

56cc的BF16 VV WMACC最终仍由外层7200秒终止，`vfwmaccbf16-vv-2h-56cc-20260927/evidence/VFWMACCBF16_VV-timeout-audit.json`（相对`isla/target/float-solve-evidence/`）SHA `d9f32f2b9cb2cd91bd1c5f03d4fac2c23215a1acb63b8d3d8bd34eafb0e1642a`。实际child 124、7201.33秒，无外signal、资源stop或最终JSON；局部5283 Retire、25,924 Illegal及3 non-encodable。1364资源样本峰RSS 8,729,508KiB，最低MemAvailable 104,554,688KiB；panic/Z3Unknown/SMT timeout日志模式均0。49,826,592,779字节残缺trace仍待完整前缀审核，不将局部计数签全域或完成，57/77库存不增。

空位已实际启动441c FVFTYPE，真实argv为7200/7140/30秒、2 worker，与56cc RFWVVTYPE两小时诊断各占一slot；资源保护不变。此为新IR与新独立预算stage，须与56cc/e6a各自30分钟结果分列，不将新预算下的进展直接归因于代码优化。

### nan单独生产批与后续任务分工

归约v2的小IR已实际生成并经独立再生成逐字节相同，normal为0 Jump且无主动查询，widen保2 Jump；源码和6个符号关系检查通过。不过实际runtime全域/异常state/查询门、CPP GMP边界和有效负控尚未完成，预计仍需生产方15–30分钟及后续独审，不能进入生产。因此主调度决定本次先只应用已审nan组件，归约继续隔离，后续另批按实际证据整合；上文“两源合批”等待方案在此被更新，不放宽组件门槛。

唯一生产owner已应用`fdext_regs.sail`第50行，完整源SHA为`dc8bdf1c20e4aa0522e77c5b7e48b2c24fb2913f18a50a3be258243bc9513851`。相对441c的931输入仅此文件变化，其余930相同；ordinary/SYMBOLIC完整strict分别186.82/194.33秒、exit 0，检查前后和封包时源均无漂移。`nan-unbox-production-20260927/handoff.json`（相对`isla/target/float-solve-evidence/`）SHA `764baa22d09c84e48d287c76947342d2172816701669b8dfe5838ae028ce2724`，931 source-manifest SHA `6822b0ede2e92c4174c2a800f067f160e8bf18b2b2704bade58805e4ebb29e02`，已交新完整CPP/IR构建。隔离86f IR不能自动代替生产快照的新产物；完整IR/CPP结构和strict/source selector仍分别独审，当前441c运行包保持冻结。

本批完整IR/C++独审由已有nan组件reviewer接续，strict/source独审由已完成向量原生实例的reviewer接手，归约reviewer继续优先原组件。441c原63+FVFTYPE26的新五CPP与实际初始化/89重放则由已完成共享AST核心独审的reviewer承担，VFMERGE120片phase由另一已有reviewer负责。各自独占新证据目录，不迁旧PASS、不改其他owner文件。

### 重复trace哈希的最小复用边界

VFMERGE执行方计时显示，四worker的数值分片约417秒，整条流水线约3525秒，原44GB trace重复哈希是主要额外成本。已检查现行`trace_reuse.py`：它只复用严格trace解析结果，`hash()`每次仍真实读取；`prepare_official.py`前后来源检查和`pair_official.py`/`sharded_official.py`也再次验hash。新优化只减少同一冻结文件在同一进程内的重复字节读取，不改变输入全集、数值比较、trace解析合同或最终漂移门。本次VFMERGE冻结证不改。

1. 仅为本次明确allowlist内的已完成原trace建立一个父进程内的审计会话。`audit_run`仍完整读取并计算真实SHA一次；哈希前后同时核规范路径及实际只读fd的dev、inode、size、mtime_ns、ctime_ns一致。
2. 由该真实读取创建进程内receipt，绑定actual/expected SHA、精确文件身份、保持打开的fd、审计会话、validator/选项和terminal语义摘要。中间消费先核全部绑定及当前path/fd身份，再复用已核hash；不能只按mtime或路径命中，不能从序列化JSON导入“已验证”receipt，不能跨PID、会话或新run沿用。
3. 仅对已列trace启用；CPP、IR、配置、脚本和manifest等其它输入保持原真实hash行为。最终全源漂移检查必须强制fresh读取并计算hash，显式绕过receipt；任何缺失或漂移都不能发布PASS。记录每次完整读取和复用的调用点、字节数和耗时。
4. 先记录现有六次读取的真实调用点和进程边界。若prepare目前在独立进程，只有将该小入口按原合同纳入同一parent并显式传递会话，才能共享receipt；不能为宣称省去四次读取而引入未经审定的跨进程信任。现有严格trace结果附证仍单独核验。
5. 隔离新模块和入口先TDD，负控包含同长度改字节后恢复mtime、inode替换、符号链接换向、fd/path不一致、expected SHA/validator/选项不同、未实际mint、跨会话/PID，以及最终fresh失败。开发使用真实小文件和小回放，独审后才测大文件收益；不为测试优化再次反复读取已冻结44GB证据。

该实现由回放owner在441c独审移交后承担，不引入通用持久化缓存系统。当前为审定边界，尚无实现或性能PASS；实际减少次数和端到端收益以新入口实测为准。


### nan 完整构建、归约现行组件及组合前件

nan 单独生产批已完成完整构建，实际入口为 `isla/target/float-solve-evidence/unified-backend-build/model-nan-unbox-build-20260927/`，IR SHA `86f1121b09634575e60629c272cfddb741c809182a2fa4b337acb6755b17e61f`。其 `independent-full-ir-review/certificate.json` SHA `4f0f7e0867409481db6d0358f19dfd4434dc3bc282967534a10de7569d531b26` 与 `independent-strict-source-review/certificate.json` SHA `43e1e908d0d4bb1b9ee26c4f8e88364a0ce2c76562654ecfd27ad566703ba975` 均通过。2049 个 IR 函数仅 nan 改变，其余 2048 函数和 3567 声明保持；普通 CPP 新增一个 `ite<lbits>` helper 及其 header 声明，不能称整个 header 未变。其余 8,826,728 token 与 25,081 全局对象经统一双向 alpha 关系核对。strict 实际 selector 共 6,525,981 次，129 region/422 引用不变，77 active 配置仅迁 hash。两份 d012 归档不动。新 67 helper 的 83+17,586 三方回归另在新实际产物上执行，旧 441c 回归不迁移。

归约组件的实际目录是 `reduction-guard-ite-probe-20260927/`，此前计划中的 `reduction-legality-pure-probe-20260927/` 不是现行证据入口。组件 producer 在旧独证后原位追加三个清单标签，导致旧证绑定漂移；旧字节已重建保存，旧证保留历史。现行只能消费 `independent-review/final-9161/certificate.json` SHA `c76e79d6c74820ce1f600d76a30e0d8867669fee55895e81299ce4c823736e85`，绑定 manifest `9161e8b1c98528e3a1e2b525da96b1dee25045ce681bcdd79ef798a0d0fcb385`。1078 依赖全核，normal 零 Jump/主动查询，widen 保留两个 Jump 及原 EEW 比较准入；48 个 SAT 路径、80 个 i128 边界和 1664 个 GMP 边界通过。该证的基线仍是 441c，单独不签 nan 组合。

组合最小前件证为 `isla/target/float-solve-evidence/nan-reduction-source-composition-20260927/review.json`，SHA `8c99975d1ab7cab85533df2ffd2ed617d3e612517992e5146b53f455cf027b83`。实际重核 931 生产源与 nan 冻结快照完全相同，并重算归约独证全部 1078 依赖。归约候选的 166 模型文件中，164 与 nan 相同，另两个分别是旧 FD 文件和目标 V 文件；将已审的两个 helper 原文替换到 nan 生产 V 文件后，与候选整文件逐字一致。生产 owner 只可应用 V 文件，保留 nan 的 FD SHA `dc8bdf1c20e4aa0522e77c5b7e48b2c24fb2913f18a50a3be258243bc9513851`。期望组合 931 文件表 SHA `2786453e1e968d5d941514e331da2d613db04609094d657636c15526a9bf15a4`。12 个生成 `__pycache__/*.pyc` 已明确列作源码库存排除，不默称工作树仅有 931 文件。应用后须重核完整源码表、普通/SYMBOLIC strict，再做新隔离完整 IR/CPP 和两道独审；本批没有其它已审 Sail 组件，recip7 不并入。此证只授权源码组合步骤，不签性能或完整模型通过。

### 441c 的 89 条整指令与 VFMERGE 最终重放

441c 新实际回放的数值/初始化总证为 `unified-backend-cpp-replay/sharedtrace-441c-source-bridge-20260927/independent-cpp-initialization-review/certificate.json`，SHA `9fb13e892f1fdaf94ad1a7d8ef9b2bf97ea5ca8e0ae49bda28b5aa4a6e4394f6`；witness 总证在同证据根的 `sharedtrace-441c-replay-20260927/independent-witness-review/certificate.json`，SHA `a48bdd5324d75d52b7c3138a433f47b66ee9e7f1f2989b67163e0e838b6b2878`。五配置 89 输入、178 phase、2,529,965 次访问逐项联立，57 Retire、22 执行 Illegal、10 原 Decode_Illegal 分列，新增的 10 execute 不混入原入口。完整 AST、ret、102 字段及 8 let/15 aux 通过。13 组 observer 独立复跑 exit 0；257 个 decoder 成员中精确换入四个真实 backwards、移出四个旧 infallible，582 调用和 12 潜写站点实际重核，不能用成员数量相同继承旧闭包。

同 56cc 的 VFMERGE 全 30,603 输入也已通过最终 phase 独审：`unified-backend-cpp-replay/sharedtrace-vfmerge-2h-reviewed-56cc69-20260927/independent-phase-review/certificate.json` SHA `e925f35cc5cd3d530e4ffcc5644899dce30edcc5a37c551c63af6cac7ea21b9e`。120 片、61,206 phase、940,516,587 次访问与全部输入相符，scratch 实际零写；与数值独证联立后才放行该批。上述有限输入结果均不签完整异常闭包纯读、全 77 或源码分支闭合。

### 最小 Z3 耗时诊断合同

441c FVFTYPE 的固定 60 分钟前缀独审入口是 `fvftype-lmul-unary-441c-prepared-20260927/evidence/architecture-060m-frontier-review/`（相对 `isla/target/float-solve-evidence/`），`review.json` SHA `dc8d953e9365aab29cbdec6f52b975f166a0d185874f793fcadf4b60699e1041`。实际捕获时间为 3601.91 秒；858 完整终态与日志一致，4,991,050 边对 25,595 catalog 全核。739 Illegal 由聚合 guard 拒绝，尚未进入标量读取或数值运算；110 Illegal 在 mask 初始化 Err 退出且尚未数值运算；六个 Retire 分别实际执行两次 RSUB、SUB、ADD、MAX、MIN。路径 active/CPU 时间含公共祖先，且 worker CPU 包含 Z3 FFI，均不能作为解释器净成本相加。trace 没有 SMT performance/diagnostic 块，当前证据不判定 SMT、分叉或 FP 主导。

据此只增加默认关闭的轻量诊断，不扩成全阶段 profiler。实现 owner 为 performance，独审由未参与实现的 numeric reviewer 承接，具体边界如下。

- 只记录现有受保护 `CheckSat`、`CheckSatAssuming`、`ModelEval` 三操作；不加查询、不改求解配置、约束、输入域、超时或 fork 行为。
- 每 worker 的序号、计数与 FFI 累计墙钟不属于 frame，不随 fork/checkpoint/restore 复制回滚。独立 JSONL 流式输出，禁止无界收集记录；PID/session/真实线程或 worker/seq 唯一关联。当前调度为每 task 新线程，并发上限不等于两个固定 worker；fork 可沿用 TaskId，不能只按 TaskId 关联。
- 在受保护 wrapper 调用及 watchdog arm 前输出并 flush operation begin，避免日志 I/O 占用已启动的查询超时窗口；真正 FFI 闭包内只计时、不写日志。end 记录 FFI 开始偏移、result、interrupted 和 FFI wall，wrapper wall 另列（含 watchdog 建立/握手/join）。无 end 的 begin 单列为未完成 operation；record 以来的 elapsed 可能包含握手或日志开销，不能称为 FFI 耗时下界，不回填完成时长。
- 只加启用时的最小 executor TLS 位置更新，绑定真实 function/PC/task；phase 按下述 v2 裁定统一为 null，修订初版 execute 一词的歧义。run 边界清理。collector 等无法精确绑定的上下文记 null，不能沿用最后 PC。SourceLoc 只证明调用点，不能据 guard 位置或上下文存在 FP 约束断定 FP 成本。
- `translate_exp`、其它 Z3 API、collector、render、output 均保留未归因。受保护 FFI 墙钟可相对于各 worker 观测窗口说明，不能把并行 worker 累计除单进程墙钟当 CPU 百分比，也不能把其补集全算为解释器。
- TDD 覆盖关闭无输出、开启前后结果相同、interrupt/error/Unknown/未完成 begin 可区分、fork/恢复不重复祖先、多 worker 序号关联及上下文清除。新 binary 与诊断目录独立，当前官方 binary 不改；完整输入 30 分钟诊断由 batch 按资源调度，单列 diagnostic，不迁官方 PASS。

receipt 优化的实际初版进一步固定为同一父进程六个调用点中的三次真读、三次复用：prepare 初绑真读且不 mint，audit_run 真读并 mint，中间 prepare 末绑/wave 导入/sharded parent validate 复用，sharded 最后必须 fresh。显式 final callback 与已冻结原 sharded 源唯一 anchor 机械生成副本，禁止靠调用次数或错误文本识别阶段。原 VFMERGE 冻结数据和工具不修改。


### 后续队列与原生来源增量

441c FVFTYPE 随后实际在 7200.90 秒外限 124，无最终 JSON、外信号或资源 stop；21 Retire/1687 Illegal/3 non-encodable，残缺 trace 2,025,410,713 字节。最终 `fvftype-lmul-unary-441c-prepared-20260927/evidence/FVFTYPE-timeout-audit.json` SHA `71f5581bed6ae24db035dbf5ac571d6b8b683c093d22b4465fc5a2681bb363d6`。nan86f 的 FVFTYPE 已在独立 stage 于 08:56:44 UTC 启动，仍全域、完整 trace、7200/7140/30 秒；不能将 441c 局部结果移到新版本。

下一三目标建议为新归约批的 RFWVVTYPE、RFVVTYPE（各 7200/7140/30 秒）及最新已通过全部门槛的 FVFMTYPE（1800/1740/30 秒）。若新归约候选在空位出现时尚未齐门，可先运行 FVFMTYPE。RFW/RF 的实际 execute 直接消费两个变更 helper；前者有两个 opcode 和 16/32 位输入，后者四 opcode 和 16/32/64 位输入。FVFMTYPE 只有六比较操作、单标量与单向量源、Bool/NV 和 mask 更新，nan 实际作用于其 `get_scalar_fp`；它在旧 56cc 资源长批中是信号 15 失败，尚无新版完整预算证。上述是按代码成本和变更点安排的候选顺序，不保证收敛或性能增益。其后可排 FVVMTYPE、FWFTYPE/FWVTYPE、三个转换 unary，再其余 FMA/BF；保持两个正式并发位、全输入域及实际版本记录。

新原生来源证据仍均属有限许可，证据根为 `isla/target/float-support-review/final-coverage/integration/p1-56cc69/`：

- setter：`source-ast-full/independent-setter-source-lowering-review/review.json` SHA `bc031a1c927f9a3a956b5f550932299e38ad78f04352ca8acd5fa00d21a2a82e`，ordinary 116/SYMBOLIC 125 行完整重建；665 原依赖、8 独审/11 producer 测试和 18 真实负控通过。`initial_check` 将 setter lhs 的 unit/tuple 分解参数，`type_check` 在 lhs 位置追加 RHS、加属性并以 unit 检查，overload 原名另保留。此证不签 callee 语义或动态覆盖。
- 类型常量：`source-ast-full/independent-native-type-dependencies-review/constant-lowering-annex-v1/certificate.json` SHA `41e29f99369e45effdca7bc857586ac361e8324176e57149d71194c52851f0b6`，333 精确节点（310 sizeof/23 constraint）和五 alias 的静态值/身份通过，1218 绑定无漂移。BF 的普通五项仍 runtime、SYMBOLIC 五项仍 IR pending。新的同源 skip-initial true/false 实际导出增量继续补 `Frontend.initial_rewrite` 输入和输出；已有 exporter 的 env_info 只有 module 身份，不能把导出对象一致称为全部 Type_check.Env 已观测一致。
- BF enum/assert：`bf16/independent-generated-enum-assert-bridge-review/certificate.json` SHA `0a67905173ccb381b37cfa04e34f7e23e52c1e7265a3f6ae499ea3c3cf7c0727`，两域各 enum/rF 共四节点的实际局部 IR/CPP 关系、三配置 15 enum 路径、五 CPP 合法路径通过；13 既有测试、9 实际负控、两次同 runtime probe 重链和 844 依赖已核。仅签抵达 false 后的 AssertionFailure/exit 局部链，未签完整 Model 动态执行或逐 rewrite-pass trace。

vector 的九项 `fp_class_onehot_pure` 生成条件为 `eq_int(bitvector_length(raw),16/32/64)`，具有局部 `'m` 及嵌套 `Nexp_if`；它们不是上述五 alias 的常量实例。原 `float_bits` 六个 type-if 的替换、重化与九个实际实例仍需独立来源桥，不能固定宽度后静态删除运行义务。历史 457 live 中三项漂移 FAIL 在所有有限来源证中继续保留，冻结副本身份不增加 producer-chain 权限。


归约随后已按上述前件实际应用并完成两模式 strict：普通 181.54 秒、SYMBOLIC 188.28 秒，均 exit 0。`isla/target/float-solve-evidence/nan-reduction-production-20260927/handoff.json` SHA `a79109b43f7672103c4a9ee6007019f756a7e0eeb83dcfbfc4a7cd01d08ff50c` 绑定完整 931 文件，与组合期望表逐项相同。候选 V 文件实际为 767→770 行（增加三行），首次实施脚本错误要求总行数不变，在生产写入前失败且日志保留；修订后严格只替换两 helper，不能沿用 nan 的行号不变结论。新完整构建入口 `unified-backend-build/model-nan-reduction-build-20260927/` 已启动；完整结构和真实 selector/source 坐标迁移仍待这份新产物独审。

nan86f 新 67 helper 回归随后也已正式封证：`unified-backend-build/model-nan-unbox-build-20260927/helper-crosscheck-nan-20260927/independent-review/certificate.json`（相对同证据根）SHA `fe432ce3dc4284fcd2b0c9a068dc94e584aaf6f861599861b937871428e5bc06`。83+17,586 三方输入、17,669 实际新 IR 完整 tuple、CPP/native 独立复跑及 19 测试/控制通过，11070 实际依赖全重 hash 无漂移。旧 nan 完整结构证的 5934 依赖中，唯一历史 live V 路径已经被本次归约合法修改；新附证显式记录这一漂移，并按原 SHA 与源码组合前件投影到实际 nan 构建的冻结 V 源，其他 5933 项和 strict 的 3745 项均相同。旧证字节保持，不把 live 漂移隐藏成零漂移。下一 nan86f 原 89 条整指令回放的新数值/初始化与 witness 独审另做，不由 helper 证替代。


nan86f 原 89 条新整指令回放最终也已完成：`unified-backend-cpp-replay/sharedtrace-86f-source-bridge-20260927/independent-cpp-initialization-review/certificate.json` SHA `a49d144e260c990453be1c47093300d27959f43f229a2813f0c21071315feb24`；同证据根 `sharedtrace-86f-replay-20260927/independent-witness-review/certificate.json` SHA `c899afe3e25b4c07fbae5c55b5a6e8e7af96e343c703ac34f49e0b571e8a37d1`。五配置 13 初始化侧车、完整 AST/ret/102、8 let/15 aux 及 89/178/2,535,669 次访问逐项联立；两证分别最终核 15,105 与 13,280 依赖无漂移，历史 live V 差异仍显式列明。Isla 是 e6a fresh→441c→86f 的精确复制来源，五个 CPP 是新实际编译，不能合称全部重新编译。257 decoder 成员和 582 调用、闭包函数体精确相同，唯一 nan IR 函数改动位于其外；12 潜写仍保留，三个全局闭合声明仍 false。

nan+reduction 的新完整构建已实际通过，IR 为 `a04050747af5354db3db507097d9ed52e3bd9daa157f2ab043b48ef2952dfa7d`，`model-build.json` SHA `9f47ff72341f10cf77ec8fc1cf76ec5dceb27c6ca02189aeeaa1ea32582ac9ee`，560.94 秒完整构建退出 0、七产物核对。新隔离候选 `unified-backend-candidates/nan-reduction-a040-20260927/` 已冻结，freeze SHA `8d5fedf48508df141edecf6fd8c0c6a67696873b386a73d0644b591ef83a53dc`；完整结构与 strict/source 两独审、新 67 helper 三方回归正在此真实产物上验证，不复用 nan 的动态 PASS。完整结构预核已发现唯一新增声明是已有 `eq_anything` 的 bv64 单态实例，3567→3568；这是复用既有原语的声明，不能把顶层声明称为完全不变。

最小诊断 v1 的生产测试通过后，正式独审仍判 `NEEDS_REVISION`。`z3-call-diagnostics-independent-review-20260927/review-v1.json`（相对同证据根）SHA `4e86d36cbe8357dcce04bad0997e38d9ff2d6034084f381b7ce32b471126680a` 记录两个缺陷：固定 `phase="execute"` 混淆 IR 运行与 solve 阶段，以及消费器未拒绝坏 completed 计数、越界 FFI 区间、错误 worker 窗口、未知 schema、worker 关闭后调用等六类损坏记录。真实记录的其它计时/关联不变量、独立 on/off 回归和活体未完成 begin 实验均通过，但该 v1 不放行诊断运行。v2 统一 phase=null、不新增相位推测，并增强已有消费器拒绝门；schema 升版，旧冻包与失败保留，另目录单批重新构建和独审。只有新版正式独审通过后，才按资源许可运行独立 30 分钟 nan86f FVFTYPE 全域诊断，不能计为官方完成。


### a040 组合全门与诊断 v2 正式放行

新 a040 的完整结构独证为 `unified-backend-build/model-nan-reduction-build-20260927/independent-full-ir-review/certificate.json`（相对 `isla/target/float-solve-evidence/`），SHA `d1031e6ad1758ef53586a709bdfaa373dbc257db6aabbf4a2840e3d252a9e5f8`。2049 函数仅两个归约 helper 改变，其余 2047（含 nan）保持；新增唯一 bv64 eq 单态声明。全部已知源码位置和诊断字符串按实际相同行映射核对，不能统一假设每个位置都加三行：第一 helper 后有 +4 区间，第二 helper 后累计 +3。普通 CPP 其余 8,827,812 token、25,109 全局对象统一双向映射，完整 4544 成员无增删，header 逐字相同；此前 4339 只是多行开括号匹配计数，本次单行 startup 也实际全 token 覆盖。四个优化组件、1664 GMP 边界、六个真实负控通过，7523 依赖封前再核无漂移。封包时曾把 inventory 的 `{bytes,sha256}` 对象当成 hash 字符串而失败，实际 Cargo.lock 未变；修正读取字段后封证，没有放宽内容门。

同构建 `independent-strict-source-review/certificate.json` SHA `517a7cad9324b9a57df7be4434f58f236e34fb14eee489a7f975ccad223ba7ae` 通过完整独审。实际编译 source_loc.rs 并执行 6,525,336 次 selector，129 region/422 精确引用/470 overlap 保持；127 非空及两个历史空不变。变更 V 文件中、两个 helper 以外的 133 条 IR 引用按真实 +4/+3 行图精确迁移，没有 active region 指向该变更文件，故这次 77 配置只迁 IR hash 的做法成立；两份 d012 档案原字节保持。完整 931 源仅目标 V 变化，nan FD 保持，3762 依赖无漂移，五测试、12 真实负控和六实际边界通过。

新 67 helper 实际三方回归也已独审：`helper-crosscheck-nan-reduction-20260927/independent-review/certificate.json` SHA `902c1d605db33892d69137f35817ecc61acf9cdb172faaaab2440b771c583332`（相对上述构建目录）。83+17,586 输入全部新 CPP/native 独立复跑，17,669 新 IR tuple 的全部字段及宽度通过，拒绝 Poison/List；15 测试/控制通过。11737 绑定逐项再核无漂移，完整消费结构证 7523 项与 strict 证 3762 项，无需历史 live 投影。实际运行的 build 输入清单 `2774…` 保留，正式 candidate 清单 `20588…` 与 freeze `8d5fedf…` 经额外精确源桥联立，不篡改已经运行的 summary 身份。上述三门允许交付新官方候选；全 77、源码闭合、性能及主 IR 切换仍不由它们决定。新 a040 原 89 条回放继续单独执行、独审。

诊断 v2 随后正式通过：`z3-call-diagnostics-independent-review-20260927/v2/review.json` SHA `10115c84c92091bf4f0ddcb1fca34b15f3c6ac769e766d3e2ad0737d6b54a056`，绑定候选 manifest `9b72dfbd0a1278ab5e1a2f7201d09cb0fe98a3659620e7a515d294bbe1891a6b` 及隔离 binary `e7ba503a2d4bffd313b0580e5eee335aeb351736806901b1616655e974010f81`。677 封包文件、518 源文件全部复核；24 项消费器检查包含 18 次损坏拒绝和未完成/部分前缀正控，9+9+1+2 运行测试通过。实际 4180 对 begin/end 中 800 项有真实 IR context 且 phase=null，3380 项 context=null；独立计数/时间/生命周期重核通过。old-off/v2-off/v2-on 的 29 shape、83 terminal、1580 检查报告逐字相同。主运行时与两个当前官方进程保持原 binary；该有限证只放行已有资源许可下的独立 30 分钟 nan86f 全域诊断，结果另报，不提前推 FP、CPU 或性能结论。

### a040 原 89 条回放的最终独证

原 89 条输入、五配置及 v2/v3 物化器边界保持，新 raw a040 回放已完成两项独审。`unified-backend-cpp-replay/sharedtrace-a040-source-bridge-20260927/independent-cpp-initialization-review/certificate.json`（相对同证据根）SHA `04a03b0d70b415e0ddeb589463628f5e68f71381cd3f73ba8d18bd637449f609`；同目录系列 `sharedtrace-a040-replay-20260927/independent-witness-review/certificate.json` SHA `63bb5c1c812db4463dd4cc5174410ae8b9723cc9777db69f23831698d1a84b9d`。13 组独立 observer 实际复跑全部退出 0；完整 AST、ret、102 字段及双 phase 序列逐项相符，共 89 输入、178 phase、2,535,669 次访问，路径异常槽写 0，八项真实负控通过。原 57 Retire、22 execute Illegal、10 Decode Illegal 与新增的十个 Illegal execute 分列。

五个 CPP 为本版实际编译，Isla 使用精确绑定的冻结 runtime，证据不宣称重新编译该 runtime。五配置的 13 初始化侧车、8 let 和 15 辅助字段均已核对；完整结构、strict/source、provider 及 witness 子证最终联立，初始化证的 16,248 项和 witness 证的 16,149 项绑定最终重 hash 均无漂移。证书针对实际 raw IR 路径，未使用候选默认路径中的旧 56cc IR；封证时 official stage 尚未准备完，后续 stage 装配与实际 spawn 另证，不回改该历史字段。

源码坐标变化意味着 raw a040 有 74 个函数字节变化；完整结构证按精确位置映射核对后，语义改变只有两个归约 helper。完整 decoder 的 257 成员、582 调用及函数体仍逐字相同，12 个潜在异常写继续保留。178 个实际正常 phase 没有观察到这些写，不将完整 decoder 宣布为纯读；全 77、完整 source 分母与分支闭合仍未由本定向包完成。

### a040 正式入口装配与隔离诊断启动

旧 snapshot 入口只接受旧 schema 和单一前像：runtime 冻包的数据 IR 为 56cc，而本次 strict 迁移证的前像为 nan86f。两次准备失败均发生在 spawn 之前，原失败保留。新的入口直接从已审候选装配真实 a040 raw IR 与全部 79 份配置，保留冻结 runtime 代码和原 binary；来源清单如实区分新装配与历史迁移，不伪造 56cc→86f 的中间运行。

`entry-adaptation-independent-review-20260927/review.json`（相对同证据根）SHA `f43ad33307d046a2fa6f491f61b2ed4ebf3448717435c9178d9a139ee7cbeef1` 已通过最小独审。旧/新 stage 各 517 项逐 SHA 核验，439 项保持，恰好替换一份 IR 和 77 份活跃配置；两份 d012 归档保持。实际 IR 为 a040，binary 为既有 `b42ac4f…147e7`，fullIR/strict 双证及 1210 项输入均联立，六次真实损坏拒绝通过。对应 `rfwvvtype-nan-reduction-a040-2h-20260927-c/` prepared `4b04080b…bcdf1` 与计划 `1fa381fa…78a03`；实际 dry-run 为 RFWVVTYPE、单目标、两 worker、7200/7140/30 秒及完整 trace，全输入不缩域。独审只签入口并已交调度，实际 spawn 和终态另记。

调度随后于 2026-09-27 10:42:48 UTC 核实该 RFWVVTYPE 已实际启动，supervisor/isarch 均位于所审 stage 的 cwd，IR 和运行参数同上，资源保护保持。此时正式运行位为 nan86f FVFTYPE 与 a040 RFWVVTYPE 两项；自然退出、完整输出和新回放仍待实际结果。

隔离诊断 `z3-diagnostic-nan86f-fvftype-20260927/` 已于 2026-09-27 10:38:02 UTC 实际启动，prepared manifest SHA `2e0777e563e774e5b658fd74074acad5782f0460df2dba8a0653ff19b7a4f005`。518 项原 runtime 来源与装配层分别记录，后者仅替换 IR 和 77 份活跃配置，两归档保持；已审 v2 binary `e7ba503a…10f81` 不变。运行 1800/1740/30 秒、完整输入和 trace，独立 `ISLA_Z3_DIAGNOSTICS` JSONL 已增长，并执行五秒资源采样及 96/48 阈值。它单列诊断，不增加官方自然完成数；只有最终记录和资源日志能支持耗时归因与退出结论。

nan86f FVFTYPE 于 10:55:58 UTC 外限退出 124，无 JSON；调度在释放的正式位于 10:58:19 UTC 启动 a040 RFVVTYPE，预算同为 7200/7140/30 秒、两 worker、完整域与 trace。其 `entry-reuse-diff` 核与已审 RFW stage 只有目标 clause/CLI 差别。此时两个正式位均为 a040，隔离诊断单列；同 56cc 自然完成库存仍为 57/77，不能把新版本启动当作新增完成。

诊断首个冻结前缀的实际时长为 362.364740 秒。有限独证 `z3-diagnostic-nan86f-fvftype-analysis-independent-review-20260927/prefix-005m/review.json` SHA `2e6de8eef1a04b243115e60cbb494acc1c94a01fe4b65155958e866958953613` 独立重算 47,258 对完成操作、131 worker（128 已关闭、3 未关闭）及两次未完成操作；全部计数和区间相符。受保护 FFI 累计 701.210 秒，占所匹配 worker 观测窗口累计 718.657 秒的 97.572%；仅已关闭 worker 的比例为 97.565%。未关闭 worker 的窗口终点仅取最后已完成记录，不延伸至 capture，未完成操作不补 FFI 下界；该比例不代表进程墙钟、CPU 或浮点计算占比。跨 worker 的五次记录时间逆序来自取时与日志锁次序，不当作因果顺序。

精确发起点另包 `z3-diagnostic-nan86f-fvftype-analysis-20260927/prefix-005m-call-sites/` manifest SHA `cc329edea7aa25d6abae8e53e1a073f687a05a3a602f526cfaeda2cafff05dda` 联到实际 nan IR：`valid_reg_group` PC29 的末尾整数相等发起 458 次已完成 CheckSatAssuming，FFI 累计 216.367 秒；FVFTYPE 最终 guard 的 execute PC29144 为 189 次、104.953 秒。无 context 的 CheckSat 保留未知调用阶段。完整统计与边界见[性能记录](solve-fix-performance.md)。下一隔离候选只研究前者最终整数相等复用既有 `option(int)` 与 `eq_anything`；公共整数域、原 lazy 指数/取余顺序、caller 与失败路径保持，不由热点数据直接授予生产修改或加速结论。

### 公共接口与模型调用闭包的当前区分

a040 [接口核定](../../isla/target/float-solve-evidence/unified-backend-current-interface-audit-20260927/brief.md) SHA `340441961bdca776c0a6413aed2db51e6d8cf5012b3fa230a4a8e012146c2bd3`、逐项 `checks.json` SHA `d5430336a9227875924eda72262b3b975fa01189d46f3178d5816b1dc469e2eb` 已核现行链：190 typed 声明＝186 CPP native 绑定＋四个 Sail 工具，186 实例对应 82 个 FP 原语名；模型当前使用 97 个 FP typed 实例（45 个 FP 名）及四工具。P1 的 190/251 公有接口门、67 helper 回归和完整 77 项 solve 各有独立分母，不能互相替代。

七 adapter、generic FP NaN sort equality 在生产、a040 与最终公有包 `73ac…` 同字节；工具链插件/binary/补丁由 `009f…` 锁定。实际 adapter 与 Model 编译均启用 TLS/FAST_INT64/WIDE/EXTRA，SoftFloat 对象内三个环境符号实际为 TLS。该同字节链允许复用完整公有 fixture 门，未发现新的必需接口缺口；不另加完整 Model 逐一执行未使用声明的门。完整 Model 的全局 scratch/状态仍要求进程隔离，公有测试也没有声称数值域穷尽。

### valid_reg_group 最终比较组件及生产应用

最终 nan86f 诊断按实际 1800.55 秒外限退出 124、无 JSON；完整统计独证 `z3-diagnostic-nan86f-fvftype-analysis-independent-review-20260927/final-030m/review.json`（相对同证据根）SHA `9a9ea14e8d317bc86b26fccc6ab60ae7c0d716b99a807754e6d038e82cd8427c` 核 199,501 次完成、两次未完成、545 worker，匹配窗口中的 FFI 比例为 97.942108%，仅关闭 worker 为 97.904266%。146 分组/114 发起点及实际 IR 定位通过；`valid_reg_group` PC29 为 1789 次、843.498757 秒。该数字定位查询发起点，不拆分查询公式内部成本。a040 同预算、同 e7ba runtime 的独立基线随后已实际启动，下一版本比较保留同目标和输入域，不将 nan→a040 的归约改动混称单一比较改动。

最小候选只把 `valid_reg_group` 最后的整数相等改为已有 `option(int)` 的 `Some` payload 泛型相等。真实新旧小 IR 为 35/31 条指令；原 `EMUL_pow > 0`、lazy pow、unsigned、mod 及全部 `%i`/`%i64` 转换实际保持，最后增加两个 `Some` 并调用已有专门化的 `eq_anything`，不再调用尾部 `eq_int`。同构造器 payload 直接构造 SMT Eq，保留原算术前缀的查询和失败路径，没有新增 type 或 primitive。

组件独证 `valid-reg-group-final-equality-design-20260927/independent-review/certificate.json` SHA `1e7763cfd6beb0227e0228783c8934f15e72f3633b79038ef5cb14ce32fefa99` 通过两条完整符号配对路径、768 对实际具体输入、3904 次 CPP 执行、八条 strict/emit 命令及六个字节一致产物；九项静态和两项实际错误 IR 负控拒绝，七项全域 BV 范围证明与五项 SAT 负控、实际模零 panic101 保留。独审重新核出小运行尾部三次主动查询变为零，2293 最终依赖无漂移。Isla release 具体宽 shift 与 symbolic BV 的既有差异，以及 GMP `pow2` 使用 `mpz_get_ui` 的边界均明列，不把这些实现当理想无界指数；不签资源预算、SMT Error 轨迹或 Bool/Symbolic 表示逐步相同。

生产前件桥 `valid-reg-group-source-composition-20260927/certificate.json` SHA `e911d99d4de5d3c0fddc003a00ab3b303786af8c793ff74bd60fe394285bc745` 逐项核 931 源与组件独证；实际目录 950 个非目录条目，额外 19 项为 14 个 pyc、四个 SMT cache 和 `.git` 指针，全部显列。随后只应用 `model/extensions/V/vext_utils_insts.sail` 的该 helper，目标 SHA `e1401308d1ead856e38d053eda625bb094b8814f380d2a2b6832b6125d8515a9`，其余 930 源、nan FD 与归约 Vfp 保持。原源桥核的是应用前状态；应用记录将改变的 live 前像按原 SHA 精确投影到保存的 before 文件，旧证不改，也不声称应用后旧 live 清单仍零漂移。

实际生产完整普通 strict 179.08 秒、SYMBOLIC strict 185.84 秒均退出 0，检查前后及封包时 931 源一致。`valid-reg-group-production-20260927/handoff.json` SHA `cec4a3be3fadffa3519079c53e482d06551adc18c24c0166e48fca399d4f4fe0`、source-manifest SHA `cb5337cb170d935af6f496bae67f1de179abf860181bf49da09fa29fb4f7c1a4` 已交新完整构建。文件 729→730 行会影响 20 个 active region 及四个 `# Sail` 锚点，必须据新 IR 实际迁移；当前 runtime、严格配置和旧运行目录未改。下一完整 IR/CPP、strict/source 两独证、新 67 helper、89 条整指令及同预算诊断各自验收，不把组件 PASS 当作性能或 77 项完成。

该批完整构建随后成功生成 IR `fc4ce9091c91b654351672c89b51304afba0876cea435f251193b4537a686415`，`unified-backend-build/model-valid-reg-group-eq-build-20260927/model-build.json` SHA `6a7b98c27fecb16f67319ddca4d4999006dc745c353bc7f4121d06e95f3c675f` 绑定七项真实产物，79＋3 接口检查通过。完整结构独审、79 配置的真实迁移及 strict/source 独审已分别启动；helper 与原 89 条新回放已绑定实际产物准备，尚不把准备合同记为动态通过。

### fc4 完整构建与严格迁移的最终双证

上述两门随后分别封证。[完整 IR/C++ 独证](../../isla/target/float-solve-evidence/unified-backend-build/model-valid-reg-group-eq-build-20260927/independent-full-ir-review/certificate.json) SHA `b2fcac07432c4d1537f0bdd86f48961789dd3021b7c7d2ab0e4c35f0fb59be6f` 核 2049 个函数、3568 项声明，语义变化仅为 `zvalid_reg_group`；其余函数按精确源码位置迁移后相同。C++ 4544 个定义、目标体之外 8,827,884 个 token 和 25,107 个全局对象由同一双射核对，头文件相同；两次独立优化 fixture 重发、六项真实损坏负控和 14,227 项依赖最终核验通过。raw IR 仍有 46 个函数字节变化，decoder 闭包中的六个 `valid_*` 函数因源码位置加一而改变原字节，不能沿用 a040 阶段“闭包函数体逐字相同”的表述。

[strict/source 独证](../../isla/target/float-solve-evidence/unified-backend-build/model-valid-reg-group-eq-build-20260927/independent-strict-source-review/certificate.json) SHA `618b90ef6f084e76bdda99de91a43097684c421ccbec65a9350fa3f4bd58f888` 绑定 7517 项最终无漂移依赖，旧 live 前像的一项预期漂移另列并精确投影。79 份配置中 77 活跃、两份 d012 归档；129 区域保持 422 次真实命中、470 次重叠及 48 次包围关系排除，两个历史空区域保持。20 个区域跨 11 份配置迁移，四个 Sail 锚点迁移，新增退役为零。扫描补入 register 初始化中的四条 Jump，全源码定位 255332→255336；6,525,852 次真实 Rust selector 调用与未迁移负控相互核对，12 项测试、18 项负控通过。

两证共同绑定 [candidate freeze](../../isla/target/float-solve-evidence/unified-backend-candidates/valid-reg-group-eq-fc4c-20260927/candidate-freeze.json) SHA `2df4ce8295175f231ead616f41ffa1d12f115fcd2707919e63c95c3f01e85586` 和 v8 来源桥 `a25da90e15960c55f0cfa19ecb77dc771bf1284a8d7c46e3c27d2e005e6f088a`。新 67 helper 的 83＋17,586 三方回归、原五配置/13 组/89 条整指令回放已交实际执行；同 e7ba runtime 的 FVFTYPE 1800/1740/30 秒诊断单独准备。它们各自等待真实结果，双证不签数值、性能、全 77 或完整源码分母。

下一官方空位已定为 `FVVMTYPE`、`FVFMTYPE` 两个不同目标，各 7200/7140/30 秒、j1×2 worker，保留全域/R1/完整 trace、30/60/90 分钟检查点与五秒 96/48 GiB 资源保护。等当前 a040 RF/RFW 各自结束并且 fc4 数值门齐后启动，不中断旧运行。`vext_fp_vm_insts.sail` 的两个真实 SYMBOLIC clause 分别有两次和一次 `valid_reg_group` 调用，覆盖本轮改动；四种与六种比较通过既有 pure helper、mask 和 flags 回写，提供不同于归约链的未完目标进展。FVFMTYPE 的 nan86f 1800 秒历史轮已外限且无 JSON；FVVMTYPE 缺近期独立长轮。本排程不预设两小时足够或已获得加速，独立 FVFTYPE 诊断继续占另列诊断位。
