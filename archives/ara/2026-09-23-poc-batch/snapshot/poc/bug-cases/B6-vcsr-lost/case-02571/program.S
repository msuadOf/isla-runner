# Isla -> Ara PoC: vssrl.vi v8, v24, 0x2, v0.t (mode=check)
# encoding: 0xa9813457, ret_val: Retire_Success, clause: VITYPE
.option norvc
.section .text.init
.align 4
.globl _start
_start:
    li x1, 0
    li x2, 0
    li x3, 0
    li x4, 0
    li x5, 0
    li x6, 0
    li x7, 0
    li x8, 0
    li x9, 0
    li x10, 0
    li x11, 0
    li x12, 0
    li x13, 0
    li x14, 0
    li x15, 0
    li x16, 0
    li x17, 0
    li x18, 0
    li x19, 0
    li x20, 0
    li x21, 0
    li x22, 0
    li x23, 0
    li x24, 0
    li x25, 0
    li x26, 0
    li x27, 0
    li x28, 0
    li x29, 0
    li x30, 0
    li x31, 0
    la t0, init_trap
    csrw mtvec, t0
    la t0, after_test
    csrw mepc, t0
    li t0, 0x6600
    .4byte 0x3002a073 # csrs mstatus, t0 (VS|FS Dirty)
    li t1, 16
    .4byte 0x01b37057 # vsetvli zero, t1, 0x1b
    la t0, vector_initial_state
    .4byte 0x02828007 # vl1re8.v v0, (t0)
    addi t0, t0, 16
    .4byte 0x02828087 # vl1re8.v v1, (t0)
    addi t0, t0, 16
    .4byte 0x02828107 # vl1re8.v v2, (t0)
    addi t0, t0, 16
    .4byte 0x02828187 # vl1re8.v v3, (t0)
    addi t0, t0, 16
    .4byte 0x02828207 # vl1re8.v v4, (t0)
    addi t0, t0, 16
    .4byte 0x02828287 # vl1re8.v v5, (t0)
    addi t0, t0, 16
    .4byte 0x02828307 # vl1re8.v v6, (t0)
    addi t0, t0, 16
    .4byte 0x02828387 # vl1re8.v v7, (t0)
    addi t0, t0, 16
    .4byte 0x02828407 # vl1re8.v v8, (t0)
    addi t0, t0, 16
    .4byte 0x02828487 # vl1re8.v v9, (t0)
    addi t0, t0, 16
    .4byte 0x02828507 # vl1re8.v v10, (t0)
    addi t0, t0, 16
    .4byte 0x02828587 # vl1re8.v v11, (t0)
    addi t0, t0, 16
    .4byte 0x02828607 # vl1re8.v v12, (t0)
    addi t0, t0, 16
    .4byte 0x02828687 # vl1re8.v v13, (t0)
    addi t0, t0, 16
    .4byte 0x02828707 # vl1re8.v v14, (t0)
    addi t0, t0, 16
    .4byte 0x02828787 # vl1re8.v v15, (t0)
    addi t0, t0, 16
    .4byte 0x02828807 # vl1re8.v v16, (t0)
    addi t0, t0, 16
    .4byte 0x02828887 # vl1re8.v v17, (t0)
    addi t0, t0, 16
    .4byte 0x02828907 # vl1re8.v v18, (t0)
    addi t0, t0, 16
    .4byte 0x02828987 # vl1re8.v v19, (t0)
    addi t0, t0, 16
    .4byte 0x02828a07 # vl1re8.v v20, (t0)
    addi t0, t0, 16
    .4byte 0x02828a87 # vl1re8.v v21, (t0)
    addi t0, t0, 16
    .4byte 0x02828b07 # vl1re8.v v22, (t0)
    addi t0, t0, 16
    .4byte 0x02828b87 # vl1re8.v v23, (t0)
    addi t0, t0, 16
    .4byte 0x02828c07 # vl1re8.v v24, (t0)
    addi t0, t0, 16
    .4byte 0x02828c87 # vl1re8.v v25, (t0)
    addi t0, t0, 16
    .4byte 0x02828d07 # vl1re8.v v26, (t0)
    addi t0, t0, 16
    .4byte 0x02828d87 # vl1re8.v v27, (t0)
    addi t0, t0, 16
    .4byte 0x02828e07 # vl1re8.v v28, (t0)
    addi t0, t0, 16
    .4byte 0x02828e87 # vl1re8.v v29, (t0)
    addi t0, t0, 16
    .4byte 0x02828f07 # vl1re8.v v30, (t0)
    addi t0, t0, 16
    .4byte 0x02828f87 # vl1re8.v v31, (t0)
    addi t0, t0, 16
    li t0, 0
    .4byte 0x00829073 # csrw vstart, t0
    li t0, 1
    .4byte 0x00a29073 # csrw vxrm, t0
    li t0, 0
    .4byte 0x00929073 # csrw vxsat, t0
    la t0, test_trap
    csrw mtvec, t0
    la sp, _stack_top
    .4byte 0xa9813457 # vssrl.vi v8, v24, 0x2, v0.t
