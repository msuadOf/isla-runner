#!/usr/bin/env python3
"""从探针首条对照输出提取指令字段与机器编码，避免 HashMap 打印顺序干扰。"""
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent

def extract(name):
    line = next(line for line in (HERE / f"{name}-run.log").read_text(errors="replace").splitlines()
                if line.startswith("COLLECTOR_CONTROL concrete_arg="))
    bits = {}
    for field in (0, 1, 3):
        match = re.search(rf'_S{field}"\): Bits\(B129 \{{ tag: false, bits: (\d+),', line)
        assert match, (name, field)
        bits[field] = int(match.group(1))
    assert '_S2"): Enum(' in line and 'zRM_DYN' in line
    assert '_S4"): Enum(' in line and 'zFDIV_S' in line
    canonical = f'F_BIN_RM_TYPE_S|S0={bits[0]}|S1={bits[1]}|S2=RM_DYN|S3={bits[3]}|S4=FDIV_S'
    encodings = [int(value) for value in re.findall(r'bits: (\d+), len: 32', line)]
    return {"run": name, "instruction": canonical, "sha256": hashlib.sha256(canonical.encode()).hexdigest(),
            "encodings_hex": [hex(value) for value in encodings], "equal_marker": 'equal=true' in line}

if __name__ == '__main__':
    result = [extract(name) for name in ('control3', 'fresh3', 'replicate', 'clean')
              if (HERE / f'{name}-run.log').exists() and
              'COLLECTOR_CONTROL concrete_arg=' in (HERE / f'{name}-run.log').read_text(errors='replace')]
    print(json.dumps(result, indent=2))
