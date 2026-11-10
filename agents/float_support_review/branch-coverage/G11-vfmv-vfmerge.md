# G11 · VFMV / VFMERGE / VFMVFS / VFMVSF 分支覆盖对照（Sail 源码 vs 56cc 80416 case）

数据源：`isla/target/float-solve-evidence/branch-coverage-distribution-20260928/cases.tsv`（clause 名实际带 `z` 前缀）。四 clause 合计 38226 case = 26067 Illegal + 12159 Retire。

除 tsv 外，本组逐 case 读取了四个 run 的 solve 产物 JSON（`stage/output/rv64_z{VFMV,VFMERGE,VFMVFS,VFMVSF}.json` 的 `gen[].isa-state`，含 tsv 没有的 vstart/vtype/mstatus/test-ins-encdec），对每 case 重放 Sail guard 求值序做归因：**四 clause 全部 26067 条 Illegal 与 12159 条 Retire 的预测与实际 verdict 零不一致（mismatch=0）**，归因闭合。

关键约定：
- tsv 的 `rm` 列是 `fcsr[FRM]` 的解码名：空串 = FRM∈{5,6}（保留值，无名），`dyn` = FRM=7。fcsr 0x20/0x40/0x60/0x80 = rtz/rdn/rup/rmm，0xa0/0xc0/0xe0 = FRM 5/6/7。
- VLEN=128（由数据反证：VFMVSF Retire 含 SEW=16、vstart=32 的 case，界 8·VLEN/SEW−1=63 需 VLEN≥128；stage 产物名 `rv64d_v128_e64` 同证）。
- 本组四指令在 `vext_fp_vm_insts.sail` 中**不存在**（该文件是 vmfeq/vmfle 等掩码比较，FVVMTYPE/FVFMTYPE）；实际定义全部在 `vext_fp_insts.sail`。`vext_types.sail` 只有类型/枚举，guard 均在 `vext_fp_utils_insts.sail`、`vext_utils_insts.sail`、`vext_control.sail`。
- IR 56cc 以 `$ifdef SYMBOLIC` 版 execute 编译（下表"是否达到"按 SYMBOLIC 路径判定；`$else` C++ foreach 路径单列）。

## 0. 通用译码边界：encdec `when` 与 vm 位（四 clause 共用）

编码：funct6=010111（VFMV/VFMERGE 共享，bit25=vm 区分）或 010000（VFMVFS/VFMVSF 共享，bit25=vm、vs2 域区分）@ … @ 0b1010111。

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case-id | case 数 |
| --- | --- | --- | --- | --- | --- |
| when: Zvfh & SEW=16 | vext_fp_insts.sail:1836-1838(VFMVFS)/2584-2586(VFMERGE)/2685-2687(VFMV)/2764-2766(VFMVSF)；Zvfh 链 vext_control.sail:25 | SEW=16 译码命中 | 是 | 四 clause Retire 各含 sew=16 | Retire 内 sew16：VFMV 864 / VFMERGE 4320 / VFMVFS 21 / VFMVSF 576 |
| when: Zve32f & SEW=32 | 同上；Zve32f=vext_control.sail:18（依赖 Ext_F） | SEW=32 译码命中 | 是 | 同上 sew=32 | 720 / 3312 / 21 / 576 |
| when: Zve64d & SEW=64 | 同上；Zve64d=vext_control.sail:21 | SEW=64 译码命中 | 是 | 同上 sew=64 | 288 / 1152 / 21 / 288 |
| when:假（SEW=8） | 同上 | SEW=8 无任何 FP 向量编码，encode 方向 `zencdec_forwards` Pattern match failure → 记 Illegal（execute 未运行） | 是（仅 direct-negative） | VFMV 1,9；VFMERGE 1,12；VFMVFS 1,12；VFMVSF 1,9（vtype=0 或 0x2） | 8（每 clause 2） |
| when:假（mstatus.FS=Off） | currentlyEnabled(Ext_F)=fdext_control.sail:18（`mstatus[FS] != 0b00`）；Zve32f/Zvfh/Zve64d 经 vext_control.sail:18-25 传递 | SEW=32 但 F 关闭 → when 假 → 同上 | 是（仅 direct-negative） | 四 clause 各 case 2（vtype=0x10, mstatus=…0200/0400 → FS=0） | 4（每 clause 1） |
| vm 位分流：vm=1,vs2=00000 → VFMV；vm=0 → VFMERGE | vext_fp_insts.sail:2583(VFMERGE) vs 2684(VFMV) | 共享 funct6=010111 的两条 encdec，vm 决定 guard 集（VFMERGE 有 vd 红线/组对齐，VFMV 无 vd 红线） | 是 | 两组编码互斥覆盖 | VFMV 5475 / VFMERGE 30603 |

