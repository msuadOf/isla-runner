#!/usr/bin/env python3
"""Assemble actual Sail-produced output and exact encodings in large batches."""
from pathlib import Path
import argparse,hashlib,json,subprocess
HERE=Path(__file__).resolve().parent
BASE=HERE/'assembly-independent/current'
SPEC={'FCVT_D_S':(0x21,0),'FCVT_D_H':(0x21,2),'FCVT_S_H':(0x20,2),'FCVT_D_W':(0x69,0),'FCVT_D_WU':(0x69,1),'FCVT_D_L':(0x69,2),'FCVT_D_LU':(0x69,3),'FCVT_S_W':(0x68,0),'FSQRT_D':(0x2d,0),'FCVT_S_D':(0x20,1),'FSQRT_H':(0x2e,0),'FCVT_H_S':(0x22,0),'FCVT_H_D':(0x22,1)}
RMS={'RNE':0,'RTZ':1,'RDN':2,'RUP':3,'RMM':4,'DYN':7}
DRIVERS={'gcc':['/usr/bin/riscv64-unknown-elf-gcc','-march=rv64gcv_zfh_zfa','-mabi=lp64d'],'clang':['/home/linuxbrew/.linuxbrew/bin/clang','--target=riscv64-unknown-elf','-march=rv64gcv_zfh_zfa','-mabi=lp64d']}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    global BASE
    parser=argparse.ArgumentParser();parser.add_argument('--base',type=Path,default=BASE);parser.add_argument('--artifacts',type=Path,default=HERE/'assembly-toolchains');parser.add_argument('--output',type=Path,default=HERE/'assembly-toolchains-independent.json');args=parser.parse_args();BASE=args.base
    cases=json.loads((BASE/'cases.json').read_text());text=[x.split('\t',1)[1] for x in (BASE/'run.log').read_text().splitlines() if x.startswith('CASE\t')];assert len(cases)==len(text)==1104
    rows=[]
    for c,s in zip(cases,text):
        assert c['expected']==s;fn,rs2=SPEC[c['op']];word=(fn<<25)|(rs2<<20)|(c['rs']<<15)|(RMS[c['rm']]<<12)|(c['rd']<<7)|0x53
        rows.append({'text':s,'word':word,'bytes':word.to_bytes(4,'little').hex(),'gnu_mnemonic':not c['exact'] or c['rm']=='RNE'})
    outdir=args.artifacts;outdir.mkdir(exist_ok=False);results=[]
    for driver,cmd in DRIVERS.items():
        for form in ['mnemonic','insn','bytes']:
            chosen=[r for r in rows if not(driver=='gcc' and form=='mnemonic') or r['gnu_mnemonic']]
            source=outdir/f'{driver}-{form}.s';obj=source.with_suffix('.o');binary=source.with_suffix('.bin')
            lines=[r['text'] if form=='mnemonic' else f".insn 4, {r['word']:#x}" if form=='insn' else '.byte '+', '.join(hex(b) for b in bytes.fromhex(r['bytes'])) for r in chosen]
            source.write_text('.text\n.option norvc\n'+'\n'.join(lines)+'\n');command=[*cmd,'-c',str(source),'-o',str(obj)];p=subprocess.run(command,capture_output=True,text=True);(source.with_suffix('.log')).write_text(p.stdout+p.stderr);assert p.returncode==0,(driver,form,p.stderr)
            subprocess.run(['/usr/bin/riscv64-unknown-elf-objcopy','-O','binary','-j','.text',str(obj),str(binary)],check=True);actual=binary.read_bytes().hex();want=''.join(r['bytes'] for r in chosen);assert actual==want,(driver,form)
            results.append({'driver':driver,'form':form,'instructions':len(chosen),'exit_code':p.returncode,'bytes_equal':True,'source_sha256':sha(source),'binary_sha256':sha(binary),'command':command})
    out={'scope':'Actual isolated Sail forwards C output; architectural register spelling only; no complete model/JSON run','cases_sha256':sha(BASE/'cases.json'),'forward_log_sha256':sha(BASE/'run.log'),'sail_forward_cases':len(rows),'gnu_nonzero_exact_mnemonic_capability_exclusions':sum(not r['gnu_mnemonic'] for r in rows),'toolchain_instruction_checks':sum(r['instructions'] for r in results),'results':results}
    args.output.write_text(json.dumps(out,indent=2)+'\n');print({k:v for k,v in out.items() if k!='results'})
if __name__=='__main__':main()
