# 向量数值调用域证据准备

本目录产出候选，最终排除由独立审阅者核定后再由向量前沿消费。结果位模式、实际动态见证、源类型约束和当前 IR 的 CFG 证据分别保存。

## 扩宽与标量输入的类型合同

`prepare_widening_contracts.py` 读取版本一致的源码、成功生成记录、实际 runtime 目录、固定 CFG、前沿和已独审的 decoder 宽度域。输出保留原义务与当版 PC，并增加函数、arm、clause、phase、root 源表达式身份。后续 IR 必须重新定位源 site、实际 Call、SSA 和 CFG；若分支已不再生成，登记为 `not_lowered`。

旧 `1dcc` 的历史候选分三类：

- 25 项数值 helper 的 16 位臂：候选沿唯一支配赋值链识别 `fp_widen_pure` tuple 的数值字段，其成功生成的 Sail 类型为 `m∈{16,32}`、结果 `bits(2*m)`。候选曾尝试以同一调用的 `m` 依赖类型关联其余实参；此理由未获独审签收，不能作为排除依据。
- 9 项 `get_scalar_fp` 断言失败：实际 FLEN 为 64，实际第二实参沿已核 SSA 链来自本 phase 的 `get_sew`，对应 decoder 宽度域不超过 64。
- 3 项 widening caller 的 `get_scalar_fp` 64 位臂：上述实际参数链结合各自 decoder 的 SEW `{16,32}` 域。

现行独审 `vector/independent-numeric-width-review/widening-getscalar-review.json`（相对 `isla/target/float-support-review/final-coverage/`）逐项接受 37 个精确原义务，SHA-256 为 `d130e1cebfa66aacce678cf287cff31aca6ce2ede45351e227dcd572dd783877`。它重新核对实际 SEW、每个实参来源、caller SSA、嵌套调用、转换返回 32/64、negate 切片拼接和 `read_vreg` 的 `2*SEW`，并明确 `same_m_contract_used=false`。某实参仍为未知时，保留未知，只用已证实际实参及具体 dispatch 条件排除相应方向。173 项完整 CFG 支配检查及 7 项语义负控通过。

独审结论限定旧 `1dcc`、默认 FD 配置及已列 root。合法 decoder、同 phase 的 vtype 不变、内部 flag 和 root 可到达等前提分别保留。任意直接构造 helper 输入不满足相同前提；不迁用于新 IR。

```sh
python3 agents/float_support_review/tools/solve_vector_numeric_review/prepare_widening_contracts.py \
  --frontier "$FRONTIER" --sidecar "$SIDECAR" --fixed-cfg "$FIXED_CFG" \
  --ir "$IR" --snapshot "$SNAPSHOT" --generation "$GENERATION" \
  --domain-certificate "$DOMAIN_CERTIFICATE" \
  --reviewed-domain-sha256 "$DOMAIN_CERTIFICATE_SHA" --output "$NEW_OUTPUT"
```

重封模型另显式提供 `--runtime-manifest` 与 `--source-bridge`。参数桥接不能替代新 decoder 域、源类型或 helper CFG 的重新审查。输出必须使用新的文件名。

`test_widening_origin.py` 核对真实 tuple payload 来源，并拒绝 flags 字段、绕过定义的路径和多个定义。当前四项测试通过。历史候选 v1/v2 保留原字节和候选标签；向量前沿只按现行独审的 `accepted_exclusions[].original_obligation` 精确消费，不以候选总数直接扣账。

## 既有估计指令证据

`prepare_estimates.py` 生成独立 oracle 绑定的定向输入。`prepare_widths.py` 和 `prepare_estimate_contracts.py` 分别准备固定格式、CLZ/索引及 wrapper 返回合同。旧 `1dcc` 的 24 项格式排除和 21 项合同排除已有独审证书；新 IR 必须按自己的源码、调用域和实际目录重新验证。

## 新 56cc 的实际元素数见证

`prepare_num32_witnesses.py` 从列定八个 widening/narrowing clause 的已有输入生成独立补充包，设 SEW16、LMUL4、VL0，得到实际 `num_elem=32`。因此同一输入可观察 `num_elem <= 16` 的 false 和 `num_elem <= 64` 的 true；VL0 保持无活动 lane 的预期状态。准备本身不算执行通过。

