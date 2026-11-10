# 从 1a135b24 起的逐提交合并价值评估

2026-10-16。范围为 `feat/sail-riscv-review-20261016` 的 `1a135b240b6a48603f7704fcf7a130df54298c85^..cfde70ec9eac79f94d808f27727c4e269f7c71ee`，共22个提交，包含起始提交。原目录仍为 `feat/isla-workarounds@4f2ac293`，不是评估链末端。

按合入本项目的 Isla 使用分支判断，区分改动价值和当前接纳条件。依据实际 `git show`、[逐层检查与最终构建记录](commits-20261016.md)及其原始日志。本轮只作源码/证据审阅，没有运行新的功能测试，没有执行合并或改变源码、索引、分支、gitlink。此前 PASS 仍只适用于各自记录的版本和范围。

## 逐提交建议

| 提交 | 改动价值 | 当前建议及原因 |
| --- | --- | --- |
| `1a135b24` | 修正FLI常量文字和四条BF16汇编分隔，直接改善生成汇编的可用性。 | **优先合入**。范围小；拆分时104条文本/编码及32项FLI映射往返通过。 |
| `a273a752` | 提供ITE、strict Bool、Bool转bit，让符号条件成为表达式，供后续状态/译码优化复用。 | **随消费者合入**。有基础设施价值，单独不带来明显功能；需要匹配Isla原语，普通后端有Sail函数体。通用接口放在IEEE命名文件中的归属可后续整理。 |
| `469e3dab` | 快速FPR访问补Ext_F断言、寄存器表示转换、写回callback和FS/SD Dirty。 | **优先合入**。修复真实状态缺失，应先于性能重写；现有21层类型检查不替代精确真实读写回归。 |
| `d6463f36` | 用ITE更新异常状态，避免flags是否变化引起路径分叉。 | **补状态/观察合同后合入**。独立flags方程检查有价值，但并非真实FPR执行证明；SYMBOLIC体直接写mstatus，未经过旧dirty函数的long_csr_write_callback，不能声称所有观察事件等价。默认Sail callback为空体。 |
| `47acd6c7` | 快速VPR写回补VS/SD Dirty及寄存器callback。 | **优先合入**。修复状态副作用缺失，价值不依赖后续大规模浮点重写；仍需按实际IR验证快速写臂。 |
| `8ff8f22a` | H/S/D取负使用符号位异或，NaN拆箱用ITE。 | **建议合入**。表达式局部、语义易核对；依赖公共ITE。新增旧helper缺陷注释不代表那些helper已被修复。 |
| `485d945b` | AMO先检查完整编码布局/合法子字段，再解payload，减少无关译码分叉。 | **建议合入**。最终树E/non-E新IR探针通过，生产amo_encoding_valid仍保留；fixture sentinel guard不能替代完整生产guard验证。 |
| `1d48fe1c` | VMVR/VEXT显式membership和完整布局，减少部分字段提前解码。 | **补精确译码回归后合入**。有针对性，但增加手写mapping维护成本；需非法字段、往返、生产扩展guard和实际路径数对照。不能套用AMO探针结果。 |
| `31ef6a2e` | 四类浮点unary子字段以纯membership匹配，保留execute。 | **补精确译码回归后合入**。方向符合既有无关clause分叉诊断；仍需真实decoder的域/往返与分叉对照。 |
| `22af8fed` | 增加SoftFloat数值adapter，分离数值计算与异常策略；统一TLS/FAST_INT64 ABI。 | **作为共用后端依赖组合入**。单独未接入生产，且SoftFloat PUBLIC宏已经改变构建合同；最终组合构建通过不证明本层旧消费者构建通过。 |
| `7020b61d` | Sail共用IEEE五异常、舍入、转换及ROD公式，避免两后端分别实现策略。 | **有价值，补工具链和数值证据后合入**。核心语义规模大；32种flags位序/分类探针不覆盖全部异常公式。 |
| `058e5a78` | 67个浮点包装改为普通C++与Isla共用Sail策略，旧SoftFloat包装留作oracle。 | **暂缓直接进入稳定分支**。这是主要架构切换，普通C++也受影响；必须固定Sail FP/RM lowering补丁、Isla版本，更新旧测试，并对精确候选做独立数值/flags差分。最终C++及两项BF16 CTest不足以验收67包装。 |
| `37a2b389` | 标量/向量共用min/max/minm/maxm的NaN、sNaN及正负零规则。 | **修复测试后合入**。减少重复规则有价值，但普通C++也改调用链；旧标量结构检查失配，vector helper旧对照构造器也不能提供当前等价证明。 |
| `aebc380d` | 普通FP拒绝SEW8、保留合法INT8转换；BF16要求SEW16，非法LMUL先返回Illegal。 | **优先接纳修复，补边界回归**。不能把所有转换的SEW8一律禁止；本层尚未修到widening reduction，后者在d59577a0补上。 |
| `d59577a0` | strict Bool/option(int)相等和快速源mask降低辅助分叉。 | **拆清语义变化并更新fixture后合入**。还把illegal_fp_widening_reduction改用illegal_fp_reduction，从而新增SEW8拒绝，超出纯优化；旧四函数fixture失配。 |
| `19ab764e` | lane helper只返回值/flags，解耦计算与fcsr写回，为mask后汇总提供基础。 | **修好helper旧新对照后合入**。设计有用，但当前生成器引用不存在的old_fp_min_pure，动态等价测试无法运行。 |
| `b206b683` | 算术/FMA/比较先算候选，mask选择值和flags，最后累计异常。 | **暂缓，补全状态等价及性能对照**。跨12类execute；源码结构检查不足以覆盖mask/vstart/vl、alias、旧目标值、异常和写回。减少分支可能增加SMT项规模，不能仅凭代码形式判断端到端提速。 |
| `d157ac2b` | 转换、sqrt/class等四类unary采用纯结果和mask汇总。 | **暂缓，补转换边界回归**。需覆盖INT8/16饱和、NaN、RTZ/ROD、宽窄化及非活动lane异常；类型检查不能证明数值边界。 |
| `fd4a7898` | VFMV/VFMERGE用向量选择代替逐lane条件控制流。 | **优先于其他大规模lane优化接纳**。最终helper探针14项通过，move路径256→1、merge8→1；这是小模型数据，不是生产完整指令或端到端耗时。须带所需接口并核对实际execute。 |
| `abd08a91` | 归约保持lane顺序，以ITE选择累加值并合并flags。 | **暂缓，补真实归约执行对照**。保持顺序是正确约束；累加有前后依赖，不能套用独立lane或move的等价结果，还需全mask/vl0及特殊值回归。 |
| `29436089` | BF16 VF标量转换只在首次活动lane累计flags，避免无活动元素的sNaN误置NV。 | **优先合入**。修复具体可解释的问题；最终普通C++的wma_flags回归覆盖vl0、全mask、vstart及活动lane。bf16_to_f32纯接口在起始基线已有，修复本身不必等待共用后端整组，提前挑选仍须解决上下文并复验。 |
| `cfde70ec` | 四条BF16向量路径采用纯候选和mask选择/异常汇总。 | **暂缓，随lane优化验证后合入**。应保留29436089独立修复；普通C++ BF16 CTest走普通分支，不能充当新增SYMBOLIC execute的动态证据。 |

## 接纳顺序和证据边界

先处理汇编和FPR/VPR状态修复，再处理SEW/BF16正确性；公共Bool接口只按所需依赖带入。随后接纳局部表达式优化、译码优化和已有定向路径证据的move/merge。共用后端作为明确依赖组评审，稳定之后再接大范围lane、unary和归约优化。

现有23批中的21个Sail模型层各做普通/SYMBOLIC类型检查，共42次；本次范围不含最前面的gitignore提交，因此仍覆盖同样21个模型层。完整C++构建使用额外Sail补丁，动态Isla探针使用dirty工作区。精确、干净、可获取的工具链和Isla提交仍是交付条件。手选提交不能按文件整体复制，否则会夹带后续依赖。

影响V源码的接纳还须核对workaround坐标并生成/记录新的实际IR；旧IR的数值或路径记录不自动迁移。本轮没有证明完整新IR、77/79目标、所有数值域或硬件测试通过。
