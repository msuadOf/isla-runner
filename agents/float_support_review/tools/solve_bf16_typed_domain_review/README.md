# BF16 sharedV typed 调用域独审

范围为最终 1dcc IR、aa069 实际运行时目录中最新 root-caller 表的 371 项前沿。生产源码只读；结果仅对精确 clause、phase、config、root Call PC、source site 与实际分支极性适用。

证明顺序：核冻结版本和原 source token；核 root Call 与唯一且支配使用点的实参定义；区分执行 guard 前 `get_num_elem` 与 guard 后读写；复用最终 BF 控制证书中已审核的断言 handler；以全部有限整数输入解释实际 helper CFG，未说明的值保留未知且两边展开。未知或有限检查仍可达的边保持 `witness-needed`，零动态命中不构成排除。

整数范围使用有符号三位 LMUL 的保守域。getter 正常返回后为 -3..3；后续扩宽断言成功边支配读写才收窄到 -3..2。`get_num_elem` 保留前置 LMUL=3、num_elem=64；不能倒用后续前提。

读寄存器的对齐前提由同一寄存器、同一组指数的实际 `valid_reg_overlap` Call 及失败路径证明。实际 helper CFG 穷举 12,288 个寄存器组合；7,336 个真返回均保证两组对齐且组末界不超过 32。

`dirty_v_context` 的 8 项断言失败边依赖 `hartSupports(Ext_Zve32x)`。工具核对冻结 IR 中 `vector_support_level = Full` 的精确常量初始化及全部 10 个只读引用，再解释 `num_of_vector_support`、`vector_support_ge` 和 `hartSupports` 的实际 CFG。此能力结论不使用 VS 状态。

8 项负控与边界检查覆盖前置 LMUL=3、后置 LMUL 上限、SEW16、reserved-vlmul、寄存器对齐、overlap 失败返回/人为绕过，以及将 `Full` 改成 `Disabled` 后能力断言失败。每项排除记录完整目标 Jump、极性与后继；未知分支始终保留两边。

入口合同：实际 R1 保持冻结配置；指令经成功译码后执行，decode 与 execute 之间不写 `vtype`。SEW16 引用同版本控制证书；结论不适用于任意 `vtype` 的直接 execute。

运行时指定冻结目录、实际 sidecar 和输出目录：

```sh
python3 agents/float_support_review/tools/solve_bf16_typed_domain_review/audit.py \
  --freeze "$BF16_FREEZE" \
  --sidecar "$BF16_SIDECAR" \
  --input isla/target/float-support-review/final-coverage/bf16/shared-v-root-caller-with-overlap.json \
  --fixed isla/target/float-support-review/final-coverage/vector/default-fixed-cfg.json \
  --control isla/target/float-solve-evidence/architecture-certificates/final-20260926T160822Z/certificate.json \
  --output isla/target/float-support-review/final-coverage/bf16/independent-typed-domain-review
```

输出在专属 `independent-typed-domain-review/` 中，由 BF owner 合入自己的 caller 表；本工具不改全局分母和共享报告。
