# 协作规范与文档重构状态

当前状态：已按用户反馈修正目录边界。根 `agents/` 保持实体目录，议题计划、状态、报告、实验和脚本均在原位；`specs/` 与 `docs/RESULTS.md` 负责项目级汇总。

- 方案：[plan.md](plan.md)
- 参考对照：[research.md](research.md)
- 实施与验证细节：[migration.md](migration.md)

已完成：创建项目级目标、结构、状态和结果文档；更新根规则、Git 说明与 README；恢复上轮错误迁出的议题文件及脚本。

验证：原有 101 个文件均为原位置的普通文件；三份用户未提交文件的 SHA-256 与开始时一致。新建文档链接、Python 语法和辅助脚本路径检查通过；严格 IR 配置校验通过，`git diff --check` 通过。历史证据中本来不存在的目标文件继续作为历史限制记录。

结论已同步到 `specs/TODOs.md`；后续按议题更新 `agents/<topic>/status.md` 与全仓状态表。
