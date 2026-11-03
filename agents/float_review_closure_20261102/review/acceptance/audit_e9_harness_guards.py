#!/usr/bin/env python3
"""Pre-sign only exact version/tree metadata additions, preserving old contracts."""
import hashlib,json,subprocess
from pathlib import Path
from audit_conversion_expected import expected
H=Path(__file__).resolve().parent;T=H.parents[1];R=H.parents[3];V=T/'validation';B=H/'harness-baselines-214'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(s):return hashlib.sha256(s.encode()).hexdigest()
E9='e9d69d2f28586c089244c8e37ee4c904c5114458';BASE='21418d0b0d4942fae20061ed580ee04aff4a8a61'
flags=V/'flags/run.py';s=flags.read_text();line=f'        "{E9}",\n';assert s.count(line)==1
assert s.replace(line,'')==(B/'validation/flags/run.py').read_text()
flagdeps=['src/main.rs','oracle.py']
for name in flagdeps:assert (V/'flags'/name).read_bytes()==(B/'validation/flags'/name).read_bytes()

conv=V/'conversions/frozen-inputs-e9d69d2';old=V/'conversions/frozen-inputs-21418d0';snap=json.loads((conv/'snapshot.json').read_text());changed=[]
for name,want in snap['files'].items():
 assert sha(conv/name)==want
 if (conv/name).read_bytes()!=(old/name).read_bytes():changed.append(name)
assert changed==['run.py']
s=(conv/'run.py').read_text()
assert 'ROOT = HERE.parents[4]' in s
s=s.replace('ROOT = HERE.parents[4]','ROOT = HERE.parents[3]')
s=s.replace('"runner_build", "model_tree"):', '"runner_build"):')
s=s.replace('    model_tree = args.model_tree.resolve()\n    assert git_head(model_tree) == args.model_commit','    assert git_head(ROOT / ".worktree/runner-float/sail-riscv") == args.model_commit')
s=s.replace('verify_source_manifest(args.model_source, model_tree, args.model_commit)','verify_source_manifest(args.model_source, ROOT / ".worktree/runner-float/sail-riscv", args.model_commit)')
s=s.replace('    record = {"model_commit": args.model_commit, "model_tree": display(model_tree),\n              "isla_commit": args.isla_commit,','    record = {"model_commit": args.model_commit, "isla_commit": args.isla_commit,')
assert s==(old/'run.py').read_text()
rows=json.loads((conv/'oracle-rows.json').read_text())
assert len(rows)==819
for row in rows:assert expected(row)==(row['result_bits'],row['flags'])

exceptions=V/'exceptions/run_directed.py';s=exceptions.read_text()
for line in [f'CORE_MODEL_COMMIT = "{E9}"\n','CORE_DELTA_SHA256 = "9dbf13575b7b32f48adb05f40c392bdbd520f77a980cea4d7594946808a1e9dd"\n','    model_delta_base_commit = None\n','        model_delta_base_commit = BASE_MODEL_COMMIT\n','                                "model_delta_base_commit": model_delta_base_commit,\n']:
 assert s.count(line)==1;s=s.replace(line,'')
s=s.replace('(BASE_MODEL_COMMIT, ASSEMBLY_MODEL_COMMIT, CORE_MODEL_COMMIT)','(BASE_MODEL_COMMIT, ASSEMBLY_MODEL_COMMIT)')
a=s.index('    elif inputs["model_commit"] == CORE_MODEL_COMMIT:');b=s.index('    for commit, tree in ',a);s=s[:a]+s[b:]
assert s==(B/'validation/exceptions/run_directed.py').read_text()
for name in ['prepare_expected.py','expected.json']:assert (V/'exceptions'/name).read_bytes()==(B/'validation/exceptions'/name).read_bytes()
tree=R/'.worktree/sail-riscv-general-float-by-model-20261022'
git=lambda *args:subprocess.check_output(['git','-C',str(tree),*args])
assert git('rev-parse',E9+'^').decode().strip()==BASE
assert git('diff','--name-only',BASE,E9).decode().splitlines()==['model/core/ieee_fp_exceptions.sail']
delta=hashlib.sha256(git('diff','--no-ext-diff',BASE,E9)).hexdigest();assert delta=='9dbf13575b7b32f48adb05f40c392bdbd520f77a980cea4d7594946808a1e9dd'
out={'scope':'Static pre-sign of exact e9 guards/tree selection and unchanged independent expectations; no e9 dynamic PASS','model_commit':E9,'candidate_parent':BASE,'candidate_core_delta_sha256':delta,'flags':{'runner_sha256':sha(flags),'inverse_to_214_sha256':sha(B/'validation/flags/run.py'),'probe_source_sha256':sha(V/'flags/src/main.rs'),'oracle_sha256':sha(V/'flags/oracle.py')},'conversions':{'runner_sha256':sha(conv/'run.py'),'snapshot_sha256':sha(conv/'snapshot.json'),'unchanged_input_files':13,'changed_input_files':changed,'frozen_subdirectory_root_depth_corrected':True,'independent_fraction_expectations':len(rows)},'exceptions':{'runner_sha256':sha(exceptions),'inverse_to_214_sha256':sha(B/'validation/exceptions/run_directed.py'),'expected_sha256':sha(V/'exceptions/expected.json'),'expected_source_commit':'8ad5e8e9e0fc2a567a3b989a3738698f5c520bde'},'pass':True}
(H/'e9-harness-guards-attempt2-independent.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
