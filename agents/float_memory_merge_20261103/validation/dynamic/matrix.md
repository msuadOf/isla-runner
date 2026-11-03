# float→memory 合流动态验收矩阵

本矩阵规定新候选的验收义务，不表示任何项目已经通过。所有运行写入本目录下新建的批次目录；旧 `float_review_closure_20261102` 和 `coordinated_memory_fixes_20261102` 输出只作脚本、用例与基线参照。启动时记录候选父仓、Isla、模型 HEAD 与 dirty 文件清单，实际二进制、五份正式 IR、配置、Makefile、seed 注入库和 oracle 的 SHA-256；运行期间这些输入必须冻结。源码或 IR 变化后重新开批次，旧结果不能改署。

| 项目 | 实际入口与范围 | 通过条件 |
| --- | --- | --- |
| 永久 IR | 普通 strict；RV32/64 的 VLEN128/256/512 及默认五份正式 IR，`ir/provenance/manifest.json`。26步安装与104负变异由 `fm_validation_impl` 执行，本目录核其新结果与哈希。 | 模型/工具/config/IR 哈希和生成日志相符；不使用旧 IR 或手工改 IR。 |
| Rust | 合流候选 `cargo test --workspace --lib` 与相关 isarch/内存/浮点测试；正式 release build | 测试退出 0，记录过滤器与总数；release 二进制链接官方 Z3。 |
| 315 异常 | 新 IR 和新 release 上重放旧已审 315 个 SoftFloat 期望值：标量、ROD、普通窄化、向量、BF16；每项重构受约束 IR | 每项 `summary.finished`、所有 partial 计数 0、恰好一个 Retire、FPR/向量位串与 fcsr flags/rm、源寄存器保留、编码、输入哈希和 seed17 均正确。独立 SoftFloat 二进制/源码/归档哈希核对。 |
| 300 flags | 五 IR 直接运行 `accrue_fflags` Rust 探针，每 IR 60 状态组合；RV32/64 均覆盖 | fcsr=旧flags OR 新flags；仅新增位时 FS/SD 更新，其他 mstatus 位保持；callback 顺序仅为静态 IR 合同，不能声称动态观测；共 300 项，不能以旧日志代新运行。 |
| SchemaUnion/混合访存 | 定向 FLD/FSD 或 FLW/FSW、LOAD/STORE/AMO、C_LD/C_SD；实际 JSON 与重放汇编 | 每个 `gen` 同时存在 GPR、FPR、fcsr、`isa-state-complete`/`isa-state-post`、`memory-events`、`pre-memory`/`post-memory`、`instruction-representations` 的 mnemonic/bitstring/`.insn`；不能按指令类别丢另一侧字段。每例按实际机器字、配置复算事件地址、宽度、读值/写数据及 pre/post-memory，核初后态与 Model。任何必需值缺失的负控须无 `gen` 且 summary partial/error；由 core owner 提供故障注入点，本目录验结果。ExecuteAs 用原16位机器字和固定初态续执行，后态同最终 Model。 |
| nat 接口合流 | VFMERGE 与走 `init_masked_source` 的合法 VLSEGTYPE，分别固定 `vstart<vl`、`vstart==vl`、`vstart>vl`/高位大值，保持合法 SEW/FS/VS/机器字 | 活动对照有实际写回；等于/大于 `vl` 正常非 Illegal 退休、目标和 vstart 后态符合模型，不能由别的非法原因使早退看似通过。RFVVTYPE 源码因 `vstart!=0` 提前 Illegal，不能用它证明 nat 适配。 |
| 三表示 | 合流 JSON 的浮点、LOAD/STORE/AMO、压缩样例，GCC 和 Clang 分别汇编助记符、原始位串/小端字节、`.insn` | 两工具链实际机器字等于 JSON `encoding`；非法助记符拒绝单列，仍核两种精确表示。 |
| 真实 Make | 候选 `scripts/run.mk` 的 `solve-FLEQ_S`、`solve-LOAD_FP`/`solve-STORE_FP`、`solve-LOAD`/`solve-STORE` 或 `solve-AMO`、`solve-C_LD` | `make -f scripts/run.mk -o build-isarch solve-*` 实际调用，记录原域与定向域区分。单 Clause 外限7200s、`SOLVE_TIMEOUT=7200s SMT_TIMEOUT=7200s OUTER_TIMEOUT=7200s THREADS=1`、seed17；保留 run.mk 的浮点 qffp、访存 qfaufbv 生产映射，记录实际 argv，CLI 覆写仅另列诊断。按完整 `summary` 判定 finished/partial/timeout，既有 memory partial 按基线比对，不能记 PASS。 |

资源约束：新批次占独立 `target` 和输出目录，先检查并行任务与 CPU 亲和性，默认一条物理核单 worker；不与 IR 生成、release 构建同时间争用。7200 秒是整 Clause 与单 SMT 查询各自预算；定向样例结果不能替代原域结论。审阅顺序为先检查脚本/输入矩阵、再启动动态运行、最后由独立 Sol 重新读取 JSON 和哈希核账。

既有 memory partial 与 F1 原基线分别重跑同配置可比较用例；变为 finished 才能另报新版本结果，仍 partial 时逐字段解释，不能默认当修好。
