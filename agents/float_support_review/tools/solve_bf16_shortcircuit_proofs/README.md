# BF16 共享 V 短路机械审查包

certify.py 只处理 BF16 owner 冻结 root 表的 22 个 V helper 短路 site 与 1 个 overlap if：236 个按 BF caller 展开的义务。它核实际 Sail token、1dcc SharedState Jump/Call、LHS 定义、短路常量、RHS 正常返回写入和已知异常出口；witness 再逐个与同配置 compact edge 关联。输出状态固定为 FOR_REVIEW，不能据此宣布 73 个 pending 项排除或全量 source branch PASS。

## 重跑

在仓库根目录设置 ROOT_TABLE、IR_PATH、MODEL_MANIFEST、MODEL_ROOT、VECTOR_CATALOG、FD_SIDECAR、SHORT_CANDIDATES、SHORT_CFG、TYPED_371、IF_REVIEW、COMPACT_EDGES 为同一冻结候选的实际路径。RUN_DIR 须为 isla/target/float-support-review/final-coverage/bf16/shortcircuit-proofs/ 下全新目录。然后执行：

    TOOL_DIR=agents/float_support_review/tools/solve_bf16_shortcircuit_proofs
    mkdir "$RUN_DIR"
    python3 "$TOOL_DIR/certify.py" --root "$ROOT_TABLE" --ir "$IR_PATH" \
      --model-manifest "$MODEL_MANIFEST" --model-root "$MODEL_ROOT" \
      --catalog "$VECTOR_CATALOG" --sidecar "$FD_SIDECAR" \
      --candidates "$SHORT_CANDIDATES" --cfg "$SHORT_CFG" \
      --typed "$TYPED_371" --if-review "$IF_REVIEW" \
      --edges "$COMPACT_EDGES" --out-dir "$RUN_DIR"
    mkdir "$RUN_DIR/negative-controls"
    python3 "$TOOL_DIR/negative_controls.py" \
      --provenance "$RUN_DIR/provenance.json" \
      --out-dir "$RUN_DIR/negative-controls"

provenance.json 在正向命令退出后由冻结流程记录正向 argv、全部输入/工具/输出哈希；负控脚本从它重用相同输入，将独立 root 表副本的源码 token、arm 极性或 witness context 各改一处，并要求三项均拒绝且不写证书。最终 1dcc 的实际命令与输入 SHA 位于忽略目录 isla/target/float-support-review/final-coverage/bf16/shortcircuit-proofs/final-20260926T194900Z/provenance.json；完整 pending73.tsv 位于同目录，三项通过的负控结果位于其 negative-controls-v2/negative-results.json。正向审查 JSON 的 SHA-256 为 3c384dcc135e3778c08f47b5122c328240eb745448bcfab4451302cdf7594dba，负控结果的 SHA-256 为 320c01df9aa581317b874305423b962a3fd5004e3a9f3971e5c9f33f51069121。

## 审查边界

- 每个短路 site 的 jump true/false 方向、skip Bool 与 RHS 入口按真实 & 或 | 核对。两臂 CFG 独立遍历至 join；每条正常路径须恰写一次结果，异常路径只按已核的 terminal PC/类型保留，绝不伪装成 Bool 返回臂。
- BF root 中 145 个短路 actual witness 和 10 个 overlap-if actual witness 仅按实际 edge、case 和 call context 关联。overlap-if 的谓词/体独审仍由已绑定的 independent-predicate-review/report.json 承担。本包不搬用 V 其它 caller 的见证。
- 8 个 fixed CFG 候选只携带原表前提。73 个 pending 项在 JSON 和 TSV 中逐条保留 source site、arm、BF root Call 的阶段/实参 AST/条款；既有 371 typed 证书没有相同 root 键，所以它们仍需新实参域证明或真实见证，由架构与 coverage owner 裁定。
