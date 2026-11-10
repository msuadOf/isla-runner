# float 固定版本独立审阅（2026-10-30）

## 独立结论

浮点支持的基本结构可接受：Sail保留指令、寄存器和异常语义，Isla提供FP/ITE原语与最终求解模型的具体化；本轮定向数值、flags、boxing、FPR和BF16活动元素检查未发现新的数值错误。但是，**当前JSON仍不能按“覆盖固定Sail模型控制流语义，并且所有文本均可由标准GCC/Clang一致汇编”验收**。

本轮确证新的双工具链失败：BF16非法寄存器布局已经进入JSON，GNU接受其助记符，Clang拒绝。另有默认数值见证只覆盖qNaN退化情形的实测覆盖缺口，以及通用入口把未续执行的ExecuteAs作为finished生成后态的缺陷。后者影响根float所带通用JSON能力，**不属于float77算术回归**。未阅读memory审阅报告，未改生产代码、分支、提交或现有output。

受审根为 `.worktree/runner-float`；下文 `isla/`、`sail-riscv/` 均相对于该根：

- 根：`90bb72683cec60fd44ff0d29dabef773d8096a2d`。
- Isla：`8fae36a90e77ec51a2ef165c79d60b3377ce18b2`。
- Sail-RISC-V：`afff3822cdaca206b325a39dfe114e28d5c63bf6`。
- 实测IR SHA256：`855deccc66c96d57f16a0a91a4279e8488b16ab3a2a9eeccc605ebce082c389b`。
- 实测isarch SHA256：`e9fd5a0bba97c736e88f2bb06f3d46c542de0f10744b9d644b38731ffa279204`。`isla/target`链接到获准复用目录，`.d`记录指向当前runner-float源，binary时间晚于当前源；本轮未重新构建。
- 审阅前后三个受审工作树均干净。原根dirty状态保留。

## P1：非法BF16向量见证的汇编文本被Clang拒绝（已证实bug）

位置：`sail-riscv/model/extensions/bfloat16/zvfbfwma_insts.sail` 的 `mapping clause assembly = VFWMACCBF16_VF`（第221行），以及 `isla/src/isarch/exec.rs:992` 的助记符收集和 `:1218` 的JSON生成。

触发：VFWMACCBF16_VF在合法SEW=16、LMUL=1/4的初态，生成 `vd=vs2` 或 `vm=0, vd=v0` 的非法路径。模型正确返回Illegal_Instruction，但映射仍输出普通助记符：

| JSON文本 | JSON机器编码 | GCC | Clang22.1.8 |
| --- | --- | --- | --- |
| `vfwmaccbf16.vf v1, f14, v1` | `0xee1750d7` | 接受且匹配 | 拒绝目的/源寄存器组重叠 |
| `vfwmaccbf16.vf v0, f30, v30, v0.t` | `0xedef5057` | 接受且匹配 | 拒绝目的寄存器组与mask重叠 |
| `vfwmaccbf16.vf v2, f14, v2` | `0xee275157` | 接受且匹配 | 拒绝目的/源寄存器组重叠 |

证据：[完整双工具链检查](assembly-extra.json)，90项中86项通过，4项Clang失败（mask例在vl0/vl1各出现一次）。CLI生成本身退出0、summary=finished，故不能用生成成功代替汇编合同。相关原始JSON为 [vl0](bf16-vl0/output/rv64_zVFWMACCBF16_VF.json) 与 [vl1](bf16-vl1/output/rv64_zVFWMACCBF16_VF.json)。

影响：这些真实模型非法分支不能通过用户要求的双工具链文本链路重放。已有合法布局的BF16汇编检查不能覆盖此范围。

最小修改建议：保留非法路径、机器编码和返回值；对于汇编器静态拒绝的布局，使用标准`.insn`字段形式，沿用当前FCVT_S_BF16的处理方式；有效布局继续用助记符。补上述非法布局的双驱动编码往返回归。不要删除这些JSON或仅改成合法寄存器，否则会损失控制流见证。本轮未实施或验证建议文本。

## P1：默认浮点数据见证缺失可达条件（已证实覆盖缺口，不是数值bug）

位置：`sail-riscv/model/extensions/FD/fdext_regs.sail:49` 的nan_unbox ITE；`model/prelude/ieee_fp_primops.sail:204`、`:209`的ITE接口与普通Sail函数体；`model/core/ieee_fp_exceptions.sail:21`起的严格布尔分类；`isla/src/isarch/exec.rs:947`、`:973`、`:1229`的每个终态/编码checkpoint取单个最终模型。

