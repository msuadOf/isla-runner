# vfmv e32 body byte0: correct=0xA5(165); vd-unchanged=0xFF(255); zero=0
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
    la t0, fbuf
    fld f0, 0(t0)
    fmv.d f5, f0
    li t1, 256
    vsetvli zero, t1, e32, m1      # vl = VLMAX
    vmv.v.i v2, -1                # v2 = all ones
    li t1, 2
    vsetvli zero, t1, e32, m1, tu, mu  # vl=2, vta=0
    vfmv.v.f v2, f5               # body elems 0,1 must be 0xA5..A5; tail must stay 0xFF..FF
    la t0, vbuf
    vs1r.v v2, (t0)
    lbu a0, 0(t0)
    j _exit

    .align 2
test_trap:
    csrr a0, mepc
    la t0, _start
    sub a0, a0, t0
    andi a0, a0, 0xff             # faulting insn offset
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
fbuf:
    .quad 0xA5A5A5A5A5A5A5A5

.section .stack
.align 4
.space 4096
_stack_top:
