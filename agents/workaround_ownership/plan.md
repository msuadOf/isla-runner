# workaround 归属与运行方式

## 方案修订

最初方案以 Sail-RISC-V 描述生成 Isla 运行副本。用户 2026-09-28 明确要求删除 Isla 副本、Sail-RISC-V 文件使用 `strict=false`、IR 不匹配仅告警，并把本议题改动单独提交。以下为现行方案；旧生成方案只作历史中间状态，不再作为实施入口。

## 目标与边界

- `sail-riscv/configs/isla/workarounds/` 保存 79 份 Isla 可直接解析的 TOML，包含执行策略、Sail 区域、`strict=false` 和供告警使用的基准 `ir_sha256`。基准取已提交的 V128 IR `6fc39efd…`；暂存的 d012 IR 偏离基准时只告警。
- 删除 `isla/configs/workarounds/` 的 79 份副本；`isla/scripts/run.mk` 的 77 个目标直接引用 Sail-RISC-V 中的配置。VFMV/VFMERGE 两份历史配置仍保留，但沿用先前已经解除的 Makefile 绑定。
- `isarch` 在非严格配置的哈希不匹配时输出 warning 并继续；原有 `strict=true` 的硬失败语义保留给其他用户。
- 不生成 IR、不重绑当前暂存的浮点模型修改、不合并分支、不纳入其他已有暂存或未暂存改动。

## 实施和验证

1. 先写 Isla 单测和 Make dry-run 测试，确认旧入口不满足新要求；再修改告警逻辑及路径。
2. 为 79 份 Sail TOML 写入非严格标志和已提交 V128 IR 的基准哈希，修正关于严格模式的说明；删除已废弃的生成器与 Isla TOML。
3. 更新用户入口、源码区域验证脚本及状态文档。配置文件仅在相关 Sail 模型代码变化、影响受限区域时调整；IR 哈希变化本身只产生 warning。
4. 运行定向 Rust/Make 测试、TOML 全量解析、`cargo fmt`、`git diff --check`；使用 `f8ce849` 已提交模型树验证 132 region/22 锚点，并如实记录当前暂存模型树的旧坐标失配。实际全量 solve 需新的同源 IR 后另验。
5. 只提交本议题文件与相应 gitlink；隔离已有浮点模型、IR、其他文档和用户暂存内容。检查三个仓库的提交树和遗留状态。
