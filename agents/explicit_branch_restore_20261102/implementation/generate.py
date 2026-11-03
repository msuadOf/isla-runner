#!/usr/bin/env python3
"""从审核通过的干净模型提交生成严格 IR，并记录四配置来源。"""
from pathlib import Path
import concurrent.futures,hashlib,json,subprocess,time,os
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent/'generation'
MODEL=ROOT/'.worktree/runner-float/sail-riscv'
SAIL=ROOT/'isla/target/float-solve-evidence/unified-backend-build/toolchain-a198-v2-20260927/sail-src/sail'
PLUGIN=ROOT/'.tmp/float-full-trace-20260929/fvv-branch-candidate/sail_plugin_isla.cmxs'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
PRESERVE=('encdec_compressed_forwards','encdec_compressed_forwards_matches','encdec_compressed_backwards','encdec_compressed_backwards_matches','get_F','set_F','set_V','riscv_f16ToI16','riscv_f16ToUi16','riscv_f32ToI16','riscv_f32ToUi16')
sources={str(p.relative_to(MODEL/'model')):sha(p) for p in (MODEL/'model').rglob('*') if p.is_file()}
base={'model_commit':subprocess.check_output(['git','-C',str(MODEL),'rev-parse','HEAD'],text=True).strip(),'model_dirty':False,'model_files':sources,'source_patch_sha256':sha(OUT.parent/'model.patch'),'plugin_sha256':sha(PLUGIN),'sail_launcher_sha256':sha(SAIL),'sail_version':subprocess.check_output([str(SAIL),'--version'],text=True).strip()}
def run(kind,config):
 out=OUT/kind;out.mkdir(parents=True,exist_ok=True)
 cfg=ROOT/'isla/ir/provenance'/config
 if kind!='ordinary-strict':
  cmd=['/usr/bin/python3',str(ROOT/'isla/scripts/regenerate_ir.py'),'--model',str(MODEL),'--sail',str(SAIL),'--plugin',str(PLUGIN),'--config',str(cfg),'--output',str(out),'--name',kind]
 else:
  cmd=[str(SAIL),'--strict-var','--strict-bitvector','--strict-exponentials','--require-version','0.20.1','--memo-z3-path',str(out/'sail_smt_cache'),'--all-modules','--just-check','--config',str(cfg),'riscv.sail_project']
 rec=base|{'command':cmd,'config_sha256':sha(cfg),'cwd':str(MODEL/'model')};start=time.monotonic()
 with (out/'driver.log').open('w') as log:r=subprocess.run(cmd,cwd=MODEL/'model',stdout=log,stderr=subprocess.STDOUT)
 rec.update(exit_code=r.returncode,seconds=time.monotonic()-start,source_unchanged=all(sha(MODEL/'model'/p)==v for p,v in sources.items()))
 if (out/(kind+'.ir')).exists():rec['ir_sha256']=sha(out/(kind+'.ir'))
 (out/'driver.json').write_text(json.dumps(rec,indent=2,ensure_ascii=False)+'\n');print(kind,r.returncode,flush=True)
 return r.returncode
if __name__=='__main__':
 assert not subprocess.check_output(['git','-C',str(MODEL),'status','--porcelain']), '源仓必须clean'
 OUT.mkdir(parents=True,exist_ok=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
  codes=list(ex.map(lambda x:run(*x), [('rv64d_v128_e64','rv64d.json'),('rv32d','rv32d.json'),('rv64d_v256_e64','rv64d_v256_e64.json'),('rv64d_v512_e64','rv64d_v512_e64.json'),('ordinary-strict','rv64d.json')]))
 raise SystemExit(any(codes))