```sh
python3 agents/float_support_review/tools/solve_vector_numeric_review/prepare_num32_witnesses.py \
  --baseline "$BASELINE_INPUTS" --frontier "$OLD_FRONTIER" \
  --config "$FD_CONFIG" --snapshot "$MODEL_STAGE" --output "$NEW_INPUT_DIR"

python3 agents/float_support_review/tools/solve_vector_numeric_review/bind_num32_witnesses.py \
  --old-frontier "$OLD_FRONTIER" --old-catalog "$OLD_CATALOG" \
  --catalog "$NEW_CATALOG" --sidecar "$NEW_SIDECAR" --snapshot "$MODEL_STAGE" \
  --generation "$GENERATION" --runtime-manifest "$RUNTIME_MANIFEST" \
  --source-bridge "$SOURCE_BRIDGE_V3" --audit "$NUM32_STRICT_AUDIT" \
  --output "$NEW_CANDIDATE_FILE"
```

先用集成 runner 实际执行输入，再用新版 vector 严格审计生成 `NUM32_STRICT_AUDIT`。绑定器重新验证 v3 来源桥接、完整实际目录、source lowering、root 源表达式和连续 Call 链；旧义务只用于确定需要核对的问题，不用旧 PC 查找新见证。

本轮 8 例、24 终态均通过。[独审证书](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/independent-num32-70-review/certificate.json)（SHA `d1f687d0e0898fff2846115541bba2232b2789c36719dfb182e21fdd730edaec`）核对 35 个实际 root、两条条件的 70 个方向，以及完整 Call/续体、actual num32 和 vtype 无写。向量 owner 已将其精确消费至[新版账本](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/new-ir-observed-num32-70-ledger.json)（SHA `750af71054550ebdf66b0f411fe88108a4d46063ef18570106de6961c78f573e`），9 个消费篡改负控通过。该结论仅适用新 `56cc/default/Machine` 的列定输入和 root；旧 `1dcc` 账本不回填。

## 新 slide 与 FS 短路候选

`bind_remaining17_witnesses.py` 消费 slide 2 例和 conversion FS-off 6 例的新版严格审计，重新绑定 2 个 slide 方向与 15 个 FS 短路 LHS 方向。utils 文件虽已变化，对应 conversion 函数的完整源码正文保持相同；绑定按函数内 token 位置、源表达式、实际 SSA 与 CFG 进行。

```sh
python3 agents/float_support_review/tools/solve_vector_numeric_review/bind_remaining17_witnesses.py \
  --old-frontier "$OLD_FRONTIER" --old-catalog "$OLD_CATALOG" --old-model "$OLD_MODEL" \
  --catalog "$NEW_CATALOG" --sidecar "$NEW_SIDECAR" --snapshot "$MODEL_STAGE" \
  --generation "$GENERATION" --runtime-manifest "$RUNTIME_MANIFEST" \
  --source-bridge "$SOURCE_BRIDGE_V3" --audit-slide "$SLIDE_STRICT_AUDIT" \
  --audit-fs "$FS_STRICT_AUDIT" --output "$NEW_CANDIDATE_DIR"
```

当前[17 项候选](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/slide-fs17-rebinding/candidates.json)（SHA `889f9102ac8355aca19c46b4e9717dfcf50f229a8ec61893d1e2f6d60d2378be`）均有新版精确见证，随后通过[独立复审](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/independent-bf-slide-fs20-review/slide-fs17-certificate.json)（SHA `8c9550a46937a85c8116c05af1546b40b42b3cfe56bcdf1c655113d54de2d675`）。向量 owner 已将精确 17 项纳入[新版主账本 v2](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/vector/source-root-ledger-v2/index.json)，与 num32 的 70 项合为 87 个已独审观察方向；其余主账本仍待审／待证，旧版 87 项待证前沿保持独立。它不证明短路 RHS 或异常出口闭合。上述向量输入与 BF16 overlap 3 例合计 19 例、45 终态，见[单列严格索引](../../../../isla/target/float-support-review/final-coverage/integration/p1-56cc69/increment-strict-index.json)；不重复并入 9583 主批。