SEW/LMUL 与 FP 支持关系小结：decode-when 把 SEW 锁死到 {16,32,64} 且各绑定 Zvfh/Zve32f/Zve64d；SEW=8 完全拒绝；LMUL 不进 decode，只影响 num_elem（vext_control.sail:307）与寄存器组对齐（vext_utils_insts.sail:52）；flen=64 使 VFMVFS 的 `SEW > flen` 恒假。

## 1. zVFMV（vfmv.v.f，5475 = 3603I + 1872R；gen 5472 + direct-neg 3）

源码：`vext_fp_insts.sail:2681-2757`（encdec 2683-2687；SYMBOLIC execute 2690-2719；`$else` 2722-2753；assembly 2756-2757）。

### Illegal 归因分布（主因按 Sail 短路求值序：guard→init_masked_result）

| 主因 | 机制 | 数量 | 证据 case-id |
| --- | --- | ---: | --- |
| J: init_masked_result → get_start_element Err | vstart > 2^(3+vlen_exp−SEW_pow)−1 = 8·128/SEW−1（SEW16/32/64 → 63/31/15）；vext_utils_insts.sail:276-287，调用点 vext_fp_insts.sail:2708-2711 | 1872 | 3874, 4421, 3243（vstart 为 2^63 级巨大值） |
| F: valid_fp_op 的 rm∈{5,6,7} | illegal_fp_vd_unmasked（vext_fp_utils_insts.sail:37-39）→ valid_fp_op:16-22；FRM5/6/7 = 298/376/406 | 1080 | 1636(frm5), 2932(frm6), 935(frm7) |
| H: valid_reg_group(vd) 组不对齐 | vd % 2^max(0,LMUL_pow) ≠ 0；vext_utils_insts.sail:52-56，调用点 vext_fp_insts.sail:2696-2698 | 648（与 F 重叠另 452，任一命中 1100） | 1058(v1,lmul2), 4407(v1,lmul4), 216(v2,lmul8) |
| direct-neg: decode-when 失败 | 见 §0 | 3 | 1,9（SEW8）；2（FS=Off） |
| 合计 | | 3603 | |

### 分支枚举表

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case-id | case 数 |
| --- | --- | --- | --- | --- | --- |
| when 三真臂 + 假臂 | vext_fp_insts.sail:2685-2687 | 见 §0 | 是 | — | 真 5472 / 假 3 |
| guard: valid_vtype vill=1 | vext_fp_utils_insts.sail:37-39→vext_utils_insts.sail:31-33 | vill 置位拒绝 | **否**（全组 vill=0） | — | 0 |
| guard: valid_fp_op SEW∈[8,64] | vext_fp_utils_insts.sail:18 | SEW 越界拒绝 | 否（decode-when 先行，恒真） | — | 0 |
| guard: valid_fp_op rm=5 | vext_fp_utils_insts.sail:19-20 | FRM 保留 | 是 | 1636 等 | 298 |
| guard: valid_fp_op rm=6 | 同上 | FRM 保留 | 是 | 2932 等 | 376 |
| guard: valid_fp_op rm=7(dyn) | 同上 | FRM=DYN 编码 | 是 | 935 等 | 406 |
| guard: valid_reg_group(vd) 假 | vext_utils_insts.sail:52-56 | LMUL≥2 时 vd 未按组对齐 | 是 | 1058, 4407, 216 | 648 主因 |
| init_masked_result: get_start_element Ok | vext_utils_insts.sail:363-377（Ok 臂 368-373） | vstart 在界内继续 | 是 | 全部 1872 Retire（vstart 全 0） | 1872 |
| init_masked_result: Err → Illegal | vext_utils_insts.sail:366-367；vext_fp_insts.sail:2709-2711 | vstart 越界 | 是 | 3874 等 | 1872 |
| init_masked_result: `__isla_use_extra_ops` 真/假 | vext_utils_insts.sail:364,372-377 | IR 走 isla_init_mask 外部 pure；假臂走 default foreach | 真=是 / 假=否 | 真臂全体 Retire+J-Illegal | — |
| vector_select_masked（外部 pure） | vext_utils_insts.sail:380-390 | vl/vstart/tail 语义收进 isla_init_mask/isla_vector_select，源码级无显式 vl=0 分支 | 是（外部函数） | 1872 Retire（vl=0 1560 / vl>0 312） | 1872 |
| write_vreg/set_vstart(0)/RETIRE | vext_fp_insts.sail:2716-2718 | 写回 | 是 | 3560, 3870, 3364 | 1872 |
| `$else` foreach `mask[i]==1` 写 | vext_fp_insts.sail:2746-2748 | C++ 后端路径 | 否（IR 为 SYMBOLIC 版） | — | — |

