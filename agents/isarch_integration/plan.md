# isarch 整合方案 B

目标：保留全部 path merge 与 fuzz 资产，迁移 replay-p0 的动态前态和配套测试。

范围：Sail-RISC-V d5aec317 加 Svnapot/Svpbmt；Isla a8b610dd；runner 38801d0c 加四个 Python 核心脚本、现有测试及 smoke 配置与用例。热点文件为四个脚本、smoke/isarch-fuzz、子模块 gitlink 和验证记录。

步骤：在独立工作树整合模型，核对继承关系与 IR 依赖，迁移脚本及现有测试，归档可运行 smoke，实测后提交。不得覆盖原 dirty 工作树。

验证：path merge Rust 回归、Python 动态前态回归、当前模型重新生成 IR 后运行原生 fuzz smoke，记录实际退出码与版本。哈希只作来源记录，不作样本有效性门槛。

阻塞：原仓库 .git 被当前环境设为只读。独立可写 Git 副本用于完成候选提交；原仓库创建 isarch、删除指定分支及收尾须待恢复写权限。旧分支与旧工作树保持原状。
