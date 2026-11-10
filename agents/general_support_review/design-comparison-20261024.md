# 通用支持分支的设计、流程与原工作区差异

2026-10-24。用户要求深入说明 `refactor/general-support-20261007` 相对 `7b7337b0dea0c4105644436a606dbec5ae9b3fea` 的设计／功能／操作背景，以及原 `isla/` 工作区与 `fix/general-review-20261008`＋`feat/float-only-20261008` 的区别。本轮只核对Git对象、当前源码与既有证据，不修改生产代码、不合并、不运行新功能测试。

核对步骤：确认分支实际SHA和工作区两层修改；阅读14提交的实际diff；沿solve-state初始化、执行、编码、物化、输出链路核查；复核MixedBits／宽值／缓存／采样及RV64域约束；对已解决组合候选逐文件比较；记录新结论和历史验证适用范围。版本与完整差异见 [机器可读证据](design-comparison-20261024.json)。

## 一、先分清Git对象

当前 `refactor/general-support-20261007` 和 `fix/general-review-20261008` 都是 `09fe5821142cfefb6760d93310337aa9fce68353`，所以这两个名字的已提交代码完全相同。通用分支相对7b7337b有14个提交：原8个职责提交＋后来6个修复；19文件，+2939/−376行，包含测试，不修改IR或Sail-RISC-V。

原 `isla/` 仍在 `feat/float-support@7b7337b`，有24个暂存路径，其中4文件还包含未暂存修改。这些最终文件已含大量通用与浮点实现；不能用HEAD的旧位置推断当前文件等于基线。`git diff`只显示未暂存层，`git diff --cached`只显示索引相对HEAD；比较完整工作区应读实际文件或使用HEAD到工作区的差异。

`refactor/general-support-20261007` 的工作树自身还有浮点残余，分支引用不包括它们。本次用干净的 `.worktree/isla-general-fix2-20261008` 阅读09fe582的代码，避免把残余当作通用提交。

用户所说的“fix＋float”不是一个现成分支名；这里使用已人工解决冲突的 `.worktree/isla-merge-check-20261008`：HEAD=09fe582，MERGE_HEAD=be1296b，暂存tree=`54fb4e8e26bcf654dc182a470f604439a1380028`。本轮确认其索引与该tree一致、没有未暂存差异，但仍未形成合并提交。

## 二、背景：符号执行究竟产生什么

Sail模型先生成IR，Isla读取IR和配置。`isla-lib`解释IR，把位向量、Bool、浮点等操作映射到SMT表达式，由Z3判断约束是否可满足；`src/isarch`组织RISC-V状态、目标指令、输出和汇编编码。

`solve-state`的入口是Sail的 `instruction` 联合类型构造器，例如某个整数或向量clause。它直接构造符号指令参数并调用 `zexecute`，不是先生成任意机器码再从取指译码开始执行。一个clause可能包含多个funct字段和mnemonic，符号参数仍可分叉。

初态S0是寄存器和CSR的符号表达式；执行一条路径后得到后态S1的表达式及路径约束P。`check_sat`只判断是否存在满足约束的赋值；SAT后取得的Model才给这些变量具体取值。该具体赋值是一个见证，不是该路径所有可能数据，也不是硬件已经执行过。

Checkpoint保存求解器声明和约束，可在另一个solver中接着求解同一组符号。Model completion则给未定值符号补一个具体选择：它让输出完整，不证明值唯一、覆盖充分或状态可从reset通过指令到达。

汇编打印与编码也是模型函数。`zassembly_forwards`把指令转为文本；`zencdec_forwards`／压缩版本把指令转为机器位串。它们可能读pre-state中的扩展／FS／VS等条件，故“执行clause存在SAT路径”不自动意味着任取一个模型都能合法编码。

## 三、最大变化：编码可行性参与见证求解

基线已有pre-state主动符号化、路径执行、SAT后生成汇编／编码及稀疏状态输出。其问题是执行后先选择一个模型，再拿具体指令请求编码，mapping还可能使用初始化寄存器，而非同一模型物化出的执行前态。某个任选模型编码失败后，可能直接放弃整条执行路径。

