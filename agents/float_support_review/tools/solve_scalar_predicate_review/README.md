# 56cc 标量谓词及正常 guard 域独审

本工具只读冻结的 56cc 源、IR、四配置实际 runtime sidecar、标量源码目录与严格 trace audit。写入位置只限调用者指定的新证书文件，以及负控新目录。它不修改 producer 候选，也不判定全量源码分支闭合。

在仓库根目录设置 `SCALAR_ROOT` 为 `isla/target/float-support-review/final-coverage/integration/p1-56cc69/scalar`，`MODEL_ROOT`、`MODEL_MANIFEST`、`IR` 为同一个冻结 56cc 候选的实际路径，`RUNTIME_INDEX` 为同版 `runtime-catalogs/index.json`。证书输出必须是尚不存在的文件：

```sh
python3 agents/float_support_review/tools/solve_scalar_predicate_review/review.py \
  --root "$SCALAR_ROOT" --model-root "$MODEL_ROOT" \
  --manifest "$MODEL_MANIFEST" --ir "$IR" \
  --runtime-index "$RUNTIME_INDEX" \
  --out "$SCALAR_ROOT/independent-predicate-normal-domain-review/new-review.json"

mkdir "$SCALAR_ROOT/independent-predicate-normal-domain-review/new-negative-controls"
python3 agents/float_support_review/tools/solve_scalar_predicate_review/negative_controls.py \
  --root "$SCALAR_ROOT" --model-root "$MODEL_ROOT" \
  --manifest "$MODEL_MANIFEST" --ir "$IR" \
  --runtime-index "$RUNTIME_INDEX" \
  --positive "$SCALAR_ROOT/independent-predicate-normal-domain-review/new-review.json" \
  --out-dir "$SCALAR_ROOT/independent-predicate-normal-domain-review/new-negative-controls"
```

现行证书是 `independent-predicate-normal-domain-review/review-final-v6.json`，SHA-256 `c0eeb1af084bc1617b6e80c596478667061872fd8765ff22ee96f8f8cda96def`；四项负控结果是同目录 `negative-controls-v6/negative-results.json`，SHA-256 `5a660a1dd7293e127b5998d706528d023685cbf41fb2bf805c48cf70033469ff`。证书逐臂保留正常状态索引、实际见证布尔值与 privilege 集合，以便下游按配置/phase/site 精确消费。

独审核对 19 个语义谓词的完整 Bool 真值表、15 项能力常量的实际完整路径、四个任意 64 位 getter 投影，以及 `validDoubleRegs` 的正常 true 返回和形参无读写。每配置重新计算 64 个布尔状态上的 224 个 phase guard 与 120 个短路因子的条件域；每个真值表行按实际 PC、SSA、Jump 后继与短路常量重放。异常出口逐一保留为 `Arbitrary`。1,772 个见证引用逐项核对到 15 份已哈希严格 trace audit 中相同的 function/PC/taken/successor、case、phase、context；不跨配置或 privilege 借用。

证书只适用于精确 guard 已进入、各调用正常完成、MISA 为本配置值、XLEN/FLEN 为 64 且求值期间相关状态原子稳定的域。异常、正式入口关系、完整 decoder 拒绝和全 77 项求解不在此证书结论内。`source_branch_closed` 保持 `false`。
