# general＋float 相对7b7337b的代码复审

受审版本：基线 `7b7337b0dea0c4105644436a606dbec5ae9b3fea`；general `ef882f01e0208de13fd2224fc83b30e13acee261`（16提交、21文件）；float `be1296bbe66ca03a3c17c17ad7b9039a9cefc9c9`（8提交、30文件）。2026-10-29执行。

结论：主体结构和改动方向可以接受，但当前组合仍有一项明确的集成问题，建议修完再正式合并。未发现本轮定向验证内新增P1数值/状态回归。若“结构不变”指完全不改变流程或接口，则两分支不满足：general增加编码求解阶段，float移除原专用helper分派、改用普通IR函数；这些是明确的功能变化，不是纯重构。

## 发现一：P2，新增ISAConfig字段使浮点独立runner无法编译（新增组合问题）

general的8948cc4增加`initial_state`与`initial_state_rv64_domain`。float的两个独立crate仍在`test/float_ir/runner/src/state.rs:26`及`test/softfloat_legacy/runner/src/main.rs:24`手写旧ISAConfig字面量，常规根crate测试不会编译它们。

真实执行`python3 test/float_ir/run.py --output <目录>`，build退出101，两处E0063：缺上述字段。旧09fe582组合的历史PASS不能用于证明新ef882f0组合兼容。

建议在两构造器各补`initial_state: Vec::new()`、`initial_state_rv64_domain: false`，合计4行，不需要新建构造器/配置框架。本轮仅在隔离候选添加该诊断补丁后继续验证，未修改正式分支；[原始编译失败](float-regression/build.log)、[最小补丁](evidence/runner-compatibility-only.patch)。修补后五份IR的helper/state/guard与装配冲突检查全部通过。

## 发现二：P2，ret_val仍有未物化的符号（既有缺口，本次未修复）

`src/isarch/exec.rs:740`在选择编码checkpoint/最终Model之前执行`let ret_val_str = ret_val.to_str(shared_state).to_string()`，随后在JSON里复用该字符串。指令、初态、后态和编码已采用最终Model，ret_val没有。

实际`make solve-C_ADDI`退出0、1gen，机器码16'h0f81，但ret_val为`ExecuteAs(ITYPE({... Sym(108) ... Sym(109) ...}))`；requested-instruction已经是具体C_ADDI参数。它不能作为完整可重放的返回指令，单看成功退出会误以为payload也被具体化。

这段先to_str的做法在基线已存在，不能算本次引入的新回归；新完整见证接口仍未填平这个缺口。建议在同一个最终Model内先`model.get_val(ret_val)?`再格式化，并补带符号payload的collector回归。具化返回值与递归执行ExecuteAs是两个任务；即便具化后，也不能宣称已完成其续执行或硬件重放。[原始C_ADDI输出](evidence/rv64_zC_ADDI.json)。

## 设计建议：FS/VS偏好可迁至TOML

float单分支的`src/isarch/exec.rs:759`开始，组合候选约818行开始，仍按official_float77名单在Rust中检查mstatus位14:13、10:9，并优先选择3。它在SAT时才追加，UNSAT/Unknown时保留原路径；组合时必须放在每个编码可行checkpoint之后。

按用户“Isla只理解位、不知道FS/VS字段”的原则，建议后续删除这段特例，确实需要Dirty初态的任务由TOML位模式配置。它目前不是覆盖显式配置的确证bug：本轮明确配置FS=1/VS=0后，FLEQ_S的16条初态全部保持1/0；不过未配置的符号初态仍被内置策略偏向Dirty。删除前应复验不依赖该偏好的可编码性与输出分布，不能把原check_sat_with的偏好不加区分地变成默认硬约束。

## 合并边界

直接在干净general ef882f0上merge float be1296b，有两文件内容冲突：`isla-lib/src/primop/float.rs`、`src/isarch/exec.rs`。不能只取ours/theirs。

float.rs应保留float的参数类型校验和bv_arg路径：该路径已支持MixedBits，因此吸收了general的转换兼容修复，不应恢复已退役的专用SoftFloat分派。exec.rs应保留general的联合编码求解/同模型物化/错误传播，同时把float的见证偏好放到每个编码可行checkpoint之后。两侧回归测试均保留。

