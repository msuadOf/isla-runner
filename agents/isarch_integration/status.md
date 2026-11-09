# isarch 整合状态

2026-11-09：候选实施与限定实测完成；原仓库分支收尾阻塞，不能视为方案 B 全部完成。

- Sail-RISC-V 候选 `34903a1e`：`d5aec317` 加 Svnapot/Svpbmt 两个 cherry-pick。
- Isla 候选以 `a8b610dd` 为祖先，完整保留 path merge、F16 统计和 fuzz；当前 v128 IR 由整合模型严格重新生成。其他 IR 保留历史来源。
- runner 候选以 `38801d0c` 为祖先，四个核心脚本与 replay-p0 动态 prestate 源码逐字节一致，配套四组回归及 smoke 配置/corpus 已归档。
- 实测：Python 153 通过、210 子测试通过；path_merging 专项 6/6；executor 396 通过、5 忽略；退出码均为 0。原生 fuzz 20/20 corpus entry 认证、20 次变异/判定，退出码 0。
- 原生探索预算 60 秒，日志存在 excluded memory 的路径修剪与局部求解超时；本次只签收成功完成的认证/变异闭环，不声明 STORE 全路径完成。未运行硬件或其他 IR 配置回归。
- 原三个仓库的分支、HEAD、索引及未提交 diff 与开始时一致。环境将原 `.git` 设为只读，无法创建原仓库 `isarch` 或删除指定分支；候选提交保存在独立 Git 副本与 bundle，未操作远端。

[方案](plan.md)、[smoke 用法](../../difftest-xiangshan/smoke/isarch-fuzz/README.md)、[验证摘要](verification/summary.json)、[原生认证](verification/native-reconfirm.json)、[命令](verification/native-command.json)。