实测默认F_BIN_RM_TYPE_S无采样、无配额，退出0、52条JSON、summary=finished。其中40条Retire_Success **全部**从FPR读取未boxing的0，全部变成canonical qNaN，结果全部为`0xffffffff7fc00000`，flags无一次变化。剩余12条是动态FRM非法路径。见[逐条独立统计](fadd-coverage.json)。

这不是“尚未测全”的泛化描述：相同IR、runtime与入口，加配置化boxed 1.0初态即可生成24条退休见证，包括FADD.S的1+1=2、FSUB.S在RDN下的-0等；[对照JSON](fadd-boxed-normal/output/rv64_zF_BIN_RM_TYPE_S.json)证明普通有限数的可行条件存在，却没有被默认批次见证。默认FLEQ_S四例也没有NV；配置化sNaN两例确实得到NV=1、FS=Dirty、SD=1。

原因：ITE/严格布尔原语正确保留公式语义，同时把普通模型的数据条件合并进SMT表达式；执行树的终态数没有等价地枚举这些条件。当前`model-coverage=not-measured`如实说明限制，`finished`并非错误地宣称全覆盖，但仍不能满足用户目标。

最小修改建议：保留当前执行器、FP和ITE结构，增加**配置化数值域批次与数据条件见证**：boxed/unboxed、±0、有限正常/次正规、±Inf、qNaN/sNaN，以及flags置位/保持、FRM合法/非法、向量lane活动/屏蔽条件。针对选定源码谓词或SMT条件，查询真假两侧是否可满足，并记录见证或UNSAT/超时；不要全局硬编码一组有限值、不要把它们当完整浮点域，也不要仅重新增加helper例数。现有终态采样和数据条件覆盖须分开计数。

另一个入口边界：`model/extensions/FD/fext_insts.sail:31`的rounding_mode只表示0/1/2/3/4/7，AST clause求解不能表达机器指令静态rm=5/6；这些编码应在decode→execute级别记覆盖义务。不能把动态FRM=5/6的Illegal见证当作静态rm=5/6译码分支。

## P1：ExecuteAs未续执行却输出finished后态（已证实通用JSON缺陷）

位置：`isla/src/isarch/exec.rs:731`只把Poison/Exit/Suspended记为未完成；`:765`接受其它Finished返回；`:1197`直接查询该frame后态并在`:1229`加入gen。模型依据：`sail-riscv/model/extensions/C/zca_insts.sail:40`，`model/postlude/step.sail:118`，`model/extensions/I/base_insts.sail:158`。

[确证见证](c-addi4spn/output/rv64_zC_ADDI4SPN.json)：`0x1fe0`，文本`c.addi4spn x8, x2, 0x3fc`；所有GPR初态7。JSON返回具体ExecuteAs(ITYPE(...ADDI...))，x8后态仍7，summary=finished。原模型step会再执行该ITYPE，按源码必须得到x8=`7+1020=1027`（`0x403`）。[自动核对](result-checks.json)固定了此差异。

这是执行边界遗漏，不是最终SMT模型取值错误：当前JSON如实记录了**第一次zexecute调用**的后态，但它不是该机器指令完成执行的后态。`ret_val`标识了ExecuteAs，仍不能把这种记录无区分地作为完整指令见证。当前FD压缩load/store源码直接调用execute，未发现float77使用ExecuteAs，故不归因于新浮点算术。

最小修改建议：按固定Sail step的同样规则，在相同符号执行状态与预算下继续执行ExecuteAs载荷，最后统一具体化；保留原始请求编码。若暂时不支持，至少把此类条目标为未完成并从可重放gen中区分，summary=partial。不要用新的初态重启载荷执行。

## P2：编码过滤统计未接线（已证实结果合同缺陷）

位置：`isla/src/isarch/encoding.rs:104`至`:107`只保留compressed.encoded，最终compressed.rejected被丢弃；`src/isarch/solve_summary.rs:16`声明encoding_filtered_paths，但全源码没有生产写入点，只有merge累加零值。`docs/json-results.md:3`却解释该字段统计编码守卫拒绝路径。

