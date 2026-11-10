# 合流动态验收独立预审

本次仅批准按修订后的动态矩阵推进准备和执行；尚无合流候选的动态 PASS。独审读取实际源码、命令、日志、JSON 和文件哈希，不继承状态表或旧验收。

动态矩阵的三个问题已反馈，实施者已修订：访存 Make 沿用生产 `qfaufbv` 映射；300 状态探针只证明动态 FS/SD/fcsr 数值，callback 顺序保留为静态 IR 合同；混合访存必须复算实际机器字、事件地址/宽度/值与前后内存，不能只检查字段存在。

## 执行与证据要求

- 新 315 异常与新 300 状态各自记录冻结输入、实际程序/IR/config/seed/oracle 哈希。独立数值审查从实际机器字和前态取操作数，不信任 owner 的 expected 字段。
- 混合 schema 覆盖浮点读写、整数读写、AMO 和压缩续执行。每例同时保留 GPR/FPR/fcsr、完整前后态、访存事件和前后内存、原机器字及三表示。
- 必需值查询或格式化失败时整例不得进入 `gen`。负控由核心 reviewer 对真实 collector 负责；独审区分写前未观测自由内存的 `null` 和查询失败。
- 普通 strict、四配置生成、五正式 IR、永久回归及独立错误变异由构建/IR owner 执行。本 reviewer 独立核源文件、工具、配置、产物及日志来源。
- 真实 Make 分别覆盖浮点、浮点访存、整数访存和压缩入口。实际命令保留原生产策略及双 7200 秒预算；定向域与完整域分列。
- GCC/Clang 均实际汇编三表示并比对字节。既有非法助记符拒绝单列，不能假装精确助记符重放已通过。
- 任一合流新失败必须定位并修复。目标 memory 既有缺陷与旧 float 全 77 预算边界单列，不因本次新有限样本通过而消失。

## 自有检查器

[`audit_schema_union_json.py`](audit_schema_union_json.py) 独立要求并集字段和 x1–x31/f0–f31/fcsr，逐位核精确表示，按事件顺序复算前后字节图，并支持 LOAD/STORE/浮点访存/AMO/LR/SC/C_LD/C_SD/C_ADDI4SPN 的实际编码语义。

[`checker-selfcheck.json`](checker-selfcheck.json) 只验证检查器本身：历史 AMO 夹具补上 schema 后为正控，缺 FPR、错误后态、错误编码、错误读值、错误后内存和未解析返回值六个变异均拒绝。这不是新生产验收。

[`inputs-preserved-start.json`](inputs-preserved-start.json) 是本 reviewer 独立读取的六原输入快照：HEAD 与原 dirty diff/file 哈希保持。最终封存前须再次读取，不能拿开始快照代替退出检查。

最终签收须核两个组件的实际双亲 merge、五 IR 来源及受测源码、父仓 memory 两个 gitlink 与组合 metadata、原 dirty 两文件保护，以及组件可获取后的父版本边界。全域覆盖、硬件重放与延期 OPEN 均不在本次有限签收中。

## 脚本后续预审修订

315 launcher 已补两项过滤计数；四个 launcher 已加入逐文件源码 manifest 前后检查，不能仅核 HEAD。混合 launcher 首版遗漏 seed 注入和实际 Z3 核验，已补。混合配置从正式 FD 配置叠加 memory 区域，RAM 缩至 4 KiB，必须单列为定向域；非零 FPR 存储源用于暴露数据关联遗漏。

新增 vstart 脚本首版用 RFVVTYPE 验高 vstart 并预期成功。独审沿 `illegal_fp_reduction → illegal_reduction` 确认，reduction 在调用 `init_masked_source` 之前已将非零 vstart 判为 Illegal；原预期会制造假失败。实施者改用 VLSEGTYPE 的真实访存调用验证 helper，VFMERGE 仍分别覆盖 active/equal/greater/large。这是验收脚本修正，不是生产错误。

当前 `run.mk` 的 21 次独立 dry-run 覆盖七目标及 default/ISA_CONFIG/SOLVE_CONFIG 三种配置方式；策略、配置优先级、双 7200 秒参数均符合预期。见 [Make 预核](make-dispatch-precheck.json)。文件哈希变化后须重核；此结果不代表真实 Make solve 已通过。
