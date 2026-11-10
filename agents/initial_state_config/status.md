# 初态配置状态

2026-10-29：已实现并完成限定验证；按用户后续要求提交为 `8948cc4543c60cb1716c90b642b3a96b30983127`，已 fast-forward 合入 `refactor/general-support-20261007`，未发布。基线通用修复 `09fe582`，新分支 `feat/initial-state-toml-20261029`，工作树 `.worktree/isla-initial-state-20261029`；原 dirty 工作区、已有分支和父 gitlink 保留。

按用户补充要求去掉 `VS/FS/MPP` 字段别名及字段表，Isla 只理解通用位模式：

```toml
[initial_state]
x1 = 42
mstatus = "0b11_?????????"
fcsr = "0b000_?????"
```

模式右端对应 bit 0；0/1 固定值，? / x 都是稳定符号位，未写出的高位继续符号化。整寄存器也支持整数、十进制/十六进制字符串、`"?"`、`"x"`。不会按架构字段名解释位含义，不改变最终见证输出格式。额外 RV64 特权域改为顶层 `initial_state_rv64_domain = true` 显式启用，默认关闭；既有 RVV 约束保留。使用入口见工作树 README 末尾。

验证：`cargo fmt --all -- --check`、`git diff --check` 通过；isla 89/89、isarch 25/25，Brew Z3 下 isla-lib 跳过三项 enum checkpoint 测试后 279/279。未过滤全量受 Z3 枚举 sort 重复声明错误阻塞，基线 09fe582 定向复现；首次系统 Z3 下的浮点测试失败在 Brew Z3 下消失，不能称全部测试通过。

最终 `make solve-MRET ISA_CONFIG=<smoke.toml> THREADS=2 SOLVE_TIMEOUT=45 OUTER_TIMEOUT=60s` 退出0，4条见证初态均满足 mstatus[10:9]=3、x1=42、fcsr[7:5]=0。只测生成入口，没有全指令/硬件验证。

[计划](plan.md)、[受测版本/哈希/结果](evidence/summary.json)、[补丁](evidence/implementation.patch)、[配置](evidence/smoke.toml)、[输出](evidence/rv64_zMRET.json)。日志在 evidence/；实现代码/README 位于上述工作树。

## 合入 general

`refactor/general-support-20261007` 已由09fe582推进到8948cc4；`fix/general-review-20261008` 保持09fe582。general工作树原有8项未暂存修改及未跟踪文件通过stash恢复，无冲突；比较逐文件增删内容及未跟踪文件SHA256均保持，索引仍为空。备份stash `e9cb22e412870e39d533bbc7dfbb5dd12a7dc4fd` 保留，见evidence/general-before.json及前后补丁。原始isla工作区、父gitlink未修改。

合入提交的tree与上轮受测功能tree一致，本轮未重复功能验证；general工作树还含既有浮点dirty内容，其组合不继承纯提交的PASS。

## 合入后复审

8948cc4负面配置复现两个P2：非法UTF-8数值字符串在既有helper切片处panic；不支持的列表寄存器在类型校验前symbolic得到Poison而panic。两项均release退出134，尚未修复。核心位模式方案保留，详见[复审建议](review.md)。

## 复审修复（2026-10-29）

两项P2已修复并提交ef882f01e0208de13fd2224fc83b30e13acee261，fast-forward合入refactor/general-support-20261007。数值helper改用strip_prefix，用户配置类型在符号化之前检查；list、非向量AnyBits、Bool、零宽度、多字段struct负例均返回Type错误。原内部不变量断言保留。

TDD先复现两项测试失败后修复；isla串行90/90、Brew Z3核心279/279（沿用三项enum跳过）、isarch25/25、fmt/diff检查通过。isla首次并行89/90，既有inline_mapping测试触发SMT未初始化，串行全过；未修改该既有测试。release两负例均由退出134变为退出1并给明确错误；make solve-MRET退出0，4条初态断言保持通过。日志见evidence/fix-*。

general原8项dirty修改的增删内容、未跟踪文件哈希与索引状态核对保持，无冲突。备份stash43823d723bca97d3879a5f93a875bdd3e96c405b保留，未push、未改父gitlink；含dirty浮点改动的组合没有新增功能签收。

2026-10-29后续交付：两分支已按指定顺序合入feat/float-support@31506ee，runner兼容及ret_val具化两项已修复，独立GPT-6.1 Sol最终审核通过；旧结论按其版本保留。[合并记录](../general_float_merge_20261029/status.md)。
