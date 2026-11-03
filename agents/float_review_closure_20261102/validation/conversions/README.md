# 整数转换真实输入定向验收

本目录为模型 `8ad5e8e` 准备六个向量窄转换及 12 个 H/S/D→I32/Ui32/I64/Ui64 包装的固定浮点输入。`prepare.py` 以独立 Berkeley SoftFloat RISC-V 专用实现计算 32/64 位转换结果和 flags，再以 RISC-V 窄饱和规则独立计算 8/16 位目标；不读取受测 IR 的输出构造预期。`oracle-rows.json` 每行保留真实源 FP 位串、RM、完整结果位和 flags。

`helpers.tsv` 共 819 条纯 helper 输入；`scalar-cases.json` 共 282 条真实 FCVT 指令，`vector-cases.json` 共 183 条真实 VFUNARY0/VFNUNARY0 指令。后两者分别核机器码译码、反编码、完成出口、目标寄存器、源寄存器与一个无关寄存器保持、`fcsr`、`vstart`、`mstatus` 的 SAT 与差异 UNSAT。向量用例含 H→i8/ui8 的合法 SEW8、五 RM 与固定 RTZ、活动/屏蔽 lane、`vl=0`、`vstart=1`、LMUL2 完整目的组及旧 flags；标量 W/WU 在 RV64 按 32 位结果符号扩展写 x 寄存器。可被源 FP 格式精确表示的整数上下端点单列；不可精确表示的端点则用紧邻 FP 值对照。未逐一观察全部无关寄存器，结果只能签列明的观察域。

有限可达性记录在 `fixture-manifest.json`：f16 最大有限为 `0x7bff=65504`，故 f16→ui16 无正有限溢出；f16→32/64 位有符号整数亦无负有限越界，全部 H→32/64 位整数无正有限越界。NaN（含负号）和 ±Inf 逐函数保留，NV 必须压制本次转换的 NX；旧 flags 与新 flags 的 OR 单独核对。真实指令用例只覆盖目录中列出的位串、RM、lane 和组，不是完整 Clause 或全域证明。

准备输入：

```sh
python3 agents/float_review_closure_20261102/validation/conversions/prepare.py
python3 agents/float_review_closure_20261102/validation/conversions/check_fixture.py
```

`check_fixture.py` 独立按 32 位指令字段检查 scalar RM/rs1/rd、vector vm/vs2/vd/op，以及 LMUL2 的对齐和源目的组不重叠。隔离 runner 的 Cargo 模板只引用既有 Isla 测试源码，依赖 float 工作树中的 `isla-lib`；`build_runners.py` 保存构建命令、被引用源码哈希与二进制哈希。两个旧 runner 在源码中固定使用 Qfaufbv，因此本批定向结果也只能按 Qfaufbv 记账。冻结新 IR、配置、Isla、源码清单与两个 runner 二进制后，向 `run.py` 显式传入文件及 SHA-256；它会核官方 Z3 动态库哈希，并用 seed 拦截器固定 17 且检查真实拦截日志，保存每阶段命令、退出码、输入哈希和逐项证明结果。此处是直接 helper/译码/执行 runner 的结果，不能算作 `isarch solve-state` JSON、qffp 或完整 Clause PASS。尚未运行动态批次时不得标 PASS。

`runs/rv64d-v128-attempt1/` 保存旧 806/264/168 fixture 的首次运行：helper 程序退出 0 且 806 条逐项通过，seed17 拦截有效；汇总器把末尾 `PASS 806 legacy SoftFloat cases` 又计为一条，于是误判 807 并在标量/向量阶段前停止。该旧证据只适用于旧 fixture。修复计数并补整数精确端点后，新增批次另存，不覆盖旧日志。
