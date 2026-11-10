# catalog 提交局部修补（2026-10-03）

**2026-10-05 后继修订**：现为`ef4ea1d`，解耦输出模式，并将共享前缀与浮点使用的接口移出提交；本文保留8545e7c阶段记录，现行见[边界收缩](catalog-boundary-20261005.md)。

## 目标与范围

用户要求通过 amend 收缩 `323021b943c413a4a17ce879040eb260f9138a50`，以其父提交 `b18d6b7` 的代码思路为基准，避免改造原有执行流程。重点是 `isla/src/isarch/exec.rs`；catalog、trace 关联的配套接口按必要性核对。不把浮点实现、IR、脚本或后续挂起修复混入 catalog 提交。

## 步骤与验证

1. 保存 HEAD、index、工作区补丁及受影响文件快照；独立目录验证精确提交候选。
2. 确认终态账本的保留范围，再以原代码为底稿做必要增量，先调整行为回归测试。
3. 验证 collector、catalog/itrace 与执行器定向测试、默认配置编译、格式；通过 make solve 的限定目标做 smoke，明确不等同全量验收。
4. 将同一修订分别应用于提交、暂存和工作区三个版本；核对其他文件及暂存层次保持。
5. 独立 index amend；记录新提交、命令、结果及限制，同步状态与发现。

## 实施结果

已 amend 为 `8545e7c77e502a693d153a7a5867f87d7b5a2e39`，父提交仍为 `b18d6b7`。原 `323021b` 的结构恢复结论只表示保留了控制流骨架，不能据此认定其符合局部修补要求；本轮实际撤销穿插在回调中的终态账本。

- `exec.rs` 生产区相对父提交只有四处局部增量：JSON 路径签名字段、构造参数、绑定 runtime catalog、构造用例时传入已有签名。生产区由父提交 1012 行变为 1022 行（+13/-3）；原 catalog 提交为 1175 行。
- 恢复原 `submit_itrace` 闭包、早退位置、错误处理、排序实现、注释及 `should_collect_unfinished_path`。不增加终态管理模块或包装回调。
- 撤销 JSON 的 `summary`、`terminals`、`case-id` 和 trace 的终态元数据接口；通过原 trace 提交函数携带已有路径签名，JSON `path-signature` 对应 trace `path_signature`。签名可能碰撞，不作为唯一 ID，也不证明覆盖完整性。
- catalog、实际 Jump 边、紧凑输出和不可变前缀共享保留。执行域抽样标记仍是原有库接口，工作区的 mapping/target 校验继续使用。
- 原浮点、完整 pre/post 状态、IR、脚本和挂起修复保持在原暂存/未暂存层。因撤销 summary，工作区新增的域说明改放 JSON 顶层 `state-domain`；它仍未进入 catalog 提交。浮点见证选择、model completion、编码上下文调整仍属于原未提交增量，不代表本轮已重新设计这些行为。
- 独立 index 只写本次候选；其他 index 条目及其他已修改文件逐字节核对保持。HEAD、index、工作树分别与已验证候选/暂存组合/完整组合一致。未 push，未提交父仓库 gitlink。

## 验证

证据目录：`isla/target/catalog-local-patch-20261003/`。三份源码目录为 `candidate/`、`staged/`、`worktree/`，共用工作区 `isla/target` 构建缓存。每条 cargo 测试/检查外限 180 秒，测试串行；测试通过不等于全部指令验收。

| 版本与命令 | 结果 |
| --- | --- |
| 原 HEAD：`cargo test --offline -q -p isla --lib --features itrace,smt-thread-interrupt collector_preserves -- --test-threads=1` | 3 通过，`baseline-collector.log` |
| 原实现＋新 schema 断言：同上 | 1 通过、2 按预期失败于账本字段仍存在，`red-collector.log` |
| 候选：`cargo test --offline -q -p isla --lib --bin isarch --features itrace,smt-thread-interrupt -- --test-threads=1 --skip isarch::target::tests::rv64_target_trait` | 64 库＋24 bin 通过；过滤既有 x0 失败，`candidate-tests.log` |
| 暂存／完整组合：同上 | 82＋24／83＋24 通过，`staged-tests.log`、`worktree-tests.log` |
| 候选／完整组合：`cargo test --offline -q -p isla-lib --lib --features itrace,smt-thread-interrupt executor:: -- --test-threads=1` | 83／84 通过；后者包含未提交 panic 传播修复 |
| 候选／完整组合：上条过滤改为 `tracetool::itrace::` | 各 57 通过 |
| 候选默认 features：`cargo test --offline -q -p isla --lib collector_preserves -- --test-threads=1`；`cargo check --offline -q -p isla --bin isarch` | 均通过，逐命令退出码见 `checks.json` |
| 三份源码 `cargo fmt --all` 后 `cargo fmt --all -- --check` | 通过 |
| 候选：`make solve ALL=MRET THREADS=1 ITRACE=1`（离线构建，整命令外限 300 秒，保留原 solve 运行超时） | 退出 0，4 gen、5 个 trace 路径签名；catalog 存在，所有 gen 签名均能在 trace 找到；`smoke-make.log`、`smoke.json` |

首次 green 编译发现新构造参数漏传，修正后完成上表验证；失败日志 `green-collector.log` 保留。未跑全量 solve、全 isla-lib 或硬件重放。MRET 测试 IR SHA-256 `6fc39efd0f72b0ee8eae247d9965e680b6874f9954334c20d748b42c0987792c`，配置 `71fb63e105331a0f329261c636e55446af42ba0367c96e45c9b49cb60332ad2d`，受测运行器 `f42d3e9d27bd00c5418fdd365d22f581839525d91fb04c5e6dbdb117e81f226e`。这些是精确 catalog 候选版本，不套用浮点历史 IR 名称。

## 后续边界

历史审计脚本或证据若消费 `summary`、`terminals`、`case-id`，仅适用于其旧 schema，不能直接套到本次输出。未来确需完整性账本时应另行讨论需求与最小接入方式；不能为了这些字段再次改造原执行回调。原未提交浮点增量的进一步收缩另行处理。
