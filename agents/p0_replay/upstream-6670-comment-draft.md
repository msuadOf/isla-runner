# 向 XiangShan #6670 补充评论的草稿（2026-11-07，未发布）

状态：**草稿，尚未发出。** 评论会以用户的 GitHub 账号公开发布，须用户确认后再发。

## 背景

上游已有 [OpenXiangShan/XiangShan#6670](https://github.com/OpenXiangShan/XiangShan/issues/6670)（2026-10-05，open，官方回复 “we will look into this”）。它报告：叶 PTE 的 PPN 超出物理地址宽度、且权限（U/SUM/MXR、R/W/X）不满足时，XiangShan 报 access fault，规范、Spike、NEMU 报 page fault。本仓库 fuzz P1b 发现的 14 个分歧与之同根。

#6670 只覆盖权限类。本仓库多出两类可补充的信息：**A=0**（Svade 下应报 page fault）和 **STORE 时 W 位满足但 A=0 / D=0**。另外 #3453（香山自己的 L2TLB 异常修复）写明 `pmp_af > {pf or gpf} > ppn_af`，与观察到的结果相反，值得询问。

## 数据来源

- 来自 fuzz P1b：5000 个变异体中 14 个分歧，见 [fuzz-p1b-results.md](fuzz-p1b-results.md)。
- 具体 PTE 取自 `output/fuzz-p1b/sv39-*/mismatches.json`（未入库）。
- 被测 XiangShan 源码 HEAD 为 `a13efc87…`，emu 构建身份已核实，见 [agents/findings.md](../findings.md) 对应条目；**不是 #6670 所用的最新 `09453ff8`**，评论里需说明，或先在最新提交上复验。
- 可附的复现 ELF 在 `output/fuzz-p1b/sv39-load/replay/mutant-1012` 等目录。发评论前需决定是否附上。

## 评论正文（英文，待确认）

```markdown
Thanks for this report. We hit the same root cause from a different direction (model-based page-table test generation, replayed on the XiangShan emu and compared with NEMU), and it also affects checks that are not listed in the table above: **A=0** (and D=0 for stores), not only U/SUM/MXR and R/W/X.

Setup: S-mode, Sv39, `sstatus.SUM`=1, MXR=0, a single 1 GiB leaf at level 2 with PTE[46]=1 (PPN bit 36, i.e. the physical address is >= 2^48).

| access | leaf (level 2, 1 GiB) | reason in the privileged spec | spec / NEMU | XiangShan |
|---|---|---|---|---|
| `ld` | `0x000040000000009f` (V R W X U, A=0, D=1) | step 9: A=0 (Svade) | 13 load page fault | 5 load access fault |
| `sd` | `0x0000400000000017` (V R W U, X=0, A=0, D=0) | step 9: A=0 (Svade) | 15 store page fault | 7 store access fault |

From reading the source (we have not changed the RTL): the walker marks `ppn_af` via `isAf()`, and the permission / A / D page faults are only computed in the L1 TLB, where the `!af` terms in `TLB.scala` (the `pf.ld/st/instr` outputs) mask them. The comment there says "pf has lower priority than af".

This looks different from the stated intent in #3453 (`pmp_af > {pf or gpf} > ppn_af`). Could you clarify whether letting an A/D/permission page fault lose to `ppn_af` is intended, or an oversight? Per the privileged spec the access fault for a nonexistent physical address is only due once the translation has succeeded.

Tested with XiangShan source at `a13efc87` (emu built from it) and a NEMU `ready-to-run` interpreter; we have not rechecked on the latest default branch.
```

## 发布前必须核实的点

- 正文不含“A=1 时两边一致”的断言：目前没有对这两个 PTE 把 A 改成 1 的定向实测，不要在评论里写这类结论。
- 表中两个 PTE 值取自 `mismatches.json`（LOAD 的 mutant-1012、STORE 的 mutant-0371）；发布前对照复现 ELF 再核一遍。
- 场景设置（S 态、SUM=1、MXR=0）取自重放平台配置，发布前对照 `design.md` 再确认。

## 待用户决定

1. 是否发布；以 msuadOf 账号发出。
2. 是否附复现 ELF（需先确认复现步骤，且最好在最新默认分支复验）。
3. 是否先在最新 `09453ff8` 上重建 emu 复验再发。
