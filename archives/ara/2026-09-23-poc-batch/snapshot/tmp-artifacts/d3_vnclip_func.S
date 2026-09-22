# Functional check of vnclip.wi at SEW=32 (source 64 -> dest 32) via memory
# src elem0 = 0x00000000FFFFFFFF (positive 2^32-1), shift 0:
#   spec (saturating clip) -> 0x7FFFFFFF ; plain truncation -> 0xFFFFFFFF
# exit: value read back from dst (tohost)
.option norvc
.section .text.init
.align 4
.globl _start
_start:
    la t0, init_trap
    csrw mtvec, t0
    li t0, 0x6600
    .4byte 0x3002a073 # csrs mstatus, t0 (VS|FS Dirty)
    li t1, 1
    .4byte 0x01037057 # vsetvli zero, t1, 0x10 (SEW=32, LMUL=1, vl=1)
    li t0, 0
    .4byte 0x00829073 # csrw vstart, t0
    li t0, 0
    .4byte 0x00a29073 # csrw vxrm, t0 (rne)
    li t0, 0
    .4byte 0x00929073 # csrw vxsat, t0
    la t0, test_trap
    csrw mtvec, t0
    la sp, _stack_top

    la t1, src
    .4byte 0x02037f07  # vle64.v v30, (t1)
    nop
    .4byte 0xbfe03a57  # vnclip.wi v20, v30, 0
    nop
    la t1, dst
    .4byte 0x02036a27  # vse32.v v20, (t1)
    li t2, 200
1:  addi t2, t2, -1
    bnez t2, 1b
    ld t0, 0(t1)
    mv a0, t0
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
src: .dword 0x00000000FFFFFFFF
dst: .dword 0

.section .stack
.align 4
.space 4096
_stack_top:
