# BF16 架构证书生成器

这三份工具从冻结的模型源码、IR、SharedState 运行目录与词法 catalog 生成静态证书。它们不运行指令、不证明动态 edge 覆盖。主证书核 13 个短路因子的 25 个 lowering、8 个 assert handler、3 个固定能力和 4 个 foreach；Wma 证书枚举 5 个抽象 Bool 输入；overlap 证书核局部 helper 的返回链与具体反例。各自的证明前提和限制以证书内 status、scope、limitations 为准。

## 输入和命令

每个输入都必须来自同一待审候选。先将以下 shell 变量设为实际冻结文件：IR_PATH、MODEL_MANIFEST、RUNTIME_MANIFEST、MODEL_ROOT、BF_CATALOG、VECTOR_CATALOG、SIDECAR。MODEL_ROOT 是 Sail-RISC-V model 的冻结副本；两个 manifest 可相同，但来自独立冻结时必须分别给出。SIDECAR 是完整 official-fd.jsonl；BF_CATALOG 是 BF16 source-catalog.json，VECTOR_CATALOG 是 vector source-branch-catalog JSON。从冻结清单填入 BF_CATALOG_SHA、VECTOR_CATALOG_SHA、SIDECAR_SHA 三个预期 SHA-256，而非根据输入临时改写预期。OVERLAP_RUNTIME 可由下述提取器从已核 SHA 的完整 sidecar 导出。

以下命令从仓库根目录执行。RUN_DIR 须是 isla/target/float-solve-evidence/architecture-certificates/ 下的全新唯一目录；已有证书文件会被拒绝。

    CERT_TOOL=agents/float_support_review/tools/solve_architecture_certificates
    RUN_DIR=isla/target/float-solve-evidence/architecture-certificates/run-unique
    mkdir "$RUN_DIR"
    OVERLAP_RUNTIME="$RUN_DIR/overlap-runtime.json"
    python3 "$CERT_TOOL/extract_overlap_runtime.py" --sidecar "$SIDECAR" \
      --runtime-sha256 "$SIDECAR_SHA" --output "$OVERLAP_RUNTIME"
    OVERLAP_SHA=$(sha256sum "$OVERLAP_RUNTIME" | cut -d ' ' -f1)
    python3 "$CERT_TOOL/certify.py" --ir "$IR_PATH" \
      --model-manifest "$MODEL_MANIFEST" --runtime-manifest "$RUNTIME_MANIFEST" \
      --model-root "$MODEL_ROOT" --catalog "$BF_CATALOG" --catalog-sha256 "$BF_CATALOG_SHA" \
      --sidecar "$SIDECAR" --runtime-sha256 "$SIDECAR_SHA" --output-dir "$RUN_DIR"
    python3 "$CERT_TOOL/certify_wma_enabled.py" --ir "$IR_PATH" \
      --model-manifest "$MODEL_MANIFEST" --runtime-manifest "$RUNTIME_MANIFEST" \
      --model-root "$MODEL_ROOT" --catalog "$BF_CATALOG" --catalog-sha256 "$BF_CATALOG_SHA" \
      --sidecar "$SIDECAR" --runtime-sha256 "$SIDECAR_SHA" --output-dir "$RUN_DIR"
    python3 "$CERT_TOOL/certify_overlap.py" --ir "$IR_PATH" \
      --model-manifest "$MODEL_MANIFEST" --runtime-manifest "$RUNTIME_MANIFEST" \
      --model-root "$MODEL_ROOT" --catalog "$VECTOR_CATALOG" --catalog-sha256 "$VECTOR_CATALOG_SHA" \
      --sidecar "$SIDECAR" --runtime-sha256 "$SIDECAR_SHA" \
      --overlap-runtime "$OVERLAP_RUNTIME" --overlap-runtime-sha256 "$OVERLAP_SHA" \
      --output-dir "$RUN_DIR"

