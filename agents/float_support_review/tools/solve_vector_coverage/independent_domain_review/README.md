# 默认 V 的 typed 整数域独审

承接既有最终覆盖议题，独占本目录和 `isla/target/float-support-review/final-coverage/vector/independent-domain-review/`。生产源码、V owner 工具及共享报告只读。

输入是固定 `actionable-default-frontier.json` 的 P2：1737 个精确 root 引用、45 个谓词。目标是分别给出可复验静态排除与仍需 caller 证明或真实 witness 的余项；不改 14095 候选分母，也不扩大到默认 2967 的其它任务。

步骤：

1. 核 1dcc IR、aa069 sidecar、实际 R1 源码、输入表及 source token；保持 clause、phase、config、root Call、site、runtime PC、taken、successor。
2. 先核 getter 的 R1 域、没有 `vtype` 写入的阶段调用闭包，以及固定 Zve32x 能力。保留 canonical vill 的低位零及 SEW8；不使用 BF16 的 SEW16 绑定。
3. 沿唯一且支配使用点的实际定义恢复各 root 的整数实参，分别处理常数 LMUL0、扩宽 SEW×2/LMUL+1、归约 seed 与不同 helper 形参顺序。
4. 只有精确 guard Call 及失败返回路径确实支配 root 时才收窄其后域；`get_num_elem` 在 guard 前的项目保留前置域。
5. 用实际 helper CFG 和有限实参上界域解释目标边。未知值保持未知、分支双向展开；未闭合项继续保留。
6. 保存负控、完整命令、版本哈希和阶段结果，由 V owner 严格消费。

未决问题：实际合法的未观测分支需要最小输入；局部 type match、宽窄转换 enum 和其它 120 个未完成 lowering 的 site 属原 owner 的独立前沿。

## 最终复验（冻结 1dcc / aa069）

`isla/target/float-support-review/final-coverage/vector/independent-domain-review/` 保存完整证据。`certificate.json` 的 SHA256 为 `96703cb72cf9ec8ef88e6263262636f1afb99357bdc0c97ef6fa49fb0af23269`；`run-pass.json` 记录退出码 0、88.755 秒和空 stderr。1737 项身份与输入一一对应，1667 项静态排除，70 项保留；8 项负控通过。

70 项均为 35 个 root 下 `assert_vector_num_elem_upto_128` 的 PC4 false→5 和 PC9 true→25。`remaining-count-70.json` 仅提供 SEW、LMUL 指数与倍率的输入候选；完整指令 witness 由 coverage owner 实测。这里不据未命中排除，也不宣称全局覆盖闭合。

实际译码 CFG 给普通 FP 的 SEW 域 `{16,32,64}`、扩宽域 `{16,32}`、VFWUNARY0/VFNUNARY0 域 `{8,16,32}`。归约的 `vstart=0` 绑定实际 `assert_vstart(0)`；寄存器对齐绑定实际同寄存器和 EMUL 的支配 guard。每个 root 的 `integer_arguments` 和 `decoder_width_proof` 可供其它审计引用，消费方须重新绑定自己的实际 SSA、入口及配置。

```sh
python3 agents/float_support_review/tools/solve_vector_coverage/independent_domain_review/audit.py \
  --freeze "$FREEZE" \
  --sidecar "$SIDECAR" \
  --input isla/target/float-support-review/final-coverage/vector/actionable-default-frontier.json \
  --fixed isla/target/float-support-review/final-coverage/vector/default-fixed-cfg.json \
  --bf_certificate isla/target/float-support-review/final-coverage/bf16/independent-typed-domain-review/certificate.json \
  --output isla/target/float-support-review/final-coverage/vector/independent-domain-review
```

`FREEZE` 与 `SIDECAR` 必须分别提供冻结模型目录和实际 aa069 sidecar；脚本严格验证版本哈希。
