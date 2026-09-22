# B10 control: identical to b10_hang.S but vstart=0. Must exit 0 quickly.
# Target: Ara commit 34bd3bc1, config=2_lanes (VLEN=2048, NrLanes=2), emu:
#   hardware/build/verilator/Vara_tb_verilator -c 2000000 -l ram,<elf>,elf
# Exit code = value written to 0xD0000000 (control reg), OS-masked to 8 bits.
#   0/2/8 from _exit path; 2 = illegal trap (mcause=2); 8 = other trap; 32 = init trap.
.option norvc
.section .text.init
.align 4
.globl _start
_start:
    la t0, init_trap
    csrw mtvec, t0
    li t0, 0x6600
    csrs mstatus, t0          # VS|FS Dirty
    la t0, test_trap
    csrw mtvec, t0
    la sp, _stack_top
    li t1, 8
    vsetvli zero, t1, e64, m1   # vl=8 (VLMAX=32)
    vmv.v.i v2, 1
    vmv.v.i v3, 2
    li t0, 0
    csrw vstart, t0             # 0x00829073, vstart=0
    vadd.vv v1, v2, v3          # 0x022180d7, retires (elements 4..7 if vstart=4)
    la t0, vbuf
.irp V, 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31
    vs1r.v v\V, (t0)
    addi t0, t0, 256
.endr
    li a0, 0                    # reached => whole export sequence completed
    j _exit
    .align 2
test_trap:
    csrr a0, mcause
    li t0, 2
    beq a0, t0, 1f
    li a0, 8                  # trapped with mcause != 2
    j _exit
1:  li a0, 2                  # trapped illegal-instruction (mcause=2)
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
    .space 8192               # vs1r.v landing buffer (32 regs x 256 B)
fbuf:
    .quad 0xA5A5A5A5A5A5A5A5

.section .stack
.align 4
.space 4096
_stack_top:
