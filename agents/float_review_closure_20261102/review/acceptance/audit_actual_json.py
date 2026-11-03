#!/usr/bin/env python3
"""Recompute numerical results from actual instruction words and JSON pre-state.

This reads no owner expected fixture and never runs Isla. Unsupported encodings
are counted explicitly; this is a numerical sample audit, not coverage proof.
"""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
ORACLE=ROOT/'.tmp/unified-backend-crosscheck/oracle-build/oracle'
FORMATS={16:'f16',32:'f32',64:'f64'}
CACHE={}
def number(x):
    if isinstance(x,int):return x
    m=re.fullmatch(r"\d+'h([\da-fA-F_]+)",x)
    return int(m[1].replace('_',''),16) if m else int(x,0)
def mask(width):return (1<<width)-1
def box(raw,width):return raw|(mask(64)^mask(width))
def effective(raw,width):
    if width<64 and raw>>width!=mask(64-width):return {16:0x7e00,32:0x7fc00000}[width]
    return raw&mask(width)
def oracle(op,width,rm,a,b=None,c=None,dst=None):
    args=['--op',op,'--fmt',FORMATS[width],'--rm',str(rm),'--a',hex(a)]
    for key,value in [('b',b),('c',c)]:
        if value is not None:args+=['--'+key,hex(value)]
    if dst is not None:args+=['--dst',dst]
    key=tuple(args)
    if key not in CACHE:
        r=json.loads(subprocess.check_output([str(ORACLE),*args],text=True));CACHE[key]=(int(r['result_bits'],16),int(r['flags'],16))
    return CACHE[key]
