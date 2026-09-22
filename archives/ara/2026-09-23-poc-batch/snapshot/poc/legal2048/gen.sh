#!/bin/bash
# Generate minimal test cases for legal-config (2 lanes, VLEN=2048) re-verification
set -e
cd /tmp/legal2048

skeleton_head() {  # $1 = comment
cat <<EOF
# $1
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
EOF
}

skeleton_tail() {
cat <<'EOF'
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
EOF
}

# ---------- B6: csrw vxrm,2 -> csrr vxrm (expect 2, suspect 0) ----------
{ skeleton_head "B6 probe: write vxrm=2 via csrrw (csrw), read back. Expect exit=2, suspect exit=0."
cat <<'EOF'
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
EOF
skeleton_tail; } > b6_vxrm.S

# ---------- B6: csrw vxsat,1 -> csrr vxsat (expect 1, suspect 0) ----------
{ skeleton_head "B6 probe: write vxsat=1 via csrrw (csrw), read back. Expect exit=1, suspect exit=0."
cat <<'EOF'
    la t0, test_trap
    csrw mtvec, t0
    la sp, _stack_top
    li t1, 4
    vsetvli zero, t1, e32, m1   # establish a valid vtype
    li t0, 1
    csrw vxsat, t0              # 0x00929073
    csrr a0, vxsat              # read back
    andi a0, a0, 0xff
    j _exit
EOF
skeleton_tail; } > b6_vxsat.S

# ---------- B8a: vsetivli uimm5=31 > VLMAX=4 (e64,mf8) (expect 4, suspect 31) ----------
{ skeleton_head "B8a probe: vsetivli x0, 31, e64, mf8. VLMAX = 2048/64/8 = 4, so vl must clamp to 4. Suspect exit=31 (unclamped uimm5)."
cat <<'EOF'
    la t0, test_trap
    csrw mtvec, t0
    la sp, _stack_top
    vsetivli zero, 31, e64, mf8 # 0xc1dff057, VLMAX=4
    csrr a0, vl
    andi a0, a0, 0xff
    j _exit
EOF
skeleton_tail; } > b8a_vsetivli.S

# ---------- B8b probe 1: vsetvli x0, x0 (rs1=x0, rd=x0) -> vl unchanged (expect 9) ----------
{ skeleton_head "B8b probe 1: prev vl=9; vsetvli x0, x0, e32, m1 (rs1=x0 AND rd=x0) must KEEP vl=9. Spec exit=9; swapped-table suspect would give VLMAX=64."
cat <<'EOF'
    la t0, test_trap
    csrw mtvec, t0
    la sp, _stack_top
    li t1, 9
    vsetvli zero, t1, e32, m1   # vl = 9 (VLMAX=64)
    vsetvli zero, zero, e32, m1 # 0x01007057 rs1=x0, rd=x0 -> vl unchanged
    csrr a0, vl
    andi a0, a0, 0xff
    j _exit
EOF
skeleton_tail; } > b8b_keep.S

# ---------- B8b probe 2: vsetvli x31, x0 (rs1=x0, rd!=x0) -> vl=VLMAX (expect 64) ----------
{ skeleton_head "B8b probe 2: prev vl=9; vsetvli x31, x0, e32, m1 (rs1=x0, rd!=x0) must set vl=VLMAX=64. Spec exit=64; swapped-table suspect would give 9."
cat <<'EOF'
    la t0, test_trap
    csrw mtvec, t0
    la sp, _stack_top
    li t1, 9
    vsetvli zero, t1, e32, m1   # vl = 9 (VLMAX=64)
    vsetvli x31, zero, e32, m1  # 0x0d007fd7 rs1=x0, rd!=x0 -> vl=VLMAX
    csrr a0, vl
    andi a0, a0, 0xff
    j _exit
EOF
skeleton_tail; } > b8b_vlmax.S

# ---------- B9: vid.v e32,m2 vl=128; second register (v5) of group ----------
# expected: v5 word0 = element64 = 0x00000040 -> byte3=0x00
# suspect (byte-packed): v5 bytes 0..3 = 0x40,0x41,0x42,0x43 -> byte3=0x43
{ skeleton_head "B9 probe a: vid.v v4 (e32,m2,vl=128); read byte3 of v5 word0. Correct=0x00 (element 64 = 0x40 fits in byte0); byte-packed bug would give 0x43."
cat <<'EOF'
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
EOF
skeleton_tail; } > b9_vid_byte3.S

{ skeleton_head "B9 probe b: same setup; read low byte of v5 word at byte offset 4. Correct=0x41 (element 65); byte-packed bug would give 0x44 (element 68 packed at byte 4)."
cat <<'EOF'
    la t0, test_trap
    csrw mtvec, t0
    la sp, _stack_top
    li t1, 128
    vsetvli zero, t1, e32, m2   # vl=128 = VLMAX, group v4-v5
    vmv.v.i v4, 0
    vid.v v4
    la t0, vbuf
    vs1r.v v5, (t0)
    lw t1, 4(t0)
    andi a0, t1, 0xff           # byte4 = element 65
    j _exit
EOF
skeleton_tail; } > b9_vid_word4.S

