# b7 diag A: drop fld+vfmv; expect exit 0x00 (body byte of vmv 0). If this traps, culprit is vsetvli/vmv.
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
    li t1, 256
    vsetvli zero, t1, e8, m1
    vmv.v.i v2, 0
    li t1, 2
    vsetvli zero, t1, e8, m1, tu, mu
    la t0, vbuf
    vs1r.v v2, (t0)
    lbu a0, 0(t0)
    j _exit
    j _exit

    .align 2
test_trap:
    csrr a0, mepc
    la t0, _start
    sub a0, a0, t0
    andi a0, a0, 0xff           # faulting insn offset (see disassembly)
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
