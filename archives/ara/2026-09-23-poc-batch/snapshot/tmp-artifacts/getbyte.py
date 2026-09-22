import sys
sys.path.insert(0,'/tmp/probe')
import probe
def vreg_word(case, vreg, half):  # half 0=lo,1=hi
    val=0
    for i in range(8):
        code=(f"    la t1, sig_region\n"
              f"    .4byte 0x{0x02830027+vreg*0x80:08x} # vs1r.v v{vreg}, (t1)\n"
              f"    ld t0, {half*8}(t1)\n"
              f"    srli t0, t0, {i*8}\n"
              f"    andi a0, t0, 0xff\n"
              f"    j _exit")
        rc,_=probe.run(probe.build(case, code, f'gb{vreg}{half}{i}'))
        if rc=='HANG': return None
        val |= rc << (i*8)
    return val
if __name__=='__main__':
    case,vreg,half=sys.argv[1],int(sys.argv[2]),int(sys.argv[3])
    x=vreg_word(case,vreg,half)
    print(f'{case} v{vreg}.{"lo" if half==0 else "hi"} = 0x{x:016x}' if x is not None else 'HANG')
