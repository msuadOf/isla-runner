# RESULTS — 验证与历史证据索引

## 2026-11-03 Sv39 局部线性化与笛卡尔积后处理 A/B 对照实测（限定验证）

在 `.worktree/mmu-symbolic-experiment/` 下建立三组端到端对照实验（执行器 `isla/.worktrees/memory-consistency/target/release/isarch`，单线程 `-T 1`，60秒硬时限，指令 `0x0000b103` `ld x2, 0(x1)`，全符号页表与 SMT Array 内存）。结果存入 `exp-ab-comparison/comparison_report.json`。
- **Group A (基线: 原生直接分叉)**：探索 179 条路径（123 废弃 Fault，56 冗余 Success，浅层 L2 偏斜）；Z3 检查 89,017 次（耗时 46.33s）；首条命中 9.14s；60.07s 超时终止 (exit=124)。
- **Group B (局部线性化: zpte_is_non_leaf / zpte_is_invalid 数据流压平)**：探索路径 105 条（下降 41.3%）；Z3 检查 36,314 次（下降 59.2%，耗时 23.67s）；成功遍历至 Level 1 (2MiB) 与 Level 0 (4KiB) 全部 3 级结构模板；因剩余权限和更新分支存在，60.07s 依然超时；首条命中 16.96s（AST 深度微增）。
- **Group C (线性化 + 笛卡尔积后处理)**：在 Group B 吐出的 3 级结构模板上，后端对 3 权限 × 2 特权 × 2 状态展开 36 种微架构用例。Z3 批量求解 36 个用例耗时 **70.36 毫秒（平均 0.452 毫秒/例）**，36/36 **100% 通过 Sv39 架构合法性独立验证**。
- **边界结论**：方案证实了“前端压平对称微观分支降低 59% 算力开销 + 后端毫秒级笛卡尔积批量产出高精纯微架构黄金用例”的有效性；但线性化无法单靠两个函数消灭超时，且笛卡尔积仅能扩增数据流，不能替代未走到的控制流异常分支探索。


## 2026-10-22 语义约束变异 E1 生成侧 pilot（限定观察）

干净 witness-pure@2fefa72，自带IR6fc39efd、FD配置01229f5f、既有二进制0baf7eb0；未重编，不新增二进制来源证明。执行 `python agents/semantic_mutation_fuzzing/pilot.py --output .tmp/semantic-mutation-pilot-20261022-r2`，两个目标／开关各三次、单worker，共12次退出0、168条记录，约34.76秒；开启seed1234/4321/20261022。VFMVFS的vl并集5→13、仅Retire1→5，中位命令耗时3.971→4.373秒；VSETIVLI的vl并集1→8，1.567→1.668秒。全部重复中各目标verdict直方图保持。仅证明输出共同字段值域扩大：旧off省略大量寄存器字段、on增加导出，完整JSON去重不可直接比较；VSETIVLI覆盖旧vl，旧值变化不证明有效硬件探索。日志旧兼容警告仍在，无DUT／分支覆盖／检错PASS。首次分析器假定源寄存器字段存在而失败，保留失败目录，修正后重跑12次。原始JSON／日志／命令与哈希、独立复算脚本见 [结果](../agents/semantic_mutation_fuzzing/pilot-results.md)；后续 [E0–E7矩阵](../agents/semantic_mutation_fuzzing/experiments.md)。

## 2026-10-22 Sail-RISC-V内存／通用浮点分支重组（限定验证）

以4f2ac293为共同基线，新内存分支1fa93117共2提交，通用＋浮点分支18389a89共4通用＋10浮点提交，通用末端0de6edd1；每个精确中间暂存tree分别执行普通／SYMBOLIC全模型严格检查，最终32次退出0，工具为已记录补丁版Sail0.20.1。后者完整tree6fafcbc4逐字等于原3ea3cbaf，151路径及配套测试保留；内存只改变4个V模型文件。初次通用链遗漏两份VPR测试被最终树核对检出，补入第02通用提交后重新做14层28次检查，初次提交和日志保留、不作为完成交付。两新worktree干净，原索引字节／两层补丁／旧分支／工作树及父gitlink和根仓版本指针保持，未push；来源空白问题、补丁工具链和旧fixture限制保留，未生成IR或新增数值／C++／全指令／硬件PASS。[交付](../agents/sail_riscv_commit_review/topics-20261022.md)、[命令/tree/日志](../agents/sail_riscv_commit_review/topics-20261022/commits.json)、[最终核账](../agents/sail_riscv_commit_review/topics-20261022/final-audit.json)。

## 2026-10-21 Sail-RISC-V独立代码审阅与定向复核

受审4f2ac293至3ea3cbaf，独立subagent直接复核源码并新增证据：标准Sail0.20.1的最小C++探针退出1（缺float_rounding_mode lowering），补丁版同输入退出0；合法性fixture、旧比较还原及向量helper类型检查分别失败，旧问题仍在。候选1011路径与既有final-source逐字相等，复用其普通C++库新编调用器，18算术包装×5RM的180000随机及524880边界调用（含重复）结果位／SoftFloat flags全部相等。仅列定普通C++包装，不证明独立数值算法、其余49包装、SYMBOLIC／向量／硬件；本轮未重新生成或完整编译模型。未发现新确证数值／最终状态回归，生产源码保留；报告与小型证据随根仓float@3bb9e8d提交。[报告、命令、哈希与失败日志](../agents/sail_riscv_commit_review/independent-review-20261021.md)。

## 2026-10-21 根仓float／memory版本核查

根仓float@754ca8e与memory@8b24dc8均从a85d6df建立，组件映射见 [版本说明](../specs/topic-versions.md)。在 `.worktree/runner-float`、`.worktree/runner-memory` 分别执行 `./init.sh --submodules-only`，均退出0；两套manifest／gitlink／实际子仓HEAD／origin／默认IR哈希一致，根工作树均干净。原master与两原子仓HEAD、索引条目、暂存补丁及子仓未暂存补丁保持。仅版本核查通过，无构建／联合求解／硬件PASS；float源码／IR尚待精确重生验证。HTTPS远端查询仍TLS EOF退出128，未push、未验线上可获取。[完整命令与哈希](../agents/branch_merge_review/root-sync-validation.json)。

## 2026-10-19 Sail-RISC-V 按model功能重组（限定验证）

从4f2ac293新建 `feat/sail-riscv-by-category-20261019@3ea3cbaf`，23原提交重组为11个模型功能提交＋1个忽略规则提交。11个精确模型中间tree各做普通/SYMBOLIC严格类型检查，共22次退出0；初次冷缓存两检查主动中断-15后用同工具链缓存重跑，未记旧尝试PASS。最终完整tree `6fafcbc406156ee275bcf301e6db1743eb417a0f` 与755fea6e相等，151路径完整保留。两旧工作树的HEAD/分支/索引字节/两层补丁/文件、全部旧分支及父gitlink保持，新worktree干净。原有空白问题保留；本轮未生成IR或执行数值/C++/全指令/硬件测试，历史证据不外推到新中间tree。[完整交付](../agents/sail_riscv_commit_review/commits-by-category-20261019.md)、[每层命令和tree](../agents/sail_riscv_commit_review/regroup-20261019/commits.json)、[最终核对](../agents/sail_riscv_commit_review/regroup-20261019/final-audit.json)。

## 2026-10-18 FLI/BF16 上游修复PR（限定PASS／已发布）

