# 五个精确转换助记符的源码与轻型验证

模型提交 `21418d0b0d4942fae20061ed580ee04aff4a8a61` 只在 `model/extensions/FD/dext_insts.sail` 与 `zfh_insts.sail` 的 assembly 映射新增 20 行，文件 SHA-256 分别为 `1e0397fbc2988383a064a6cfc26f8870464122cd136fc62537e0612ab07ee688`、`f5e7311bc490c2cb728fc8702d0491be263dee0cb822e32648bc33c405f9512e`。五个精确转换 `FCVT_D_S`、`FCVT_D_H`、`FCVT_S_H`、`FCVT_D_W`、`FCVT_D_WU` 的 `RM_RNE` 新增无 RM 参数的规范文本条款；原三条泛化双向映射逐字保留，非零 RM 文本和机器字段没有改。`FCVT_D_L/LU`、`FCVT_S_W` 等可能舍入的转换没有套用无 RM 语法。

五条新条款放在泛化条款之前。它们在这五个 op 的 RM_RNE 正向域与泛化条款重合；Sail 实际 C 正向映射按前条款选择规范文本。反向文本域按有无末尾 `, rm` 区分：无 RM 条款构造固定 `RM_RNE`，原泛化条款仍保留显式 `, rne` 和其他 RM 的解析表达式。Sail 0.20.1 的字符串拼接反向原语 `P_string_append` 原本不可执行；baseline 与新版均不能调用 `assembly(string)` 做运行时反解析。这里签的是映射源码结构和类型检查，**不声称反向动态 PASS**。独立源码审查见[模型审查](../../review/model/assembly-source-review.json)和[验收审查](../../review/acceptance/assembly-source-review.md)。后者独立重跑 ordinary/SYMBOLIC 隔离 C 各 1104 项正向输出，并从实际 Sail 文本核对 GCC/Clang 共 5824 项机器字节；同样没有签反向动态执行。

[隔离红绿探针](probe-final/result.json)从实际两份 Sail 文件抽取映射，并使用测试用 `f0…f31`/`x0…x31` 名称映射（不覆盖生产 ABI/Zfinx 命名）。固定基线 `8ad5e8e` 的映射可类型检查和编译为 C，但首条精确 RNE 期望无 RM 时断言失败；新提交同样通过类型检查与 C 编译，12 个受触及 op 加 `FCVT_S_W` 负对照、六个 RM、五个目标 op 各 32 个源/目的寄存器代表共 **1104/1104** 条真实 Sail 正向输出与预期一致。所有有限字符串比较均完整包含 opcode、寄存器和 RM 后缀；非零 RM 没有被无 RM 前缀吞掉。

[工具链结果](toolchains-attempt2/result.json)只从新版 Sail 探针真实输出中抽 5 个目标 op 和 `D.L/D.LU/S.W` 三个负控，各六个 RM 共 48 条：Clang 48/48 与预期机器字一致；GNU 接受五个无 RM 的 RNE 目标及 18 个负控，共 23 条。GNU 对 25 个目标非零 RM 原助记符真实拒绝；同 25 个 `.insn 4` 精确替代逐一汇编并保留原机器字。GNU 14.2.0、Clang 22.1.8；先前独立 112 次手写语法探针仍保留于 `review/acceptance/exact-conversion-syntax-independent.json`。

普通与 SYMBOLIC 全模块 strict `--just-check` 曾用独立新 memo 在 CPU 7/9 启动。主验证开始统一严格生成后，本轮主动终止以避免竞争；[停止记录](typecheck-attempt1/stopped.json)为 `STOPPED_PARTIAL`，**不计类型检查通过**。正式 ordinary strict、四配置新 IR、实际 IR assembly 顺序及新 JSON 三表示统一由主验证冻结同一提交后签收。旧 `8ad5e8e` 数值定向结果仍只属于旧 IR 的历史证据，不迁为新版 PASS。

可提交的小型证据：本报告、`probe.py`、`toolchains.py`、`probe-final/result.json`、其 baseline/current `cases.json`、`probe-forward.sail`、类型检查/C编译/运行日志、`toolchains-attempt2/result.json`、`typecheck-attempt1/stopped.json`。探针 C 生成物、二进制、memo、尝试期临时变体和最终全树 IR 可重建，不列入本目录提交清单。

## 模型 `e9d69d2` 的重新执行

