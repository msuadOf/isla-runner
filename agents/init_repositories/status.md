# 初始化依赖仓库脚本状态

状态：已实现并完成静态验证。

## 已确认

- 根 `Makefile` 当前只 clone `isla`、`sail` 和 `sail-riscv`；仅 Sail 固定 revision，且 clone 失败会被忽略。
- `assembly-gen`、`difftest`、`sail-riscv`、`isla` 与 `difftest-xiangshan/xiangshan` 都是独立 Git 工作树。
- `difftest-xiangshan/` 外层是 harness 目录而非 Git 仓库；真正可 clone 的上游仓库是其内部 `xiangshan/`。
- 多个工作树含未提交或未推送内容，初始化脚本不得覆盖它们。

## 后续

- `init.sh` 已新增；目标分支为 `isla/dev-isarch-runall-ext`、`sail/sail2`、`sail-riscv/isla/symbol-excution_6_14`、`assembly-gen/dev`、`difftest/dev` 和 `xiangshan/kunminghu-v3`。其中 Sail 会在更新 `sail2` 后固定到 `446fb477c508853595ccc937ed60765aa685ae31`。
- `bash -n init.sh`、`./init.sh --help` 和 `git diff --check` 均已通过。
- 安全试运行会在当前脏 `isla/` 工作树前 fail-closed，未执行 fetch、checkout 或 pull。
