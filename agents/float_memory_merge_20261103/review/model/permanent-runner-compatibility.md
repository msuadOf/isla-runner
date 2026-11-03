# 浮点永久回归测试配置兼容审查

新合流树的首次 `float_ir/run.py --mode all` 在编译测试程序阶段失败，错误为两处 `ISAConfig` 字面量缺少 memory 新增的四个字段；尚未执行 helper/state 断言。原始失败保留在候选 `agents/float_memory_merge_20261103/validation/integration/preliminary-float-ir-all/build.log`。

已核 `isla-lib/src/config.rs` 的字段类型与配置解析缺省值，允许实施以下最小兼容修正：仅在 `test/float_ir/runner/src/state.rs` 和 `test/softfloat_legacy/runner/src/main.rs` 的 `empty_config()` 各补 `pma_regions: None`、`symbolic_registers: Vec::new()`、`value_hints: Vec::new()`、`encoding_slices: Vec::new()`。这是四项配置缺失时现有解析器采用的默认值，不加入 PMA、额外寄存器符号化、值域提示或编码切片，不修改生产或已有断言/夹具。

修后已独立读取实际 diff：上述两处各增加四行，合计八行；没有其他语句、断言、夹具或生产修改。两路径 `git diff --check` 通过，实现负责人报告对应 runner `cargo fmt` 退出 0。实际修改符合已签最小兼容合同。修后完整回归仍待实施负责人交付；原失败不改署 PASS，前面的模型及新 IR 来源签收不受测试程序初始化器补项影响。

修后预检 `preliminary2-float-ir-all` 已自然退出 0。独立读取 checks 清单、实际命令和日志：26 步全部 exit 0，五个 IR 入口均执行 helper/state/guard；RV64 每入口 327 个 helper 用例、RV32 307 个，state/guard 全部 `failures=0`。两个实际 debug runner 的动态链接均指向指定官方 Z3，库 SHA-256 为 `899cbc70affab963044e975c814fd549a605b5d7bef31b0fd65fb01421bf9970`。清单和日志/程序哈希见 [预检独立证据](permanent-preliminary-independent.json)。由于 core 源码此时尚在修改，本批仅签预检，必须在最终源码冻结后正式重跑，不能改称最终生产通过。

stage v2 的正式测试曾完成 26 步，V128 的 104 个定向负变异也已独立重放，结果与本批报告逐项相同。随后 executor/primop 的 cfg(test) 模块新增 5+9 行显式 SMT 初始化；主负责人和 core reviewer 已确认改动性质。这不会改变本轮 IR/checker 哈希，但完整源码清单发生变化，因此 v2 只保留历史版本边界，不署最终完整状态，见 [v2 历史核账](permanent-stage-v2-historical.json)。v3 已重新冻结 1042 个文件，初次独立回读无漂移；正式回归结束后另行签收。

最终结论以 `4d085b14` 为准：新 `ir-all-4d085b14` 26/26、五 IR helper/state/guard 与 104 负变异独立重放均通过，最终 1042 文件清单无漂移，见 [最终签收](final-signoff.md)。上面的失败、预检和中间版本只保留原版本边界。
