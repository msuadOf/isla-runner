# 内存 clause 分支覆盖对照合并矩阵（W19 跑批 + G1-G8 对照）

- 日期：2026-09-27。范围：`make solve` MEMORY 组 48 clause（run.mk 原序；A 扩展展开为 AMO/LOADRES/STORECON）的逐 clause 语义分支覆盖五分类对照（①已覆盖 ②配置性不可达 ③预算/超时截断 ④引擎缺陷 ⑤语义无此分支）。
- 本文件是八份组报告的合并矩阵与发现收敛（议题详细文件；原定文件名 report.md 被本环境写入限制拦截，故用本名）；逐 clause 证据细节（源码行号、JSON 抽样、log 佐证）保留在组报告原文，本文只引用：`/tmp/isla-memsolve-survey-20260927-125738/coverage/G1-scalar.md` … `G8-fd.md`。

## 0. 口径与总量（凭据见 SURVEY.md §1-2）

- worktree `isla/.worktrees/memory-consistency` @ d643e0e isarch（md5 `b53f5bde0eb319484bb876ea27dda7e8`，`--features smt-thread-interrupt`）、rv64d.ir sha256 `33c2efef…`、配置 `riscv64_difftest_mem_excluded_pma.toml`（md5 `2c02b341…`，即 W15 修正 pma size 后的 green 基线配置：RAM 8TB 地图 + PMP NAPOT-RWX 钉死 + satp=0 + mmio_hole excluded + clint 关）、`limits_b12.toml`（fork 1/12、concretize）、`--timeout 55m --smt-timeout 1m`、`ISLA_RISCV_MODEL_TIMEOUT_MS=120s`；时间盒 600/1800/3600s 三档。
- 48 clause 中 45 有 JSON；AMO 确定性 panic 无 JSON；VLXSEGTYPE/VSXSEGTYPE 三档均超时无 JSON。
- 总分布（4124 gen）：Retire_Success 1251（30.3%）/ E_Load_Access_Fault 1135 / Illegal_Instruction 1012 / E_SAMO_Access_Fault 712 / Virtual_Instruction 10 / E_Load_Addr_Align 4；含访存事件 663；降级条目 0。zSTORE 24 成功/104 fault 与 W15 修正后基线逐数一致（交叉验证）。

## 1. 合并覆盖矩阵（按组）

