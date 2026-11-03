# `accrue_fflags` changed 显式分支：实施与定向检查

## 源码范围

基线为模型提交 `6202e23fc43a9aa98d9fbfd42f0f2e6128cf7f9a`。仅修改 `.worktree/runner-float/sail-riscv/model/extensions/FD/fdext_regs.sail` 的 `SYMBOLIC accrue_fflags`：`changed = not_bool(eq_anything(old, old | flags))` 进入显式 `if`；真臂执行原扩展互斥断言，并且仅在 `Ext_F` 下将 FS 置 Dirty、SD 置 1。假臂不赋值 mstatus。原 `FFLAGS = old | flags` 和其后的 `fflags`、`fcsr` 两个 CSR callback 顺序保留。未调用 `dirty_fd_context_if_present`，因此未加入原 SYMBOLIC 版本没有的 mstatus callback。普通非 SYMBOLIC 实现未改。

基线文件 SHA-256：`5cc769261a4716a4238c3446a36bbba9692a5ac74fe2a9615ca0c3d5eb5c1fa2`。修改后文件 SHA-256：`252002bb29d17da842bfacc2ac5733baec7eeada2d84dce29c233a1a8dafb3b5`。单文件补丁见 [model.patch](model.patch)，SHA-256：`6688048a547bf6589c275a3de5e54fda98b51c766f17959505f2503856185a74`。工作树另有其他 owner 的模型修改，未纳入本补丁或本项结论。

## 实施检查

运行 `python3 agents/float_review_closure_20261102/flags/check_flags_changed.py`，退出 0：`PASS: 393216 helper states; FFLAGS, mstatus, assertion, callback order`。检查器先确认源码的关键语句与顺序，然后遍历所有 5 位旧 flags、5 位本次 flags、四种 F/Zfinx 开关、FS 四种初态、RV32/RV64 SD 位置、三种其他 mstatus 位模式和四种 FCSR 高位模式；比较原 ITE 公式与显式分支的 FCSR、mstatus、断言结果、callback 参数和次序。覆盖旧 flags 已含同位而 `changed=false`、从零新增单/多位、已有其他位后再新增；不把本次 flags 非零直接当作 changed。`git diff --check` 退出 0。

这是 helper 级公式与源码结构检查。整条指令的目标寄存器写入可能独立置 Dirty，因此不能仅凭指令后态 Dirty 推断此分支工作。共享模型其他文件在并发修改；曾启动普通 `--just-check`，随主 agent 要求中断，退出 130，日志见 `ordinary-strict.log`，不计 PASS。普通检查本来也不验证 `$ifdef SYMBOLIC` 新分支。SYMBOLIC 严格类型检查、生成 IR 的真实 Jump/支配关系及动态完整 Clause 仍分别待验，旧版本结果不能代签。

独立模型 reviewer 对上述 SHA-256 的单文件源码 hunk 已审查通过：确认 changed 真臂断言语义、FS/SD 更新、假臂保持、FFLAGS 与两个 callback 顺序，以及无新增 mstatus callback。该结论仅属源码阶段，待主 agent 在集成后统一提交并固定完整模型来源。
