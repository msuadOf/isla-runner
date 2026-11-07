> ecfg3 接续（2026-11-07）：新IR `3f16d5e7…`，四场景2836类/584形状一致；E3 584/584 PASS；指定三例＋PBMT对照4/4、隔离2/2，emu与独立NEMU一致；E4 587/587验收PASS（584正例＋3负对照）；unittest100/100。见 [ecfg3结果](ecfg3-results.md)与[方案](ecfg3-plan.md)。下方批次A为历史记录。

# P0 重放器状态

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
