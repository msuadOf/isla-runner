# Isla `42000be` Release isarch 冻结

## 2026-11-02 轨迹 feature 修正：正式长跑改用新程序

首批完整 Clause harness 还传入 `--itrace=output/trace/itrace_<Clause>.txt`。原 `isarch-42000be-interrupt` 只启用 `smt-thread-interrupt`，未启用 `itrace`/`tracetool`；旧批次已启动的 14 项均在入口退出 1、没有 JSON，各自 `run.log` 原文为“当前构建未启用轨迹支持，请启用 itrace/ftrace/btrace feature”。旧结果保存在 `agents/float_review_closure_20261102/validation/runs/float-closure-8ad5e8e-42000be-20261102/`，不计为 Clause 验收，也没有覆盖或删除。下文原先将旧 interrupt 程序列为正式候选的结论仅适用于发现本缺口之前；新正式批次须另封输入并使用本节程序。

新冻结程序为[isarch-42000be-interrupt-itrace](isarch-42000be-interrupt-itrace)，SHA256 `acda0dceb259205fe0c43a3785484ffcafbef26b3194de3b9f67ad38eccbcf7d`，不覆盖前两个程序或清单。[新机器清单](manifest-interrupt-itrace.json)、[构建日志](build-isarch-42000be-interrupt-itrace.log)、[isarch 指纹](fingerprint-isarch-interrupt-itrace.json)与[isla-lib 指纹](fingerprint-isla-lib-interrupt-itrace.json)记录两个 crate 均启用 `default,itrace,smt-thread-interrupt,tracetool`。构建基点仍为 `42000be`，`smt.rs` SHA256 仍为 `aa3cb973102299707fc2d87c94369136daed8b88944e47b48ff3ee9e9ec1f9cc`。根 `isla/` 构建检出有他人未跟踪的 `test/float_ir/check_float_closure_branches.py`，跟踪文件无修改；相同 HEAD 和 `smt.rs` 哈希的 `.worktree/runner-float/isla` 完全干净。此来源边界已写入新清单，未触碰该脚本。

新构建使用独立 `enum/target`、CPU99（同胞 CPU35 预检空闲）、jobs1 和相同官方 Z3 RUSTFLAGS，退出 0、Release 构建 1m58s。完整命令见新机器清单；相对下文旧构建，CPU 改为 99，feature 参数改为 `--features 'smt-thread-interrupt,itrace'`。[ldd](ldd-interrupt-itrace.txt)、[动态段](readelf-interrupt-itrace.txt)及[实际装载日志](runtime-loader-interrupt-itrace.log)均指向官方 `libz3.so.5.3`，真实库 SHA256 `899cbc70affab963044e975c814fd549a605b5d7bef31b0fd65fb01421bf9970`。

按 `agents/float_review_closure_20261102/validation/run_clause.py` 的完整命令参数和 seed17 预加载器实际运行 `FLEQ_S`，不是 `--help` 或 dry-run：[命令](smoke-FLEQ_S-interrupt-itrace/command.json)、[结果](smoke-FLEQ_S-interrupt-itrace/result.json)、[运行日志](smoke-FLEQ_S-interrupt-itrace/run.log)。CPU99，16.687s，退出 0，生成 1 份结构完整的 JSON、48 条退休见证，summary 为 `finished` 且所有 partial/error 计数为 0；[itrace](smoke-FLEQ_S-interrupt-itrace/output/trace/itrace_FLEQ_S.txt) 非空，共 17,956,369 字节，seed17 拦截有效。此启动门只证明该 Clause 与这套完整参数可运行，不替代新批次 77 项及单次 SMT watchdog 的独立验收；watchdog 复核另见[新程序独审证据](../../review/enum/watchdog-itrace-result.json)。

## 正式长跑程序

