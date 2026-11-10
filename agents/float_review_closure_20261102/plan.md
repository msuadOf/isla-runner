# 浮点遗留项闭环

## 基线与发布

用户授权先推送已复核提交，再计划并实施遗留项，所有实施和验收继续由独立 GPT-6.1 Sol 审查。已按模型→Isla→父float顺序非强推，三个远程SHA回读一致，见[发布记录](publication/completed.json)。实施基线模型6202e23、Isla `cf1aa14`、根float a6b6ecd；官方Z3固定1fd1d3613。保留原根dirty模型、memory分支和无关工作树。

## 范围与判断口径

逐项登记调用者、原Sail/纯helper行为、生成IR跳转与具体见证义务。NaN、sNaN/qNaN、无穷、正负零等特殊值选择不同语义行为，按控制流审查；mask激活、异常/合法性、饱和边界同理。普通数值运算和flags位拼接不因含ITE机械改写。

优先处理：正式accrue_fflags changed；六个窄转换（含已有f16→i16的正负饱和出口）；Inf抵消、零除/0÷0、其他异常与ROD等剩余选择。新发现逐项纳账，不以名称或旧状态推断当前缺陷。枚举重放先查API契约，修实际实现缺陷或无效测试用法，不删测试、不放宽断言掩盖问题。

## 分工与写边界

1. 清单/语义分析：只读模型与IR，写inventory/；独立Sol给每项控制流/数据流判定和实施前语义意见。
2. 模型实施：待清单确定文件后分配flags、窄转换、异常三个互不冲突写边界；同一模型文件仅一owner。仅改runner-float/sail-riscv，原根模型只读。
3. 枚举修复：仅根isla中的明确源码/测试边界；TDD与官方库测试，单独提交后同步float子模块检出。
4. 验证：独立目录冻结source/IR/config/binary/lib/seed/命令；调度多个空闲物理核，不与其他任务同核或SMT同胞竞争。
5. 独立GPT-6.1 Sol：不参与实现，单独review/签源码、IR CFG、动态结果；各阶段不跨版本继承PASS。主agent集成、版本同步、文档和沟通。禁止二级代理。

## 阶段及退出条件

- P0：旧提交安全发布（已完成）。
- P1：当前源码清单和调用图，Sol逐项判定，固定测试与待改文件。
- P2：先红后绿实施；模型按model职责分commit，Rust cargo fmt；枚举同/异Context、重复重放、单/多成员和多枚举、冲突及模型回读边界须核实。
- P3：ordinary strict和四配置SYMBOLIC完整生成；166模型源/工具/配置哈希、五IR、区域/锚点和永久CFG回归；只认实际可达控制关系。
- P4：影响Clause以原完整配置并行跑，T1/qffp/seed17，整Clause及单次SMT均7200秒。覆盖H/S/D和相关SEW、活动/屏蔽、多lane、五舍入及ROD等，具体矩阵由调用图确定。定向边界/oracle检查不替代全Clause预算验收。
- P5：Sol独立核数值/flags/状态/编码与覆盖义务、GCC/Clang助记符/位串/.insn、真实make solve；修全部阻断后同步源分支/五IR/父gitlink/manifest，形成提交和证据。

若超预算，区分主路径与辅助路径，分析路径上界/已完成/排队账及单次SMT耗时。不得缩域或取消预算冒充通过；未决项明确保留。全部特殊行为控制流覆盖须逐项闭合，不以单一格式或固定vl代表全域。

## 清单收敛后的分解与冻结版本

静态调用闭包确认64条受影响Clause，另13条作为同版本兼容回归，详见[inventory](inventory/affected-clauses.json)。实施扩展为六窄、12普通整数包装、18算术异常helper、最终异常类别与finite gate、ROD普通/专用模式和jam；不是只改五处overflow。源码已冻结到模型8ad5e8e和Isla42000be，按model职责分四提交。

