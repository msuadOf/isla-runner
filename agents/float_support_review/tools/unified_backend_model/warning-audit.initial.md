# 统一浮点后端生成日志的 warning 审计

日期：2026-09-27。范围：只读检查现有双模式 strict、Sail→IR、首次 C++ 失败和 v7 恢复构建日志；没有为展示 warning 重跑完整生成。逐项日志路径、SHA-256、编译选项及机器可读结论见 [warning-audit.json](warning-audit.json)。本轮 Sail 模型由 v7 `source-manifest.json` SHA-256 `7e945fbace1f28fdf86ff94744100311a97db31576cebaba2d2b141fb1502093` 绑定；IR 生成记录退出0，IR SHA-256 `348147f833432008d559be0e673dbd45982148b0750cd4533c68589a55aac061`。v7 C++ 恢复日志结尾为 `Built target sail_riscv_sim`；该日志中没有编译器 `warning:`、`error:` 或 `runtime error:` 行。

| 类别 | 当前记录 | 旧版本对照与判断 |
| --- | --- | --- |
| Sail 显式 effect 注解弃用 | `core/regs.sail:277` 的 `get_X_bits ... effect {rreg}`；v7 配置、首次 Sail→CPP、两模式 strict 可见 | 旧 `bf16-cpp-p2/build.log` 与布局改动前日志已有同一类别；该文件 SHA-256 `913197b8efb5382b0ccb17979268ba57a34524b3462763fc2833c014be59db55` 未变。生成规则为 Sail `parser.mly:180`。 |
| Sail 不完整 match | SYMBOLIC strict 中 `vext_arith_insts.sail` 的 1472 `encdec_nreg_forwards`、1511 `vmvr_layout_backwards`、2022 `vext_vs1_backwards`、2062 `vext_layout_backwards` | 与统一后端改动前 `decoder-layout-negate/layout-typecheck.symbolic.log` **逐字相同**，两日志 SHA-256 均为 `9d13b2605c51a806d5e36618791ec2e5b096a55b93883ad895fa0af6d4fcb45b`。源文件 SHA-256 `144c38f3d6fe8854ca2cc9c133165ae08c48dd76fb89181781c091bb29c70d23` 未在统一后端包中改变；生成规则见 Sail `pattern_completeness.ml:1012,1030`。普通 strict 没有这四条可见提示。 |
| `23 warnings have been suppressed` | 首次 Sail→CPP、IR、两模式 strict 均出现该计数；v7 恢复编译复用了已生成的 C++ 源，所以该份编译日志没有再次输出 Sail 计数 | 旧 BF16 C++ 构建及布局改动前两模式 strict 也显示23。Sail `reporting.ml:290–331` 只对重复的 `once_from` 调用增加该计数；它不是23个不同类别的清单。现有日志不能逐条展开或判定这23次的具体内容，故**不将它们标为全部无害**。可触发 `once_from` 的旧规则还包括其它 deprecated 语法及重复类型声明。 |
| CMake 策略弃用 | `cmake-configure-v7.log` 显示根 `CMakeLists.txt:12` 的 CMP0135 `OLD` 策略提示 | 旧 `bf16-cpp-p2/configure.log` 已有同一提示；该根文件 SHA-256 `cfc93a5692133ec4cfca6bff8f3ed86d5f5bb80113cf0fbb3bcd133350922a3` 未变。 |
| C/C++ 编译器诊断 | `cpp-build-v7.log` 对 SoftFloat、生成模型、主/宽/额外 adapter 及模拟器的完整恢复编译，报告的 warning 数为0 | 这是**当前编译选项下的零报告**。首次 v6 日志中的 `platform.h` 缺失是 fatal error，已由 v7 恢复20个 Git 跟踪的上游平台源码解决，不能归类为旧 warning。 |

编译命令实际对新 adapter 启用 `-Wall -Wextra -Wno-sign-compare`；生成模型还启用 `-Wno-extra -Wno-unused -Wno-uninitialized`。本轮命令没有 `-Wconversion` 或 sanitizer 标志。因而零编译器 warning 不证明不存在隐式转换、未初始化使用或未定义行为。后续若出现类型、转换、溢出、移位、未初始化或 sanitizer 诊断，须按受测源、具体选项、ABI 与旧日志逐项核对；不能只凭退出码0验收。

Sail patched 工具链的 `reporting.ml`、`parser.mly`、`pattern_completeness.ml` 和 `type_env.ml` 与 P0 隔离源码对应文件 SHA-256 相同；本审计依据这些规则解释日志计数，不把 IR 日志中只有汇总行的23次强行分配给某个具体 warning。日志原件保留在 `isla/target/float-solve-evidence/unified-backend-build/model-p1-v6-20260927/`，旧对照在 `isla/target/float-solve-evidence/bf16-cpp-p2/` 和 `isla/target/float-solve-evidence/decoder-layout-negate/`。
