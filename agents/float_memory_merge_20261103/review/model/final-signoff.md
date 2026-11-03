# 最终模型、IR 与永久回归签收

限定签收通过，无本审查范围阻断。最终 Isla 为 `4d085b14aa0f987436b86d72f41fab1df9e9a132`，tree 为 `3d852a5fac6a07ae906e502a430a8ee14a65c075`；模型为 `bf861b3e687894480aec701a886a38d4e50b8a99`。独立回读两个候选工作树 clean，最终 1042 个 Isla 源文件与冻结清单全部一致，无后续漂移。

最终输入清单 SHA-256 为 `30f6847f904ea22b8c7dd355cda988bf35bc9938ec46e7b564c408801365d5e2`，正式二进制 SHA-256 为 `3e44cdd6db67f88f94bc894b5b9c6f1de94b7deeb9eb3d9379c49bec1bafbd3e`。模型/五 IR/四配置及 manifest 均保持先前本轮实际生成并签收的身份，见 [最终输入回读](final-4d085b14-inputs-independent.json)。

- 模型生产源码等于三方自动合并加两处必要 nat 接口适配；保留 memory 越界 vstart 非陷阱和 segment 寄存器检查。float 77 纯数据回退、NaN/真实 trap 与 OPEN 保持。79 配置的 262 个来源映为 130 个区域，七处 vvtype 同区域预算沿用 memory 修正、两处旧 vstart 陷阱区域明确退役，见 [源码签收](source-review.md)。
- ordinary strict 和四配置 SYMBOLIC 实际新生成均 exit 0，166 模型与 149 工具文件前后哈希以及实际 live Sail/编译 Z3 来源一致。五 IR 和 manifest 安装/索引身份通过，默认 RV64 与 V128 别名字节相同；每配置 direct-nat helper 等 memory，浮点相关 helper 函数体 RV64 各 220 个、RV32 215 个保持，见 [IR 签收](ir-review.md)。
- 最终 `ir-all-4d085b14` 真实 `run.py --mode all` 的 26 步全部 exit 0；五入口均执行 helper/state/guard。RV64 每入口 327 个 helper 用例、RV32 307 个，state/guard 全部 `failures=0`。两个实际 debug runner 均动态链接指定官方 Z3，库 SHA-256 为 `899cbc70affab963044e975c814fd549a605b5d7bef31b0fd65fb01421bf9970`。两个 runner 仅补过各四个缺省配置字段，实际断言和夹具保持，见 [兼容审查](permanent-runner-compatibility.md)。
- 最终 V128 上 104 个定向负变异由独立重放全部拒绝，与最终报告逐项相同；104 个目标变异互异，涉及 43 个函数，拒绝详情全部非空。实际 IR SHA-256 为 `40f34f706963afcca7dfbf8504ee888bdd004cd0c437712f097b7dda64a705c9`，检查器仍为已签 `9ebd0d937edc805e49103984bffbb507470115d349d7262553b6943b9e2763cf`。见 [最终永久回归与负控证据](permanent-stage-4d085b14-independent-portable.json) 和 [负控独立重放](negative-104-4d085b14-independent-replay.json)。

首次初始化器编译失败、preliminary、stage v2 和 `7cce7834` 的结果保留各自身份，不改署最终提交。此次结论限模型合流源码、预算区域映射、严格生成来源和上述永久回归/定向负控，不宣称全 77 条预算、全输入域或硬件差异验证通过；动态数值、真实 Clause 与 workspace 测试另由对应负责人签收。

精选归档说明：上面的 `-portable` 文件只规范化本机路径前缀，独立审查的原始证据仍在主工作区。原件与副本哈希见[证据清单](../../implementation/evidence-selection.json)；签收结论和所引原哈希未改。
