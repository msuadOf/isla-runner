# BF16 当前 V4 调用集成

`integration.py` 重算 `56cc69/default` 下四个实际 BF16 execute root 经 `illegal_fp_variable_width` 到 `valid_fp_op`、`valid_rd_mask` 的八个 callee-instance 合同。当前[候选](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/bf16/v4-value-integration/candidate.json) SHA `05cbe2e91bd567b80adb617703b00c4312d4289d91312625f2ef6375f87284c0`，待独立审查。

以下为首次生成时的历史命令；当前依赖复核使用末尾的显式重定位入口。

```sh
python3 -m unittest discover \
  -s agents/float_support_review/tools/solve_bf16_value_domain -p 'test_*.py'
python3 agents/float_support_review/tools/solve_bf16_value_domain/integration.py \
  --output "$NEW_OUTPUT_DIR/candidate.json"
```

工具使用冻结快照及依赖哈希，重执行 v3 来源验证。六项测试先红后绿，包含返回比较操作数、constructor 解包来源、聚合否定和 caller 极性的变异，以及 `vsew` 保留域的四个异常出口。输出路径拒绝覆盖。

证明内容：

- 从当前 `zexecute` 的实际 BF16 SourceLoc 和 constructor `Kind` 重新发现四个 root；校验同一 `Unwrap` 的 typed 字段、完整 SSA、`fcsr[7:5]` 和 helper 参数转发。
- `get_sew` 从全部八个 `vsew` 值重算：四个正常值为 8、16、32、64，其余四个 `AssertionFailure` 保留。未使用 root 后的 `SEW == 16` 断言。
- 重建两个 helper 的完整返回表达式，并联立既有 V4 组件和 full IR 独审。组件旧路径指向的 runtime 文件在指定冻结 runtime 快照中按相同 SHA 核验。
- 解释实际 `illegal_fp_variable_width` 的 16 组正常 Bool 返回组合；核对 root 返回真值通过 SSA 和 Jump 触发 `Illegal_Instruction`。返回 false 只意味着继续 caller 的剩余检查。
- 列出当前入口至 root 的完整前序调用闭包、体系寄存器和显式 let 写入检查及原语列表，供独审核对 runtime 效果。未借用 decoder/encoder 完整闭包纯读结论。

旧 40 个控制义务仅多对一链接这八个实际调用合同。严格 Bool 中间值没有新增分支，不增加真假覆盖臂；候选不增加动态命中、全源码排除或可达分母。`source_branch_closed=false`。

## 后续正式独审

[独审报告](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/bf16/independent-v4-call-integration-review/review.json) SHA `e833094953c48d18a14194ebbf04c8422f825e8fd51563450c5553c24a9e7e2f` 已签 `PASS_SCOPED`，提供八项可消费的 `accepted_contracts`。独立重算包含 8 个 `vsew`、64 个 mask 组合、32 个 FP 参数组合、16 个聚合 Bool 组合，以及 caller 的正常与异常路径。13 项测试含 11 项有效变异负控通过，126 个依赖无漂移。

独审另核当前前序闭包及两 helper 的 12 函数、479 指令，无体系状态或隐式异常 scratch 写入；此局部效果证明不扩展到完整 phase。BF owner 负责把八个正式合同及旧 40 项迁移关系精确消费到新版本账本。首段“待独审”为候选提交时状态，候选原字节保留。

后续[严格消费账本](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/bf16/v4-value-integration-reviewed-v1.json) SHA `d2c7c72c368f258155319c792876a292526342abeebf753963c4565392bdd16b` 已接入八个限定域合同，当前八项 pending 为 0。40 条历史链接均标记为 `legacy_transformation_discharged`，新增分支、动态命中、全源码排除均为 0。逐项七个前提和独审限制完整保留，十项消费器测试通过。

## 历史模型路径的同字节重定位

后续源码工作改变了活动工作树的 `sail-riscv/model/extensions/V/vext_fp_insts.sail`。原组件证书中 15 个模型引用采用活动工作树路径；原始候选和工具保持原字节及原 locator 检查，因此原六项测试的首次 PASS 只对应当时绑定状态。

`rehouse_dependencies.py` 为全部 15 个历史模型 locator 指定冻结快照中的唯一位置，再核同一 SHA 和 source manifest 键。未列文件继续在原位置核 SHA。126 个历史引用合并为 124 个物理文件；八个合同 ID、全部语义内容、40 条历史链接及原证书均未改变。

```sh
python3 -m unittest discover \
  -s agents/float_support_review/tools/solve_bf16_value_domain \
  -p 'test_rehouse_dependencies.py'
python3 agents/float_support_review/tools/solve_bf16_value_domain/rehouse_dependencies.py \
  --output "$NEW_OUTPUT_DIR/dependency-relocation-candidate.json"
```

四项新测试先红后绿，覆盖冻结字节变化、manifest 不符及路径越界。[候选](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/bf16/v4-value-integration/dependency-relocation-candidate.json) SHA `84e15597a4c07347d6346dc6847f9ff41f3a71cdcf49b9714958a744d43bbc1b` 已获[同字节定位独审](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/bf16/independent-v4-call-integration-review/dependency-relocation-review.json)许可，证书 SHA `94d0eb196cfa46affc1c219d5517b746569bbf5a52ad96059850230c47ab9b65`。该附证只修正依赖定位，不增加语义许可，也不改变冻结 `56cc` 模型的适用范围。

当前严格消费入口为[账本 v2](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/bf16/v4-value-integration-reviewed-v2.json)，SHA `af52904b2f6c96d2b88bb849c8677ef7eb99f4c9808b2d935b1a20024d8e3f04`。v1 的 134 个验证 locator 明确解析并合并为 132 个物理文件，全部复核通过；除依赖表与新增重定位元数据，其余顶层字段与 v1 逐项相等。新消费器十项测试通过，八项合同的语义、前提和计数保持不变。