after_test:
    # signature dump
    la t6, sig_region
    sd t6, 240(t6)
    sd x1, 0(t6)
    addi t6, t6, 8
    sd x2, 0(t6)
    addi t6, t6, 8
    sd x3, 0(t6)
    addi t6, t6, 8
    sd x4, 0(t6)
    addi t6, t6, 8
    sd x5, 0(t6)
    addi t6, t6, 8
    sd x6, 0(t6)
    addi t6, t6, 8
    sd x7, 0(t6)
    addi t6, t6, 8
    sd x8, 0(t6)
    addi t6, t6, 8
    sd x9, 0(t6)
    addi t6, t6, 8
    sd x10, 0(t6)
    addi t6, t6, 8
    sd x11, 0(t6)
    addi t6, t6, 8
    sd x12, 0(t6)
    addi t6, t6, 8
    sd x13, 0(t6)
    addi t6, t6, 8
    sd x14, 0(t6)
    addi t6, t6, 8
    sd x15, 0(t6)
    addi t6, t6, 8
    sd x16, 0(t6)
    addi t6, t6, 8
    sd x17, 0(t6)
    addi t6, t6, 8
    sd x18, 0(t6)
    addi t6, t6, 8
    sd x19, 0(t6)
    addi t6, t6, 8
    sd x20, 0(t6)
    addi t6, t6, 8
    sd x21, 0(t6)
    addi t6, t6, 8
    sd x22, 0(t6)
    addi t6, t6, 8
    sd x23, 0(t6)
    addi t6, t6, 8
    sd x24, 0(t6)
    addi t6, t6, 8
    sd x25, 0(t6)
    addi t6, t6, 8
    sd x26, 0(t6)
    addi t6, t6, 8
    sd x27, 0(t6)
    addi t6, t6, 8
    sd x28, 0(t6)
    addi t6, t6, 8
    sd x29, 0(t6)
    addi t6, t6, 8
    sd x30, 0(t6)
    addi t6, t6, 8
    .4byte 0xc2002373 # csrr t1, vl
    sd t1, 0(t6)
    addi t6, t6, 8
    .4byte 0xc2102373 # csrr t1, vtype
    sd t1, 0(t6)
    addi t6, t6, 8
    .4byte 0x00802373 # csrr t1, vstart
    sd t1, 0(t6)
    addi t6, t6, 8
    .4byte 0x00f02373 # csrr t1, vcsr
    sd t1, 0(t6)
    addi t6, t6, 8
    mv t1, t6
    .4byte 0x02830027 # vs1r.v v0, (t1)
    addi t1, t1, 16
    .4byte 0x028300a7 # vs1r.v v1, (t1)
    addi t1, t1, 16
    .4byte 0x02830127 # vs1r.v v2, (t1)
    addi t1, t1, 16
    .4byte 0x028301a7 # vs1r.v v3, (t1)
    addi t1, t1, 16
    .4byte 0x02830227 # vs1r.v v4, (t1)
    addi t1, t1, 16
    .4byte 0x028302a7 # vs1r.v v5, (t1)
    addi t1, t1, 16
    .4byte 0x02830327 # vs1r.v v6, (t1)
    addi t1, t1, 16
    .4byte 0x028303a7 # vs1r.v v7, (t1)
    addi t1, t1, 16
    .4byte 0x02830427 # vs1r.v v8, (t1)
    addi t1, t1, 16
    .4byte 0x028304a7 # vs1r.v v9, (t1)
    addi t1, t1, 16
    .4byte 0x02830527 # vs1r.v v10, (t1)
    addi t1, t1, 16
    .4byte 0x028305a7 # vs1r.v v11, (t1)
    addi t1, t1, 16
    .4byte 0x02830627 # vs1r.v v12, (t1)
    addi t1, t1, 16
    .4byte 0x028306a7 # vs1r.v v13, (t1)
    addi t1, t1, 16
    .4byte 0x02830727 # vs1r.v v14, (t1)
    addi t1, t1, 16
    .4byte 0x028307a7 # vs1r.v v15, (t1)
    addi t1, t1, 16
    .4byte 0x02830827 # vs1r.v v16, (t1)
    addi t1, t1, 16
    .4byte 0x028308a7 # vs1r.v v17, (t1)
    addi t1, t1, 16
    .4byte 0x02830927 # vs1r.v v18, (t1)
    addi t1, t1, 16
    .4byte 0x028309a7 # vs1r.v v19, (t1)
    addi t1, t1, 16
    .4byte 0x02830a27 # vs1r.v v20, (t1)
    addi t1, t1, 16
    .4byte 0x02830aa7 # vs1r.v v21, (t1)
    addi t1, t1, 16
    .4byte 0x02830b27 # vs1r.v v22, (t1)
    addi t1, t1, 16
    .4byte 0x02830ba7 # vs1r.v v23, (t1)
    addi t1, t1, 16
    .4byte 0x02830c27 # vs1r.v v24, (t1)
    addi t1, t1, 16
    .4byte 0x02830ca7 # vs1r.v v25, (t1)
    addi t1, t1, 16
    .4byte 0x02830d27 # vs1r.v v26, (t1)
    addi t1, t1, 16
    .4byte 0x02830da7 # vs1r.v v27, (t1)
    addi t1, t1, 16
    .4byte 0x02830e27 # vs1r.v v28, (t1)
    addi t1, t1, 16
    .4byte 0x02830ea7 # vs1r.v v29, (t1)
    addi t1, t1, 16
    .4byte 0x02830f27 # vs1r.v v30, (t1)
    addi t1, t1, 16
    .4byte 0x02830fa7 # vs1r.v v31, (t1)
    addi t1, t1, 16
sig_done:
    # compare signature against golden
    la t0, sig_region
    la t1, golden_signature
    li t2, 99
    li a0, 0
1:  ld t3, 0(t0)
    ld t4, 0(t1)
    bne t3, t4, 2f
    addi t0, t0, 8
    addi t1, t1, 8
    addi t2, t2, -1
    bnez t2, 1b
    j _exit
2:  la t5, sig_region
    sub a0, t0, t5
    srli a0, a0, 3
    addi a0, a0, 1
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
    li t0, 0xD0000000
    sd a0, 0(t0)
    nop
    nop
    nop
    nop
1:  j 1b

.section .data
.align 3
vector_initial_state:
    .dword 0x0000000000000001
    .dword 0x0000000000000001
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000003
    .dword 0x0000000000000000
    .dword 0x0000000000000006
    .dword 0x0000000000000000
    .dword 0x0000000000000002
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000003
    .dword 0x0000000000000000
    .dword 0x0000000000000006
    .dword 0x0000000000000003
    .dword 0x0000000000000000
    .dword 0x0000000000000003
    .dword 0x0000000000000000
    .dword 0x0000000000000002
    .dword 0x0000000000000000

.align 3
sig_region:
    .space 792
.align 3
golden_signature:
    .dword 0x0000000000000000
    .dword 0x0000000080001ce0
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000080000460
    .dword 0x0000000000000010
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000010
    .dword 0x000000000000001b
    .dword 0x0000000000000000
    .dword 0x0000000000000002
    .dword 0x0000000000000001
    .dword 0x0000000000000001
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000001
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000003
    .dword 0x0000000000000000
    .dword 0x0000000000000006
    .dword 0x0000000000000000
    .dword 0x0000000000000002
    .dword 0x0000000000000000
    .dword 0x0000000000000000
    .dword 0x0000000000000003
    .dword 0x0000000000000000
    .dword 0x0000000000000006
    .dword 0x0000000000000003
    .dword 0x0000000000000000
    .dword 0x0000000000000003
    .dword 0x0000000000000000
    .dword 0x0000000000000002
    .dword 0x0000000000000000
    .dword 0x0000000000000000

.section .stack
.align 4
.space 4096
_stack_top:

.section .tohost
.align 3
.globl tohost
tohost: .dword 0
.globl fromhost
fromhost: .dword 0