旧 c5 复现输入的 IR SHA-256 为 c5cbb0bbdaa9369b669aa7330531bfb1a0cf1ef7d905b071f14f510d10c7385c；model/runtime manifest 同为 128d59a5661c3efdba566682c58ee6733f4799d9afd19fa3c6a542d24d95f346；BF_CATALOG_SHA 为 31ce9e417869d335a7443ca1eec428cb69ca0327dd76211cf4a737269192e3fc；VECTOR_CATALOG_SHA 为 fc3117925577ff161252b6f9e65ed59dee3f131a3e85ebb89b07a455dbc3d805；SIDECAR_SHA 为 e3c25cee39a7c2618a0cffafc3185a319b676798d853a2c7376227f22fa5bb29；OVERLAP_SHA 为 94b122eaa249081725a4165f58af6c820b689a0d96521c8e4422871e74a4d640。它们只标识旧输入，不能作为新候选的期望哈希。

## Schema 和绑定边界

- certificate.json 保留历史 schema bf16-p2-independent-lowering-polarity-v1；名称中的 p2 是原 schema 名，不代替 runtime_header 中的实际 IR、配置和初始化事实。factors、asserts、capability_exclusions、loops 与旧 c5 语义相同；新增 relocation_audit 记录每个 site 的 token 候选数和经原 CFG 断言筛选后的唯一候选数。
- wma-enabled-certificate.json 的 schema 是 bf16-wma-last-zfbfmin-implication-v1；truth_table_over_abstract_inputs 枚举 32 个输入赋值。其 enabled_witness_rule 只描述末项调用的上下文义务，不虚构末项 RHS Jump。
- overlap-certificate.json 的 schema 是 valid-reg-overlap-final-factor-v1。当前 vector catalog schema 仅有逐源码 source_sha256，没有 catalog 自身的 IR 或 manifest 字段；工具将全部 source SHA 与 model manifest 和实际 model-root 逐文件核对，以 runtime header 对实际 IR/runtime manifest，并要求派生 overlap-runtime 的 header、names 与全部 145 条 helper rows 逐项等于完整 sidecar。不能从 catalog 虚构不存在的 IR 字段。
- 三份证书记录 catalog、完整 sidecar、两个 manifest、实际源码的哈希或 header，以及 tool_sha256 中的入口脚本和 inputs.py 哈希。预期 catalog/sidecar SHA 错误在读取证书算法前拒绝；输入字节或证书输出路径变化须重跑。证书中的固定旧 PC 与极性断言继续作为结构门槛；新 IR 若改变 CFG，失败就是待重定位，不得仅平移 PC 或改期望以取得 PASS。Wma 和 overlap 目前尤其保留旧 PC 全断言。

旧 c5 参数化复现和负控位于忽略目录 isla/target/float-solve-evidence/architecture-certificates/ 中。这里保留完整错误输出与更改前后输入哈希；旧归档证书原字节未改。

最终候选 IR SHA-256 为 1dcc80812b8beaba49abaebf605e8090c2796b5930aefa36635b478c5f2b8180，model/runtime manifest SHA-256 为 28fb65ee77e2c5e5c629c50b239a2e009337b47936b2fdbb897bf9c11bca055e，BF_CATALOG_SHA 为 1b39fded03901551ed62f35758ce41549a725fecac2f4b96dea68506f480db9f，VECTOR_CATALOG_SHA 为 a8755acda37e27b62819e861fd730657442126bd657ef078e4c3d68cf5cb3f46，SIDECAR_SHA 为 aa069e7f2232b70990763073a2c4c58f73ca2f91c368e6edec284dc9e5acfc60。三证书和精确 argv/输入 SHA 清单位于 isla/target/float-solve-evidence/architecture-certificates/final-20260926T160822Z/；三脚本在相同实际 SharedState 下退出 0。该结果是上述静态证书，不替代动态 edge 和终态关联。
