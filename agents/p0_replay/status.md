> S0 #6669（2026-11-08，已复现）：当前 a13efc87 emu 上，作者 g 附件及手写六页 ld+sd / ld+sd+lw 均 mismatch（emu 未触发异常、NEMU cause 5）；五个对照均 agree，与 issue 一致；R-XS-001 不命中，规则及重放链未改，见 [结果、脚本及版本限定](seq-6669.md)。

> E2 四场景扩展（2026-11-08，完成）：新增 Sv39 STORE 609/609、Sv48 LOAD 2074/2074、Sv48 STORE 958/958 三方 agree；原始 mismatch、已有规则归类、新分歧和运行失败均 0。单测142/142、成员复验及逐例核账3641/3641；只用MPRV+MPP数据权限路径，见 [结果与代表例子](ecfg5-all-scenarios.md)。

> E2 符号前态（2026-11-08）：U/S、SUM/MXR 数据访问回放已实现；单测137/137、成员复验1359/1359，emu＋独立NEMU全量1359例：agree 1359、原始mismatch 0（既有窄规则归类0、新分歧0），运行失败0；只用MPRV+MPP，不证明真U执行等价；未回放E1/E3，见 [本轮报告](ecfg5-u-mode.md)。

> 收尾（2026-11-07）：**ecfg4b 通过**——新模型（Sail `d79d8b32`、Isla `ae1a335`）在 ecfg3 同一香山配置下重生 IR，2836类/584形状/122路径一致，J1 2836/2836、E3 584/584、E4 587/587、单测124/124，见 [ecfg4b](ecfg4b-results.md)；先前 [ecfg4](ecfg4-results.md) 误用官方发布 IR，已更正。P1b 的 14 个分歧归为已上报问题族并另提 [#6884](upstream-issue-body.md)（关联上游 #6670）；判官、变异体类号统计与精确位组合数在 Isla 仓库 `feat/isla-judge` 分支。待办：Rust 变异器、按类调度、维度网格。

> Fuzzing P1b（2026-11-07）：**完成**。四场景5000例全部重放及逐例核账完成：4986 agree、14原始mismatch、3个新形态待查；新形态简化输入J1及三方重放通过，unittest119/119 PASS。Sv48 STORE监控竞态已修复并保留中断证据。见 [本轮报告](fuzz-p1b-results.md)。

> Fuzzing P1（2026-11-07）：**六项完成，无阻塞**。728种子原样J1重判一致；M1/M2/M5=168/140/192，500/500确认并重放。原始498 agree＋2个A.3优先级差异（XS cause5、Isla/独立NEMU cause13）；后续精确过滤2例、保留2个代表，未过滤mismatch0。形状136→142、形状×切片桶4423→4983、拟入语料331，仅记录无反馈调度，父种子类仅作来源。610次尝试去重110，正式判官丢弃0；unittest115/115、N3负对照与最终核账PASS。原覆盖阻塞已由用户澄清解除，别名断言与TLB漏算的中间失败保留为历史；见 [完成报告](fuzz-p1-results.md)。

> ecfg3 接续（2026-11-07）：新IR `3f16d5e7…`，四场景2836类/584形状一致；E3 584/584 PASS；指定三例＋PBMT对照4/4、隔离2/2，emu与独立NEMU一致；E4 587/587验收PASS（584正例＋3负对照）；unittest100/100。见 [ecfg3结果](ecfg3-results.md)与[方案](ecfg3-plan.md)。下方批次A为历史记录。

# P0 重放器状态

**动态前态模板（2026-11-08）**：Python 重放链已取消固定 x1/x2、VA 和根表要求，使用实际操作数、求解前态与场景地址域；八槽位四场景回归及真实 ELF 编译通过，pytest 153 项＋210 子用例 PASS。成员复验命令移除旧 GPR/SATP 固定值；本轮未新跑 isarch/emu/NEMU，历史硬件 PASS 仅适用旧版本，当前版本待复验。见 [实施与验证](dynamic-prestate.md)。

**批次 A：E-exit PASS，E-dev FAIL（完整判死未验证），三个扩展场景限定 PASS（2026-11-07）。** 五个 E0 正例已按 v2 出口契约重新生成并实跑。设备配置导致锁定运行器 panic；没有替换方案或修运行器。E1—E4 仍未测。

| 项目 | 当前状态与边界 |
| --- | --- |
| 退出归类 | 只在单次 GOOD、精确 good_trap_ins PC、无 ABORT/limit、退出 0、ELF 哈希匹配时 agree；失败桩返回原因码 |
| 生成侧检查 | objdump 核对 GOOD 顺序入口、唯一 GOOD 与 7 个登记失败出口，拒绝绕过检查或游离 XSTrap |
| 定向测试 | 原 9 项保持通过；新增 3 项，共 12/12；先红后绿 |
| E-exit | X1—X5 通过，正例 5/5 重新实跑 agree；错误期望、rd 翻位、V 清零对照原因码正确；游离 GOOD 拒绝；-I10000 退出 0 仍判 limit |
| E-dev | 普通根 mmio+excluded / 仅 mmio 都 panic（smt.rs:968 缺 enum id）；前缀计数不当最终结论 |
| 设备定向探针 | 仅 mmio 的设备根已导出 10 条读设备 PTE 的样本；excluded 同一地址 BadRead、0 样本，但 partial/errors=1；数据分支未完成验证 |
| E-cfg 原 Sv39 LOAD | 历史限定 PASS：20 路径、2404 类、104 形状；原报告保留不改 |
| E-cfg 扩展 | Sv39 STORE 20/1204/92；Sv48 LOAD 27/6918/140；Sv48 STORE 27/3510/124（路径/类/形状）；退出 0、地址断言通过 |
| 全项 E-cfg | 未签收：设备判死失败；新 IR、count 模式、独立 C3 与完整平台描述生成未测 |
| E0 v1 历史 | 原“必须打印 BAD”条件 FAIL 保留；现按 v2 PC 契约重新验证，见 E-exit，不静默改写旧报告 |
| 下一步 | 在独立授权任务修复运行器 enum id 问题后重跑 E-dev；再推进完整平台生成、E1—E4 |

- [设计 v2](design.md)：本轮未改。
- [实施计划](plan.md)
- [E-exit 结果与命令](e-exit-results.md)
- [E-dev 失败证据与定向结果](e-dev-results.md)
- [E-cfg 原记录与扩展场景](e-cfg-results.md#扩展场景)
- [E0 历史证据](e0-results.md)：页异常 guided_exec 强制同步、高 PA/有效 RAM 别名 AF、当前 emu 未安装 L2TLB 检查器的结论仍按原版本限定。

本轮输出在 output/exit、output/dev、output/ecfg 三个扩展目录与 output/batch-a。没有 Git 写操作，没有写其他工作树或 /home，没有重编 emu、NEMU、isarch 或 IR。
