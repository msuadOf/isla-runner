# 合流后 IR、构建与永久回归

最终模型为 `bf861b3e687894480aec701a886a38d4e50b8a99`，Isla 为 `4d085b14aa0f987436b86d72f41fab1df9e9a132`。两个子仓工作树干净。模型全量已跟踪文件清单见 [`model_source_manifest.json`](generation/merge-bf861b3e-20261104/model_source_manifest-portable.json)，Isla 生成 IR 以外的 1042 个已跟踪文件清单见 [`isla-source-4d085b14.json`](build/isla-source-4d085b14-portable.json)。最终动态输入账本 [`inputs-4d085b14.json`](build/inputs-4d085b14-portable.json) SHA-256 为 `30f6847f904ea22b8c7dd355cda988bf35bc9938ec46e7b564c408801365d5e2`，固定两提交、两清单、五 IR、配置、程序和官方 Z3。

普通严格检查及四组完整 SYMBOLIC 生成全部退出 0；166 个模型输入、149 个工具/配置文件及实际 Sail/编译期 Z3 进程经过前后哈希审计。五个入口由本轮生成产物安装，RV64 默认与 VLEN128 字节相同。四份配置 sidecar 哈希由 manifest 逐项记录；79 份 workaround、130 个 region、22 个锚点核对通过。细节与独立来源复核见[生成报告](generation/report.md)。

正式 `make -C isla build-isarch ITRACE=1 Z3_TIMEOUT_IMPL=thread_interrupt` 使用独立 `validation/build/target/`，实际启用 `tracetool` 和 `smt-thread-interrupt`，见[构建日志](build/release-4d085b14-portable.log)。最终 Release `isarch` SHA-256 为 `3e44cdd6db67f88f94bc894b5b9c6f1de94b7deeb9eb3d9379c49bec1bafbd3e`；`ldd` 指向官方 Z3 `libz3.so.5.3`，实际库 SHA-256 为 `899cbc70affab963044e975c814fd549a605b5d7bef31b0fd65fb01421bf9970`。编译期 Sail 调用的 Z3 4.16.0 可执行文件单列在生成报告，不能与运行时库混记。

同一最终源码与官方 Z3 下，`cargo test --manifest-path isla/Cargo.toml -p isla-lib --lib --offline --features smt-thread-interrupt,tracetool` **394/394** 通过；`cargo test --manifest-path isla/Cargo.toml --workspace --lib --offline --features smt-thread-interrupt,tracetool` **610/610** 通过；`cargo test --manifest-path isla/Cargo.toml --workspace --tests --offline --features smt-thread-interrupt,tracetool` 含库及集成共 **665/665** 通过。三份实际输出分别见 [`isla-lib`](integration/isla-lib-4d085b14-default.log)、[`workspace --lib`](integration/workspace-lib-4d085b14-default-portable.log)、[`workspace --tests`](integration/workspace-tests-4d085b14-default-portable.log)。不把这些不同测试集合的计数互相替代。

永久 `python3 isla/test/float_ir/run.py --mode all` 父进程退出 0，全部 **26/26** 步退出 0；五 IR 的 helper、state、guard 都在本轮执行，两个 runner 链接同一官方 Z3。见[逐步记录](integration/ir-all-4d085b14/checks-portable.json)和[启动日志](integration/ir-all-4d085b14-launch.log)。新 VLEN128 IR 上独立施加 104 个定向错误变异，永久检查器 **104/104** 拒绝，见[负控结果](integration/negative-104-4d085b14.json)。动态 Clause、315/300 定向数值与 Make/访存证据由同一最终输入账本另行核算；本报告不以静态或库测试替代它们。

实施中保留了失败记录：首次永久入口因两个测试 runner 的 `ISAConfig` 缺四个 memory 字段而构建退出 101；最小兼容各补四个缺省字段后重新通过。先前默认并发的 `isla-lib` 14 项和 `isla` 45 项测试因未显式初始化 SMT 失败；测试模块分别增加显式初始化，独立 fresh 复核后在最终提交的默认并发入口全部通过。旧失败与限制线程通过分别留在 `integration/` 原日志中，不重署最终版本。

精选归档说明：上面 `-portable` 文件仅规范化本机路径前缀，原始命令/输入/日志仍在候选工作区。原件及副本 SHA-256 见[证据清单](../implementation/evidence-selection.json)；报告中的输入和程序哈希均指原件。
