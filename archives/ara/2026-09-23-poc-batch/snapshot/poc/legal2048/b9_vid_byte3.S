# B9 probe a: vid.v v4 (e32,m2,vl=128); read byte3 of v5 word0. Correct=0x00 (element 64 = 0x40 fits in byte0); byte-packed bug would give 0x43.
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
    li t1, 128
    vsetvli zero, t1, e32, m2   # vl=128 = VLMAX, group v4-v5
    vmv.v.i v4, 0               # zero the whole group
    vid.v v4                    # 0x5208a257
    la t0, vbuf
    vs1r.v v5, (t0)             # 0x028282a7
    lw t1, 0(t0)
    srli a0, t1, 24             # byte3 of word0
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
