# Issue draft — B10: vector store reading the destination register of `vcompress.vm` (and friends) never completes — simulation hangs

> Note: pulp-platform/ara has no `.github/ISSUE_TEMPLATE` (only a PR template), so this draft
> follows a generic bug-report structure matching the repo's concise style.

**Title:** Simulation hangs forever when a whole-register/element store reads the destination register of `vcompress.vm` (also after masked `vslideup`, `vrgather`, `vnclip`, `vmadc/vmsbc`)

## Description

After `vcompress.vm` retires, any subsequent vector memory instruction that **reads the same
destination register** never completes: the simulation runs to the cycle limit without
retiring the store or writing `tohost`/the CTRL exit register. The `vcompress` itself
retires normally, and stores of *other* vector registers proceed fine.

Found by differential fuzzing: 167/10087 check cases (all of the form "test instruction +
32×`vs1r.v` signature export") timed out at 20M cycles. The affected test-instruction
families are `vslideup` (40), `vnclip`/`vnclipu` (41), `vrgather` (52), `vmadc`/`vmsbc`
(17), `vcompress` (2), `vslidedown` (6), `vrgatherei16` (5). The hang is **independent of
`vstart`** (minimal repro below uses `vstart=0`) and independent of the loaded register
contents. Five original timeout ELFs were re-run unmodified on the default 2_lanes build:
5/5 still hang, so this is not an artifact of an unusual configuration.

Minimized trigger matrix (e16, m1, vl=1, `vstart=0`, `vcompress.vm v31, v0, v0`):

| Sequence | Result |
|---|---|
| `vcompress.vm` alone, then exit | retires, exits (tohost=0) |
| `vcompress.vm` + `vs1r.v v0, (t0)` | OK |
| `vcompress.vm` + `vs1r.v v30, (t0)` | OK |
| `vcompress.vm` + `vs1r.v v31, (t0)` (the vd) | **hangs** |
| `vcompress.vm` + `vse16.v v31, (t0)` (the vd) | **hangs** |
| `vadd.vv` + 32× `vs1r.v` (incl. its vd) | OK |

So the wedge requires a vector store whose *source* is the register just written by
`vcompress` (same shape for the other families above). A plausible mechanism is state left
in the operand queue for the `vd` operand (`use_vd_op` path — `vcompress` and the other
affected instructions read-modify-write or forward `vd` through the opqueues), which the
store's operand-fetch then waits on forever.

## Minimal reproducer

```asm
# vcompress.vm then ONE vs1r.v of its destination register -> hangs forever
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
    li t1, 1
    vsetvli zero, t1, e16, m1     # vtype = 0x8: e16, m1
    csrw vstart, zero             # vstart = 0 (hang does not need vstart != 0)
    vcompress.vm v31, v0, v0      # retires normally
    la t0, vbuf
    vs1r.v v31, (t0)              # <-- never completes; sim runs to cycle cap
    li a0, 0
    j _exit

    .align 2
test_trap:
    csrr a0, mcause
    li t0, 2
    beq a0, t0, 1f
    li a0, 8
    j _exit
1:  li a0, 2
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

.section .data
vbuf:
    .space 8192
.section .stack
.align 4
.space 4096
_stack_top:
```

Build and run (bare-metal ELF linked at 0x80000000):

```sh
riscv64-unknown-elf-gcc -march=rv64gcv -mabi=lp64d -nostdlib -static \
  -T ara.ld -o vcompress_store_hang.elf vcompress_store_hang.S
# note: -c must come before -l (the emu's argv handling permutes otherwise)
./hardware/build/verilator/Vara_tb_verilator -c 2000000 -l ram,vcompress_store_hang.elf,elf
```

## Expected behavior

The `vs1r.v v31` store retires, the program writes the exit value to the CTRL register
(0xD0000000), and the simulation terminates within a few thousand cycles (a store of `v0`
or `v30` instead of `v31`, or dropping the store entirely, terminates at ~190 cycles).

## Actual behavior

No store completion, no exit write; the simulation runs until the cycle limit:

```
Simulation timeout of 1e8480 cycles reached, shutting down simulation.
```

Reproduced with `-c 2000000` and `-c 20000000`; also reproduced with `vse16.v v31` instead
of `vs1r.v v31`, and with masked `vslideup.vi v8, v0, 0, v0.t` (e8/m8) followed by the
32-register export.

## Environment

- Ara commit: `34bd3bc1` (main at time of report)
- Config: `config=2_lanes` (VLEN=2048, NrLanes=2), Verilator emu
  (`hardware/build/verilator/Vara_tb_verilator`)
- Also observed on a `vlen=128` 2_lanes build (167 differential cases)
