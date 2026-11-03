# 显式控制流恢复计划

目标：恢复官方 Z3 消融中 B 三次均完成、未超过完整 Clause 7200 秒的语义分支，并与生成 IR 协同。NaN/非 NaN、正负零、mask 活动性及非法原因属于需要分别见证的控制条件；普通数值表达式不一律拆分。

范围：float 模型工作树的 fp_minmax.sail、softfloat_symbolic_f32.sail、vext_fp_insts.sail、vext_fp_red_insts.sail、vext_fp_utils_insts.sail。accrue_fflags 与未完成 flags-arithmetic 共用，暂缓；分类已三对完成并纳入；饱和等消融结论。根 sail-riscv 暂存内容不动。

步骤：核对旧单变量补丁和当前源码；只恢复同条件同结果的 if；独立 GPT-6.1 Sol 语义审查；普通与 SYMBOLIC 严格检查及 RV64D/V128、V256、V512 和 RV32D 四配置完整 IR 重生；核对源码区域 workaround；组合配置实际 Clause 验证；主 agent 审核后按 model 分类提交与同步引用。

Sail 工具链：使用既有 toolchain-a198-v2-20260927/sail-src 快照，Isla plugin 使用此前已验证构建。不改编译器通用优化而影响其他模型，先检查显式 if 是否在 IR 保留真实 Jump。若 Sail native float 包含协同条件，则单独给出证据和调整。

验证记录写 implementation/。单项历史消融不是组合改动全量验收，当前尚未 PASS。