官方e5acebb0上修复提交 `fbacdfff8257346b144b54b4fa2a6d45a97d2eef` 已发布 [#2030](https://github.com/riscv/sail-riscv/pull/2030)。独立官方Sail0.20.3全模型严格类型检查退出0（标准库unused request警告）；实际映射和两个原生测试函数在定向C/C++运行通过，104条文本和LLVM22.1.8编码匹配、32常量往返通过；GNU2.45.50四种hex float在H/S/D共12条保留索引；恢复旧FLI/BF16映射的两个对照均触发断言。格式/拼写通过，DCO线上SUCCESS。旧编译器及初版测试依赖失败经更换工具链/补齐依赖后复验；完整CMake/CTest、架构执行/IR/硬件及其他CI未验，原子仓/索引/gitlink保持。[完整范围](../agents/sail_riscv_commit_review/pr-1a135b24-20261018.md)、[精确源码/命令/提交/线上记录](../agents/sail_riscv_commit_review/pr-1a135b24-20261018.json)。

## 2026-10-18 1a135b24 最新上游汇编对照（限定PASS／上游缺陷复现）

联网获取官方 `master@e5acebb04ff573e93203596486b831a5974117c3`，从实际源码抽取FLI.H/S/D各32项及四条BF16指令各两种mask。Sail0.20.1严格小模型成功打印104条，上游文本匹配0/104且LLVM22.1.8全部拒绝；仅在临时clone应用1a135b24的三模型补丁后，104文本/编码及32常量映射往返通过。GNU as2.45.50另对实际 `fli.s f16, 0x10` 生成f01c8853（16.0），修复文本1.0生成f0180853。临时clone已恢复干净，原子仓源码/索引/HEAD及gitlink保留。未验完整模型、IR、数值执行或硬件，未发布issue。[复现报告](../agents/sail_riscv_commit_review/upstream-1a135b24-20261018.md)、[版本/命令/摘要/哈希](../agents/sail_riscv_commit_review/upstream-1a135b24-20261018.json)。

## 2026-10-18 FLI 四个二次幂常量文本（限定PASS）

四个常量的普通十进制/科学计数文本用Fraction精确核对，对每项三种写法（另含 `0x1p-16`/`0x1p-15`/`0x1p-8`/`0x1p-7`）分别运行GNU as2.45.50.20251209与LLVM MC22.1.8，共24次FLI.S汇编全部成功且机器码保留索引2/3/4/5。完整命令/输出/编码见 [机器记录](../agents/sail_riscv_commit_review/fli-literals-20261018.json)。未验FLI.H/D、数值执行或硬件，未修改生产映射；解释见 [补充复核](../agents/sail_riscv_commit_review/fli-syntax-20261017.md#2026-10-18-四个小常量的可读写法)。

## 2026-10-17 FLI GNU / LLVM 独立汇编复核（限定PASS）

GCC14.2、GNU as2.45.50.20251209及2.46、LLVM MC/Clang22.1.8各测试 `fli.s f0, 0x10`、`1.0`、`16.0`，共15次。GNU接受0x10但生成 `f01c8053`（索引25/16.0）；LLVM拒绝0x10且退出1。1.0全部生成 `f0180053`（索引16），16.0全部生成 `f01c8053`。所有返回值/诊断/编码符合工具差异预期，官方GNU手册和LLVM22解析器已核。没有执行Sail/IR/硬件，不改模型/索引/gitlink；历史104项LLVM回归不外推GNU语法。详见 [复核](../agents/sail_riscv_commit_review/fli-syntax-20261017.md)和 [15次完整命令/输出](../agents/sail_riscv_commit_review/fli-syntax-20261017.json)。

## 2026-10-16 Sail-RISC-V 实际提交整理（限定验证）

受测23层源码各绑定实际Git tree，分支 `feat/sail-riscv-review-20261016@cfde70ec`。21个模型层各做普通/SYMBOLIC严格类型检查，共42次通过；新增测试入口语法检查通过。精确C02汇编104文本/LLVM编码及32FLI往返通过，C05八组RV32/RV64 F/Zfinx flags状态方程通过。最终独立源码快照逐文件等于commit tree，使用既有补丁版Sail 0.20.1、离线核验依赖、Ninja Release并行4完整构建模拟器通过（587.89秒）；新编译RV64 BF16 nan_boxing/wma_flags两项CTest通过。最终新生成共享类型IR的32个flags位序及三格式分类、E/non-E AMO布局证明、move/merge14项探针通过；四项lane源码结构检查通过。

vector helper新旧探针退出1：旧对照生成器将当前min/max包装内调用替换为不存在的 `old_fp_min_pure`，属于保留的fixture结构失配，未记生产语义FAIL/PASS。原合法性fixture、纯比较恢复、minmax双体及旧cpp符号期待仍有历史版本限制，本轮未全部重跑。完整IR/全指令/数值/硬件与逐层C++构建未验；空白检查保留EOF及冻结patch原字节。最终tree `6fafcbc406156ee275bcf301e6db1743eb417a0f`与原索引排除12pyc后一致，原工作区/索引字节/补丁/文件不变，新worktree干净。完整命令、版本、源码/产物/日志hash见 [交付](../agents/sail_riscv_commit_review/commits-20261016.md)及 [validation.json](../agents/sail_riscv_commit_review/split-20261016/validation.json)。

## 2026-10-14 Sail-RISC-V 提交审阅有限复验

受测 `sail-riscv@4f2ac293` 加完整原暂存内容（binary diff SHA-256 `47ce7fb311f727f6ff976a40206b7eeb448ca8876f8e700a98eb52a67fc86b69`）。当前源码汇编检查104文本/LLVM编码和32FLI往返PASS；vector lane/unary/move及BF16四项源码结构检查退出0。合法性fixture与纯比较旧快照恢复退出1；minmax校验在HEAD控制快照下因当前无旧双体结构退出1（不作历史语义对照）。workaround坐标检查退出1，另有非严格IR基准哈希warning；暂存diff空白检查退出2。命令、输出摘要与源哈希见[检查证据](../agents/sail_riscv_commit_review/checks.json)，范围与解释见[报告](../agents/sail_riscv_commit_review/report.md)。无精确中间候选构建、全模型类型/数值/求解或硬件验收；未改变子仓原索引或源码。

## 2026-10-08 两分支试合并核对（意图一致／候选限定 PASS）

以`7b7337b`为共同基线，`09fe582`＋`be1296b`在`.worktree/isla-merge-check-20261008`试合并，float.rs／exec.rs两处冲突按新浮点原语及编码可行checkpoint内偏好解决。候选tree=`54fb4e8e26bcf654dc182a470f604439a1380028`；与原最终工作区986同／15异／新增14／无缺失，包含实际通用与IR修复，文件树及部分实际行为不同。用户随后澄清“等价”指代码意图及预期效果、允许bug fix；按此口径一致。前轮“不等价”结论采用文件树／精确行为标准，与用户本意不同，保留此说明以区分结论口径。

候选93库＋25bin、浮点原语10、MixedBits／模型物化集成8＋2＋2＋3、默认编译及fmt通过；offline、j8、feature itrace/smt-thread-interrupt、测试单线程，命令见[核对记录](../agents/float_support_review/merge-check-20261008.md)。原HEAD／分支引用／索引条目／两层binary patch／1001源码哈希保留。未提交合并、未移动生产分支、未make solve／全量／硬件。

## 2026-10-08 仅浮点修复提交（限定PASS）

`feat/float-only-20261008@be1296b`，`5ceb3ad`＋`be1296b`均按fix(scope)格式；补齐4旧IR缺体helper并恢复5IR快速FPR getter/setter副作用，RV32 SD31。最终1615个独立SoftFloat向量、180状态＋20隔离guard、BF16六例、legacy35、原语10、isla68＋bin25（跳1个既有失败）、默认编译/fmt与2装配负例通过。四份RV64同60/50/20秒T1 make均退出0、MRET4／FLEQ.S16gen，默认另BF1639／FLI.S32；旧V256 FLEQ.S0→16，全部有编码。普通helper和状态组件逐字可重装配，独审通过。

原d012已由aea104c8默认IR替代；165件冻结源严格生成FD提供方退出0／516.72s，再组件装配，未将当前Sail工作树冒充源链。原isla HEAD／索引／两层补丁未变、受审分支干净；未push、全77、公共RV32入口或硬件。其他旧IR的BF16历史execute与v512实际256仍保留。[交付与版本／命令／证据](../agents/float_only_review/fix.md)。


## 2026-10-08 通用复审第二轮修复（限定 PASS）

精确`09fe582`（4b141eb＋三个fix）：库89＋bin25、组合93＋25、集成8＋2＋2＋3、executor88、默认编译和fmt通过。有效红灯后修复拼接访存／具化、断言转换后压缩编码接续、编码可行替代前态及错误退出；独审补充的assembly拒绝仅跳过当前编码亦有红绿回归。精确和组合的V128/V256实际make solve各退出0，MRET4、ITYPE32、SRET6、VSETIVLI12，全部VSETIVLI前态VS非零及vr0前后位宽核对通过；C_ADDI1 ExecuteAs单列，不当退休或完整重放证明。不同V128 IR各自验收，不作跨IR等价宣称。目标分支已接入，原工作树与浮点剩余保留；未push／全量／硬件，无整体性能结论。[版本、命令和证据](../agents/general_support_review/fix2-20261008.md)。

## 2026-10-08 仅浮点分支独立复审（FAIL／限定数值通过）

受审`d04883b`相对`7b7337b`。主审与独立gpt-6-astra high确认全局退役SoftFloat分派但4份自带IR未迁移：同一f32Add包装器基线4/4通过，分支4/4 NoFunction；公共`IR_FILE=ir/rv64d_v256_e64.ir` FLEQ.S退出0但0gen。默认d012的FADD.S和直接FPR写回Dirty状态，两版均6/12失败，是继承缺陷。

原语10、legacy35、isla68＋bin25（明确跳1个既有失败）、fmt/default check通过；新增独立SoftFloat327例覆盖67helper，完整结果/五flags差异UNSAT。BF16 VF scalar sNaN六例基线4败2过，分支6过，证明无活动元素修复。最终make 60/50/20秒、T1、ITRACE、qfaufbv退出0，MRET4／FCVT.S.BF1639／FLI.S32／FLEQ.S16gen。Debug实际Z3 4.13.3，release 4.16.0；d012IR／20851fdb FD配置，未跑完整77项、全库、全状态或硬件，无生产修改。此前分支整理的限定PASS不覆盖本次发现。[报告、命令及哈希](../agents/float_only_review/report.md)。


## 2026-10-08 通用支持最新提交复审（FAIL／限定定向通过）

`4b141eb` 相对 `7b7337b`，独立 gpt-6-astra high 与主审一致确认三组 P1、一组 P2。相同新增消费者测试（具化、索引、访存）基线5/5、当前0/5；assert 转换后压缩编码接续基线1/1、当前0/1。同 IR、同配置的 V128/V256 五 clause 对照：MRET 4/4、ITYPE 32/32、SRET 6/6、C_ADDI 0/0（既有缺口）、VSETIVLI 基线12／当前0；四组make皆退出0。当前仅隔离加入 VS 非零约束恢复12，恢复精确源码后再次0，证明合法替代解被选模后拒绝丢失。

精确当前定向81＋25、持久集成8＋2＋3、executor85、primop67、fmtval2、缓存3、默认编译和fmt通过；只限定上述范围，不能计整体PASS。Rust/Cargo1.93.1，单测Z3 4.13.3、Make Z3 4.16.0；离线构建-j8、单测单线程，make-j4且每clause单worker。未修改生产源码／分支，未全量或硬件。命令、哈希、诊断补丁和有效失败日志见[复审报告](../agents/general_support_review/rereview-20261008.md)及[provenance](../agents/general_support_review/rereview-evidence/provenance.json)。准备阶段的探针编译／汇总错误只记harness，不记生产FAIL。

**2026-10-08 仅浮点分支（限定PASS）**：28f626a至d04883b直接基于7b7337b，不含通用8提交。浮点10、legacy35、Target23、库68＋bin25、fmt/默认编译通过；明确跳过已在基线复现的x0测试。MRET 4 gen、BF16 39 gen均有编码。原工作区保持，新工作树干净。[边界和命令](../agents/float_support_review/float-only-20261008.md)。

## 2026-10-08 通用审查修复（限定 PASS）

`isla@4b141eb`（2792afd＋三个 fix 提交）：精确库81＋bin25、组合库85＋bin25、持久集成8＋2＋3、旧helper组合1、既有primop67/位向量47/executor85/fmtval2/cache3、默认编译/fmt通过；精确与组合的 V128/V256 MRET 四组各退出0、4 gen＝3 Retire＋1 Illegal，宽值完整前后态保留。MPP 无 S 排除1、保留当前 Sail 无 U reset 的0并标注manifest，独审通过。已接回目标分支，原工作树/index/dirty文件核验不变，通用浮点剩余保留；未push，本轮未重跑全库/整组/硬件。历史失败按旧2792afd保留。[完整命令、版本及范围](../agents/general_support_review/fix.md)、[四组输出](../agents/general_support_review/fix-evidence/smoke-summary.json)。

**2026-10-07 浮点提交整理（限定PASS）**：bc7bc59至2d46ce7在新工作树按六类提交。浮点primop10/10、SoftFloat legacy35/35、Target35、库83＋bin25、默认编译/fmt通过；d012 IR的MRET 4 gen、FCVT_S_BF16 39 gen均有编码。首例runner MixedBits不兼容已最小修正，未改生产代码；已知通用回归未修、未测全77项。[完整命令和边界](../agents/float_support_review/float-split-20261007.md)。

## 2026-10-07 通用分支独立审查（发现回归）

受审 `isla@2792afd`、基线 `7b7337b`，仅已提交生产代码。主审与独立 gpt-6-astra high 共同确认两个 P1：拼接后整数算术 8 例及 FP 转换 1 例基线通过、分支 Type；同一 VLEN256 IR 的 MRET 基线 4 gen→分支 0 gen，两边 make 均退出 0。V128 两版各 4 gen、返回类别与编码相同；MPP 无 S 能力 fixture 仍允许 Supervisor，属新域覆盖不足。定向 79＋25、85＋67＋2＋3、默认编译/fmt及转换后 assert 两臂探针通过；全 isla-lib 分支 354／基线 344 均被旧 Z3 enum sort 重名中断，不算全量 PASS。Model 缓存 20,000 次同符号查询的 Z3 调用 20,000→1，约 2.119→0.0058 秒，限局部收益，未证端到端提速。没有生产修改、提交或硬件验证。[完整报告、命令与适用范围](../agents/general_support_review/report.md)、[哈希与工具版本](../agents/general_support_review/evidence/provenance.json)、[四组 smoke](../agents/general_support_review/evidence/smoke-summary.json)。旧归并/重做的限定 PASS 保留为历史，不能据此越过新发现的验收失败。

**2026-10-07 通用提交按类型重做（限定PASS）**：416b94f至2792afd八层定向分别67/2/3/85/4/25/73＋25/79＋25项通过；fmt及最终tree一致性通过。原工作区和浮点补丁未变，同tree沿用此前MRET证据，本轮未重复solve。[范围与逐层命令](../agents/float_support_review/general-split-20261007.md#按改动类型重做已完成)。


## 2026-10-07 通用修改独立工作树归并（限定PASS）

`4089545`精确候选：79库＋25bin、85执行器、67位向量、2格式化、3模型缓存测试、默认编译及fmt通过；MRET退出0、4 gen。新工作树完整组合83库＋25bin、fmt及MRET（4 gen）通过。不同IR各自验证，不宣称跨版本等价；首次smoke路径错误已修复并重跑。24文件哈希及原索引/HEAD核验保持，浮点17路径未提交。[范围、命令和哈希](../agents/float_support_review/general-split-20261007.md)。

## 2026-10-07 局部结构修整（限定PASS）

7b7337b加当前浮点工作区：测试先迁真实collector/mapping入口，基线82项通过；内联及对象归属调整后82库＋25bin＋10浮点primop通过，默认编译/fmt和MRET（4 gen）通过。过滤既有x0测试，未全量或硬件，未提交；原索引保持。[命令与版本哈希](../agents/float_support_review/local-structure-20261007.md)。

**2026-10-06 worker panic（限定PASS）**：`7b7337b`精确候选编译/fmt、有界collector panic及executor定向回归通过；本轮未重复solve，工作区源码哈希不变，既有MRET结果见同一报告前节。[命令和证据](../agents/float_support_review/solve-process-commit-20261006.md#接续worker-panic-记账独立提交)。

**2026-10-06 smtperf测试（限定PASS）**：`d9f0fe0`精确候选在smtperf与smtperf,smt-thread-interrupt下各4/4通过，fmt通过；本轮仅测试修正，未跑solve。[命令与证据](../agents/float_support_review/solve-process-commit-20261006.md#接续通用-smtperf-测试修正独立提交)。

## 2026-10-06 solve进程管理独立提交（限定PASS）

`1eddd68`精确脚本候选执行test_solve_cleanup.py，12项通过；完整工作区make solve MRET退出0、4 gen，监督器报告退出0。索引条目/工作区源码/未暂存补丁保留，浮点入口未纳入。未全量或硬件验证。[命令、哈希与证据](../agents/float_support_review/solve-process-commit-20261006.md)。


## 2026-10-06 itrace 数据归属（限定 PASS）

`69cf43a` tracetool61项，`a9884b2` 62项，fmt、ITRACE/FTRACE/BTRACE全开的隔离MRET退出0。原staged/unstaged binary diff逐字一致，28文件SHA一致；未重跑全量或全部CLI组合。[命令与证据](../agents/float_support_review/trace-composition-20261006.md#itrace-数据归属修正并重做两提交2026-10-06完成)。

## 2026-10-06 提交重做核验（PASS）

`9da2eaa`＋`48619f2` 最终tree与4a84366一致；主分支迁移前后index条目和28个未提交文件SHA一致。第一提交tracetool定向61项及fmt通过；此前最终源码三层/MRET验证继续适用，本轮未重跑全量。[证据](../agents/float_support_review/trace-composition-20261006.md#按原提交重做2026-10-06完成)。

## 2026-10-06 tracetool 平级结构（限定 PASS）

`4a84366`：精确tracetool62/executor84/isla64＋25，暂存82＋25/executor84，完整83＋25/executor85，CLI默认及ftrace,btrace编译/fmt通过；跳过既有x0失败。精确和完整MRET及i/f/b/fb/ifb对同层旧版静态清单、动态边、函数事件、签名和生成指令一致。暂存两层归一化增删行核对及迁移快照核验通过。未做全量/硬件回归。[命令与证据](../agents/float_support_review/trace-composition-20261006.md#tracetool-平级归属修正2026-10-06完成)。

## 2026-10-06 组合轨迹与独立 writer（限定 PASS）

`9d8b915`主轨迹＋`c1d6bc6`writer已迁回；精确主候选itrace60/executor84、isla64＋25，writer后itrace61；暂存82＋25/executor84，完整83＋25/executor85，默认CLI/ftrace+btrace编译/fmt通过（过滤既有x0失败）。精确与完整两层MRET分别对同层旧版核验：静态清单、实际分支、签名、统计、生成结果一致；均4 gen。精确5条签名trace、完整4条，不跨层宣称等价。原暂存和未暂存差异保留，未跑全量或硬件。[命令、失败修正、哈希与证据](../agents/float_support_review/trace-composition-20261006.md)。


## 2026-10-05 catalog CLI 开关（限定 PASS）

`d21ad62` 精确候选与完整工作区的MRET CLI开/关对照通过：catalog段有无正确，轨迹、边与签名保留，指令/编码/执行结果一致。具体寄存器见证值在相同配置重复运行中也变化，未记逐字一致。定向测试、默认编译、fmt及工作区make solve MRET通过；未跑全量/硬件。[命令、红绿回归和哈希](../agents/float_support_review/catalog-boundary-20261005.md#cli-实施和验证完成)。


## 2026-10-05 itrace 容量比较（限定 PASS）

`isla@5c376fb` 默认Unlimited；旧256分块的独占序列回归红，修改后无限与有限256配置各60项itrace通过，executor83、isla64＋24（过滤既有x0）、编译/fmt通过。精确候选使用工作区d012 IR的MRET退出0、4 gen、5条签名trace；未跑全量或硬件。[命令与证据](../agents/float_support_review/catalog-boundary-20261005.md#容量类型与比较运算符-amend2026-10-05完成)。


## 2026-10-05 itrace 独立提交（限定 PASS）

`isla@64f74f3` 精确候选 itrace58、executor83、isla64库＋24bin通过（过滤既有x0测试），默认编译/fmt通过；完整工作区 MRET退出0、4 gen、4条签名trace，使用d012 IR，不能当成精确提交的solve验证。未跑全量或硬件。共享存储与writer现已提交，其他改动保留。[命令、哈希和证据](../agents/float_support_review/catalog-boundary-20261005.md#后续两项-itrace-改动独立提交2026-10-05)。


## 2026-10-05 catalog 边界收缩（限定 PASS）

`isla@ef4ea1d`（父b18d6b7）恢复Vec/切片、解耦catalog与紧凑输出。旧实现完整trace回归按预期红；精确候选64库＋24bin、暂存82＋24、完整组合83＋24通过（过滤既有x0失败）；executor82/84、itrace53/58、默认定向/编译与三层fmt通过。`make solve ALL=MRET THREADS=1 ITRACE=1`退出0，4 gen与旧8545e7c的JSON相同，实际边/签名/紧凑统计一致。命令、版本哈希及证据见[详细记录](../agents/float_support_review/catalog-boundary-20261005.md)。未跑全量solve、全isla-lib或硬件；共享存储、浮点接口与原挂起修复仍在未提交层。

## 2026-10-03 catalog 局部修补（限定 PASS）

受测候选即 `isla@8545e7c`；恢复 exec.rs 原流程，撤销终态账本，保留 catalog 与路径签名。旧实现新断言红例1过2失败；精确候选64库＋24bin、暂存组合82＋24、完整工作区83＋24通过（过滤既有x0失败）；候选/工作区executor83/84、itrace各57、默认定向/编译/格式通过。`make solve ALL=MRET THREADS=1 ITRACE=1` 退出0，4 gen、5 trace路径，catalog及签名关联检查通过。命令、三层版本、IR/配置/运行器哈希、首次漏参编译失败与证据见[完整记录](../agents/float_support_review/catalog-local-patch-20261003.md)。未跑全量solve、全isla-lib或硬件；原浮点及挂起修复未混入提交。

## 2026-09-30 挂起测试修复（当前未提交工作区）

TERM PID1363231后确认其及父1362027退出。修复 `executor.rs` worker unwind完成记账并继续传播panic，`itrace.rs` 空队列条件变量等待。新增 `multi_runtime_propagates_collector_panic` 先编译后测试，修前 `timeout -k 1s 10s cargo test --offline -q -p isla-lib --features itrace,smt-thread-interrupt --lib multi_runtime_propagates_collector_panic` 返回124，修后返回0（1项，0.01秒）。同样外限下，lib筛选 `executor::` 84项/0.58秒、`itrace` 72项/0.06秒通过；`-p isla --lib`筛选原挂起测试1项/0.21秒通过，过滤 `isarch::target::tests::rv64_target_trait` 的库83项/0.37秒通过。全isla-lib返回1，Z3报 `enumeration sort name is already declared`，未归因，不记全量PASS。cargo fmt和git diff --check通过；未执行make solve或提交。日志位于 `isla/target/hang-{regression-red,regression-green,executor-green,itrace-green,collector-green,isarch-full,lib-full}.log`，构建先用--no-run完成，测试每条命令10秒外限。旧候选原panic未恢复，不能用当前回归通过覆写旧候选挂起记录。

本文件汇总已有的逐次验证记录，保留其当时的版本与限制。**当前任务状态以 [specs/TODOs.md](../specs/TODOs.md) 为准。**详细命令、逐条结果和原始分析继续保存在原位 `agents/` 专题文件或 `archives/`；这里不把历史结果重写成当前工作树的 PASS。

| 日期 / 范围 | 原记录的结果 | 证据入口与限制 |
| --- | --- | --- |
| 2026-09-30，T3b XiangShan issue 发布 | 用户审核后发布 [#6655](https://github.com/OpenXiangShan/XiangShan/issues/6655)，线上 OPEN；标题和 UTF-8 9,106 字节正文与本地发布稿逐字一致，无附件。当前账号无 `AddLabelsToLabelable` 权限，模板标签未能保留／补加。 | [发布核账](../agents/memsolve_branch_coverage/vsse32_issue/publication.md)、[实际正文](../agents/memsolve_branch_coverage/vsse32_issue/issue-body.md)。这是外部发布核对，未增加新的 RTL 验证或根因证据。 |
| 2026-09-30，T3b 无附件上游稿／最新 v3-v2 独立复验 | 两名独立 agent 只按 issue 正文 clone、`make init`、构建 `DefaultConfig` 和编译 ELF。官方最新 v3 `09453ff8` 对齐 `vsse32.v` 在目标 `0x80000034` 前冻结，DiffTest 15,000 周期无提交后 ABORT（19/23,331）；同 ELF `--no-diff -C30000` 19 次提交、无 GOOD TRAP；错位版同样 ABORT，对齐 unit GOOD TRAP。最新 v2 `e7bab53` 对齐／错位 strided、对齐 unit、对齐 no-diff 四项均 GOOD TRAP。证明旧 `case-007` 的错位不是必要触发条件。 | [交审稿](../agents/memsolve_branch_coverage/vsse32_issue/draft.md)、[现行发现](../agents/findings.md)、本机 gitignored 独立报告 `difftest-xiangshan/work/vsse32-issue-verification/{v3,v2}/report.md`（各含完整命令、SHA、日志索引）。构建先经 quota/Mill 目录、`NOOP_HOME`、GCC flag 修订，最终以 make 命令行 `CC=clang CXX=clang++ -j24` 通过；没有 RTL 根因波形，未向 GitHub 提交。 |
| 2026-09-30，T3b 原载体 DiffTest 与上游去重 | `a13efc8775` 原 ELF 复跑：`case-007` commit trace 最后提交 PC `0x80000214`，下一条 `vsse32.v` 未退休；`--no-diff -C 30000` 冻结于 140 次提交。`case-004` 的 `vse32.v` 已提交，随后首字节 `lbu` 读出 `0xa5`、REF 为 0。GitHub #5279 先前报告同类错位 `vse32.v` 零写掩码，第二例不计原创；第一例仍是新症状候选 | [核账与限制](../agents/findings.md)、[议题状态](../agents/memsolve_branch_coverage/status.md)。命令：`./build/emu -i <原 ELF> --diff ./ready-to-run/riscv64-nemu-interpreter-so -C 5000 --dump-commit-trace`（case-007 加 `-b 2000 -e 5000`，case-004 加 `-b 0 -e 5000`）；第一例另跑 `--no-diff -C 30000`。同条件 issue 搜索未找到不等于证明不同 RTL 根因；对齐对照、最小化、写转发区分和波形均未做。 |
| 2026-09-30，73df 标量 `execute` 源码 arm 只读核账 | 51 个冻结 JSON/ITRACE 对同批 Sail 模型：非 BF16 的 49 clause 有 238 个 `execute` 词法 arm，观察 224；BF16 两 clause 另有 4/4；总计 228/242。其余 14 个为 RV64/FLEN64 固定值下 `assert` 失败臂，当前配置不可达 | [具体分母与版本限制](../agents/findings.md)、[冻结批次退出账](../isla/target/float-solve-evidence/direct-entry-73df-batch-20260928/evidence/batch-v3-scalar-audit.json)。只签 `execute` 本体显式 arm，非共享 helper、译码或数值域的完整源码 branch PASS；无新求解／硬件运行。 |
| 2026-09-29，bughunt F 线验收战役 | 四签名：#6475 自动级 155 例（片内含 vsseg3e32+自由批 43）、#6486 自动级 295 例含 41 例 data/mask/addr 级真分歧（错元素 mask 0x10↔0x01、错地址±0x10；vsseg2e16×24/vse32×27）、T3b 未复现（nf=2 错位 PASS/nf=3 转触 #6475，疑依赖定向载体）、#6605 出新候选；三族新 DUT bug 候选自动发现：NC-1 vstart 保留区 vsseg DUT 死锁 15000 周期（5 例）、NC-2 vstart≥vl 仍访存 mcause7@垃圾地址（3+ 例，P2 mstatus/mepc/mcause 同根）、NC-3 locked-PMP 段 store mtval+0x10（2 例）；P3 收口：zAMO 88 reject、AMO 过滤后全量重放 0 失败、preclass 可见化 144 例；VSSEG 自由批 0 命中→分片每片必出、zSTORE 错位 0→256+。结论：P1-P3 改造达标 | [findings](../agents/findings.md)、[议题状态](../agents/memsolve_branch_coverage/status.md)、产物根仓 `.tmp/accept1-20260929-124451/`（gitignored）。受限：a1 盒杀于 nf=6、a2 用 P1 冻结 JSON 代用、P1 hint 批前置待办（VSSEGTYPE 自由批税 4×1800s）、T3b 待原载体复验、A4 需 PMP 前导可配置化；上游上报包 7 项（E 线四草稿+NC-1/2/3）。 |
| 2026-09-29，catalog观测范围收缩 | `323021b`：先确认旧错误升级/完整性门槛红例；最终精确64库＋24bin、暂存组合82＋24、未暂存组合83＋24、默认3项定向/编译/fmt PASS | [版本、命令与证据](../agents/float_support_review/catalog-commit-review-20260929.md#catalog限于观测信息2026-09-29)。原错误退出策略恢复，complete仅报告；原27文件暂存和exec.rs未暂存浮点层保持。过滤已知x0旧失败，未跑全量solve/完整Sail/硬件重放。 |
| 2026-09-29，XiangShan GitHub 浮点 issue 逐条索引 | GitHub Search 取得 898/898 条公开 issue；每条标题／正文／公开时间线全读，37 条首屏不全者补第二页，最终 898/898 时间线完整。五批逐条记录 180/180/180/180/178，编号无重漏。表格含 27 条直接相关 XiangShan 浮点报告（12 open／15 closed）、17 条参考模型／重复／被否定等报告、7 条性能／FP 代码配置／构建交集；新补 #2890 `vfmacc.vf` 工作负载、#3735 FP 调度参数笔误、#4980 MMIO `fld` DiffTest 同步，#6410 FP 影响仍只是推论。 | [表格](../agents/float_support_review/xiangshan-github-float-issues.md)、[总审计](../agents/float_support_review/github-issue-audit/summary.json) SHA `491c2e30…af5cbb`、[全量快照](../agents/float_support_review/github-issues-all-20260929.json) SHA `b6af07e4…0c15e`、[完整公开时间线](../agents/float_support_review/github-issue-details-20260929.json) SHA `af17f7dc…990e29`。只做 GitHub 身份、评论和上游状态调查，无求解／emu 新验证；截图／附件中独有信息未逐个下载。 |
| 2026-09-29，`e893` 直接入口浮点 77 项完整 trace 基线 | 无抽样、300/270/30 秒、`-j4`/T2：77 启动退出，55 正常／22 外限；55 JSON 的 1432 `gen` 与终态、trace 核账错误0；51 标量全完成、26 向量仅4完成。局部 `FVFTYPE`／`VFUNARY1` 限制及隔离 `FVVTYPE` lane 延迟计算试验均未收束；整组 FAIL | [本轮逐项记录](../agents/float_support_review/vector-sampling-20260929.md#直接入口完整-trace-批次与卡点2026-09-29)、[机器账本](../agents/float_support_review/evidence/float-full-trace-20260929/final-audit.json) `59cd1509…3690`。22 项超时无最终 JSON，trace 为残缺前缀；没有静态源码语义分支闭合证据。 |
| 2026-09-29，bughunt 第一波 P1/P2/P3 | P1 `[[value_hints]]`：错位 0→192（#1574 类捕获材料，语义勘误"错位成功形态需平台位"）、非零 vr 可见、T2 完整形态 45/45、回归逐项一致；P2 `[[encoding_slices]]`+panic 修复：--instruction-bits 向量译码 panic 根因（独立 solver 传符号寄存器/向量守卫读符号 mstatus.VS，向量任意组合均触发）修复后 E 线 T1 命令 0.9s 复现，VSSEG 28/28 组合（vsseg3e32 基线 0→有）、vsseg3e32 重放自动命中 #6475（ROB assert ABORT，无定向参数）、VLX 缩域 32 条破超时、140 绿；P3 译码回环过滤：物化环境缺陷（model.get_val %i64 字段 64 位 Bits 垃圾值致 when 守卫放行，ldu 16 条三层收敛）修复后 ldu 16→0、其余零差异、148 绿；pipeline preclass 可见化 80 绿 | [findings](../agents/findings.md)（P2 专条含根因/验收/zSTORE 128 vs 2579 口径注记与 --timeout 单路径语义）、[议题状态](../agents/memsolve_branch_coverage/status.md)；worktree 60ca0e0/58c9766/47ac90c、根仓 488803f。受限：zAMO 全量 JSON（>30min，以 37 回环 13 REJECT+单测替代）、VSSEG 全量扫描不完整（转 F 线验收战役）、Bits 形态 i64 放行守卫机制未定论。 |
| 2026-09-29，73df 标量浮点运行结果本地备份 | 51标量目标／1344 gen 的求解JSON、日志、trace及冻结IR/配置/isarch，连同本工作区XiangShan DiffTest输入、ELF、结果、重试诊断、emu/NEMU已压缩保存。归档约80MiB，SHA-256 `c0111394…09815`；`zstd -t`、`tar -I zstd -df`、原件5639/5639哈希复核PASS。 | [备份范围与命令](../archives/float-scalar-2026-09-29/README.md)、[逐文件身份](../archives/float-scalar-2026-09-29/manifest.json)；`archives/_raw/`本机Git忽略，不是远端备份。原始文件仍保留。 |
| 2026-09-29，FLOAT-01 历史完整批次卡点只读复核 | d012、1dcc 均有77项完整退出账本，分别40成功/36外限/1 SMT失败及50成功/27外限；56cc跨stage57自然完成、20剩余。73df旧FullEncoded32入口的剩20目标19×30分钟＋FVFTYPE两小时均外限无JSON。19份原日志流扫58,845个fork，四个反向译码位点12,866、浮点变量宽度guard两位点9,542、LMUL正负判断3,917、vstart上界2,334；FVFTYPE两小时95,679次SAT检查累计14,094.107秒双worker FFI。 | [版本与聚合方法](../agents/float_support_review/vector-sampling-20260929.md#已有完整批次与长时卡点复核2026-09-29只读)、工作区 `.tmp/float-vector-sampling/full19-hotspots.json`。这是历史残缺前缀的定位，不代表77项完成，也不能外推到当前直接`zexecute`入口。 |
| 2026-09-29，GitHub 内存 issue 分阶段对照／本工作区定向重放 | 当前 XiangShan `a13efc8`、MinimalConfig emu `87141692…a85ee`、NEMU `9188e7dd…ef43`、pipeline `3b31333c…a0ace`。手工构造 `vsseg3e32.v` 触发 #6475 同名 ROB 断言、仅改 nf=2 对照 GOODTRAP；#6486 上游原 ELF 用本地 emu 复现同 PC 数据分歧，合成单指令非零源值版通过。源码正则及 `sc.w`／VSSSEG 小探针表明 #6296/#6316 不能笼统归因于标量低地址 preclass 过滤。 | [专题报告](../agents/memory_github_xref/report.md)、[定向机器核账](../difftest-xiangshan/work/github-memory-review/evidence.json) SHA `55c8474a…f45521`、[预分类探针](../difftest-xiangshan/work/github-memory-review/preclass-probe.json) SHA `07a583b9…b3307`。全部定向输入另记，不是 W19/W24 官方求解；历史 E 线“#6316 修复未生效或回归”未比对其 MMIO/NC 条件，不可直接迁作此结论。GitHub 维护者称 v3 所测 segment 功能 WIP。 |
| 2026-09-29，已修复 GitHub bug 的触发条件补账 | 旧 Vext `rv64_zVMVXS.json` `gen[2]` 已含 #5809 的 `vmv.x.s`＋`vill=1`／Illegal；本轮同原 JSON 行在当前 pipeline `3b31333c…a0ace`、XiangShan `a13efc8`、MinimalConfig emu `87141692…a85ee`／NEMU `9188e7dd…ef43` 重编并运行，ELF payload `0x42202557` 报 cause 2、GOODTRAP／退出 0。修复提交 `fdd634f` 为当前 HEAD 祖先；**计历史求解触发条件覆盖与修复后验证**。旧 2026-09-18 trap 补跑基线 `case-4815` 也曾记 success，初始 Retire-only 过滤并非全部历史。 | [逐项归因](../agents/memory_github_xref/report.md#已修复-bug-的触发条件覆盖另列的向量非访存例)、[机器核账](../difftest-xiangshan/work/github-memory-review/fixed-coverage-evidence.json) SHA `4af0be30…33f615`、[旧 trap 补跑](../isla/agents/validation/Vext-test-9-16-difftest-xiangshan/trap-entries-结果.md)。#5739 缺 `csrr vl` 观察序列，#6316 缺 MMIO／NC 触发谓词证明；二者不计覆盖。旧 Vext IR／配置未重绑，非当前 d012／73df 官方结果。 |
| 2026-09-29，内存 E 线已知 XiangShan bug 定向复现 | 4/4 靶标全部触发（单指令确定性）：T1 #6475 ROB assert `robEntries 18 uopNum is overflow!`（instrCnt=214，vsseg5e32/masked 同 abort、m2 形态 pass）；T2 #6486 精化为"错选源寄存器"——DUT 把字段 1 源选成 v8 而非 v10（origin 128bit 直证，比原报告"写 0"更精确）；T3a #6288/#6316 类同址错位 sw=7 vs amoswap.w=6 且 v2/v3 emu 均现（修复未生效或回归）；T3b #6296 族新变体：vsse32 RAM 错位 DUT 死锁、vse32 错位静默丢字节（疑似可报新 issue）；T4 #6605 strided/indexed 入 locked PMP 不 trap 且核心停摆 15000+ 周期（比原报告恶化；Sail=AccessFault/NEMU=trap7/unit 对照正确） | [README 与四份 upstream_reply 草稿](/data1/baiyifan/tmp/xs-known-bugs-repro-20260929-034817/README.md)、[findings](../agents/findings.md)。emu 谱系：根仓 `difftest-xiangshan/xiangshan`@a13efc8775=kunminghu-v3（四 bug 全活）、`isla-xiangshanv2`@f86f50b83=kunminghu-v2（T1 不触发原因）；生成用 worktree 9f82a87。未改仓库无提交。 |
| 2026-09-29，FLOAT-01 向量抽样与编码域预检 | Sail 双后端严格型检、实验 V128 IR `e893e127…4d9` 生成、Isla exec 23/23 与 FS/VS collector 通过。同 IR 独立具体编码/状态八包894/894通过。当前运行器 `196809a4…a81c8` 的 26 项60秒预检：`VFMVFS`、`VFMVSF` 退出0且完整JSON共24个可编码gen；24项外限124且无最终JSON。两项成功目标的 ITRACE/JSON 终态守恒；BF16和widening的SEW断言修复候选在受限试验中无执行错误但无Retire。 | [本轮报告](../agents/float_support_review/vector-sampling-20260929.md)、工作区 `.tmp/float-vector-sampling/matrix/summary.json` 与 `.tmp/float-vector-sampling/e-runner/summary.json`。60秒为诊断预算，不替代正式60分钟；实验IR未切主、79配置未重绑、C++/Isla全量回放与源码分支闭合未完成，整组仍0/77正式签收。 |
| 2026-09-29，内存六线并行轮（A/B1/B2/B3/C/D） | B1：F1=PR#1752（0.13 已修，与 XiangShan 公式逐字等价）、F2=PR#1744（0.12 配置化，whole-reg 形态已修）、基线 efdfe9b 不含三修复、spec 四 anchor 摘录；B2：#1574 判 Z3 未覆盖（45 条 ok 全对齐）、新发现 ldu 非法变体（枚举越过 encdec 守卫）与 LOAD 汇总丢失（F8 实为 28 abort），cherry-pick #1603/#1625/#1900 可消 38 例；B3：F5=difftest#969 框架 bug、F8=裁定实现自由（NEMU #990 open）、F6b 非 bug、未命中归因表与定向五条、CBO 缺失=EnableCHI 门控；A（model-fix-vd-nf@46f8273a 不合回）：移植 #1752+Vstart_Ignore，修复 IR 984d9f4a，探针 F1 翻 6/F2 翻 2/守卫 12 不变，重放 4/4 GOODTRAP；D（9f82a87）：csr_sym_vs 四 clause 3-9 倍恢复超旧 survey、F6a 阴性对照消失、FS 组必须保留；C（0d70b06+根仓 419dafb）：F3 根因（write_ram Ok(_)=>true）修复、F4 f/v 初值输出+装载、顺带修 F6(a)(b)，isla 127 绿/pipeline 77 绿，复验 F3 7→0、F4 30→0、合计 517 pass | [六线分节](../agents/memsolve_branch_coverage/status.md)、[findings](../agents/findings.md)、B 笔记 `/data1/baiyifan/tmp/github-xref-b{1,2,3}/NOTES.md`、A/C/D `/data1/baiyifan/tmp/{model-fix-20260929,isarch-fix-f3f4-20260929-005822,vs-explore-20260929-004109}/`。A 分支不合回、模型修复转正待决策；#1698 不移植（证据口径）；#1800/F5 为可上报素材。 |
| 2026-09-29，catalog 回调原结构恢复 | `31523ab`（amend替代`6fefb6b`）：精确候选64库＋24bin、主工作区82库＋24bin、默认两项collector/编译/fmt PASS；原callback及生产区注释无缺失 | [版本、命令与证据](../agents/float_support_review/catalog-commit-review-20260929.md#恢复回调原结构和注释2026-09-29)。恢复原嵌套分支、日志、早退，原闭包追加终态；仍过滤已知x0旧失败，未跑全量solve/完整Sail/硬件重放。原27文件暂存保留。 |
| 2026-09-29，当前工作区 XiangShan 标量浮点 DiffTest | 冻结 IR `73dfb2e1…671d2a`／Isla `4e315e9a…59ae0`／FD 配置 `20851fdb…723d0`；本仓 XiangShan `a13efc8`、MinimalConfig `emu` SHA `8714169…a85ee`、配套 NEMU SO `9188e7d…ef43`、pipeline `8099715d…22390c`。51 JSON／1344 输入；本地支持分区 1322/1322 GOODTRAP＋退出0（1145 Retire、177 Illegal），32 FPR 原始位＋fcsr post 检查通过。22 BF16 Retire 于 payload cause 2，负对照 f0 检查失败；管线测试 77/77。 | [逐例本地核账](../difftest-xiangshan/work/float-v3-20260929/current-workspace-audit.json) SHA `97b8dfe3…cb610bf`、[运行详情](../agents/difftest_xiangshan_v/status.md)。核账逐条比对51份冻结 JSON；首轮短超时与第二轮5条超时均单独封存，只按最终成功重试计通过；另一工作区的旧结果不计本轮。BF16 不支持、其它数值域未覆盖，C++/Isla 双后端重放与源码 branch 未闭合，77 项正式验收不变。 |
| 2026-09-29，catalog 单调用封装整理 | `6fefb6b`（amend替代`f5aa97d`）：FS/VS16组合迁到真实collector前后均通过；最终隔离64库＋24bin、主工作区82库＋24bin、默认两项collector测试/编译/fmt PASS | [版本、命令及测试迁移记录](../agents/float_support_review/catalog-commit-review-20260929.md#撤销单调用封装2026-09-29)。两项直接封装测试由真实collector验证替代；库过滤已知x0失败。未跑完整Sail指令、全量solve或硬件重放；原27文件继续暂存。 |
| 2026-09-29，catalog 最小修正 | `f5aa97d`（amend替代`d740e02`）：真实collector红例确认Memory_Exception被拒绝；修复后八场景、隔离66库＋24bin、主工作区84库＋24bin、默认定向测试/编译/fmt PASS | [版本、命令、测试准备失败及证据](../agents/float_support_review/catalog-commit-review-20260929.md#最小修正与-amend2026-09-29)。库回归过滤已知x0失败；未跑完整Sail指令、全量solve或硬件重放。原27文件继续暂存，另外index条目和工作区文件保持。 |
| 2026-09-29，catalog 单提交收拢 | Isla `d740e02`（amend替代`1b7276b`）精确候选72项trace、83项executor、65库及24bin通过，默认编译/fmt/diff检查通过 | [版本、命令及日志](../agents/float_support_review/status.md#catalog-单提交收拢2026-09-29)。库测试另有x0列表断言失败，已在`1b7276b`复现同一失败，过滤后回归；未跑全量solve，原暂存树/工作区字节保持。 |
| 2026-09-29，catalog 独立提交 | Isla `1b7276b` 精确候选66项 itrace 测试通过，isarch 默认及 itrace,smt-thread-interrupt 编译、fmt/diff检查通过；原暂存树及31个工作区文件哈希保持 | [提交、命令和证据](../agents/float_support_review/status.md#catalog-独立提交2026-09-29)。首轮残留元数据测试断言导致1失败，拆分修正后通过；未跑全量solve/重放。 |
| 2026-09-28，Execute 入口编码残留清理 | 旧代码真实物化FS=VS=0回归失败（NoModel），删除编码模式/钉值后16组合通过且编码字段保持；itrace,smt-thread-interrupt下84库＋24bin及fmt/diff检查 PASS | [实施接续与日志](../agents/float_support_review/scope-review-20260928.md#用户明确边界后的实施接续)。只改工作区exec.rs，未迁全量solve或历史重放结果，未更新暂存区。 |
| 2026-09-28，Isla 浮点改动范围 review | `b18d6b7`＋暂存 diff `02bf5c1c…fa011`、d012 IR；默认 features FP 10/10、isarch bin 24/24、isla lib 84/84 PASS；系统 Python 环境清理兼容测试 1 项 FAIL（第223行） | [命令与审查记录](../agents/float_support_review/scope-review-20260928.md)。未修改生产代码，未重跑官方 solve/完整 IR 等价；静态问题与动态结果分列。 |
| 2026-09-28，内存一致性 W24 最新生成+24 路并行 DiffTest campaign | WT e4410fe/isarch md5 bd945aa4…/`_csr_sym` 配置/pipeline 41ff806（仓库零改动）；阶段 A：41/44 clause 共 1990 路径——恢复类 AMO 0→552（W20）、C_F* 0→70、STORE_FP 0→80（LOAD_FP 仍 0），向量收缩 −75~−90%（mstatus VS=Off 分支消耗预算，只记现象）；重放 37 clause、1683 实跑、1307 pass（77.7%，剔 ext-missing 213+已知错位 13 后 89.8%），LOADRES/STORE/压缩标量/FENCE/SINVAL 满分；候选发现分诊 8 条：F1 模型 bug 坐实（`vext_utils_insts.sail:202` illegal_load 缺 vd+nf×EMUL≤32 组界检查，emu 权威 `VecExceptionGen.scala` lsSegIllegal，12 探针吻合）、F2 vstart 保留区过严 80 例、F3 isarch AMO 非 aqrl post-memory 漏物化 7 例、F4 FPR/VPR 初值缺失 30 例、F5 VLSEGFF case-038 唯一真 ABORT（NEMU/emu v0 复位差 1 字节）、F6 管线 VS=Off×向量前导+MPRV×PMP 先序、F7 SC 无前置 LR 15 例、F8 错位真分歧 13 例 | [SUMMARY](/data1/baiyifan/tmp/campaign24-20260928-193712/SUMMARY.md)、[议题状态](../agents/memsolve_branch_coverage/status.md)、[findings](../agents/findings.md)。受限：VLX/VSX 无重放面、VS=Off 剥离为明示偏差、向量产率降至旧 1/8~1/10、/tmp 配额事件致伪挂死已改 /data1、F3/F4/F7 待修复后复验。 |
| 2026-09-28，workaround 唯一配置归属 | Sail-RISC-V 中 79 份 `strict=false` 配置带已提交 V128 IR `6fc39efd…` 基准哈希，Isla 79 份副本已删除；Make 77 个绑定目标直接引用 Sail-RISC-V。Isla 非严格哈希失配告警/继续与严格拒绝两项 Rust 单测通过，Make/TOML 三项测试通过；f8ce849 模型树 132 region/22 锚点 PASS，当前暂存模型源码检查 FAIL（旧坐标漂移）。未跑全量 solve。 | [现行状态](../agents/workaround_ownership/status.md)；旧生成器已删除，当前暂存源码坐标仍需重绑。 |
| 2026-09-28，直接 `zexecute` 入口 v3 的 51 标量 | Isla `fc9ba690`＋未提交直接入口/终态见证修复，二进制 `4e315e9a…59ae0`，IR `73dfb2e1…671d2a`，FD 配置 `20851fdb…723d0`。`make -o build-isarch -k -j48`，51 项，T1，1800/1740/30 秒，qfaufbv，ITRACE，完整符号输入；51/51 退出 0、JSON complete，1344 gen（1167 Retire＋177 Illegal），51 份日志及 trace 的 case-id/status/signature 全等；输出见证 FS/VS 均为 3。仅证明直接 execute 求解及日志守恒；同版本物理译码、C++/Isla 全量重放、源码 branch 未完成，不能迁记旧 56cc 的 PASS。 | [命令与身份](../isla/target/float-solve-evidence/direct-entry-73df-batch-20260928/evidence/batch-v3-scalar-launch.json) SHA `2528f5b9…04ef0`，[逐项哈希与核账](../isla/target/float-solve-evidence/direct-entry-73df-batch-20260928/evidence/batch-v3-scalar-audit.json) SHA `91a0a3a1…c7b5fa2`；正式主 IR 仍 d012。 |
| 2026-09-28，直接入口向量预检 | v2 `-j16` 向量批因失败主动中止；宿主复查并终止遗留进程后，最终 23/26 启动，7 项 `complete=false` JSON，16 项无最终 JSON，3 项未启动，0 项完成。v3 `VFMVFS` 定向 120/90/30 秒真实退出 1，9 终态＝3 Retire＋3 Illegal＋2 具体编码无返回＋1 Sail Assertion；case 2/6 的 execute 已返回 Illegal，仅编码无返回；case 9 的合法 vtype、SEW=8 越过该指令译码守卫，在 `vext_fp_insts.sail:1848` 断言失败。当前直接执行配置域不能签 26 向量。同版本 replay runner 因当前 `isla-lib` 六处 API 不匹配未建成，故无重放 PASS。 | [专题状态](../agents/float_support_review/status.md)、[最终停止账本](../isla/target/float-solve-evidence/direct-entry-73df-batch-20260928/evidence/batch-v2-vector-stop.json) SHA `cb432bbd…f131ed9`、[v3 预检产物](../isla/target/float-solve-evidence/direct-entry-73df-batch-20260928/evidence/v3-preflight.tar) SHA `75a2e86f…b011a8bfe9c06`；不得将无最终 JSON 计入完成。 |
| 2026-09-28，73df FVFTYPE 两小时与路径爆炸诊断 | 隔离 IR `73dfb2e1…d2a`、e7ba 诊断运行器、77活跃strict、完整符号域/ITRACE、j1×T2、7200/7140/30秒；child7201.319秒外限124、make2、无最终JSON。残缺日志2212终态（33 Retire/2176 Illegal/3 nonenc）、trace 2,687,990,476字节只封哈希。790352已完成Z3操作中，SAT检查95679次；CheckSat/Assuming p99为1.236/1.001秒，最大4.398/3.057秒，≥5秒零次；实际双可满足fork6828，其中反向译码2544次来自运行器对77目标启用的`FullEncoded32`符号wrapper，并非Sail `execute`自身；另有向量组判断1449、FVFTYPE复合guard1305。当前证据支持路径增长及累计短查询，不支持单次SMT失控 | [诊断与源码/IR对照](../agents/float_support_review/path-explosion-diagnosis-20260928.md)、[退出账本](../isla/target/float-solve-evidence/num-elem-order-rm-eq-2h-20260928/evidence/exit-audit.json) `78a07ed4…ee72e`、[Z3耗时](../isla/target/float-solve-evidence/num-elem-order-rm-eq-2h-20260928/evidence/z3-duration-audit.json) `63ea5bcd…e49e`、[fork账本](../isla/target/float-solve-evidence/num-elem-order-rm-eq-2h-20260928/evidence/fork-audit.json) `a8dda7ff…13bb62`；不签完整trace守恒或回放。73df 的20未完目标均超时，旧56cc库存57/77不变。 |
| 2026-09-28，73df 剩余11项 30分钟诊断与19项目标汇总 | 新增 VFNUNARY0、FWVTYPE、FWVFMATYPE、FWVVMATYPE、FWVVTYPE、RFVVTYPE、RFWVVTYPE、VFUNARY1、VFWMACCBF16_VF/VV、VFWUNARY0 各独立 stage 均按 b42/73df、77活跃strict、完整符号域/ITRACE、j1×T2、1800/1740/30秒运行；逐项 child124、make2、无最终 JSON。连同前8项，19项局部日志合计32522终态、残缺trace合计42,018,002,096字节，只封存逐项哈希 | [19项逐目标退出汇总](../isla/target/float-solve-evidence/num-elem-order-rm-eq-candidate-20260928/target19-exit-summary.json) `34c03da3…00b7`绑定每项原账本/manifest；全19仍OPEN，不签完整trace守恒或C++/Isla回放。FVFTYPE两小时另待退出，旧56cc库存57/77。 |
| 2026-09-28，73df FVVTYPE/FWVFTYPE 全域诊断 | 73df IR、冻结 b42 运行器、77 活跃 strict、完整符号域/ITRACE、j1×T2、1800/1740/30 秒；分别 1801.373／1801.252 秒 child124、make2、无最终 JSON；局部日志 1591／3356 终态、残缺 trace 1,878,152,835／4,531,340,390 字节仅封哈希。无资源止损或 signal | [VV 退出账本](../isla/target/float-solve-evidence/fvvtype-73df-diagnostic-20260928/evidence/exit-audit.json) `9e041ce8…2acd`、[WVF 退出账本](../isla/target/float-solve-evidence/fwvftype-73df-diagnostic-20260928/evidence/exit-audit.json) `f8e34828…72a7`；无完整 trace 守恒或双后端回放，两目标仍 OPEN，旧57/77不变。 |
| 2026-09-28，73df FVFMATYPE/FVVMATYPE 全域诊断 | 73df IR `73dfb2e1…d2a`、冻结 b42 运行器、77 活跃 strict、完整符号域/ITRACE、j1×T2、1800/1740/30 秒；分别 1801.720／1801.335 秒 child124、make2、无最终 JSON；局部日志 2356／1813 终态、残缺 trace 2,729,862,142／2,183,077,089 字节仅封哈希。无资源止损或 supervisor signal | [VFMA 退出账本](../isla/target/float-solve-evidence/fvfmatype-73df-diagnostic-20260928/evidence/exit-audit.json) `97ee1203…0423`、[VVMA 退出账本](../isla/target/float-solve-evidence/fvvmatype-73df-diagnostic-20260928/evidence/exit-audit.json) `2fef431e…380e`。两项仍 OPEN，不签完整 trace 守恒或双后端回放，57/77 旧库存不变。 |
| 2026-09-28，73df FWFTYPE/VFUNARY0新IR全域诊断 | b42冻结运行器、73df IR、完整符号域/ITRACE、j1×T2/1800-1740-30秒；两项分别1800.551／1800.698秒child124、make2，均无最终JSON，残缺日志2932/1451终态；trace约3.91/1.75GB仅封哈希，不签完整守恒 | [FW退出账本](../isla/target/float-solve-evidence/fwftype-73df-diagnostic-20260928/evidence/exit-audit.json) `c850f84c…7fe8d`、[unary退出账本](../isla/target/float-solve-evidence/vfunary0-73df-diagnostic-20260928/evidence/exit-audit.json) `554269ed…95e4`；两目标仍OPEN，后续FVVTYPE/FWVFTYPE另stage诊断中。 |
| 2026-09-28，73df FADD.S保留rm=110定向复验 | 物理word `0x0020e1d3`、FS使能，使用新IR `73dfb2e1…d2a`与实际重物化的初始化侧车；Isla双阶段实际执行PASS、CPP AST/ret/102字段匹配，异常槽沿途写0。89条新回放已有同clause rm=101原输入，两个保留位值分别记账 | [新IR限定见证](../isla/target/float-solve-evidence/num-elem-order-rm-eq-rm6-directed-20260928/summary.json) `ce61b42a…388d`；此为定向译码负例，不改56cc官方零覆盖或77完成库存。 |
| 2026-09-28，73df FVVMTYPE/FVFMTYPE新IR全域诊断 | 517冻结runtime/b42运行器、IR`73dfb2e1…d2a`、77活跃strict重绑、完整符号域/ITRACE、j1×T2/1800-1740-30秒；两项分别1800.722／1800.945秒child124、make2，均无最终JSON。局部日志1199/1572终态，残缺trace约1.46/1.98GB已封哈希但未签完整守恒；旧56cc库存57/77不变 | [VV退出账本](../isla/target/float-solve-evidence/fvvmtype-73df-diagnostic-20260928/evidence/exit-audit.json) `a0389388…30cf`、[VF退出账本](../isla/target/float-solve-evidence/fvfmtype-73df-diagnostic-20260928/evidence/exit-audit.json) `d7b2720c…fa30`；无JSON不计目标完成，之后空槽转入FVFMATYPE/FVVMATYPE独立诊断。 |
| 2026-09-28，73df隔离候选89整指令双后端重放 | 新IR重导schema仅IR哈希变、五配置CPP回放器均重建；原89条输入重新物化与生成新初始化侧车，13组89/89实际Isla/CPP的完整AST、返回值、102字段匹配，178阶段/2533781条指令/沿途异常写0。首次尝试因旧侧车版本拒绝留存；旧新输入顶层字段相同，`zpma_regions`侧车序列化顺序不同，不声明全局初始化等价 | [配对结果](../isla/target/float-solve-evidence/num-elem-order-rm-eq-replay89-20260928/summary-v2.json) `0aff37a3…1e31`、[复核](../isla/target/float-solve-evidence/num-elem-order-rm-eq-replay89-20260928/independent-scope-review.json) `10e77958…dd71`；限新IR `73dfb2e1…d2a`/五配置/列定89输入，不计77官方完成或源码闭合。 |
| 2026-09-28，RM转换纯比较双后端隔离候选 | 在match顺序候选上只改`riscv_valid_rm_to_ieee`四个3-bit相等；完整CPP/IR构建退出0，IR `73dfb2e1…d2a`较前版2049函数仅此函数变动。新CPP、新Isla与独立native对67 helper的83 smoke＋17,586 full输入均逐例PASS；五分钟FVFTYPE诊断外限124/无最终JSON，两版前缀均未调用该RM函数，不能从短对照推收益。30分钟同runtime完整域诊断也外限124、无最终JSON；RM转换位点448次／228.735秒→0，总完成Z3调用245494→261566、局部终态684→732，不计官方完成 | [完整构建](../isla/target/float-solve-evidence/num-elem-order-rm-eq-build-20260928/model-build.json) `06b84fdd…1f3c`、[函数IR差异](../isla/target/float-solve-evidence/num-elem-order-rm-eq-candidate-20260928/ir-delta.json) `1933456f…d5c8`、[三方限定结果](../isla/target/float-solve-evidence/num-elem-order-rm-eq-crosscheck-20260928/overall-summary.json) `3c36b568…7d01d`、[长预算诊断](../isla/target/float-solve-evidence/num-elem-order-rm-eq-candidate-20260928/long-comparison.json) `3c1b584a…c6bb`；生产Sail/正式主IR未切换，完整ISA及源码17门待验。 |
| 2026-09-28，fc4 FADD.S原始rm=110定向拒译 | 从原89条中rm=101完整初态派生新run-id，物理word `0x0020e1d3`（rm=110、FS使能、fcsr=0）；fc4 Isla实际解码`ILLEGAL`、两阶段重放PASS，C++ AST/ret/102字段配对通过，8let/15aux读回一致。旧run-id首试产物留存，最终只计v2 1例 | [限定双后端见证](../isla/target/float-solve-evidence/fc4ce-rm6-directed-20260928/final-summary.json) `36aa0dad…2509`；与原89条rm=101见证并列，仅定向输入，不转记56cc官方57目标/77完成数，也不签17源码门。 |
| 2026-09-28，fc4官方目标隔离续跑与下一性能候选 | 旧FVVMTYPE/FVFMTYPE stage被人工中断、无最终JSON；新stage复用同IR `fc4ce909…86415`、517源码/b42二进制与完整符号域，以1800/1740/30秒、j1×T2、完整ITRACE运行；两项分别1800.64/1801.05秒外限124、make2、无最终JSON，残缺日志局部终态1145/1435，库存57/77不变。`assert_vector_num_elem_upto_128`仅在隔离副本重排`<=16`的互斥match；整数集合差异SMT为UNSAT、完整CPP/IR构建退出0。五分钟同二进制对照两侧均外限124/无求解JSON，五处Eq查询162→30、FFI 64.787→16.006秒；只签局部热点下降；同e7ba的新IR 30分钟诊断也child124/无最终JSON，Eq调用相对旧fc4 30分钟1612→384、FFI642.207→144.109秒，局部终态606→684，仍不计官方完成 | [新FVVMTYPE manifest](../isla/target/float-solve-evidence/fvvmtype-fc4ce-resume-20260928/evidence/manifest.json) `8dd4643a…f2af0`、[新FVFMTYPE manifest](../isla/target/float-solve-evidence/fvfmtype-fc4ce-resume-20260928/evidence/manifest.json) `65cbaeac…dac7a`、各目录`resume-provenance.json`；[官方双目标退出账本](../isla/target/float-solve-evidence/fc4ce-resumed-two-targets-20260928-summary.json) `b954049d…04d3`、[隔离候选清单](../isla/target/float-solve-evidence/num-elem-order-candidate-20260928/source-manifest.json) `10649f20…c8b2`、[完整构建](../isla/target/float-solve-evidence/num-elem-order-build-20260928/model-build.json) `303507a1…2121`、[短诊断对照](../isla/target/float-solve-evidence/num-elem-order-candidate-20260928/short-comparison.json) `d77a2b78…0669`、[30分钟对照](../isla/target/float-solve-evidence/num-elem-order-candidate-20260928/long-comparison.json) `ed51cb64…9a95`。生产模型与正式主IR未切换。 |
| 2026-09-28，内存一致性 W21 CSR 符号化与 FD 恢复 | `[symbolic_registers]` 机制（pin_mask/pin_value+nonzero_groups、冲突硬失败、物化门读按路径具象化 CSR 克隆、符号后 Assert、未声明零开销）；mstatus 钉死定稿（SD/MBE/SBE=0、FS≠Off 域、MPP/MPRV/MXR/SUM/TVM/VS/UXL 全符号）；FD 恢复验收：Zcd 四 clause gen 与 G8 已执行基线逐项一致（32/32/24/24）、mstatus 模型值全量输出违例 0、zSTORE 对照零影响（128/514/6s 一致）；CSR 全量审计（satp/PMP 两难与分阶段建议、6 个 CSR 保持钉死、fcsr 挂议题） | [议题状态](../agents/memory_support_review/status.md)、[CSR 审计](../agents/memory_support_review/csr-audit.md)、[findings](../agents/findings.md)、证据 `/data1/baiyifan/tmp/isla-memimpl-w21-20260928-030550/`；worktree 898e267。遗留：STORE_FP/LOAD_FP（width 守卫+符号长度 zeros）、C_FLW/C_FSW RV64 死、PMA 符号 size 与 CSR 符号化共存未端到端。 |
| 2026-09-28，内存一致性 W20 AMO panic 根治 | IR 加载期 8 个比较算子改写位向量原生 Bvult/Bvslt（n<128 逐例等价、n≥128 唯一正确语义）；TDD 10+1 绿、isla 119/119、isla-lib 263 过；端到端 zAMO：rc=0、23s、670 gen（原 rc=134 零产物）=258 成功+408 AF+4 Addr_Align，五宽度与 aq/rl 变体齐全，amominu.q.aq 复现 Retire_Success+16B 独占事件；G3 出口基线 #1-6/#10-11 达成 | [议题状态](../agents/memory_support_review/status.md)、[findings](../agents/findings.md)、证据 `/data1/baiyifan/tmp/isla-memimpl-w20-20260928/`；worktree 0c4fd52。遗留：AMOCAS 两臂（#7/#8）需定向约束、写阶段 fault（#9）形态难现。附带发现：/tmp 配额满致 println panic→SIGABRT 空 stderr 酷似引擎缺陷，产物已迁 /data1/baiyifan/tmp。 |
| 2026-09-28，56cc BF16局部symbolic RM独审收尾 | 既有19 PC、六成员、三配置的正常未截断helper路径证按1501依赖重hash零漂移；34封包文件`sha256sum -c`全部通过。本次仅封存历史执行，新动态运行0 | [局部证书](../isla/target/float-support-review/final-coverage/integration/p1-56cc69/bf16/independent-three-config-symbolic-rounding-enum-contract-review-v1/certificate.json) `ceb6750e…3a80c`、[BF后继导航](../isla/target/float-support-review/final-coverage/integration/p1-56cc69/bf16/resume-navigation-20260928/index.json) `c2c42e05…08ceb`；17全局/8 BF义务仍OPEN，不迁fc4或完整encoder。 |
| 2026-09-28，fc4 FVVMTYPE/FVFMTYPE首次官方stage | 两份独立stage绑定IR `fc4ce909…86415`、517源码/b42二进制；79配置预检问题0、无执行限制dry-run通过。两路`single.started`和5秒监控实际记录正确目标、1800/1740/30秒、j1×T2、完整符号域与ITRACE；约7分钟后按指示人工终止，均无最终JSON，不计自然完成 | [FVVMTYPE准备](../isla/target/float-solve-evidence/fvvmtype-fc4ce-prepared-20260928/evidence/manifest.json) `0ccc34ac…1996`、[FVFMTYPE准备](../isla/target/float-solve-evidence/fvfmtype-fc4ce-prepared-20260928/evidence/manifest.json) `d84707d7…4f81`；残缺日志/trace保留，结果以新stage另计。 |
| 2026-09-28，fc4 FVFTYPE独立诊断 | 1800.655874秒子进程124、无最终JSON；173591569字节完整Z3 JSONL有219605完成调用/2未完/0残行，FFI占匹配worker窗口97.636480%。局部601 Illegal/2 Retire/3 nonenc；完整trace正文未签，不计官方完成 | [分析汇总](../isla/target/float-solve-evidence/z3-diagnostic-fc4ce-fvftype-analysis-20260927/final-030m/summary.json) `97ebd663…9466`、[分析报告](../isla/target/float-solve-evidence/z3-diagnostic-fc4ce-fvftype-analysis-20260927/final-030m/report.md)。同e7ba二进制/518诊断runtime与a040匹配；模型仅V utils源一处变化。旧batch退出sidecar缺失，未补造；整数相等五处1612次/642.207秒为下一隔离候选，不签全域加速。 |
| 2026-09-28，fc4统一浮点67 helper与89整指令独审 | 新83＋17586 helper三方比较、独审18,240绑定零漂移；五配置原89输入的新C++/Isla完整AST/ret/102字段、8let/15aux一致，178阶段/2535845指令/异常槽沿途写0；8实际负控拒绝，native22,640绑定零漂移 | [helper独证](../isla/target/float-solve-evidence/unified-backend-build/model-valid-reg-group-eq-build-20260927/helper-crosscheck-valid-reg-group-20260927/independent-review/certificate.json) `f5313cf0…3291`、[89 native终证](../isla/target/float-solve-evidence/unified-backend-cpp-replay/sharedtrace-valid-reg-group-source-bridge-20260927/independent-cpp-initialization-review/certificate.json) `8e774fd9…02b2a`及[交付汇总](../isla/target/float-solve-evidence/unified-backend-cpp-replay/sharedtrace-valid-reg-group-replay-20260927/final-directed89/summary.json) `40296a3d…e499`。限该IR/列定输入，非官方全77或源码branch闭合。 |
| 2026-09-27，a040 RFVVTYPE两小时全域求解 | 7201.04秒timeout child124、无外信号/最终JSON/资源stop；局部1389 Retire/2782 Illegal/3不可编码，残缺trace5600260763字节、峰RSS6872184 kB；a040两归约均未自然完成，库存57/77保持 | [退出账本](../isla/target/float-solve-evidence/rfvvtype-nan-reduction-a040-2h-prepared-20260927/evidence/RFVVTYPE-timeout-audit.json) `7bfa96ef…62e3`；两官方空位待fc4新67/89独审齐后接FVVMTYPE/FVFMTYPE，独立FVFTYPE诊断另列。 |
| 2026-09-27，a040 RFWVVTYPE两小时全域求解 | 7200.76秒timeout child124、无外信号/最终JSON/资源stop；局部745 Retire/1210 Illegal/3不可编码，残缺trace2709679027字节、峰RSS3607544 kB；仍未自然完成，库存57/77不变 | [退出账本](../isla/target/float-solve-evidence/rfwvvtype-nan-reduction-a040-2h-20260927-c/evidence/RFWVVTYPE-timeout-audit.json) `5ea8a749…2066`；未把残缺trace当完整核账，下一fc4 FVVMTYPE待新版回归门齐后接续。 |
| 2026-09-27，fc4完整IR/CPP与strict/source双独审 | 完整IR仅valid_reg_group语义体变化，C++其余对象/8827884 tokens对应保持；fullIR14227依赖及负控通过。strict/source7517绑定零漂移，129region/422实际选择保持，20region/4锚点位移验证通过 | [完整结构证](../isla/target/float-solve-evidence/unified-backend-build/model-valid-reg-group-eq-build-20260927/independent-full-ir-review/certificate.json) `b2fcac07…9be6f`、[strict/source证](../isla/target/float-solve-evidence/unified-backend-build/model-valid-reg-group-eq-build-20260927/independent-strict-source-review/certificate.json) `618b90ef…8f888`；2历史空region/2归档保留，旧坐标真实负控暴露7区域错误。新67/89回归及求解收益另验。 |
| 2026-09-27，a040最终30m Z3统计/位置独审 | 155837644字节一次流读，199004完成/2未完成/544 worker（541 closed）；140分组/114 site核等。完成FFI3516.985722783秒÷匹配窗口3593.730093966秒＝97.864493%；valid_reg_group PC29为1789次/875.449186734秒，完整IR与文件位置表独核 | [最终独证](../isla/target/float-solve-evidence/z3-diagnostic-a040-fvftype-analysis-independent-review-20260927/final-030m/review.json) `8e213656…99c6c`；child124/无JSON，仅核账/查询位置，不签CPU/FP因果、优化收益或官方完成。 |
| 2026-09-27，valid_reg_group新版完整CPP/IR构建 | 新IR `fc4ce909…686415` 与同源C++构建PASS，7产物完整、79历史接口＋3状态接口保持 | [构建报告](../isla/target/float-solve-evidence/unified-backend-build/model-valid-reg-group-eq-build-20260927/model-build.json) `6a7b98c2…c675f`；完整IR/strict-source独审、20region/4锚点迁移及新67/89实际回归继续，不迁a040动态结果。 |
| 2026-09-27，a040匹配基线Z3诊断退出 | 同e7ba诊断二进制/1800-1740-30秒/两线程/全输入域；1800.60秒child124，无signal/资源stop/最终JSON，局部2 Retire/536 Illegal/3不可编码；查询日志已冻结待最终统计独审 | [退出账本](../isla/target/float-solve-evidence/z3-diagnostic-a040-fvftype-20260927/evidence/diagnostic-exit-audit.json) `cdfbd2b8…5b53d5`，JSONL `347f964a…acf8`；独立诊断不计官方完成，后续validreg须使用相同二进制与预算对照。 |
| 2026-09-27，valid_reg_group生产应用与双strict | 单点应用e140后像，仅目标文件729→730行；931源逐项符合expected、其余930不变。普通179.08秒/SYMBOLIC185.84秒完整strict均exit0，全程无漂移 | [生产交接](../isla/target/float-solve-evidence/valid-reg-group-production-20260927/handoff.json) `cec4a3be…f4fe0`；完整CPP/IR及20region/4锚点实际迁移待构建，旧a040回归不迁记。 |
| 2026-09-27，nan86f最终30m Z3统计独审 | 157818104字节一次流读，199501完成调用/545 worker（542 closed）、2未完成/0 partial；146分组/114 site及top表全核。完成FFI3519.092413404秒÷匹配worker窗口3593.033153190秒＝97.942108%，closed97.904266%；valid_reg_group PC29为1789次/843.498757342秒 | [最终独证](../isla/target/float-solve-evidence/z3-diagnostic-nan86f-fvftype-analysis-independent-review-20260927/final-030m/review.json) `9a9ea14e…8427c`；child124/无JSON，有限PASS只签核账和调用位置，不代表CPU/FP成本、性能收益或官方完成。 |
| 2026-09-27，a040统一公共接口身份核定 | 190 typed声明＝186 C++ native＋4 Sail工具，对应82个不同FP原语名；当前模型调用97 FP实例/45名。a040/live/P1七adapter同字节，工具链及实际TLS/FAST/WIDE/EXTRA构建链、三个环境TLS符号核对通过 | [核定简报](../isla/target/float-solve-evidence/unified-backend-current-interface-audit-20260927/brief.md) `34044196…c2bd3`、checks `d5430336…e2eb`。可复用73ac完整190声明/251生成方法fixture证；本轮为身份核对，非重新执行全矩阵或任意值域证明。完整模型仍按进程隔离。 |
| 2026-09-27，valid_reg_group末尾相等隔离组件独审 | 共用无约束bv5/int128的两条完整符号路径差异UNSAT；768具体输入对、3904次CPP helper执行、8项strict/生成命令通过，错误IR被真实SAT拒绝；2293依赖零漂移 | [组件独证](../isla/target/float-solve-evidence/valid-reg-group-final-equality-design-20260927/independent-review/certificate.json) `1e7763cf…efa99`；仅末尾相等换用既有option(int)/eq_anything，guard/pow/mod/转换顺序保持。组件PASS，生产完整构建/严格区域迁移及实际求解收益另验。 |
| 2026-09-27，86f独立Z3诊断最终退出 | 1800.55秒外限child124、无信号/最终JSON/资源stop；局部2 Retire/537 Illegal/3不可编码，峰RSS3663104 kB；完整查询日志157818104字节已冻结，最终查询统计待独审 | [退出账本](../isla/target/float-solve-evidence/z3-diagnostic-nan86f-fvftype-20260927/evidence/diagnostic-exit-audit.json) `9cbd316d…246c`，JSONL `43b87f55…e07e3`；仅独立诊断，不计官方完成或语义PASS。 |
| 2026-09-27，86f FVFTYPE两小时全域求解 | 7200.89秒监督器child124、无信号/JSON/资源stop，整项仍未完成；官方唯一自然完成库存57/77保持 | [官方记录](../agents/float_support_review/solve-fix-official.md)，a040 RFVVTYPE于10:58 UTC以完整域7200/7140/30秒接续，与RFW并行；独立Z3诊断另列。 |
| 2026-09-27，Z3诊断固定首前缀独审 | 实际362.365秒捕获，47258完成调用/131worker/2未完成；完成FFI701.210秒÷匹配worker窗口718.657秒＝97.5723%，closed子集97.5654%；精确查询位置聚合与输入哈希独立复核一致 | [前缀独审](../isla/target/float-solve-evidence/z3-diagnostic-nan86f-fvftype-analysis-independent-review-20260927/prefix-005m/review.json) `2e6de8ee…53613`；仅有限观测wall比例，不推CPU/FP因果；open窗不延长到capture，incomplete不补FFI下界。 |
| 2026-09-27，a040官方入口精确装配独审 | 旧snapshot因报告schema/多前像拒绝、两次no-spawn失败保留；新stage517项恰1IR＋77活跃配置变化，79配置含2归档、b42构建复用链与d103/517双证全核，1210绑定及6负控通过 | [入口独审](../isla/target/float-solve-evidence/entry-adaptation-independent-review-20260927/review.json) `f43ad333…beef1`。RFWVVTYPE于10:42 UTC实际启动7200/7140/30秒全域运行，尚无完成结论；独立诊断不混入official。 |
| 2026-09-27，a040组合新版89整指令最终双独审 | 五配置/13初始化/原89输入完整物化并配对，178阶段/2535669指令/异常槽写0，8let15aux与AST/返回值/102字段全匹配；13组observer独立复跑与8实际数值负控通过 | [重放记录](../agents/float_support_review/solve-fix-replay.md)，summary `3df8df58…a22dc`，native `04a03b0d…9f609`（16248绑定）、witness `63bb5c1c…84b9d`（16149绑定）、联链 `fa31bc4c…ff7c3`。只签实际raw a040＋冻结runtime/新CPP，不冒充尚未启动的officialstage或全77/source闭合。 |
| 2026-09-27，a040 nan＋归约新版67 helper三方独审 | 83＋17586新CPP/native独立复跑、17669新IR精确tuple核对、15测试/控制全部通过；11737依赖零漂移并联完整模型/严格配置证 | [数值报告](../agents/float_support_review/unified-backend-crosscheck.md)，独证 `902c1d60…83332`，fullIR `d1031e6a…9e5f8`、strict `517a7cad…ba7ae`；仅67 helper列定输入，不签官方全域/全77/全部typed接口。 |
| 2026-09-27，Z3最小诊断v2限定独审 | 默认关闭、phase=null、独立JSONL；677封包/518源核验，24消费端控制与9默认＋9interrupt＋真实timeout1＋旧契约2通过，4180实际begin/end及旧off/v2off/v2on完整结果一致 | [诊断独审](../isla/target/float-solve-evidence/z3-call-diagnostics-independent-review-20260927/v2/report.md)，证 `10115c84…4a056`、binary `e7ba503a…10f81`；v1 phase/分析器缺陷保留为NEEDS_REVISION。可用于独立全域诊断，非FP/CPU主导或官方PASS结论。 |
| 2026-09-27，86f nan新版89整指令完整双独审 | 全63＋26/五配置/13初始化侧车，AST/返回值/102prepost及实际8let15aux一致；178阶段/2535669指令/沿途异常槽写0，13组observer独立复跑通过 | [重放记录](../agents/float_support_review/solve-fix-replay.md)，summary `668b4509…933da`、witness `c899afe3…a37d1`（13280绑定）、native `a49d144e…feb24`（15105绑定）、联链 `8414ffaf…fe4d8`；仅该版本列定输入，非官方全域/全77/source闭合。 |
| 2026-09-27，441c VFUNARY1两小时全域求解 | 7200.64秒监督器child124、无信号，make/monitor2、无最终JSON，未自然完成 | [官方记录](../agents/float_support_review/solve-fix-official.md)，stage `vfunary1-lmul-unary-441c-prepared-20260927/`；nan86f FVFMTYPE于09:44 UTC接续1800/1740/30秒全域运行，不提前使用未全审的归约候选。 |
| 2026-09-27，86f nan新版67 helper三方独审 | 新CPP/IR及native的83＋17586完整比较通过；17669新IR精确tuple检查与CPP/native独立复跑通过，19测试控制、11070依赖核验 | [数值报告](../agents/float_support_review/unified-backend-crosscheck.md)，独证 `fe432ce3…5bc06`。后续归约live V变化一项显式映射到同原hash冻结源，历史drift=1保留；仅67helper列定输入，不签全77/源码分母。 |
| 2026-09-27，完整回放trace receipt限定独审 | 21原测试＋7独立负控通过；独立7输入/3片真实回放exit0，14阶段/130683指令/异常槽写0，完整数值对象一致。六调用实际3完整读取＋3复用，9.6MB trace共读28844370B | [独审记录](../agents/float_support_review/unified-backend-cpp-replay-independent-audit.md)，独证 `9984f6c0…4b51c`，1810绑定；只同父进程/同epoch/原trace许可范围，保final fresh，旧工具不改，不外推大包墙钟。 |
| 2026-09-27，内存 clause 分支覆盖对照（W19+G1-G8） | 48 clause 跑批（worktree d643e0e isarch、`riscv64_difftest_mem_excluded_pma.toml`、fork 1/12、smt-timeout 1m、600/1800/3600s 三档）：45 有 JSON、4124 gen（1251 成功/1135 Load_AF/1012 Illg/712 SAMO_AF/10 VirI/4 Addr_Align）、降级 0；zSTORE 24/104 与 W15 基线逐数一致。八组五分类对照收敛：①覆盖良好（标量/压缩 B/H/LR/SC/向量段式含 first-fault 全分支/cbo-fence 全）；两次勘误（`plat_enable_misaligned_access` IR 固化 true 致普通访存 Addr_Align ②不可达仅 LR 可出；`sys_enable_fdext` 死键、FD 真实闸门 mstatus.FS，Zcf 四条 RV64 应剔除）；④缺陷 7 项（AMO min/max.q panic 全缺、LOAD_FP 符号 width zeros、终值物化脱钩、is_exclusive AK_arch、--instruction-bits panic、W/D store 零拆分写嫌疑、独占 Bool 偏置）；③集中在 VLX/VSX（5-12×）与 W/D 分块路径 | [议题状态](../agents/memsolve_branch_coverage/status.md)、[合并矩阵](../agents/memsolve_branch_coverage/coverage-matrix.md)、[SURVEY](/tmp/isla-memsolve-survey-20260927-125738/SURVEY.md)、[组报告](/tmp/isla-memsolve-survey-20260927-125738/coverage/)。AMO/VLXSEGTYPE/VSXSEGTYPE 无产物；对照为产物核对+源码归因非新动态验收；勘误一同时修订 W13 上报项⑤前提。 |
| 2026-09-27，nan＋归约组合生产严格检查 | 归约现行组件证 `c76e79d6…36e85` 与nan前件桥 `8c99975d…27b83` 通过后，仅两归约helper应用，保FDdc8b；931源精确对expected，V真实＋3行，普通181.54秒/SYMBOLIC188.28秒完整strict退出0 | [实施报告](../isla/target/float-solve-evidence/nan-reduction-production-20260927/report.md)，handoff `a79109b4…ff50c`，新完整CPP/IR构建PASS（561秒，报告 `9f47ff72…ac9ee`，IR `a0405074…dfa7d`），strict/source独审 `517a7cad…ba7ae` 与完整IR/C++ `d1031e6a…9e5f8` 均通过。归约v1异常行为差异与旧manifest漂移证均保留，不迁旧候选动态PASS。 |
| 2026-09-27，441c FVFTYPE两小时全域求解 | 7200.90秒监督器child124、无外信号，make/monitor2、无最终JSON；官方唯一自然完成仍57/77 | [官方记录](../agents/float_support_review/solve-fix-official.md)，stage `fvftype-lmul-unary-441c-prepared-20260927/`。nan86f FVFTYPE于08:56 UTC接续实际启动；不把较低RSS/少终态写成收敛改善。 |
| 2026-09-27，441c新89整指令完整配对及独审 | 五配置63＋26原输入重新物化/执行；完整AST/ret/102prepost、实际8let/15aux一致，178阶段/2529965指令/异常槽沿途写0；13组observer独立复跑退出0 | [重放记录](../agents/float_support_review/solve-fix-replay.md)，summary `aad0ffdf…413c5`、数值 `2ba4713c…4df16`、witness/source/phase `a48bdd53…b2878`、provider `b5758211…f887f`；native总证 `9fb13e89…394f6` 与联链 `e0635e97…d6b74` 已封存。限定新441c列定输入，非官方全域/全77，旧e6a证不迁记。 |
| 2026-09-27，56cc 57目标完整输出机器映射 | 57唯一自然完成目标，80416唯一回放身份＝80283gen＋91direct＋42derived；32runID、3源binary分列，各包完整source/numeric/phase证逐目标映射通过 | [机器汇总](../.tmp/unified-backend-cpp-replay-independent-57-target-scope-56cc69/summary.json) `2b858535…deefd`，target-map `52b0b27f…5f6d3`；215直接证据重hash，未重复全trace/全部传递依赖审计。排除历史18584及42encoder辅助输入，20未完、全77/source仍未通过。 |
| 2026-09-27，56cc VFMERGE完整输出双后端最终独审 | 新目录真实退出0、3524.787秒；120/120片、30603输入（30600gen＋3direct）全部完整AST/返回值/102字段一致，61206阶段/940516587指令/异常槽沿途写0；source215491497边与7615非法操作数组合逐例核验通过 | [独审报告](../agents/float_support_review/unified-backend-cpp-replay-independent-audit.md)，summary `119a6cfb…016fa`、数值 `39ec127c…89707`、phase `e925f35c…21b9e`、最终联证 `74eff86c…e5b5a`。首次prepare失败及旧30分钟超时保留；当前57个自然完成目标的完整输出闭环不代表全77或源码分支闭合。 |
| 2026-09-27，56cc RFWVVTYPE两小时全域诊断 | 7202.35秒外限124，监督器确认无外信号/资源止损，make/monitor2，无最终JSON | [官方记录](../agents/float_support_review/solve-fix-official.md)，stage `rfwvvtype-2h-56cc-prepared-20260927/`；唯一自然完成仍57/77，不从局部Retire数推断全域或数值收敛。 |
| 2026-09-27，nan_unbox单行ITE生产应用 | 组件独审 `55d32438…0b81c` 通过无界n切片关系、29形状和Isla/CPP各1580检查；生产仅内层选择一行改变，其余930源码相同，普通/SYMBOLIC完整strict分别186.82/194.33秒退出0 | [实施报告](../isla/target/float-solve-evidence/nan-unbox-production-20260927/report.md)，handoff `764baa22…2724`。新完整CPP/IR构建PASS（报告 `60af7f07…c9052`，IR `86f1121b…7e61f`），完整IR/C++独审 `4f0f7e08…31b26` 与strict/source `43e1e908…ba975` 均通过；新官方/helper/replay待验，不迁441c PASS。 |
| 2026-09-27，441c新版67 helper三方实际回归独审 | 新CPP/Isla/原生flags oracle的83 smoke＋17586完整语料均通过，14161全位＋1733规范NaN＋1692无效整数返回，五flags一致；独立增强Isla精确tuple类型门17669条通过，3815绑定无漂移 | [数值报告](../agents/float_support_review/unified-backend-crosscheck.md)，报告 `ae4a9a2f…7ef06`、独证 `3f197c8f…463e1`；仅列定67 helper，不签整指令、全77或源码分母闭合。 |
| 2026-09-27，56cc BF16 VV两小时全域诊断 | VFWMACCBF16_VV 7201.33秒外限124，监督器确认无外信号/资源止损，make/monitor2，无最终JSON | [官方记录](../agents/float_support_review/solve-fix-official.md)，stage `vfwmaccbf16-vv-2h-56cc-20260927/`。不计完成，唯一自然完成仍57/77；释放slot后441c FVFTYPE已按7200/7140/30秒完整域启动，结果待验。 |
| 2026-09-27，LMUL＋unary统一模型完整构建 | 普通/SYMBOLIC strict均0，931输入仅两源变化；同源C++模拟器/模型库及新IR `441c145b…5f47c` 完整构建PASS，79＋3接口齐 | [构建记录](../agents/float_support_review/unified-backend-build.md)，报告 `752f10c9…dd12`、输入manifest `a2eeba26…539ae`；strict/source独审 `2ba9c521…1313` 已通过（3735绑定、422实际选择不变），完整IR/C++独审 `37609239…e6612` 亦通过（2841输入＋36审查文件）。尚未官方运行，不迁旧语义PASS。 |
| 2026-09-27，e6a五配置89输入完整重放独审 | 63＋26唯一输入；完整AST/返回值/102字段、8let/15aux匹配；178阶段/2531598指令/异常槽沿途写0，原57 Retire/22 execute Illegal/10 Decode Illegal来源保持 | [独审报告](../agents/float_support_review/unified-backend-cpp-replay-independent-audit.md)，summary `1dba7eeb…e23c7`，最终证 `0d414d76…5f6ca`，身份桥v2/v3及5215依赖绑定。仅定向域，不代替官方全77及源码分支闭合。 |
| 2026-09-27，56cc VFMERGE长预算及三目标续队列 | VFMERGE 2359.20秒自然0、30603终态、215491497分支边守恒；完整回放首轮prepare于2443.29秒退出1、输入审计未通过、未分片；7615条vd=0拒绝后获实际Sail/IR guard逐case独审 `f900c97b…e8f9f`，新目录完整30603重跑已启动（工具门 `e80cc2f4…b6168`）；另RFVVTYPE/RFWVVTYPE/VFUNARY1三目标均1800秒外限124，无完整JSON | [77项执行表](../agents/float_support_review/solve-audit-batch.md)，同56cc唯一完成索引 `d0d0988a…8b05d` 为57/77，20未完；旧VFMERGE30分钟失败保留，三目标timeout不计通过。 |
| 2026-09-27，56cc续批六成功目标完整回放 | H/S FMA、H/S/D BIN_RM前五27320输入逐包独审通过；VFMV5475输入另独审通过，合计32795成功输入但七项目标中VFMERGE外限124无JSON。VFMV源trace38148123边、5472重汇编及10950阶段观察全部核过 | [逐包独审](../agents/float_support_review/unified-backend-cpp-replay-independent-audit.md)，前五快照 `12003f32…57d7`、VFMV `2d980eed…6f612`，失败/交接 `78332c86…9cc`。同56cc跨stage共56/77自然目标，预算/runtime分列；七总PASS不成立，VFMERGE另启2h完整域运行。 |
| 2026-09-27，内存一致性 W18（S4）pipeline 地图假设过滤 | pipeline 解析 pma_regions size 模型值并按假设无关口径过滤（成功<真实顶界/fault≥，不一致跳过 reason=map-hypothesis-mismatch 并计数）；--map-limit 可配（默认 0x80000000000）；修复无 vreg 条目 8 字节占位 .data 与低地址用例相撞误判 code-overlap；测试 61/61（基线 44+17）；端到端：W17 case0 真机 GOODTRAP（1.39s，pre 恢复+U 态 payload+post 校验全过）、case1 正确跳过（hypothesis_consistent=true）、W12 ok 131 条重建 built=104/overlap=27 逐数一致且抽检 3/3 GOODTRAP、fault32 30/2 与 W13/W14 预分类一致 | [议题状态](../agents/memory_support_review/status.md)、[findings](../agents/findings.md)、证据 `/tmp/isla-memimpl-w18-20260927-104711/`（含 RESULT.txt）；根仓库 5ba0cec→6c56001，worktree 至 d643e0e 不变。遗留：多符号 region 仅记录 sizes、zLOAD 符号条目不支持（出现即报错）、--map-limit 不影响 preclass 口径；mcause 断言与 ④⑤ 分歧维持上报不修。 |
| 2026-09-27，sharedtrace新增23官方目标全量闭环 | 9692/9692=9624 gen＋55直接负例＋13派生负例，19384主阶段/260610144指令/沿途异常写0；完整trace47438081边、9233重汇编及391实际Illegal guard逐条独审。原两BF16 prepare失败保留，补输入证据后新目录完整通过 | [最终独审](../agents/float_support_review/unified-backend-cpp-replay-independent-audit.md)，证书 `12a39845…aec39d`、phase `dc88188a…177b2`、guard `25d0d16a…215f`。仅新23目标列定完整输出，旧25910不迁记，完整闭包纯读仍FAIL、全77/source branch未闭合。 |
| 2026-09-27，e6a完整IR与严格配置实际行为迁移 | 组件364形状/1040路径证明通过；完整2057函数仅execute局部变化、全局22494 SSA一一映射与6负控通过。129保留配置的实际选择集合旧新相同，127非空＋2历史为空，422 actual/470 overlap，历史退役1、新增退役0 | [IR记录](../agents/float_support_review/solve-fix-ir-generation.md)，IR `e6a3232d…7d27e`，结构 `dcb524a9…dd179`、SSA `9590c217…63bf55`、strict `7681cf6b…5464e`。旧“129均实际命中”不成立；不改配置掩盖历史空限制，性能与完整回放另验。 |
| 2026-09-27，内存一致性 W17（S2）PMA 边界符号化 | Spike 三点全过（plausible 放行符号 List(Struct)、defaults 注入后执行链完整消费、zrange_subset 符号比较自然分叉 3 路径 Sat）；端到端钉址 sb@0x80001000 同址两类路径——Retire_Success+写事件（size=0x1002 界内）/AccessFault（size=0x1000 界外）3/3 稳定 ~1.0s；具体基线回归一致、超域对照 x31=2^45 单 fault 证域约束生效；回归 119/119、fmt 过（预存 enum sort 崩溃 stash 对照无关） | [议题状态](../agents/memory_support_review/status.md)、[计划](../agents/memory_support_review/plan-pma.md)、[findings](../agents/findings.md)、证据 `/tmp/isla-memimpl-w17-091536/`；实现 6 文件 +735（PmaSize 双态、size_bounds 默认 [0x1000,2^43) 锚 emu 顶界、checkpoint 前注入、solve_pre_state 侧通道输出 size），worktree d643e0e、根仓库 8631735。遗留：首跑一次终值查询降级（高载偶发）、多 region 符号化未压测、属性符号化（S3）未做、符号边界用例重放需 pipeline 过滤（S4 职责）。 |
| 2026-09-27，三组实际异常状态observer全量补证 | D1096＋wave6230＋历史18584，共25910输入/51820实际ext_decode＋execute阶段/779354630指令，沿途隐式异常写0、typed初末相等；两后端完整结果与旧观察逐条匹配，4worker全exit0。最终独审2761文件绑定、全ID与canonical hash及48后端launch序列通过 | [完整独审](../agents/float_support_review/unified-backend-cpp-replay-independent-audit.md)，证书 `bb1a2459…b7fa`，总summary `f1805425…787c`。旧runtime＋唯一只读getter，完整闭包纯读仍FAIL；13 encoder专项和新同锁observer另列，不混计，仍非全77及源码闭合。 |
| 2026-09-27，trace共享版FVFTYPE完整30分钟对照 | 1805.04秒外层124、make2，无JSON；局部17 Retire/24990 Illegal/3 nonenc、无匹配执行/SMT异常。345条从spawn前开始的5秒资源采样：峰值RSS34.8GiB、最少可用105.7GiB，未触止损，trace28,924,314,971字节 | [官方记录](../agents/float_support_review/solve-fix-official.md)，stage `fvftype-sharedtrace-j1-56cc-20260927-080749`、binary `0c73a17e…`。旧j1约697秒RSS119.5GiB受控停止；本轮证明资源改善，目标仍未完成，残缺trace不冒充完整目标。 |
| 2026-09-27，内存一致性 W16 rv64_target_trait 清零 | 根因＝测试断言未跟上 fd92696 设计变更（x0/PC 排除从 setup_pre_state 上移到 reg_list，承重逻辑非环境依赖非回归）；按新语义改断言后 `cargo test -p isla --lib` 118/118 全绿、预置失败清零；顺带发现 RV32::reg_list 仍旧语义 (0..32)+PC 但 solve 路径 RV32 panic 不可达，记入遗留 | [findings](../agents/findings.md)、[议题状态](../agents/memory_support_review/status.md)、证据 `/tmp/isla-memimpl-w16-20260927-084122/`；worktree 21b4388（59e2b5d→f1fb43f→21b4388）、根仓库 b11a6f6→8cadc13→608f756。 |
| 2026-09-27，内存一致性 W15 非单调销案与 pma size 勘误 | 销案：W14"2^43 顶界非单调"为伪异常（探针实际钉 2^47，JSON x31 误读）；根因为 size=0x7FFF80000000 配置笔误（12 位十六进制多一个 F，base+size=2^47），W13 报告第 34 行推荐值算错作废，正确 0x7FF80000000；35 探针（W14 22+W15 13）按 Sail range_subset 环绕语义手算与实测 100% 吻合，非 Isla bug。修复复验（worktree commit f1fb43f）：钉址 13/13 全过、[2^31,2^43) 完全单调；green 全量 24 OK/104 FAULT 计数不变、24 写事件全部归入 8TB 内（修正前 20 条在外）；`cargo test -p isla --lib` 117 过/1 败（rv64_target_trait 为 HEAD 预置失败，stash 验证） | [议题状态](../agents/memory_support_review/status.md)、[findings](../agents/findings.md)、证据 `/tmp/isla-memimpl-w15-20260927-080623/`；fault32 9→0 零影响；green 24/104 成为修正后基线；W13"emu RAM=8TB"维持。W14 脚本 ISLA_RISCV_BUILTIN_* 在当前源码不存在（无效遗留，无害）。 |
| 2026-09-27，隐式异常let正常返回域补证 | 两IR/两root固定点独立复算一致，13负控通过，实际runtime初have_exception=false、无shadow与非Poison/Ctor或Bits/SAT门槛逐项匹配；指定正常返回域不写隐式异常lets，独审消费6401文件绑定 | [最终补证](../agents/float_support_review/unified-backend-cpp-replay-independent-audit.md)，架构 `7f606935…b648`、独审消费 `4cbc8ca9…e521`。恢复348147/56cc历史18584、新D1096、wave6230的列定成功输入双段语义签收；完整调用闭包纯读仍FAIL，异常路径不签，新observer回归另记。 |
| 2026-09-27，内存一致性 W14 PMA 8TB 对齐+PMP 钉死+预分类 | isla WT 配置 `riscv64_difftest_mem_excluded_pma.toml`（pma size→0x7FFF80000000；pmpcfg_n={bits=0x1f}/pmpaddr_n=全1 NAPOT-RWX，sys_pmp_count=16 为 IR let 故 const_primops 死配置）+ 根仓 pipeline.py 预分类（tests +9 共 44/44）；定向 c015/c030 假 fault 消失（92f+28o→1 成功带写事件）、5 条 @0x90000000 转成功、图外对照（0x6ffffffc/0x10000000/2^43 恰界/+0x100）全 AccessFault 边界精确；green 重跑 131 成功/2479 fault/107 图内假 fault → 128 gen=24 成功/104 fault/0（路径坍缩为 PMP 符号分支消除的预期）；fault32 复跑 9 失败→0（30/30：5 顶界+2 假 fault 转 GOODTRAP、2 低位错位预分类 skip），ok 回归 15/15 | [议题状态](../agents/memory_support_review/status.md)、[findings](../agents/findings.md)、证据 `/tmp/isla-memimpl-w14-20260927-065108/`；isla WT 收口 commit 59e2b5d（W2-W14，17 文件 +5682/−471）、根仓库 b11a6f6。④⑤ 真分歧上报不修；W15 候选：2^43 顶界以上放行非单调（2^43+1/2^44/2^47−ε 放行，2^43/2^43+0x100/2^47/2^63 fault），与 range_subset 环绕语义手算矛盾，需 IR 级定位，不影响 ≤2^43 与既有重放。（W15 勘误销案：探针误读，见下条。）
| 2026-09-27，56cc单目标FVFTYPE资源诊断 | j1×2worker、1800/1740/30，约697.15秒因资源策略终止：RSS/HWM125,275,944kB，supervisor记录外部TERM并收束顽固组、return143，make2；4801 Illegal＋3 nonenc局部终态、0 Retire，无JSON，5.43GB trace。52条资源采样覆盖23:41:01–23:45:16Z，起始约运行7分18秒，前段未采 | [官方记录](../agents/float_support_review/solve-fix-official.md)，stage `fvftype-j1-56cc-20260927-084800`。143为人为external_resource_stop，不当SMT错误或预算外限；全部PID已收束。手动PATH Python缺os.pidfd_open先安全拒绝，后核验supervisor身份再局部TERM；兼容修复与trace共享优化继续。 |
| 2026-09-27，solve退出清理修复 | 旧全局pkill改为当前timeout专属进程组收束；真实uutils顽固孙进程反例保留。10项真实进程测试通过，Astra独立复跑10/10（7.229秒）；508个原冻结文件含Rust同字节，两个既有脚本变化及新监督器/测试单列 | [清理证据](../isla/target/float-solve-evidence/solve-process-cleanup-20260927/README.md)，架构独审 `306ce57f…c849c`。只授权新j1运行入口，未改变IR/数值runtime；跨session逃逸不在合同内，旧j8信号原因不据此倒推。 |
| 2026-09-27，重放纯读证书漏项勘误 | 代码核实globals只收显式Register/Let，漏frame注入的current_exception/have_exception/throw_location；let赋值不产WriteReg，动态事件白名单也未补上。旧348147及新56cc decoder/encoder完整纯读判定不充分 | [独审修订](../agents/float_support_review/unified-backend-cpp-replay-independent-audit.md)。原数值/AST/ret/102post与8let/15aux匹配事实保留；完整双后端等价待修复及新证据，旧冻结PASS不改hash，按本勘误缩限。 |
| 2026-09-27，56cc首轮j8全77长批资源中断 | 1800/1740/30秒、8目标×2worker、完整trace，06:46:37启动；多向量进程各17–28GiB，交换空间满。停止后26自然完成、6信号退出（1项137、5项15）、8人为中断，其余未启动；只按本stage验证PID树停止，make.rc=-9，证据保留 | [官方记录](../agents/float_support_review/solve-fix-official.md)，stage `official-56cc-long-20260927-064348`。cgroup OOM kill为0，尚不归因为内核OOM；26项另做完整重放。检查全局退出清理并改为j1带内存监控续跑，不缩输入域。 |
| 2026-09-27，56cc官方D FMA代表全输出闭环 | 自然exit0、86.50秒；1096终态=840 Retire＋252 Illegal＋4 nonenc，1092 gen无抑制。全部汇编/trace守恒，新Isla/CPP 1096/1096完整AST/ret/102post与初始化匹配；独审重跑全部重汇编及trace、核2245文件绑定PASS | [完整双后端独审](../agents/float_support_review/unified-backend-cpp-replay-independent-audit.md)，证书 `db60facd…866b6`。仅该官方代表；同批V FMA外限124，全77与source branch未完成。 |
| 2026-09-27，56cc告警完整展开 | 普通/SYMBOLIC strict `--all-warnings --just-check`均exit0，无剩余suppression；普通24 Deprecated与v7日志相同，SYMBOLIC另有旧4 V部分匹配及新1 AMO value部分匹配 | [告警审计](../agents/float_support_review/tools/unified_backend_model/warning-audit.md)，证书 `e3f8db65…f33a5`。新AMO提示对应非法opcode保留MatchFailure，真实decoder matcher→value域已独审；不据编译检查声称无UB或官方运行全部通过。 |
| 2026-09-27，56cc定向与严格trace复验 | 9,583输入/27,455终态，87组严格PASS；scalar5413/15305、V3228/9396、BF942/2754；M9307/U138/S138分别记账。最小63、FD4/VPR48另通过，额外19输入及trace亦通过 | [覆盖集成索引](../isla/target/float-support-review/final-coverage/integration/p1-56cc69/strict-audit-index.json) `283b4acc…d5b52`，结果索引 `07f7e6ba…c790a`。绑定新56cc/各实际配置，新增见证的源码义务消费继续；不代表全部source branch闭合或官方77完成。 |
| 2026-09-27，内存一致性 W13 fault 分歧裁定（只读诊断） | 实测+源码（SoC.scala:335 memRange、Parameters.scala:568 SimMemSize=8190GB）证实 emu 有效 RAM=[0x80000000,0x80000000000) 8TB；探针 0x90000000..0x1000000000 放行、0x9/0x2ff/0x80000000000 fault。9 条 fault 失败裁定 5/2/2（修正 W12 报的 4/2/3）：5 条 @0x90000000=Isla 地图顶界与 emu 8TB 不对齐；2 条低地址=NEMU mcause6 vs emu mcause7 真分歧（difftest 内部不一致）；2 条图内=PMP 假 fault（符号 pmpcfg/pmpaddr 未关、sys_pmp_count=0 未折叠，--debug rf 证 119 fork 全在 pmp_control，green 全量 107/2479 同因，JSON 不输出 PMP 状态故重放不可复现） | [议题状态](../agents/memory_support_review/status.md)、[findings](../agents/findings.md)、证据 `/tmp/isla-memimpl-w13-20260927-053000/`；据此启动 W14（pma 对齐 8TB、PMP 钉死、pipeline 预分类）。真分歧上报不修：错位异常优先级 NEMU(6) vs emu(7)、Isla plat_enable_misaligned_access=false vs emu 支持错位。 |
| 2026-09-27，56cc的67 helper三方复验 | 83 smoke与17,586 full完整bits/五flags三方比较PASS；Astra重算全部结果并实际复跑CPP smoke/full、Isla smoke和native83，5负控检出；931构建源/166模型/125 Sail库/510 runtime来源绑定通过 | [三方报告](../agents/float_support_review/unified-backend-crosscheck.md)，独审 `7421e482…73ca6d`。CPP full 0.086秒，Isla含SAT/UNSAT证明61.939秒，不据此算速度倍率；仅67 helper与列定合同，不代表全typed接口或ISA77。 |
| 2026-09-27，56cc历史全量输入双后端回归 | 18,584/18,584 PASS（18,477 gen＋107负例），19片/4worker，204.427秒；完整AST/ret/102post、8let/15aux及逐例辅助态观察唯一性匹配；独审重核3,224文件绑定、两端全部ID，589文件最终索引零漂移 | [双后端独审](../agents/float_support_review/unified-backend-cpp-replay-independent-audit.md)；summary `cad2f88a…e7b0a`，独审 `0f2e324e…9d177`，IR `56cc69a4…9956ac`、FD `20851fdb…723d0`。历史50目标的全部seed新版本回归；不代表新官方77输出或源码分支闭合。 |
| 2026-09-27，56cc完整IR结构与精确region退役 | V完整IR结构PASS（`afa7d113…af687`），AMO完整IR结构PASS（`cd6090cf…d0d6`）：核同源931文件与7构建输出、真实guard闭包及四encdec入口；V消除纯判断分叉。单region退役授权PASS（`72e53ee2…c4fb`），旧d012→348147函数桥接成立，新valid_rd_mask为0 Jump | [架构记录](../agents/float_support_review/solve-fix-architecture.md)、[IR记录](../agents/float_support_review/solve-fix-ir-generation.md)。IR `56cc69a4…9956ac`；精确1条退役、余129项严格迁移及79配置最终独审通过（`0ab22029…72e8f`），新官方代表准备运行，不代表77完成或源码分支闭合。 |
| 2026-09-27，内存一致性 W12 pipeline.py 内存上下文重放 | `difftest-xiangshan/pipeline.py` +262/-34（`memory_plan()`/前导 sb store/0xA5 填充/post 逐字节检查+park/两遍 ELF 精确窗口/`--sample-mode`/build-summary），测试 +428（17 用例，修 4 个既有 mock subprocess.run vs Popen error），单测 34/34 绿（基线 10 过 4 error）；探针 0x8ffffff8 写读 GOODTRAP 2/2（256MB 上界成立；W13 修订：只证该地址可达，emu 实际有效 RAM 8TB）；端到端 green JSON 2610 条：成功路径 131 条→精确跳过 27 条 code-overlap（比静态 8KB 多保留 10 条）→104/104 GOODTRAP；fault 抽样 32 条 23 GOODTRAP、9 超时失败（Isla AccessFault vs emu 正常退休：4 条 ≥0x90000000、2 条低地址 0x9/0x2ff、3 条 DRAM 内；W13 修正分类为 5/2/2，见 W13 条目）；抽查 4 条汇编与 JSON 逐字节一致 | [议题状态](../agents/memory_support_review/status.md)、[计划](../agents/memory_support_review/plan-pipeline.md)、[findings](../agents/findings.md)、证据 `/tmp/isla-memimpl-w12-20260927-050541/`；改动仅限 pipeline.py/tests/README 三文件。9 条 fault 分歧 W13 已裁定 5/2/2（非管线缺陷）；mcause 断言、按平台地图过滤、多指令序列、MMIO 未做。 |
| 2026-09-27，内存一致性 W10（S1）pma_regions 配置地图 | 单测 6/6 GREEN（config 4+target 2）、`cargo test -p isla --lib` 117 过+1 预存红、isla-lib 单线程跳 3 预存 enum 崩后 250 全过、fmt 过；shell `t_pma_regions_config_error_hard_fails` PASS（`t_pma_regions_store_writes_in_config_ram` 180s 盒 SKIP，600s 证据覆盖）；三件套 3/3；zSTORE 1/12 预算、600s 盒三组：RED（旧二进制配置被忽略）逐项复现 W9 基线 2579/2554/25/19，GREEN（RAM-only 地图 [0x80000000,0x90000000)）2610/2479/131——131 写事件全落配置地图内、地图外成功写 6→0 转为 fault、max addr=0x8fffffff 边界精确，UNCONF（新二进制未配置）与基线逐项一致 | [议题状态](../agents/memory_support_review/status.md)、[计划](../agents/memory_support_review/plan-pma.md)、[findings](../agents/findings.md)、证据 `/tmp/isla-memimpl-w10-20260927-032747/`（RESULT.txt/judge.py/三组 JSON）；未配置不注入，IR 与模型零改动。success 25→131 归因（PMA 链 fork 减少 + MMIO 段转 PMA fault 路径）只记现象；S0 重放地图 DRAM [0x80000000,0x90000000) 与 difftest DEFAULT_EMU_RAM_SIZE=256MB 一致但为编译期宏，emu 构建覆盖未确认（W13 修订：该 emu 实际有效 RAM 8TB，256MB 宏不约束 emu）；跨层重叠组合未校验、rom 别名 write_idempotent=T 语义存疑。 |
| 2026-09-27，V4+AMO同源完整构建 | 全新离线构建PASS，931文件快照前后哈希一致；C++模拟器及IR `56cc69a4…9956ac` 生成，79历史接口和3个direct接口齐全 | [构建报告](../isla/target/float-solve-evidence/unified-backend-build/model-v4-amo-20260927/model-build.json) SHA `d6b825af…47259`；CPP `96d18cea…`、头 `f79d0009…`、模型库 `3dbc3b43…`、模拟器 `c2e3830d…`。只代表构建及接口检查；实际fullIR guard/异常接线与本版语义/求解门槛另验，旧348147证据不转记。 |
| 2026-09-27，V4纯判断与AMO格式组件独审 | 两组件限定PASS：V4旧60条SAT路径及新四SEW各一未知SAT、完整四Bool/状态差异UNSAT，错误返回负控拒绝；AMO非E/E完整bits32 441/721 SAT、7自由payload/raw i64正向结构关系、域扩张负控拒绝 | V4[独审](../isla/target/float-solve-evidence/fp-legality-20260927/independent-review/review.json) SHA `42f923e5…9c3fa`，AMO[独审](../isla/target/float-solve-evidence/amo-layout-20260927/independent-review/review.json) SHA `def63782…4ac63`。AMO简化sentinel只证明生成顺序，不冒充真实guard全部语义；条件放行合批生成，完整IR中真实guard/异常出口/正反向顺序仍待核，性能尚未通过。 |
| 2026-09-27，历史全部输入在统一双后端重新配对 | 18584/18584通过：18477 gen+83直接负例+24派生负例，19片、4个流水worker，端到端201.601秒；新Isla逐例观察唯一性及CPP完整AST/ret/102post匹配，8let+15aux实际核验 | [汇总](../isla/target/float-solve-evidence/unified-backend-cpp-replay/p1-348147-20260927/historical-full-paired/summary.json) SHA `4c5d1995…abcb5`；IR348147、FD20851、cpp-r03，初始化scoped证书 `e8ee1f7e…2bbbf`。历史1dcc输入逐项保留来源，非新官方77输出；whole77/source-branch仍false；[最终独审](../agents/float_support_review/unified-backend-cpp-replay-independent-audit.md) `7d84219a…d71ee` 通过，662文件[证据索引](../isla/target/float-solve-evidence/unified-backend-cpp-replay/p1-348147-20260927/evidence-index.json) SHA `679875a5…3bc42` 零漂移。 |
| 2026-09-27，统一IR348147定向与完整trace复验 | 9583/9583输入、27455终态通过；28个配置任务/87组，标量5413/15305、向量3228/9396、BF942/2754。三族每组按新25711 Jump目录核实际trace、初始化/R1、终态及来源桥接；最小63与FD4/VPR48另过 | [总严格索引](../isla/target/float-support-review/final-coverage/integration/p1-348147/strict-audit-index.json) SHA `92dfd023…2fffa`；[结果索引](../isla/target/float-support-review/final-coverage/integration/p1-348147/result-index.json) SHA `f10b7626…67587`；[direct](../isla/target/float-solve-evidence/direct-state-p1-348147/reports/summary.json) SHA `b0e9d977…f6d5`。三族源码arm/static证书未迁记，source_branch_closed=false；普通求解预算/全77另验。后续性能源码变化须另冻复验。 |
| 2026-09-27，统一模型完整Sail告警展开审计 | 冻结v7以补丁Sail运行普通/SYMBOLIC `--all-warnings --just-check`均exit0；普通24条均为既有显式effect注解弃用，SYMBOLIC另有4条已记录的V不完整match；未留suppressed项 | [告警审计](../agents/float_support_review/tools/unified_backend_model/warning-audit.md)、[展开证据](../isla/target/float-solve-evidence/unified-backend-model/20260927-warning-all/warning-expansion.json) SHA `66c50971…e304e2b1`。三份effect源与旧版本逐字相同；仅typecheck，未重复生成模型。C++现行编译旗标下无报告，其屏蔽诊断及未启用sanitizer边界另列，不推导无UB。 |
| 2026-09-27，统一模型67 helper三方独审 | 限定PASS：83 smoke与17,586完整语料的真实CPP/Isla结果位、五flags相同，独立native按NaN/ISA整数合同比较通过；独立CPP重跑逐字一致 | [完整报告](../agents/float_support_review/unified-backend-crosscheck.md)、[独审](../.tmp/unified-backend-crosscheck/independent-review/final-review.json) SHA `347cb58d…50f21`；[最终绑定](../.tmp/unified-backend-crosscheck/independent-review/manifest-binding-review.json) SHA `b006521d…14504`；核920模型源、166同源Sail、67真实Model方法、三静库及新IR348147。CPP执行0.064秒，Isla含SAT/差异UNSAT为47.140秒，不作速度比；首次CPP未加载JSON失败保留并已修。不代表全部输入、ISA或源码分支闭合。 |
| 2026-09-27，统一IR348147两个官方热点 | 两项均外限124，make2，全组未通过；同300/270/30秒、2目标×2线程、qfaufbv、全ITRACE，不采样或固定符号状态 | [代表批](../isla/target/float-solve-evidence/representatives-3481-20260927-041103/evidence/representatives-run.json)，目标FVVMATYPE/F_MADD_TYPE_D；严格79配置/130活跃region已迁移核对。继续分析真实trace，未启动新全77；1dcc的50完成/27超时保持历史。 |
| 2026-09-27，1dcc定向追加稳定索引v3 | 9583/9583结果、27455终态：标量5413/15305，向量3228/9396，BF16 942/2754；Machine9307、User138、Supervisor138；最小63与协议3另列 | [结果索引v3](../isla/target/float-support-review/final-coverage/integration/result-index-v3.json) SHA `cc93ea74…3bc89`，旧9152与9561索引保留。限定IR1dcc及列定配置/输入，`source_branch_closed=false`；不计新348147复验或全域77通过。 |
| 2026-09-27，统一C++完整模型恢复构建 | v7 920文件补全并逐项校验后，`cmake --build ... --target sail_riscv_sim --parallel 4` 自然exit0；生成CPP、共享模型/SoftFloat/runtime静库及完整模拟器均产出 | [构建记录](../agents/float_support_review/unified-backend-build.md)、[来源补件绑定](../isla/target/float-solve-evidence/unified-backend-build/model-p1-v6-20260927/cpp-source-v7-bind.json) SHA `d4a31e79…`；生成头 `45fd0f83…`、源 `3f2af389…`、模型库 `8cd6d91d…`、模拟器 `2251afe3…`。安装Sail未改，使用隔离补丁工具链；此为完整构建PASS，helper三方/初始化兼容/完整指令状态另验，原v6失败保留。 |
| 2026-09-27，统一IR348147共享helper完整数值语料 | Isla侧限定PASS：67 helper、17,586/17,586真实输出，普通体trace、SAT、单完成路径及结果位/五flags差异UNSAT；smoke83另过。完整执行47.140秒，runner构建18.725秒 | [工具/合同](../agents/float_support_review/tools/unified_backend_crosscheck/README.md)、[完整报告](../.tmp/unified-backend-crosscheck/isla-p1-v6-full/summary.json) SHA `ab021c7d…83f59c`；输入SHA `3a701790…912216`，冻结runtime与1dcc同版。独立SoftFloat oracle，NaN只屏蔽native payload，ISA无效整数饱和值完整比较；CPP尚待链接，状态为PASS_PROOF_ONLY，非三方或整指令PASS。 |
| 2026-09-27，统一完整模型IR生成及快照修复 | 新IR `348147f8…aac061` 实际生成exit0/388.687秒，79历史接口齐；两decoder的378 constructor顺序、四guard结构独审通过。C++首轮因快照遗漏SoftFloat平台源码FAIL，已修冻结规则并以v7补全，链接待验 | [生成记录](../isla/target/float-solve-evidence/unified-backend-build/model-p1-v6-20260927/ir-generation.json) SHA `46f9c877…`；[结构独审](../isla/target/float-solve-evidence/decoder-layout-negate/full-ir-348147-review/review.json) SHA `8d545f0d…c18ab`；[统一方案](../agents/float_support_review/unified-backend-plan.md)。v6 manifest `749c3c5b…` 保留，v7 `7e945fba…02093` 含920文件，两版Sail树相同。仅生成/结构门槛，不代表完整双后端数值或77项PASS。 |
| 2026-09-27，C++完整指令重放工具历史模型验证 | 历史concrete-match：102字段高半部样例、16项控制、选定50clause的72条实际gen通过；decoder架构写/隐藏CSR写/内存回调/Sail异常注入拒绝，5项协议故障检查通过 | [工具](../agents/float_support_review/tools/unified_backend_cpp_replay/README.md)、[证据索引](../.tmp/unified-backend-cpp-replay-20260927/evidence-index.json) SHA `7bc8f670…94c61e`；r04 runner `ef71b200…`，最终2进程2例和r03所选72例分版本记录。真实旧模型，非共享P1验证，非全量；同源模型/配置、aux证据与新IR绑定尚待完成，不计全77或完整CPP replay PASS。 |
| 2026-09-27，内存一致性 W9 excluded 判死区域 | 替换 W8 白名单后单测：RED 106 过/10 失败 → GREEN `cargo test -p isla --lib` 115 过 + 1 预存红、isla-lib 223 过（+预存 enum 崩）、fmt 过；1/12 预算、600s 盒两档：默认档复现 W8 基线逐项一致（2631 gen/2554 AccessFault/77 Retire/52 写事件落 MMIO），判死档（`region_type = "excluded"`）2579 gen（=2631−52 自洽）、写事件落 MMIO 52→0、写事件地址收缩进模型 RAM、2554 fault 不变（洞仍 trap）、成功+fault 仍并存；三件套 3/3 PASS | [议题状态](../agents/memory_support_review/status.md)、[findings](../agents/findings.md)、证据 `/tmp/isla-memimpl-w9-20260927-023425/`；`ISLA_RISCV_CONSTRAIN_ADDR_TO_REGIONS` 已被本轮删除。复跑命令所带 `ISLA_RISCV_BUILTIN_*/ASSUME_*` 为死配置（默认档与 W8 基线逐项一致佐证无效）。遗留：`# clint_enabled = true` 注释位于 `[[memory_regions]]` 之后（TOML 作用域陷阱）、判死使每次符号访存多一次 check_sat。 |
| 2026-09-27，共享浮点双后端P0隔离验证 | 限定P0 PASS：CPP31例、Isla26个Add完整bits/五flags、3非NaN f128完整位比较、NaN抽象相等及2未知入口单SAT路径；五native identity、C11及record37项ASan/UBSan检查通过 | [工具与完整命令](../agents/float_support_review/tools/unified_backend_p0/README.md)、[manifest](../isla/target/float-solve-evidence/unified-backend-p0/20260926T162859Z/manifest.json) SHA `d05ddcf5…f7b72`；Sail446fb477加patch`a19828d5…c4875`。真实共享Sail flags公式，独立SoftFloat原生flags；f64的f128链实际执行。原raw NaN→BV固定编码预期失败保留，Z3该域未指定，ISA canonical仍严格比较。未改安装工具链，不代表生产模型、完整190接口或77项通过。 |
| 2026-09-27，1dcc 全部完整目标输出重放 | 完成子集PASS：50目标18,477/18,477 gen的完整AST、返回值、102状态字段回放通过；107不可编码终态在原初态下译码拒绝且状态不变；Dead/sample/suppressed均0 | [汇总证据](../isla/target/float-solve-evidence/official-1dcc-20260927-002314/replay-aggregate-final.json) SHA `18fb2ee7…34795`，绑定本批manifest/strict audit与三波全部gen。18,076标准汇编重编码同word；401 LLVM拒绝逐case核为confirmed-illegal-operand，不计标准汇编通过。Python54/54、Rust10/10。`whole-run-complete=false`，其余27超时无JSON；不代表完整源码分支或独立CPP数值oracle通过。 |
| 2026-09-27，1dcc 全77官方求解及日志审计 | 全组未通过：50自然退出0、27外限124、0底层错误退出，make2；50项JSON/日志/完整trace终态守恒、branch edge对catalog全部有效，日志未匹配执行/SMT异常 | [新批记录](../agents/float_support_review/solve-fix-official.md)、[严格审计](../isla/target/float-solve-evidence/official-1dcc-20260927-002314/evidence/official-audit.json) SHA `ed4376e6…d99d1`；IR1dcc、manifest28fb、300/270/30秒、4目标×2线程、全trace。50项JSON共18584终态，其中12903退休；27超时均无最终JSON，不能合计为完成。全部输出重放及source branch闭合继续，不据运行器无异常认定语义PASS。 |
| 2026-09-27，c5→1dcc 实际 decoder 限定等价 | VFMACC VV、VFWMACC VF 两固定形状，四独立方向各120秒均自然退出0；完整typed AST/payload比较通过，VV正向315条外层路径/315对内层交集、反向270条外层路径/315对内层交集，VF双向各360条/360对 | [完整证据](../isla/target/float-solve-evidence/mapping-decoder-1dcc-20260927-lxm85ubv/final-proof.json) SHA `3fd93f28…d6b5e`；同Symtab克隆248函数闭包，使用实际R1/初始化/断言转换。计数按证据中的实际路径义务解释；仅两形状，不代表全decoder或全77。前次把两个方向合在各120秒内运行的timeout124原证据保留。 |
| 2026-09-27，1dcc 浮点定向与 helper/direct 回归 | 9152/9152 定向结果 PASS（标量5121、向量3105、BF16 926；26394台账终态）；277未知入口与列定数值helper组、FD direct 4/4、VPR 48调用 PASS | IR `1dcc8081…8180`、源码manifest `28fb65ee…a055e`；[定向结果索引](../isla/target/float-support-review/final-coverage/integration/result-index.json) SHA `f6e074b8…44878`、[helper](../isla/target/float-solve-evidence/helper-final-1dcc8081/reports/summary.json) SHA `8154da5f…d0e4`、[direct](../isla/target/float-solve-evidence/direct-state-final-1dcc8081/reports/summary.json) SHA `1f6124fd…d314`。定向900秒预算，默认/合法alternate域分列；source_branch_closed=false，77项官方完整求解与全部输出重放仍待完成。 |
| 2026-09-26，内存一致性 W8 区域约束语义分层 | 两档端到端（difftest_mem 配置、预算 1/12、600s、两档 RC=0）：默认档（无区域地址约束，地址全域自由）2631 gen、77 Retire（71 带写事件）、2554 AccessFault，写事件 MMIO 52 / sym_ram 内 15 / 模型 RAM 且 sym_ram 外 4，fault 路径无访存事件（trap 在访存前）；开关=开（`ISLA_RISCV_CONSTRAIN_ADDR_TO_REGIONS` 定向重放档）2579/25/2554/19 全 ∈ sym_ram，与 W7 基线逐项一致。单测：memory_model 31/31、`cargo test -p isla --lib` 114 过 + 1 预存红、isla-lib 230 过（未触碰）、fmt 过；3 个 RED→GREEN，W7 系列 10 个测试重排到开关=开档 | [议题状态](../agents/memory_support_review/status.md)、[findings](../agents/findings.md)、证据 `/tmp/isla-memimpl-w8-20260926-234713/`；isla-lib 零改动。受限：默认档 fault:success≈33:1（需更多成功路径可用定向档或采样偏置）；MMIO 符号写走成功路径（52 条 CLINT 区写事件，读写细化未做）；IR 固化 PMA 地图（[0x90000000,0x100000000) 按模型 PMA 是合法 RAM 不 trap）精确边界需重生成 IR。 |
| 2026-09-26，内存一致性 W7 显式区域联立 Unsat 修复 | 修复后单测：`cargo test -p isla --lib` 108 过 + 1 预存红、`-p isla-lib` 208 过 + 5 预存 enum 冲突、fmt 过；`configs/riscv64_difftest_mem.toml` 下 zSTORE 预算 1/12、500s rc=0 收敛：2579 路径、19 写事件全部 ∈ sym_ram（含边界）、data==post-memory 19/19 逐字节一致、pre=null（首触写）——定向模式闭环 PASS；zC_LD 预算 1/12、780s 内 3507 路径、108 事件（全部 ∈ sym_ram、pre=post=事件值、0 不一致）但 rc=124 不收敛，预算 1/9、330s 收敛 rc=0 但 0 事件，预算扫描 8→24 显示 fork 悬崖在 9↔10，"收敛且含事件"预算点 ≤780s 盒内不存在（受限如实） | [议题状态](../agents/memory_support_review/status.md)、[findings](../agents/findings.md)、证据 `/tmp/isla-memimpl-w7-1748/`（unsat_dump2..4 同构 600+ 份、user_output_backup）；根因为 PMA 首析取分支（ROM 钉死）与 sym_ram OR 链交集为空且矛盾路径死得太晚，修复语义见 findings。遗留：zC_LD 探索侧改进（读约束前移/采样偏向 sym_ram）、unsat dump Z3 命名与 isla `k!N` 撞名，均为后续议题。 |
| 2026-09-26，c5完整候选首轮77项诊断 | 77项均结束，41退出0、36外限124；41份JSON complete且suppressed=0，36项无最终JSON。日志终态40434 Retire/60961 Illegal/214不可编码，外限中的28854 Retire仍为局部结果 | [批次记录](../agents/float_support_review/solve-fix-official.md)，`official-c5cbb-20260926-204047`，300/270/30秒、4目标×2线程、全trace。该版本FmtVal有已确认的128位具体状态输出缺陷，全批仅诊断，不作语义PASS或与旧预算直接比较性能；修复后须新批。 |
| 2026-09-26，c5完整接口IR与MixedBits运行时局部复验 | 277未知、67helper、估算350+1618+420、旧12体39+24、legacy35全部通过；FD/VPR direct通过。MixedBits局部67测试与58对真实decoder结果差异UNSAT通过 | [helper证据](../agents/float_support_review/solve-fix-helpers.md)、[表示优化](../agents/float_support_review/solve-fix-mixed-bits.md)。IR c5cbb0bb… / primop6c6d5a42…；测试程序具体化兼容修复仅在外部副本。独审随后复现FmtVal的B129宽位输出错误，首轮77批降为诊断；这些helper/direct不经过FmtVal，不能据其通过推断输出序列化正确。 |
| 2026-09-26，P2冻结模型首轮真实回归 | IR d86655a4… strict生成退出0；FD完整状态/全符号flags、VPR48组direct、FADD.S/FLI.S红例转绿。相同165模型快照重建普通C++后端，V128两项SUCCESS、V256 CTest 2/2通过 | [FD状态](../agents/float_support_review/solve-fix-fd-state.md)、[VPR状态](../agents/float_support_review/solve-fix-vpr-state.md)、[C++证据](../agents/float_support_review/tools/bf16_lmul/README.md)。P2 source manifest128d59a…；完整277/helper/指令覆盖、77项、全量replay及source-arm仍待验收，尚未切主IR/config。 |
| 2026-09-26，P1新运行器三代表热点诊断 | F_UN_RM_FF_TYPE_S、VFUNARY1、FVVMATYPE均90秒外限124，无最终JSON；标量10条15秒SMT超时仍定位flags changed比较，两个向量项仅观察到Illegal/不可编码终态；全组未通过 | P1 IR f5141217…、当时新运行器、旧完整ITRACE渲染，90/80/15秒、2线程、3并发；[官方批实施记录](../agents/float_support_review/solve-fix-official.md)、[性能设计](../agents/float_support_review/solve-fix-performance.md)。P1尚未含后续纯lane/VPR修复；完整trace每项约38–723MB，不能与后续紧凑渲染直接比较性能。 |
| 2026-09-26，solve修复P1中间候选 | 严格生成IR f5141217…，79配置/132区域/22锚点通过；真实FD getter/setter、flags符号累计单路径及FADD.S旧红新绿通过。d012基线新增向量2526与三配置565条、BF16 898条定向结果通过 | [FD状态修复](../agents/float_support_review/solve-fix-fd-state.md)、[向量覆盖](../agents/float_support_review/solve-fix-vector-coverage.md)、[BF16覆盖](../agents/float_support_review/solve-fix-bf16-coverage.md)。P1未切正式IR；旧基线结果不转记后续lane优化，实际source-arm闭合与77项正式复跑待完成。 |
| 2026-09-26，内存一致性 W2-W6 实施（feat/memory-consistency） | worktree `isla/.worktrees/memory-consistency`（基于 f06371f，未提交）内：`cargo test -p isla --lib` 105 通过（仅预存失败为用户在途 `rv64_target_trait` 红测试）、`cargo test -p isla-lib` 241/241（跳过 5 个预存 Z3 全局 enum sort 冲突用例）、`cargo fmt --check` 通过；CLI 三件套（help/no_filter/c_mul）array/fresh 双档 PASS；零配置端到端闭环 PASS：默认 difftest 配置（零 memory_regions）+ 数组模型，zC_LD 300s 盒 149 条生成、14 条非空 memory-events，无预算 870s 799/799 物化、440 模型复用、435 读事件、0 超时，zLOAD 限流 1285 物化、504 读事件；JSON 判读 `c.ld x8,0xb0(x8)` 读地址/初值/终值吻合 | [议题状态](../agents/memory_support_review/status.md)、[findings](../agents/findings.md)、证据 `/tmp/isla-memimpl-w6-1532/`（zc_ld_tiny/zc_ld_zero/zload_limited）。受限如实：zC_LD/zC_SD 无预算在高载机器 600-1800s 不收敛（fork 爆炸，需预算落盘；超时路径 rc=1 但文件先写）；时间盒依赖 feature 构建；W7 显式 sym_ram 区域与模型 PMA/PMP 联立 Unsat 进行中（`/tmp/isla-memimpl-w6-1532/unsat_dump/`）；`ISLA_RISCV_BUILTIN_*`/`ISLA_RISCV_TEST_Z*_WIDTH` 为死配置。 |
| 2026-09-26，现d012非访存浮点官方与分支审计 | 77显式目标全部尝试：40退出0、36外限124、1 SMT退出1，全组未通过；新补/复跑433条定向状态记录全部PASS。11目标61条SMT超时，另1路径超时；41份JSON3474条均缺fcsr。确认96条FLI及四BF16向量clause的汇编文本问题 | [审计总表](../agents/float_support_review/solve-audit.md)、[77项执行表](../agents/float_support_review/solve-audit-batch.md)、[源码/日志合理性](../agents/float_support_review/solve-audit-log-semantics.md)。THREADS2、外限90s/路径80s/SMT15s，四隔离stage；版本/二进制/源码manifest独立复核。正常Illegal与超时分开；退出0和433定向PASS都不代表全部branch或全输入正确。 |
| 2026-09-26，最终C1类型复用与BF16修复 | V128最终IR d0123541生成退出0且与79配置同批切主；277未知SAT/单路径、67helper/估算/旧体/35legacy、24组1509状态样例覆盖77非访存clause、BF16 LMUL10及79/132/22配置检查全部PASS（列定范围），Astra独立复核 | [最终IR记录](../agents/float_support_review/ir-refresh.md)、[类型取舍](../agents/float_support_review/type-reuse-architecture.md)、[性能对照](../agents/float_support_review/type-reuse-performance.md)。A/B未交付；内部Bool/出口共享flags恢复未知门槛。完整make solve、全符号官方批次及10访存不宣称通过。同批切换后通用10/10、MRET与FCVT_S_BF16 smoke均退出0；参数见IR记录。 |
| 2026-09-26，类型复用首候选361980ea | strict生成退出0；类型32+36+3探针、BF16 LMUL10、77非访存clause的1509具体样例通过；未知f16门槛600秒退出124，仅17/90，f32/f64未跑，候选未获交付 | [实施记录](../agents/float_support_review/implementation.md#首个类型复用候选的未知输入性能门槛未通过暂停切换)、[类型架构](../agents/float_support_review/type-reuse-architecture.md)；正式IR仍c9e1bfe2，继续保持既有类型复用的flags表达式A/B。 |
| 2026-09-26，旧c9e1bfe2浮点官方77项续跑完成 | 39项底层退出0，37项外限124，F_UN_RM_FF_TYPE_S因5秒SMT查询超时底层退出1；全组未通过 | [续跑记录](../agents/float_support_review/official-continuation.md)、[77项摘要](../agents/float_support_review/tools/official_float/summary.md)；THREADS2、外限60s/路径50s/SMT5s。后半批共享主机CPU争用，不能直接比较性能；退出0不等于数值/flags语义PASS，也不转记后续类型复用新IR。 |
| 2026-09-26，浮点接续审查与 smtperf 修复 | BF16 VF e16,m8 真实编码在旧 c9e1bfe2 IR 触发断言，退出101（FAIL）；smtperf旧宏调用编译失败复现后修复，两种feature组合各4/4测试PASS；M09注释静态检查PASS | [接续实施记录](../agents/float_support_review/implementation.md#2026-09-26-接续实施与类型复用调整进行中)；BF16新源码尚待新IR动态绿灯；用户要求先审现有类型复用，不能宣布E完成。 |
| 2026-09-26，浮点 D 完整 V128 隔离候选 | Sail生成退出0，IR哈希`c9e1bfe2…`；删旧分发后67个helper、六估算体350+1618+420、旧12函数体39+24样例均先SAT后对完整结果位/五flags差异求UNSAT，277未知入口各一条路径；Astra独立复核，D固定候选门槛PASS | [完整D记录](../agents/float_support_review/d-run.md)、[实施记录](../agents/float_support_review/implementation.md)；早期仅抽样模型值及首次缓存路径错误生成退出2保留为历史；有限样例非全输入证明。正式IR及配置仍未切换，指令验收属E。 |
| 2026-09-26，浮点 E 正式源码/IR/配置同批切换 | 主Isla的旧分发已删，新V128 IR哈希`c9e1bfe2…`，79份严格配置通过官方脚本及全132region/22锚点检查；浮点通用单测10/10，旧20项迁移成35条独立SoftFloat样例35/35；主FCVT_S_BF16与MRET定向入口退出0 | [实施记录](../agents/float_support_review/implementation.md)、[旧测试迁移说明](../isla/test/softfloat_legacy/README.md)；主与外部候选91/91文件逐字节一致。普通make solve默认220项在60秒时间盒后退出137，只7项完成，不计全量PASS；全库Z3 enum单测在干净基线也FAIL。77非访存的部分子操作和RV32两Zfa已在隔离验证；10访存依赖独立内存分支，本任务未验收。 |
| 2026-09-26，浮点 E RV64 非访存首批全clause定向样例 | 三包clause集合47+20+10无重叠，恰覆盖77个RV64非访存clause；各至少一条真实编码→译码/反编码→成功退休，写回和状态差异UNSAT。标量50/50加FMINM/FMAXM18/18、其他向量22/22、BF16/ROD等34个去重样例通过 | [实施记录](../agents/float_support_review/implementation.md)、[标量证据](../agents/float_support_review/tools/e_scalar_cases/README.md)、[向量证据](../agents/float_support_review/tools/e_vector_cases/README.md)、[BF16/ROD证据](../agents/float_support_review/tools/e_nonmem/RESULTS.md)。限定具体子操作和配置，不能据clause名推全部enum/RM/SEW/VL；访存依赖独立内存分支，本任务未验收；全量make solve仍未通过。 |
| 2026-09-26，浮点官方非访存入口交接快照 | 独立副本与主浮点源码/IR/配置86文件逐字节一致；固定77项非访存名单前35项中，24项底层退出0，11项向量目标触发60秒外限（底层124、make2），后者无最终JSON；第36–44项运行中 | [逐项批次摘要](../agents/float_support_review/tools/official_float/summary.md)、[交接说明](../agents/float_support_review/handoff.md)；固定THREADS2、外限60s/求解50s/SMT5s、qfaufbv。退出0与Retire不能单独证明数值/flags正确；超时项不计PASS，其余未测。未触碰独立内存分支。 |
| 2026-09-26，RV32浮点非访存限定项隔离入口 | 完整RV32 IR中两项Zfa真实编码合法反译；FMVH_X_D、FMVP_D_X各两条可行路径的写回/五flags差异均UNSAT，隔离具体样例PASS | [实施记录](../agents/float_support_review/implementation.md)、[RV32测试入口](../sail-riscv/test/rv32_fp/run.sh)；四项Zcf为访存指令，本浮点任务不验收其内存执行；公共RV32 solve-state仍panic。 |
| 2026-09-26，当前联合Sail源码 BF16 真实指令复验 | 独立重建RV64 C++模拟器，BF16 WMA flags及NaN boxing在V256 CTest 2/2，显式V128配置两项均输出SUCCESS，退出0 | [实施记录](../agents/float_support_review/implementation.md)；Sail 0.20.1、Sail-RISC-V f8ce849加当前源码修改，外部构建留命令/日志/源码与产物哈希。仅两条C++指令测试通过，新Isla IR的BF16状态仍待E复验。 |
| 2026-09-26，浮点访存历史只读预检 | 当时快照确认10个访存clause含FLH/FSH、RV32公共入口panic，记录了当时内存分支的地址位宽疑点 | [历史审查](../agents/float_support_review/memory-integration.md)；该时点结论不描述内存分支现状。用户已将独立内存分支排除出本浮点任务，访存不计本任务PASS。 |
| 2026-09-26，浮点共享异常库隔离差分 | 算术/比较 3888/3888、转换/取整/BF16/ROD 4353/4353，SoftFloat预期下先SAT再差异UNSAT；受限符号 f32 Add/Sub/Div/FMA 各一条路径 | [实施记录](../agents/float_support_review/implementation.md)、[算术边界脚本](../agents/float_support_review/oracle/boundary_probe.py)、[转换边界脚本](../agents/float_support_review/oracle/conversion_boundary_probe.py)；固定快照、具体输入/RM为主，受限符号仅有限离散域，NaN原生payload和无效整数候选不比较；源码继续变化，当前联合构建待复验。 |
| 2026-09-26，f16 包装隔离 helper | 22/22原外部声明均有普通函数体；strict Sail、IR及C++绑定检查通过；SoftFloat完整结果位/五flags差分3042/3042，Astra独立重跑 | [实施记录](../agents/float_support_review/implementation.md)、[测试入口](../sail-riscv/test/symbolic_fp/check_f16_wrapper.sh)；839固定+2200 seeded random+3受限符号，一条完成路径且SAT→差异UNSAT。未知输入只测3个入口，正式67项、禁旧分发及指令状态仍待验。 |
| 2026-09-26，f32 包装隔离 helper | 23/23有普通函数体；算术/比较570、转换/取整/ROD/BF16 3734及Astra边界1178例完整位/五flags差异UNSAT，未知23入口单路径；Astra独立复核 | [实施记录](../agents/float_support_review/implementation.md)、[测试说明](../sail-riscv/test/symbolic_fp/f32_c_README.md)；ROD=6普通候选已先映RTZ，隔离IR哈希见记录；正式联合IR、禁旧分发和指令状态未测。 |
| 2026-09-26，f64 包装隔离 helper | 22/22有普通函数体；807个完整位/五flags样例及受限未知输入SAT→差异UNSAT、各一条路径，Astra独立重建复核 | [实施记录](../agents/float_support_review/implementation.md)、[测试说明](../sail-riscv/test/symbolic_fp/f64_README.md)；C++只查生成接线，未执行；正式IR、指令状态未测。 |
| 2026-09-26，浮点 B 最小调用链 | strict Sail/IR/C++ 结构检查与 Isla 实际执行通过；8组 f32 quiet Eq 对照 SoftFloat，受限未知输入 SAT→结果/flags 不同 UNSAT；未知 Eq/add 各一条路径；B 门槛 PASS | [实施记录及产物哈希](../agents/float_support_review/implementation.md)、[可重跑小模型](../sail-riscv/test/symbolic_fp/README.md)；Isla f4f8e45 加 A 修改，Sail-RISC-V f8ce849 加 B 修改，Sail 0.20.1。仅完整 Eq、独立 bits-only RNE 加法演示和 BF16 接口小式；正式加法 flags、其余 helper 和最终 IR 未通过。 |
| 2026-09-26，SoftFloat 独立参考工具 | 使用仓内 RISC-V specialization、after-rounding tininess 和 ROD 配置构建；7/7 组定向样例通过，涵盖算术、异常、ROD、BF16和边界 | [工具与复现命令](../agents/float_support_review/oracle/README.md)、[实施记录](../agents/float_support_review/implementation.md)；Sail-RISC-V/SoftFloat f8ce849，CMake 4.2.3、GCC 15.2.0，产物哈希见记录。仅证明 oracle 自检，不表示 Isla 或 Sail 新模型已差分通过。 |
| 2026-09-26，浮点 A 通用接口 | 先复现单独旧测试 SMT 未初始化失败，修后 `f32_add_basic` 1/1、通用测试 10/10、旧 softfloat 测试 21/21、浮点模块 31/31；Astra 复核旧 73 名保留、新 9 名及测试补项，A 门槛 PASS | [实施记录与命令](../agents/float_support_review/implementation.md)；Isla f4f8e45 加当前 float.rs/smt.rs 修改，具体文件哈希见记录。只覆盖通用原语，未生成新 IR，不代表旧专用 helper flags 或 B–E 通过。 |
| 2026-09-26，BF16 VF 活动元素累计 | 旧模型新增真实汇编测试 `vl=0` 失败 `FAILURE: 2`；修后新增 WMA flags 和既有 NaN boxing 两条 CTest 2/2 通过 | [实施记录](../agents/float_support_review/implementation.md)、[下方复现命令](#bf16-vf-定向测试命令)；Sail-RISC-V f8ce849 加 BF16 修复，Sail 0.20.1、Clang 22.1.8、RV64/VLEN256 C++ 模拟器。生成后共享异常源码又变化，当前联合源码和正式 V128 IR 待复验；不代表完整 BF16 数值或 Isla PASS。 |
| 2026-09-26，浮点计划与文档收尾核对 | 统一职责、参考来源、A–E 顺序、67/12/79/89 的范围及历史修订；名称集合、文档本地链接/锚点和空白检查无误。同日再复核D/E集成边界、RV32限定项、10个访存依赖、BF16早期接口门槛和agent写入边界 | [文档核对记录](../agents/float_support_review/documentation-review.md)、[现行计划](../agents/float_support_review/plan.md)；Isla f4f8e45、Sail-RISC-V f8ce849；仅改文档，未运行 Isla 功能测试，不新增浮点 PASS。 |
| 2026-09-26，浮点接口全量清单 | 73个通用primop、79个Sail/IR helper名称对照；ITE及支撑层静态核对；CLI Z3 4.16.0小式确认比较/min、打印与简单混合公式 | [参考总表](../agents/float_support_review/reference-list.md)、[原语检查命令](../agents/float_support_review/inventory-primops.md)、[支撑检查命令](../agents/float_support_review/inventory-support.md)；基线Isla f4f8e45/Sail-RISC-V f8ce849。新列ROD、BF16 flags及union ITE等问题，均未运行Isla动态复现，不作为完整浮点PASS。 |
| 2026-09-26，内存分支 f06371f 静态调查 | 确认初始内存接线、同址读写规则未接通、事件逆序及压缩访存未续执行 | [详细报告](../agents/memory_support_review/report.md)；远端版本已核实，未构建或运行该分支，不作为动态 PASS；0008fae 旧基线另行解释。 |
| 2026-09-26，浮点分层设计源码核对 | 确认已有通用ITE、具体FP输入缺口、Sail flags布局/类型别名差异及默认V256生成配置 | [细化方案](../agents/float_support_review/refactoring-plan.md)；仅静态核对，接口和算法示例未编译，不作为动态PASS。 |
| 2026-09-25，浮点ITE与边界审查 | 全量核对8文件diff，15处ITE调用均位于float.rs；区分原生FP、异常模型和ISA策略 | [全量清单](../agents/float_support_review/ite-boundary.md)；源码/标准文档审查，未动态验证或实施接口调整。 |
| 2026-09-25，浮点分支扩展复核 | 远端仍为1a1910e；补充Sub NX、NaN/invalid NX、整数转换结果与边界问题，核实RVV复用及测试缺口 | [详细报告](../agents/float_support_review/report.md)；只读源码推导，未构建或动态测试，不作为PASS。 |
| 2026-09-25，项目级文档重构 | 原 101 个 agent 文件留在原位；新规范链接与 Python 静态检查通过 | [实施与修正记录](../agents/agent_collaboration_rules/migration.md)；历史缺失目标和基准 binary 门槛单独记录。 |
| 2026-09-25，浮点分支静态审查 | 找到符号 rm、Eq/qNaN、FMA NV 三类问题 | [审查状态](../agents/float_support_review/status.md)；未在该分支重新构建或动态测试。 |
| 2026-09-25，V IR/workaround | 新 RV64 IR 哈希与 79 份严格配置绑定，67 个 region 坐标校验通过 | [验证状态](../agents/v_symbolic_ir_workarounds/status.md)；适用所记源码和 IR 哈希。 |
| 2026-09-23/25，V 去重性能 | 四类样本、三轮 A/B 与 helper 对照；未见明显性能退化 | [报告](../agents/v_symbolic_dedup_perf/report.md)、[原数据](../agents/v_symbolic_dedup_perf/results-final.json)；不能外推全量指令。 |
| 2026-09-23，依赖初始化 | `init.sh` 静态与隔离验证通过，脏子模块保留 | [提交批次状态](../agents/commit_workspace_audit/status.md)、[初始化状态](../agents/init_repositories/status.md)；现行行为仍需以脚本和工作树核对。 |
| 2026-09-19，XiangShan 草稿复现 | 三项 PoC 有历史运行；Issue 1 的限时超时不能证明永久挂死 | [冻结档案](../archives/xiangshan/2026-09-23-issue-reproduction/README.md)、[状态](../agents/vext_issue_draft_reproduction/status.md)。 |
| 2026-09-18，Isla→XiangShan 回放 | 历史差异测试及覆盖缺口已记录 | [专题验证记录](../isla/agents/validation/Vext-test-9-16-difftest-xiangshan/验证报告.md)；不代表新版本 DUT。 |
| 2026-09-17，Ara 合法配置复验 | 部分 bug 家族在合法配置复现，部分早期结论被修订 | [Ara 冻结档案](../archives/ara/2026-09-23-poc-batch/README.md)、[缺陷表](../agents/ara_poc_batch/bugs.md)；先看后续修订。 |
| 2026-07-30，VVTYPE 局部限制 | 当时 30 分钟目标内完成 21/21 mnemonic | [状态与运行参数](../agents/vvtype_balanced_local_limits/status.md)；绑定当时 IR 与限制配置。 |
| 2026-07-30，VVTYPE saturation | 定向语义与 qfaufbv 测试通过，性能差异仅为单轮信号 | [状态](../agents/vvtype_saturation_qfaufbv/status.md)。 |
| 2026-07-16，XiangShan VLEN128 smoke | 当时真实 NEMU DiffTest 小样本链路通过 | [专题状态](../agents/difftest_xiangshan_v/status.md)；reset-zero 模式不等同完整 Isla 状态重放。 |
| 2026-07-10，assembly-gen V 初始化 | 单测与集成、Spike 定向验证通过 | [状态](../agents/v-ext-init/status.md)；仅适用当时 assembly-gen 版本。 |
| 2026-04，zSTORE 路径爆炸 | PMA/PMP 原型、smoke 与语义核对分阶段进行 | [状态原文](../agents/zSTORE_path_explosion/status.md)、[审计](../agents/zSTORE_path_explosion/audit.md)；不同阶段的开关和配置不能混作一次验收。 |

其他议题的计划、状态和报告均保持在 [agents/](../agents/)；[代码发现](../agents/findings.md)保留全部发现与历史修订。新增结果应注明日期、源码/IR/配置版本、命令或产物、判定范围与限制，再更新 `specs/TODOs.md` 对应状态。

## BF16 VF 定向测试命令

构建目录在仓库外，以下用 `BF16_BUILD` 表示该目录；不依赖其本机绝对路径。CMake 配置使用 `-DCMAKE_BUILD_TYPE=Release -DENABLE_RISCV_TESTS=OFF -DFIRST_PARTY_TESTS=ON -DDOWNLOAD_GMP=OFF`。定向构建和运行命令：

```sh
cmake -S sail-riscv -B "$BF16_BUILD" -DCMAKE_BUILD_TYPE=Release -DENABLE_RISCV_TESTS=OFF -DFIRST_PARTY_TESTS=ON -DDOWNLOAD_GMP=OFF
cmake --build "$BF16_BUILD" --target build_rv64d_test_bf16_wma_flags.S sail_riscv_sim -j 8
ctest --test-dir "$BF16_BUILD" -R '^first_party_rv64d_test_bf16_(wma_flags|nan_boxing)\.S$' --output-on-failure
```

两条测试使用 `rv64d_v256_e64.json` 与 `test/first_party/src/no_override.json`；V256 配置、测试 ELF、模拟器的 SHA-256 依次为 `e28ac77273be6a31c544db6b196914dfb55b3b9fb72295ae7ef6cfc7b99dfc47`、`918863ec017c51732a294eddae17685929390d7f6af72f29dfcd054360ecedfa`、`aa493777b7c0362abc98f7a38d5008b0e3ff1970831e65eeaff9633b22182631`。修复前 CTest 退出 8 且新测试 `FAILURE: 2`；修复后 CTest 退出 0、2/2 通过。此结果只对应上述产物，后续源码和 V128 IR 需复验。

## 2026-10-29 初态 TOML 部分符号化（限定验证）

候选为 `feat/initial-state-toml-20261029` 的未提交补丁，基线09fe582；Isla89/isarch25通过，Brew Z3下isla-lib279通过、跳过三项enum checkpoint测试。未过滤全量受枚举sort重复声明错误阻塞，基线定向复现。make solve-MRET配置smoke退出0，4条初态满足mstatus[10:9]=3、x1=42、fcsr[7:5]=0；fmt与diff检查通过。无全指令/硬件验收。[状态、精确IR/配置/补丁哈希及日志](../agents/initial_state_config/status.md)。

2026-10-29初态配置8948cc4负面验证：x1="中"和pma_regions="?"均使release进程退出134；确证两项待修P2，不是功能PASS。[复现与日志](../agents/initial_state_config/review.md)。

2026-10-29复审修复ef882f0：isla串行90/90、Brew Z3核心279/279（跳三项enum）、isarch25/25；首次并行受既有SMT初始化时序失败，串行全过。两项release负例退出1带明确错误；make solve-MRET退出0、四条初态断言通过。已合入general；dirty组合未新增签收。[记录](../agents/initial_state_config/status.md)。

## 2026-10-29 ef882f0＋be1296b组合复审

基线7b7337b，隔离未提交候选解两冲突后：isla94、isarch25、核心267（明确跳三项enum）、集成20通过；默认七个make短入口和V256 MRET/VSETIVLI均退出0，显式FS1/VS0保持。float独立runner原构造器E0063构建失败，隔离补4行新配置字段后，五IR helper1615/state180/guard20通过。保留C_ADDI符号ret_val证据；不是完整重放或硬件PASS。[版本、命令、分层证据与报告](../agents/general_float_review_20261029/report.md)。未实际合入两分支。

### 2026-10-29 种子包有界抽检

候选目录 `.tmp/seed-handoff-20261029/`，`sha256sum -c SHA256SUMS` 退出 0。W19 调查 45 文件、35 非空、4124 条，详细生成状态及版本限制见包内 README 和 SURVEY。包内 pipeline、gcc 14.2.0、VLEN 128、XiangShan a13efc8775 的 emu 与匹配 NEMU 对 VSETIVLI smoke 和 STORE `sd x0, 0x640(x22)` 各 build 后 run，分别 1/1 success；二进制哈希及命令见包内 README。未验证整批及迁移，未做负对照；LOAD/STORE 抽查为指令与结果代理而非源码路径覆盖。

## 2026-10-29 实际合并最终31506ee

受测为general ef882f0＋float be1296b的最终隔离候选，正式feat/float-support经两个顺序merge与ret_val小修后1015文件逐字节一致。isla94/isarch25、fmt/diff通过；MRET4/C_ADDI1/VSETIVLI12/FLEQ_S16/FCVT_S_BF16 63五make入口均退出0，ret_val均无Sym，C_ADDI仍为具体ExecuteAs而非续执行完成。新增fixture先RED再GREEN。独立6.1-sol审阅无确证P1/P2。核心/数值runner复用此前同源码定向结果，全77/硬件/性能未测。[提交、备份与日志](../agents/general_float_merge_20261029/status.md)。

## 2026-10-29 分支术语统一验证

general cc7700b库90及model_concretization3通过；float-only99a28b0库65通过、明确跳过既有rv64_target_trait，独立runner cargo check通过；顺序合并目标75e7440库94及model_concretization3通过，fmt/diff通过。独立6.1-sol核对仅术语/测试名/文档变化，原修复保留；未重复数值/全指令/硬件验收。[版本、命令日志和工作树边界](../agents/terminology_concretization_20261029/status.md)。

## 2026-10-30 根float/memory版本更新

float bb9d271、memory1731207的gitlink/manifest/checkout/IR哈希逐项一致；在各自runner工作树运行init.sh --submodules-only退出0，提交后根/子模块干净。只作版本管理验证，未编译/重生IR/联合功能/硬件验收。[精确版本与原master检查边界](../agents/branch_merge_review/root-version-update-20261030.md)。

## 2026-10-30 float/memory根版本的JSON语义复审

float bb9d271、memory1731207及子模块独立构建后测试：五IR helper1615/state180/guard20通过；memory数组30通过，定向ld/sd/c.ld/AMO事件与内存自洽。新负例确认memory模型/IR两项语义错配（vd31/nf2误退休，vstart越界误Illegal）；float32条FLI文本GNU仅接受6且6条全部重汇编错码，LLVM拒绝。MRET两分支采样均4→1且退出0但JSON无partial；SC配置从具体true改符号恢复失败分支。FVFTYPE45秒外限124无JSON。未全指令/全源码控制流/硬件验收，不能签收目标全部达成。[命令、版本、报告与证据](../agents/json_semantic_review_20261030/status.md)。

## 2026-10-30 JSON语义复审修复与双工具链限定验收

根float90bb726、memory31ef3b9及精确子模块见[报告](../agents/json_semantic_fixes_20261030/report.md)。IR从对应干净模型完整重生；两memory负例转绿，FLI文本编码正确。GCC14.2/Clang22.1.8：132条浮点JSON共264比较与8条内存JSON共16比较全部通过；模型实际映射116条两套均通过。95/149项isarch、42项执行限制与浮点22步均通过。make-MRET两边退出0但summary如实partial，float-FLI_S退出0/32条finished。未强制触发终值查询超时，未验完整源码控制流/全77/全访存域/硬件；未push。旧报告的失败仅适用于旧版本，不覆盖这次结果。

## 2026-10-30 两subagent独立复审当前float/memory

根float90bb726：14个有界探针；新第一组112次双汇编通过，追加90次86通过／4次Clang非法BF16布局拒绝；默认算术40退休例全部未boxing→qNaN，定向boxed可达有限数。根memory31ef3b9：7个完整模型探针14条JSON／28次双汇编通过，但同址concrete快照与符号地址读值不一致，源x6漏导出导致pipeline前导修改payload数据；异常返回值仍Sym。未改实现／未验硬件；字段ModelEval超时仅静态缺口。[独立报告及证据](../agents/independent_topic_review_20261030/summary.md)。旧有限样本PASS保留适用范围，不外推全控制流。

## 2026-10-31 NaN-boxing显式分支恢复

根float1c7a354固定Isla80231ce9／模型9c339044。五IR全部保留等宽/boxing两Jump，普通严格检查退出0；浮点23步全部通过（1615helper/180state/20guard及结构检查）。同二进制/配置前后：FLEQ4→10条，四算术52→208条／退休40→160条，四种两源boxing组合各40退休例，有效boxing且有限数源0→40例。单次四算术耗时9.78→55.70秒，覆盖集合不同且无重复性能基准，不解释为纯性能比。GCC/Clang新见证416＋20项通过；根float make-FLEQ退出0/10条，两侧检查通过，初始化核对通过。memory未动；其他review问题保留。[证据与边界](../agents/nan_unbox_branch_restore_20261031/report.md)。

**浮点分支合并并行消融（2026-10-31，完成／限定域）**：五组逐项完整IR与AB/BA/AB三对。min/max 5.510→12.816秒、20→36见证；mask 7.65→11.17秒、27→54，归约4.17→5.21秒、12→24；显式分支补条件见证。flags算术ITE约52.288秒完成、if三次60秒超时；NaN规范化与饱和同样ITE完成/if超时，分类及宽域guard双臂超时。guard窄域小幅耗时/非法分区取舍，不算等覆盖加速。生产版本/干净状态保持、未实施回退；全格式/全部调用点未验。[汇总与建议](../agents/branch_ablation_20261031/report.md)。

**两小时消融核查更正（2026-11-01，续测中）**：分类769.93/1099.23秒、310/508条，两臂三次完整，if补齐十类；宽域guard132.69/133.68秒、81/108条均完整。发现未传SMT参数仍默认60秒，flags/NaN以partial退出而非外限；三项受影响实验现显式SMT7200秒重测，不沿用旧完成性建议。[核查](../agents/branch_ablation_20261031/budget-2h-audit-20261101.md)。

**浮点超时性能定位（2026-11-01，调查完成／未改生产）**：flags慢于包含f32/f64除法的changed可达性查询；NaN慢于isNaN(sqrt)查询。相同dump重放flags qfaufbv60秒unknown，qffp三次约3.71秒SAT；NaN37.74→约0.209秒。等价sqrt输入NaN/负非零条件在原query约0.108秒SAT，差异UNSAT。增量seed影响和完整Clause仍未验证，不以延长限时或合并分支替代性能处理。[报告](../agents/branch_ablation_20261031/solver-diagnosis/report.md)。

**Z3统一策略源码调查（2026-11-01，query验证完成／未接入）**：源码和probe确认Sail枚举阻断default的is-qffp分类；qffp直接调用提前浮点转换。统一simplify→dt2bv→fpa2bv→simplify→default通过25真实慢dump（flags9.3–16.8秒、NaN0.21–0.41秒）及10混合类型探针，2次C API带假设与模型原断言回读为true；完整Clause7200秒及seed接入未验证。[证据](../agents/branch_ablation_20261031/z3-strategy-source/report.md)。

**Z3上游贡献评估（2026-11-01，准备完成／未发布）**：六行独立例子仅增加无关枚举即可使default变慢；三次无枚举中位0.109秒，含枚举15.826秒（6.613–16.028），dt2bv后0.209秒。master相关浮点probe代码限制仍在，未编译master；建议提出受限混合类型分发性能议题和回归，而非正确性bug或无条件放宽datatype。未向社区发消息。[评估与草稿](../agents/branch_ablation_20261031/z3-upstream-assessment/report.md)。

**Z3 default浮点/枚举源码修复（2026-11-01，完成／限定验证）**：独立上游8fbb275分支fix/default-fp-enum-11500中新增受限mixed分发dt2bv→qffp，保留数组/ADT/proof等原路径。红例资源预算unknown→SAT；fpa及4组既有测试PASS、41query预期一致，2真实query假设双侧模型回读为true。未替换生产Z3/Isla、未PR；全Clause7200秒未验。[报告与补丁](../agents/branch_ablation_20261031/z3-upstream-fix/report.md)。

**Z3补丁独立审查完成（2026-11-01，修订后复验通过）**：两位独立reviewer发现大枚举性能/预算P2及域测试不足，已增加4096模型成本护栏并增强自由枚举域UNSAT回归；原反例关闭。56/110双侧功能执行、成本边界、假设/增量/资源恢复及原模型断言检查未发现正确性变化；最终源码hash冻结。不能保证所有输入都更快或同预算UNKNOWN不变，全Clause未验。[独审汇总](../agents/branch_ablation_20261031/z3-upstream-fix/independent-review/summary.md)。

**大枚举当前default/qffp对比（2026-11-01）**：同guarded二进制/输入/CPU五对交替70运行均SAT；成本超过4096的四大例default约44–58ms、qffp42–55ms，差2–3ms；护栏内轻量FP约20ms转换开销仍存在。非全Clause，不外推普遍速度比。[原始结果与规模](../agents/branch_ablation_20261031/z3-upstream-fix/large-enum-qffp/report.md)。

**Z3枚举策略恢复（2026-11-01，完成）**：按用户要求去掉4096模型成本护栏，恢复受限FP＋枚举dt2bv→qffp；保留增强域UNSAT测试。构建与五组回归通过；恢复后大例default约0.49/0.90秒、qffp约0.045秒，之前几毫秒差异仅适用护栏版。性能P2按用户选择保留开销，生产未改。[记录](../agents/branch_ablation_20261031/z3-upstream-fix/restored-no-cost-limit/report.md)。

## 2026-11-01：Z3两个最小替代修复的独审与发布

上游base8fbb275，自报5.3.4；A953e433（PR11505）修订版90/90独立query、18API/64模型原断言true及fpa通过，独审42次CLI/14模型回读通过，关闭初版lambda导致UNSAT→UNKNOWN类型回退。Bae64857（PR11506）独审27query与base/显式SMT对照、三API模式及fpa通过；作者18API/64模型回读通过，90query中88在60秒内符合预期，两个flags的UNKNOWN/canceled正按7200秒query预算续测，不宣称全通过或完整Clause通过。两PR及issue11500评论已回读，生产组件未改。[版本、报告、原始证据](../agents/branch_ablation_20261031/z3-alternative-prs/status.md)。

Z3 B续测更正：ae64857的flags-dump-7/11在显式7200000ms SMT、7210s外限下退出0且SAT，耗时395.04/436.12秒；结合此前88项，90项均取得预期答案（混合预算，非全项60秒PASS）。初期共享CPU107，约6分钟后分到106/107，时间不用于受控性能比较；完整Clause仍未验。[汇总](../agents/branch_ablation_20261031/z3-alternative-prs/B/combined-summary.json)。

## 五重复交叉实验完成（2026-11-01）

最终A953e433与Bae64857，8个相同workload，各版本5次，AB/BA/AB/BA/AB，固定每组CPU，80/80均SAT且退出0，输入和二进制哈希核对一致。无预热，SMT7200秒/外限7210秒；机器共享，独立query而非完整Clause。

墙钟中位秒A/B：NaN0.1456/0.2356、flags6.4469/15.4842、最小例0.3525/0.2135、枚举6×256为0.1636/0.1198、512×256为0.5946/0.0676、1024×256为1.2632/0.0552、flags-7为6.3014/41.4227、flags-11为1.8329/119.0785。四个真实query均A更快；最小及三枚举规模query均B更快。不能外推全workload；短例进程启动/共享负载影响明显，B慢例波动较大（flags-7为41.29–234.50秒、flags-11为85.70–241.24秒）。原计时pilot因wait(timeout)轮询尾延迟废弃，正式80次全部从头重跑，未复用pilot数据。

[全部五次数据与原始证据](../agents/branch_ablation_20261031/z3-alternative-prs/comparison-five/report.md)。

**六成员枚举变量规模复测完成（2026-11-01）**：A953e433/Bae64857，64/256/512/1024变量，AB/BA/AB/BA/AB各5次，共40/40均SAT、退出0。墙钟中位毫秒A/B：39.20/29.71、63.34/47.29、70.09/45.64、91.69/52.29，A额外9.49/16.05/24.45/39.40ms。256输入与旧测试字节一致；每变量仅约束不等于C0，另有独立fp.isNaN(x)，不含真实浮点运算耦合；短时进程墙钟含启动/解析，机器共享，不能从跨规格非单调耗时推导算法下降。未改生产/PR。[五次原始数据与来源](../agents/branch_ablation_20261031/z3-alternative-prs/enum-six-five/report.md)。

**Z3 fork主线选择A与数据共享（2026-11-01，完成）**：msuadOf/z3默认main已指向953e433；独立证据分支2dec1be8公开120次数据/12输入/哈希与便携复现脚本（40次smoke通过）。issue11500评论6553829092包含逐次结果、命令及内容，远端回读一致；未替换生产Z3。[交付记录](../agents/branch_ablation_20261031/z3-alternative-prs/status.md)。

**Z3 fork二进制Actions（2026-11-01，已启用／首次云端构建待完成）**：main32f4df28，五平台native构建/fpa/解压smoke及GitHub Release/SHA256，无外部secret；本机Linux打包与actionlint通过。首轮[Actions41279354596](https://github.com/msuadOf/z3/actions/runs/41279354596)由push触发，尚未宣称发布成功，未替换生产Z3。[状态与验证]( ../agents/branch_ablation_20261031/z3-alternative-prs/fork-actions/status.md )。

**Z3 fork Actions首轮修复（2026-11-01，修订后云端构建中）**：首轮Make目标z3不存在失败，5292580e5改用shell；全新Make目标核对及当前提交本地重编译/fpa/迁移打包通过。最新[运行41279556474](https://github.com/msuadOf/z3/actions/runs/41279556474)进行中，release仍待矩阵成功。[原失败与修订证据](../agents/branch_ablation_20261031/z3-alternative-prs/fork-actions/status.md)。

**Isla使用fork Z3 A（2026-11-01，隔离加载与限定验证通过）**：实际Release5292580e5校验和通过；float isarch副本显式换新libz3，ldd -r/版本验证通过，default种子能力校验未阻塞，FLEQ_S 4.08秒/10条/finished/无错误超时。MRET新旧均partial/unfinished=1，未作完整验收。使用A须新库＋--tastic default；尚未正式重链接/修改生产或分支。[证据]( ../agents/branch_ablation_20261031/z3-alternative-prs/isla-integration/status.md )。

**Isla CLI默认default、Make具体策略（2026-11-01，已修改／限定验证）**：float缺省Default并支持qffp；memory已有default不重复改；两条源码与runner快照Make的ALL显式qfaufbv、非访存浮点显式qffp，无新增报错、保留覆盖。TDD2/2、4×347目标dry-run及新Z3下CLI不传参数/Make qffp两次FLEQ_S均10条finished。未提交/推送/更新gitlink，未全Clause回归。[修改与证据](../agents/isla_tactic_defaults_20261101/status.md)。

**采用维护者Z3方案（2026-11-02，已切换fork main／新版CI待完成）**：maind5aa015a2正常合入PR11506 head6ef1c356（上游已MERGED），移除全局A，改为扩展原probe并在qffp内dt2bv；四solver/test文件与PR精确一致，保留发布CI。fpa/18API/64模型断言及Isla default/qffp两次FLEQ_S各10条finished通过；不外推旧性能数据，旧Release仍为A。[版本/验证/CI](../agents/z3_maintainer_route_20261102/status.md)。

**官方最新Z3编译（2026-11-02，完成／限定验证通过）**：干净官方master1fd1d3613（#11506），Release shell/libz3/test-z3构建安装至.tmp/z3-official-20261102/install；版本含官方SHA。fpa、两个default原查询（flags-11 8.33秒SAT）、18API/64原断言模型回读及Isla隔离default FLEQ_S10条finished通过；未全Clause或切换生产/系统库。[版本与使用目录](../agents/z3_official_build_20261102/status.md)。

**Isla正式切到官方Z3（2026-11-02，完成／限定验证）**：用户前缀~/.local/opt/z3-official-1fd1d3613，根/float/memory Make显式链接及RPATH、Release真实重编译，四处程序版本均官方1fd1d3613；根Debug亦切换。6次浮点/定向访存smoke全finished、无错误超时，SMT初始化2/2通过。保留旧系统库/在途源码/既有输出，未提交/推送/更新gitlink，未全Clause回归。[证据与边界](../agents/isla_official_z3_switch_20261102/status.md)。


**浮点 review 三项集成（2026-11-02，限定验证／覆盖仍部分）**：真实BF16两批与压缩例13条JSON、78项GCC/Clang检查符合预期，保留Illegal路径及三种表示；ExecuteAs红绿例x8由7修为1027。数据条件6次Clause/40条JSON均finished，补左源sNaN/qNaN及估算正常/次正规活动lane；右源独立及BF16/多lane等义务未闭合。统计尾段快照红绿回归通过，collector11/11＋三表示5/5＋API1/1＋统计1/1；根与runner-float源码同步、正式Release构建及真实make solve smoke通过。独立复审P2关闭。未提交/推送/gitlink更新。[状态与全部证据](../agents/float_review_completion_20261102/status.md)。


**显式语义分支恢复（2026-11-02，限定验证通过）**：模型7f3f50d/fd71c9a按FD/V分类恢复特殊值、十分类、两个mask循环及三guard；GPT-6.1 Sol独立源码与四配置IR签收无阻断。普通strict重跑、四完整SYMBOLIC、五IR24步回归、真实make-FMINM_S（12条）及GCC/Clang72项检查通过；Isla f152290固定IR与永久CFG回归。七Clause组合验证四项PASS、三项后台继续，flags/sat未结束不恢复；非全Clause/非全部同构条件验收。首轮ordinary包装缓存目录失败按版本保留。[证据](../agents/explicit_branch_restore_20261102/status.md)。


## 2026-11-02 最终后台验证结果

七项新组合Clause全部退出0、finished、无错误或超时。FVVTYPE 3121.758秒（329条），VFUNARY1 1880.107秒（520条），RFVVTYPE 290.252秒（184条），其余四项15.471–150.914秒；均低于完整Clause7200秒预算。以validation/report.md和summary.json的最终记录为准，旧“运行中”记录仅适用于提交时快照。

单变量消融84/84已结束。flags算术和转换饱和的显式分支B各三次均触及7200秒外限，故不符合本轮恢复条件，保留ITE；不能写成这些情况不需要控制流或覆盖已经完整。其他格式/循环、右源独立NaN、BF16融合及多lane异常等仍有覆盖验证义务。


**剩余特殊值控制流（2026-11-02，定向验收通过／最终同步中）**：模型四类提交350a072/f263774/eb17b05/a9fd947，四配置严格生成与普通检查通过，Sol源码/实际CFG/动态结果独审通过。56项定向完整Clause全部退出0、156条JSON、3518断言通过；固定域及vl≤2，不宣称全域完整覆盖。flags超时主要为SMT累计成本，旧sat另有不活动lane先计算造成额外分叉；新活动gate已纠正，overflow显式化须另行复测。详见[状态](../agents/special_control_restore_20261102/status.md)。


## 2026-11-02：独立源NaN与活动lane分支

模型四分类提交350a072/f263774/eb17b05/a9fd947，Isla对应IR提交99a83bb9；四配置严格生成、普通严格检查、五IR25步回归通过。独立GPT-6.1 Sol源码、实际CFG、56项定向结果复核通过。156条JSON、3518断言、正式make solve及GCC/Clang60项编码检查通过。固定域与vl≤2，不代表全域完整覆盖。

flags超时主要为昂贵浮点异常约束导致多次SMT求解变慢；旧饱和实验对不活动lane提前计算，导致额外分叉，新的活动gate已纠正。饱和overflow显式化仍需重新预算实验；flags changed及其余特殊异常分界未全部恢复。见[本轮状态](../agents/special_control_restore_20261102/status.md)和[超时定位](../agents/explicit_branch_timeout_diagnosis_20261102/report.md)。未推送。


## 2026-11-02：flags/sat超时完整归因确认

六臂冻结B的qffp/default/smt完整Clause对照均7200s外限exit124，无完整JSON；CPU约99.5–99.7%，更换这两策略未使本轮负载完成。插桩主路径2h账：flags结构上界332、创建256、执行返回150/收集返回149、排队106+collector中1；sat上界1033、创建435、执行返回199/收集返回198、排队236+collector中1。主树/编码辅助树/JSON分别计数。

flags已完成SMT查询约94.5%时间在collector，最长单次1038.658s SAT；sat最长4.819s、16951次已返回查询累积，兼旧8lane溢出组合。两项已返回check无UNKNOWN，外限截断时各一条刚开始的pending。旧源只加活动gate、保留overflow-if，同seed17三次57–64秒完整finished，确认不活动lane过早转换是重要原因。flags干净同具体FDIV_S编码诊断：原路径约束36.50秒，隔离后0.04–0.05秒，同机器码；不能据此直接删除生产约束。

独立review发现并修正计数混合、旧探针残留同核竞争、check边界误归属；先前240/455秒性能值撤回为受干扰诊断。未微观定位原17分钟query为何跨轮变动，不宣称tactic普遍无影响或会话历史bug。生产源码/模型/策略未改。完整证据见[确认报告](../agents/explicit_branch_timeout_diagnosis_20261102/confirmation-report.md)。


## 2026-11-02：编码候选约束分离与活动 lane 饱和分支（完成／限定验收）

Isla `cf1aa14`、模型 `6202e23`：辅助编码仅保留指令字段原断言，所有候选仍在完整执行约束下验证；恢复活动 lane 内 f16→i16 overflow 显式分支。独立 GPT-6.1 Sol 源码、四配置 IR、实际 JSON 和官方库 Rust 回归签收通过。

完整旧显式 flags B / 当前正式浮点算术 / 新 VFUNARY0 分别 2626.07 / 1127.51 / 22.33 秒 finished，均 T1/qffp/seed17、Clause 与单次 SMT 各 7200 秒，原配置未缩域；错误及 partial 均零。56 项定向、126 项双工具链、15 项官方库 Rust 回归及真实 Make 入口通过。两版各 1258 条实际见证的指令、编码、完整前后态、返回值多重集合相同；不推断全域覆盖或严格加速比。

五 IR/四配置严格生成和 25 步回归通过；flags changed 与其他未验窄转换仍维持现实现。既有枚举同 Context 重放单测失败单列，不计入通过数。旧 eager lane 饱和 B 初版诊断7200.20秒外限exit124、无完整JSON，不替代新模型验收。根 float 更新组件与证据，本轮未推送。详见[本轮状态](../agents/encoding_constraint_isolation_20261102/status.md)。

## 2026-11-02：Sail-RISC-V／Isla 内存协同接纳审阅

受审模型c70482a7／Islabdd047bc；使用已有Release及官方Z3 1fd1d3613，未重新构建。9主探针退出0、16JSON：8finished/1partial；concrete初态与数组分离、sd x6初值漏导出两个P1及异常返回值Sym已重现，不能记为整体验收PASS。segment越界、vstart最大/零、SC响应两路、压缩访存的限定行为符合预期；四配置各159模型文件、5IR路径和配置哈希匹配，79预算/130region/22锚点核对通过。自由地址store另行debug复跑确认vmem_utils.sail:224 SymbolicLength并正确标partial。三次初始VS=Off配置被译码拒绝的日志保留，显式VS使能后用新目录复验。未运行硬件、全量回归或更新IR；[命令、哈希、反例及接纳意见](../agents/coordinated_memory_review_20261102/report.md)。

本轮追加4次隔离IR后态断言：VLRETYPE/VSRETYPE固定vstart全1，原helper函数体逐字保留；两次最终等于0被断言过滤、两次最终仍全1通过且退休无访存。确认模型早退漏清零（P2）；不把退出0或summary.finished解释为零值性质PASS，生产IR未改。[插桩入口](../agents/coordinated_memory_review_20261102/probe_vstart_post.py)。


## 2026-11-02 浮点遗留项源码冻结与历史超时口径修订

新模型8ad5e8e与Isla42000be已完成独立Sol源码签收，枚举完整库280/280及独审SMT29/29；新IR/完整Clause/动态验收进行中，不计整组PASS。[本轮状态](../agents/float_review_closure_20261102/status.md)。

复核上一轮冻结程序abce451a的构建元数据、构建警告和动态符号，确认其未启用smt-thread-interrupt。旧实验的7200秒**整Clause外限有效**，但传入--smt-timeout 7200s在该默认feature程序中未执行单次SMT看门狗。因此旧结果不能支持“单次SMT限时已生效”的声明；原命令与实际输出保留，不静默改写。本轮正式程序明确启用该feature，并另核实际中断路径。[审计](../agents/float_review_closure_20261102/review/enum/old-binary-timeout-audit.json)。

## 2026-11-02：内存协同F1–F5修复及实施后Sol独审

受测模型c70482a7+dirty补丁27395dea，Islabdd047bc+本轮未提交修复；最终Release SHA ed4685e0、exec SHA2046fb3d，官方Z3链接与源码哈希见final-build-inputs.json。正式make build-isarch通过，最终Isla lib163/163、格式/diff核对通过。完整IR12组19JSON/65断言全部通过，11组finished、1组既存store SymbolicLength partial；vstart早退后态8/8通过。消费端Python80/80、文本GCC/Clang38/38（最终文本/编码多重集一致）；正式make C_MUL exit0且finished。MRET另4gen/1Poison未完成，正确partial，不作全路径PASS。

普通/SYMBOLIC严格模型检查、四配置生成及5IR安装通过，636条源文件哈希、配置、dirty源码补丁与IR哈希一致；79预算/130region/22锚点核对通过。独立Sol审阅未参与实现，关闭四个汇编/编码错误诊断出口并复审；用最终二进制及生产IR独立执行AMO concrete符号地址、sd x6重放两组探针均finished，无未关闭P1/P2。本轮范围限定接纳，未做完整指令覆盖或硬件验收、未提交/移动分支或gitlink。[完整命令、失败历史与验证](../agents/coordinated_memory_fixes_20261102/report.md)、[独审](../agents/coordinated_memory_fixes_20261102/independent-review/report.md)。


## 2026-11-03：0008fae共同参照与浮点纯数据分支精简（源码签收）

模型 `e9d69d2` 仅core异常文件+16/-74，恢复18处纯flags/ROD jam数据表达式，删除六处冗余mask调用及helper；数值公式、特殊值/非法原因/finite/valid/饱和/changed状态写回保留。两个GPT-6.1 Sol分别从214 Git对象重建和核查局部等价，源码签收通过。此结论不包括新IR、动态或性能；各项重新验证中。Isla以0008fae为共同参照，模型另记独立版本，避免跨仓对比SHA。见[候选独审](../agents/float_review_closure_20261102/baseline-0008fae/control-candidate-review.md)及[当前状态](../agents/float_review_closure_20261102/status.md)。

## 2026-11-03：Sv39 全符号页表预算实证

指定现成 memory-consistency isarch（精确SHA256见实验manifest）与 rv64d.ir（c0e4661a73888c56438a6f76059370667d141a026502d0511291586067bd31c0），LD 0x0000b103、VA=0x20000000、SUM=1。Bare/Identity单线程各1成功、finished，墙钟1.166/1.668秒；全符号60秒exit124，返回415条：76成功、291页故障、48访问故障；8564次已完成Z3检查累计26.629秒，最长0.01302秒。16线程补充3181条仍超时；两份实际原始数组模型逐字节和独立Sv39检查2/2 PASS。全符号总数/过滤数未知，未宣称全量或硬件PASS。完整报告、配置、命令和原始数据位于`.worktree/mmu-symbolic-experiment/`；[状态](../agents/mmu_symbolic_experiment/status.md)。


2026-11-03 e9d69d2新IR定向验收：flags五逻辑IR300/300、转换819helper+282scalar+183vector、异常/ROD/BF16315/315已新跑并获GPT-6.1 Sol限定签收。以actual机器字/初态分别用Fraction和SoftFloat独立重算；冻结inputs eb830e77、V128 IR661fd6e4、isarch acda0dce。direct helper/转换runner与正式isarch/qffp口径分开，定向输入不代完整Clause或全域覆盖。首次转换在fixture前因复制路径ROOT层数失败、未执行fixture；修正路径重新冻结并独审attempt2，原失败保留。[新批独审](../agents/float_review_closure_20261102/review/acceptance/modele9-results-review.md)。


2026-11-03 float最终收敛限定验收完成：模型0f7b8fbc/Isla591693d，77纯data选择回退、OPEN冻结延期memory。Sol已签新strict/IR/104错误变异/安装26步/300状态/819+282+183转换/315异常/双工具链与Make/两完整域入口，最终限定签收无阻断；不声称全77预算或全域覆盖。组件已安全推送回读一致，根float封存接续。见[交付报告](../agents/float_review_closure_20261102/final-report.md)。


2026-11-03 float最终交付发布完成：根float0665526d7e14a207eb9928e282e627584b5635fe固定模型0f7b8fbc/Isla591693d；三远程分支均已非强推并逐SHA回读一致，float与两子模块工作树clean。GPT-6.1 Sol已签实际源码/IR/限定回归及2173路径最终根提交（新生产改动只在子模块；根含审查证据），OPEN冻结延期memory，memory未改未合。最终后发布收据见agents/float_review_closure_20261102/publication/post-publication.json，本轮不为自引用另加root commit。


2026-11-03 float0665526d→memory31ef3b9隔离merge-tree预检：根9、Isla15、模型19配置冲突；memory原2888字节dirty补丁叠加后Isla新增README至16。独立Sol确认2处模型get_start_element返回nat但调用match Ok/Err，属于自动文本合并后的静态合同不兼容。原六仓HEAD和dirty哈希前后一致。本轮未构建/生成IR/跑语义验收，不记PASS；[证据与步骤](../agents/float_memory_merge_20261103/preflight-report.md)。


2026-11-04 float→memory限定合流发布完成：根memory `29aa4765`、Isla `4d085b14`、模型 `bf861b3e`，三正式远程逐SHA回读及原目标三仓clean均获Sol独立终核。Rust610/665、永久26/104负控、315/300、union9、nat8/helper4、ExecuteAs、定向Make和双工具链通过；原F1/原域访存partial/全域无退化未证与OPEN继续单列，未扩功能。完整索引见 `agents/float_memory_merge_20261103/status.md`。


2026-11-04 全量生成启动快照（非整组PASS）：memory29aa4765/Isla4d085/modelbf861，实际已审bin3e44，ALL347×三个RV64配置=1041任务，12×T1，Clause/路径/SMT各7200秒。79qffp/268qfaufbv按配置，默认128别名/RV32 solve不支持实证登记；资产冻结、FIFO压缩日志，输出`.worktree/runner-memory/output/full-generation-20261104/`。进度见`agents/full_generation_20261104/status.md`。


2026-11-04 用户要求全量生成仅v128并提并发：旧controller3047417和12个在途任务已定向优雅退出，原122项v128成果哈希不变；新controller367606仅重跑剩余225项，40并发×T2，无taskset/128CPU，预算均7200s。新入口`.worktree/runner-memory/output/full-generation-v128-fast-20261104/`，每15秒更新progress。见`agents/full_generation_20261104/status.md`；启动不代表任务成功。


2026-11-04 全量生成按最新用户指定改为仅v128、10worker×THREADS32、无taskset。旧367606及40个在途任务已定向优雅退出；旧155项产物保留，66项成功继承，89项非成功+192未完成共281新任务。新PID2047613，实测10个isarch均T32/128CPU，入口`.worktree/runner-memory/output/full-generation-v128-10x32-20261104/`，进度每15秒刷新。见`agents/full_generation_20261104/status.md`。


2026-11-04 服务器重启后v128续跑已启动：新宿主PID101892，严格4worker×T32，无taskset/128CPU，三层7200秒。132项旧成果/14085条JSON样例逐SHA保留（后来66项11881样例仍按partial/failed保留），10中断+205未执行共215项队列。新入口`.worktree/runner-memory/output/full-generation-v128-4x32-resume-20261104/`，显式gpt-6.1-terra每60秒专项监控。状态见`agents/full_generation_20261104/status.md`，启动不表示全量PASS。


## 2026-11-09 历史分支清理脚本验证

受测入口 `.worktree/historical-branch-cleanup-20261109/cleanup_historical_branches.py`；命令 `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .worktree/historical-branch-cleanup-20261109 -p test_cleanup\*.py -v`：2项通过、exit 0，3.084秒。独立小仓库实际清理5个已合并分支，5个dirty工作树同提交detach后索引、暂存/未暂存diff和未跟踪文件均保留；核心分支、独立未合并分支、标签和远端引用保留；引用变化时拒绝过期清单。

真实三仓逐分支预检通过：25个本地分支，12个候选，11个关联worktree（5个dirty）。实际`--apply`因原`.git`只读在任何detach/删除前停止，exit 2、删除0，不记真实清理PASS。未改源码或IR，未重跑上轮功能测试。[状态与证据](../agents/historical_branch_cleanup_20261109/status.md)。


## 2026-11-09 std-gaps 合并树预检

在独立Git副本对模型isarch34903a1e与feat/sail-std-gaps7d7e76f3执行`git merge-tree --write-tree origin/isarch origin/feat/sail-std-gaps`：exit0，无文本冲突；结果regs.sail与isarch相同，x0修复保留。相对isarch新增变动为4份V源码和24份workaround。两分页cherry-pick的stable patch-id分别一致。仅验证Git合并树和补丁关系，不记类型、IR、语义或性能PASS；生产分支未变。[调查与证据](../agents/historical_branch_cleanup_20261109/std-gaps-analysis.md)。


## 2026-11-09 std-gaps合入isarch限定验收

候选模型cbb4766f、Isla79d0e335、runner fb9916b9。普通/SYMBOLIC严格类型190.15s/194.02s，严格v128 IR生成460.23s，均exit0；两个v128入口更新，其他IR保留历史来源。path merge6通过，executor396通过/5忽略，Python153通过/210子测试，真实IR向量定向22通过，原生fuzz20/20认证及20次变异/判定，均exit0。配置79/区域130/注释锚点22校验通过，7项预算变化原样继承。早期探针的初值类型与结果格式问题已修正，失败日志保留，不记为模型失败或PASS。未测硬件、其他IR配置或完整向量覆盖。

收尾脚本真实预检通过，并在隔离三仓实际执行快进及源分支清理，原主工作树与脏源工作树保全通过。实际原仓`--apply`因.git只读在写入前停止。完整日志和命令见[议题状态](../agents/isarch_std_gaps_merge_20261109/status.md)。


## 2026-11-09 origin历史分支清理脚本验证

受测`.worktree/origin-branch-cleanup-20261109/cleanup_origin_branches.py`。`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .worktree/origin-branch-cleanup-20261109 -p test_cleanup_origin\*.py -v`：3项通过、5.183秒、exit0。隔离本地bare远端实删10目标并origin-prune，本地及核心远端分支/标签/upstream/暂存和未跟踪文件保留；远端在预检前或之后推进的两类情形均阻止删除，后者验证atomic精确租约。

参数校验通过，不等于真实联网dry-run。三仓真实`git push --dry-run origin --delete ...`均因代理不可达exit128；实时ls-remote也失败，真实远程删除和fetch-prune尚未执行。[命令及记录](../agents/origin_branch_cleanup_20261109/status.md)。


## 2026-11-09 全分支发布与仅清索引脚本验证

命令`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .worktree/push-index-cleanup-20261109 -p test_maintenance.py -v`最终2项通过、1.356秒、exit0。临时bare远端实测单仓atomic推送全部测试分支与archive、设置upstream；非快进dry-run在任何实际发布前阻断。索引测试验证没有完整推送回执不能清理、部分暂存中间版可从原index+pack在独立存储恢复、工作区及未跟踪文件保留、仅移除缺失记录和重复执行幂等。初次测试入口的非ASCII bytes字面量已修正，不列为通过依据。

实际工作区原审计3处223条cached，207条历史精确覆盖；16条为旧源码/缓存，已保存恢复材料。调查期间观察到外部清空索引并移除dead记录；本会话清理脚本先因变化停止，后续只读终核为空。12分支origin上游已由外部设置，真实网络回读仍因代理不可达失败，未把本地缓存当作本发布计划完整成功。源码/IR未修改，不新增功能PASS。[完整清单与证据](../agents/push_index_cleanup_20261109/status.md)。

## 2026-11-09 执行帧 CoW 与 MMU 归档

候选Isla7885b24d，基线849900a6，官方Z3 1fd1d3613，离线8路构建。frame默认6通过、tracetool执行器498通过/5忽略、数组内存34通过，axiomatic类型检查和格式检查通过。新增读计数回归先复现路径串扰，修复后自定义区域和回调两种模式均通过。只读真实预检、隔离主线快进与重复执行通过；原仓主线尚未合入。未生成IR、未做make或端到端性能验收。[完整范围、命令与审查](../agents/cow_local_frame_20261109/report.md)、[结构化结果](../agents/cow_local_frame_20261109/verification.json)。

MMU本轮仅归档和关停，无新增动态PASS。旧运行44393文件/169658699字节已清理，保留Markdown和处理后数据；历史计数和2026-11-05后处理结论修订均保留。[最终报告](../agents/mmu_symbolic_experiment/final-report.md)。