例如FLEQ的执行体本身不检查FS，编码守卫要求currentlyEnabled(Ext_Zfa)：符号初态中不可编码的FS关闭域会在mapping阶段排除，但新JSON仍一律显示encoding-filtered-paths=0。显式FLI FS=0探针得到32 errors、0gen、partial，说明不同分组形态还会把无合法编码的完整终态记为error；此处**未证实丢失合法编码路径**，不把合法性过滤本身列为语义bug。

最小修改建议：编码接口返回成功checkpoint及最终拒绝数/来源，将该统计交给同一个collector；保持非编码域过滤与执行错误分别记账。是否partial应遵循声明的覆盖域，不应仅因合法性过滤就强制partial；更不能保持一个永远为0却声称已测量的字段。

## P2：state-domain未披露实际RVV域（已证实元数据缺口／配置域选择）

位置：`isla/src/isarch/target.rs:807`无条件加入合法vtype/vl或vill/vl=0的限制，`:812`至`:814`在额外RV64特权域关闭时直接返回`status=not-applicable`。本轮所有默认/向量JSON均观察到这个字段。

这些约束本身是可接受的架构初态域选择，不能据此指控求解不正确；但“not-applicable”没有说明实际始终生效的RVV域。显式initial_state与const primop由输入配置哈希可追溯，但用户仅审阅JSON时仍无法判断哪些源码非法上下文被域限制排除。

最小修改建议：分项记录RV64特权域是否开启、RVV合法上下文策略及VLEN/ELEN；把来源定位到已存在的域构造函数，避免复制第二份规则。域内覆盖与模型任意输入覆盖分别验收。

## 本轮验证与可接受能力

精确命令、工作目录、退出、二进制/IR/config哈希在每个探针的`result.json`；入口为[probe.py](probe.py)、[probe_extra.py](probe_extra.py)、[probe_contract.py](probe_contract.py)、[probe_quota.py](probe_quota.py)。每次使用独立本目录输出，`-T 1 --timeout 25 --tastic qfaufbv`，外限40秒，`LD_LIBRARY_PATH=/home/linuxbrew/.linuxbrew/opt/z3/lib`。

- 14个有界CLI探针完成，无外限超时；其中FLI FS=0按预期退出1，其余退出0。包含一次误用助记符作配额key的配置对照，该key不匹配返回类，保持4例；正确的`Retire_Success=0`另跑得到0gen、omitted-cases=4、partial，未把误配当bug。
- 显式分支采样FLEQ为1gen、sampled-paths=1、partial；配额裁剪如上。Poison与运行错误静态分支已有partial核账，本轮没有强制产生Poison或最终查询超时，不能给新的动态PASS。
- 标量FLEQ normal/sNaN对照和BF16 vl0/vl1、masked/unmasked对照显示flags与FS/VS/SD后态符合所查源码；[13个结果断言](result-checks.json)通过。向量仅固定SEW16、LMUL1/4、vstart0、VLEN128，无全lane/全vstart/全LMUL结论。
- 新FLEQ及四算术JSON的GCC/Clang编码比较[112/112通过](assembly.json)。新FLI_S、两个BF16向量批次及C_ADDI4SPN共[90次中86次通过](assembly-extra.json)，4次失败就是首项问题。工具为GCC14.2.0+19、Clang22.1.8；实际驱动命令和stderr逐条保留。FLI_S32常量本轮64次均通过，旧FLI文本错码没有在当前版本复现。
- [IR来源核对](artifact-check.json)：manifest列出的IR/config/model文件673次哈希检查全部匹配（跨artifact含重复，不是673个独立文件）。当前五份IR与固定模型的来源声明一致，旧拼接IR错配未重现；未独立重新生成IR，也未证明无.git工具链源快照与版本字符串完全一致。
- `exec.rs:947`至`:1207`中编码参数、完整初态、后态和返回值使用同一个最终Model；本轮定向JSON亦符合这一关系。没有证据支持把现有最终模型具体化修复回退。

本轮未重跑已有1615 helper/180 state/20 guard大回归，不把其数量当覆盖分母；未做普通C++与SYMBOLIC全指令双后端重放、全部77 clause、所有向量数据条件或硬件验收。

建议先修BF16非法布局的文本合同，再解决通用ExecuteAs后态边界；随后接编码/域元数据，建立配置化条件见证及覆盖账本。浮点数值和状态实现可保留当前分层，现有正面证据支持继续使用定向、可追溯的见证；完整源码控制流覆盖和所有生成文本双工具链验收仍不能签收。