新流程在 `exec.rs::run_symbolic_execute_with_target` 和新增 `encoding.rs` 中组织：

1. 初始化寄存器／lets，建立符号前态和符号指令，加入目标状态域约束。
2. 对 `zexecute` 做符号执行，保留原执行frame、后态、路径签名与checkpoint。
3. 确认执行约束SAT后，从该checkpoint、符号指令和原符号前态继续运行普通编码器；不是先任取一个具体S0。
4. 编码成功的每个终态保存独立checkpoint；只有普通编码器的正常拒绝域进入压缩编码器，普通成功域仍优先。一个执行路径可以因此产生多个编码可行见证。
5. 在每个编码终态的solver中最终取Model，用它统一物化原指令、原S0和原execute frame的S1。
6. 用同一模型的具体S0再调用汇编／编码mapping，并核对具体编码等于符号编码的值；不一致直接panic。
7. 输出稀疏初态、完整初态、完整后态和请求构造器；编码／物化异常进入失败记账。

其核心约束是 `D(S0) ∧ P_execute(I,S0) ∧ E_encode(I,S0,bits)`，其中D是本实现明确施加的状态域，E是编码器成功域。后态仍来自原执行表达式，不是重跑另一条指令或从mapping后态取值。它不等于完整decode→execute→硬件重放证明，也没有保证所有编码／数据都枚举。

实际反例：VSETIVLI的执行路径未必约束入口VS，但编码guard要求VS非零。先选模可能取VS=0并丢弃整条路径，即使VS=1/2/3有合法解。09fe582把编码guard带入符号求解，保留合法替代S0。历史同IR的V128/V256对照曾从12条变0，再经此修复恢复12，见 [第二轮修复](fix2-20261008.md)；这是历史版本证据，本轮不新增动态PASS。

普通编码失败不是所有错误都被当作“试压缩”：只有严格识别的mapping默认MatchFailure才属于正常拒绝。嵌套MatchFailure、内部断言、Poison、Unknown和采样后的不完整mapping必须报错。

## 四、值表示：MixedBits从展示扩展到实际数据流

基线已有 `Bits`、`Symbolic`、`MixedBits`，但append的符号＋具体输入会立刻变成整个SMT concat。新append保留片段，例如 `symbolic9 @ concrete7` 存成两段。读取低7位即可直接拿到具体位串，跨段切片才构造所需表达式；空拼接不新增无效段，零长度切片返回空位向量。

这是表示优化，不应改变位串语义；但实际生产数据开始频繁出现MixedBits，所有只接受Bits或Symbolic的消费者都需要处理。最终6个修复中的一部分为此补齐整数加减、原有IEEE／整数到浮点入口、旧SoftFloat helper、访存地址、寄存器向量索引及Monomorphize。

大多数消费者复用 `replace_mixed_bits` 归一化，而非重写一套分段算法。Monomorphize还须把归一化符号写回frame，确保后续checkpoint/fork继续约束同一变量，否则会静默跳过枚举。负索引、大索引截断、high/low反转和越界明确检查，不能通过 `as u32` 截断成看似合法范围。

因此它不只是“拼接更快”：它是跨解释器、primop和内存接口的表示契约调整。原8提交中没有补齐消费者，后续修复是最终分支的一部分，不能只挑早期append优化就认为兼容性已完整。

## 五、宽位值：格式化与模型物化是两个问题

`fmtval.rs` 把 `lower_u64`逐位取值改为 `BV::to_vec()`，避免具体位向量超过64位时高位错误。这个修改解决输出位宽，不等于解决Model物化。

生产isarch常用B129；SMT中的256／512位值可以存在，但旧 `Model::get_val` 强制把具体结果变成单个B129，因此超宿主位宽报Type。原先稀疏输出有时避开这条链路，新增完整S0物化后，合法向量路径也可能因此丢失。

