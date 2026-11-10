# 按实际 caller 排除 overlap 大小关系分支

2026-09-27，继续使用 `1dcc8081…` 冻结 IR、`aa069e7f…` actual SharedState 和 `28fb65ee…` 源快照。工具为 [overlap_arguments.py](overlap_arguments.py)，摘要为 [overlap-evidence.json](overlap-evidence.json)。不读取新 live 模型，不修改原31项 `report.json`。

## 结果与范围

**14个实际调用点通过；6项负控均拒绝。** 其中非BF向量9个调用点，BF16五个调用点。共证明BF16 **14个 caller×direction**、非BF向量 **26个 caller×direction** 在指定调用上下文内不可达。全局仅涉及既有 `valid_reg_overlap` 的两个 if site；helper 的全局分母及可达分支不删除。

| 实际 `zexecute` Call PC | clause | 两个 EMUL 实参 | 静态排除 |
| --- | --- | --- | --- |
| 51189 | VFNCVTBF16_F_F_W | `(LMUL+1, LMUL)` | helper pc75 true；pc78 false |
| 51403 | VFWCVTBF16_F_F_V | `(LMUL, LMUL+1)` | helper pc75 false；pc78 true/false |
| 51620、51629 | VFWMACCBF16_VV | `(LMUL, LMUL+1)` | 每个调用点分别排除上述三个方向 |
| 51898 | VFWMACCBF16_VF | `(LMUL, LMUL+1)` | 上述三个方向 |
| 27398 | VFNUNARY0 | `(LMUL+1, LMUL)` | pc75 true；pc78 false |
| 24940、24949 | FWVVTYPE | `(LMUL, LMUL+1)` | 每个调用点 pc75 false；pc78 true/false |
| 25230、25239 | FWVVMATYPE | `(LMUL, LMUL+1)` | 同上 |
| 25539、26435、30271、30546 | FWVTYPE、VFWUNARY0、FWVFTYPE、FWVFMATYPE | `(LMUL, LMUL+1)` | 每个调用点分别排除同组三个方向 |

## 证明链

1. actual `get_lmul_pow` 从 `vtype` 调用 `_get_Vtype_vlmul`；后者实际取 `[2..0]` 三位，再由 `sail_signed` 解释。证明使用保守范围 `[-4,3]`；实际正常返回的 assert 还排除 -4，不依赖这项收窄。
2. 每个调用点的第三、第四实参沿 actual Assign/Primop 逐级追溯至**同一个** `get_lmul_pow` Call。每项定义都必须唯一，并用 CFG 删除定义节点后的可达性检查确认其支配 use。不能凭源码变量名猜测实参身份。
3. 仅允许整数转换和 `add_int`；得到精确仿射式 `LMUL` 与 `LMUL+1`。所有 `i64→int`、`int→i64` 转换逐项记录范围；`LMUL+1∈[-3,4]`，没有机器整数溢出。两种顺序分别得到 `rs−rd=-1/+1`。
4. actual helper pc74 是 `lt(EMUL_pow_rs,EMUL_pow_rd)`，结果直接供 pc75 Jump；pc77 是 `gt`，结果直接供 pc78 Jump。形参在 helper 内不被改写。CFG 证明 pc78 只可能在 pc75 false 后到达，所以加宽调用不能进入 pc78 的任一方向。
5. 负控覆盖增量改0、实参交换、getter替换、helper比较替换、Jump极性反转和绕过 getter 定义。全部必须拒绝。

这是**条件于实际调用点已进入**的参数关系证明，不代替动态 caller 到达见证，也不把静态排除记为动态命中。LMUL、mask、VL 的具体测试值无需固定；在同一 typed IR 下，配置变化可改变调用是否进入，但不能改变本证书已核的两个局部实参之间的关系。

## 产物与复跑

产物为 `isla/target/float-support-review/final-coverage/vector/independent-predicate-review/overlap-arguments.json`。字段 `scope` 固定 phase、根 Call PC、callee；`excluded_helper_directions` 只能与相同 caller 的义务匹配。

沿用 [31项说明](README.md) 中的冻结目录变量：

```sh
python3 agents/float_support_review/tools/solve_vector_coverage/independent_predicate_review/overlap_arguments.py \
  --sidecar "$SIDECAR_STAGE/official-fd.jsonl" \
  --model-root "$IR_STAGE/model" \
  --manifest "$IR_STAGE/source-manifest.json" \
  --output isla/target/float-support-review/final-coverage/vector/independent-predicate-review/overlap-arguments.json
```

冻结执行 exit0：`caller_count=14, V_caller_count=9, BF_caller_count=5, BF_excluded_caller_directions=14, V_excluded_caller_directions=26`。早先交流中的“非BF11个调用”已由 actual Call 全枚举修订为9个，没有加入整数或 crypto 调用点。