当时按 `--smt-timeout 7200s` 选定的旧程序为[isarch-42000be-interrupt](isarch-42000be-interrupt)，SHA256 `fe4bdcebd1d970d6f026c0f81ccd22f807f5cb4729da27ef67e20b2c08d09d80`。与它对应的[机器清单](manifest-interrupt.json)、[构建日志](build-isarch-42000be-interrupt.log)、[Cargo feature 指纹](fingerprint-isarch-interrupt.json)及[isla-lib feature 指纹](fingerprint-isla-lib-interrupt.json)均保留。二者的 feature 均为 `default,smt-thread-interrupt`；该版本未满足 harness 的 itrace 要求。源码 `isla` HEAD `42000be47596ec088623881d03c0eadc5cf0ba27`，当时工作树干净，`isla/isla-lib/src/smt.rs` SHA256 `aa3cb973102299707fc2d87c94369136daed8b88944e47b48ff3ee9e9ec1f9cc`，与枚举独审一致。

从 `isla/` 执行的等价可重放命令如下。实际构建把 `$ROOT` 展开为当前根目录，把 `$Z3_LIB` 展开为本机官方库目录；独立 `enum/target` 为上轮已用 reflink 复制的 Release 缓存，不覆盖正式 `isarch`。

```sh
ROOT="$(pwd)/.."
Z3_LIB="$HOME/.local/opt/z3-official-1fd1d3613/lib"
taskset -c 114 env CARGO_BUILD_JOBS=1 \
  CARGO_TARGET_DIR="$ROOT/agents/float_review_closure_20261102/enum/target" \
  RUSTFLAGS="-L native=$Z3_LIB -C link-arg=-Wl,-rpath,$Z3_LIB" \
  cargo build --release --bin isarch --features smt-thread-interrupt
```

构建在 CPU114、同胞 CPU50 空闲时进行，退出 0，Release 构建日志末行记录 2m10s。`ldd` 指向官方 `libz3.so.5.3`，[动态段](readelf-interrupt.txt)包含对应 RUNPATH；清空 `LD_PRELOAD` 与 `LD_LIBRARY_PATH` 后，`LD_DEBUG=libs` 运行冻结程序 `--help` 退出 0，实际装载官方库，见[装载日志](runtime-loader-interrupt.log)。库真实文件 SHA256 `899cbc70affab963044e975c814fd549a605b5d7bef31b0fd65fb01421bf9970`，与上轮正式库一致。[ldd 输出](ldd-interrupt.txt)单独保存。

## 默认 feature 对照与历史口径

先按上一轮正式构建的默认 feature（本仓定义为空）生成并保存[默认版](isarch-42000be-default)，SHA256 `4230545803dd57535a3741b294c576b81b2e9c65a417e51fb3e539d9d36c1c30`；其[机器清单](manifest-default.json)、[构建日志](build-isarch-42000be-default.log)、[Cargo feature 指纹](fingerprint-isarch-default.json)及[isla-lib feature 指纹](fingerprint-isla-lib-default.json)分别保存。此版本不用于带单次 SMT 超时要求的正式长跑。

旧 `agents/encoding_constraint_isolation_20261102/binary-selective-ready.json` 明确记录默认 feature，而本轮 `validation/run_clause.py` 和旧诊断命令均带 `--smt-timeout 7200s`。源码 `isla/isla-lib/src/smt/z3_timeout.rs` 的无 `smt-thread-interrupt` 分支直接执行 Z3 调用；参数可被接受，但不会启动单次 operation watchdog。`timeout_error` 中无 feature 时的 panic 只针对已经返回中断错误的分支，不能说传入 `--smt-timeout` 就会 panic。历史完整 Clause 的外层运行时间、JSON 和结果仍按其原始命令解释；先前“每次 SMT 均有 7200s 中断限制”的说法不适用于默认 feature 程序，须以新版本重新验证，不能静默继承 PASS。

本轮只构建和冻结程序，没有修改生产源码或重跑全库单测；枚举修复的既有单测与独审结果见 `agents/float_review_closure_20261102/enum/report.md` 和 `agents/float_review_closure_20261102/review/enum/report.md`。
