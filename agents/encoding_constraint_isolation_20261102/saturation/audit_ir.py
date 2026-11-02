#!/usr/bin/env python3
"""核对正式 IR 仅改变已验证的 f16→i16 helper，并保留活动 gate。"""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OLD = ROOT / "agents/special_control_restore_20261102/implementation/generation"
BRANCH = ROOT / "agents/explicit_branch_timeout_diagnosis_20261102/active-lane-control/B.ir"
FN = "fn zriscv_f16ToI16_pure(zrm, zv) {"
NAMES = ("rv64d_v128_e64", "rv32d", "rv64d_v256_e64", "rv64d_v512_e64")


def extract(ir):
    begin = ir.index(FN)
    end = ir.index("\n}\n", begin) + 3
    return ir[begin:end]


def normalize(fragment):
    return re.sub(r" `[^;]+;", ";", fragment)


def normalized_functions(text):
    result = {}
    for name, formals, body in re.findall(r"(?ms)^fn ([^(\n]+)\(([^\n]*)\) \{\n(.*?)^\}", text):
        body = re.sub(r"`\d+(?: \d+:\d+(?:-\d+:\d+)?)?", "", body)
        body = re.sub(r"([\w./-]+\.sail):\d+\.\d+-\d+\.\d+", r"\1:LOC", body)
        replacements = {formal.strip(): "__arg" + str(i)
                        for i, formal in enumerate(formals.split(",")) if formal.strip()}

        def rename(match):
            token = match.group()
            if token not in replacements:
                replacements[token] = "__local" + str(len(replacements))
            return replacements[token]

        tokens = "|".join(re.escape(token) for token in replacements)
        pattern = r"(?<![A-Za-z0-9_$])(?:zz[0-9]+" + ("|" + tokens if tokens else "") + r")(?![A-Za-z0-9_$])"
        result[name] = re.sub(pattern, rename, body)
    return result


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


reference = normalize(extract(BRANCH.read_text()))
checks = {}
for name in NAMES:
    old_path = OLD / name / (name + ".ir")
    new_path = HERE / "generation" / name / (name + ".ir")
    old = old_path.read_text()
    new = new_path.read_text()
    old_fn = extract(old)
    new_fn = extract(new)
    before = normalized_functions(old)
    after = normalized_functions(new)
    changed = sorted(key for key in before.keys() | after.keys()
                     if before.get(key) != after.get(key))
    assert changed == ["zriscv_f16ToI16_pure"], (name, changed)
    assert "zitezIB5zK(zz44" in old_fn, name
    assert "jump zz44 goto" in new_fn, name
    assert normalize(new_fn) == reference, name
    driver = json.loads((new_path.parent / "driver.json").read_text())
    generation = json.loads((new_path.parent / "generation.json").read_text())
    assert driver["exit_code"] == generation["exit_code"] == 0, name
    assert driver["model_commit"] == generation["model_commit"] == "6202e23fc43a9aa98d9fbfd42f0f2e6128cf7f9a", name
    assert driver["source_unchanged"] and not driver["model_dirty"], name
    assert driver["ir_sha256"] == generation["ir_sha256"] == digest(new_path), name
    checks[name] = {
        "baseline_ir_sha256": digest(old_path),
        "ir_sha256": digest(new_path),
        "outside_helper_normalized_equal": True,
        "helper_normalized_equal_to_measured_explicit_arm": True,
        "model_commit": driver["model_commit"],
    }

(HERE / "ir-audit.json").write_text(json.dumps(checks, indent=2) + "\n")
print(json.dumps(checks, indent=2))
