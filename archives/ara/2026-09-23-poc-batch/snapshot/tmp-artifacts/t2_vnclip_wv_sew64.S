.option norvc
.section .text.init
.align 4
.globl _start
_start:
    la t0, init_trap
    csrw mtvec, t0
    li t0, 0x6600
    .4byte 0x3002a073
    li t1, 1
    .4byte 0x01837057
    li t0, 0
    .4byte 0x00829073
    li t0, 0
    .4byte 0x00a29073
    li t0, 0
    .4byte 0x00929073
    la t0, test_trap
    csrw mtvec, t0
    la sp, _stack_top
    
    .4byte 0xbfe20a57
    li a0, 2
    j _exit

    .align 2
test_trap:
    csrr a0, mcause
    li t0, 2
    beq a0, t0, 1f
    li a0, 10
    j _exit
1:  li a0, 4
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
    .dword 0

.section .stack
.align 4
.space 4096
_stack_top:
