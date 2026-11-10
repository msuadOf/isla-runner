An independent finite-enumeration constraint prevents `default` from recognizing an otherwise floating-point goal. The existing `qffp` tactic can process this restricted mixture: it converts FP operations first and sends residual datatype constraints to its existing SMT fallback.

Add an internal probe for quantifier-free FP expressions mixed with simple finite-enum constants and constructors, and use it alongside the existing `is-qffp` probe in `default`. Enum expressions are preserved; there is no enum-to-BV conversion or new tactic pipeline. Existing public `is-qffp`/`is-qffpbv` probes remain unchanged.

This is alternative B for #11500, independent of the alternative that preprocesses enums with `dt2bv`. These alternatives should not be stacked.

Scope and safeguards:
- Require both an FP term and an enum term; retain the existing predicate's checks for all other terms.
- Reject quantifiers/lambdas, arrays, general datatypes, enum-valued functions/ITEs, and other terms outside this restricted fragment. Initial simplification can eliminate unsupported terms before classification.
- Keep the original dispatch for the new fragment when proofs or unsat cores are requested. The existing pure-FP route is unchanged.
- If enums remain after `fpa2bv` and bit-blasting, the existing non-propositional fallback invokes SMT. Enum domain constraints and model interpretations remain available.

Validation against base `8fbb275aba0472e862e289c7af1331b3bd5d512c` (Release build reports 5.3.4):
- `test-z3 fpa` passes, including the FP/enum resource-budget reproducer, enum model readback, finite-domain exhaustion and an FP contradiction.
- Independent review: 27 semantic/type cases agree with base `default` and explicit SMT; SAT models satisfy original assertions. Three C API modes (plain/core/proof) each pass SAT/push-UNSAT/pop-SAT/assumption-UNSAT/recovery-SAT checks. Trace inspection confirms the FP-to-BV and residual-SMT route, with the original routes retained for core/proof modes.
- Author checks: 18 API checks pass with 64 original-assertion model evaluations true. Of 90 standalone queries, 88 produce expected answers within the short 60-second SMT probe limit; two real flags queries return UNKNOWN/canceled at that limit. With an explicit 7,200-second query budget, both now return SAT (395.04 s and 436.12 s elapsed), giving expected answers for all 90 cases across the stated budgets. These long-run wall times include initial CPU sharing and a subsequent affinity correction; they are completion evidence, not controlled speed comparisons. These are query probes, not complete Clause runs.

Tradeoff: preserving enums avoids eager enum model reconstruction but leaves a mixed residual goal for SMT. In a three-pair AB/BA/AB comparison, one real flags query took median 15.35 s here versus 5.95 s with enum preprocessing; a minimal reproducer took 0.085 s here versus 0.143 s with preprocessing. These measurements use the same base and fixed per-case CPUs; they are not universal performance claims. No complete Clause or production Isla integration is claimed.

Related: #11500.
