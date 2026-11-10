# 当前float模型的同类改动（2026-10-31）

受审模型为9c339044，根float1c7a354／Isla80231ce9。nan_unbox已恢复，但不是唯一分支合并位置。本轮静态核对源码及历史记录，没有新跑性能或修改实现；以下是主要类别，并非所有ITE点位的穷尽清单。

| 类别 | 当前源码位置（Sail-RISC-V仓相对路径） | 合并的情况 | 证据与限制 |
| --- | --- | --- | --- |
| 条件更新浮点状态 | model/extensions/FD/fdext_regs.sail:542–550，accrue_fflags | flags新增置位/没有新增，条件更新FS/SD | 旧批11目标61次CheckSatAssuming超时定位到此，动机明确；已有符号状态等价测试，未找到该单项的整Clause严格前后收益量化 |
| min/max数值选择 | model/extensions/FD/fp_minmax.sail:15–20、37–42 | 双NaN/单NaN、正负零、数值大小 | 真实标量提取fixture十二旧入口合计1566完成路径，新十二入口合计12；逐旧路径结果/flags差异UNSAT。这是单函数隔离数据，不是十二完整Clause的运行统计 |
| 数值分类与转换选择 | model/extensions/V/vext_fp_utils_insts.sail:291、model/extensions/FD/softfloat_symbolic_f32.sail:10、103–105及f16/f64对应文件 | qNaN/sNaN/Inf/zero/normal等分类；NaN结果规范化；转换invalid/饱和结果 | class隔离每格式10→1路径，窄适配2或3→1；有等价/定向数值测试。新数值后端也含此前外部函数内部语义，不是所有位置都可机械“改回一行if”；整Clause收益/分类覆盖需逐项核查 |
| 向量lane掩码与归约 | model/extensions/V/vext_fp_insts.sail:80–82、各SYMBOLIC循环；vext_fp_red_insts.sail；bfloat16/zvfbfmin_insts.sail、zvfbfwma_insts.sail | lane活动/不活动、写新值/保留旧值、累计/屏蔽flags | 真实f16Add小原型8lane路径256→1，5.97→0.12秒；4lane顺序归约16→1，约11.8→4.0秒。有局部实测，不能外推完整Clause同倍数收益或mask语义已被JSON全覆盖 |
| 合法性判断聚合 | model/extensions/V/vext_fp_utils_insts.sail:18–33、58–62；共享vext_control.sail等 | SEW/RM/vtype/vstart/寄存器限制的短路判断变严格布尔 | caller仍可按最终Bool分叉，但各拒绝原因不再必然各有路径。部分eq_anything改动有隔离主动查询收益数据，不能把这些证据概括为全部guard的完整性能证明 |

历史原始依据：agents/float_support_review/solve-fix-performance.md第1、9、11.2、14.3节；solve-fix-scalar-minmax.md；solve-fix-vector-lanes.md。min/max机器报告已读取isla/target/float-solve-evidence/scalar-minmax/20260926T150621Z/probe-v5/report.json，保存132/126→1等实际记录。class和掩码数据本轮按已有报告核对，未重跑。

结论：仍有类似的覆盖风险，但不能全部称为“没有数据的优化”。优先按语义条件逐项核账；accrue_fflags、分类/NaN/饱和结果选择需要重点检查，已有小原型收益也不替代完整Clause性能与JSON覆盖。不得一次性回退整个统一浮点数值后端或误删状态正确性修复。
