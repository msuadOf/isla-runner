import sys, subprocess, os
CASEDIR='/home/baiyifan/workplace-local/isla-runner/ara/work-diff/elf-check-emu'
def build(case, probe_asm, out, drop_test=False):
    src=open(f'{CASEDIR}/{case}/program.S').read()
    head, rest = src.split('after_test:', 1)
    tail = '.section .data' + rest.split('.section .data', 1)[1]
    if drop_test:
        # remove last .4byte (test instr) line from head
        lines=head.rstrip().split('\n')
        assert '.4byte' in lines[-1], lines[-3:]
        lines=lines[:-1]
        head='\n'.join(lines)+'\n'
    epilogue = "after_test:\n" + probe_asm + """
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
    open(out+'.S','w').write(head+epilogue+tail)
    subprocess.run(['riscv64-unknown-elf-gcc','-nostdlib','-nostartfiles','-march=rv64gcv_zfh_zvfh',
                    '-Wl,-Ttext=0x80000000','-x','assembler','-o',out+'.elf',out+'.S'],check=True)
def run(elf):
    import subprocess as sp
    try:
        r=sp.run(['/home/baiyifan/workplace-local/isla-runner/ara/ara/hardware/build-v128/verilator/Vara_tb_verilator',
            '-c','500000','-l','ram,'+elf+',elf'],capture_output=True,text=True,timeout=60)
        return r.returncode & 0xff
    except sp.TimeoutExpired:
        return 'HANG'
if __name__=='__main__':
    case, probef, out, mode = sys.argv[1], sys.argv[2], sys.argv[3], (sys.argv[4] if len(sys.argv)>4 else 'run')
    probe=open(probef).read()
    build(case, probe, out, drop_test=(mode=='droptest'))
    print('EXIT', run(os.path.abspath(out+'.elf')))
