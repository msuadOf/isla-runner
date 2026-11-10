An independent finite-enumeration constraint prevents `default` from recognizing an otherwise floating-point goal. For example, the FP square-root/NaN reproducer in #11500 exceeds a resource budget when an unrelated enum variable is present.

Run the existing `dt2bv` preprocessor after the initial simplification, then retain the existing strategy dispatch. For eligible finite-enum expressions, this supplies BV domain constraints and the existing model converter restores enum values. The existing `is-qffp` probe and FP solver are unchanged.

This is alternative A for #11500, independent of the alternative that directly routes a restricted FP/enum fragment to `qffp`. These alternatives should not be stacked.

Scope and safeguards:
- Skip the new preprocessor for goals containing quantifier ASTs, including lambdas. The existing enum rewriter does not consistently convert lambda binders; a regression checks that such a goal still returns UNSAT through the original path.
- Preserve the original paths when proofs or unsat cores are requested.
- Reuse `dt2bv`'s existing applicability checks for enum uses. This affects eligible enum goals beyond FP; it is deliberately a broader preprocessing alternative.

Validation against base `8fbb275aba0472e862e289c7af1331b3bd5d512c` (Release build reports 5.3.4):
- `test-z3 fpa` passes, including a resource-budget FP/enum reproducer, enum model readback, six-value domain exhaustion, an FP contradiction and the lambda regression.
- 90/90 standalone queries pass (55 behavior/type cases, 25 real slow-query dumps and 10 mixed-type queries). These are query-level probes, not full instruction/Clause runs.
- 18 C API checks pass; 64 evaluations of original assertions in returned models are true, covering assumptions and incremental restoration.
- Independent review found the lambda boundary in the initial draft; the guard and regression address it. The revised patch passed independent source review, 42 fresh CLI executions, and 14 original-assertion/assumption model readbacks.

Tradeoff: preprocessing adds a traversal and eager enum model reconstruction. In an independent pure-enum probe with 8,192 constructors and 32 distinct variables, the initial preprocessing version took a median 0.483 s versus 0.095 s for base. This change does not promise universal speedups or unchanged results under identical resource budgets. No production Isla integration or complete 7,200-second Clause validation is claimed.

Related: #11500.
