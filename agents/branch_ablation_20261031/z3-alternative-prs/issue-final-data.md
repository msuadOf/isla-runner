We have selected **A (#11505)** for [our fork's `main`](https://github.com/msuadOf/z3/tree/main), at exact commit `953e43301f406bbf41cf1ae8e600641345a8823b`. B (#11506) remains an alternative for discussion; this is a downstream choice, not a request to merge both.

Here are the completed five-pair comparisons and a public reproduction package: **[exact inputs, portable runner, environment and all per-run records](https://github.com/msuadOf/z3/tree/972455591a92ce548e40da05731640ed7f57f606/benchmarks/fp-enum-11500)** (evidence commit `972455591a92ce548e40da05731640ed7f57f606`).

A is finite-enum preprocessing followed by existing dispatch. B is restricted FP/enum detection followed by direct existing qffp. Base is `8fbb275aba0472e862e289c7af1331b3bd5d512c`; B is `ae64857b47ed6123c034c825e4b4dcb930e75b81`.

### Protocol

For each workload: AB, BA, AB, BA, AB (five fresh processes per version, no extra warmup), identical query bytes and the same CPU for both versions. Different workloads ran concurrently on separate physical cores. Explicit SMT budget: `-t:7200000` (7,200 seconds); outer process budget: 7,210 seconds. The host was shared, not CPU-isolated. Wall times include startup, parsing and solving. **All 120 runs returned SAT with exit code 0; no timeout/UNKNOWN observations are treated as completed timings.** These are standalone SMT queries, not whole Isla Clauses.

Environment: AMD EPYC 7543, two 32-core sockets, SMT2; GCC 15.2.0, CMake 4.2.3, Release `-O3 -DNDEBUG`, no LTO/GMP. Both source builds report Z3 5.3.4. Binary/input hashes, CPU topology/mapping and user/system time/RSS are in the package. The discarded preliminary timing pilot is excluded entirely.

### Mixed real/synthetic suite

Median wall time in seconds:

| Query | A | B | B/A |
| --- | ---: | ---: | ---: |
| nan | 0.1456 | 0.2356 | 1.618 |
| flags | 6.4469 | 15.4842 | 2.402 |
| minimal | 0.3525 | 0.2135 | 0.606 |
| enum-6-256 | 0.1636 | 0.1198 | 0.732 |
| enum-512-256 | 0.5946 | 0.0676 | 0.114 |
| enum-1024-256 | 1.2632 | 0.0552 | 0.044 |
| flags-dump-7 | 6.3014 | 41.4227 | 6.574 |
| flags-dump-11 | 1.8329 | 119.0785 | 64.968 |

`flags-dump-11` is a real query exported while executing `F_BIN_RM_TYPE_S`: path constraints select single-precision FDIV.S with round-toward-zero. It asks whether `old_fflags != (old_fflags | new_flags)` is reachable. The formula includes symbolic register selection, NaN-boxing/path constraints, f32 division, and f64 upward/downward divisions used to compute exception flags. `11` is a local input index, not an instruction ID.

The 512/1,024-constructor cases are stress boundaries, **not representative of our Sail enums**. Our relevant enum types usually have only 4–6 constructors, with potentially many variables. We therefore also ran the following variable-count sweep.

### Six constructors, varying variable count

Median wall time in milliseconds:

| Enum variables | A | B | A minus B |
| ---: | ---: | ---: | ---: |
| 64 | 39.20 | 29.71 | 9.49 |
| 256 | 63.34 | 47.29 | 16.05 |
| 512 | 70.09 | 45.64 | 24.45 |
| 1024 | 91.69 | 52.29 | 39.40 |

Each enum variable is independently constrained by `e_i != C0`, with the independent FP constraint `fp.isNaN(x)`. This measures variable-count overhead, not realistic FP/enum coupling. The 256-variable input is byte-identical across both suites, but the suites were scheduled separately: their wall times must not be pooled or attributed to a code change. Short process timings are sensitive to startup and shared-host load.

A was faster on the four real query inputs in this sample. B was faster on the synthetic enum inputs, but its median advantage for six-member enums up to 1,024 variables was 9–39 ms. B also showed considerable spread on the real flags queries (all five observations below). That tradeoff led us to choose A for our current workload, rather than claiming either approach wins universally.

<details>
<summary>All five wall-time observations (seconds; columns follow each version's chronological order)</summary>

| Suite / query | Version | 1 | 2 | 3 | 4 | 5 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| mixed / nan | A | 0.2266 | 0.1455 | 0.1445 | 0.1456 | 0.1531 |
| mixed / nan | B | 0.3919 | 0.4158 | 0.2323 | 0.2340 | 0.2356 |
| mixed / flags | A | 13.6727 | 6.5924 | 6.4469 | 6.1428 | 6.1134 |
| mixed / flags | B | 26.1270 | 16.0067 | 15.4382 | 15.4842 | 15.3393 |
| mixed / minimal | A | 1.1379 | 0.6825 | 0.3525 | 0.3180 | 0.3363 |
| mixed / minimal | B | 0.6612 | 0.7003 | 0.2135 | 0.2088 | 0.1924 |
| mixed / enum-6-256 | A | 0.1949 | 0.1572 | 0.1477 | 0.1636 | 0.1862 |
| mixed / enum-6-256 | B | 0.1123 | 0.0985 | 0.1198 | 0.1198 | 0.1241 |
| mixed / enum-512-256 | A | 0.8924 | 0.5946 | 0.5552 | 0.5343 | 0.6054 |
| mixed / enum-512-256 | B | 0.0902 | 0.0898 | 0.0507 | 0.0563 | 0.0676 |
| mixed / enum-1024-256 | A | 1.2711 | 1.2632 | 1.3063 | 1.1757 | 1.1680 |
| mixed / enum-1024-256 | B | 0.0587 | 0.0623 | 0.0552 | 0.0504 | 0.0502 |
| mixed / flags-dump-7 | A | 12.2492 | 6.3014 | 6.4073 | 6.2269 | 6.2811 |
| mixed / flags-dump-7 | B | 66.4233 | 41.4227 | 41.3781 | 41.2932 | 234.4996 |
| mixed / flags-dump-11 | A | 2.4852 | 1.7522 | 1.7324 | 1.8329 | 1.8837 |
| mixed / flags-dump-11 | B | 91.6394 | 85.6962 | 129.2787 | 241.2420 | 119.0785 |
| six-member / enum-6-64 | A | 0.0644 | 0.0404 | 0.0388 | 0.0392 | 0.0384 |
| six-member / enum-6-64 | B | 0.0297 | 0.0313 | 0.0301 | 0.0278 | 0.0282 |
| six-member / enum-6-256 | A | 0.0892 | 0.0633 | 0.0667 | 0.0580 | 0.0600 |
| six-member / enum-6-256 | B | 0.0473 | 0.0473 | 0.0488 | 0.0418 | 0.0430 |
| six-member / enum-6-512 | A | 0.1253 | 0.0760 | 0.0701 | 0.0679 | 0.0639 |
| six-member / enum-6-512 | B | 0.0574 | 0.0627 | 0.0433 | 0.0456 | 0.0444 |
| six-member / enum-6-1024 | A | 0.1372 | 0.1010 | 0.0917 | 0.0835 | 0.0761 |
| six-member / enum-6-1024 | B | 0.0698 | 0.0637 | 0.0523 | 0.0513 | 0.0489 |

</details>

Earlier flags-7/11 probes stopped at a 60-second SMT budget and returned UNKNOWN/canceled. Their subsequent 7,200-second-budget runs returned SAT after 395/436 seconds, but initially shared a CPU and had affinity changed mid-run. Those were completion checks, not controlled performance comparisons; the five-pair table above uses new runs with fixed affinity throughout.

### Reproduce

Build the exact two revisions with the same compiler/settings:

```sh
git clone https://github.com/msuadOf/z3.git z3-a
git -C z3-a checkout 953e43301f406bbf41cf1ae8e600641345a8823b
cmake -S z3-a -B z3-a/build -DCMAKE_BUILD_TYPE=Release
cmake --build z3-a/build --target shell -j 24

git clone https://github.com/msuadOf/z3.git z3-b
git -C z3-b checkout ae64857b47ed6123c034c825e4b4dcb930e75b81
cmake -S z3-b -B z3-b/build -DCMAKE_BUILD_TYPE=Release
cmake --build z3-b/build --target shell -j 24

git clone --filter=blob:none --sparse --branch benchmarks/fp-enum-11500 \
  https://github.com/msuadOf/z3.git z3-evidence
git -C z3-evidence sparse-checkout set benchmarks/fp-enum-11500
```

Pin evidence to `972455591a92ce548e40da05731640ed7f57f606` (`git -C z3-evidence checkout 972455591a92ce548e40da05731640ed7f57f606`).


Run both suites (Linux/Python 3/GNU time/taskset; output directories must be new):

```sh
python3 z3-evidence/benchmarks/fp-enum-11500/reproduce.py \
  --a "$PWD/z3-a/build/z3" --b "$PWD/z3-b/build/z3" \
  --suite mixed-five --cpus 33 47 49 52 56 60 37 17 --output rerun-mixed

python3 z3-evidence/benchmarks/fp-enum-11500/reproduce.py \
  --a "$PWD/z3-a/build/z3" --b "$PWD/z3-b/build/z3" \
  --suite enum-six-five --cpus 33 47 49 52 --output rerun-enum
```

Replace CPU IDs with CPUs available on your machine, each on a distinct physical core (`lscpu -p=CPU,CORE,SOCKET`). The runner checks the core topology and preserves each workload's affinity. Reports include every run, medians, means, ranges and input hashes. I smoke-tested the portable runner on the full 40-run small-enum suite; those smoke timings are not mixed into the published original observations.

The six-member synthetic input content can also be generated directly:

```python
for count in [64, 256, 512, 1024]:
    lines = ["(declare-datatypes () ((E C0 C1 C2 C3 C4 C5)))",
             "(declare-const x (_ FloatingPoint 8 24))",
             "(assert (fp.isNaN x))"]
    for i in range(count):
        lines += [f"(declare-const e{i} E)", f"(assert (not (= e{i} C0)))"]
    lines += ["(check-sat-using default)"]
    open(f"enum-6-{count}.smt2", "w").write("\n".join(lines) + "\n")
```

All real queries are included verbatim as `mixed-five/<query-name>/query.smt2`, with SHA256 checksums. Full reproduction instructions and workload descriptions are in the package README. No production Isla integration or complete-Clause performance result is claimed.
