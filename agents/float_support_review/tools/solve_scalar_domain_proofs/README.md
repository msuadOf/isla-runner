# Scalar fle 与固定配置站点证据

certify.py 只消费已有 scalar minimal-evidence 前沿中的 24 个 fle site 和 9 个 fixed-configuration site；不新增分母，也不自行裁定 source arm 不可达。输入是同一冻结候选的模型、Sail library、IR、SharedState sidecar、词法 catalog、fixed CFG 证书与实际 scalar 定向结果。输出两个 FOR_REVIEW JSON。

## 运行

从仓库根目录设置实际冻结路径变量：MODEL_ROOT、SAIL_LIBRARY（sail --dir 下的 lib）、MODEL_MANIFEST、IR_PATH、SOURCE_CATALOG、MINIMAL_EVIDENCE、FD_SIDECAR、FIXED_CFG、SCALAR_RUN_SUMMARY、FROZEN_RUNNER、TARGET_SOURCE。RUN_DIR 应为 isla/target/float-support-review/final-coverage/scalar/domain-proofs/ 下的全新目录。命令：

    CERT_TOOL=agents/float_support_review/tools/solve_scalar_domain_proofs
    mkdir "$RUN_DIR"
    python3 "$CERT_TOOL/certify.py" --model-root "$MODEL_ROOT" \
      --sail-library "$SAIL_LIBRARY" --model-manifest "$MODEL_MANIFEST" \
      --ir "$IR_PATH" --catalog "$SOURCE_CATALOG" --minimal "$MINIMAL_EVIDENCE" \
      --sidecar "$FD_SIDECAR" --fixed-cfg "$FIXED_CFG" \
      --run-summary "$SCALAR_RUN_SUMMARY" --frozen-runner "$FROZEN_RUNNER" \
      --target-source "$TARGET_SOURCE" --out-dir "$RUN_DIR"

本轮最终 1dcc 输入的精确 argv、脚本/输入/输出 SHA-256 和退出码见忽略目录 isla/target/float-support-review/final-coverage/scalar/domain-proofs/run-20260926T173221Z/provenance.json。

## 核验范围

- fle-closure.json 逐源码 SHA 与 UTF-8 byte offset 核 24 个 site 都在 H/S/D 的真实 fle 定义内；十二个旧 fle 调用全部落在顶层条件编译的普通后端 $else clause，十二个 SYMBOLIC clause 各有一个纯 helper 调用。随后对实际 SharedState sidecar 的 zexecute Call/source_loc 逐项对应，并检查全体编译函数与从 zexecute 出发的 Call 图无 zfle 定义或调用。该证据仅适用于绑定的 SYMBOLIC IR；普通后端仍保留旧 fle 数值体。
- fixed-nine-premises.json 逐 site 保存源码位置和配置/CFG 前提：真正的 header 中 zxlen=64、IR 中唯一 zxlen global let 初始化、sidecar 全指令无 zxlen destination；fixed CFG 证书中 Ext_F=true 与 Ext_Zdinx=false；validDoubleRegs 的 Zdinx 短路与 rF_or_X_D/wF_or_X_D 的外层 F 选择有实际 PC 和调用链接。它还逐个复核 8 组、4871 个 scalar 定向结果的 R1 SAT 入口，非 Target 初态键仅为 misa，引用冻结 runner 源码/entry contract。validDoubleRegs 外层 false 臂有实际意义，不能把三项概括为“整个函数不可达”。

最终的 arm 适用域、调用上下文和是否移出动态覆盖义务由架构与 coverage owner 审定；本工具输出的 FOR_REVIEW 状态不等于闭合。

## FCLASS 与 D move 的追加 8 项

prove_fclass_move.py 消费同一 IR、manifest、完整 FD sidecar、冻结 Sail library，并绑定 scalar typed caller 工件和上述 fixed-nine-premises.json。它只处理当前精确前沿的三个 FCLASS caller 各两项，以及两个 D move assert；输出仍为 FOR_REVIEW。运行时另设 TYPED_ARTIFACT、FIXED_NINE、FCLASS_RUN_DIR 为实际路径：

    mkdir "$FCLASS_RUN_DIR"
    python3 "$CERT_TOOL/prove_fclass_move.py" --sail-library "$SAIL_LIBRARY" \
      --model-root "$MODEL_ROOT" --model-manifest "$MODEL_MANIFEST" \
      --ir "$IR_PATH" --sidecar "$FD_SIDECAR" --typed "$TYPED_ARTIFACT" \
      --fixed-nine "$FIXED_NINE" --out-dir "$FCLASS_RUN_DIR"

FCLASS 核对实际 zfloat_classify 的六个 Sail library 谓词及 assert handler CFG，再对 f16/f32/f64 的全部符号 exponent/mantissa 求解六类“恰有一类”的反例；三份 SMT 都须 UNSAT。D move 核对 xlen/flen 两个 64 位 let 的实际初始化和不可写、两处 xlen>=64 且 flen>=64 的编译数据流、短路与 assert handler。输入 runner 的 R1 域仍需与具体调用关联，本文不单独宣称八项 arm 已关闭。

最终 1dcc 的精确命令、输入/工具/SMT/输出 SHA-256 和 Z3 版本见忽略目录 isla/target/float-support-review/final-coverage/scalar/domain-proofs/fclass-move-20260926T185706Z/provenance.json。D move 校验额外要求真臂从第一个比较直达 flen 比较、合并临时值只有短路 false 与 flen 比较两处定义，最终 assert 条件仅有一处定义；避免仅凭源码公式忽略生成 CFG 的支配关系。
