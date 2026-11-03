#!/usr/bin/env python3
"""核当前JSON三种汇编表示：GCC与Clang须产生与编码完全相同的字节。"""
from pathlib import Path
import hashlib,json,subprocess
HERE=Path(__file__).resolve().parent
DRIVERS={'gcc':['/usr/bin/riscv64-unknown-elf-gcc','-march=rv64gcv_zfh_zfa','-Wa,-march=rv64gcv_zfh_zfa_zfbfmin_zvfbfmin_zvfbfwma','-mabi=lp64d'],'clang':['/home/linuxbrew/.linuxbrew/bin/clang','--target=riscv64-unknown-elf','-march=rv64gcv_zfh_zfa_zfbfmin_zvfbfmin_zvfbfwma','-mabi=lp64d']}
SOURCES=[HERE/'make-smoke/output/rv64_zFLEQ_S.json',HERE/'runs/bf16-VV-fused-rm0/output/rv64_zVFWMACCBF16_VV.json',HERE/'runs/bf16-VF-fused-rm0/output/rv64_zVFWMACCBF16_VF.json']
def main():
 dest=HERE/'toolchains';dest.mkdir(exist_ok=True);checks=[];fixture=0
 for p in SOURCES:
  for item in json.loads(p.read_text())['gen']:
   rep=item['instruction-representations'];enc=rep['encoding'];assert enc['status']=='complete';assert rep['insn']['status']=='complete';expected=enc['bytes-le'];assert int(enc['bits'],2).to_bytes(enc['bit-length']//8,'little').hex()==expected
   forms={'mnemonic':rep['mnemonic'],'insn':rep['insn']['text'],'binary':'.byte '+', '.join('0b'+format(b,'08b') for b in bytes.fromhex(expected))}
   for driver,argv in DRIVERS.items():
    for form,text in forms.items():
     stem=dest/f'{fixture}-{driver}-{form}';asm=stem.with_suffix('.s');obj=stem.with_suffix('.o');raw=stem.with_suffix('.bin');asm.write_text('.text\n.option norvc\n'+text+'\n');cmd=argv+['-c',str(asm),'-o',str(obj)];proc=subprocess.run(cmd,capture_output=True,text=True);actual=None
     if proc.returncode==0:subprocess.run(['/usr/bin/riscv64-unknown-elf-objcopy','-O','binary','-j','.text',str(obj),str(raw)],check=True);actual=raw.read_bytes().hex()
     checks.append({'source':str(p.relative_to(HERE)),'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'fixture':fixture,'driver':driver,'representation':form,'text':text,'command':cmd,'exit':proc.returncode,'stderr':proc.stderr,'expected':expected,'actual':actual,'pass':proc.returncode==0 and actual==expected})
   fixture+=1
 result={'state':'PASS' if all(c['pass'] for c in checks) else 'FAIL','fixtures':fixture,'checks':len(checks),'passed':sum(c['pass'] for c in checks),'versions':{n:subprocess.check_output([a[0],'--version'],text=True).splitlines()[0] for n,a in DRIVERS.items()},'results':checks};(dest/'results.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n');print(result['state'],result['passed'],result['checks']);assert result['state']=='PASS'
if __name__=='__main__':main()
