#!/usr/bin/env python3
"""核对本轮严格生成来源，安装五入口及可移植来源记录；不写 Git。"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'output/memory-enum-20261107'
STAGE = OUT / 'generation/current'
ISLA = ROOT / 'isla'
MODEL = ROOT / 'sail-riscv'
PROV = ISLA / 'ir/provenance'
sys.path.insert(0, str(ROOT / 'agents/float_memory_merge_20261103/validation'))
from audit_generation import collect_tool_hashes
sys.path.insert(0, str(ROOT / 'agents/float_memory_merge_20261103/validation/integration'))
from install_ir import CONFIGS, check_workarounds

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def git(p,*args):
    return subprocess.check_output(['git','-C',str(p),*args],text=True).strip()

def portable(value):
    if isinstance(value,dict):
        return {portable(k):portable(v) for k,v in value.items()}
    if isinstance(value,list):
        return [portable(v) for v in value]
    if isinstance(value,str):
        return value.replace(str(ROOT)+'/', 'repo:/').replace('/home/linuxbrew/.linuxbrew/', 'linuxbrew:/')
    return value

def dump(p,value):
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def main():
    source=json.loads((STAGE/'source.json').read_text())
    commit=git(MODEL,'rev-parse','HEAD')
    isla_commit=git(ISLA,'rev-parse','HEAD')
    assert commit==source['commit'] and not git(MODEL,'status','--porcelain')
    files={n.removeprefix('model/'):sha(MODEL/n) for n in git(MODEL,'ls-files','model').splitlines()}
    assert files==source['model_files']
    tools,binary=collect_tool_hashes(Path(source['sail_path']),Path(source['plugin_path']))
    assert tools==source['tool_files_pre']
    assert all(Path(p).stat().st_ctime_ns < (STAGE/'source.json').stat().st_mtime_ns for p in tools)
    assert sha(Path(source['compile_z3_path']))==source['compile_z3_sha256']
    ordinary=json.loads((STAGE/'ordinary-strict/driver.json').read_text())
    def check_driver(d):
        assert d['exit_code']==0 and d['model_commit']==commit and d['model_files']==files
        assert d['source_unchanged'] and d['tool_files_unchanged'] and d['compile_z3_unchanged']
        assert d['compile_z3_live_hash_matches'] and d['actual_sail_binary'] in d['live_executables']
    check_driver(ordinary)
    assert '--just-check' in ordinary['command'] and '-D' not in ordinary['command']
    old=json.loads((PROV/'manifest.json').read_text())
    old_sha=sha(PROV/'manifest.json')
    artifacts=[]; receipts={}
    strict={'--strict-var','--strict-bitvector','--strict-exponentials','--require-version','0.20.1','--all-modules'}
    assert strict.issubset(ordinary['command'])
    template=None
    for kind,(config,paths) in CONFIGS.items():
        d=json.loads((STAGE/kind/'driver.json').read_text())
        g=json.loads((STAGE/kind/'generation.json').read_text())
        check_driver(d)
        ir=STAGE/kind/(kind+'.ir'); digest=sha(ir)
        assert g['exit_code']==0 and g['model_commit']==commit and g['model_files']==files
        assert d['ir_sha256']==g['ir_sha256']==digest
        assert d['config_sha256']==g['config_sha256']==sha(PROV/config)
        assert g['sail_launcher_sha256']==source['sail_sha256'] and g['plugin_sha256']==source['plugin_sha256']
        assert strict.issubset(g['command']) and g['command'][g['command'].index('-D')+1]=='SYMBOLIC'
        substitutions={source['sail_path']:'SAIL',source['plugin_path']:'PLUGIN',str(STAGE/kind/'sail_smt_cache'):'MEMO',str(STAGE/kind):'OUT',str(PROV/config):'CONFIG',kind:'NAME'}
        current=[substitutions.get(x,x) for x in g['command']]
        if template is None:template=current
        assert current==template
        receipt={'schema':1,'date':'2026-11-07','isla_commit':isla_commit,'generation':g,'driver':d,
                 'logs':{str(p.relative_to(ROOT)):sha(p) for p in [STAGE/kind/'driver.log',STAGE/kind/'generation.log']}}
        receipt_path=PROV/('generation-'+kind+'.json'); dump(receipt_path,portable(receipt))
        for rel in paths:
            shutil.copy2(ir,ISLA/rel)
            assert sha(ISLA/rel)==digest
        artifacts.append({'paths':list(paths),'sha256':digest,'config':config,'config_sha256':sha(PROV/config),
                          'model_files':{n:{'sha256':s} for n,s in files.items()},'generation_seconds':g['seconds'],
                          'provenance':receipt_path.name,'provenance_sha256':sha(receipt_path)})
        receipts[kind]={'paths':list(paths),'sha256':digest,'generation_seconds':g['seconds']}
    audit={'schema':1,'date':'2026-11-07','source':source,'ordinary_strict':ordinary,
           'isla_commit':isla_commit,'isla_source_branch':'feat/postprocess-enumeration',
           'model_source_branch':'feat/sail-riscv-memory-by-model-20261022',
           'model_file_count':len(files),'tool_file_count':len(tools),'tool_ctime_precedes_generation_start':True,
           'model_and_tools_unchanged':True,
           'configuration_adjustment':{'reason':'新模型新增配置项，Isla后端不支持未定值的运行时配置',
                                       'RV64':{'Svnapot.supported':True,'Svpbmt.supported':True},
                                       'RV32':{'Svnapot.supported':False,'Svpbmt.supported':False},
                                       'basis':'sail-riscv/config/config.json.in 的 CONFIG_XLEN_IS_64'},
           'workarounds':check_workarounds(MODEL,receipts['rv64d_v128_e64']['sha256'])}
    audit_path=PROV/'generation-inputs-20261107.json'; dump(audit_path,portable(audit))
    manifest=dict(old)
    manifest.update(model_commit=commit,model_dirty=False,isla_commit=isla_commit,
                    isla_commit_role='生成插件/执行器源码基准；本轮IR及四配置补项尚未提交',
                    isla_generation_config_dirty=True,isla_ir_installation_pending_commit=True,
                    isla_source_branch='feat/postprocess-enumeration',model_source_branch=audit['model_source_branch'],
                    sail_version=source['sail_version'],sail_binary_sha256=tools[binary],
                    sail_launcher_sha256=source['sail_sha256'],plugin_sha256=source['plugin_sha256'],
                    artifacts=artifacts,command_template=template,generated='2026-11-07',
                    generation_audit={'path':'isla/ir/provenance/'+audit_path.name,'sha256':sha(audit_path),
                                      'model_file_count':len(files),'tool_file_count':len(tools)},
                    change='枚举分支含区域合并/枚举并已合入4d085b14；模型增加Svnapot、Svpbmt、非叶PTE U/A/D检查，含70b4d10全寄存器访存早退修复',
                    publication_status='待发布')
    manifest['history']=[*old.get('history',[]),{'model_commit':old['model_commit'],'manifest_sha256':old_sha,
                          'isla_commit':old.get('isla_commit','4d085b14aa0f987436b86d72f41fab1df9e9a132'),
                          'artifacts':[{k:a[k] for k in ('paths','sha256','config','config_sha256')} for a in old['artifacts']],
                          'note':'旧合流来源与PASS只适用4d085b14/bf861b3e；历史报告保留原结论'}]
    dump(PROV/'manifest.json',manifest)
    report={'model_commit':commit,'isla_commit':isla_commit,'ordinary_strict_seconds':ordinary['seconds'],
            'artifacts':receipts,'manifest_sha256':sha(PROV/'manifest.json'),'workarounds':audit['workarounds']}
    dump(OUT/'installed.json',report)
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
