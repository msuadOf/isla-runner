I have opened two independent, alternative fixes for this dispatch problem:

- **A: #11505 — preprocess eligible finite enums with the existing `dt2bv`, then retain the existing `default` dispatch.** This is a three-line production addition (including the include). The existing conversion supplies enum-domain bounds and model reconstruction. It skips goals containing quantifier ASTs (including lambdas) and skips proof/core modes. Its scope is broader than FP: non-FP enum goals also incur the preprocessing cost.
- **B: #11506 — recognize a restricted FP + simple-enum fragment and send it directly to the existing `qffp`.** This leaves enum expressions unchanged. After FP conversion and bit-blasting, residual enum constraints reach the existing SMT fallback. Public QF_FP probes remain unchanged; unsupported types and the newly handled fragment's proof/core modes retain the original paths.

These are alternatives, not stacked changes. For the restricted fragment handled by B, the code preserves satisfiability in both routes: A encodes finite-enum values with domain bounds and a model inverse, whereas B keeps the datatype constraints intact. The patches have different overall applicability and performance; identical concrete models or identical resource-bounded UNKNOWN behavior are not expected.

Both patches have independent source/dynamic reviews and pass `test-z3 fpa`. A's initial draft exposed an existing `dt2bv` lambda-binder boundary; the published version skips such goals, includes the regression, and passed fresh independent review. A passes 90 query-level checks plus 18 API checks with 64 original-assertion model evaluations true. B's independent 27 semantic/type cases agree with base default and explicit SMT; its plain/core/proof API state-transition checks pass. In the author's 90-query suite, B has 88 expected answers within the 60-second probe budget; two real flags queries return UNKNOWN/canceled at that limit. The explicit 7,200-second query-budget rerun has now completed: both return SAT, at 395.04 s and 436.12 s elapsed, so all 90 cases have expected answers across these budgets. The long-run times include initial CPU sharing and a later affinity correction; they are not controlled comparative timings. No complete Clause validation is claimed.

A three-pair AB/BA/AB comparison on fixed per-case CPUs illustrates the tradeoff (median seconds, same base `8fbb275`, Release build reporting 5.3.4):

| Query | A: enum preprocessing | B: direct qffp |
| --- | ---: | ---: |
| Minimal FP/enum reproducer | 0.143 | 0.085 |
| One real flags query | 5.95 | 15.35 |
| One real sqrt/NaN query | 0.100 | 0.179 |
| Synthetic FP/enum, 1,024 constructors × 256 enum variables | 0.513 | 0.027 |

These comparison timings used the initial A preprocessing version; the published A adds a quantifier/lambda skip guard. The timed inputs are quantifier-free, but the table is not presented as a new timing run of the revised binary. Larger enum-model reconstruction and residual mixed SMT solving have different costs, so neither proposal is claimed to be universally faster.

I would welcome guidance on whether the broader reuse of finite-enum preprocessing or the narrower dispatch-only change is preferred upstream.
