# 最终证据提交清单

选定 **2157个普通文件，25,557,577字节（24.37MiB）**，另加本JSON/MD索引。快照时间 `2026-11-03T09:38:48.611536+00:00`。最终限定签收已落盘，父仓发布与gitlink-refseal由main处理。

精确文件集合为[机器清单](final-evidence-files.json)的`files`数组，每项含根目录相对`path`、真实`bytes`和`sha256`。索引不做递归自哈希，须另行复制。只写这两份索引，没有复制、暂存、提交或修改已审脚本/报告。

## 选择边界

保留可复用代码、源fixture、配置、补丁、计划/状态/最终报告、最终converged源码与IR独审、独立Fraction/SoftFloat审查、最终315实际小JSON及command/result/config、两正式入口实际JSON、执行时序、26步回归summary/checks与最终限定签收。小Sail fixture与SMT等价证明也保留。

排除所有symlink、IR、二进制、target/cache/compile/objects、itrace、任何.log、工具链.s/.bin与大体积Sail生成C/H。旧315逐例目录、旧conversion/probe重复archive、旧representation实际结果及旧CFG生成JSON不收入；历史摘要、独审和真实hash仍保留。超2MiB JSON只记录真实hash和结构，不伪造裁剪actual。归档symlink不跟随。

## 体量分组

| 分组 | 数量 | 字节 |
| --- | ---: | ---: |
| `validation/exceptions` | 1296 | 12,361,315 |
| `validation/conversions` | 69 | 3,237,046 |
| `review/acceptance` | 118 | 2,333,410 |
| `validation/generation` | 59 | 2,126,395 |
| `validation/assembly-fix` | 49 | 1,652,427 |
| `validation/runs` | 63 | 730,846 |
| `review/model` | 80 | 655,107 |
| `validation/full_batch` | 54 | 376,597 |
| `validation/representations` | 116 | 335,572 |
| `validation/integration` | 12 | 219,693 |
| `baseline-0008fae/reduction` | 25 | 216,635 |
| `validation/flags` | 43 | 134,455 |
| `validation/make` | 14 | 119,827 |
| `baseline-0008fae/architecture-decision-20261103.json` | 1 | 76,830 |
| `review/enum` | 25 | 70,787 |
| `exceptions/source.diff` | 1 | 50,139 |
| `inventory/affected-clauses.json` | 1 | 43,843 |
| `baseline-0008fae/converged-ir-review-20261103.json` | 1 | 43,828 |
| `baseline-0008fae/converged-checker-9ebd0d937edc805e49103984bffbb507470115d349d7262553b6943b9e2763cf.py` | 1 | 42,273 |
| `baseline-0008fae/model-review.checker-053b48b3b588c58f87d74a72c7a5d5097a610ccea37700d94380142fede5ad16.py` | 1 | 42,210 |
| `validation/bin` | 21 | 33,869 |
| `baseline-0008fae/converged-checker-negative-20261103.json` | 1 | 22,516 |
| `baseline-0008fae/converged-checker-positive-20261103.json` | 1 | 20,360 |
| `baseline-0008fae/model-review.checker-positive-e9d69d2.json` | 1 | 19,796 |
| `baseline-0008fae/model-review.ir-e9d69d2.json` | 1 | 19,632 |
| `inventory/current-source-ir.md` | 1 | 18,248 |
| `baseline-0008fae/model-review.json` | 1 | 18,109 |
| `baseline-0008fae/isla-review.json` | 1 | 16,586 |
| `baseline-0008fae/isla-review.md` | 1 | 16,296 |
| `baseline-0008fae/model-review.md` | 1 | 16,154 |
| `(topic root)` | 5 | 15,272 |
| `baseline-0008fae/converged-ir-values-20261103.json` | 1 | 14,300 |
| `validation/run_clause.py` | 1 | 12,383 |
| `validation/inputs.model-converged-0f7b8fb-itrace.json` | 1 | 12,053 |
| `validation/inputs.model-e9d69d2-itrace.json` | 1 | 11,987 |
| `validation/inputs.model-21418d0-itrace.json` | 1 | 11,953 |
| `validation/inputs.model-8ad5e8e-itrace.json` | 1 | 11,953 |
| `validation/inputs.model-8ad5e8e.json` | 1 | 11,932 |
| `validation/inputs.final.template.json` | 1 | 10,929 |
| `validation/inputs.itrace.template.json` | 1 | 10,929 |
| `validation/inputs.template.json` | 1 | 10,908 |
| `baseline-0008fae/architecture-decision-20261103.md` | 1 | 10,906 |
| `validation/procedure.md` | 1 | 10,675 |
| `validation/generate.py` | 1 | 10,153 |
| `inventory/validation_plan.md` | 1 | 10,087 |
| `baseline-0008fae/model-review.values-e9d69d2.json` | 1 | 10,015 |
| `baseline-0008fae/architecture-decision-20261103.py` | 1 | 7,660 |
| `baseline-0008fae/architecture-candidates-review-20261103.json` | 1 | 7,384 |
| `validation/checker-negative-controls-final-v2.json` | 1 | 7,243 |
| `validation/checker-negative-controls-final-v3.json` | 1 | 7,243 |
| `baseline-0008fae/control-opinion.md` | 1 | 7,120 |
| `baseline-0008fae/architecture-candidates-review-20261103.py` | 1 | 6,998 |
| `exceptions/rewrite_exceptions.py` | 1 | 6,753 |
| `validation/matrix.md` | 1 | 6,698 |
| `baseline-0008fae/model-review.checker-negative-e9d69d2.json` | 1 | 6,671 |
| `baseline-0008fae/converged-checker-negative-20261103.py` | 1 | 6,542 |
| `baseline-0008fae/converged-ir-values-20261103.py` | 1 | 6,505 |
| `baseline-0008fae/model-review.checker-negative-e9d69d2.py` | 1 | 6,498 |
| `baseline-0008fae/control-candidate-review.py` | 1 | 6,357 |
| `baseline-0008fae/model-review.py` | 1 | 6,265 |
| `baseline-0008fae/model-review.values-e9d69d2.py` | 1 | 6,240 |
| `exceptions/verify_equivalence.py` | 1 | 6,224 |
| `wrappers/report.md` | 1 | 5,911 |
| `validation/check_cfg.py` | 1 | 5,892 |
| `baseline-0008fae/converged-source-review-20261103.py` | 1 | 5,888 |
| `inventory/build_clause_closure.py` | 1 | 5,822 |
| `validation/checker-negative-controls-final.json` | 1 | 5,556 |
| `validation/checker-negative-controls-v128-v4.json` | 1 | 5,556 |
| `baseline-0008fae/model-review.candidate.py` | 1 | 5,278 |
| `inventory/workaround-region-audit.md` | 1 | 5,270 |
| `wrappers/prove_selection.py` | 1 | 5,198 |
| `narrow/prove_equivalence.py` | 1 | 5,098 |
| `baseline-0008fae/converged-provenance-review-20261103.py` | 1 | 5,004 |
| `baseline-0008fae/model-review.provenance-e9d69d2.py` | 1 | 4,899 |
| `validation/check_cfg_mutations.py` | 1 | 4,775 |
| `validation/checker-negative-controls-v128-v3.json` | 1 | 4,692 |
| `baseline-0008fae/isla-review.py` | 1 | 4,299 |
| `narrow/source-review.md` | 1 | 4,267 |
| `validation/audit_generation.py` | 1 | 4,183 |
| `flags/check_flags_changed.py` | 1 | 4,081 |
| `baseline-0008fae/converged-ir-review-20261103.py` | 1 | 3,858 |
| `validation/check_cfg_mutations_e9.py` | 1 | 3,754 |
| `validation/seal_inputs.py` | 1 | 3,704 |
| `validation/inputs.model-converged-0f7b8fb-two-clause.json` | 1 | 3,701 |
| `validation/checker-negative-controls-v128-v2.json` | 1 | 3,529 |
| `validation/checker-negative-controls-v128.json` | 1 | 3,529 |
| `baseline-0008fae/model-review.ir-e9d69d2.py` | 1 | 3,503 |
| `baseline-0008fae/model-review.checker-e9d69d2.md` | 1 | 3,329 |
| `baseline-0008fae/converged-ir-review-20261103.md` | 1 | 3,263 |
| `validation/check_cfg_mutations_converged.py` | 1 | 3,199 |
| `narrow/source.patch` | 1 | 3,189 |
| `baseline-0008fae/converged-source-review-20261103.json` | 1 | 3,086 |
| `enum/report.md` | 1 | 3,064 |
| `baseline-0008fae/model-review.provenance-e9d69d2.json` | 1 | 2,952 |
| `baseline-0008fae/converged-provenance-review-20261103.json` | 1 | 2,947 |
| `exceptions/report.md` | 1 | 2,740 |
| `baseline-0008fae/ir-review-e9d69d2.md` | 1 | 2,719 |
| `narrow/equivalence.json` | 1 | 2,696 |
| `flags/implementation.md` | 1 | 2,632 |
| `baseline-0008fae/architecture-candidates-review-20261103.md` | 1 | 2,598 |
| `baseline-0008fae/control-candidate-review.md` | 1 | 2,581 |
| `baseline-0008fae/model-review.checker-positive-e9d69d2.py` | 1 | 2,510 |
| `baseline-0008fae/converged-source-review-20261103.md` | 1 | 2,454 |
| `baseline-0008fae/plan.md` | 1 | 2,374 |
| `baseline-0008fae/converged-checker-review-20261103.md` | 1 | 2,264 |
| `baseline-0008fae/model-review.candidate.md` | 1 | 2,186 |
| `baseline-0008fae/converged-checker-positive-20261103.py` | 1 | 2,178 |
| `validation/freeze_source.py` | 1 | 1,857 |
| `baseline-0008fae/model-review.candidate.json` | 1 | 1,729 |
| `review/registry.json` | 1 | 1,537 |
| `baseline-0008fae/control-candidate-review.json` | 1 | 1,344 |
| `narrow/f16ToI16.smt2` | 1 | 1,339 |
| `narrow/f32ToI16.smt2` | 1 | 1,339 |
| `narrow/f16ToI8.smt2` | 1 | 1,304 |
| `baseline-0008fae/converged-checker-installed-20261103.json` | 1 | 1,089 |
| `baseline-0008fae/model-review.generation-scripts-e9d69d2.json` | 1 | 1,042 |
| `publication/completed.json` | 1 | 1,041 |
| `flags/model.patch` | 1 | 983 |
| `narrow/f16ToUi16.smt2` | 1 | 955 |
| `narrow/f32ToUi16.smt2` | 1 | 955 |
| `validation/red-baseline.json` | 1 | 942 |
| `narrow/f16ToUi8.smt2` | 1 | 932 |
| `baseline-0008fae/model-review.checker-schema-e9d69d2.json` | 1 | 775 |
| `validation/cpu-allocation.json` | 1 | 569 |

## 最终315与独审锚点

`{"result_json": 315, "command_json": 315, "config_toml": 315, "actual_output_json": 315}`

最终315数值/来源、最终执行时序、安装集成、26步summary/checks和final-signoff.md/json均已收入。数量及本清单不代替独立审查结论；限定范围仍以final-exit-scope及final-signoff为准。

## 大文件与symlink

排除超2MiB文件16项；JSON的实际SHA、top keys和list长度见over_2mib。最终315大summary记录完整真实SHA及results=315，逐例实际JSON仍收入。排除symlink6项：

| 路径 | 目标（未跟随） |
| --- | --- |
| `agents/float_review_closure_20261102/validation/assembly-fix/make-converged-0f7b8fb/smoke/scripts` | `.worktree/runner-float/isla/scripts` |
| `agents/float_review_closure_20261102/validation/assembly-fix/make-e9d69d2/smoke/scripts` | `.worktree/runner-float/isla/scripts` |
| `agents/float_review_closure_20261102/validation/make/model-21418d0-exact/smoke/scripts` | `.worktree/runner-float/isla/scripts` |
| `agents/float_review_closure_20261102/validation/make/model-8ad5e8e/smoke/scripts` | `.worktree/runner-float/isla/scripts` |
| `agents/float_review_closure_20261102/validation/runs/float-closure-21418d0-42000be-20261103` | `${HOME}/.cache/isla-runner-float-closure-20261103/archives/float-closure-21418d0-42000be-20261103` |
| `agents/float_review_closure_20261102/validation/runs/float-closure-e9d69d2-42000be-20261103-pool16` | `${HOME}/.cache/isla-runner-float-closure-20261103/archives/float-closure-e9d69d2-42000be-20261103-pool16` |

