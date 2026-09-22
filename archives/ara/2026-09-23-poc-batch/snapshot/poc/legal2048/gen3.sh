#!/bin/bash
# vfmv.v.f characterization probes (prefill vd = -1)
set -e
cd /tmp/legal2048

# body/tail probe for a given SEW string and byte offset; $1=file $2=sew $3=off $4=comment
gen_vfmv() {
cat > $1 <<EOF
# $4
.option norvc
.section .text.init
.align 4
.globl _start
_start:
    la t0, init_trap
    csrw mtvec, t0
    li t0, 0x6600
    csrs mstatus, t0
    la t0, test_trap
    csrw mtvec, t0
    la sp, _stack_top
    la t0, fbuf
    fld f0, 0(t0)                 # f0 = 0xA5A5A5A5A5A5A5A5
    li t1, 256
    vsetvli zero, t1, $2, m1      # vl = VLMAX
    vmv.v.i v2, -1                # v2 = all ones
    li t1, 2
    vsetvli zero, t1, $2, m1, tu, mu  # vl=2, vta=0
    vfmv.v.f v2, f0               # body elems 0,1 must be 0xA5..A5; tail must stay 0xFF..FF
    la t0, vbuf
    vs1r.v v2, (t0)
    lbu a0, $3
    j _exit

    .align 2
test_trap:
    csrr a0, mepc
    la t0, _start
    sub a0, a0, t0
    andi a0, a0, 0xff             # faulting insn offset
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
    .space 8192
fbuf:
    .quad 0xA5A5A5A5A5A5A5A5

.section .stack
.align 4
.space 4096
_stack_top:
EOF
}

# e32: body byte0 (correct 0xA5; vd-unchanged 0xFF; writes-0 0x00)
gen_vfmv v32_body.S e32 "0(t0)" "vfmv e32 body byte0: correct=0xA5(165); vd-unchanged=0xFF(255); zero=0"
# e32: tail byte at offset 12 (element 3, tail): correct 0xFF (tu); writes-1 bug=0x01
gen_vfmv v32_tail12.S e32 "12(t0)" "vfmv e32 tail byte12 (element3>=vl): correct=0xFF(255, tu-preserved); tail-agnostic-1s=0x01"
# e64: body byte0
gen_vfmv v64_body.S e64 "0(t0)" "vfmv e64 body byte0: correct=0xA5(165); vd-unchanged=0xFF; zero=0"
# e64: tail byte at offset 16 (element 2, tail)
gen_vfmv v64_tail16.S e64 "16(t0)" "vfmv e64 tail byte16 (element2>=vl): correct=0xFF(255); tail-1s=0x01"
# e16: body byte0
gen_vfmv v16_body.S e16 "0(t0)" "vfmv e16 body byte0: correct=0xA5; vd-unchanged=0xFF; zero=0"
# e8 (known trap): repeat with prefill to confirm trap offset
gen_vfmv v8_body.S e8 "0(t0)" "vfmv e8 body byte0: traps illegal on Ara (expect mepc offset ~0x4c)"

LD=/home/baiyifan/workplace-local/isla-runner/ara/work-all/elf/ara.ld
for s in v32_body v32_tail12 v64_body v64_tail16 v16_body v8_body; do
  riscv64-unknown-elf-gcc -march=rv64gcv -mabi=lp64d -nostdlib -static -T "$LD" -o $s.elf $s.S 2>/dev/null
done
echo built