| 组 | clause | 收敛结论 |
|---|---|---|
| [G1](/tmp/isla-memsolve-survey-20260927-125738/coverage/G1-scalar.md) 标量 | LOAD/STORE | ①可达出口全覆盖：四宽度成功+fault、w2 非对齐 2×1B 拆分、8 条 lh 跨 2^43 顶界"首字节成功+次字节 fault"、U/M 双态（含 MPRV）。③：LOAD rc=1（4 次 60s SMT 超时 @ mem.sail:42 is_aligned）致 w4/8 非对齐拆分成功 0 条；STORE rc=0 但 sh 对齐成功 0 条且 128 条无任何多事件写（纯 fork 预算）。④零。附域观察：`ldu`（funct3=111 非法编码）11 条因 union 参数域探索照印 |
| [G2](/tmp/isla-memsolve-survey-20260927-125738/coverage/G2-compressed.md) 压缩 | C_L*/C_S* 13 | ①B/H 宽度四形态全（对齐单访存、非对齐 2×1B 拆分、区外 fault、跨界部分读写后 fault）；imm/creg 域全量核验无越域。C_LB ⑤（Zcb 无 c.lb，三方一致）。③：C_LW/C_LD/C_LWSP/C_LDSP 全部中止于 `is_aligned_paddr`（mem.sail:42）60s 超时——LW/LD 缺 W/D 非对齐分块读与跨界部分读，LWSP/LDSP 连 PMA fault 都未及（可达性由同态 C_SWSP 反证）；读事件 size 为符号值致 `addr%size` 非线性。④嫌疑：C_SW/C_SD/C_SWSP/C_SDSP rc=0 正常终止却零非对齐分块写（fork 点已发生、子树无产出、无超时无报错）。方向验证：fault 占比 52-75% 落 G1 带内 |
| [G3](/tmp/isla-memsolve-survey-20260927-125738/coverage/G3-amo.md) AMO/LR/SC | AMO/LOADRES/STORECON | zAMO ④全缺（见 §3-1）；zLOADRES ①基本覆盖：LR.W/D × aq/rl/aqrl 六变体、成功 82/AF 143/Align 4——Align 独立检查定论见 §2-1；zSTORECON ①成功 45/AF 94，失配→rd=1 分支 ②（match_reservation="true" 钉死 + write_ram 丢 Bool 恒 true）；SC.B/H ⑤（lrsc_width_valid={4,8}，encdec 空被 finalize 丢弃）。保真度缺陷见 §3-4/3-7 |
| [G4](/tmp/isla-memsolve-survey-20260927-125738/coverage/G4-vec-unit.md) 向量 unit/mask | VLRETYPE/VMTYPE/VSRETYPE | ①除两缺口全：成功侧（全量/部分首寄存器/vstart 早退/VLM 尾写回/vl=0/空循环）、逐元素 fault 侧首元素+部分成功后异常（35/5/19 条，事件贴 2^43±ε）、非对齐拆分 28、vill、vstart 界值、vd%nf（VSRETYPE 一致见证）。④：VLRETYPE vd%nf 分支被走过但唯一见证与路径条件矛盾（物化 vd=16/nf=8 应继续执行）；③：VSRETYPE 早退真侧被 fork 预算吞（vs8r 需 vstart≥128 与 SEW=8 界 127 结构矛盾）；rc=1 为 4 次 SMT 60s 超时（JSON 完整）。口径勘误：whole-register 不读 vl；illegal_vd_unmasked 名不副实只查 vill |
| [G5](/tmp/isla-memsolve-survey-20260927-125738/coverage/G5-vec-seg-load.md) 段 load | VLSEG/VLSEGFF/VLSSEG + VLX | 前三 ①齐：vstart 越界（占 Illg 81-86%，物化 30..254 贴界）、vill、vd=v0、nf·EMUL>8、组未对齐、成功、逐元素 LAF；first-fault 全分支：i==0 立即异常 97 + i>0 吞异常+vl trim 100（77 零事件+23 部分读）+ AGNOSTIC/UNDISTURBED 尾段 52/48。VLXSEGTYPE ③：三档超时无 JSON，log 持续产出（158 条：131 Illg+27 LAF，nf1-8/双 mop/ei8-64 全档在跑）非死锁非 panic，吞吐劣化 12.6×，根因为逐元素符号索引地址+大索引组读的 SMT 膨胀；建议独占泳道 7200s+ 或 vs2 索引组提前 concretize。8 条/clause（约 5%）四约束复核合法却 Illegal 的未归因样本疑④（见 §3-3） |
| [G6](/tmp/isla-memsolve-survey-20260927-125738/coverage/G6-vec-seg-store.md) 段 store | VSSEG/VSSSEG + VSX | 前二 ①齐：成功 vstart>0/0×vm=0/1 四象限、首元素 AF（95+85）、部分成功 AF（13+10，含段内 j 循环中途与 stride=0）、misaligned 字节拆分写、四类 Illegal（vstart 占 91-93%）。VSXSEGTYPE ③：3600s 完成 300 条（12s/条=5-6×）后被 kill 全丢；log 侧 EMUL_index 范围（无前置 assert）真实可达 3 条、vs2 组对齐独立 14、部分写 AF 1；建议按 mop 拆跑+prestate 钉 vstart/vtype（砍 85% Illg 态）+增量落盘。3+3 未归因 Illg ④嫌疑（nf=8∧EMUL<0，prestate 复跑同编码形状既出 AF 又出 ILL 且与特权态相关）。--instruction-bits panic 见 §3-5。G6 §4.1 更正 G5 §4.3 的 Addr_Align 机制描述（见 §2-1） |
| [G7](/tmp/isla-memsolve-survey-20260927-125738/coverage/G7-cbo-fence.md) cbo/fence | ZICBOM/ZICBOP/ZICBOZ/FENCE 族/SFENCE 族 10 | ①出口级基本完备、无③无已触发④：ZICBOM 四类出口（CBCFE/CBIE Illg、区外 AF 54、区内成功 17 全 M 态——Machine 恒 true 证实）；ZICBOP 与 FENCE/FENCEI/FENCE_TSO 语义唯一出口实测 100%；ZICBOZ 成功带真实 64B 零写（证实 ram 别名 supports_cbo_zero）；SFENCE_VMA 五运行时出口全覆盖——S 态同编码 TVM 双向实证、M 态 4 条恰覆盖 asid/addr 四组合、VirtualUser VirI 真实可达 4 条；SINVAL_VMA 直通 SFENCE_VMA 分布逐项一致。②：satp=0 翻译/TLB、单区 PMA 属性拒绝、Svbare 编码级；VS 态 internal_error 未触发（潜在④：H 未支持）。⑤：无 CHERI 直通、CBO 强制块对齐、HINVAL 未实现 |
| [G8](/tmp/isla-memsolve-survey-20260927-125738/coverage/G8-fd.md) FD | C_FL*/C_FS* + LOAD_FP/STORE_FP | gen=0 根因收敛（非"FD 关语义不可达"）：路径全部真实执行完（错误剖面与整数同型逐项一致、FPR 上下文正常），被物化过滤器按 encdec=None 整批丢弃。Zcd 四条 ②：mstatus=0x600（FS=Off）关 encdec 守卫（assembly 映射无守卫故 asm 打印正常）——solve-state 绕过 decode，关 FD 造不出 Illegal_Instruction 只杀物化；mstatus 置 FS≠0 一行即恢复日志已执行分布。Zcf 四条 ②（更深一层）：assembly 映射 `when xlen==32` 编译期死，RV64 应从清单剔除。LOAD_FP ④：符号 width 直传 vmem_read 撞 `zeros()` 符号长度（vmem_utils.sail:139）0 存活（整数 LOAD 靠 match width 先 fork 常量幸免），叠加 ③ 60s 截断与 ② encdec 守卫。STORE_FP ②：160 条执行完、asm 四档全出、encdec 守卫全关；width=1（fsb）档 ⑤恒无编码 |

