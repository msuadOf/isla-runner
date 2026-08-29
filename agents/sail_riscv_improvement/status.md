# sail-riscv 符号执行改进空间 —— 状态

## 议题状态:研究完成,待用户确认实施方向

完整分析见 [report.md](report.md)。本文件记录当前热点、进展、待办。

## 当前热点文件(sail-riscv 侧,改进落地位置)

### V 扩展(V-ALU-MUX,攻击 VITYPE/VVTYPE/VXTYPE)
- `sail-riscv/model/extensions/V/vext_arith_insts.sail` —— 115 个 `foreach (i from 0 to num_elem-1)` 符号循环
  - VITYPE SYMBOLIC 分支:1762-1898(`$else`)
  - VVTYPE SYMBOLIC 分支:165-386
  - VXTYPE:同构
- `sail-riscv/model/extensions/V/vext_control.sail` —— 关键 helper:
  - `checked_sew_value`(39):`match SEW {8,16,32,64}` 收窄模板
  - `assert_vector_num_elem_upto_32/64`(172/190):num_elem 有限域枚举模板
  - `get_num_elem`(437):符号 num_elem 来源
- `sail-riscv/model/extensions/V/vext_utils_insts.sail` —— `valid_*`/`illegal_*` 约束 helper(23-228)

### MEMORY(MEM-01,攻击 LOAD)
- `sail-riscv/model/pmp/pmp_control.sail`
  - `pmpCheck`(:106 `if sys_pmp_count==0`、:118 foreach)—— MEM-01 短路位置
  - `pmpRangeMatch`(:44)、`range_subset`(:50)—— PMP 簇 fork 源
- `isla/rv64d.ir:24247` —— `sys_pmp_count` 固化为 16

## 关键证据(已核查)
- **默认 `make solve` 真实超时集 = {VITYPE, VVTYPE, VXTYPE},3 个全是 V 扩展**(`output/status.timeout.log` + make 求值 ACTIVE_ALL 确认这 3 个在范围内)。
- **LOAD 不在默认 solve 范围**:LOAD 在 MEMORY 组(`run.mk:71`),被 `ACTIVE_ALL = $(filter-out $(MEMORY), ...)` 排除,make 求值 `LOAD-in-active: 0`。`status.timeout.log` 里那条 `LOAD timeout` 是旧 run 残留(日志 22:09 早于当前 run.mk 配置)。LOAD 属于 `make solve-memory` 子目标。
- VITYPE.log:612 个 fork `taints:["vtype"]`,主簇 vext_arith_insts.sail:1689 计 586 次
- **SYMBOLIC 已启用**:rv64d.ir 有 4 处 `zisla_init_mask` 调用(SYMBOLIC 独有);VITYPE IR 体引用 sail 源 1763-1898(`$else` 分支)
- VLEN=256(zvlen_exp=8),config 未固定 vtype
- LOAD.log:PMP 簇约 64-76 fork(占 ~37%),是唯一大簇(仅对 solve-memory 有意义)

## 优先级(默认 make solve)
1. **V-ALU-MUX**(effort medium-high,conf high):把 V 扩展算术 foreach 的符号 num_elem 循环边界,用 `checked_sew_value`/`assert_vector_num_elem_upto_*` 同款有限域枚举收窄。攻击 VITYPE/VVTYPE/VXTYPE。**这是默认 solve 唯一需要做的改进。**

## 次优先(make solve-memory,非默认 solve)
- **MEM-01**(effort low,conf high,is_sound=true):pmpCheck 加 `$ifndef SYMBOLIC ... $else: return None()`。攻击 LOAD 等 MEMORY 组。

## 待办
- [ ] 用户确认是否实施(若实施,先在 VITYPE 跑通 V-ALU-MUX 模式再推广)
- [ ] (可选)核查 vector_crypto 的 EGW/寄存器组约束完成度
- [ ] (未来)solve-fd-float 启用前做 FD-5-ABSTRACT(softfloat extern abstract 标记)

## 被否决的改进(避免重复)
- 全部 FD-1~FD-6:FD_FLOAT 组被 `run.mk:78` filter-out,对 make solve 零增益
- MEM-02(split_misaligned 短路):SymbolicLength 全日志 0 命中,机制杜撰;config misaligned.supported=true,改它逼近 guides.md 红线
- MEM-05(ZICBOZ cache_block_size 固化):IR 已固化常量 6,无对象可消
