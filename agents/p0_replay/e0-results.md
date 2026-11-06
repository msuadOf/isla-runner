# E0 框架探针结果（2026-11-07）

**结论：五个正例通过，E0 整体验收不通过。** 错误期望已进入 C2 失败桩，但现有 emu 把 `0x0005006b` 仍报为 GOOD，未达到“必须 HIT BAD TRAP”的要求。未替换既定方案，未重编 emu。

| 核心问题 | 本次结论 | 依据与边界 |
| --- | --- | --- |
| 保留位 PF 会在 NEMU 比对前被 L2TLB 检查器 ABORT 吗？ | **当前 emu 没有 ABORT**；不能推广到启用该检查器的构建 | c 正常进入 handler，C1/C2 通过；生成头文件定义了 `CONFIG_DIFFTEST_L2TLBEVENT`，但安装检查器还需 `DEBUG_L2TLB`。后者在配置中被注释；实际二进制 `Difftest::init_checkers()` 也没有 L2TLB 安装代码。 |
| PBMT / N / 未对齐超级页 PF | **未测** | 输入集合中有这些形状；本轮只选 E0 要求的五个代表，没有运行这三类。不能凭保留位结果推断。 |
| NEMU 对 PA ≥ 2^48 是截断还是 AF？ | **本次判别输入报 AF，未截断成有效 RAM** | 在成功样本的 L0 PPN 上仅置 bit 36，PA=`0x1040043000000`，低 48 位为已初始化 RAM `0x40043000000`。XiangShan=NEMU：cause 5，mtval=`0x20000000`，没有 `guided_exec`。此结论限于本次地址与 SO。 |
| 成功样本是否 GOOD？ | **是，限定 PASS** | a 的退出 PC=`0x80000244`，符号为 `good_trap_ins`；rd、PTE 与数据回读检查均经过。 |
| PF 在 C1 下能否一致通过？强制同步是否实际发生？ | **是，已动态确认** | b/c 的只读 SO 观测记录 `force=1 cause=13 mtval=0x20000000`；NEMU 返回相同 CSR。C1 的“一致”不构成独立 PF 预言机。 |
| C2 能否检出错误期望，并输出 BAD？ | **能检出；BAD 输出要求 FAIL** | b 的期望改成成功后，退出 PC=`0x80000224`，落在 `fail_unexpected_trap_trap`；但 emu 打印 GOOD、退出 0。最终解析器将其判为 `xs!=expected`，不计通过。 |

## 运行结果

指令均为 `ld x2,0(x1)`，x1=`0x20000000`，satp=`0x8000000000080200`。所有运行串行进行，单次上限 600 秒；没有超时。

| 代表 | 原 sample_id | 主跑退出码 | emu 原始输出 | 退出 PC 对应符号 | L2TLB failed / ABORT | XiangShan mcause / mtval | NEMU mcause / mtval | 主跑耗时 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| a | 9680 | 0 | GOOD | `good_trap_ins` | 无 | 0 / `0x0` | 0 / `0x0` | 4.434s |
| b | 1017 | 0 | GOOD | `good_trap_ins` | 无 | 13 / `0x20000000` | 13 / `0x20000000` | 3.027s |
| c | 1010 | 0 | GOOD | `good_trap_ins` | 无 | 13 / `0x20000000` | 13 / `0x20000000` | 2.626s |
| d | 5072 | 0 | GOOD | `good_trap_ins` | 无 | 5 / `0x20000000` | 5 / `0x20000000` | 2.625s |
| e | 129 | 0 | GOOD | `good_trap_ins` | 无 | 5 / `0x20000000` | 5 / `0x20000000` | 2.776s |
| b-wrong-expected | 1017 | 0 | GOOD | `fail_unexpected_trap_trap` | 无 | 13 / `0x20000000` | 13 / `0x20000000` | 2.874s |
| d-alias-control | 9680 | 0 | GOOD | `good_trap_ins` | 无 | 5 / `0x20000000` | 5 / `0x20000000` | 3.690s |

