.option norvc
.section .text.init
.align 4
.globl _start
_start:
    la t0, init_trap
    csrw mtvec, t0
    li t0, 0x6600
    .4byte 0x3002a073
    li t1, 16
    .4byte 0x01b37057
    li t0, 0
    .4byte 0x00829073
    la t0, test_trap
    csrw mtvec, t0
    la sp, _stack_top
    .4byte 0xa9813457 # vssrl.vi v8, v24, 0x2, v0.t
    .4byte 0x008022f3 # csrr t0, vstart
    mv a0, t0
    j _exit
    .align 2
test_trap:
    li a0, 99
    j _exit
    .align 2
init_trap:
    li a0, 98
    j _exit
    .align 2
_exit:
    li t0, 0xD0000000
    sd a0, 0(t0)
    nop
    nop
    nop
    nop
1:  j 1b
.section .stack
.align 4
.space 4096
_stack_top:
