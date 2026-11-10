# Sail-RISC-V 与 Isla 分支及合并选择

清理追记（2026-10-21）：用户随后要求删除本地 `feat/sail-riscv-review-20261016` 与 `feat/sail-riscv-review-20261016-readable`，已执行。旧split工作树改为detached cfde70ec并保留，功能归组分支3ea3cbaf保留。下文分支表记录清理前调查快照；现行清理状态见 [记录](../sail_riscv_commit_review/status.md)。

核查日期：2026-10-21。依据当前 Git 对象、索引、工作区、worktree 和既有专题记录；机器可读快照及试算输出见 [证据](evidence-20261021.json)。本轮没有执行实际 merge、commit、checkout、push 或功能测试。`merge-tree --write-tree` 只生成试算对象，不移动分支或修改工作树。

## 当前工作区与提交的关系

| 仓库 | 当前分支／HEAD | 相对 HEAD 的工作区状态 | 父仓记录 |
| --- | --- | --- | --- |
| 根仓 | `master@a85d6df` | 已有多项文档、脚本和证据修改／未跟踪文件；缓存引用显示领先 `origin/master` 20提交 | 两个gitlink都未暂存更新 |
| `isla/` | `feat/float-support@7b7337b` | 24个暂存路径，另4个路径有未暂存修改，无额外未跟踪文件 | 固定 `b18d6b7`，当前HEAD在其上新增5提交 |
| `sail-riscv/` | `feat/isla-workarounds@4f2ac293` | 163个暂存路径，无未暂存／未跟踪文件；其中12个pyc | gitlink与HEAD相同 |

Isla 的未暂存4文件为 `isla-lib/src/primop/float.rs`、`src/isarch/exec.rs`、`src/isarch/mod.rs`、`src/isarch/target.rs`，主要是后续结构修整。暂存24路径同时包含通用支持和浮点改动，含默认IR、官方浮点名单和legacy测试，不能将当前索引整体视为“纯浮点提交”。相对HEAD暂存增删量约24.9万／24.2万行，主要来自整份IR更新，不代表同等规模的手写实现。

本地 `feat/float-support` 与缓存 `origin/feat/float-support@f276fdd` 分叉：本地独有6提交，远端引用独有7提交，共同祖先为 `f4f8e45`。本地新增workaround归属、trace组合／writer、进程组清理、smtperf测试和worker panic记账；远端一侧保留较早的浮点整批实现。当前工作区又保存了后续拆分来源。因此不宜用普通 `git pull` 直接把旧整批实现叠回新拆分结果。

两次 `git ls-remote --heads origin` 均因TLS EOF退出128，未获取最新线上状态。本文 ahead/behind、远端分支位置及“本地候选未见远端同名引用”均基于缓存，不证明线上当前不存在相应提交。

## Isla：两条工作线与后续拆分

内存与浮点工作线共同祖先为 `0008fae`。当前浮点基线 `7b7337b` 有20个内存线未包含的提交；内存线有17个浮点基线未包含的提交。

| 分支／引用 | HEAD | 定位与提交范围 | 工作树状态 |
| --- | --- | --- | --- |
| `feat/float-support` | `7b7337b` | 原浮点工作线；后续实现仍在暂存／未暂存层 | 原 `isla/`，24个dirty路径 |
| `origin/feat/memory-support` | `f06371f` | 内存最初5提交，接入initial memory和事件；是缓存远端引用 | 不等于后续完整内存成果 |
| `feat/memory-consistency` | `47ac90c` | 在f06371f上追加12提交；自共同祖先共17提交 | `isla/.worktrees/memory-consistency`，干净 |
| `feat/float-only-20261008` | `be1296b` | 从7b7337b增加6个浮点提交＋2个复审修复，共8提交 | `.worktree/isla-float-only-20261008`，干净 |
| `refactor/general-support-20261007` | `09fe582` | 从7b7337b增加8类通用支持＋6个复审修复，共14提交 | `.worktree/isla-general-20261007`，另留浮点残余 |
| `fix/general-review-20261008` | `09fe582` | 与上一分支指向同一提交，不是另一组功能 | `.worktree/isla-general-fix2-20261008`，干净 |
| `feat/witness-randomization` | `2fefa72` | 从f4f8e45增加1提交，见证随机化，10文件 | `isla/.worktrees/witness-pure`，干净 |

“仅浮点”指相对 `7b7337b` 的增量只纳入浮点专项；基线自身已包含早期浮点支持、trace及基础设施。随机化分支的“纯净”也指新增提交不夹带同期浮点修改，不表示整个祖先历史没有浮点代码。

其他本地分支 `dev-isarch-runall-ext@85d7c70` 和 `master@b898a55` 均为当前浮点基线祖先，不是待合入的新能力分支。

内存17提交包含：initial-memory接线及事件；数组一致性、事件正序、pre/post物化和ExecuteAs；PMA配置与边界符号化；AMO128位比较；CSR符号化及mstatus域修订；独占写与FPR/VPR初值修复；value hints；encoding slices；物化后的encdec回环过滤。**它已经超出单纯“内存符号化”，同样混有平台配置和采样／找bug策略。** 如果只接纳核心内存，需要在隔离候选重新提取并验证，不能假定全部12个后续提交都属于最小内存功能。

仅浮点8提交覆盖primop、默认IR、旧SoftFloat分派退役／回归迁移、fcsr、FS/VS见证偏好及非访存FD入口；两个修复补齐其他4份IR的helper，并恢复5份IR的快速FPR状态副作用。通用14提交覆盖MixedBits、宽值格式化、模型值缓存、采样历史、mapping校验、断言两臂、同模型前后态与编码、RV64域约束，以及后续消费者／宽值／MPP／编码可行性修复。原8提交并不是最终已修版本。

通用分支工作树的10条status记录是残余浮点修改（含未跟踪目录的折叠显示），不属于 `09fe582` 提交树；合并该分支引用不会自动带入这些残余。

## Isla：已有候选不能混淆

1. `.worktree/isla-float-support` 当前为干净detached `cf128bb`，2026-10-09创建的合并提交。父为 `7b7337b` 和 `be1296b`，完整tree与 `be1296b` 相同：**已合仅浮点，未合通用、内存或随机化。** 它已不是10-08记录中“干净基线7b7337b”的状态，但尚无本地分支直接指向该detached HEAD。
2. `.worktree/isla-merge-check-20261008` 当前仍停在待提交合并：HEAD=`09fe582`，MERGE_HEAD=`be1296b`，30条暂存记录，无未解决冲突、无未暂存修改。复制其索引后算得tree=`54fb4e8e26bcf654dc182a470f604439a1380028`，与10-08报告相同。这是**通用＋仅浮点**候选，还没有合并提交。
3. `.worktree/isla-float-review-base-20261008@7b7337b` 与 `.worktree/isla-general-fix-20261007@4b141eb` 是干净历史快照，不是最新版功能交付。

前两项不能相互替代，也不能据此说原 `feat/float-support` 分支已前进。原分支仍为 `7b7337b` 加dirty层。[原试合并记录](../float_support_review/merge-check-20261008.md)对“意图一致／实现含bug fix”的判断仍可参考，其10-08创建基线段落只描述当时状态。

## Sail-RISC-V：三条等价拆分链与独立补丁

三条拆分链均从 `4f2ac293` 出发，末端完整tree相同：`6fafcbc406156ee275bcf301e6db1743eb417a0f`。逐个索引条目核对后，原工作区暂存内容与该tree仅差12个新增pyc；排除这些缓存，模式和blob全部相同。它们是同一批改动的不同提交组织，不应作为三套功能重复合并。

| 分支 | HEAD／数量 | 用途 |
| --- | --- | --- |
| `feat/sail-riscv-by-category-20261019` | `3ea3cbaf`／12提交 | 11类模型功能＋忽略规则，适合按功能审核 |
| `feat/sail-riscv-review-20261016` | `cfde70ec`／23提交 | 更细的实现阶段，便于逐项挑选 |
| `feat/sail-riscv-review-20261016-readable` | `755fea6e`／23提交 | 上一条逐层tree相同，主要重写提交说明 |
| `model-fix-vd-nf` | `46f8273a`／1个独有提交 | 来自较早5f1a0de基线；segment寄存器组界和vstart语义，不含于上述tree |
| `fix/zvksha2-sew-assert` | `72884c97`／1提交 | 从4f2ac293恢复SHA2的SEW断言，不含于上述tree |

12提交链和23提交工作树均干净；可读23提交分支没有独立worktree。`master@563dace0` 是另一条上游历史；它相对4f2ac293有6个独有提交，同时缺少该基线的9个提交，不能拿名字当作本项目当前集成主线。

12提交的审核边界依次为：忽略规则；FLI/BF16汇编；公共条件选择与标量表达式；FPR/VPR状态；译码优化；共用IEEE浮点后端；SEW合法性；向量辅助／掩码／纯lane工具；逐元素浮点；归约；BF16无活动元素异常；BF16纯计算优化。[完整提交／依赖索引](../sail_riscv_commit_review/commits-by-category-20261019.md)。

若希望单独接纳正确性修复而暂缓性能改写，需注意12提交链把公共Bool接口和标量优化合在一起。更细粒度可从23提交链取来源hunk；但其SEW修复分散于 `aebc380d`、`d59577a0`、`cfde70ec`，不能漏掉加宽归约及BF16转换合法域。12提交链的 `795bfdf1` 已集中这几处修复。两种链都不意味着所有提交可任意独立cherry-pick。

另有缓存远端 `origin/fix/zfa-bf16-assembly@fbacdfff`：是在官方新基线上的上游汇编修复交付，与本项目旧基线的 `d9db8dae`／`1a135b24` 属于同一问题的不同移植，不能计为额外独立功能；其版本不适合无核对直接合进旧模型。本轮未操作该PR。

## 当前文本合并试算

使用 `git -C <repo> merge-tree --write-tree --name-only <left> <right>`；以下只表示提交树的文本冲突，不包含dirty层，也不证明运行正确。

| 组合 | 冲突文件 |
| --- | --- |
| Isla仅浮点＋通用 | `isla-lib/src/primop/float.rs`、`src/isarch/exec.rs`；已有上述已解决候选 |
| Isla通用＋内存 | `agents/findings.md`、`isla-lib/src/smt.rs`、`scripts/run.mk`、`src/isarch/exec.rs`、`src/isarch/mod.rs`、`src/isarch/target.rs` |
| Isla仅浮点＋内存 | `agents/findings.md`、`isla-lib/src/smt.rs`、`scripts/run.mk`、`src/isarch/exec.rs` |
| Isla基线7b7337b＋随机化 | `src/isarch/exec.rs`、`src/isarch_main.rs` |
| Isla通用＋随机化 | `src/isarch/exec.rs`、`src/isarch_main.rs` |
| Sail-RISC-V功能链＋model-fix | `model/extensions/V/vext_arith_insts.sail`、`model/extensions/V/vext_utils_insts.sail` |
| Sail-RISC-V功能链＋SHA2断言补丁 | 无文本冲突；语义与动态结果未验 |

没有试算“通用＋浮点＋内存”的完整三方最终候选，上述两两冲突数不能当作最终总数。

关键人工合并要求：

