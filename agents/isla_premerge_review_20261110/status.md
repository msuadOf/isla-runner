# 审查状态

限定审查与当轮修复完成。两分支带本轮修复后可进入合并；未做 Git 写操作。

- loop：修复 M1 默认开关/缓存隔离和 M2 嵌套读取足迹条件；格式通过，isla-lib 839 单元+53集成+3文档通过，顶层仍为修前相同的缺 IR 七项失败。
- quick：RISC-V 平台熵适配移入 isarch，隔离 RV64 初态默认值，矛盾前态不再误报不适用；格式通过，isla-lib 814单元+53集成+3文档通过（文档测试指定 RUSTDOCFLAGS），顶层240通过、原有缺 IR 七项失败。
- 两树新增失败均为零；合并文本预检无冲突，合并树尚未运行。
- 未跑 isarch 长时实测；LOAD_FP、浮点 helper、CPOP/CPOPW 原阻塞未宣称解决。

计划见 [plan.md](plan.md)，问题、合并取舍、失败名单与命令见 [review.md](review.md)。两工作树的 `agents/premerge_review/` 保存本轮证据；quick 原有未跟踪 `diag/` 保留。