最终版增加 `Val::from_bits_slice`：在宿主上限内返回Bits，超宽则分成多个具体MixedBits片段。输入bit数组低位在前，分段列表高位在前，与位串拼接语义对齐；结构体／list／vector／ctor递归物化也使用该路径。Arbitrary的默认零值同样不能构造超宽单个B129。

这使“把完整向量初态交给具体mapping”可行。它不是把VLEN固定成128、跳过宽寄存器，或声称任意位宽都被单个宿主整数支持。

## 六、模型值缓存与采样历史

`Model`按符号缓存已经读出的具体Bits/Bool/Enum；同一Model被用于指令、多个状态字段和编码检查时，重复查询不再反复进入Z3。缓存是每个Model对象私有的，不跨路径或不同solver；切换complete_model时清空。Arbitrary不缓存，避免在开启completion之后仍返回旧“未定值”结果。历史重复查询20000→1只支持局部收益，不能当作端到端加速数字。

路径状态新增 `sampled_execution_domain`。真正提交分支采样或Monomorphize保留当前模型而舍弃SAT余域时置true，随frame快照继承。它与fork计数不同：即使forks=0也可能已经丢弃余域。mapping和hart能力探测读取该标记，拒绝把不完整探索当作确定结果。

这个布尔量是采样历史，不是新增采样策略，更不是独立 `feat/witness-randomization` 功能；该随机化分支不属于09fe582。该标记也不能证明主solve输出已完整覆盖所有状态。

## 七、状态输出和错误的合同

每条JSON保留 `isa-state` 稀疏初态，并新增 `requested-instruction`、`isa-state-complete`、`isa-state-post`。稀疏初态仍用于突出约束相关输入，完整字段是在同一Model中completion后的具体见证。后态只覆盖Target选入本次pre-state的寄存器，不是所有IR寄存器／内存／平台状态的通用快照，不能将其与内存分支的pre-memory/post-memory混为一谈。

顶层 `state-domain` 说明此次施加的架构域规则，不代表硬件已验证，也不是完整性证书。`requested-instruction`是稳定构造器文本，字段排序避免HashMap迭代顺序造成无意义差别；它不是机器码反译码结果。

新增的错误记账保存first_error，处理完仍可写出部分JSON，随后使clause／整体solve失败。不能只看JSON存在或gen非空。编码异常、状态物化错误、Unknown等不再仅日志后静默成功；不再catch Model内部panic来伪造正常完成。但原execute的AssertionFailure／MatchFailure仍有显式过滤例外，不能说所有终态都变成非零退出。

solve-state自动使用已有 `assertions_to_jumps` 转换，让符号assert真／假域都能进入路径探索。它不等于assert失败一定写入gen；collector仍有上述过滤。转换还会往IR尾部附加handler，因此默认mapping拒绝不能只匹配旧固定尾巴。新版核对当前函数、唯一默认MatchFailure位置、源位置、handler跳入／回跳结构，既保留压缩编码接续，也不吞真正内部错误。

`Illegal_Instruction`本身是模型的正常ExecutionResult，可作为预期异常见证；它与实现Type错误、Unknown、崩溃是不同层次。完全不可编码的非Illegal终态会记失败。

## 八、RV64架构域：通用于RISC-V，非架构无关

基线已经有主动符号化和vtype/vl配对约束；不能把整段现存向量约束都归功于本分支。新增部分主要是 `Rv64Domain` 和hart能力驱动的特权／mstatus规则。

实际运行IR内的 `zhartSupports(S/U/H)`，要求唯一具体Bool终态、没有寄存器／内存依赖、没有fork或采样。根据能力限制cur_privilege：始终允许M，按S/U/H组合决定S、U与虚拟特权枚举。SXL／UXL在支持时为RV64编码2，不支持时0。

MPP排除保留编码2；无S时排除1；0和3保留。即使未实现U，也保留当前Sail从全零reset得到的MPP=0例外，并在manifest中说明。CSR写入的WARL/legalize域不能直接替代reset及所有可达状态域。该规则只是明确字段范围，不证明完整mstatus组合可达。