{ skeleton_head "B9 probe c (sanity): same setup but read v4 (FIRST register of group), low byte of word at offset 4. Correct=0x01 (element 1) - first register is known-good."
cat <<'EOF'
    la t0, test_trap
    csrw mtvec, t0
    la sp, _stack_top
    li t1, 128
    vsetvli zero, t1, e32, m2   # vl=128 = VLMAX, group v4-v5
    vmv.v.i v4, 0
    vid.v v4
    la t0, vbuf
    vs1r.v v4, (t0)
    lw t1, 4(t0)
    andi a0, t1, 0xff           # byte4 = element 1
    j _exit
EOF
skeleton_tail; } > b9_vid_v4_sanity.S

# ---------- B7 sub-item: vfmv.v.f with vta=0 (tu), tail must be preserved ----------
{ skeleton_head "B7 probe (body sanity): e8,m1; zero v2 (vl=256); vl=2, vta=0; vfmv.v.f v2, f0 (0xA5..A5); read body byte0. Expect exit=0xA5 (165)."
cat <<'EOF'
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
    lbu a0, 0(t0)               # body byte 0
    j _exit
EOF
skeleton_tail; } > b7_vfmv_body.S

{ skeleton_head "B7 probe (tail): same setup; read TAIL byte 4 (>= vl=2, tu). Spec: tail-undisturbed -> keep 0x00 (exit=0). Bug would write 1s -> exit=0xFF (255)."
cat <<'EOF'
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
EOF
skeleton_tail; } > b7_vfmv_tail.S

# ---------- A3 extra: vcompress.vm with vstart!=0 must raise illegal ----------
{ skeleton_head "A3 probe: csrw vstart=1 then vcompress.vm v1, v2, v3 (e32,m1,vl=4). RVV 1.0 MANDATES illegal-instruction when vstart!=0. Spec exit=2 (trap); Ara bug: retires -> exit=0."
cat <<'EOF'
    la t0, test_trap
    csrw mtvec, t0
    la sp, _stack_top
    li t1, 4
    vsetvli zero, t1, e32, m1   # vl=4
    vmv.v.i v2, 1
    vmv.v.i v3, 3
    li t0, 1
    csrw vstart, t0             # 0x00829073, vstart=1 != 0
    vcompress.vm v1, v2, v3     # 0x5e21a0d7
    li a0, 0                    # reached => instruction retired, no trap
    j _exit
EOF
skeleton_tail; } > a3_vcompress.S

# ---------- A1 extra: vnclip.wi with SEW=64 must raise illegal ----------
{ skeleton_head "A1 probe: vsetvli e64,m1 (zimm=0x18) then vnclip.wi v10, v8, 11. Source EEW=2*SEW=128 > ELEN=64 -> MUST be illegal (exit=2). Ara bug: simd_alu unique-case assertion kills the sim."
cat <<'EOF'
    la t0, test_trap
    csrw mtvec, t0
    la sp, _stack_top
    li t1, 4
    vsetvli zero, t1, e64, m1   # zimm = 0x18: SEW=64
    vmv.v.i v8, 1
    vmv.v.i v4, 1
    vnclip.wi v10, v8, 11       # narrowing, source EEW = 128
    li a0, 0                    # reached => retired (no trap)
    j _exit
EOF
skeleton_tail; } > a1_vnclip.S

# ---------- B10: vstart=4 + vadd.vv (retires) + 32x vs1r.v export ----------
gen_b10() { # $1=file $2=vstart_val $3=comment
{ skeleton_head "$3"
cat <<EOF
    la t0, test_trap
    csrw mtvec, t0
    la sp, _stack_top
    li t1, 8
    vsetvli zero, t1, e64, m1   # vl=8 (VLMAX=32)
    vmv.v.i v2, 1
    vmv.v.i v3, 2
    li t0, $2
    csrw vstart, t0             # 0x00829073, vstart=$2
    vadd.vv v1, v2, v3          # 0x022180d7, retires (elements 4..7 if vstart=4)
    la t0, vbuf
.irp V, 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31
    vs1r.v v\V, (t0)
    addi t0, t0, 256
.endr
    li a0, 0                    # reached => whole export sequence completed
    j _exit
EOF
skeleton_tail; } > $1
}
gen_b10 b10_hang.S 4 "B10 probe: vstart=4, vadd.vv v1,v2,v3 (retires), then 32x vs1r.v export. Control is b10_ctl.S (vstart=0). Suspect: never writes exit (hang)."
gen_b10 b10_ctl.S  0 "B10 control: identical to b10_hang.S but vstart=0. Must exit 0 quickly."

echo "generated:"; ls -1 /tmp/legal2048/*.S
