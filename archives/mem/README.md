# 内存线证据档案索引

日期：2026-09-30。原散落在 `/tmp`、`/home`、`/data1/baiyifan/tmp` 的内存议题（MEM-REVIEW/MEM-IMPL/MEM-PMA/MEM-COVER/MEM-BUGHUNT 全线）证据产物已集中迁移至 `archives/_raw/mem/`（gitignored，本地持久）。各议题文档中的旧 `/tmp/...` 路径按本表对应到现行位置；根仓库为基准。

## 迁移映射

| 原位置 | 现位置（`archives/_raw/mem/` 下） | 内容 |
| --- | --- | --- |
| `/tmp/isla-memimpl-w4..w18-*` | `isla-memimpl-*`（同名） | W2-W18 各阶段验证产物（含 W13 诊断、W15 勘误探针、W17 S2、W18 S4） |
| `/tmp/isla-memsolve-survey-20260927-125738` | `isla-memsolve-survey-20260927-125738/` | W19 48-clause 跑批分布图（SURVEY.md、distribution-all.json、coverage/G1-G8） |
| `/tmp/isla-memimpl-w20/w21/w22-*` | `isla-memimpl-w2{0,1,2}-*` | AMO 修复、CSR 符号化、审计修订产物 |
| `/data1/baiyifan/tmp/xs-known-bugs-repro-20260929-034817` | `xs-known-bugs-repro-20260929-034817/` | E 线已知 bug 4/4 复现证据与上游回帖草稿 |
| `/home/baiyifan/xsrepro/{T1..T4,p1,p2,p3,...}` | `xsrepro/` | E 线定向靶标与 P1/P2/P3 实施产物 |
| 根仓 `.tmp/accept1-20260929-124451` | `accept1-20260929-124451/` | F 线验收战役（四签名矩阵、NC-1/2/3 证据） |
| `/data1/baiyifan/tmp/github-xref-b{1,2,3}` | `github-xref-b{1,2,3}/` | B 组上游交叉对照笔记（NOTES.md） |
| 各时期 tgz 归档 | `tgz/` | campaign24（含 SUMMARY.md 副本）、w23、isarch-fix-f3f4、model-fix、vs-explore 压缩包 |

## 备注

- `campaign24-archive.tgz` 内含 W24 campaign 全量（replay/gen/log）；`campaign24-SUMMARY.md` 在 `tgz/` 内同置。
- A 线模型修复的 worktree 在 `sail-riscv/.worktrees/model-fix`（分支 `model-fix-vd-nf@46f8273a`），产物 tgz 在 `tgz/model-fix-archive.tgz`。
- 2026-09-30 同日清理了 `/tmp` 中浮点线 09-26/27 历史批次（~95G，冻结证据已在 `isla/target/float-solve-evidence`）与本线残留；`/tmp` 不再保存项目证据。