这些变化会实际缩小可生成初态域，是功能／策略变化，不能一概称为保持全部旧行为的纯重构。

## 九、原工作区与“fix＋float”的当前精确差异

本轮逐文件内容及Git模式核对结果与10-08冻结记录一致：原工作区1001文件／链接，组合候选1015；986相同、15个已有文件不同、新增14、没有缺失原路径或模式差异。详细文件哈希见 [对照证据](design-comparison-20261024.json)。

原工作区已经包含MixedBits拼接、宽值格式化、Model值缓存、采样历史、完整状态schema、初版mapping严格化及RV64域约束，也包含浮点primop、fcsr、官方名单和FD入口。组合不是从零增加这些能力，而是把拆出的功能接回后，再纳入独立复审修复。

组合相比原工作区的重要增量：

1. MixedBits整数加减、地址／具化等消费者兼容，超宿主位宽递归物化。对应error/executor/ir/memory/primop/smt六文件。
2. 新 `encoding.rs` 与exec/mod更新：编码可行性先求解，合法替代初态和压缩域接续，具体同模型核验，first_error失败退出。原工作区仍是取模后检查编码的旧实现。
3. target修复无S时的MPP=1，并保留reset例外；测试结构也因浮点独立基线调整而不同。
4. 五份IR修复：默认rv64d恢复快速FPR getter/setter的扩展检查、表示转换、Dirty和callback；另外四份旧IR补齐普通helper兼容并修状态路径。原默认IR SHA256为d0123541…，组合aea104c8…。
5. legacy runner追加MixedBits规范化，避免表示差异导致误报。

新增14文件为4份通用集成测试、encoding.rs、IR迁移脚本及8份float_ir测试／配置。原工作区没有只存在于它而被组合丢掉的路径；相同的986文件包括最终 `isla-lib/src/primop/float.rs`、fmtval、采样/frame、FD配置、run.mk和官方名单。这说明差别主要是复审修复和组合接线，不是新增另一套浮点算法或新内存一致性功能。

两个组合冲突仍应按已有解决方式理解：float.rs保留新浮点实现及消费者兼容；exec.rs保留联合编码求解，并把FS/VS见证偏好放在每个编码可行checkpoint之后。偏好若提前加入，可能把唯一合法编码域筛掉。任意重新merge不是自动得到tree54fb4e8e。

## 十、如何查看／使用与验证边界

从根目录执行以下只读命令可区分对象：

```sh
git -C isla diff --stat 7b7337b refactor/general-support-20261007
git -C isla log --reverse --oneline 7b7337b..refactor/general-support-20261007
git -C isla diff --cached --stat
git -C isla diff --stat
git -C .worktree/isla-merge-check-20261008 status
```

要理解执行过程，可先在对应独立候选核对实际IR／配置，再用MRET或ITYPE等短clause观察输出；向量例子明确指定VLEN并检查完整前后态宽度，浮点使用已提交FD入口和配置。现成测试命令和参数见 [第二轮修复](fix2-20261008.md) 及 [浮点修复](../float_only_review/fix.md)，不要在原output上盲目覆盖既有证据。

历史09fe582验证包含89库＋25bin、MixedBits／物化持久测试及V128/V256的MRET/ITYPE/SRET/VSETIVLI；通用＋浮点候选另有93库＋25bin、浮点10和集成15等限定结果。全库旧Z3 enum sort问题、全clause、全部浮点、RV32公共入口和硬件仍有各自边界。今日只重新确认源码／版本／文件树，没有重跑这些动态测试。

若后续推进整合，09fe582＋be1296b的已解决候选比直接提交原dirty工作区更能保留这些复审修复；但它仍是待提交组合，且不包含完整内存一致性或独立见证随机化。是否接纳RV64域约束、断言探索及更严格失败策略，应作为明确设计选择审核，不能只看“refactor”分支名。
