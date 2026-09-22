 .option norvc
.section .text.init
.align 4
.globl _start
_start:
    la t0, init_trap
    csrw mtvec, t0
    li t0, 0x6600
    csrs mstatus, t0
    li t1, 4
    .4byte 0x01037057
    la t0, test_trap
    csrw mtvec, t0
    csrr t0, vl
    li a0, 0
    j _exit
    .align 2
test_trap:
    csrr a0, mcause
    li t0, 2
    beq a0, t0, 1f
    li a0, 8
    j _exit
1:  li a0, 6
    j _exit
    .align 2
init_trap:
    li a0, 32
    j _exit
    .align 2
_exit:
    la t0, tohost
    slli a1, a0, 1
    ori a1, a1, 1
    sd a1, 0(t0)
1:  j 1b
.section .tohost
.align 3
tohost: .dword 0
fromhost: .dword 0