`e9d69d2f28586c089244c8e37ee4c904c5114458` 相对 `21418d0` 只改 `model/core/ieee_fp_exceptions.sail`；本轮仍从候选源码树重新抽取真实映射，`dext_insts.sail`、`zfh_insts.sail` 的 SHA-256 分别保持 `1e0397fbc2988383a064a6cfc26f8870464122cd136fc62537e0612ab07ee688`、`f5e7311bc490c2cb728fc8702d0491be263dee0cb822e32648bc33c405f9512e`。[新 Sail C 探针](probe-e9d69d2/result.json)的旧基线 RED、新候选正向 **1104/1104**，类型检查与 C 编译均退出 0；反向字符串映射在 Sail 0.20.1 仍不可动态执行，不将其记为 PASS。[新工具链结果](toolchains-e9d69d2/result.json)从这次 Sail 实际输出重取 48 条：Clang 接受并核对 48/48，GNU 接受 23 条；25 条精确目标的非 RNE 显式 RM 被 GNU 拒绝，但 25 条逐一以精确 `.insn 4` 保留机器字。GNU 14.2.0、Clang 22.1.8。

正式输入 `validation/inputs.model-e9d69d2-itrace.json`（SHA-256 `eb830e77f6d31e88574e018ef08e1eb1d5f47f2e9369169d9fd4613877e6973a`）及新 V128 IR `661fd6e443a690f5b1c2a0ccfd1a5b84c908baba5e1b6cea786a1e0696a022ad` 还用于[真实 Make smoke](make-e9d69d2/smoke/result.json)。私有目录的 `solve-FLEQ_S` recipe 实际运行，程序退出 0、3.3 秒、8 条完整 JSON，seed17、定向语义及 GNU/Clang 三表示 48/48 项检查均通过；真实命令、配置和工具哈希见[命令记录](make-e9d69d2/smoke/command.json)。[独立验收审查](../../review/acceptance/modele9-results-review.md)另从实际 Sail 文本核 5824 项机器字节，并复算 Make 的 8 条见证与 48 项工具链结果，已限定签收。Make 只验证固定初态入口，不代替完整 Clause 或全域 assembly 验收。新证据均署候选版本，旧 `21418d0` 记录保持原样。

## 收敛模型 `0f7b8fb` 的重新执行

模型 `0f7b8fbc6724103f91f929ef6918f123df75d6c9` 的候选树干净，五个 strict/IR 生成记录退出 0 且源码未变；本轮重新从该树抽取 assembly 映射，而非将 e9 输出改署新版本。`dext_insts.sail` 与 `zfh_insts.sail` 的哈希仍分别是 `1e0397fbc2988383a064a6cfc26f8870464122cd136fc62537e0612ab07ee688`、`f5e7311bc490c2cb728fc8702d0491be263dee0cb822e32648bc33c405f9512e`。[新 Sail C 探针](probe-converged-20261103/result.json)的旧基线 RED、新候选正向 1104/1104；[新工具链记录](toolchains-converged-20261103/result.json)从新 Sail 文本重抽 48 条，Clang 48/48、GNU 接受 23 条，GNU 对 25 条显式非零 RM 拒绝但 25 条精确 `.insn 4` 均保留目标机器字。Sail 0.20.1 的反向字符串映射仍不可动态执行，未签反向 PASS。

正式输入 `validation/inputs.model-converged-0f7b8fb-itrace.json` SHA-256 `5147af93ecd9cfb5cd6c0607d8073fa997b608dc9993f8c81dee8e739f1e631e` 和新 V128 IR `0fb0897e028803155108ec59f8289d4f89bafa98deb063bfa7f016a3d29f0786` 用于[真实 Make smoke](make-converged-0f7b8fb/smoke/result.json)：私有目录 `solve-FLEQ_S` recipe 退出 0、3.72 秒、生成 8 条完整 JSON，seed17、定向语义与 GNU/Clang 三表示 48/48 均通过。[命令记录](make-converged-0f7b8fb/smoke/command.json)保存正式输入、配置、程序、IR、Z3 与实际命令哈希。Make 结果只适用于这组固定初态，不能替代完整 Clause 预算。[独立验收 Sol](../../review/acceptance/model-converged-results-review.md)已重新执行归档 C，核 1104 条正向文本及实际输出的 5824 项机器字节；另核 48 条原始工具链记录与 Make 的 8 条 JSON、48 项三表示和非目的状态，限定签收本批。
