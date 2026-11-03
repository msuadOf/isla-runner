"""只安装四配置全部成功且来源一致的完整IR，保留已有未提交源码。"""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SRC = ROOT / 'isla'
MODEL = ROOT / '.worktree/runner-float/sail-riscv'
STAGES = HERE / 'saturation/generation'
NAMES = ['rv64d_v128_e64', 'rv32d', 'rv64d_v256_e64', 'rv64d_v512_e64']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not subprocess.check_output(['git', '-C', str(MODEL), 'status', '--porcelain'])
    commit = subprocess.check_output(['git', '-C', str(MODEL), 'rev-parse', 'HEAD'], text=True).strip()
    records = []
    for name in NAMES:
        stage = STAGES / name
        record = json.loads((stage / 'generation.json').read_text())
        assert record['exit_code'] == 0 and record['model_commit'] == commit, name
        assert record['ir_sha256'] == digest(stage / (name + '.ir')), name
        assert all(digest(MODEL / 'model' / p) == sha for p, sha in record['model_files'].items()), name
        config = 'rv64d.json' if name == 'rv64d_v128_e64' else name + '.json'
        assert record['config_sha256'] == digest(SRC / 'ir/provenance' / config), name
        records.append((name, config, record))
    ordinary = json.loads((STAGES / 'ordinary-strict/driver.json').read_text())
    assert ordinary['exit_code'] == 0 and ordinary['model_commit'] == commit and ordinary['source_unchanged']
    manifest_path = SRC / 'ir/provenance/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    artifacts = []
    for name, config, record in records:
        paths = ['rv64d.ir', 'ir/rv64d_v128_e64.ir'] if name == 'rv64d_v128_e64' else [
            'rv32d.ir' if name == 'rv32d' else 'ir/' + name + '.ir']
        for relative in paths:
            shutil.copy2(STAGES / name / (name + '.ir'), SRC / relative)
        artifacts.append({
            'paths': paths, 'sha256': record['ir_sha256'], 'config': config,
            'config_sha256': record['config_sha256'],
            'model_files': {p: {'sha256': sha} for p, sha in record['model_files'].items()},
            'generation_seconds': record['seconds'],
        })
    manifest.update(model_commit=commit, model_dirty=False, artifacts=artifacts,
                    sail_version=records[0][2]['sail_version'],
                    plugin_sha256=records[0][2]['plugin_sha256'],
                    change='在活动lane控制下恢复f16转i16的显式溢出分支；与编码候选/执行约束分离配套验收')
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(commit)


if __name__ == '__main__':
    main()