### 未达分支
vill=1；SEW∈[8,64] 假臂；`$else` foreach；`__isla_use_extra_ops=false`；get_sew_pow 的 vsew∈4..7 断言路径（decode-when 先拒，本 root 不可达）。

### 维度覆盖小结
Retire 1872 全部 vd=v0、fs1=f0..f23、vta=0、vstart=0；vl=0/vl>0 = 1560/312；SEW 16/32/64 = 864/720/288；LMUL 覆盖 frac4/frac2/1/2/4/8；priv M/S/U。注意 **vd=v0 在 vm=1 编码下合法**（无红线），全组 1129 条 vd=v0 的 Illegal 均由 F/J 拒；vd≠v0 的 Illegal 2471 条由 F/H/J 拒。

## 2. zVFMERGE（vfmerge.vfm，30603 = 21819I + 8784R；gen 30600 + direct-neg 3）

源码：`vext_fp_insts.sail:2580-2677`（encdec 2582-2586；SYMBOLIC execute 2589-2624；`$else` 2627-2673；assembly 2676-2677）。execute 第一件事是 `get_start_element()` match（2591-2594），先于 guard if（2601-2604）。

### Illegal 归因分布

| 主因 | 机制 | 数量 | 证据 case-id |
| --- | --- | ---: | --- |
| B: get_start_element Err | vstart 越界（execute 最先求值）；vext_utils_insts.sail:276-287；vext_fp_insts.sail:2591-2594 | 1512 | 1263, 8341, 249 |
| D: vd==v0 红线 | illegal_fp_vd_masked（vext_fp_utils_insts.sail:32-34 的 `vd == zvreg`） | 7560（任一命中 7615，其中 55 例同时 vstart 越界落 B 主因；**与历史"7615 个 vd=0"逐数吻合**） | 10556, 9366, 10599 |
| F: rm∈{5,6,7} | valid_fp_op:19-20 | 7560 = 1617/1541/4402 | 13335(frm5), 16688(frm6), 21910(frm7) |
| G: valid_reg_group(vs2) 假 | vs2 组不对齐；vext_fp_insts.sail:2602 | 3240（任一 6379） | 22824, 21722, 26507 |
| H: valid_reg_group(vd) 假 | vext_fp_insts.sail:2603 | 1944（任一 9720） | 17844, 11166, 20037 |
| direct-neg: decode-when 失败 | 见 §0 | 3 | 1,12（SEW8）；2（FS=Off） |
| 合计 | | 21819 | |

F/G/H/D 多因叠加严重（短路序去重后如上）；9072 条 gen 缺 fcsr 键的状态（求解器在 encode 前即知非法、不物化 FP 态）全部落在 D/B：7615 含 vd=v0，1457 纯 vstart 越界。

