# 内存 clause 分支覆盖对照状态（W19 + G1-G8）

- 日期：2026-09-27。
- 范围：`make solve` MEMORY 组 48 clause（A 扩展展开 AMO/LOADRES/STORECON）逐 clause 语义分支覆盖五分类对照（①已覆盖 ②配置性不可达 ③预算/超时截断 ④引擎缺陷 ⑤语义无此分支）。
- 实施：调查与对照完成，无代码修改。产物底座 `/tmp/isla-memsolve-survey-20260927-125738/`（SURVEY.md 总表 + 48 clause 产物 + distribution-all.json + coverage/G1..G8 八份组报告）。
- 口径：worktree d643e0e isarch（md5 b53f…，smt-thread-interrupt）、配置 `riscv64_difftest_mem_excluded_pma.toml`（= W15 修正后 green 基线：RAM 8TB 地图 + PMP NAPOT 钉死 + satp=0 + mmio excluded）、limits_b12（fork 1/12）、--smt-timeout 1m、MODEL_TIMEOUT_MS=120s、时间盒 600/1800/3600s。
- 验证：48 clause 中 45 有 JSON（AMO panic、VLXSEGTYPE/VSXSEGTYPE 三档超时无 JSON）；总分布 4124 gen=1251 成功+1135 Load_AF+1012 Illg+712 SAMO_AF+10 VirI+4 Addr_Align；zSTORE 24/104 与 W15 基线逐数一致（交叉验证）。对照本身为产物核对+源码归因，非新动态验收。
- 结论：①覆盖良好——标量 LOAD/STORE、压缩 13 clause（B/H 四形态全）、LR（成功/AF/Align 齐且 Align 独立检查定论）、SC 成功/fault、向量 unit/mask 与段式（含部分成功后异常、first-fault 全分支）、cbo/fence 10 clause 全（TVM 双向实证、VirI 真实可达）。两次重要勘误：`plat_enable_misaligned_access` IR 固化 true（TOML 死键）→ 普通访存 Addr_Align ②不可达、仅 LR 可出；`sys_enable_fdext` 死键，FD 真实闸门是 mstatus FS=Off（Zcd 四条仅物化被杀、Zcf 四条 RV64 应剔除）。④引擎缺陷 7 项（AMO min/max.q panic 最严重，AMO 12+ 出口全缺）。③预算截断集中 VLX/VSX（吞吐 5-12×）与 W/D 宽度分块路径。②汇总：MMIO/PMP/翻译/SC 失配/VS 态等。
- 下一步候选（均未实施）：AMO ④修复（比较改位向量原生/fun_args 编码约束/limits 截 width=16 三选一）；FD 配置一行恢复（mstatus FS≠0）+ 清单剔除 Zcf；终值物化脱钩单开引擎议题（VLRETYPE 见证矛盾+未归因 Illg）；VLX/VSX 独占泳道复跑；is_exclusive 保真度与 --instruction-bits panic 修复。
- 入口：[合并矩阵与发现收敛](coverage-matrix.md)（原定 report.md 文件名被本环境写入限制拦截，改用此名）、[SURVEY 与跑批口径](/tmp/isla-memsolve-survey-20260927-125738/SURVEY.md)、[组报告 G1-G8](/tmp/isla-memsolve-survey-20260927-125738/coverage/)、[findings](../findings.md)。