表中的 NEMU CSR 来自只读代理的 `difftest_regcpy` 观测。DUT CSR 来自 handler 的 `csrr s0,mcause`、`csrr s1,mtval` 提交值；直接原 SO 的 commit trace 与代理运行结果相同。所有主跑均没有实际 BAD，因此“BAD PC”均不适用；负对照有明确的**错误 GOOD 的失败 PC**。

| 代表 | 输入特征 | 来源与转换 |
| --- | --- | --- |
| a | L0 叶，数据 PA=`0x40043000000`，值=`0x0101010101010101` | 原始 Isla 9680，未构造 |
| b | L0 叶形态 V=0，原 PTE=`0x2001010101010102` | 原始 Isla 1017，未构造；该 PTE 还含 PBMT，但 V=0 已足以产生 PF，不能拿它单独验证 PBMT |
| c | L0 PTE=`0x0140010101010107`，[58:54] 非零 | 原始 Isla 1010，未构造 |
| d | L0 PPN=`0x10080000000`，PA=`0x10080000000000` | 原始 Isla 5072，未构造 |
| e | 下一级 PTE PA=`0x80000000000`，位于 [2^43,2^48) | 原始 Isla 129，未构造 |
| b-wrong-expected | b 的硬件输入不变，只把 C2 期望写成成功 | 原始输入加错误期望，不冒充新的 Isla 输出 |
| d-alias-control | a 的 L0 PPN[36] 置 1；低位别名数据作为诱饵初始化 | **构造变体，不是 Isla 产出**；构造步骤见 `output/e0/extra_probes.py` |

五个代表读到的 PTE/数据均已落在设计允许的 DRAM，且待规范化位恰好为零，所以这五例的实际地址映射和值转换是恒等的。低端 RAM 搬迁、非 RAM 指针搬到 2^44、[60:59] 清零、指针 U/A/D 清零已由定向测试覆盖，不能据此声称已完成真实样本全量搬迁验收。

`d` 单独不能排除截断：其低 48 位仍为非 RAM，截断和拒绝均可能 AF。因此补充了 `d-alias-control`；该例若截断为低 48 位，将读到有效数据并与 DUT 的 AF 分歧。本次仍一致报 AF，且 C1 没有强制同步调用。

## 两项设计事实修订

**L2TLB 事件与检查器启用是两回事。** 只读检查发现：

- `build/generated-src/difftest-state.h:133` 定义事件宏；二进制也包含 `L2TLBChecker::check` 和错误字符串。
- `difftest/config/config.h:119` 注释了 `DEBUG_L2TLB`。
- `difftest.cpp:406-412` 要求两个宏同时满足才安装检查器。
- 实际 emu 的 `Difftest::init_checkers()` 反汇编有 L1TLB 安装、没有 L2TLB 安装；证据在 `output/e0/init-checkers.asm`。

因此，设计第 6 节关于保留位导致框架 ABORT 的推测，**在当前 emu 下不成立，因为该检查器没有启用**；启用后的行为仍未测。当前不需要重编一个关闭检查器的 emu。

若后续必须得到**连事件宏都不存在**的构建，方案是：在新的隔离源码副本中给 `L2TLB.scala` 的 `DiffL2TLBEvent` 发射块增加参数门控，关闭该事件，重新生成 RTL 与头文件，再用原 MinimalConfig 构建流程构建 emu；验收生成头文件没有 `CONFIG_DIFFTEST_L2TLBEVENT`，并重新执行 E0。只关闭 `DEBUG_L2TLB` 已足以停止检查器，但不会移除事件宏。本轮没有执行任何这些构建。

