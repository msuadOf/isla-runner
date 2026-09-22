#!/bin/bash
# Diagnostic probes: round 2
set -e
cd /tmp/legal2048

diag_head() {
cat <<EOF
# $1
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
EOF
}

# trap handler reports (mepc - _start) & 0xff = byte offset of faulting insn
mepc_tail() {
cat <<'EOF'
    j _exit

    .align 2
test_trap:
    csrr a0, mepc
    la t0, _start
    sub a0, a0, t0
    andi a0, a0, 0xff           # faulting insn offset (see disassembly)
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

# ---------- b7 diagnosis: which instruction traps? ----------
{ diag_head "b7 diag: identify faulting instruction via mepc offset. Sequence identical to b7_vfmv_body."
cat <<'EOF'
    la t0, fbuf
    fld f0, 0(t0)
    li t1, 256
    vsetvli zero, t1, e8, m1
    vmv.v.i v2, 0
    li t1, 2
    vsetvli zero, t1, e8, m1, tu, mu
    vfmv.v.f v2, f0
    la t0, vbuf
    vs1r.v v2, (t0)
    lbu a0, 0(t0)
    j _exit
EOF
mepc_tail; } > b7_diag.S

# ---------- b7 variant A: no fld / no vfmv (check vsetvli e8 + vmv path) ----------
{ diag_head "b7 diag A: drop fld+vfmv; expect exit 0x00 (body byte of vmv 0). If this traps, culprit is vsetvli/vmv."
cat <<'EOF'
    li t1, 256
    vsetvli zero, t1, e8, m1
    vmv.v.i v2, 0
    li t1, 2
    vsetvli zero, t1, e8, m1, tu, mu
    la t0, vbuf
    vs1r.v v2, (t0)
    lbu a0, 0(t0)
    j _exit
EOF
mepc_tail; } > b7_diagA.S

# ---------- b7 variant B: keep fld, replace vfmv.v.f with vmv.v.f? use vfmv at SEW=e32 ----------
{ diag_head "b7 diag B: vfmv.v.f at e32 instead of e8 (vl=2). body byte0 expect 0xA5. Checks whether e8 is the trigger."
cat <<'EOF'
    la t0, fbuf
    fld f0, 0(t0)
    li t1, 256
    vsetvli zero, t1, e32, m1
    vmv.v.i v2, 0
    li t1, 2
    vsetvli zero, t1, e32, m1, tu, mu
    vfmv.v.f v2, f0
    la t0, vbuf
    vs1r.v v2, (t0)
    lbu a0, 0(t0)               # expect 0xA5
    j _exit
EOF
mepc_tail; } > b7_diagB.S

# ---------- b9 extra: v5 byte0 (expect 0x40 if correct, 0 if untouched) ----------
{ diag_head "b9 probe p1: vid.v e32,m2; v5 BYTE0. Correct=0x40 (element 64). 0 => v5 untouched."
cat <<'EOF'
    li t1, 128
    vsetvli zero, t1, e32, m2
    vmv.v.i v4, 0
    vid.v v4
    la t0, vbuf
    vs1r.v v5, (t0)
    lbu a0, 0(t0)
    j _exit
EOF
mepc_tail; } > b9_p1.S

# ---------- b9 extra: v5 byte64 (expect 0x50=element 80 if correct, else 0) ----------
{ diag_head "b9 probe p2: vid.v e32,m2; v5 BYTE64. Correct=0x50 (element 80). 0 => untouched."
cat <<'EOF'
    li t1, 128
    vsetvli zero, t1, e32, m2
    vmv.v.i v4, 0
    vid.v v4
    la t0, vbuf
    vs1r.v v5, (t0)
    lbu a0, 64(t0)
    j _exit
EOF
mepc_tail; } > b9_p2.S

# ---------- b9 SEW64 variant: e64,m2 vl=64; v5 byte4 (elem32 is bytes 0..7) ----------
{ diag_head "b9 probe e64: vid.v e64,m2,vl=64; v5 BYTE4 = middle of element 32. Correct=0x00; byte-packed bug would give 0x24 (element 36)."
cat <<'EOF'
    li t1, 64
    vsetvli zero, t1, e64, m2
    vmv.v.i v4, 0
    vid.v v4
    la t0, vbuf
    vs1r.v v5, (t0)
    lbu a0, 4(t0)
    j _exit
EOF
mepc_tail; } > b9_e64.S

# ---------- b9 SEW64 variant: v5 byte0 (expect 0x20 = element 32) ----------
{ diag_head "b9 probe e64b: vid.v e64,m2,vl=64; v5 BYTE0. Correct=0x20 (element 32). 0 => untouched."
cat <<'EOF'
    li t1, 64
    vsetvli zero, t1, e64, m2
    vmv.v.i v4, 0
    vid.v v4
    la t0, vbuf
    vs1r.v v5, (t0)
    lbu a0, 0(t0)
    j _exit
EOF
mepc_tail; } > b9_e64b.S

LD=/home/baiyifan/workplace-local/isla-runner/ara/work-all/elf/ara.ld
for s in b7_diag b7_diagA b7_diagB b9_p1 b9_p2 b9_e64 b9_e64b; do
  riscv64-unknown-elf-gcc -march=rv64gcv -mabi=lp64d -nostdlib -static -T "$LD" -o $s.elf $s.S 2>/dev/null
done
echo built
