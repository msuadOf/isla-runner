# E-exit：退出归类与负对照（2026-11-07）

**结论：按 design v2 §9.3、§9.4 的 E-exit 通过。** 五个 E0 正例、d-alias-control 均已重新生成 ELF 并实跑，全部 agree。错误期望、rd 翻位、V 清零保留成功期望均归为 xs≠expected，原因码正确；游离 GOOD 为 other-failure，指令上限为 limit。

此结论修订 E0 v1 的“必须打印 BAD”验收口径，不改写历史结果。E0 原日志保留。未重编 emu；E1—E4、UART 诊断及“DUT 错跳但 REF 不跟随”的推论未测。

## 实施与 TDD

- agree 要求单次 GOOD、PC 正向匹配 good_trap_ins、无 ABORT/limit、退出 0、实际 ELF 哈希匹配。哈希缺失或不符不能通过；运行前哈希不符直接 raise，运行后再次校验。
- 单次失败桩 PC 匹配 fail_<reason>_trap 时，无论 GOOD/BAD 均返回 xs!=expected，并返回 reason。超时、上限、多 HIT、缺 HIT、未知 PC 均不通过。
- build_case 保存 objdump，检查 check_memory 至 good_trap 顺序落入、禁止跳入块内部或 GOOD、禁止间接跳转；GOOD 前为内存比较分支。取消原 good_trap 尾部回跳，避免第二个直达 GOOD 的入口。
- GOOD 与 7 个失败桩均保留 li a0,0/1 和 0x0005006b。检查 8 个 XSTrap 的地址集合恰好等于登记出口、失败符号及其地址唯一、各桩前置 a0 编码正确。

设计 §9.3“全程序只有 GOOD 桩一条 0x..06b”若按字面理解，与同节“保留失败桩 .4byte 0x0005006b”矛盾。本次按同节完整出口契约解释：**GOOD 出口唯一，另有 7 条登记失败出口，禁止额外 XSTrap**。没有修改 design.md。X2 是故意绕过生产生成入口手工编译的破坏性探针，不能作为生产 ELF；其 case.json 明确标记。

原 9 项测试加 3 项回归共 12 项通过。红灯见 output/exit/tdd-red.log；绿灯见 tdd-green.log。真实 X4 首轮暴露 emu 打印字面量 `EXCEEDING CYCLE/INSTR LIMIT`，原正则只覆盖独立 CYCLE/INSTR；补先行测试 tdd-red-limit.log 后修正，tdd-green-limit.log 12/12 通过。代码变化后旧 PASS 曾退为待复验，最终表全部来自修正后的重新运行。首轮完整产物保留在各 *-first 目录及 results-first.json，不用首轮冒充最终通过。

## 最终实跑

| 例 | 退出码 | 桶 | 原因码 | PC 符号 | 耗时 |
| --- | ---: | --- | --- | --- | ---: |
| a | 0 | agree | — | `good_trap_ins` | 3.527s |
| b | 0 | agree | — | `good_trap_ins` | 2.776s |
| c | 0 | agree | — | `good_trap_ins` | 3.780s |
| d | 0 | agree | — | `good_trap_ins` | 3.082s |
| e | 0 | agree | — | `good_trap_ins` | 3.397s |
| d-alias-control | 0 | agree | — | `good_trap_ins` | 3.024s |
| b-wrong-expected | 0 | xs!=expected | unexpected_trap | `fail_unexpected_trap_trap` | 4.386s |
| a-wrong-rd | 0 | xs!=expected | rd | `fail_rd_trap` | 4.483s |
| n1-v-zero | 0 | xs!=expected | unexpected_trap | `fail_unexpected_trap_trap` | 3.331s |
| n1-prime | 0 | agree | — | `good_trap_ins` | 5.232s |
| stray-good | 0 | other-failure | — | `无` | 2.574s |
| instruction-limit | 0 | limit | — | `无` | 31.697s |

X1：另对 output/e0/ 的 7 份日志复判，6 agree、b-wrong-expected 为 xs!=expected(unexpected_trap)，详见 output/exit/reclassified.json。复判核对现存原 ELF 哈希，不能代替最终实跑。X2：.Lstray 不进入 nm，额外 0x0000006b 使 emu 打印 GOOD/退出 0，退出 PC 不匹配登记符号，正确拒绝。X3 为 a-wrong-rd；X4 自环加 -I 10000，原始日志包含 EXCEEDING CYCLE/INSTR LIMIT，退出 0；X5 为 a。N1′ 为 V=0 且期望 PF，仍 agree。每例只有一个 bucket。

## 环境与复现

沿用 E0 锁定环境：emu SHA-256 `871416926352103051fce0efac7bf219602547c0852d5aa24af0c01a35ea85ee`；NEMU SO `9188e7dda30709962f0bfbc1dd87cea73d88a18c92c30892f93ed529c22def43`。运行前检查两者哈希，使用原 SO，无观测器。GCC 沿用 riscv64-unknown-elf-gcc 14.2.0。每份 case.json 保存本轮 ELF 哈希、符号和编译命令；result.json 保存 emu argv、退出码、耗时、桶与原因码，difftest.log 保留完整日志，objdump.txt 保存反汇编。来源与哈希另见 output/exit/environment.json；本轮代码文件哈希见 output/exit/code-sha256.json。

```sh
cd difftest-xiangshan
PYTHONDONTWRITEBYTECODE=1 PT_DECODE_DIR=../../isla-enumerate/agents/path_merge_call_support/pt_decode \
  python3 -m unittest tests.test_paging_replay
cd ..
PYTHONDONTWRITEBYTECODE=1 python3 output/exit/run_exit.py
```

单次 emu 600 秒上限，串行；无超时。再次运行前换用空输出目录，避免覆盖最终证据。驱动复用 E0 的 case.json 输入，调用当前 build_case/run_probe，不做地址重定位新设计或平台改写。没有 git 写操作，所有新增运行产物留在本工作树 output/。