本轮隔离工作树`.worktree/isla-general-float-review-20261029`从ef882f0准备merge，以上两文件复用已审阅的09fe582＋be1296b旧组合解决结果，其余自动三方合并。最新initial_state和类型检查保持。原始已解决index tree为6323cdba70521f79c72d73cd477669f8e771f939；4行runner诊断修补在unstaged层单独保留。没有真正合入/提交/发布组合，也没有更改原工作区或父gitlink。

## 对结构与合理性的判断

- general的MixedBits、宽值物化、Model缓存、采样标记：沿用既有Val/Model/Frame与replace_mixed_bits，必要修复有消费者测试，不是另建执行器。append开始返回MixedBits会扩大消费者要求，故这些兼容提交应成套保留，不建议只摘第一层优化。
- general的编码求解：执行→取一个模型→检查编码，改成执行→同约束下求可编码分支→同一模型物化。流程确实改变，但解决的是合法替代解被任选模型丢掉的问题，复用现有IR执行/checkpoint抽象。新增encoding.rs职责明确，可以接受；长期可清理exec.rs大段嵌套和历史调试注释，没必要为本轮review重写框架。
- general的初态配置：在现有Target::setup_pre_state之后对同一符号加位约束，未增加架构字段映射。额外RV64特权域默认关闭且可显式启用；原vtype/vl规则保留。它不是保证任意符号组合合法或全域可达的机制。
- float的原语：继续在既有primop/SMT层做格式/舍入/运算，普通Sail helper承载RISC-V数值和flags语义。移除原Rust helper特判，方向更符合既有普通IR调用结构。fcsr与FPR副作用修复属于功能正确性所需，建议接受。
- float的IR：不是手工逐条改机器执行器，但五份生成IR改动很大，包含冻结组件装配而非同一完整源码快照重生。运行正确性已有定向证据；后续正式版本维护宜用对应Sail/Sail-RISC-V提交统一重生，补齐可重复生成链。旧v512文件实际VLEN256与旧IR其他历史语义仍在，不归本次新增回归，也不由helper测试自动验收。

## 本轮实际验证

组合候选（主库/核心/集成在4行runner修补之前）：isla94/94、isarch25/25；Brew Z3下核心267/267，明确跳过三项既有enum checkpoint测试；持久集成20/20；cargo fmt与diff检查通过。核心测试较纯general少12项，因为专用SoftFloat实现及其原单测被普通helper回归替代，不是测试静默丢失。

runner原始build失败后加上述4行兼容字段，再运行`test/float_ir/run.py`：22个脚本检查退出均0，五份IR的helper1615/1615、state180/180、guard20/20通过。结果限列定用例，不是所有浮点输入的全域证明。

make公共入口，T1、SOLVE_TIMEOUT45、OUTER_TIMEOUT60s、qfaufbv：默认IR MRET4、ITYPE32、C_ADDI1、VSETIVLI12、FLEQ_S16、FCVT_S_BF16 63、FLI_S32，各退出0。另用TOML将FS设1、VS设0，FLEQ_S16且每条初态保持指定值。V256 IR的MRET4/VSETIVLI12，各退出0，vr0实际宽度256。BF16本轮63与旧float-only历史39基于不同求解流程/域策略，不应凭数量差异判错或称覆盖增长。

未运行全部77浮点clause、全部模型分支、硬件差分或整体性能验收；核心三项enum问题仍按历史跳过。general含dirty浮点残余的工作树没有被当作本轮受测提交。完整命令、退出、tree与IR/配置/补丁证据见[evidence/summary.json](evidence/summary.json)、[helper/state/guard检查](float-regression-compat/checks.json)。

建议决策：接受两分支的主体设计；正式合并先补runner构造器并按上述规则解决冲突。ret_val具体化建议作为单独小修，FS/VS偏好迁TOML作为按用户原则的后续清理。不要将本结论写成“代码结构完全未改”或“全量验收通过”。
