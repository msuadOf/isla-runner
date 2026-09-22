# B7 probe (tail): same setup; read TAIL byte 4 (>= vl=2, tu). Spec: tail-undisturbed -> keep 0x00 (exit=0). Bug would write 1s -> exit=0xFF (255).
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
    la t0, fbuf
    fld f0, 0(t0)               # f0 = 0xA5A5A5A5A5A5A5A5
    li t1, 256
    vsetvli zero, t1, e8, m1    # vl = VLMAX = 256
    vmv.v.i v2, 0               # v2 all zero
    li t1, 2
    vsetvli zero, t1, e8, m1, tu, mu  # vl=2, vta=0
    vfmv.v.f v2, f0             # 0x5e005157: body bytes 0,1 = 0xA5
    la t0, vbuf
    vs1r.v v2, (t0)
    lbu a0, 4(t0)               # tail byte 4
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
