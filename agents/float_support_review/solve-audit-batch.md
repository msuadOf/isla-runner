# 当前 d012 IR 的官方 77 项非访存浮点 solve 审计

> **现行续跑导航（2026-09-27）**：56cc跨stage唯一自然完成目标为57/77，剩余20项的精确名单见[机器去重索引](../../isla/target/float-solve-evidence/vfmerge-2h-56cc-20260927-c/evidence/aggregate-completed-56cc.json)的`remaining_targets_in_official_order`；最新源侧结果见[56cc后续段](#56cc跨stage长预算后续2026-09-27)及[官方批记录](solve-fix-official.md)。这57个不同目标的既存自然完成输出包已形成[双审汇总](../../.tmp/unified-backend-cpp-replay-independent-57-target-scope-56cc69/summary.json)（SHA-256 `2b858535…eefd`）和[逐目标映射](../../.tmp/unified-backend-cpp-replay-independent-57-target-scope-56cc69/target-map.json)（SHA-256 `52b0b27f…f6d3`）：80,416个输入身份=80,283 gen+91 direct负例+42 derived负例，跨32个run ID、3种56cc源binary；该限定汇总不表示单批、单runtime或全77完成。本标题下的d012表和随后1dcc表均为对应旧IR/预算的历史结果，不代表现行56cc验收。

> 本文主体保留 d012 历史审计。2026-09-27：修复候选 IR `1dcc8081…8180`、源码 manifest `28fb65ee…a055e` 的全77批已结束：50自然退出0、27外限124，全组未通过；50完整目标的日志/JSON/trace守恒及全部18,477条gen重放通过，其余27项无JSON；批次入口 `isla/target/float-solve-evidence/official-1dcc-20260927-002314/`。同版9152条定向结果通过，但源码分支闭合仍未完成，不能与官方求解混计。此前c5批41退出0/36外限仅作宽位输出缺陷诊断。当前进展见[摘要](status.md)及[官方批记录](solve-fix-official.md)；统一C++/Isla模型改造见[方案](unified-backend-plan.md)，其后续版本须重新验证。

2026-09-26 执行。受测集合为 [固定清单](tools/official_float/targets77.txt) 中 77 个 RV64 非访存浮点 `solve-X`；与 [旧 c9e1 批次](official-continuation.md)分开记录。普通 `make solve` 默认排除 `FD_FLOAT`，本轮没有测试 10 个浮点访存项或两项需要另验模式可达性的 `FMVH_X_D`、`FMVP_D_X`。入口和结论的适用边界见[运行器审计口径](solve-audit-method.md)及[原始 JSON 语义复核](solve-audit-log-semantics.md)。

## 固定快照与执行方式

- 使用 `tools/official_float/prepare.sh` 从主 `isla/` 生成新的仓库外快照，证据目录记为 `RUN_DIR`，本轮目录名 `isla-float-official-d012-20260926-150048`。没有写主 `isla/output/`，也没有进入 `.worktrees`。原有未提交内容保留。
- Isla HEAD `f4f8e4584a70588c66c9e7a6286cc20211618f18`；Sail-RISC-V HEAD `f8ce8490981eac6396a31013180a2e718615757d`。两者另有未提交修改，故以清单哈希界定本轮文件。IR SHA-256 `d0123541491c6ad7cb00d745e751b6a74deac442148fdf95a2488abf6b5e5409`；79 份严格 workaround 配置同批复制。原 `evidence/manifest.json` 含 86 个源码、IR、脚本和配置文件；补充 `evidence/runtime-supplement.json` 含 6 个运行器关键源码。四个 stage 在运行前后均与所记 SHA-256 一致。
- 在隔离 stage 独立执行 `make build-isarch`，退出 0；Rust/Cargo 1.93.1、Z3 4.16.0，默认 `smt-thread-interrupt` feature，未启用 itrace。固定 release `isarch` SHA-256 `34feb0923bf13123cc11fded795308e1d4d52cf47d166a5496d6db29752b4eb8`，四个 stage 二进制相同。
- 为隔离 `output/`、进度计数器与状态日志，按编号 1–20、21–40、41–59、60–77 分成四个 stage；各 stage 内顺序执行，至多四项目标同时运行。每项使用下列命令；`-o build-isarch` 只跳过已经单独完成的构建前置目标，避免多个 stage 重编译不同二进制。目标专用配置仍由原 `scripts/run.mk` 选择。

```sh
make -o build-isarch solve-X THREADS=2 OUTER_TIMEOUT=90s SOLVE_TIMEOUT=80s SMT_TIMEOUT=15s TASTIC=qfaufbv
```

- `OUTER_TIMEOUT=90s` 用于在旧批次共享 CPU 负载及 5 秒 SMT 限额后，做明确预算的复验；不是性能改善证据。运行开始阶段主机另有内存议题 isarch 约占 24 核；本批逐项目标启动时 1 分钟负载均值为 4.08–9.82，中位 7.39。UTC 执行窗口 07:03:25–07:25:45。

## 结果及判定

| 底层 isarch / make 退出 | 项数 | 日志 Finished（Retire / Illegal） | 最终 JSON | 判定 |
| --- | ---: | ---: | ---: | --- |
| 0 / 0 | 40 | 3,458（3,340 / 118） | 40 份、3,458 条，有效 | 本预算内运行器自然结束；仍非全部源码分支或数值/flags 证明。 |
| 124 / 2 | 36 | 4,648（585 / 4,063） | 0 份 | 外层 90 秒中止；日志路径均为局部结果。 |
| 1 / 2 | 1 | 16（10 / 6） | 1 份、16 条，有效 | `F_UN_RM_FF_TYPE_S` 的 SMT 超时使目标失败；JSON 存在不改变判定。 |

合计 77/77 项均已启动并取得退出状态：make 退出 0 为 40 项、退出 2 为 37 项；底层退出 0/124/1 分别为 40/36/1。全部日志打印 8,122 条 Finished（Retire 3,935、Illegal 4,187、其他 0），其中 4,648 条属于未完成的外限目标。41 份最终 JSON 均能解析，3,474 条 `gen` 路径的数量及 Retire/Illegal 分类与日志逐项一致；`test-ins`、编码和 `isa-state` 空字段均为 0。

精确匹配 `[SYM_EXEC]: 执行错误:` 为 62 行：11 个目标合计 61 条 `SMT timeout during CheckSatAssuming`，另 `VFNCVTBF16_F_F_W` 一条 CLI 路径 `Timeout(Timeout)`。61 份 SMT2 dump 保留于各 stage 的 `output/timeout-smt/`；60 条 SMT 错误指向 `extensions/FD/fdext_regs.sail:523:6`，一条指向同一 if 的 523:2–527:3 区间。宽关键词列 `execerror=63` 还包含 `F_UN_RM_FF_TYPE_S` 的最终 clause 失败总结，不是第 63 个独立执行错误；`other_error=64` 与上述重叠，并包含该目标的两条最终错误总结。这两列都只扫描 isarch 日志，没有把 make 的 Error 1 计入。其余 25 个外限目标日志没有显式执行错误文本，仍未完成。

全部 77 份日志的 assert、panic、Poison、unknown、`Z3Unknown`、MatchFailure 关键词计数为 0；退出 0 的 40 项也没有执行错误或 timeout 文本。**MatchFailure 与 AssertionFailure 可以被运行器静默丢弃**，因此零关键词不证明这两类分支没有发生，更不能证明全部源码分支已跑到。41 份 JSON 的 3,474 条输入状态均缺 `fcsr`（也缺 `mstatus`）；JSON 本身没有输出寄存器、post-state 或 fflags，不能由此验证数值与五标志。具体重放和汇编文本局限见[日志语义复核](solve-audit-log-semantics.md)。

初次外部运行脚本把 JSON 文件名误探为 `rv64_<目标>.json`，而真实文件为 `rv64_z<目标>.json`，故进度行和最初 77 份 `result.json` 的 `json=False` 是元数据探测错误。已把原元数据逐份保存在 `evidence/result-initial/`，更正逐项 `result.json`，并从真实 JSON 重新生成下表和 `evidence/audit.csv`；原始 make 日志、isarch 日志与 JSON 未改。以最终审计 CSV、JSON 和原始文件为准。

## 逐项目标

表中 `路径` 为该项日志中已打印的 Finished 数；外限项的这些路径不代表整项完成。`异常` 的 SMT/Path 是精确执行错误行数；`—` 表示无显式执行错误。`JSON` 只记最终文件的有效记录数。每项原始命令、make 与底层退出、启动负载和墙钟见外部 `evidence/<目标>.command/.make.log/.result.json`；完整异常行及上下文见 `evidence/anomalies.jsonl`。

| # | 目标 | make/isarch | 路径 | Retire | Illegal | JSON | 异常 | 秒 |
| ---: | --- | --- | ---: | ---: | ---: | --- | --- | ---: |
| 1 | `FCVTMOD_W_D` | 0/0 | 46 | 46 | 0 | 46 | — | 2.8 |
| 2 | `FCVT_BF16_S` | 0/0 | 36 | 30 | 6 | 36 | — | 14.7 |
| 3 | `FCVT_S_BF16` | 0/0 | 39 | 36 | 3 | 39 | — | 2.6 |
| 4 | `FLEQ_D` | 0/0 | 6 | 6 | 0 | 6 | — | 1.7 |
| 5 | `FLEQ_H` | 0/0 | 16 | 16 | 0 | 16 | — | 2.2 |
| 6 | `FLEQ_S` | 0/0 | 16 | 16 | 0 | 16 | — | 2.3 |
| 7 | `FLI_D` | 0/0 | 32 | 32 | 0 | 32 | — | 1.7 |
| 8 | `FLI_H` | 0/0 | 32 | 32 | 0 | 32 | — | 1.7 |
| 9 | `FLI_S` | 0/0 | 32 | 32 | 0 | 32 | — | 1.7 |
| 10 | `FLTQ_D` | 0/0 | 6 | 6 | 0 | 6 | — | 1.7 |
| 11 | `FLTQ_H` | 0/0 | 16 | 16 | 0 | 16 | — | 2.2 |
| 12 | `FLTQ_S` | 0/0 | 16 | 16 | 0 | 16 | — | 2.2 |
| 13 | `FMAXM_D` | 0/0 | 169 | 169 | 0 | 169 | — | 13.3 |
| 14 | `FMAXM_H` | 0/0 | 196 | 196 | 0 | 196 | — | 18.5 |
| 15 | `FMAXM_S` | 0/0 | 196 | 196 | 0 | 196 | — | 17.1 |
| 16 | `FMINM_D` | 0/0 | 157 | 157 | 0 | 157 | — | 12.8 |
| 17 | `FMINM_H` | 0/0 | 184 | 184 | 0 | 184 | — | 17.4 |
| 18 | `FMINM_S` | 0/0 | 184 | 184 | 0 | 184 | — | 15.9 |
| 19 | `FROUNDNX_D` | 0/0 | 23 | 20 | 3 | 23 | — | 5.3 |
| 20 | `FROUNDNX_H` | 0/0 | 36 | 30 | 6 | 36 | — | 3.4 |
| 21 | `FROUNDNX_S` | 0/0 | 36 | 30 | 6 | 36 | — | 4.2 |
| 22 | `FROUND_D` | 0/0 | 23 | 20 | 3 | 23 | — | 2.0 |
| 23 | `FROUND_H` | 0/0 | 36 | 30 | 6 | 36 | — | 2.6 |
| 24 | `FROUND_S` | 0/0 | 36 | 30 | 6 | 36 | — | 2.5 |
| 25 | `FVFMATYPE` | 2/124 | 175 | 0 | 175 | 缺失 | SMT×1 | 90.2 |
| 26 | `FVFMTYPE` | 2/124 | 105 | 5 | 100 | 缺失 | — | 90.2 |
| 27 | `FVFTYPE` | 2/124 | 394 | 6 | 388 | 缺失 | — | 90.2 |
| 28 | `FVVMATYPE` | 2/124 | 172 | 0 | 172 | 缺失 | SMT×1 | 90.2 |
| 29 | `FVVMTYPE` | 2/124 | 104 | 8 | 96 | 缺失 | — | 90.2 |
| 30 | `FVVTYPE` | 2/124 | 183 | 7 | 176 | 缺失 | — | 90.2 |
| 31 | `FWFTYPE` | 2/124 | 187 | 6 | 181 | 缺失 | — | 90.2 |
| 32 | `FWVFMATYPE` | 2/124 | 154 | 0 | 154 | 缺失 | — | 90.2 |
| 33 | `FWVFTYPE` | 2/124 | 154 | 0 | 154 | 缺失 | — | 90.2 |
| 34 | `FWVTYPE` | 2/124 | 170 | 0 | 170 | 缺失 | SMT×1 | 90.2 |
| 35 | `FWVVMATYPE` | 2/124 | 154 | 0 | 154 | 缺失 | — | 90.2 |
| 36 | `FWVVTYPE` | 2/124 | 157 | 0 | 157 | 缺失 | — | 90.2 |
| 37 | `F_BIN_F_TYPE_D` | 0/0 | 341 | 341 | 0 | 341 | — | 27.6 |
| 38 | `F_BIN_F_TYPE_H` | 0/0 | 404 | 404 | 0 | 404 | — | 38.0 |
| 39 | `F_BIN_RM_TYPE_D` | 2/124 | 3 | 0 | 3 | 缺失 | SMT×8 | 90.3 |
| 40 | `F_BIN_RM_TYPE_H` | 2/124 | 41 | 32 | 9 | 缺失 | — | 90.2 |
| 41 | `F_BIN_RM_TYPE_S` | 2/124 | 33 | 24 | 9 | 缺失 | SMT×7 | 90.3 |
| 42 | `F_BIN_TYPE_F_S` | 0/0 | 404 | 404 | 0 | 404 | — | 37.2 |
| 43 | `F_BIN_TYPE_X_S` | 0/0 | 52 | 52 | 0 | 52 | — | 4.6 |
| 44 | `F_BIN_X_TYPE_D` | 0/0 | 18 | 18 | 0 | 18 | — | 2.6 |
| 45 | `F_BIN_X_TYPE_H` | 0/0 | 52 | 52 | 0 | 52 | — | 4.8 |
| 46 | `F_MADD_TYPE_D` | 2/124 | 3 | 0 | 3 | 缺失 | SMT×10 | 90.3 |
| 47 | `F_MADD_TYPE_H` | 2/124 | 18 | 12 | 6 | 缺失 | — | 90.2 |
| 48 | `F_MADD_TYPE_S` | 2/124 | 20 | 14 | 6 | 缺失 | SMT×9 | 90.2 |
| 49 | `F_UN_F_TYPE_D` | 0/0 | 2 | 2 | 0 | 2 | — | 1.0 |
| 50 | `F_UN_F_TYPE_H` | 0/0 | 2 | 2 | 0 | 2 | — | 1.0 |
| 51 | `F_UN_RM_FF_TYPE_D` | 2/124 | 24 | 15 | 9 | 缺失 | SMT×7 | 90.8 |
| 52 | `F_UN_RM_FF_TYPE_H` | 2/124 | 63 | 42 | 21 | 缺失 | SMT×6 | 90.2 |
| 53 | `F_UN_RM_FF_TYPE_S` | 2/1 | 16 | 10 | 6 | 16 | SMT×10 | 78.7 |
| 54 | `F_UN_RM_FX_TYPE_D` | 2/124 | 37 | 25 | 12 | 缺失 | — | 90.2 |
| 55 | `F_UN_RM_FX_TYPE_H` | 0/0 | 344 | 320 | 24 | 344 | — | 53.4 |
| 56 | `F_UN_RM_FX_TYPE_S` | 2/124 | 193 | 169 | 24 | 缺失 | — | 90.2 |
| 57 | `F_UN_RM_XF_TYPE_D` | 2/124 | 39 | 27 | 12 | 缺失 | — | 90.2 |
| 58 | `F_UN_RM_XF_TYPE_H` | 0/0 | 144 | 120 | 24 | 144 | — | 58.3 |
| 59 | `F_UN_RM_XF_TYPE_S` | 2/124 | 118 | 94 | 24 | 缺失 | — | 90.2 |
| 60 | `F_UN_TYPE_F_S` | 0/0 | 2 | 2 | 0 | 2 | — | 1.0 |
| 61 | `F_UN_TYPE_X_S` | 0/0 | 24 | 24 | 0 | 24 | — | 1.9 |
| 62 | `F_UN_X_TYPE_D` | 0/0 | 22 | 22 | 0 | 22 | — | 1.8 |
| 63 | `F_UN_X_TYPE_H` | 0/0 | 24 | 24 | 0 | 24 | — | 1.9 |
| 64 | `RFVVTYPE` | 2/124 | 117 | 16 | 101 | 缺失 | — | 90.2 |
| 65 | `RFWVVTYPE` | 2/124 | 114 | 12 | 102 | 缺失 | — | 90.3 |
| 66 | `VFMERGE` | 2/124 | 140 | 32 | 108 | 缺失 | — | 90.2 |
| 67 | `VFMV` | 2/124 | 116 | 15 | 101 | 缺失 | — | 90.2 |
| 68 | `VFMVFS` | 0/0 | 16 | 3 | 13 | 16 | — | 3.3 |
| 69 | `VFMVSF` | 0/0 | 38 | 20 | 18 | 38 | — | 13.6 |
| 70 | `VFNCVTBF16_F_F_W` | 2/124 | 189 | 0 | 189 | 缺失 | Path×1 | 90.2 |
| 71 | `VFNUNARY0` | 2/124 | 142 | 0 | 142 | 缺失 | — | 90.2 |
| 72 | `VFUNARY0` | 2/124 | 174 | 2 | 172 | 缺失 | — | 90.2 |
| 73 | `VFUNARY1` | 2/124 | 185 | 8 | 177 | 缺失 | SMT×1 | 90.2 |
| 74 | `VFWCVTBF16_F_F_V` | 2/124 | 202 | 8 | 194 | 缺失 | — | 90.2 |
| 75 | `VFWMACCBF16_VF` | 2/124 | 197 | 3 | 194 | 缺失 | — | 90.2 |
| 76 | `VFWMACCBF16_VV` | 2/124 | 204 | 3 | 201 | 缺失 | — | 90.2 |
| 77 | `VFWUNARY0` | 2/124 | 167 | 0 | 167 | 缺失 | — | 90.2 |

## 证据入口与后续口径

- 仓库外 `RUN_DIR/evidence/audit.csv`、`audit.json`、`audit-summary.json` 是 77 项机器可核对表；`manifest.json`、`runtime-supplement.json`、`isarch.sha256` 固定受测版本；`anomalies.jsonl` 逐行附上下文；四个 `stage*/output/` 保存原始日志、状态、JSON 与 SMT2。
- 40 个退出 0 目标只得到本次官方入口的自然结束证据。已有[1509 条定向指令状态样例](e-coverage.md)及本轮[独立审计补证](solve-audit-method.md)分别承担列定输入的结果与 flags 验证；二者不等价于 77 个目标的全分支穷尽。36 个外限目标和 1 个 SMT 失败目标的官方验收仍未通过。
- 本轮只报告观察事实，不对超时运行时作修复。后续若调整 IR、模型、预算或配置，须作为新批次重新绑定哈希并逐项复验。

## 1dcc 同版新77项执行表（2026-09-27）

本表是新增的1dcc批次结果，保留上方d012旧表原样。冻结入口为运行目录 `isla/target/float-solve-evidence/official-1dcc-20260927-002314/` 的 `evidence/manifest.json`、`evidence/official-audit.json` 和 `evidence/official-diagnostic-audit.json`。IR SHA-256 `1dcc80812b8beaba49abaebf605e8090c2796b5930aefa36635b478c5f2b8180`，候选源码清单 SHA-256 `28fb65ee77e2c5e5c629c50b239a2e009337b47936b2fdbb897bf9c11bca055e`，FD配置 SHA-256 `20851fdbd5120066b5a0275d3780c255edb715b233fb31a2529b8e110ef723d0`；完整运行方式和限制见[本轮记录](solve-fix-official.md)。

50项自然退出0，27项300秒外限124，无其他底层退出；全局make退出2。50份最终JSON逐项complete=true、suppressed=0，含18,584个终态；日志和完整itrace终态守恒，branch edge与运行时catalog校验无效边0。27项超时无最终JSON，下表的终态只是中止前已打印的局部证据，不计覆盖或PASS。整批未生成全量replay manifest；数值/flags结果以独立replay/oracle为准。

| # | 目标 | make/isarch | 日志终态 | Retire | Illegal | 不可编码 | 最终JSON gen | 异常行 | 秒 |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `FCVTMOD_W_D` | 0/0 | 79 | 78 | 0 | 1 | 78 | 0 | 7.48 |
| 2 | `FCVT_BF16_S` | 0/0 | 1873 | 1440 | 432 | 1 | 1872 | 0 | 145.60 |
| 3 | `FCVT_S_BF16` | 0/0 | 1657 | 1440 | 216 | 1 | 1656 | 0 | 119.56 |
| 4 | `FLEQ_D` | 0/0 | 85 | 84 | 0 | 1 | 84 | 0 | 11.47 |
| 5 | `FLEQ_H` | 0/0 | 211 | 210 | 0 | 1 | 210 | 0 | 18.67 |
| 6 | `FLEQ_S` | 0/0 | 211 | 210 | 0 | 1 | 210 | 0 | 16.75 |
| 7 | `FLI_D` | 0/0 | 97 | 96 | 0 | 1 | 96 | 0 | 6.54 |
| 8 | `FLI_H` | 0/0 | 98 | 96 | 0 | 2 | 96 | 0 | 6.93 |
| 9 | `FLI_S` | 0/0 | 97 | 96 | 0 | 1 | 96 | 0 | 6.72 |
| 10 | `FLTQ_D` | 0/0 | 85 | 84 | 0 | 1 | 84 | 0 | 10.21 |
| 11 | `FLTQ_H` | 0/0 | 211 | 210 | 0 | 1 | 210 | 0 | 18.81 |
| 12 | `FLTQ_S` | 0/0 | 211 | 210 | 0 | 1 | 210 | 0 | 16.09 |
| 13 | `FMAXM_D` | 0/0 | 22 | 21 | 0 | 1 | 21 | 0 | 5.07 |
| 14 | `FMAXM_H` | 0/0 | 85 | 84 | 0 | 1 | 84 | 0 | 8.87 |
| 15 | `FMAXM_S` | 0/0 | 85 | 84 | 0 | 1 | 84 | 0 | 9.36 |
| 16 | `FMINM_D` | 0/0 | 22 | 21 | 0 | 1 | 21 | 0 | 4.84 |
| 17 | `FMINM_H` | 0/0 | 85 | 84 | 0 | 1 | 84 | 0 | 9.44 |
| 18 | `FMINM_S` | 0/0 | 85 | 84 | 0 | 1 | 84 | 0 | 8.62 |
| 19 | `FROUNDNX_D` | 0/0 | 40 | 30 | 9 | 1 | 39 | 0 | 4.41 |
| 20 | `FROUNDNX_H` | 0/0 | 79 | 60 | 18 | 1 | 78 | 0 | 6.70 |
| 21 | `FROUNDNX_S` | 0/0 | 79 | 60 | 18 | 1 | 78 | 0 | 6.69 |
| 22 | `FROUND_D` | 0/0 | 40 | 30 | 9 | 1 | 39 | 0 | 4.48 |
| 23 | `FROUND_H` | 0/0 | 79 | 60 | 18 | 1 | 78 | 0 | 7.07 |
| 24 | `FROUND_S` | 0/0 | 79 | 60 | 18 | 1 | 78 | 0 | 6.66 |
| 25 | `FVFMATYPE` | 2/124 | 1980 | 0 | 1977 | 3 | 缺失 | 0 | 305.33 |
| 26 | `FVFMTYPE` | 2/124 | 1855 | 0 | 1852 | 3 | 缺失 | 0 | 305.71 |
| 27 | `FVFTYPE` | 2/124 | 2065 | 0 | 2062 | 3 | 缺失 | 0 | 305.93 |
| 28 | `FVVMATYPE` | 2/124 | 2775 | 0 | 2772 | 3 | 缺失 | 0 | 304.85 |
| 29 | `FVVMTYPE` | 2/124 | 2630 | 0 | 2627 | 3 | 缺失 | 0 | 304.87 |
| 30 | `FVVTYPE` | 2/124 | 3271 | 0 | 3268 | 3 | 缺失 | 0 | 304.75 |
| 31 | `FWFTYPE` | 2/124 | 3392 | 0 | 3389 | 3 | 缺失 | 0 | 304.07 |
| 32 | `FWVFMATYPE` | 2/124 | 2969 | 0 | 2966 | 3 | 缺失 | 0 | 304.17 |
| 33 | `FWVFTYPE` | 2/124 | 3565 | 0 | 3562 | 3 | 缺失 | 0 | 305.04 |
| 34 | `FWVTYPE` | 2/124 | 4794 | 0 | 4791 | 3 | 缺失 | 0 | 302.74 |
| 35 | `FWVVMATYPE` | 2/124 | 3993 | 0 | 3990 | 3 | 缺失 | 0 | 302.73 |
| 36 | `FWVVTYPE` | 2/124 | 4182 | 0 | 4179 | 3 | 缺失 | 0 | 302.54 |
| 37 | `F_BIN_F_TYPE_D` | 0/0 | 110 | 105 | 0 | 5 | 105 | 0 | 11.79 |
| 38 | `F_BIN_F_TYPE_H` | 0/0 | 425 | 420 | 0 | 5 | 420 | 0 | 34.01 |
| 39 | `F_BIN_RM_TYPE_D` | 0/0 | 1096 | 840 | 252 | 4 | 1092 | 0 | 75.42 |
| 40 | `F_BIN_RM_TYPE_H` | 2/124 | 2216 | 1732 | 480 | 4 | 缺失 | 0 | 301.36 |
| 41 | `F_BIN_RM_TYPE_S` | 2/124 | 3986 | 3088 | 894 | 4 | 缺失 | 0 | 300.63 |
| 42 | `F_BIN_TYPE_F_S` | 0/0 | 425 | 420 | 0 | 5 | 420 | 0 | 28.81 |
| 43 | `F_BIN_TYPE_X_S` | 0/0 | 633 | 630 | 0 | 3 | 630 | 0 | 43.69 |
| 44 | `F_BIN_X_TYPE_D` | 0/0 | 255 | 252 | 0 | 3 | 252 | 0 | 25.86 |
| 45 | `F_BIN_X_TYPE_H` | 0/0 | 633 | 630 | 0 | 3 | 630 | 0 | 48.45 |
| 46 | `F_MADD_TYPE_D` | 2/124 | 3135 | 2744 | 387 | 4 | 缺失 | 0 | 302.53 |
| 47 | `F_MADD_TYPE_H` | 2/124 | 799 | 714 | 81 | 4 | 缺失 | 0 | 302.07 |
| 48 | `F_MADD_TYPE_S` | 2/124 | 1179 | 1028 | 147 | 4 | 缺失 | 0 | 302.01 |
| 49 | `F_UN_F_TYPE_D` | 0/0 | 7 | 6 | 0 | 1 | 6 | 0 | 2.50 |
| 50 | `F_UN_F_TYPE_H` | 0/0 | 7 | 6 | 0 | 1 | 6 | 0 | 2.57 |
| 51 | `F_UN_RM_FF_TYPE_D` | 0/0 | 159 | 120 | 36 | 3 | 156 | 0 | 11.16 |
| 52 | `F_UN_RM_FF_TYPE_H` | 0/0 | 356 | 270 | 81 | 5 | 351 | 0 | 20.45 |
| 53 | `F_UN_RM_FF_TYPE_S` | 0/0 | 79 | 60 | 18 | 1 | 78 | 0 | 6.62 |
| 54 | `F_UN_RM_FX_TYPE_D` | 0/0 | 280 | 240 | 36 | 4 | 276 | 0 | 14.30 |
| 55 | `F_UN_RM_FX_TYPE_H` | 0/0 | 556 | 480 | 72 | 4 | 552 | 0 | 28.69 |
| 56 | `F_UN_RM_FX_TYPE_S` | 0/0 | 556 | 480 | 72 | 4 | 552 | 0 | 29.11 |
| 57 | `F_UN_RM_XF_TYPE_D` | 0/0 | 316 | 240 | 72 | 4 | 312 | 0 | 16.66 |
| 58 | `F_UN_RM_XF_TYPE_H` | 0/0 | 316 | 240 | 72 | 4 | 312 | 0 | 17.14 |
| 59 | `F_UN_RM_XF_TYPE_S` | 0/0 | 316 | 240 | 72 | 4 | 312 | 0 | 16.08 |
| 60 | `F_UN_TYPE_F_S` | 0/0 | 7 | 6 | 0 | 1 | 6 | 0 | 2.61 |
| 61 | `F_UN_TYPE_X_S` | 0/0 | 74 | 72 | 0 | 2 | 72 | 0 | 6.59 |
| 62 | `F_UN_X_TYPE_D` | 0/0 | 68 | 66 | 0 | 2 | 66 | 0 | 6.23 |
| 63 | `F_UN_X_TYPE_H` | 0/0 | 74 | 72 | 0 | 2 | 72 | 0 | 6.87 |
| 64 | `RFVVTYPE` | 2/124 | 2741 | 0 | 2738 | 3 | 缺失 | 0 | 304.68 |
| 65 | `RFWVVTYPE` | 2/124 | 3209 | 0 | 3206 | 3 | 缺失 | 0 | 303.84 |
| 66 | `VFMERGE` | 2/124 | 3571 | 0 | 3568 | 3 | 缺失 | 0 | 303.07 |
| 67 | `VFMV` | 2/124 | 4069 | 194 | 3872 | 3 | 缺失 | 0 | 301.14 |
| 68 | `VFMVFS` | 0/0 | 255 | 63 | 189 | 3 | 252 | 0 | 17.83 |
| 69 | `VFMVSF` | 0/0 | 2451 | 1440 | 1008 | 3 | 2448 | 0 | 147.94 |
| 70 | `VFNCVTBF16_F_F_W` | 0/0 | 1623 | 261 | 1359 | 3 | 1620 | 0 | 264.30 |
| 71 | `VFNUNARY0` | 2/124 | 4333 | 0 | 4318 | 15 | 缺失 | 0 | 302.44 |
| 72 | `VFUNARY0` | 2/124 | 4384 | 0 | 4381 | 3 | 缺失 | 0 | 301.65 |
| 73 | `VFUNARY1` | 2/124 | 4599 | 0 | 4596 | 3 | 缺失 | 0 | 301.74 |
| 74 | `VFWCVTBF16_F_F_V` | 0/0 | 1812 | 312 | 1497 | 3 | 1809 | 0 | 197.04 |
| 75 | `VFWMACCBF16_VF` | 2/124 | 3612 | 0 | 3609 | 3 | 缺失 | 0 | 303.05 |
| 76 | `VFWMACCBF16_VV` | 2/124 | 3140 | 0 | 3137 | 3 | 缺失 | 0 | 303.24 |
| 77 | `VFWUNARY0` | 2/124 | 4600 | 0 | 4588 | 12 | 缺失 | 0 | 301.81 |

严格audit逐项结果为50/77无已知运行器错误；27个超时目标各记“目标超时或失败、缺最终JSON”，全局错误为make exit2。50项完整trace原文与规范化catalog哈希、状态域哈希和逐项文件哈希保存在 `evidence/official-audit.json`/`evidence/manifest.json`；27项残缺trace保留原文及大小，不据其推断全域。新的生产源码或IR变动后，本表仅作此版历史证据。

## 3481 统一后端两代表诊断（2026-09-27）

本节只记录 `FVVMATYPE` 与 `F_MADD_TYPE_D` 的同预算代表复验，**不是3481版完整77项批次**。冻结stage为 `isla/target/float-solve-evidence/representatives-3481-20260927-041103/`；IR SHA-256 `348147f833432008d559be0e673dbd45982148b0750cd4533c68589a55aac061`，候选源码清单 `1890f0a1…`、严格配置报告 `affdc1e3…` PASS、FD配置 `20851fdb…`。原make两个目标 `-k -j2`、每目标2线程、完整ITRACE、300/270/30秒及`qfaufbv`，无目标专用执行限制。逐项完整命令、日志、时间与源哈希见[官方批记录](solve-fix-official.md)及stage的 `evidence/representatives-run.json`、`evidence/representatives-audit.json`。

| 目标 | make/isarch | 墙上秒 | 局部Retire | 局部Illegal | 局部不可编码 | 最终JSON | 判定 |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| `FVVMATYPE` | 2/124 | 303.22 | 0 | 4,014 | 3 | 缺失 | 外限、未完成 |
| `F_MADD_TYPE_D` | 2/124 | 302.14 | 2,826 | 633 | 4 | 缺失 | 外限、未完成 |

两份日志没有匹配到执行错误或SMT超时；残缺itrace原文均留存。新两代表并发上限2，旧1dcc全批上限4，主机负载亦不同，局部路径数不可直接作性能比值。完整3481版77项目标尚未启动。

独立流式trace复核进一步发现：`FVVMATYPE` 轨迹4,017终态与日志一致；`F_MADD_TYPE_D` 轨迹完整终态为Retire 2,825、Illegal 633、不可编码4，较上表日志少1条Retire。两者均无最终JSON，差异保留为局部证据不守恒，不能据日志路径数推断完整覆盖。原始复核见 `isla/target/float-solve-evidence/unified-performance-review/review.json`（SHA-256 `ebd528be…`）。

## 56cc V4+AMO 官方入口续测（2026-09-27）

300/270/30秒两代表：`F_MADD_TYPE_D` 自然exit0，1096终态（840 Retire/252 Illegal/4不可编码）、1092gen，完整JSON/日志/trace守恒；`FVVMATYPE` 外限124，局部53 Retire/3353 Illegal/3不可编码，无最终JSON。证据和同版哈希见[官方批记录](solve-fix-official.md)。

随后在独立stage `isla/target/float-solve-evidence/official-56cc-long-20260927-064348/` 启动原77项长预算1800/1740/30秒、`-j8`×每目标2线程，全trace且不采样。内存压力下安全止损：40项启动，其中26项自然退出0、6项非预算失败（1项137、5项15，原因待核）、8项人为中断；37项未启动。make -9为人为结束，**该stage不是完整77项执行结果**。机器分类与原始进程记录在 `evidence/stopped-batch-audit.json`、`controlled-interruption.json`；26自然完成目标的独立冻结回放入口为 `replay-wave-001-manifest.json`。这26项可逐项复核，不得把失败、中断或未启动项写成外限或PASS。局部trap修复与低并发新stage结果将另立证据。

该26项完整目标的6,230个终态已完成双后端输入归账与观察到的数值/状态配对；消费端后来确认遗漏异常let的纯读及完整等价检查，因此**纯读与完整等价待补证**，不得沿用旧全语义PASS，见[官方批记录](solve-fix-official.md)。局部清理修复后另建 `fvftype-j1-56cc-20260927-084800/`，`FVFTYPE` 以同预算单目标运行约697秒后因进程RSS约119.5GiB主动资源止损：监督进程返回143、make2、无最终JSON，日志局部Illegal4,801/不可编码3/Retire0。其结果为 `external_resource_stop`，不记自然完成或1800秒外限；详细5秒采样范围、进程归属与脚本哈希见[官方批记录](solve-fix-official.md)和该stage `evidence/fvftype-resource-audit.json`。

## 56cc跨stage长预算后续（2026-09-27）

共享trace运行时的单目标`-j1`、每目标2线程、1800/1740/30秒、完整ITRACE、原符号域无采样。第一单目标序列23项各自自然退出0、冻结回放manifest；连同旧长批26项及代表`F_MADD_TYPE_D`，机器去重为50/77。第二固定七项目标的结果如下，原始入口为`isla/target/float-solve-evidence/single-family-queue-20260927-020959/`的`status.json`、`events.jsonl`和`frozen.jsonl`，逐项证据见其stage的`evidence/*-freeze.json`与`stage/output/`。

| 目标 | 结果 | 完整终态 | Retire / Illegal / 不可编码 | 回放冻结 |
| --- | --- | ---: | --- | --- |
| `F_MADD_TYPE_H` | 自然退出0 | 8,740 | 6,720 / 2,016 / 4 | COMPLETE |
| `F_MADD_TYPE_S` | 自然退出0 | 8,740 | 6,720 / 2,016 / 4 | COMPLETE |
| `F_BIN_RM_TYPE_H` | 自然退出0 | 4,372 | 3,360 / 1,008 / 4 | COMPLETE |
| `F_BIN_RM_TYPE_S` | 自然退出0 | 4,372 | 3,360 / 1,008 / 4 | COMPLETE |
| `F_BIN_RM_TYPE_D` | 自然退出0 | 1,096 | 840 / 252 / 4 | COMPLETE |
| `VFMERGE` | 外限124、make2 | 无最终JSON | 局部路径，不计完整数 | 无 |
| `VFMV` | 自然退出0、make0 | 5,475 | 1,872 / 3,600 / 3 | COMPLETE |

`VFMERGE`监督器无外信号，实际wait到timeout child 124、1800.73秒，队列继续进入`VFMV`。`VFMV`监督器实际wait到child 0、464.49秒；其冻结报告`VFMV-freeze.json`核JSON/日志/完整trace终态双向守恒、38,148,123条branch edge无效0。六项自然完成manifest均按SHA进入`frozen.jsonl`；更新的跨stage去重索引`aggregate-completed-56cc.json` SHA-256 `b099be75…133e`列56/77唯一自然完成与剩余21项。该库存仍待各目标独立语义重放，不代表整组PASS。

e6a新caller的`FVFTYPE`另用冻结517源stage、IR SHA-256 `e6a3232d…7d27e`及同样预算运行；supervisor无外部信号、实际wait到timeout child 124、1805.23秒，make2且无最终JSON。`fvftype-caller-e6a-prepared-20260927/evidence/fvftype-partial-trace-audit.json` SHA-256 `d25388f2…4a0`流式核17,025,686,964字节残缺trace：14,140条局部终态与日志五元组双向一致（Retire31/Illegal14,106/不可编码3），85,694,666条branch edge无效0；监控345样本峰值RSS约30.8GiB、最低可用约109.3GiB，无资源止损。此局部自洽证据不使该目标成为完整目标，也不并入56cc唯一完成数。完整版本、命令和资源边界见[官方批记录](solve-fix-official.md)。

后续独立2小时预算`VFMERGE`在56cc共享trace stage`vfmerge-2h-56cc-20260927-c/`自然退出0（2359.20秒），严格冻结`replay-manifest-VFMERGE.json` SHA-256 `6c5749ca…56e3`：完整30,603终态Retire8,784/Illegal21,816/不可编码3，JSON/日志/44,122,131,855字节itrace五元组守恒，215,491,497条edge无效0。源侧完成库存的另建去重索引`evidence/aggregate-completed-56cc.json` SHA-256 `d0d0988a…8b05d`为57/77、剩20；独立语义回放待验。同期三目标队列`single-family-queue-20260927-035801/`首项`RFVVTYPE`外限124、无最终JSON/资源止损，局部Retire361/Illegal30,417/不可编码3，不计库存，队列已自动转`RFWVVTYPE`。新的`VFWMACCBF16_VV`两小时独立目标同时运行；其余结果待实际退出。详细预算、监督器与证据见[官方批记录](solve-fix-official.md)。

该三目标队列随后全部完成**外限124**的执行结论：`RFWVVTYPE`局部Retire1,382/Illegal24,608/不可编码3、`VFUNARY1`局部Retire443/Illegal4,006/不可编码3；两项均无最终JSON、无资源止损，故整个队列没有新增自然完成manifest，57/77库存不变。逐项目标的监督器实际wait、资源峰值、日志SHA和残缺trace大小在各stage`evidence/*-timeout-audit.json`；残缺trace未作全域核账。获批后`RFWVVTYPE`另建56cc两小时全符号域诊断stage，05:31 UTC实际spawn；旧30分钟尾部Retire为VL=0早退，不作为数值收尾证据。`VFWMACCBF16_VV`另建56cc两小时独立stage，30/60/实际约97分钟局部检查点保留；7200秒外限124，无最终JSON/资源止损，最终日志局部Retire5,283/Illegal25,924/不可编码3，残缺trace49,826,592,779字节，证据`evidence/VFWMACCBF16_VV-timeout-audit.json` SHA-256 `d9f32f2b…642a`。该目标仍不计完成，57/77库存不变。释放slot后，441c新IR `FVFTYPE`独立7200/7140/30秒stage于06:52 UTC实际spawn，另一路RFW仍运行；新候选原输入域、完整trace及1800秒固定对照门槛见[官方批记录](solve-fix-official.md)。

旧56cc两小时`RFWVVTYPE`随后于07:30:59 UTC外限124、无最终JSON/资源止损；最终局部日志Retire5,828/Illegal38,171/不可编码3，残缺trace59,566,629,106字节，证据`rfwvvtype-2h-56cc-prepared-20260927/evidence/RFWVVTYPE-timeout-audit.json` SHA-256 `2d74d024…863e`。仍不计完整目标，库存57/77。释放的并发位于07:41 UTC供新441c `VFUNARY1`独立7200/7140/30秒全输入stage实际spawn，与在运行的441c `FVFTYPE`合计两目标；其独立1800秒检查点及最终退出状态待实测。[官方批记录](solve-fix-official.md)保留同源快照、二进制复用和双独审边界。

441c新`FVFTYPE`的1800秒固定对照检查点实际采于1976.70秒，局部Retire2/Illegal519/不可编码3；60/90分钟由只读watcher根据原5秒资源样本自动触发。该目标最终于7200秒外限124、无最终JSON/资源止损，日志局部Retire21/Illegal1,687/不可编码3，残缺trace2,025,410,713字节，`fvftype-lmul-unary-441c-prepared-20260927/evidence/FVFTYPE-timeout-audit.json` SHA-256 `71f5581b…63d6`为最终诊断入口，未计完整目标。释放slot后nan-only IR `86f1121b…e61f`的独立`FVFTYPE`在08:56 UTC实际spawn，保持全输入域/完整trace/7200秒预算及自动1800秒检查点；另一441c `VFUNARY1`仍运行。旧56cc自然完成库存继续为57/77，不能将新IR局部路径转记为完成。

441c `VFUNARY1`在7200秒预算内亦外限124，最终无JSON/资源止损，局部Retire317/Illegal1,615/不可编码3，残缺trace2,484,724,725字节；最终证据`vfunary1-lmul-unary-441c-prepared-20260927/evidence/VFUNARY1-timeout-audit.json` SHA-256 `aa24d529…3d78`。空slot随后用于nan86f `FVFMTYPE`原1800/1740/30秒全域目标，09:44 UTC实际spawn，另一nan86f `FVFTYPE`仍运行。nan86f `FVFTYPE`的原1800秒自动对照点实际采于1803.81秒，局部2 Retire/576 Illegal/3不可编码，不能据此称优化收敛；结果待最终退出。56cc库存仍57/77。

nan86f `FVFMTYPE`最终原预算1800秒外限124、无JSON/资源止损，局部Retire29/Illegal1,792/不可编码3，详账`fvfmtype-nan-unbox-86f-prepared-20260927/evidence/FVFMTYPE-timeout-audit.json` SHA-256 `d268e381…551`。nan86f `FVFTYPE`继续到7200秒亦外限124，局部Retire27/Illegal1,911/不可编码3，无JSON/资源止损，详账`fvftype-nan-unbox-86f1-prepared-20260927/evidence/FVFTYPE-timeout-audit.json` SHA-256 `a3cd4aef…e1ef5`；60/90分钟自动前缀证据独立保留。a040新候选通过fullIR/strict/source双门后，`RFWVVTYPE`和`RFVVTYPE`各在独立stage以7200/7140/30秒、原全域/完整trace启动；同runtime和候选配置逐SHA复用，独立入口审查对RFW阶段放行。新两项目标结果以实际后续退出为准，不能把这些新IR局部执行计入旧56cc的57/77完成库存。

a040 `RFWVVTYPE`两小时运行已实际外限124、无最终JSON或资源止损，局部Retire745/Illegal1,210/不可编码3，最终小账本`rfwvvtype-nan-reduction-a040-2h-20260927-c/evidence/RFWVVTYPE-timeout-audit.json` SHA-256 `5ea8a749…2066`；`RFVVTYPE`已收90分钟自动前缀但仍在原预算运行，完整结论待真实退出。两项的30/60/90分钟检查点各自按实际elapsed冻结，详情见[官方批记录](solve-fix-official.md)。另fc4 IR的同e7ba `FVFTYPE`为单独30分钟Z3诊断，不能转记官方完成；fc4下一官方FVVMTYPE/FVFMTYPE须待新67和89实际回归双独证，56cc库存仍57/77。

a040 `RFVVTYPE`随后亦在7200秒外限124、无最终JSON或资源止损，局部Retire1,389/Illegal2,782/不可编码3，最终小账本`rfvvtype-nan-reduction-a040-2h-prepared-20260927/evidence/RFVVTYPE-timeout-audit.json` SHA-256 `7bfa96ef…62e3`。两条a040官方全域目标均未完成、无新回放入口；57/77仍专属56cc跨stage已自然完成集合。下一fc4官方FVVMTYPE→FVFMTYPE仅在新67 helper及必要89整指令实际回归独证齐后按原域、原两小时预算启动。
