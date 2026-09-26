# 符号化 PMA 实施计划（已确认；2026-09-27 二次修订；同日 S0/S1 完成并验收）

用户方向：PMA 地图由 Isla config 配置；通用情况下可符号化（简单规模必须跑通），爆炸用部分区域钉死控制；JSON 补充求解出的内存信息（另议）。二次修订吸收外部研究观点（isa-testgen 处理方式分析）：S1 升格为主交付并要求与重放环境地图一致；S2/S3 降为 opt-in 研究档，oracle 约束显式化。

## 目标

1. **主交付（S1）**：PMA 地图由 Isla config（TOML）配置为具体值，不重新生成 IR；**配置应与目标重放环境（XiangShan/NEMU）的真实内存布局一致**——此地图下成功路径与 access-fault 路径自然并存（W8 已实测两类并存）。
2. **研究档（S2/S3，opt-in）**：地图字段符号化（边界/属性/整 region），模型自身 `pmaCheck` 分叉。价值场景限定：一次求解扫多地图假设、重放平台可配地图（spike `-m`、自定义 TB）、边界诊断用例。**重放期必须按目标平台地图过滤/选定假设**（pipeline 职责），固定平台直接重放则退化为 S1。

## 机制核心（2026-09-27 spike 核实）

`zpma_regions` 是 IR 顶层寄存器 `%list(%struct zPMA_Region)`（`rv64d.ir:48263`，默认 3 个字面量 record 的 cons 链）；`zpmaCheck` 经 ReadReg 读取后用 `@is_empty/@hd/@tl` 结构遍历——固定长度 list、字段符号化均可走通。solve-state 启动时按 config 构造地图值写入该寄存器——模型逻辑与 IR 零改动；未配置沿用 IR 固化默认。列表结构始终 concrete（SMT 无变长列表 sort）；符号化仅限字段级，PMP 的符号 CSR 是先例。

核实出的实现要点：
- **record 字段是 base+size（非 base+end）**：`zPMA_Region { zattributes: zPMA(若干 bool + misaligned_fault/reservability 枚举), zbase: bv64, zsizze: bv64, zinclude_in_device_tree: bool }`，配置字段镜像此布局。
- **注入走 Rust 构造**：`[registers.defaults]` 的值解析器支持 record/枚举但**无 list 语法**；`[[pma_regions]]` 按 array-of-tables 解析（`get_memory_regions` 有先例）后手工构造 `Val::List(vec![Val::Struct(...)])` 写入 `default_registers` 映射（`initialize_register`+`plausible` 接受 List/Struct）。
- **重叠校验自己来**：`zcheck_mem_layout` 只在 `init_model` 路径执行，isarch 不经过，注入地图不会被模型自动查排序/重叠，配置解析需自校验。
- **S2 待验证点**：`undefined : %struct` 仅整寄存器全符号（`symbolic_from_typedefs` 递归）；逐字段混符号需手工拼 Struct，且含符号 Struct 的 list 在 AssumeReg/smt 层的完整消费未验证——S2 spike 首项。
- **上游无可抄实现**：本地 rems 谱系 isla-testgen（cc4c613）全仓无 PMA 建模（PMP 用 `sys_pmp_count=0` 关掉绕开）；"JSON 配置→pma_regions 物化"属 CTSRD-CHERI 谱系工具，非本 checkout 内容。本计划为自建。

## 与既有两层的关系（正交）

- 内容层（W2-W9）：`[[memory_regions]]` concrete/symbolic/excluded——管"存什么、哪些不关心"；
- 属性层（本计划）：`[[pma_regions]]`——管"哪里可访问、属性、trap 边界"，模型自身逻辑执行；
- 例：地图只配 RAM=[0x80000000,0x90000000)（与目标环境一致）→ 圈外 store access fault，fault 用例在真机成立；连 fault 用例都不要才用 excluded。

## 步骤

- **S0（前置输入）**：确认 XiangShan/NEMU 重放环境真实内存布局（DRAM base/size、ROM/外设区），作为 S1 验收地图。（已完成：DRAM [0x80000000,0x90000000)，与 difftest `DEFAULT_EMU_RAM_SIZE=256MB` 一致；caveat：编译期宏，XIANGSHAN_TOOLS emu 构建是否覆盖未确认。）
- **S1 具体配置地图**：TOML `[[pma_regions]]`（base/size + attr 别名 ram/rom/mmio/hole 或明细位，逐字段对齐模型 `PMA_Region`，含 misaligned 策略/reservability 枚举）；list-of-records 值构造 + 寄存器初始化（先 spike 验证装配路径）；TDD：配置地图 → 圈外按地图 trap；未配置与现状逐项一致。（已完成 2026-09-27：GREEN 端到端 131 写事件全落地图内、边界精确，证据 `/tmp/isla-memimpl-w10-20260927-032747/`；细节见 findings。）
- **S2 边界符号化（opt-in 研究档）**：region 边界符号值，同地址"界内/界外"两类用例。
- **S3 全符号地图（opt-in 研究档）**：record/属性符号化（同地址"是 RAM/是 MMIO"两假设）；fork 预算限流。
- **部分钉死**：与 S2/S3 正交，混合 concrete/symbolic 控分叉。
- **S4（另议）**：JSON 每路径地图判定结果，供 pipeline 过滤。

## 验收口径

- S1：配置地图生效（trap 边界=配置）、未配置回归一致、与目标环境地图一致时 fault 用例可重放；
- S2/S3：简单规模（预算限流）产出"同地址两假设"用例；爆炸如实记受限；
- oracle 规则：任何符号化假设的重放必须过目标平台地图过滤。

## 风险

- list-of-records `Val` 构造与寄存器初始化支持度未知（S1 spike 首项；退路 const_primops/IR 侧并回报）；
- record 枚举字段对齐遗漏=地图错误（TDD 锁）；
- pmaCheck 链 fork 放大（PMP×PMA×地图假设），预算+采样控制；
- `within_mmio_*`/CLINT 基址另由 const 管理，需核对避免双处配置打架；
- 重放环境地图确认错误 → fault 用例假失败（S0 消除）；
- 与主谱系 PMP/PMA builtin 合流需重评。

## 明确不做

多指令序列、MMIO 设备副作用、pipeline.py 集成本体、IR 重新生成。