**`rs1=a0` 的编码正确，不代表当前 emu 会把它用作退出码。** 反汇编确认失败桩是 `li a0,1; .4byte 0x0005006b`，负对照落在该桩却报 GOOD。只读源码和生成 RTL还显示：XSTrap 对应 ALU 功能码 `0x7f`，当前 ALU 的结果选择没有为该值选择 rs1，ROB 则以执行结果作为 trap code。这支持问题位于现有 emu 的退出码实现，而非页异常自检分支。最小可靠结论是上述运行事实，不能沿用设计第 2 节“a0=1 必然 BAD”的说法。

没有改成超时、其他指令或改写日志来制造 BAD。后续需单独决定修复受测 emu 的 XSTrap 结果传递，或修订失败出口契约；本轮保持既定编码，整体验收记 FAIL。

## 实现与测试

新增 `difftest-xiangshan/paging_replay.py`，仅支持 E0 固定 Sv39 ld 输入；提供 `convert`、`build`、`run`、`classify`。严格复用外部 `pt_decode`，以及 pipeline 的 `pmp_open_setup`、`LINKER`、`elf_alloc_ranges`、`memory_overlaps_ranges`。拒绝损坏解码、result_mismatch、未知内存和非空 TLB，不做替代输入。

生成程序在 M 态、satp=0 时用 sd 初始化 PTE/数据；依次写 satp、sfence.vma、带 MPRV/MPP 的 mstatus、恢复 GPR、执行 ld。成功和异常路径先清 MPRV，再检查 rd 或 cause/tval/mepc，以及全部初始化内存。清零 medeleg/mideleg/menvcfg；handler 4 字节对齐；所有 ELF 分配节位于 [0x80000000,0x80100000)。

原 `pipeline.run_case` 会裁掉成功日志并在超时后重跑，不能满足本轮完整取证。因此新文件复用了它的命令形式与进程组终止办法，保留完整日志，超时不重跑。原 pipeline 和 `analyze_trap_results.py` 均未修改。

| 验证 | 结果 | 证据 |
| --- | --- | --- |
| 测试先于实现 | RED：模块尚不存在 | `output/e0/tdd-red.log` |
| 初始转换/汇编/归类测试 | 6/6 PASS | `output/e0/tdd-green-first.log` |
| 错误 GOOD 回归 | 先 RED，再 GREEN | `output/e0/tdd-red-false-good.log`、`tdd-green-false-good.log` |
| 最终定向测试 | **9/9 PASS**，包含真实链接与 ELF 范围检查 | `output/e0/tests-final.log` |
| 五个正例的 C1+C2 | **5/5 限定 PASS** | 各例主跑、提交与观测日志；`output/e0/evidence.json` |
| 错误期望必须 HIT BAD | **FAIL** | `b-wrong-expected/difftest.log`、符号与观测日志 |
| 外部 Isla check-samples / C3 | **未测** | 本轮不承担 E3 |
| PBMT、N、未对齐超级页；启用 L2TLB 的构建 | **未测** | 不从当前运行推断 |

曾尝试不经完整复位引导直接调用 NEMU SO；未到达退出点，诊断在 `output/e0/d/native-nemu*.log`。该尝试不用于任何结论。后续使用只读转发代理，在真实 emu 的初始化和运行过程中观测 REF，避免另建初始化模型。

## 来源与环境

以下路径均相对本工作树根目录；实际解析后的绝对路径同时记录在 `output/e0/environment.json`。

