# Issue draft — A1: `vnclip`/`vnclipu` with SEW=64 kills the simulation (missing illegal-instruction check)

> Note: pulp-platform/ara has no `.github/ISSUE_TEMPLATE` (only a PR template), so this draft
> follows a generic bug-report structure matching the repo's concise style.

**Title:** `vnclip`/`vnclipu` with vtype SEW=64 crashes the simulator (`simd_alu.sv:444` unique-case assertion) instead of raising illegal-instruction

## Description

With a valid `vsetvli` context of SEW=64, executing any `vnclip`/`vnclipu` variant
(`.wi`/`.wv`/`.wx`) makes the Verilator simulation abort with a `unique case` assertion
inside `simd_alu` instead of raising an illegal-instruction exception.

Per the RVV 1.0 specification, narrowing instructions read their source operands at
EEW = 2×SEW. With SEW=64 the source EEW is 128, which exceeds ELEN (=64 for Ara), so the
instruction is *illegal* and must trap. Ara's own dispatcher already implements exactly this
check for the sibling narrowing instructions `vnsrl`/`vnsra`
(`ara_dispatcher.sv:872/890`, `1141/1159`, `1380/1398`: `vsew > EW32 -> illegal_insn`),
but the three `VNCLIPU`/`VNCLIP` decode sites are missing it:

- OPIVV: `ara_dispatcher.sv:901-908`
- OPIVX: `ara_dispatcher.sv:1170-1177`
- OPIVI: `ara_dispatcher.sv:1409-1416`

These sites only set `eew_vs2 = vsew.next()`, producing `EW128` (`3'h7`... effectively the
`vew_i` value `3'h3` = EW64 reaches `simd_alu.sv:444`), where the `VNCLIP` `unique case`
covers only `EW8/EW16/EW32` — hence the assertion.

## Minimal reproducer

```asm
# vnclip.wi SEW=64: source EEW = 2*SEW = 128 > ELEN(64) -> must be illegal
.option norvc
.section .text.init
.align 4
.globl _start
_start:
    la t0, init_trap
    csrw mtvec, t0
    li t0, 0x6600
    csrs mstatus, t0              # VS|FS Dirty
    la t0, test_trap
    csrw mtvec, t0
    la sp, _stack_top
    li t1, 4
    vsetvli zero, t1, e64, m1     # zimm = 0x18: SEW=64
    vmv.v.i v8, 1
    vnclip.wi v10, v8, 11         # <-- must trap; kills the sim instead
    li a0, 0
    j _exit

    .align 2
test_trap:
    csrr a0, mcause
    li t0, 2
    beq a0, t0, 1f
    li a0, 8
    j _exit
1:  li a0, 2                      # illegal-instruction observed
    j _exit

    .align 2
init_trap:
    li a0, 32
    j _exit

    .align 2
_exit:
    li t0, 0xD0000000             # Ara CTRL eoc register
    sd a0, 0(t0)
1:  j 1b

.section .stack
.align 4
.space 4096
_stack_top:
```

Build and run (bare-metal ELF linked at 0x80000000):

```sh
riscv64-unknown-elf-gcc -march=rv64gcv -mabi=lp64d -nostdlib -static \
  -T ara.ld -o vnclip_sew64.elf vnclip_sew64.S
# note: -c must come before -l (the emu's argv handling permutes otherwise)
./hardware/build/verilator/Vara_tb_verilator -c 2000000 -l ram,vnclip_sew64.elf,elf
```

## Expected behavior

`vnclip.wi` with SEW=64 raises an illegal-instruction exception (mcause=2), as spike does
(`--isa=rv64gcv_zvl2048b` traps the instruction). Control experiment on the same setup:
`vnsrl.wi v10, v8, 11` at SEW=64 correctly traps on Ara.

## Actual behavior

The simulation aborts:

```
%Error: hardware/src/lane/simd_alu.sv:444: Assertion failed in
  TOP...i_valu.i_simd_alu.p_alu: unique case, but none matched for '3'h3'
%Error: hardware/src/lane/simd_alu.sv:444: Verilog $stop
```

All six variants (`vnclip`/`vnclipu` × `.wi`/`.wv`/`.wx`) behave the same; SEW ∈ {8,16,32}
retire normally. Found by differential fuzzing (16/19908 single-instruction cases).

## Suggested fix

Mirror the `VNSRL`/`VNSRA` check in the three `VNCLIPU`/`VNCLIP` decode sites:

```systemverilog
if (int'(csr_vtype_q.vsew) > int'(EW32)) illegal_insn = 1'b1;
```

(These sites likely also want the `lmul_vs2 = next_lmul(...)` source-EMUL bookkeeping that
the narrowing siblings set, so the shared operand-group checks validate rs2/vs2 at 2×LMUL.)

## Environment

- Ara commit: `34bd3bc1` (main at time of report)
- Config: `config=2_lanes` (VLEN=2048, NrLanes=2, ELEN=64), Verilator emu
  (`hardware/build/verilator/Vara_tb_verilator`)
- Reproduced on both the default 2_lanes build and a vlen=128 build
