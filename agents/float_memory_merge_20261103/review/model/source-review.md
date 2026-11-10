# 模型合流独立源码审查

已签收实际暂存树 `8b991abd601777a07c62504ad457651b9728fab2`，可由模型负责人形成 memory+float 双亲合并提交。独立核对索引无未合并路径、工作文件与索引相同，166 模型文件及 79 配置均绑定该树。本结论不包含 Sail 严格检查、IR 生成或动态语义验收。

提交后已独立回读模型 `bf861b3e687894480aec701a886a38d4e50b8a99`：tree 与上述已签树相同，父提交顺序为 memory `c70482a7`、float `0f7b8fbc`，工作树 clean。新生成只能以此模型提交署名。

固定输入为 memory `c70482a73be2a67c5a89d88b1e6c2bbea224940c` 与 float `0f7b8fbc6724103f91f929ef6918f123df75d6c9`。独立参照为预检三方自动合并树 `58e9e61079336e250d6ac0892e83dba238f07fef`，逐个读取其实际 blob，比对候选的全部 166 个模型文件。唯一额外源码修改是 SYMBOLIC VFMERGE 和 SYMBOLIC init_masked_source 两处直接 `let start_element : nat = get_start_element();`。没有新增辅助包装、恢复 Ok/Err，或导入其他研发工作树修复。

这两处适配保持 memory 直接读取 `vstart` 的合同，不再仅因越界 `vstart` 生成非法指令陷阱。其他合法性条件仍保留。memory 的 segment 寄存器越界检查以及其他 nat 调用适配均与三方合并参照一致。float 的 77 处纯数据回退所在五个模型文件逐字等于 `0f7b8fbc`；其余模型源码精确身份比对同时固定了 NaN、真实 trap 和 OPEN 的原实现，没有借合流修改策略。

独立解析 79 份 TOML 的两侧共 262 个区域来源：memory 130、float 132。按 helper/指令 arm、实际表达式和预算映射后，候选共 130 个区域。19 份冲突配置逐项核查，其他配置也一起核查。不同 DIV/DIVU 和 REM/REMU arm 虽含相同文本，按不同指令 arm 保留；同一源码语义区域没有机械重复登记。

三类需要说明的合流判断：

- float vexttype/vxtype 各有一个旧 `get_start_element` 越界 if→Err 区域；memory 已授权删除对应陷阱控制，因此这两项明确退役，没有移到其他分支或恢复旧陷阱。
- vexttype 的 `valid_rd_mask` 在 float 已由短路 OR 改为严格 Bool 表达式。两侧是同一 helper 的同一预算意图，合并为一个区域，并修正旧的截尾坐标到当前完整表达式 `46:2–47:79`。
- vvtype 的七个同区域预算存在 float=1、memory=0 的差别。共同祖先为 1，但原注释已明确要求 0；memory `c70482a7` 实际将七处 1→0，float `afff382` 仅迁坐标和注释。保留 memory 的 0 延续目标已有修正；七个差别逐项记录，不重复挂载两个预算。此判断不声称新性能或覆盖率通过。

配置的全局预算、case quota、sample bias、方向和其他非区域参数均核对两侧保持；全部坐标与源码注释锚点有效。基准 IR SHA 按既有 `strict=false` 约定保留，不借其相等性声明新 IR 来源。

另将全部 766 个非模型、非 workaround 的已跟踪 blob 与预检自动合并树逐字比较，全部相同，覆盖 C++ 后端、构建接线和测试夹具，见 [辅助文件身份](staged-support-files-independent.json)。本次冲突修复相关路径的空白检查干净；全量 staged diff 仍会报告 float 继承的文件尾空行及 `test/solve_pure_compare/before.patch` 历史 patch 空白。它们逐字来自固定输入，不为合流另行重写，不能将全量空白检查写成干净。

独立重跑入口为 `python3 agents/float_memory_merge_20261103/review/model/audit_source_union.py`。逐文件源哈希、262 个来源及对应候选区域见 [机器证据](source-union-independent.json)。脚本仅写本审查目录，不修改生产源码或配置。

下一阶段必须另审 ordinary strict、四配置 SYMBOLIC 的实际新生成日志、源/工具/配置哈希、五 IR 与来源侧车。float 旧 PASS 和 memory 旧修复证据均不改署本候选。
