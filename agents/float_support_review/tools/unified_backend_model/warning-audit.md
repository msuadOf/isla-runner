# 统一浮点后端生成日志的 warning 审计

日期：2026-09-27。范围：只读检查现有双模式 strict、Sail→IR、首次 C++ 失败和 v7 恢复构建日志；没有为展示 warning 重跑完整生成。逐项日志路径、SHA-256、编译选项及机器可读结论见 [warning-audit.json](warning-audit.json)。本轮 Sail 模型由 v7 `source-manifest.json` SHA-256 `7e945fbace1f28fdf86ff94744100311a97db31576cebaba2d2b141fb1502093` 绑定；IR 生成记录退出0，IR SHA-256 `348147f833432008d559be0e673dbd45982148b0750cd4533c68589a55aac061`。v7 C++ 恢复日志结尾为 `Built target sail_riscv_sim`；该日志中没有编译器 `warning:`、`error:` 或 `runtime error:` 行。

## 23 项抑制提示的后续展开

此前只读日志无法逐项列出23次抑制，原记录保留在 [初版审计](warning-audit.initial.md)和[初版机器清单](warning-audit.initial.json)。根据后续要求，已在**同一冻结v7模型**上，用经 `--help` 核实支持 `--all-warnings` 的P0隔离Sail，仅运行普通和 `-D SYMBOLIC` 两次 `--just-check` 严格类型检查；均退出0。完整 argv、工作目录、工具/源码/配置SHA和日志哈希见[展开运行记录](../../../../isla/target/float-solve-evidence/unified-backend-model/20260927-warning-all/run.json)及[逐条位置清单](../../../../isla/target/float-solve-evidence/unified-backend-model/20260927-warning-all/warning-expansion.json)。**没有重生IR或C++。**

普通模式实际打印24条 `Deprecated`，解释文本全部为“Explicit effect annotations are deprecated”，没有其它类别或抑制汇总；这恰好展开了原普通日志的**1条可见+23条抑制**。SYMBOLIC模式打印同样24条 effect 提示，另有下表的四条不完整match提示，共28条，也没有抑制汇总。24处来源为：

| 冻结源码 | 行号 | 条数 | 与旧BF16源码 |
| --- | --- | ---: | --- |
| `model/core/regs.sail` | 277、279、290、292、303、307、311、313 | 8 | SHA-256 `913197b8efb5382b0ccb17979268ba57a34524b3462763fc2833c014be59db55`，逐字相同 |
| `model/extensions/FD/fdext_regs.sail` | 251、260、271、282、293、297、301、307 | 8 | SHA-256 `5cc769261a4716a4238c3446a36bbba9692a5ac74fe2a9615ca0c3d5eb5c1fa2`，逐字相同 |
| `model/extensions/V/vext_regs.sail` | 231、235、241、251、261、265、269、275 | 8 | SHA-256 `6682f5ce387359c4d5a6873cf877e2f001231b4f38917b8721c89cdfd81f17d9`，逐字相同 |

普通展开日志SHA-256为`f1e725694053a802acd6bab15c5063cf5479ef6ea93ff58ab9049c66fe4bf13c`；SYMBOLIC展开日志为`b00f4986b2afd7a39aa7bf3f990fc88cfd02f2d8c28c6976742b6dcf9273c201`。这个结果闭合**严格类型检查**中的23次重复提示，并以相同源、相同计数和Sail `once_from`规则解释生成日志中的汇总。由于未对完整IR/CPP生成运行`--all-warnings`，不声称独立展开了那些进程的每次后续诊断；编译器warning及UB边界仍按下文另行审计。

| 类别 | 当前记录 | 旧版本对照与判断 |
| --- | --- | --- |
| Sail 显式 effect 注解弃用 | `core/regs.sail:277` 的 `get_X_bits ... effect {rreg}`；v7 配置、首次 Sail→CPP、两模式 strict 可见 | 旧 `bf16-cpp-p2/build.log` 与布局改动前日志已有同一类别；该文件 SHA-256 `913197b8efb5382b0ccb17979268ba57a34524b3462763fc2833c014be59db55` 未变。生成规则为 Sail `parser.mly:180`。 |
| Sail 不完整 match | SYMBOLIC strict 中 `vext_arith_insts.sail` 的 1472 `encdec_nreg_forwards`、1511 `vmvr_layout_backwards`、2022 `vext_vs1_backwards`、2062 `vext_layout_backwards` | 与统一后端改动前 `decoder-layout-negate/layout-typecheck.symbolic.log` **逐字相同**，两日志 SHA-256 均为 `9d13b2605c51a806d5e36618791ec2e5b096a55b93883ad895fa0af6d4fcb45b`。源文件 SHA-256 `144c38f3d6fe8854ca2cc9c133165ae08c48dd76fb89181781c091bb29c70d23` 未在统一后端包中改变；生成规则见 Sail `pattern_completeness.ml:1012,1030`。普通 strict 没有这四条可见提示。 |
| `23 warnings have been suppressed` | 首次 Sail→CPP、IR、两模式默认 strict 均出现该计数；v7 恢复编译复用了已生成的 C++ 源 | 两次严格类型检查用`--all-warnings`展开后，普通为24条、SYMBOLIC为24条相同的effect弃用提示加四条partial-match；三份effect来源与旧BF16源码逐字相同。生成进程没有单独用`--all-warnings`重跑；其后续阶段的warning仍须按原日志和具体编译诊断审查。 |
| CMake 策略弃用 | `cmake-configure-v7.log` 显示根 `CMakeLists.txt:12` 的 CMP0135 `OLD` 策略提示 | 旧 `bf16-cpp-p2/configure.log` 已有同一提示；该根文件 SHA-256 `cfc93a5692133ec4cfca6bff8f3ed86d5f5bb80113cf0fbb3bcd133350922a3` 未变。 |
| C/C++ 编译器诊断 | `cpp-build-v7.log` 对 SoftFloat、生成模型、主/宽/额外 adapter 及模拟器的完整恢复编译，报告的 warning 数为0 | 这是**当前编译选项下的零报告**。首次 v6 日志中的 `platform.h` 缺失是 fatal error，已由 v7 恢复20个 Git 跟踪的上游平台源码解决，不能归类为旧 warning。 |

编译命令实际对新 adapter 启用 `-Wall -Wextra -Wno-sign-compare`；生成模型还启用 `-Wno-extra -Wno-unused -Wno-uninitialized`。本轮命令没有 `-Wconversion` 或 sanitizer 标志。因而零编译器 warning 不证明不存在隐式转换、未初始化使用或未定义行为。后续若出现类型、转换、溢出、移位、未初始化或 sanitizer 诊断，须按受测源、具体选项、ABI 与旧日志逐项核对；不能只凭退出码0验收。

Sail patched 工具链的 `reporting.ml`、`parser.mly`、`pattern_completeness.ml` 和 `type_env.ml` 与 P0 隔离源码对应文件 SHA-256 相同；`reporting.ml:290–331` 只对重复的 `once_from` 调用增加抑制计数。日志原件保留在 `isla/target/float-solve-evidence/unified-backend-build/model-p1-v6-20260927/`，旧对照在 `isla/target/float-solve-evidence/bf16-cpp-p2/` 和 `isla/target/float-solve-evidence/decoder-layout-negate/`。