### 分支枚举表

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case-id | case 数 |
| --- | --- | --- | --- | --- | --- |
| when 三真臂 + 假臂 | vext_fp_insts.sail:2584-2586 | 见 §0 | 是 | — | 真 30600 / 假 3 |
| get_start_element Ok 臂 | vext_fp_insts.sail:2591-2594；vext_utils_insts.sail:283-286 | vstart 在界 | 是 | 全部 Retire（vstart 全 0）+F/G/H/D 主因者 | 29088 |
| get_start_element Err → Illegal | vext_fp_insts.sail:2592-2593 | vstart 越界 | 是 | 1263, 8341, 249 | 1512 |
| guard: vill=1 | vext_utils_insts.sail:31-33 | vill 拒绝 | 否 | — | 0 |
| guard: vd==v0 | vext_fp_utils_insts.sail:33 | 掩码编码（vm=0）目的地不得为 v0（Sail 实现的红线） | 是 | 10556, 9366 | 7560 主因 / 7615 任一 |
| guard: SEW∈[8,64] 假臂 | vext_fp_utils_insts.sail:18 | — | 否 | — | 0 |
| guard: rm=5/6/7 | vext_fp_utils_insts.sail:19-20 | FRM 保留 | 是 | 13335/16688/21910 | 1617/1541/4402 |
| guard: valid_reg_group(vs2) 假 | vext_utils_insts.sail:52-56 | vs2 不按 EMUL 对齐 | 是 | 22824, 21722, 26507 | 3240 主因 |
| guard: valid_reg_group(vd) 假 | 同上 | vd 不按 EMUL 对齐 | 是 | 17844, 11166, 20037 | 1944 主因 |
| assert(SEW != 8) | vext_fp_insts.sail:2606 | decode-when 保证 | 否（不可达断言） | — | — |
| SYMBOLIC 体：isla_init_mask + 2×vector_select_masked（外部 pure） | vext_fp_insts.sail:2611-2619；vext_utils_insts.sail:357-390 | vstart/vl/tail/vm 语义全在外部函数；v0 掩码通道 vm_val 读 v0 | 是（外部函数） | 8784 Retire | 8784 |
| write_vreg/set_vstart(0)/RETIRE | vext_fp_insts.sail:2621-2623 | 写回 | 是 | 18465, 22729, 30225 | 8784 |
| `$else` foreach: i<start / 尾部(tail_ag UNDISTURBED\|AGNOSTIC) / 体(vm=1\|0) | vext_fp_insts.sail:2656-2667 | C++ 后端路径 | 否（IR 为 SYMBOLIC 版） | — | — |

### 未达分支
vill=1；SEW 范围假臂；assert(SEW!=8)；`$else` foreach 全部分支（i<start、尾部两臂、vm 两臂）。

### 维度覆盖小结
Retire 8784 全部 vd≠v0（vd=v0 的 7615 条全部 Illegal，红线自洽）、vstart=0、vta=0；vl=0/2551、vl>0/6233；SEW 16/32/64 = 4320/3312/1152；vs2 覆盖大量寄存器号（含对齐/不对齐）；fs1 覆盖多 f 寄存器。

## 3. zVFMVFS（vfmv.f.s，129 = 66I + 63R；gen 126 + direct-neg 3）

源码：`vext_fp_insts.sail:1832-1865`（encdec 1834-1838；execute 1840-1862，**无 $ifdef SYMBOLIC 拆分**，单版）。

### Illegal 归因分布

| 主因 | 机制 | 数量 | 证据 case-id |
| --- | --- | ---: | --- |
| F: rm∈{5,6,7} | illegal_fp_vd_unmasked（1845）→ valid_fp_op | 63 = 18/25/20 | 104(frm5), 24(frm6), 23(frm7) |
| direct-neg: decode-when 失败 | 见 §0 | 3 | 1,12（SEW8）；2（FS=Off） |
| 合计 | | 66 | |

### 分支枚举表

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case-id | case 数 |
| --- | --- | --- | --- | --- | --- |
| when 三真臂 + 假臂 | vext_fp_insts.sail:1836-1838 | 见 §0 | 是 | — | 真 126 / 假 3 |
| guard: vill=1 | vext_fp_utils_insts.sail:37-39→vext_utils_insts.sail:31-33 | — | 否 | — | 0 |
| guard: SEW∈[8,64] 假臂 | vext_fp_utils_insts.sail:18 | — | 否 | — | 0 |
| guard: rm=5/6/7 | vext_fp_utils_insts.sail:19-20 | FRM 保留 | 是 | 104/24/23 | 18/25/20 |
| guard: SEW > flen | vext_fp_insts.sail:1845 | flen=64、SEW≤64 | **否（本配置不可达）** | — | 0 |
| assert(num_elem>0 & SEW!=8) | vext_fp_insts.sail:1848 | decode 保证 | 否（不可达断言） | — | — |
| match 'm: 16→F_H(rd) | vext_fp_insts.sail:1854-1858 | 半字写回 | 是 | sew16 Retire | 21 |
| match 'm: 32→F_S(rd) | 同上 | 单字写回 | 是 | sew32 Retire | 21 |
| match 'm: 64→F_D(rd) | 同上 | 双字写回 | 是 | sew64 Retire | 21 |
| set_vstart(0)/RETIRE | vext_fp_insts.sail:1859-1861 | 写回 | 是 | 129, 85, 127 | 63 |

