# P2 wide numeric adapter

`sail_softfloat_wide.h` and `.cpp` are production copies for P1 to place beside
`sail_softfloat.cpp`. P1 owns the public `sail_fp*` wrappers and build wiring.
The internal hooks support all `n > 0` bitvectors for eight integer-to-FP
operations, all 32 combinations of FP source and 16/32/64/128-bit integer
destination, and FP128 IEEE bit encoding. FP-to-integer inputs outside the
target range, NaNs and infinities return zero; the shared Sail policy chooses
the architectural saturated result and flags.

Run from the repository root, using the P0 patched Sail compiler and the P1
TLS build under test:

```sh
python3 agents/float_support_review/tools/unified_backend_p2_wide/run.py \
  --p0-sail isla/target/float-solve-evidence/unified-backend-p0/20260926T162859Z/sail-src/sail \
  --p1-build .tmp/unified-backend-p1-adapter/build \
  --out .tmp/unified-backend-p2-wide/final
```

`run.py` regenerates 82 Sail methods, compiles and runs them through a bridge
to the production P2 hooks, checks 61,820 conversions against a separate
integer-math oracle, and tests eight concurrent threads with distinct SoftFloat
environment sentinels. It also runs directed calls through P1's public
dispatch for n=129/65537, 16/128-bit outputs, FP128 IEEE encoding and state
restoration. P2 and test translation units use ASan and UBSan. The
P1 SoftFloat static library is linked with its TLS build and separately checked
for TLS state symbols; its C objects are not sanitizer instrumented by this
runner. Detailed commands and output live in the ignored output directory;
`manifest.json` records this run's source, compiler, library and binary hashes.

The generated fixture checks the wide-hook calling ABI and actual execution
of every shape. Full generated public-wrapper dispatch, shared Sail helper
flags and Isla model integration are separate integration gates.
