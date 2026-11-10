# F2/F4/F5 见证输出修复记录

受测源码：`isla/.worktrees/memory-consistency`，起点 `bdd047bc`，本轮未提交、未移动分支。只修改 `src/isarch/target.rs`、`src/isarch/exec.rs` 及两文件内测试；同工作树的 `README.md`、`scripts/run.mk` 和内存实现由其他协作者修改，本轮保留。

## 修改

- F2：RV64/RV32 将 `x1..x31` 列为必输出初态；未约束 GPR 通过原有 complete model 路径，用该路径最终 `Model` 导出。`x0` 不列入。既有 `isa-state` 结构继续供重放前导后恢复寄存器。
- F4：完成路径在取得最终 `Model`、求得初态后，对 `ret_val` 调用 `Model::get_val` 递归具体化，再写普通 `gen`；求值失败记录 incomplete。终值查询超时时仍只把符号返回值写入原有诊断。
- F5：必需访存地址、读取值、写数据和独占写结果求值失败时，记录带字段名及错误类别的 incomplete diagnostic，并沿原有错误计数令 summary 为 partial；不输出普通 `gen`。普通写的 Bool 是非必需字段，查询失败仍允许合法路径。首写自由初值的 `pre-memory: null` 保持原义。初态与汇编门/参数求值错误同样记录 incomplete。

## 验证

统一环境：`CARGO_BUILD_JOBS=4`；`RUSTFLAGS="-L native=$HOME/.local/opt/z3-official-1fd1d3613/lib -C link-arg=-Wl,-rpath,$HOME/.local/opt/z3-official-1fd1d3613/lib"`。以下命令均在 `isla/.worktrees/memory-consistency` 执行。

| 阶段 | 命令 | 结果 |
| --- | --- | --- |
| RED | `cargo test -p isla --lib rv64_target_trait -- --exact` | 新回归测试先于接口实现写入，构建因新增 `concretize_return_value` 等接口缺失退出 101；根级旧 Release 集成 RED 另见 `../red-integration/checks.json`。 |
| GREEN | `cargo test -p isla --lib isarch::exec::tests:: -- --test-threads=4` | 54/54 通过，含异常地址、字段错误、ModelEval 超时注入、原内存重放测试。 |
| GREEN | `cargo test -p isla --lib isarch::target::tests:: -- --test-threads=4` | 33/33 通过，含 RV32/RV64 31 个未约束 GPR 的同模型值测试。 |
| 扩大检查 | `cargo test -p isla --lib --no-fail-fast` | 已编译，但其他协作者正在修改的 `memory_model::tests::预置页表的符号地址读取使用页表初值` 栈溢出，测试进程 SIGABRT；不能计为全量 PASS。 |
| 格式与 diff | `rustfmt --edition 2021 --config skip_children=true src/isarch/exec.rs src/isarch/target.rs`；`git diff --check -- src/isarch/exec.rs src/isarch/target.rs` | 退出 0。为避免格式化并行协作者文件，只格式化本轮两文件。 |

随后一次变量改名使 `ret_val_str` 误落入内层作用域，根级 Release 构建与 lib 测试的首次运行报 E0425。已把具体返回值变量声明移至外层，保留符号字符串仅用于 incomplete 诊断；修正后重跑上述 exec 54/54、target 33/33 均通过。根级首次失败日志应作为历史保留，以后续 v2 构建结果为准。

最终本轮 diff：`exec.rs` +223/-56，`target.rs` +56/-16。尚待根级新 Release 集成复跑与独立 Sol 审阅；这两项结果不能由上述单测替代。

## 独立审阅后的 F5 补充

独立 Sol 指出三个汇编必需字段错误出口只有错误计数、没有 JSON incomplete 条目：汇编名称 `try_get_assembly_name`、编码 `try_get_assembly_encdec`、编码 `FmtVal::from_val`。现均通过 `record_required_field_result` 写入路径签名、实际字段名、符号返回值及错误；原有错误记录和提前退出保留。`Ok(None)` 是正常无解，继续按原行为跳过，不生成错误诊断。编码格式化错误也立即退出该路径。

TDD：先加 `三种必需汇编字段错误有诊断且正常无解不算错误`，`cargo test -p isla --lib 三种必需汇编字段错误有诊断且正常无解不算错误` 因缺少新接口报 E0425（RED）；实现后同命令 1/1 通过。随后 `cargo test -p isla --lib isarch::exec::tests:: -- --test-threads=4` 为 55/55 通过；`rustfmt --edition 2021 --config skip_children=true src/isarch/exec.rs` 与 `git diff --check -- src/isarch/exec.rs` 退出 0。上述 cargo 命令使用前述统一环境。

最终文件 SHA-256：`src/isarch/exec.rs` `ea789317957dfb7ebe27c604df1454732a9b95271cec80c47775b8833c1856da`；`src/isarch/target.rs` `39677e77250dc763089140ce88138465e2ef8a1a06c17aa390b5fd290343cfc9`。前节 diff 数值对应独审前版本；补充后当前 diff 为 `exec.rs` +360/-146、`target.rs` +56/-16。

## 编码守卫回环错误补充

独立 Sol 继续发现 `encdec_guard_roundtrip_ok` 的 `Err(String)` 原先只写日志后退出，未计入 summary，也没有 incomplete 条目。现将错误转换为 `ExecError::Type`，直接复用现有 `record_required_field_result` 写 `test-ins-encdec` incomplete，并由 `ErrorRecorder` 计错；`Ok(false)` 仍按合法的编码守卫过滤处理。未增加只供这一处使用的生产封装。终值模型超时附近旧注释也已改为当前的 diagnostics 合同。

同段已核对：汇编名称/编码无解 `Ok(None)` 和守卫 `Ok(false)` 是正常过滤；三个汇编字段 Err、初态 Err、返回值 Err、访存必需字段 Err 均有 ErrorRecorder 与 incomplete；终值查询超时按既有 `final-model-query-timeout` 诊断；普通写 Bool 为非必需字段。非法编码多样化及终值模型获取错误属于字段求值前的路径错误，已有错误计数，本补丁没有改动其既有诊断结构。

回归先写，RED 因缺少回环错误记录接口报 E0425；实施并按局部规则改为直接复用现有接口后，`cargo test -p isla --lib isarch::exec::tests:: -- --test-threads=4` 为 56/56 通过（11.22 秒），含真实非位向量回环错误、summary partial、incomplete 及 gen 空检查。`rustfmt --edition 2021 --config skip_children=true src/isarch/exec.rs` 与 `git diff --check -- src/isarch/exec.rs src/isarch/target.rs` 退出 0。最终 `src/isarch/exec.rs` SHA-256 为 `2046fb3df706218cad4e7d744b26896059266399541e082009c90ccef33765ff`，`src/isarch/target.rs` 不变；当前 diff 为 `exec.rs` +405/-146、`target.rs` +56/-16。上节文件哈希和 diff 保留为上一轮适用版本。