## 引用检查

选中文档直接链接和JSON单一路径值的缺失/外置/排除项均在reference_audit.items逐项列明；被排除的小文件尽量附真实hash。版本化仓库源码清单标为versioned_source_reference，不当作议题目录的缺失文件。命令、源码行号、动态Python路径、glob和模板不展开。

| 类别 | 数量 |
| --- | ---: |
| `excluded_by_policy` | 2557 |
| `existing_external_dependency` | 151 |
| `external_symlink_artifact` | 158 |
| `versioned_source_reference` | 68 |
| `missing_reference` | 30 |

### 缺失引用

| 路径 | 来源（最多2项） |
| --- | --- |
| `agents/float_review_closure_20261102/review/acceptance/time.txt` | `agents/float_review_closure_20261102/review/acceptance/final-harness-dryrun-C_ADDI4SPN.json`<br>`agents/float_review_closure_20261102/review/acceptance/final-harness-dryrun-FLEQ_S.json` |
| `agents/float_review_closure_20261102/review/enum/time.txt` | `agents/float_review_closure_20261102/review/enum/itrace-smoke-preflight.json` |
| `agents/float_review_closure_20261102/validation/conversions/runs/rv64d-v128-model-e9d69d2-attempt1` | `agents/float_review_closure_20261102/validation/conversions/run-launch-model-e9d69d2.json` |
| `agents/float_review_closure_20261102/validation/full_batch/e9/time.txt` | `agents/float_review_closure_20261102/validation/full_batch/e9/harness-preflight.json` |
| `agents/float_review_closure_20261102/validation/full_batch/final/time.txt` | `agents/float_review_closure_20261102/validation/full_batch/final/preflight-C_ADDI4SPN.json`<br>`agents/float_review_closure_20261102/validation/full_batch/final/preflight-FLEQ_S.json` |
| `agents/float_review_closure_20261102/validation/full_batch/time.txt` | `agents/float_review_closure_20261102/validation/full_batch/final-smoke-preflight.json`<br>`agents/float_review_closure_20261102/validation/full_batch/first-job-preflight.json` |
| `agents/float_review_closure_20261102/validation/generation/model-converged-0f7b8fb/time.txt` | `agents/float_review_closure_20261102/validation/generation/model-converged-0f7b8fb/fleq-dry-run.json` |
| `agents/float_review_closure_20261102/validation/representations/model-21418d0-exact/bf16-vl0/time.txt` | `agents/float_review_closure_20261102/validation/representations/model-21418d0-exact/bf16-vl0/result.json` |
| `agents/float_review_closure_20261102/validation/representations/model-21418d0-exact/bf16-vl1/time.txt` | `agents/float_review_closure_20261102/validation/representations/model-21418d0-exact/bf16-vl1/result.json` |
| `agents/float_review_closure_20261102/validation/representations/model-21418d0-exact/c-addi4spn/time.txt` | `agents/float_review_closure_20261102/validation/representations/model-21418d0-exact/c-addi4spn/result.json` |
| `agents/float_review_closure_20261102/validation/representations/model-21418d0-exact/exact-int-to-D/time.txt` | `agents/float_review_closure_20261102/validation/representations/model-21418d0-exact/exact-int-to-D/result.json` |
| `agents/float_review_closure_20261102/validation/representations/model-21418d0-exact/fleq-D-qNaN/time.txt` | `agents/float_review_closure_20261102/validation/representations/model-21418d0-exact/fleq-D-qNaN/result.json` |
| `agents/float_review_closure_20261102/validation/representations/model-21418d0-exact/fleq-H-qNaN/time.txt` | `agents/float_review_closure_20261102/validation/representations/model-21418d0-exact/fleq-H-qNaN/result.json` |
| `agents/float_review_closure_20261102/validation/representations/model-21418d0-exact/fleq-S-qNaN/time.txt` | `agents/float_review_closure_20261102/validation/representations/model-21418d0-exact/fleq-S-qNaN/result.json` |
| `agents/float_review_closure_20261102/validation/representations/model-21418d0-exact/sqrt-D/time.txt` | `agents/float_review_closure_20261102/validation/representations/model-21418d0-exact/sqrt-D/result.json` |
| `agents/float_review_closure_20261102/validation/representations/model-21418d0-exact/sqrt-H/time.txt` | `agents/float_review_closure_20261102/validation/representations/model-21418d0-exact/sqrt-H/result.json` |
| `agents/float_review_closure_20261102/validation/representations/model-21418d0-exact/sqrt-S/time.txt` | `agents/float_review_closure_20261102/validation/representations/model-21418d0-exact/sqrt-S/result.json` |
| `agents/float_review_closure_20261102/validation/representations/model-21418d0-exact/vfncvt-i8/time.txt` | `agents/float_review_closure_20261102/validation/representations/model-21418d0-exact/vfncvt-i8/result.json` |
| `agents/float_review_closure_20261102/validation/representations/model-21418d0-exact/vfncvt-ui8/time.txt` | `agents/float_review_closure_20261102/validation/representations/model-21418d0-exact/vfncvt-ui8/result.json` |
| `agents/float_review_closure_20261102/validation/representations/model-8ad5e8e/bf16-vl0/time.txt` | `agents/float_review_closure_20261102/validation/representations/model-8ad5e8e/bf16-vl0/result.json` |
| `agents/float_review_closure_20261102/validation/representations/model-8ad5e8e/bf16-vl1/time.txt` | `agents/float_review_closure_20261102/validation/representations/model-8ad5e8e/bf16-vl1/result.json` |
| `agents/float_review_closure_20261102/validation/representations/model-8ad5e8e/c-addi4spn/time.txt` | `agents/float_review_closure_20261102/validation/representations/model-8ad5e8e/c-addi4spn/result.json` |
| `agents/float_review_closure_20261102/validation/representations/model-8ad5e8e/fleq-D-qNaN/time.txt` | `agents/float_review_closure_20261102/validation/representations/model-8ad5e8e/fleq-D-qNaN/result.json` |
| `agents/float_review_closure_20261102/validation/representations/model-8ad5e8e/fleq-H-qNaN/time.txt` | `agents/float_review_closure_20261102/validation/representations/model-8ad5e8e/fleq-H-qNaN/result.json` |
| `agents/float_review_closure_20261102/validation/representations/model-8ad5e8e/fleq-S-qNaN/time.txt` | `agents/float_review_closure_20261102/validation/representations/model-8ad5e8e/fleq-S-qNaN/result.json` |
| `agents/float_review_closure_20261102/validation/representations/model-8ad5e8e/sqrt-D/time.txt` | `agents/float_review_closure_20261102/validation/representations/model-8ad5e8e/sqrt-D/result.json` |
| `agents/float_review_closure_20261102/validation/representations/model-8ad5e8e/sqrt-H/time.txt` | `agents/float_review_closure_20261102/validation/representations/model-8ad5e8e/sqrt-H/result.json` |
| `agents/float_review_closure_20261102/validation/representations/model-8ad5e8e/sqrt-S/time.txt` | `agents/float_review_closure_20261102/validation/representations/model-8ad5e8e/sqrt-S/result.json` |
| `agents/float_review_closure_20261102/validation/representations/model-8ad5e8e/vfncvt-i8/time.txt` | `agents/float_review_closure_20261102/validation/representations/model-8ad5e8e/vfncvt-i8/result.json` |
| `agents/float_review_closure_20261102/validation/representations/model-8ad5e8e/vfncvt-ui8/time.txt` | `agents/float_review_closure_20261102/validation/representations/model-8ad5e8e/vfncvt-ui8/result.json` |

## main发布入口

- 逐项复制files[].path及本两份索引；复制前lstat拒绝symlink，不遍历归档目标。
- 新增publication final-components/refseal由main另行纳入；若再次修改选中文档，更新对应bytes/SHA后复制。
- 不将旧77条预算或延期OPEN转写成新版本通过。

全量lstat/大小/SHA复核异常0项；所有priority anchors均已检查。复制、暂存、修改已审脚本/报告与新增PASS等actions均为false。
