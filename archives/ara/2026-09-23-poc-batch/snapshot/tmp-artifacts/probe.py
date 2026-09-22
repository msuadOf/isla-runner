import sys, subprocess, struct, os, re
CASEDIR='/home/baiyifan/workplace-local/isla-runner/ara/work-diff/elf-check-emu'
EMU='/home/baiyifan/workplace-local/isla-runner/ara/ara/hardware/build-v128/verilator/Vara_tb_verilator'
LD='/home/baiyifan/workplace-local/isla-runner/ara/work-diff/elf-check-emu/ara.ld'
EPILOGUE_TMPL="""
after_test:
{CODE}
    .align 2
test_trap:
    csrr a0, mcause
    li t0, 99
    j _exit
    .align 2
init_trap:
    li a0, 98
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
"""
def build(case, code, tag):
    src=open(f'{CASEDIR}/{case}/program.S').read()
    head, rest = src.split('after_test:', 1)
    tail = '.section .data' + rest.split('.section .data', 1)[1]
    out=f'/tmp/probe/pb-{tag}.S'
    open(out,'w').write(head + EPILOGUE_TMPL.replace('{CODE}', code) + tail)
    subprocess.run(['riscv64-unknown-elf-gcc','-nostdlib','-nostartfiles','-march=rv64gcv_zfh_zvfh',
        '-T',LD,'-o',out+'.elf',out],check=True,capture_output=True)
    return out+'.elf'
def run(elf, dump=False, timeout=90, cycles='2000000'):
    cwd='/tmp/probe/prun'; os.makedirs(cwd+'/x',exist_ok=True)
    res=cwd+'/gold_results.txt'
    if os.path.exists(res): os.remove(res)
    try:
        r=subprocess.run([EMU,'-c',cycles,'-l','ram,'+elf+',elf'],cwd=cwd+'/x',capture_output=True,text=True,timeout=timeout)
        rc=r.returncode&0xff
    except subprocess.TimeoutExpired:
        return ('HANG',None)
    vregs=None
    if os.path.exists(res):
        by=bytes(int(l,16) for l in open(res) if l.strip())
        vregs=list(struct.unpack('<%dQ'%(len(by)//8),by))
    return (rc,vregs)
def csr_probe(case, csr_hex, tag):
    code=f"    .4byte 0x{csr_hex}02373 # csrr t1\n    andi a0, t1, 0xff\n    j _exit"
    return run(build(case, code, tag))
VSDUMP="    li t0, 0xD0000000\n    li t1, 1\n    sd t1, 32(t0)\n    la t1, sig_region\n"
for r in range(32):
    VSDUMP += f"    .4byte 0x{0x02830027 + r*0x80:08x} # vs1r.v v{r}, (t1)\n    addi t1, t1, 16\n"
VSDUMP += "    li a0, 0x77\n    j _exit"
def vreg_probe(case, tag):
    return run(build(case, VSDUMP, tag))
