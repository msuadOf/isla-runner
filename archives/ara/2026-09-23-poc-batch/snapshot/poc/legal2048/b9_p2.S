# b9 probe p2: vid.v e32,m2; v5 BYTE64. Correct=0x50 (element 80). 0 => untouched.
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
    li t1, 128
    vsetvli zero, t1, e32, m2
    vmv.v.i v4, 0
    vid.v v4
    la t0, vbuf
    vs1r.v v5, (t0)
    lbu a0, 64(t0)
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
