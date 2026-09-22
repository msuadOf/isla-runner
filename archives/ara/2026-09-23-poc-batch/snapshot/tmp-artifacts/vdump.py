import sys, subprocess, struct, os, re
CASEDIR='/home/baiyifan/workplace-local/isla-runner/ara/work-diff/elf-check-emu'
EMU='/home/baiyifan/workplace-local/isla-runner/ara/ara/hardware/build-v128/verilator/Vara_tb_verilator'
LD='/home/baiyifan/workplace-local/isla-runner/ara/work-diff/elf-check-emu/ara.ld'
def build(case, tag='vd'):
    src=open(f'{CASEDIR}/{case}/program.S').read()
    head, rest = src.split('after_test:', 1)
    n0=len(head)
    # 等长替换: vstart 复位对 -> 加载 0xD0000000; vxsat 复位对 -> 置 hw_cnt_en
    head2=re.sub(r'li t0, 0\n(\s+)\.4byte 0x00829073[^\n]*',
                 r'li t0, 0xD0000000\n\1# ena dump', head, count=1)
    head2=re.sub(r'li t0, 0\n(\s+)\.4byte 0x00929073[^\n]*',
                 r'li t1, 1\n\1sd t1, 32(t0)', head2, count=1)
    assert head2!=head, 'pattern not found'
    # 代码长度需一致: 检查汇编后 .text 大小
    out=f'/tmp/probe/vd-{case}-{tag}.S'
    open(out,'w').write(head2+rest)
    subprocess.run(['riscv64-unknown-elf-gcc','-nostdlib','-nostartfiles','-march=rv64gcv_zfh_zvfh',
        '-T',LD,'-o',out+'.elf',out],check=True,capture_output=True)
    return out+'.elf'
def run(case, tag='vd'):
    elf=build(case,tag)
    cwd=f'/tmp/probe/vrun'; os.makedirs(cwd+'/x',exist_ok=True)
    res=cwd+'/gold_results.txt'
    if os.path.exists(res): os.remove(res)
    try:
        r=subprocess.run([EMU,'-c','2000000','-l','ram,'+elf+',elf'],cwd=cwd+'/x',capture_output=True,text=True,timeout=120)
        rc=r.returncode&0xff
    except subprocess.TimeoutExpired:
        return None,'HANG',None
    vregs=None
    if os.path.exists(res):
        by=bytes(int(l,16) for l in open(res) if l.strip())
        vregs=list(struct.unpack('<%dQ'%(len(by)//8),by))
    return vregs,rc,len(open(res).read().split()) if os.path.exists(res) else 0
if __name__=='__main__':
    for case in sys.argv[1:]:
        v,rc,n=run(case)
        print('==',case,'check_rc=',rc,'dumpbytes=',n*1)
        if v:
            for i in range(min(6,len(v)//2)):
                print('   v%d = %016x %016x'%(i,v[2*i],v[2*i+1]))
            print('   ... v31 = %016x %016x'%(v[62],v[63]) if len(v)>=64 else '')