四模型owner唯一文件边界：flags→fdext_regs；narrow→vext_fp_utils_insts六helper；wrappers→三softfloat_symbolic_f*；exceptions→core/ieee_fp_exceptions。源码签收后切换为定向动态验收：flags owner核状态；narrow owner核六窄/12整数包装真实FP；wrapper owner核算术/ROD/BF16 oracle；exception owner核三表示/真实Make。validation owner统一生成与永久CFG，原model Sol独审源码/IR，另Sol独审动态结果；enum Sol核同Context修复及正式程序/runner冻结。所有长测待最终资产哈希齐备。


## 2026-11-03 按共同参照收敛

Isla共同参照为 `0008fae76f4cff86dae1a036d889f0414c228e9d`，模型对应独立版本边界，不跨仓比较SHA。已有枚举缓存、编码约束隔离、ExecuteAs修复分别有错误或超时实证；不擅自删除用户初态配置及继承功能。

模型精简候选 `e9d69d2` 已在独立 named 工作树提交，仅core异常文件 +16/-74，删除18处纯数据分支及冗余mask包装；必要特殊值、非法原因、饱和和状态写回控制保留。两Sol已签源码，数值公式不变。新的ordinary/four-config strict与IR正在生成，随后按新哈希重跑定向oracle、双工具链和完整Clause；永久CFG检查同步改为只要求必要控制关系。

冻结214模型与42000be Isla继续原77项完整预算，不改源、输入或旧结果。精简候选以另一批新输入验收。任务分解与边界见[最小性方案](baseline-0008fae/plan.md)。当前尚不具备整体闭环结论。


## 2026-11-03 架构指导再审定

用户最新要求以实测/理论路径规模约束展开，严格区分控制与数据流。统一决策口径见[GOAL最新准则](../../specs/GOAL.md#浮点架构决策准则2026-11-03-最新用户指导)。不因控制流分类或定向PASS自动批准新增fork，不因未证明ITE更快而反向要求展开。

独立GPT-6.1 Sol重新核flags changed、六窄转换、十二整数包装及算术异常/finite gate：逐项定位6202→e9与模型原生表达，列KEEP/REVERT/OPEN及实测/理论依据；缺证记OPEN，禁止用源码或数值等价签收冒充必要性通过。期间e9/214冻结完整Clause继续，新裁决未定前不新增生产分支、不移动gitlinks或宣称最终接纳。若需修改，另开候选并重验。


最新准则首批意见已进入准备：narrow owner只在议题 `baseline-0008fae/reduction/new-policy/` 准备5overflow+3sign返回数据流的候选；exceptions owner在同目录准备33个纯flags原因if回退。两者按文件分工，不写共享模型树、不改冻结输入。flags changed及未定gate先记OPEN。Sol正式裁决将明确原生NaN传播/陷阱/模式的保留边界，之后另建候选实施，来源哈希变化须重验。


## 最终收敛交付（2026-11-03 用户明确范围）

仅应用已审33原因+8窄+12整数包装的77处纯数据选择回退，保留已有NaN特殊值/真实trap以及OPEN实现。OPEN必要性和通用ITE/符号化策略配置统一延期到内存分支合流，不再作为本轮扩展研究。最终独立模型树已按core/V/FD三提交形成0f7b8fbc，源码Sol签收，e9/214对照版本保留。

退出矩阵经独立Sol明确、主agent采纳：精确源码回退/OPEN保持，ordinary+四配置strict/IR及永久正负控，新版本300flags、819+282+183转换、315异常actual oracle，1104汇编实际字符串/双工具链字节与真实Make，完整域FLEQ_S及C_ADDI4SPN两入口（7200秒双限、原配置与seed17）。77全域预算不再是本次有限回退的退出前置，也不宣称77全域通过；旧214/e9失败分类单列，真实本轮新增bug仍须修。最终范围声明及动态签收由acceptance Sol留证。

旧两批已自然结束，21449/77与e952/77，不静默改作PASS；大产物在不丢字节和逻辑路径的前提下归档至其他文件系统，释放最终IR/验收空间。之后集成IR/永久测试到Isla、更新float gitlinks/manifest、形成最终提交与限定验收报告，准备memory合流，不执行memory合并。