def check_entry(entry):
    if 'Retire_Success' not in entry.get('ret_val',''):return None
    word=number(entry['test-ins-encdec']);pre=entry['isa-state-complete'];post=entry['isa-state-post']
    opcode=word&127;rd=word>>7&31;rs1=word>>15&31;rs2=word>>20&31;rm=word>>12&7
    oldflags=number(pre['fcsr'])&31
    if rm==7:rm=number(pre['fcsr'])>>5&7
    assertions=[]
    def check(label,actual,expected):
        assertions.append({'field':label,'actual':hex(actual),'expected':hex(expected),'pass':actual==expected})
    if opcode==0x53:
        fn=word>>25;fmt=fn&3;width={0:32,1:64,2:16}.get(fmt)
        if width is None:return None
        op={0:'add',4:'sub',8:'mul',12:'div',44:'sqrt',96:'fp_to_int',104:'int_to_fp'}.get(fn-fmt)
        if op is None:return None
        if op=='int_to_fp':
            source_kind={0:'i32',1:'u32',2:'i64',3:'u64'}.get(rs2)
            if source_kind is None:return None
            source_width=32 if rs2<2 else 64
            raw=(0 if rs1==0 else number(pre[f'x{rs1}']))&mask(source_width)
            args=['--op','int_to_fp','--fmt',source_kind,'--dst',FORMATS[width],'--rm',str(rm),'--a',hex(raw)]
            r=json.loads(subprocess.check_output([str(ORACLE),*args],text=True));bits,flags=int(r['result_bits'],16),int(r['flags'],16)
        else:
            a=effective(number(pre[f'f{rs1}']),width)
            b=None if op in ('sqrt','fp_to_int') else effective(number(pre[f'f{rs2}']),width)
            dst={0:'i32',1:'u32',2:'i64',3:'u64'}.get(rs2) if op=='fp_to_int' else None
            if op=='fp_to_int' and dst is None:return None
            bits,flags=oracle(op,width,rm,a,b,dst=dst)
        if op=='fp_to_int':
            if dst.endswith('32') and bits>>31:bits|=0xffffffff00000000
            if rd:check('x'+str(rd),number(post['x'+str(rd)]),bits)
        else:check('f'+str(rd),number(post['f'+str(rd)]),box(bits,width))
    elif opcode in (0x43,0x47,0x4b,0x4f):
        width={0:32,1:64,2:16}.get(word>>25&3)
        if width is None:return None
        rs3=word>>27&31
        a=effective(number(pre[f'f{rs1}']),width);b=effective(number(pre[f'f{rs2}']),width);c=effective(number(pre[f'f{rs3}']),width)
        # FMSUB = a*b-c; FNMSUB = -a*b+c; FNMADD = -a*b-c.
        if opcode in (0x4b,0x4f):a^=1<<(width-1)
        if opcode in (0x47,0x4f):c^=1<<(width-1)
        bits,flags=oracle('fma',width,rm,a,b,c);check('f'+str(rd),number(post['f'+str(rd)]),box(bits,width))
    elif opcode==0x57:
        funct6=word>>26;funct3=word>>12&7;vm=word>>25&1
        vt=number(pre['vtype']);width=8<<(vt>>3&7);vl=number(pre['vl']);start=number(pre['vstart'])
        # This audit intentionally supports LMUL1, undisturbed tails/masks only.
        if (vt&7)!=0 or vt&0xc0 or width not in FORMATS:return None
        is_narrow=funct6==18 and funct3==1 and rs1 in (20,21)
        is_bf16=funct6==59 and funct3 in (1,5) and width==16
        op={0:'add',2:'sub',36:'mul',32:'div'}.get(funct6) if funct3==1 else None
        if not (is_narrow or is_bf16 or op):return None
        sourcewidth=2*width if is_narrow else width;destwidth=2*width if is_bf16 else width
        if vl*max(sourcewidth,destwidth)>128:return None
        expected=number(pre[f'vr{rd}']);flags=0;rm=number(pre['fcsr'])>>5&7
        vmask=number(pre['vr0'])
        for lane in range(vl):
            if lane<start or not(vm or vmask>>lane&1):continue
            a=number(pre[f'vr{rs2}'])>>(lane*sourcewidth)&mask(sourcewidth)
            if is_narrow:
                bits,oneflags=oracle('fp_to_fp',sourcewidth,6 if rs1==21 else rm,a,dst=FORMATS[destwidth])
            elif is_bf16:
                b=(number(pre[f'vr{rs1}'])>>(lane*16)&mask(16)) if funct3==1 else effective(number(pre[f'f{rs1}']),16)
                c=number(pre[f'vr{rd}'])>>(lane*32)&mask(32)
                bits,oneflags=oracle('fma',32,rm,a<<16,b<<16,c)
            else:
                b=number(pre[f'vr{rs1}'])>>(lane*width)&mask(width)
                bits,oneflags=oracle(op,width,rm,a,b)
            flags|=oneflags;expected=(expected&~(mask(destwidth)<<(lane*destwidth)))|(bits<<(lane*destwidth))
        check('vr'+str(rd),number(post['vr'+str(rd)]),expected)
        check('vstart',number(post['vstart']),0)
    else:return None
    check('fcsr.flags',number(post['fcsr'])&31,oldflags|flags)
    check('fcsr.other',number(post['fcsr'])&~31,number(pre['fcsr'])&~31)
    return {'instruction':entry['test-ins'],'word':hex(word),'checks':assertions,'pass':all(x['pass'] for x in assertions)}
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    rows=[];skipped=[];files=sorted(args.root.rglob('output/*.json'))
    for path in files:
        data=json.loads(path.read_text())
        for index,entry in enumerate(data.get('gen',[])):
            try:result=check_entry(entry)
            except Exception as error:result={'pass':False,'error':repr(error),'instruction':entry.get('test-ins')}
            name={'file':str(path),'index':index}
            if result is None:skipped.append({**name,'instruction':entry.get('test-ins'),'ret_val':entry.get('ret_val')})
            else:rows.append({**name,**result})
    out={'scope':'Actual machine-word/pre-state numerical replay; no owner expected fixture read','oracle_sha256':hashlib.sha256(ORACLE.read_bytes()).hexdigest(),'files':len(files),'checked_entries':len(rows),'skipped_entries':len(skipped),'failures':sum(not r['pass'] for r in rows),'rows':rows,'skipped':skipped}
    args.output.write_text(json.dumps(out,indent=2)+'\n');print({k:v for k,v in out.items() if k not in ('rows','skipped')});assert rows and not out['failures']
if __name__=='__main__':main()
