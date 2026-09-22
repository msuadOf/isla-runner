# B6 probe: write vxrm=2 via csrrw (csrw), read back. Expect exit=2, suspect exit=0.
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
    li t1, 4
    vsetvli zero, t1, e32, m1   # establish a valid vtype
    li t0, 2
    csrw vxrm, t0               # 0x00a29073
    csrr a0, vxrm               # read back
    andi a0, a0, 0xff
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
