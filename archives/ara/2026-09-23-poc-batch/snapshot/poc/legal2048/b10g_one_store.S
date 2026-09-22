# B10 minimal repro: clone of work-diff case-00292 on a clean skeleton.
# vcompress.vm v31, v0, v0 @ e16,m1, vl=1, vstart=0, then 32x vs1r.v export.
# Expect (spec): retires and exits normally. Observed on v128 emu: hang. Verify on legal 2048.
.option norvc
.section .text.init
.align 4
.globl _start
_start:
    la t0, init_trap
    csrw mtvec, t0
    li t0, 0x6600
    csrs mstatus, t0
    la t0, test_trap
    csrw mtvec, t0
    la sp, _stack_top
    li t1, 1
    vsetvli zero, t1, e16, m1     # vtype = 0x8: e16, m1
    csrw vstart, zero             # vstart = 0
    vcompress.vm v31, v0, v0      # 0x5e21afd7: vd=v31, vs2=v0, mask=v0
    la t0, vbuf
    la t0, vbuf
    vs1r.v v31, (t0)
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
    li t0, 0xD0000000
    sd a0, 0(t0)
1:  j 1b

.section .data
vbuf:
    .space 8192
.section .stack
.align 4
.space 4096
_stack_top:
