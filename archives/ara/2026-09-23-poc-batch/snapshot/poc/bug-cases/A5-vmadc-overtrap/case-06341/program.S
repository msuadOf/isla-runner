# Isla -> Ara PoC: vmadc.vi v0, v0, -0x3
# encoding: 0x460eb057, ret_val: Retire_Success, clause: VIMCTYPE
.option norvc
.section .text.init
.align 4
.globl _start
_start:
    la t0, init_trap
    csrw mtvec, t0
    la t0, after_test
    csrw mepc, t0
    li t0, 0x6600
    .4byte 0x3002a073 # csrs mstatus, t0 (VS|FS Dirty)
    li t1, 3
    .4byte 0x01237057 # vsetvli zero, t1, 0x12
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
    li t0, 1
    .4byte 0x00829073 # csrw vstart, t0
    li t0, 0
    .4byte 0x00a29073 # csrw vxrm, t0
    li t0, 0
    .4byte 0x00929073 # csrw vxsat, t0
    la t0, test_trap
    csrw mtvec, t0
    la sp, _stack_top
    .4byte 0x460eb057 # vmadc.vi v0, v0, -0x3
after_test:
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

.section .data
.align 3
vector_initial_state:
    .dword 0xffffeffc00000000
    .dword 0x00000000bfffff01
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

.section .tohost
.align 3
.globl tohost
tohost: .dword 0
.globl fromhost
fromhost: .dword 0

.section .stack
.align 4
.space 4096
_stack_top:
