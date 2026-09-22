# Functional check: vnclip.wi v20, v30, 0 with SEW=32/LMUL=1 (source 64 -> dest 32)
# v30 elem0 = 0x00001FFFFFFFFFFF (2^53-1, positive). vnclip shift 0:
#   spec (saturating clip) -> 0x7FFFFFFF, vxsat[0]=1
#   plain truncation        -> 0xFFFFFFFF
# exit 2 = correct saturation; 7 = truncation (bug); 6 = other mismatch; 4 = illegal trap
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
    li t0, 0x00001FFFFFFFFFFF
    .4byte 0x5e02cf57  # vmv.v.x v30, t0
    nop
    .4byte 0xbfe03a57  # vnclip.wi v20, v30, 0
    .4byte 0x434022d7  # vmv.x.s t0, v20
    li t1, 0x7FFFFFFF
    beq t0, t1, .Lpass
    li t1, -1
    beq t0, t1, .Ltrunc
    mv a0, t0
    j _exit
.Ltrunc:
mv a0, t0
    j _exit
.Lpass:
    csrr t1, 0x9       # vxsat
    andi t1, t1, 1
    beq t1, zero, .Ltrunc
    li a0, 2           # pass: correct clip + vxsat set
    j _exit

    .align 2
test_trap:
    csrr a0, mcause
    li t0, 2
    beq a0, t0, .Lill
    li a0, 10
    j _exit
.Lill:
    li a0, 4
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
