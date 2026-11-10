# 内存正确性修复状态

2026-11-02：**F1–F5修复及实施后Sol独立review完成；本轮范围可接纳，无未关闭P1/P2。** 保留原模型/MemoryCallbacks/Target分层，未提交或移动分支及父gitlink。起点见[before.json](before.json)，总体结论与证据见[报告](report.md)，独立结论见[独审报告](independent-review/report.md)。

- 已统一Concrete初态与数组状态、补齐RV32/RV64 GPR初态、修复全寄存器访存早退vstart清零、使用最终同一Model具体化返回值，并将必需字段求值失败写入incomplete且移出gen。
- 独审指出的四个汇编/编码错误出口已补齐错误计数与诊断，再次复审通过；Sol另用最终二进制及生产IR独立跑AMO和sd x6两组探针，均finished。
- 最终v4：正式Release构建、Isla lib163/163、完整IR12组19JSON/65断言、vstart后态8/8、正式make C_MUL finished、格式/diff核对通过；Python80/80及GCC/Clang38/38。源码和二进制由final-build-inputs.json固定。
- 模型普通/SYMBOLIC严格检查通过；四配置实际生成并安装5IR，636条模型来源哈希及配置/补丁/IR哈希一致。manifest明确标记dirty模型基线+补丁，未伪称原提交源码；79预算/130region/22锚点有效。
- 原有README/scripts/run.mk内容保留；vmtype预算652→658、673→679。过程编译错误、深Store链栈溢出及生成调度冲突记录保留，最终验证在修正后的同一源码上重跑。
- 限制：既有自由地址store SymbolicLength及MRET Poison仍正确标partial；没有把它们列为全路径PASS。未做全量指令覆盖、硬件、完整LR/SC或全部寄存器后态验收。相关未扩展API边界见报告。