（源码不读 vl/vstart/vta——vfmv.f.s 恒取 vs2[0]，无相关分支。）

### 未达分支
vill=1；SEW 范围假臂；**SEW>flen**（flen=64 下恒假）；assert。

### 维度覆盖小结
Retire 63：fd 全部 f0、vs2 覆盖 v0..v17；SEW 16/32/64 = 21/21/21；vl=0 40 / vl>0 23（两者 verdict 同象，源码无 vl 分支，符合预期）；priv M/S/U。

## 4. zVFMVSF（vfmv.s.f，2019 = 579I + 1440R；gen 2016 + direct-neg 3）

源码：`vext_fp_insts.sail:2760-2807`（encdec 2762-2766；execute 2768-2804，单版）。

### Illegal 归因分布

| 主因 | 机制 | 数量 | 证据 case-id |
| --- | --- | ---: | --- |
| J: init_masked_result → get_start_element Err | vext_fp_insts.sail:2783-2786；vext_utils_insts.sail:276-287 | 360 | 98, 672, 218 |
| F: rm∈{5,6,7} | vext_fp_insts.sail:2773 → valid_fp_op | 216 = 87/70/59 | 569(frm5), 22(frm6), 78(frm7) |
| direct-neg: decode-when 失败 | 见 §0 | 3 | 1,9（SEW8）；2（FS=Off） |
| 合计 | | 579 | |

### 分支枚举表

| 分支 | 文件:行号 | 语义 | 是否达到 | 证据 case-id | case 数 |
| --- | --- | --- | --- | --- | --- |
| when 三真臂 + 假臂 | vext_fp_insts.sail:2764-2766 | 见 §0 | 是 | — | 真 2016 / 假 3 |
| guard: vill / SEW 范围假臂 | vext_fp_utils_insts.sail:18,37-39 | — | 否 | — | 0 |
| guard: rm=5/6/7 | vext_fp_utils_insts.sail:19-20 | FRM 保留 | 是 | 569/22/78 | 87/70/59 |
| guard 通过 → init_masked_result Ok | vext_fp_insts.sail:2783-2786 | vstart 在界 | 是 | 1440 Retire | 1440 |
| init_masked_result Err → Illegal | 同上 | vstart 越界 | 是 | 98, 672, 218 | 360 |
| `if mask[0] == 0b1` 真：result[0]=rs1 | vext_fp_insts.sail:2790 | 体元素写入（vstart=0 且 vl>0） | 是 | mask0=1 组 | 720 |
| `if mask[0] == 0b1` 假 | 同上 | vl=0 或 vstart>0 时元素 0 为 prestart/tail，不写 | 是 | mask0=0 组（含 155 例 0<vstart≤界） | 720 |
| foreach 1..n-1: tail_ag UNDISTURBED | vext_fp_insts.sail:2793-2799 | 尾部保持（vta=0） | 是 | vta=0 组 | 720 |
| foreach 1..n-1: tail_ag AGNOSTIC | 同上（2662 同款 TODO，两臂同值但 IR 中是两个 match 臂） | 尾部 agnostic（当前实现同值） | 是 | vta=1 组 | 720 |
| init_masked_result 内 `__isla_use_extra_ops` 真/假 | vext_utils_insts.sail:364,372-377 | 真=外部 pure，假=default foreach | 真=是 / 假=否 | — | — |
| write_vreg(LMUL=0)/set_vstart(0)/RETIRE | vext_fp_insts.sail:2801-2803 | 写回 | 是 | 1583, 940, 1336 | 1440 |

（LMUL 恒按 0 参与读写（2781/2801 传 0），无组对齐 guard，故无 G/H 类 Illegal。）

### 未达分支
vill=1；SEW 范围假臂；`__isla_use_extra_ops=false`。

