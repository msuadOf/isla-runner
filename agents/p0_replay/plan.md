# E0 实施计划

## 动态前态与模板绑定（2026-11-08）

- 目标：Python 重放链消费求解样本中的实际 GPR、指令和 SATP，取消固定 x1/x2、VA 和页表根地址要求。
- 范围：`difftest-xiangshan/` 的三个 paging/replay Python 入口、对应单测及使用说明；不改求解器、IR、模拟器和已知分歧规则，不提交 Git。
- 热点：`scenario_profile`/`bound_template`、`decode`/`platform_case`/`paging_assembly`、`predict_sample`/`check_command`；同步页表变异地址选择与覆盖记录。
- 步骤：解析实际 ld/sd 操作数，按样本计算有效地址；加入场景地址列表或区间/掩码；成员复验移除旧命令的 GPR/SATP 固定值；汇编绑定实际操作数并保护 LOAD 结果；补四场景八槽位与异常回归，再运行全目录 pytest。
- 验证：全量 Python 单测及真实 ELF 编译/反汇编，记录源码与 decoder 哈希；新硬件重放和求解器成员复验不计为本轮已测。
- 状态：实施及单测完成，详见 [本轮记录](dynamic-prestate.md)。旧硬件 PASS 仅适用于旧版代码，当前版本待复验。

按 [既定设计](design.md) 完成框架探针，不扩展到 E1—E4。

- 范围：新增 `difftest-xiangshan/paging_replay.py` 与定向测试；保留现有 pipeline 和分析器。
- 输入：只读使用 isla-enumerate 的 samples v1 与 pt_decode；记录 SHA-256。
- 步骤：先测试红灯；实现 Sv39 ld 的严格解码、重定位、规范化和 ELF；逐个运行五例与错误期望负对照。
- 验证：记录完整 stdout/stderr、退出码、GOOD/BAD/ABORT、符号和 CSR 证据；单次 emu 最多 600 秒。
- 未决：L2TLB 是否在异常提交前阻断；NEMU 高 PA 行为；页异常强制同步的实际效果。
- 边界：不写其他工作树、不做 Git 写操作、不重编 emu。运行产物统一在 `output/e0/`。

详细结果见 [E0 报告](e0-results.md)，摘要见 [status](status.md)。

## P0 批次 A（2026-11-07）

按 design v2 执行，顺序为 E-exit、设备区、扩展场景。第一部分失败不阻断后两部分。

- 可改：paging_replay.py、定向测试、本议题结果与摘要、全仓状态和发现。design.md 保持原样。
- E-exit：先补归类及 ELF 静态检查测试并确认红灯；实现正向 PC 匹配、哈希校验和原因码；重跑 E0 正负例及 X1—X5。旧正例 PASS 在代码变更后待复验。
- E-dev：冻结 E-cfg 运行器和 IR，低端设备窗口分别使用 mmio+excluded、仅 mmio；T64，单次 1200 秒。统计实际访问与 AF 目标，必要时定向约束目标验证判死。
- 扩展：Sv39 STORE、Sv48 LOAD/STORE；T32，最多同时 4 个，单次 1200 秒。记录路径、类、形状、地址和禁读区断言。
- 输出均在 output/；不做 git 写操作、不写其他工作树或 /home。逐次命令和哈希随结果保存。
- 未决：设备区 excluded 能否阻止访存前的 AF 分支；STORE 解码和直方图须区分数据写与 PTE 读。

## E2 四场景符号前态回放（2026-11-08）

- 目标：在已完成的 Sv39 LOAD 之外，回放 Sv39 STORE 609、Sv48 LOAD 2074、Sv48 STORE 958 个 corpus entry。
- 入口：读取 `isla-sym-config` 的 fuzz-step6a 完整导出；Sv48 LOAD 使用 `serial64`。IR 使用 ecfg4b 原 `rv64d.ir`，成员检查绑定各自 E2.toml、SATP 和指令。
- 热点：`replay_symbolic_prestate.py`、`paging_fuzz.py`、`tests/test_symbolic_prestate.py`。共用 platform_case/paging_assembly/predict_sample/check；不修改已有窄规则。
- 步骤：失败测试、补齐入口与 STORE 未知初值预测、全量单测、逐字段预测、具体输入成员复验、emu 与独立 NEMU 全量回放、按旧规则归类、选取相对 E0 新行为的代表。
- 验证：保留原 137 项；三个场景顺序运行，本轮 emu 总并发最多 8，每例超时 120 秒；60 分钟无进展则停止报告。
- 边界：只写本工作树，输出在 `output/ecfg5-all-scenarios/`；不做 Git 写操作。M 态执行访存，MPRV+MPP 表达 U/S 数据权限，不使用 mret 进入 U。
- 未决：硬件是否出现新分歧。新分歧只保存完整输入及三方 cause，不自行定性，不新增或放宽规则。

实施和验证均已完成，结果、首次观察器失败记录、代表例子及复现命令见 [E2 扩展报告](ecfg5-all-scenarios.md)。

## S0 #6669 顺序访问定向实验（2026-11-08）

- 目标与范围：只在当前 emu/NEMU 比较作者附件及正文的七个固定访问条件，不改重放链、窄规则或模拟器。
- 热点与步骤：只读 `issue.json` 和 ELF；在 `output/seq-6669/s0/` 手写汇编并沿用现有 gcc 参数及链接脚本；顺序跑 DiffTest、无 DiffTest及独立 NEMU；按最终访问序号、CSR 和出口符号记录结果。
- 验证：每次 `-I 1000`、120 秒外限，并发 1；40 分钟无进展则停止。独立 NEMU 对齐默认 flash 状态，禁止 guided_exec；最终核对八份运行记录。
- 未决与限定：emu a13efc87 早于 issue 的 09453ff8，构建配置也不同；不裁决 RTL 原因。准备阶段的无网络限制已由用户提供本地材料解除。

实施及验证完成：附件与两个触发条件复现、五个对照 agree，见 [报告](seq-6669.md)。
