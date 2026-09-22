## `vfmv.v.f` splats 0 (or traps) for EEW < 64 — FP operand ignored

**Environment**
- Ara @ commit `34bd3bc1` (= origin/main), Verilator emulator
- `config=2_lanes` (stock config, VLEN=2048, ELEN=64)
- Reproduce: `./build/verilator/Vara_tb_verilator -c 2000000 -l ram,<elf>,elf` (note: `-c` must come before `-l`)

**Observed** (after `csrs mstatus, VS|FS dirty`, `f0` loaded with a non-zero double):
- `vsetvli` SEW=8 + `vfmv.v.f v2, f0` → **illegal-instruction trap**
- SEW=16 / SEW=32 → instruction retires, but **every body element is 0** (FP operand ignored)
- SEW=64 → correct

**Expected**: per RVV 1.0, `vfmv.v.f vd, fs1` writes `fs1` (converted to the element width) into every body element; SEW=8/16/32 are legal and must produce the operand value.

`FUNCTIONALITIES.md` lists `vfmv.v.f` as supported. All three widths reproduce on the stock `2_lanes` config. Happy to attach the minimal ELF/assembly on request — the reproducer is just the `vsetvli` + `vfmv.v.f v2, f0` pair above wrapped in a bare-metal `_start` that stores the result out via `vs1r.v`.