## 2. 两次重要勘误（多处注明，修正此前口径）

1. **`plat_enable_misaligned_access` IR 固化 true，TOML 同名键死配置**（rv64d.ir:10771-10775 为 IR 生成期 `let`，取 Sail config `memory.misaligned.supported` 默认值；`[const_primops]` 只能钉 primop、对 let 无效，配置文件内 `sys_pmp_count` 注释为同型先例）。后果：普通访存 Addr_Align 出口 ②结构性不可达；非对齐走 `split_misaligned` 拆分**且 B/H 宽度已覆盖成功**（lhu 奇地址拆 2×1B 成功为行为反证）；全 survey 仅有的 4 条 Addr_Align 均出自 **LR 的 res=true 无条件对齐检查**（vmem_utils.sail:125-129，不受该开关门控，ISA 规范要求）。G6 §4.1 据此更正 G5 §4.3"可达未成径"的机制描述（结论层面 0 条一致）。若验收需要 misaligned 报 Align，须重生成 IR（Sail config 层关闭），toml 无解。本条同时修订 W13 上报项⑤的前提——其"配置生效为 false"不成立，错位分歧源预测需按 IR 固化 true 重估。
2. **FD 真实闸门是 mstatus.FS，`sys_enable_fdext` 是死键**（rv64d.ir 中 0 次出现；本模型扩展开关已在 IR 生成期烘成 `hartSupports`，const_primops 键名无匹配则静默无效）。currentlyEnabled(Ext_D) 链上唯一假因素是默认 mstatus=0x600 的 FS=00（fdext_control.sail:19）。修复口径：registers.defaults 置 FS≠0（如 0x6600）即可恢复 Zcd 四条与 STORE_FP/LOAD_FP 的 2/4/8 档；Zcf 四条 RV64 剔除；同时建议删除死键 `sys_enable_fdext`/`__isla_always_aligned`（日志已告警）避免误导归因。

## 3. ④引擎缺陷清单（本轮最可行动产出）