### 维度覆盖小结
Retire 1440：vd 全部 v0（生成器维度，非约束；vd≠v0 的 558 条 Illegal 全由 F/J 拒）；SEW 16/32/64 = 576/576/288；vl=0/565、vl>0/875；vstart=0 1285、0<vstart≤界 155（覆盖"vstart 在界但 >vl"的 prestart 行为）；vta 0/1 各 720；priv M/S/U。

## 5. 全组结论

1. **Illegal 全量归因（26067 = 100%，零预测冲突）**：FRM∈{5,6,7} 8919（VFMV 1080 + VFMERGE 7560 + VFMVFS 63 + VFMVSF 216，主因口径）；vd=v0 红线 7560（仅 VFMERGE，任一命中 7615 与历史 vd=0 独审数吻合）；寄存器组对齐 5832（VFMERGE vs2 3240 + vd 1944 + VFMV vd 648）；vstart 越界 3744（VFMERGE 1512 + VFMV 1872 + VFMVSF 360）；decode-when 负例 12（SEW=8 ×8、mstatus.FS=Off ×4）。
2. **共享编码边界**：funct6=010111 由 vm 位分流——vm=1（vs2=00000）走 VFMV 无 vd 红线（1872 条 vd=v0 全部 Retire），vm=0 走 VFMERGE 带 `vd==zvreg` 红线（7615 条 vd=v0 全部 Illegal），两 clause 的 guard 差异被 case 集完整双向覆盖。
3. **vl/vstart/vta 执行语义**：vl=0 跳过、tail/vm 处理在 IR（SYMBOLIC）路径下全部收进 `isla_init_mask`/`isla_vector_select` 外部 pure 函数，源码级仅 VFMVSF 保留显式 `mask[0]`/`tail_ag` 分支且两臂均达（各 720）；VFMVFS 不读 vl/vstart，无相应分支，数据一致。
4. **未达分支（结构性，非生成器遗漏即配置不可达）**：vill=1（四 clause 无一 case）；valid_fp_op SEW 范围假臂（decode-when 先行拦截）；VFMVFS `SEW>flen`（flen=64 不可达）；VFMV/VFMERGE 的 `$else` C++ foreach 与 `__isla_use_extra_ops=false`（IR 用 SYMBOLIC/extra_ops 路径）；各 assert（decode 保证的不变量）。
5. **覆盖薄弱点**（若需补 case）：vill=1 状态、vta=1 的 VFMV/VFMERGE（当前 Retire vta 全 0，但该两指令 SYMBOLIC 路径无 vta 分支，仅 VFMVSF 已双向覆盖）、FS=Off 的 gen 正向 case（现仅 direct-negative 从 encode 方向覆盖）。

## 版本注记

- 产物 IR 56cc69a4 的构建源是**冻结树** `isla/target/float-solve-evidence/unified-backend-build/model-v4-amo-20260927/sail-riscv/`（model-build.json `model_head=f8ce849`，即子模块 HEAD f8ce849 + 当时未提交补丁；IR SHA 56cc69a4…见 `agents/float_support_review/solve-fix-architecture.md`）。本组归因以该冻结树核对。
- 当前工作树相对冻结 56cc 含后续 LMUL/unary、valid_reg_group Eq 热点等 perf 改动（`git -C sail-riscv diff --stat -- model/extensions/V/`：8 文件 +2034/−171，未提交）。对本组四指令：**guard 条件与分支集合三方（冻结 56cc / 工作树 / HEAD f8ce849）语义一致**——`vext_fp_insts.sail` 四段 execute 逐字同（工作树行号=冻结版+110：VFMERGE 2470→2580、VFMV 2571→2681、VFMVFS 1722→1832、VFMVSF 2650→2760）；其余差异为机械改写（`valid_reg_group` 余数改 `eq_anything`、`assert_lmul_pow` 改 strict 形状、valid_fp_op strict 化——冻结 56cc 与工作树同为 strict 版，HEAD f8ce849 为非 strict，短路语义等价且无 IR Jump 差异，见 `agents/findings.md` 1487 条）。
- 本文字号统一按**当前工作树** `sail-riscv/model/extensions/V/` 标注；引用冻结 56cc 源码时 vext_fp_insts.sail 行号减 110，其余文件行号相同或 ±1。