- SMT保留浮点基线已有的显式tactic初始化和seed能力检查，迁入内存侧SAT模型缓存／超时逻辑；不要把旧的“不支持seed则跳过”整段覆盖回来。内存缓存的是Solver最近SAT模型，通用分支缓存的是Model具体值，不能因都叫缓存就删除其中一个。
- collector保留通用同模型编码可行性和错误传播，同时迁入内存数组、事件及pre/post；FS/VS偏好置于编码可行checkpoint内。内存CSR符号化／约束与通用RV64域约束须逐项核对，避免双重约束意外丢解。
- `run.mk` 统一或兼容 `ISA_CONFIG` 与 `SOLVE_CONFIG`，保留进程组监督、trace和FD入口。组合FP访存配置必须实际启用FD、FS及内存/PMA；两边原配置分别关闭功能的默认值不能机械拼接。
- Sail-RISC-V `model-fix` 来自较早基线，保留当前workaround归属与向量重构；仅迁入目标修复并重新检查语义。SHA2补丁改变非法SEW从显式Illegal返回到assert，应单独审核预期，不能因为无冲突就自动接纳。

## 合并选择与建议

**选择A：按职责逐批整合，推荐。** 以7b7337b的基础设施为基线，在隔离候选核对并复用 `54fb4e8e` 的通用＋仅浮点结果，先形成可追溯交付；再整合 `47ac90c` 内存线，区分核心一致性、PMA/CSR、value hints/encoding slices等策略；随机化 `2fefa72` 最后独立接纳。Sail-RISC-V选12提交链作功能审核目录，只合一套历史；内存模型修复与SHA2补丁另列。整合期间原dirty工作区留存，不重复提交已被拆分覆盖的整批补丁。

**选择B：只合正确性和必要支持，优化继续分支审查。** 优先汇编、FPR/VPR状态、SEW、BF16无活动元素异常；公共接口随消费者带入。共用浮点后端、大范围lane/归约、随机化和找bug策略分别审核。此方案需要重组精确候选并生成匹配IR，不能直接把基于完整新后端的仅浮点IR放到部分旧模型上并声称版本一致。

**选择C：先做完整功能集成分支。** 合入双方已完成能力并集中解决冲突，适合尽快得到联合运行环境；暂不把该候选当稳定版本。仍保留每个功能提交及独立验证，不建议squash后丢掉审核边界。与A相比，单轮验证面更大，更难定位行为变化。

当前更适合A：拆分与复审已做过，通用＋浮点候选也仍完整存在；需要补的主要是内存联合语义和源码／IR／配置的版本闭合。若用户明确不接纳某些优化或策略，则转B，按依赖重新提取，不能仅按提交标题删除。

## 验证与发布门槛

历史限定证据：仅浮点修复的helper／状态／legacy与指令smoke；通用修复的MixedBits、宽值、编码可行性及V128/V256 smoke；通用＋浮点候选的93库＋25bin、浮点10、集成15和编译／fmt；Sail-RISC-V功能链22次普通/SYMBOLIC类型检查。原报告明确未全77项／全库／硬件，不能迁记为本轮联合PASS。

实际整合后应验证内存同址/重叠/路径隔离、事件顺序和pre/post，保留编码回环及错误退出；通用宽值/MixedBits；FD状态与NaN/flags；所选向量和BF16路径。FP访存单独验证组合配置与真实读写，不能由非访存或整数内存结果代替。求解检查gen数量、内容、超时和失败，不只看退出0。

模型取舍确定后固定相应Sail编译器补丁、Sail-RISC-V提交与Isla提交，按需重生IR并核对workaround源码坐标；目前根目录没有 `sail/` checkout，不应把现有外部编译器补丁当成父仓已固定依赖。Sail-RISC-V源码提交、消费它的Isla提交先成为可获取版本，最后根仓更新两个gitlink及相关harness/文档。原163路径、24路径及通用工作树浮点残余在新交付覆盖范围确认之前继续保留。

核查收尾：15个存在的既有worktree的HEAD、索引条目、两层补丁、status与dirty文件哈希均与记录时一致；两子仓所有本地分支HEAD及父仓gitlink未变。一个失效临时worktree仅记录、不清理。首次收尾脚本将一个同inode的挂载路径别名归为仓库外，导致路径查找失败；确认别名关系并改用根相对路径后核对完成，不涉及源码修改或功能测试结果。
