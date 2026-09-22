import sys, subprocess, struct, os
CASEDIR='/home/baiyifan/workplace-local/isla-runner/ara/work-diff/elf-check-emu'
EMU='/home/baiyifan/workplace-local/isla-runner/ara/ara/hardware/build-v128/verilator/Vara_tb_verilator'
LD='/home/baiyifan/workplace-local/isla-runner/ara/work-diff/elf-check-emu/ara.ld'
def build(case, tag):
    src=open(f'{CASEDIR}/{case}/program.S').read()
    head, rest = src.split('after_test:', 1)
    # after_test label; then enable hw_cnt_en dump; then ORIGINAL rest (dump+compare+exit)
    ins = ("after_test:\n"
           "    li t0, 0xD0000000\n"
           "    li t1, 1\n"
           "    sd t1, 32(t0)\n")
    out=f'/tmp/probe/{case}-{tag}.S'
    open(out,'w').write(head+ins+rest)
    subprocess.run(['riscv64-unknown-elf-gcc','-nostdlib','-nostartfiles','-march=rv64gcv_zfh_zvfh',
        '-T',LD,'-o',out+'.elf',out],check=True,capture_output=True)
    return out+'.elf'
def run_dump(case, tag='dump'):
    elf=build(case,tag)
    cwd=f'/tmp/probe/run-{case}-{tag}'; os.makedirs(cwd+'/x',exist_ok=True)
    res=cwd+'/gold_results.txt'
    if os.path.exists(res): os.remove(res)
    try:
        r=subprocess.run([EMU,'-c','2000000','-l','ram,'+elf+',elf'],cwd=cwd+'/x',capture_output=True,text=True,timeout=120)
        rc=r.returncode&0xff
    except subprocess.TimeoutExpired:
        return None,'HANG'
    if not os.path.exists(res): return None,'NODUMP rc=%d'%rc
    by=bytes(int(l,16) for l in open(res) if l.strip())
    words=list(struct.unpack('<%dQ'%(len(by)//8),by))
    # emu stream: [t6val][x1..x30][vl][vtype][vstart][vcsr][v0..v31]
    sig={'x':words[1:31],'vl':words[31],'vtype':words[32],'vstart':words[33],'vcsr':words[34],'vregs':words[35:99]}
    return sig, rc
def golden(case):
    b=open(f'/home/baiyifan/workplace-local/isla-runner/ara/work-diff/elf-x/{case}/golden.bin','rb').read()
    w=struct.unpack('<99Q',b)
    return {'x':w[0:30],'vl':w[30],'vtype':w[31],'vstart':w[32],'vcsr':w[33],'vregs':w[34:98]}
def compare(case, tag='dump'):
    a,rc=run_dump(case,tag); g=golden(case)
    if a is None: print(case,'EMUFAIL',rc); return None
    diffs=[]
    for i,(x,y) in enumerate(zip(a['x'],g['x'])):
        if x!=y: diffs.append(('x%d'%(i+1),x,y))
    for k in ['vl','vtype','vstart','vcsr']:
        if a[k]!=g[k]: diffs.append((k,a[k],g[k]))
    for i in range(31):
        lo,hi=a['vregs'][2*i:2*i+2]; glo,ghi=g['vregs'][2*i:2*i+2]
        if lo!=glo: diffs.append(('v%d.lo'%(i),lo,glo))
        if hi!=ghi: diffs.append(('v%d.hi'%(i),hi,ghi))
    return a,g,diffs,rc
if __name__=='__main__':
    for case in sys.argv[1:]:
        r=compare(case)
        if r is None: continue
        a,g,diffs,rc=r
        print('==',case,'check_exit=',rc)
        for d in diffs[:12]: print('   DIFF %-8s ara=%016x spike=%016x'%(d[0],d[1],d[2]))
        if not diffs: print('   no diff')
