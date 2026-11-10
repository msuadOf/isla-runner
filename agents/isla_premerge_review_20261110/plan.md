# 两分支合并前审查与当轮修复

- 范围：Isla 两工作树各自相对 `daf61c04` 的提交及本轮修复；不审历史。
- 目标：检查通用库边界、M1/M2 正确性、编码域与不适用状态，直接修复明确问题。
- 热点：`isla-lib/src/executor/`、`ir/regions.rs`、`primop/`、`config.rs`、`smt.rs`、`src/isarch/`。
- 分工：loop 与 quick 两审查 agent 仅写各自工作树；主 agent 汇总、预判冲突并维护本议题文档。
- 步骤：读取规范和设计；记录修复前失败；集中审查；先补失败测试再修；跑指定检查；汇总。
- 验证：两树各自 `cargo fmt --check`、`cargo test -p isla-lib`、`cargo test`，链接指定 Z3 5.4.0。若 rustdoc 未沿用 RPATH，记录环境失败并用动态库搜索路径复核。
- 边界：不做 Git 写操作，不跑 isarch 长时实测，不修改 Sail 标准行为，不算哈希。设计文档只读。
- 未决：争议较大的架构取舍只报告选项和影响。
