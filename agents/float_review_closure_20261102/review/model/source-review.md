# 模型源码阶段独立签收

相对于已发布模型 `6202e23`，六个生产文件的最终源码差异独审通过，未发现源码阻断。此结论不包括完整类型检查、ordinary/SYMBOLIC 严格生成、五份 IR CFG、动态 oracle 或完整 Clause 预算；这些必须在最终冻结版本分别签收。审查者未改生产源码。

| 文件（相对模型仓库） | 受审 SHA-256 | 证据 |
| --- | --- | --- |
| `model/extensions/FD/fdext_regs.sail` | `252002bb29d17da842bfacc2ac5733baec7eeada2d84dce29c233a1a8dafb3b5` | [flags](flags-source-review.json)、[差异](flags-reviewed.patch) |
| `model/extensions/V/vext_fp_utils_insts.sail` | `2c6042a67c1798e746178725ab42a3cf2ff9c1df5b4552a18bcb1e1757ec3564` | [六窄适配器](narrow-source-review.json)、[差异](narrow-reviewed.patch) |
| `model/extensions/FD/softfloat_symbolic_f16.sail` | `63c22bc512222b9697a5d7bf544f4260074eb5cbd2b62cbd716e7cd8917a5877` | [包装函数](wrappers-source-review.json)、[差异](wrappers-reviewed.patch) |
| `model/extensions/FD/softfloat_symbolic_f32.sail` | `eb9d4883a239700a78f1969c879ac3857f7b8cb2d9290098c4d06ca769d94ac1` | 同上 |
| `model/extensions/FD/softfloat_symbolic_f64.sail` | `0cd758949af3ed2b13bc519087aff3fa87cf9c080d79b53efe1bebc7108b14ed` | 同上 |
| `model/core/ieee_fp_exceptions.sail` | `23fda9824c2280609062bbe2b9766597681c29af13a1e9cf1be045d9106757a8` | [异常](exceptions-source-review.json)、[差异](exceptions-reviewed.patch) |

flags changed 真臂才断言扩展互斥并更新 FS/SD；FFLAGS OR、其他状态位与原两个 callback 保持。六窄适配器显式区分 overflow，三个 signed helper 在 overflow 内分别选择正负端点；NV 替代上游 flags，范围内保留原 flags。独立重跑官方 Z3 的33个全位向量检查，12项等价反例 UNSAT、21项候选边界 SAT；该证明不包含上游 FP 输入可达性。

12个 FP→整数包装保留原舍入、异常与候选表达式，显式按 invalid、NaN、符号选择结果，负 NaN 仍饱和最大值。两个 ROD 包装先分模式，再同臂返回 flags/bits；普通 RM 解码仅在普通臂。控制选择脚本独立重跑13260项通过。中间版曾删除普通 RM helper；审查者首查只搜 model，未发现现有 test 探针依赖。实现者补查整个仓库后恢复原 helper，最终表达式不变、注释更新，已重新签收；旧 f32 `43f74365…` 与差异另存 intermediate 历史，不得用于最终冻结。

异常核心的18个算术 helper 保留每源 NaN 分类，在特殊异常原因处分支，只有原 finite/valid 臂运行更宽算术与舍入异常。四个 rounded helper 将最终 OF/UF/NX 选择作为真实 flags 返回；不改变阈值公式，不假定 OF⇒NX 或 OF/UF 互斥来删其他位。FP→整数范围判断、round NX、四个普通转换/BF16 finite gate 与两个 ROD jam 的原语义保持。独立 [审计脚本](audit_exception_source.py) 检查33个改动函数、28项数学公式身份、18528个特殊类别/任意舍入异常组合及8种任意 OF/UF/NX 元组，见 [结果](exceptions-formula-audit.json)。它验证源码与布尔等价，不证明 native FP primitive 正确或动态见证齐全。

实施者直接 `--just-check` 遇到未改 `masked_select` 量词错误，ordinary 检查曾因并发编辑被停止；均未计作类型检查 PASS。正式生成应按项目既有流程固定完整源码与工具链后重做，不从 fmt parse、局部代数或历史生成结果外推本轮通过。