1. **AMO min/max.q panic**：`primop.rs:1322 assert length<128`——`sail_unsigned` 把 ≥128 位位串 ZeroExtend 装进 `%i128`，`lt_int` 又是有符号 128 位比较，无符号值须 <2^127 故断言必炸；width=16（AMOCAS.Q 的 X_pair 128 位）× op∈{AMOMIN/MAX/MINU/MAXU} 触发。solve-state 按类型符号化不施加 `amo_encoding_valid`（非法 op×width 可自由探索），amoswap/add/xor.q 能跑通而 min/max*.q 全死；进程 panic 且 JSON 只在正常结束写盘 → AMO 12+ 出口全缺（日志丢失前已见 Addr_Align/AccessFault/Success/读写事件/全宽度形态，足证本可覆盖）。修复三选：(a) 比较模式改写为位向量原生 Bvult/Bvslt（根治，顺带消 ZeroExtend）；(b) fun_args 施加编码约束（顺带修 LR width∉{4,8} 与 SC.B/H 的探索后丢弃）；(c) limits 按 IR 源位置截断 width=16 子树。
2. **LOAD_FP 符号 width 撞 `zeros()` 符号长度**（vmem_utils.sail:139 `bits(8*'width)`），0 条存活；对照整数 LOAD 靠 `match width` 先 fork 常量宽度幸免。修法：引擎支持符号长度 zeros，或 clause 宽度常量化对齐 base_insts 写法。
3. **终值物化与路径条件脱钩**：VLRETYPE vd%nf 见证矛盾（物化 vd=16/nf=8 与 Illegal 路径条件矛盾）+ G5/G6 未归因 Illg（8/8/3/3 条，四约束静态复核全合法；G6 侧 prestate 复跑同编码形状既出 AF 又出 ILL 且与 cur_privilege/mstatus 相关）疑同根；G4 建议单开引擎议题复现（单 clause、fork=1 即现）。另 G2 广泛观察到"终值重解最后一次 check Sat:false 后仍保留缓存模型"。
4. **`is_exclusive` 只识别 AK_explicit 不识别 AK_arch**（sail lib read_write_v1.sail）：一切 `.aqrl` 变体（LR/SC/AMO）的访存事件 exclusive=false——LR.aqrl 保留读被标普通读（26 条）、SC.aqrl 条件写走无条件提交路径（16 条），属模型库/事件物化侧保真度缺口，直接影响重放比对。
5. **`--instruction-bits` panic**：d643e0e isarch 任何组合均 `smt.rs:2168 Could not get Z3 func_decl 101`（G6 新发现，与参数无关），阻断了未归因 Illg 的定向复现路径。
6. **W/D 宽度 store 零拆分写嫌疑**（G2 四 clause + G1 STORE 同型）：fork 点已发生而子树无任何产出、无超时无报错，外部证据不足归③，需引擎内部确认子树去向。
7. **独占写 value Bool 全 false 物化偏置**：`write_symbolic` 为每次写声明自由 Bool，本批 29/29 全物化 false（post-memory 空，形似"事件在、写未落"），"提交的独占写"形态 0 条属求解器偶然非系统枚举（G3）。

## 4. ②配置性不可达汇总

MMIO 分派（PMA 地图 RAM-only 先行拒绝 + mmio_hole excluded 判死 + clint/htif 关，三重独立）；PMP 拒绝（NAPOT-全1-RWX 钉死恒 None）；翻译异常（satp=0 恒 Bare，含 TLB 非空相关分支）；SC 失配（match_reservation="true" + write_ram 丢 Bool，rd=1 只能来自失配故不可达）；普通访存 Addr_Align（勘误 §2-1）；PMA 属性分支（misaligned_fault/权限拒绝，单区 ram 全放行）；EEW>elen（encdec when 钉死）与 EMUL 出界（前置 assert 剪枝，VSX 的 EMUL_index 除外——真实可达）；FD 物化守卫（勘误 §2-2）；VS 态 internal_error（H 未支持，isarch 未枚举该初始态，潜在④）。

## 5. ③预算截断汇总

VLXSEGTYPE/VSXSEGTYPE（吞吐劣化 5-12×，建议独占泳道 ≥7200s、增量落盘 JSON、vs2 索引组提前 concretize、按 mop 拆跑、prestate 钉 vstart/vtype）；C_LW/C_LD/C_LWSP/C_LDSP（符号 size 致 `addr%size` 非线性，is_aligned_paddr 60s 超时整体中止，JSON 完整但 W/D 分块读/SP fault 未及）；LOAD w4/8 非对齐拆分成功（rc=1 中止）；STORE sh 对齐成功与多事件写（rc=0 纯预算）；VSRETYPE 早退真侧；STORECON 20 条对齐 mod 查询超时（rc=1、JSON 完整）。

## 6. ⑤语义无此分支摘要

C_LB（Zcb 无此指令）；SC.B/H（lrsc_width_valid={4,8}）；STORE_FP width=1（模型恒 false，无字节级 FP 访存编码）；FENCE 族/ZICBOP 唯一出口；VMTYPE 对齐（宽度 1 恒对齐）；store 无 first-fault 变体；lr.rl not-implemented（(aq,rl)=(0,1) 构造不出）；无 CHERI 下 ext_data_get_addr 直通；CBO 强制块对齐；HINVAL 未实现；普通 store `Ok(false)→internal_error`（res=false 无 false 源）。

## 7. 下一步候选（均未实施）

AMO ④-1 修复（三选一）；FD 配置一行恢复（mstatus FS≠0）+ RV64 清单剔除 Zcf + 删除死键；终值物化脱钩（④-3）单开引擎议题；VLX/VSX 独占泳道复跑（按 §5 预算方案）；is_exclusive 保真度（④-4）与 --instruction-bits panic（④-5）修复后可解锁 G6 未归因定向复现。
