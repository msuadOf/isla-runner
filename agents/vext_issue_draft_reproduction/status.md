# V 扩展 Issue 草稿复现状态

整理注（2026-09-23）：下文为历史运行记录。成套 issue1/2/3 材料现提交至 [根 XiangShan 档案](../../archives/xiangshan/2026-09-23-issue-reproduction/README.md)，原目录只作本地副本。Issue 1 的有限时超时不证明永久挂死，也缺完整 itrace/VCD；本次未重跑。

状态：三项均已从草稿原文创建 testcase、重新编译 ELF 并运行完成。

## 环境核对

- XiangShan 工作树：`difftest-xiangshan/xiangshan/`，当前 detached HEAD 为 `c8d7b3a5c1abf3f42c954e61abba20dd27e02a21`，与本地 `origin/kunminghu-v3` 一致。
- 该工作树另有用户已有未跟踪内容：`mill.dMWuA8`、`src/test/scala/xiangshan/backend/fu/vector/ByteMaskTailGenParameterizedTest.scala` 和 `tests/`；复现工作不得触碰它们。
- 可复用 emulator：`difftest-xiangshan/xiangshan/build/verilator-compile/emu`，修改时间为 2026-09-19 04:35:16 +0800。
- `riscv64-unknown-elf-gcc` 可用。
- 后续只读核验 `git ls-remote origin refs/heads/kunminghu-v3` 成功，输出为 `c8d7b3a5c1abf3f42c954e61abba20dd27e02a21\trefs/heads/kunminghu-v3`；预编译 emulator 对应远端当前提交，无需另行询问用户。

## 分工

- Issue 1：向量指令不提交/永久停顿。
- Issue 2：`vsm.v` store access fault 的 `mtval`。
- Issue 3：DUT vector register 写入未同步到 REF。

## 本轮结果

- Issue 1：`issue1/poc.elf`（SHA-256 `edc1f3feec1b2dcedf5f6e177f648b4ac23a31a9df51ddbbbb3e6b1275155c65`）编译成功。首次与在 XiangShan 根目录按草稿调用方式的补跑，均以 `--no-diff --dump-commit-trace` 运行 40 秒后外层 timeout 返回 `124`，未达 GOODTRAP，复现永久挂起。补跑强制终止时 stderr 为 `double free or corruption (!prev)`；两次都未生成新的 commit trace，不能以本轮证据确认草稿声称的最后一条提交是 `csrw vstart`。
- Issue 2：`issue2/poc.elf`（SHA-256 `c26bc31f66f8df423e63d32f0473783f226e014a6b49e95a92f06aa5d12ef04f`）编译成功。difftest 返回 `1`，日志记录 `mcause=0x7`、`mepc=0x80000048`（`vsm.v`）以及 `mtval different`：REF `0x2000000`、DUT `0x1fffffe`，精确复现草稿。
- Issue 3：`issue3/poc.elf`（SHA-256 `af07a56b94c9f7e06c5d923d95fc4b5b63a06ab34ef307f90277189f65f0730a`）编译成功。difftest 在约 14 秒后返回 `1`，日志记录 `v2_low/high different`：REF `0xffffffff00000000` / `0xffffffffffffffff`，DUT 均为 `0x5555555555555555`，精确复现草稿。
- 三项都使用远端 `kunminghu-v3` 当前确认的 `c8d7b3a5c1abf3f42c954e61abba20dd27e02a21` 预编译 emulator；未修改 XiangShan 工作树。
