# 浮点向量 lane 纯化实施与验证

本记录对应 [性能边界](solve-fix-performance.md)第9–10节已审定的第一组12个 clause，随后获批的 VFMV/VFMERGE、三组转换与 VFUNARY1 sqrt/class。生产文件限 `sail-riscv/model/extensions/V/vext_fp_utils_insts.sail`、`vext_fp_insts.sail`、`vext_fp_vm_insts.sail`；测试在 `sail-riscv/test/symbolic_fp/solve_vector_lanes/`。本轮不改共享掩码初始化、归约、BF16 或估算算法。

## 实施

- 12个普通算术/FMA/widen/比较 clause 的 SYMBOLIC 数值 loop 使用无状态 `(fflags, bits/bool)` tuple。每个选定 opcode 仅求当前运算；数据经 `vector_select_masked(mask, initial_result, candidates)` 或比较位的 `masked_select` 合并，所有转换与算术 flags 先 OR 再按 mask 以 ITE 屏蔽，写目标前一次 `accrue_fflags`。合法性、`init_masked_result[_cmp]`、写回和 `vstart` 保留原语义。非 SYMBOLIC clause 与原带累计接口完整保留。
- min/max 保留 quiet 比较 flags、NaN/±0 的原优先次序，使用严格 Bool 与 total 位串 ITE。gt/ge 仍为 NV 则 false，否则分别取反 le/lt。`fp_widen_pure(rm, narrow)` 显式传 RM，转换的 NV 连同最后运算 flags 累计。
- VFMV 对既有初始化 mask 广播 scalar；VFMERGE 用 `isla_init_mask` 构造 body mask，先按原 v0 mask 选 scalar/vs2，再按 body mask 保留原目标。两个后端的 fractional `real_num_elem = num_elem / (0 - LMUL_pow)` 原公式均未改。
- VFUNARY0/VFWUNARY0/VFNUNARY0 的选定转换调用原 tuple 入口；六个窄整数饱和适配在 SYMBOLIC 使用位串等值和 ITE 返回原饱和值/原flags或NV。SEW=8 下原本只在首个 active lane 报非法的 VFW/VFN 组合继续走旧 loop，故全 inactive 仍合法。
- VFUNARY1 的 sqrt 使用原 `riscv_f* Sqrt` tuple；class 用 `float_decompose` 字段和严格 Bool 拼10位 onehot，flags=0。Recip7/Rsqrte7 留在原 mask loop；FVFTYPE 中 slide1up/down 也保留原 loop，避免 eager 索引/断言。
- SYMBOLIC 纯 helper 的直接位串比较已改显式 `eq_anything`/`not_bool`，范围只含 min/max ±0、gt/ge NV、class 字段和窄整数饱和；NaN 继续调用共享 `ieee_is_nan`。原有通用分类和非 SYMBOLIC 包装未改。

## 红绿与小 IR 证据

`check_clauses.py`、`check_move_merge.py`、`check_unary_clauses.py` 分别先在无 SYMBOLIC 定义时失败，实施后通过；它们只守护源结构。共享 core 冻结为 `6a53eb01…d6faeb` 后，Sail 0.20.1 对完整 `model/riscv.sail_project` 使用 `--strict-var --strict-bitvector --strict-exponentials --all-modules --just-check`，SYMBOLIC/非 SYMBOLIC 均退出0。此次严格型检是当前源码的语法/类型门槛，不是正式 IR 验收。

真实 helper 小 IR 由 `build_helper_probe.py` 从当前生产纯 helper 与旧 min/max/gt/ge、六窄适配函数体生成；old 小函数只移除 `accrue_fflags`、返回原 `(flags,result)`，以便比较数值与 flags。测试的旧分类 stub 使用位级等价的 NaN/±0 谓词，因此路径数只描述此 fixture，**不代表生产旧 helper 的实际路径数**。每条完成路径先查 SAT，再约束新旧值或 flags 不等并查 UNSAT；`runner.rs` 对零完成路径和所有 `new_*` 非单路径硬失败，日志检查也要求完整入口。

共享 core 冻结后重生成的小 IR 49项全部退出0，涵盖 f16/f32/f64 未知位串 min/max/gt/ge 新函数各1路径，旧提取函数各12/12/2/2路径且逐路径差异 UNSAT；三个格式 class 的旧函数各10路径、新函数各1路径且逐路径差异 UNSAT，exact-onehot 反例 UNSAT，每格式10类定向值通过；六窄适配旧函数各2或3路径、新函数各1路径，逐路径差异 UNSAT。f16 min/max 的 qNaN、sNaN、±0 和完整五位 flags 定向也通过。`check_pure_ir.py` 验证12个纯 helper IR 函数体不调用 `eq_bits`/`neq_bits`。本次 IR SHA-256 为 `6dbb358e…73e75d8f`，runner 为 `89b00a87…cd2f188`，plugin 为 `c4eccb06…1d0e22f6`；外部原始证据目录标识 `isla-vector-helper-probe-20260926`，含 `helper_probe.ir`、`run.log`、`hashes.txt`，最后一份文件逐项记录全部 include 源、生成器、插件和 runner 的完整 SHA-256。它验证了这些小函数与隔离形状，不替代正式指令的完整状态差异。

`move_probe.sail` 用真实 `isla_vector_select`、`isla_init_mask` primop 比较未知 mask、scalar、src、old：8 lane VFMV 原256路/新版1路；VFMERGE 在固定 `(start,end,real)=(1,5,4)` 原8路/新版1路，另测 VL0、prestart、fractional real=2、full body 四种固定 bound，原1/8/4/256路、新版各1路。所有旧路径 SAT 且差异 UNSAT。它验证这些具体形状，不能作为未知所有 vtype/LMUL 的正式指令验收；全状态回归待新生产 IR。外部 `move_run.log` 和 `move_hashes.txt` 保存输出与哈希；小 IR SHA-256 为 `3554abbb…fe6799aa8`。

可复现命令（在仓库根目录执行，`OUT`、`PLUGIN` 为本机输出目录和 Isla plugin 路径）：

```sh
bash sail-riscv/test/symbolic_fp/solve_vector_lanes/build_runner.sh "$OUT/runner" isla/isla-lib
bash sail-riscv/test/symbolic_fp/solve_vector_lanes/run_helper_probe.sh "$OUT/helper" "$PLUGIN" "$OUT/runner/target/release/vector_helper_runner"
bash sail-riscv/test/symbolic_fp/solve_vector_lanes/run_move_probe.sh "$OUT/move" "$PLUGIN" "$OUT/runner/target/release/vector_helper_runner"
```

## 冻结与后续门槛

三个 V 生产文件已交独立性能审查：其在独立目录重跑生产提取器，确认 fixture 与当前源逐字一致、49入口及12个纯IR体门槛通过，报告标识 `isla-vector-helper-final-independent-20260926/report.json`。生产 SHA-256：`vext_fp_utils_insts.sail` 为 `8a642a1d…98379d`，`vext_fp_insts.sail` 为 `b5188c7c…6c665`，`vext_fp_vm_insts.sail` 为 `0985a596…cc9c`。16个 `vext_fp_insts.sail` 和2个 `vext_fp_vm_insts.sail` 的非 SYMBOLIC clause 函数体与未改前 HEAD 逐字节相同（忽略首尾空白）。已向 IR 集成人发送各函数旧/新源码起始行和三文件完整哈希，暂停修改这三文件。

新正式 IR、严格配置绑定、全状态指令差异与官方77入口复验仍属后续集成门槛；小 IR 的 PASS 不代表这些门槛已经通过。
