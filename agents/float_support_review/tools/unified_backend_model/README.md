# 共用浮点模型与 CMake 集成工具

`prepare.py` 从尚未集成的 Sail-RISC-V 工作树冻结完整源码，在隔离目录中生成单一候选。它只改 190 条原生声明的目标绑定、六个原有 SYMBOLIC 数值/异常体的外层门控、67 个策略级 CPP 绑定、12 个标量 min/max clause、两个 V min/max helper 和三份 CMake；原函数公式、指令 guard 和状态写入顺序由精确源检查保持。`verify_candidate.py` 对冻结前后字节、目标范围、CMake 接线、旧 wrapper 隔离及 SHA-256 作检查，输出相对路径的 review patch。`apply.py` 在全部目标及未改模型源码哈希符合冻结前件、双模式严格类型检查已通过时，才把候选限定文件应用到生产工作树。

2026-09-27 当前自含快照在根目录 `isla/target/float-solve-evidence/unified-backend-model/20260927-final-v7/`。`source-manifest.json` 给出 920 个源码文件、16 个被改文件、七个 adapter 新文件及20个上游 SoftFloat 平台源码文件的哈希；`source-check.json`、`typecheck-result.json`、`repair-report.json` 给出检查、命令及适用边界。七个 adapter 文件由其独占 owner 冻结并复制，本工具只在 CMake 中接线。完整 C++ 构建和 IR 生成由集成人从该快照执行。

**v6 结论修订：** `prepare.py` 原先递归排除所有名为 `build` 的目录，误删了 Git 跟踪的 `dependencies/softfloat/berkeley-softfloat-3/build/` 平台头与 Makefile。因此 v6 的“source ready for CPP and IR build”只适用于 Sail 模型/IR 输入，不能作为完整 C++ 构建自含快照；第一次完整 C++ 构建失败保留为历史证据。`repair_tracked_build.py` 从 v6 导出 v7，逐个与固定 Git HEAD 及 live 文件字节核对并补齐20个追踪文件；Sail 模型树和已通过的双模式严格类型检查受测字节不变。v6 与其原清单未覆盖或改写。

普通 C++ 生产 target 使用共用 Sail 函数体和主、宽、额外三个 adapter 源。`riscv_softfloat.cpp` 从生产 target 移出，仅作为 `EXCLUDE_FROM_ALL` 的独立 oracle target。`SOFTFLOAT_FAST_INT64` 与 C/C++ 的 TLS 定义沿 softfloat target 公开传递；`SAIL_SOFTFLOAT_ENABLE_WIDE=1` 和 `SAIL_SOFTFLOAT_ENABLE_EXTRA=1` 沿 `riscv_model` 公开传递。生成模型显式保留 `ext_decode` 和 `execute`。这些源码与构建合同的静态核验不等于完整 C++ 链接或 77 项运行验收。
