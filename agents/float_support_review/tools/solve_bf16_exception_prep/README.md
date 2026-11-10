# BF16 异常方向证据准备

`prepare.py` 为旧 `1dcc`、默认 FD 配置中 `currentlyEnabled` 的 40 项异常合同准备独立审查输入。它读取真实 runtime 全指令目录，从完整 Call 图保守计算 `have_exception` 的写效应，未知外部调用保持可能写；只有实际异常 flag 检查可裁减 caller CFG。8 个 BF literal root 均需证明入口 flag 为 false。

随后对两种 BF 扩展、各 16 个 FS/VS 状态重新运行已审解释器，记录所有递归 callee 的完整正常返回路径。新候选还绑定冻结 runtime 的新帧初始化、顶层 let 覆盖边界、实际 getter 和原语别名。此前的 `bf-vector-control-domains.json` 只证明 32 项 LHS；其结论没有扩展到本目录的异常合同。

产物 `isla/target/float-support-review/final-coverage/bf16/exception-prep/exception40-candidates.json` 的状态为 `FOR_INDEPENDENT_REVIEW`，SHA-256 为 `7a2ac14a2b5ad7ac602eb853a87ab7f97060112e0c317413594432c55f6d98c9`。4 项测试核对异常检查裁边、撤销检查、未知 external 和 flag 引用逃逸；测试通过不替代 runtime 原语保持、完整状态域和正常求值的独立审查。

```sh
python3 -m unittest discover -s agents/float_support_review/tools/solve_bf16_exception_prep -p 'test_*.py' -v
python3 agents/float_support_review/tools/solve_bf16_exception_prep/prepare.py \
  --contracts "$CONTRACTS" --sidecar "$SIDECAR" --snapshot "$SNAPSHOT" \
  --state-certificate "$STATE_CERTIFICATE" --phase-purity "$PHASE_PURITY" \
  --output "$NEW_OUTPUT"
```

输出必须使用新文件名。异常出口和正常 Bool 方向分别计数；候选未独审前不扣前沿，也不增加动态命中。新 IR 必须重新核 caller、实际参数、SSA/CFG 和初始化来源。

独审现已接受旧 `1dcc/default` 的列定 40 项条件异常排除：`bf16/independent-exception40-review/certificate.json`（相对上述 `final-coverage/`），SHA-256 为 `d1c5a8dce959dcdae6db68c28373c11607b27c00dcd60cb7a90ebe4e81046e8b`。独立审查采用更保守的调用写效应上界，额外 170 个函数按可能写处理后，8 个 root 入口仍只有 false；32 个 FS/VS 投影、764 个完整递归调用均重新核对。该证书包含 8 项测试和 6 个实际负控，全部前提由 BF16 消费账保留。历史候选不改标签；新 `56cc69` 必须重新证明。
