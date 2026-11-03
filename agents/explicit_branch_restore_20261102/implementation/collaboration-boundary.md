# Sail 与 Isla 协同边界

本次行为分界位于 Sail-RISC-V 的模型函数；Sail 模型和 Isla 生成 IR 必须一并更新。工具链快照不含独立 `.git`，不能将父 Isla 的 HEAD 误报为 Sail 编译器提交。

实际 include 链为 `model/prelude/prelude.sail:21` 的 `<float/interface.sail>`，后者包含 float 分类与比较函数；native FP 声明由模型的 `prelude/ieee_fp_primops.sail` 提供。Sail `lib/float.sail` 不是这里的实际直接 include 入口。所恢复的 NaN 规范化属于 RISC-V 包装函数，底层 `fp_is_nan` 只构造判定表达式、`fp_to_ieee` 只构造编码表达式，它们不应自动 fork。是否按 NaN 分裂在包装层的 `if` 决定。

Isla 后端 `isla-sail/sail_plugin_isla.ml` 的 `eager_control_flow=false`，不会一般性将 Sail if 转回 ITE。应以本轮生成 IR 中目标函数的真实 Jump 验证，不以源文本 if 推断完成。

本轮只修改预算已有完成证据的函数。f16/f64 输出规范化、同一文件其他转换规范化、其他向量与 BF16 lane、core/ieee_fp_exceptions.sail 异常事实中的分类等仍有同构 ITE/strict 聚合；这些不是本次已测的单一变化，须单列范围和预算，不宣称全部恢复。纯分类 predicate 与 IEEE 数值运算内部表达式保留数据流形式；实际行为分界（NaN/有限数、非法原因、mask 活动）由可见 if 表达。
