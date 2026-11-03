# float→memory 合流准备独立审查

结论：可按隔离候选方案继续准备，不能直接在原memory工作树合并。三仓预检均发现冲突；模型另外有两处自动合并留下的函数类型合同不兼容。尚未实施合并、构建、IR生成或语义验证，不给语义PASS。

## 固定输入和工作树

2026-11-03独立读取实际HEAD、gitlinks及porcelain状态：float根0665526d／Isla591693df／模型0f7b8fbc全部clean；memory根31ef3b9／Islabdd047bc／模型c70482a7符合计划。memory仅Isla的README.md和scripts/run.mk未提交，模型clean。未触碰master dirty树或其他研发树。

两个子模块对象库彼此独立，memory Isla原库不包含591693df；独审用进程级GIT_ALTERNATE_OBJECT_DIRECTORIES只读访问float对象，未写原库配置或执行fetch。主预检在独立bare对象库产生虚拟树；独审另算两侧改动路径及共同祖先，核对预检stdout/stderr哈希。

共同祖先为根a85d6dfb、Isla0008fae76、模型4f2ac293。原始状态与增量证据见[independent-worktrees-dirty.json](independent-worktrees-dirty.json)、[independent-versions-deltas.json](independent-versions-deltas.json)；与主预检输入、共同祖先、两侧路径、重叠路径及输出哈希全部相符，见[independent-preflight-checks.json](independent-preflight-checks.json)。

## 实施前必须处理的事项

1. **模型自动合并不等于可编译。** 虚拟树58e9e610把get_start_element改为返回nat，但float新增SYMBOLIC VFMERGE和init_masked_source仍match Ok/Err，分别在vext_fp_insts.sail:2591与vext_utils_insts.sail:429。这是静态类型合同矛盾。候选应让这两处直接接收nat，保留memory的超界vstart不陷阱约定，再做ordinary及四配置SYMBOLIC严格检查。源码上下文见[independent-model-contract-context.txt](independent-model-contract-context.txt)，完整调用检索见[independent-model-call-sites.txt](independent-model-call-sites.txt)。尚未运行Sail类型检查，因此结论限于源码合同。
2. **模型19项workaround冲突。** 三个重叠Sail生产文件没有文本冲突，配置仍不能干净合。多数冲突是坐标或注释锚点，两侧还存在region集合差别，例如float vxtype/vexttype增加init_mask相关region；应逐项保留原有预算意图、映射合并后源码并核全部配置/region/锚点，不整文件取一侧。固定数量需由合并后实际集合统计，不照抄历史130或132。见[independent-model-conflict-blocks.json](independent-model-conflict-blocks.json)、[自动合并相对float的生产增量](independent-model-auto-merge-vs-float.patch)。
3. **Isla15项冲突。** 包括6个Rust文件、run.mk、五IR、manifest、两文档。exec.rs有15块、target.rs有6块，涉及内存事件、pre/post-memory、值域/编码批标签、diagnostics/partial、最终求解模型、完整寄存器前后态、CSR与initial_state、ExecuteAs续执行及三表示；不能只并字段或整边取。execution_limits测试说明、frame接口和SMT tactic/种子能力初始化也须同步。无文本冲突的memory.rs/config.rs/executor.rs等仍应沿调用关系核接口。见[independent-isla-conflict-blocks.json](independent-isla-conflict-blocks.json)。五IR及所有来源sidecar必须从合并模型重新生成，不能只替换冲突manifest或文本合IR。
4. **dirty配置与float重叠。** 原补丁见[independent-dirty.patch](independent-dirty.patch)，SHA-256为e67728f312f49c5505cd651be547c5514064a5709e78432df865b06dbc93e5d8。Z3前缀、RUSTFLAGS与qffp/qfaufbv分配的核心新增行在float已存在；float构建改用tracetool，不能套回旧ITRACE构建行。README官方Z3段逐行相同，策略说明部分同义但不逐字。应在隔离候选逐项核保留效果与来源，原memory两文件保持字节不变；当前末次哈希复核未变。run.mk必须明确兼容memory既有SOLVE_CONFIG调用及float ISA_CONFIG目标配置，make -n核访存/浮点/压缩三个入口，核显式TASTIC与配置覆盖。主追加的隔离dirty预检把两文件写入无ref临时提交，独审逐字核临时blob与原dirty一致、仅两文件变化；叠加后16项冲突，比纯提交预检多README，原15项仍在。见[independent-dirty-and-old-memory-fixes.json](independent-dirty-and-old-memory-fixes.json)。
5. **根9项冲突。** 两gitlink等子模块合流提交形成后再写；topic-version仍为memory，components填新组合SHA，IR哈希填本轮生成产物。排除列表、来源分支、publication、status与validation必须按实际组合重写，不能沿用“排除float”或把float限定PASS署到合流版。GIT/README及历史结果保留两侧有效内容，旧日期/版本结果只作历史证据。

## memory既有修复证据的版本边界

独立核对coordinated_memory_fixes_20261102/final-build-inputs.json的四个生产Rust源码哈希：memory.rs、memory_model.rs、target.rs、exec.rs均与当前目标不同；当前目标四文件逐字等于bdd047bc已提交版本。旧F1–F5修复是在其他dirty工作树验收，不能因为记录的HEAD同为bdd047bc就认为已在本目标具备。本次固定合流不自动取其他研发改动；旧具体/符号内存、GPR导出、返回值等问题继续按基线单列，如阻断本轮验收则报告边界，另行决定修复范围。哈希证据同上。

## 后续最小实施分解与验证

1. 原树只读复核SHA/dirty哈希；在有空间的文件系统建立独立模型和Isla候选，不复用共享target软链，不拿在途memory修复当固定bdd047bc输入。
2. 先解模型两处类型适配与19配置冲突，由Sol独审实际源码、纯数据77处回退保持、OPEN不改策略及region映射；再ordinary strict和RV32/RV64 VLEN128/256/512四配置严格生成。
3. 最小拼合Isla Rust生产冲突，先用有效失败用例锁定对应合同，再改代码、cargo fmt；独审ExecuteAs保留实际frame/约束/初态，内存事件与浮点寄存器/返回值使用同一个最终可满足求解模型，partial/错误不进入完整gen。
4. 用指定官方Z3构建并核动态链接及watchdog feature；跑同Context枚举回放、ExecuteAs压缩访存、内存事件和具体/符号状态、完整初态/后态、三表示及GCC/Clang往返；保留浮点永久回归和最小定向数值/异常探针。原memory已知问题必须分账，不能把bdd047bc旧缺陷称为合流新回归，亦不能宣称其已被修复。
5. 从本轮模型实际生成五IR及全部provenance；Sol独审工具/源/配置/IR哈希和回归后，再跑真实make浮点/访存/压缩入口及所定完整Clause预算。任何新失败应查明后再形成组件提交。
6. 最后解根文档/metadata/gitlinks，核子模块可获取、原dirty仍完整且兼容后，按既有合流授权推进目标。本阶段尚未执行合并、构建、IR生成、提交或发布，预检不等于合流完成。

旧float214/e9全77超时、最终float限定验收及memory partial/已知缺陷均保留原版本边界。通用ITE配置、路径线性化和OPEN架构策略不属于本次兼容合流。