| 项目 | 路径或版本 | SHA-256 |
| --- | --- | --- |
| 工作树 | 分支 `feat/p0-replay`，根 HEAD `cf4cedf74ef32262d139f9b0b81a8c0b4f235dff` | 未做 Git 写操作 |
| XiangShan | `../../difftest-xiangshan/xiangshan`，HEAD `a13efc8775abb093e23727772a562f0605380685` | emu 自报同一 commit，构建时间 2026-09-29 02:15:05 |
| emu | `../../difftest-xiangshan/xiangshan/build/emu`，链接到 `build/verilator-compile/emu` | `871416926352103051fce0efac7bf219602547c0852d5aa24af0c01a35ea85ee` |
| NEMU SO | `../../difftest-xiangshan/xiangshan/ready-to-run/riscv64-nemu-interpreter-so` | `9188e7dda30709962f0bfbc1dd87cea73d88a18c92c30892f93ed529c22def43` |
| samples v1 | `../isla-enumerate/output/stride-validation/sv39-1-final/samples.jsonl` | `79beb427deba352d21d0f6dc9ed12cc9b13545cad792881775f3c43b2bc53bbd` |
| pt_decode | `../isla-enumerate/agents/path_merge_call_support/pt_decode/pt_decode.py`，按路径只读导入 | `2ddc69915d0cde369759160182dd34d2ea7191fffc258ed93ab167645a4d7e47` |
| GCC | `riscv64-unknown-elf-gcc (14.2.0+19) 14.2.0`；主机 GCC 15.2.0 | `output/e0/versions.json` |
| 只读 NEMU 观测器 | `output/e0/nemu_observer.so`，转发到原 SO，未修改 guide 或寄存器 | `04ebe5b124a5789a0401b31c5123fc66222ef4f86959ad5f0104d21c1a4a5301` |

`decode-sv39-1/merge/page_tables.json` 的输入哈希与本次 merge JSONL 一致。顶层 `decode-sv39-1/page_tables.json` 对应 fork，哈希不同，不把它混作本次样本账本。merge 输入有 16592 条，多数带 truncated 标志；五条所用读集均通过严格解码，此事实不代表集合完整性验收。

源码、生成配置和两份 page_tables 的快照及哈希见 `output/e0/environment/`、`environment-sources.json`。各例 `case.json` 保存完整输入、解码、地址映射、期望、导入哈希、编译命令、ELF 哈希和符号。

## 复现命令

从本工作树根目录运行；不需要本工作树有 XiangShan checkout：

```sh
export PYTHONDONTWRITEBYTECODE=1
export PT_DECODE_DIR="$(realpath ../isla-enumerate/agents/path_merge_call_support/pt_decode)"
export E0_SAMPLES="$(realpath ../isla-enumerate/output/stride-validation/sv39-1-final/samples.jsonl)"
export XIANGSHAN_EMU="$(realpath ../../difftest-xiangshan/xiangshan/build/emu)"
export XIANGSHAN_DIFF_SO="$(realpath ../../difftest-xiangshan/xiangshan/ready-to-run/riscv64-nemu-interpreter-so)"

python3 -m unittest discover -s difftest-xiangshan/tests -p test_paging_replay.py -v
python3 output/e0/run_e0.py
python3 output/e0/trace_probes.py
python3 output/e0/extra_probes.py

gcc -shared -fPIC -Wall -Wextra -Werror \
  -o output/e0/nemu_observer.so output/e0/nemu_observer.c \
  -Wl,--no-as-needed "$XIANGSHAN_DIFF_SO" -ldl
python3 output/e0/observe_probes.py
```

观测器只转发 API 并打印 REF CSR/guide；原始主跑均直接使用原 SO。两类运行的退出码与退出 PC 一致。每次原始命令和耗时分别保存在 `results.json`、`trace-runs.json`、`observer-runs.json`。

单例公开入口示例：

```sh
python3 difftest-xiangshan/paging_replay.py convert \
  --input "$E0_SAMPLES" --sample-id 9680 \
  --pt-decode-dir "$PT_DECODE_DIR" --output output/e0/cli-a
python3 difftest-xiangshan/paging_replay.py build \
  --case output/e0/cli-a/converted.json --output output/e0/cli-a
python3 difftest-xiangshan/paging_replay.py run \
  --case output/e0/cli-a/case.json --timeout 600
```

主跑命令均为 `emu -i output/e0/<代表>/program.elf --diff NEMU_SO`，运行 cwd 为该代表目录，保证运行器附带文件也留在 `output/e0/`。每个 emu 使用现有构建固有的仿真线程数，外部始终单例串行。没有重编 emu，没有写其他工作树或 `/home`。
