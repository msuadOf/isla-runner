# 最终浮点 IR 安装核对

目标模型是 `.worktree/sail-riscv-float-converged-20261103` 的 `0f7b8fbc6724103f91f929ef6918f123df75d6c9`；旧 `runner-float/sail-riscv` 的 `21418d0` 不作为来源。生成批次是 `agents/float_review_closure_20261102/validation/generation/model-converged-0f7b8fb`。

[最小安装脚本](install_final_ir.py)默认只读核对，须显式传 `--install` 才把四配置 IR 安装到根 Isla 的五个路径，并更新 `ir/provenance/manifest.json`。它核对模型 HEAD/clean、166个已跟踪模型文件、149个工具文件、普通严格检查、四份生成记录/配置/IR 哈希，以及模型工作树中79份 workaround 的132个 region、22个注释锚点。候选 provenance 保留原 schema1 和四 artifact 结构，更新精确模型提交、来源工作树、实际 Sail 可执行/launcher、插件、166个模型文件、配置和IR哈希；通过生成审计的路径与SHA指向149个工具文件证据。`rv64d.ir` 与 `ir/rv64d_v128_e64.ir` 从同一产物复制。

先行[安装前结果](preflight.json)为 PASS、`installed=false`；最终模型独审签收后，[安装结果](installed.json)为 `installed=true`，根 Isla 五份 IR 与[候选 manifest](candidate-manifest.json) 逐字节匹配。已安装 `ir/provenance/manifest.json` SHA256 `6caab4ef6b1a2b95b2e78691dc6b23e6acecca708fca41f4f036834c866a7093`。四组 IR SHA256：V128/默认 `0fb0897e028803155108ec59f8289d4f89bafa98deb063bfa7f016a3d29f0786`，RV32 `e17c4fe18552f8ce219b35f846c4c1a2c530dcad0ac9fc8f10d0da2604c3fa4e`，V256 `47ba73418d6dcb1b1e86db7680ce4df9508e7885a02096e25e213c2c3b2c05e1`，V512 `2bdea17d36c64545254f50cc5a6902e570a1fea682de3f7c062bf641a85a62a9`。79份 workaround 的旧 IR 基准哈希均告警；按 `specs/ir-workflow.md`，单纯新 IR 哈希不要求修改配置，region与注释锚点已核对通过。

安装依据为独立 Sol 的 `agents/float_review_closure_20261102/baseline-0008fae/converged-source-review-20261103.*`、`converged-provenance-review-20261103.*` 与 `converged-ir-review-20261103.*` 的 PASS 签收。安装仅改变根 Isla 五份 IR 与 provenance；根 Isla 中其他 owner 的四个测试文件改动保留。`runner-float/isla` 仍干净，未参与安装。`git diff --check` 对六个安装路径通过。

永久回归在独立 `validation/integration/target` 中先以官方 Z3 RUSTFLAGS、CPU80、jobs1 离线构建 debug runner，耗时3m00s，target约790 MiB；没有复制共享的16 GiB debug target。[预构建日志](runner-prebuild.log)和[两程序哈希及链接](float-ir-all-summary.json)已记录。随后执行真实入口：

```sh
cd isla
z3_lib="$HOME/.local/opt/z3-official-1fd1d3613/lib"
taskset -c 80 env CARGO_BUILD_JOBS=1 CARGO_NET_OFFLINE=true \
  CARGO_TARGET_DIR="$(pwd)/../agents/float_review_closure_20261102/validation/integration/target" \
  RUSTFLAGS="-L native=$z3_lib -C link-arg=-Wl,-rpath,$z3_lib" \
  python3 test/float_ir/run.py --mode all \
  --output ../agents/float_review_closure_20261102/validation/integration/float-ir-all-0f7b8fb
```

父进程退出0，[逐步记录](float-ir-all-0f7b8fb/checks.json) **26/26 exit0**，包括构建、五项静态检查、五IR的helper包装与数值回归、state和guard。RV64默认/V128/V256/V512各327条旧 SoftFloat 对照，RV32按实际接口307条；各helper日志末行均 PASS。[完整输出](float-ir-all-launch.log)与各步日志位于 `float-ir-all-0f7b8fb/`。两个debug runner的`ldd`均解析到官方`libz3.so.5.3`，真实库SHA256 `899cbc70affab963044e975c814fd549a605b5d7bef31b0fd65fb01421bf9970`。`cargo fmt --check`退出0；未重跑280项Rust全库单测。动态完整Clause预算不由本回归代替。

官方 Z3 Rust 回归核验：当前 `42000be` 的 `isla-lib/src/smt.rs` 与既有枚举独审文件 SHA256 同为 `aa3cb973102299707fc2d87c94369136daed8b88944e47b48ff3ee9e9ec1f9cc`。既有官方库 Release 测试程序 SHA256 `1ebb556f1c09b669f83701c23afec98b6ad6dee746e47fded6010d5bf7422209`，本轮以 CPU99/单线程复跑 `smt::tests::` **23/23 PASS**，见[日志](rust-smt-42000be.log)；`ldd` 指向官方 `libz3.so.5.3`。枚举全库280/280与独审29项为此前同源码哈希的历史结果，本轮未重跑全库。
