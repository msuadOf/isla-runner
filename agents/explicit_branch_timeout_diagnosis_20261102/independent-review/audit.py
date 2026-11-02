"""只读复核冻结输入、A 路径账及策略结果；输出限定在独审目录。"""
from pathlib import Path
import collections
import csv
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
TOPIC = HERE.parent
ROOT = TOPIC.parents[1]
INPUTS = ROOT / "agents/branch_ablation_official_z3_20261102/inputs"


def functions(path):
    return {m[1]: m[0] for m in re.finditer(
        r"^fn (\S+)\([^\n]*\) \{\n.*?^\}", path.read_text(), re.M | re.S
    )}


def normalize_parameters(body):
    params = body.split("(", 1)[1].split(")", 1)[0].split(", ")
    for index, param in enumerate(params):
        if param:
            body = re.sub(r"(?<![\w])" + re.escape(param) + r"(?![\w])", f"PARAM{index}", body)
    return body


result = {}
for workload in ("flags-arithmetic", "sat"):
    directory = TOPIC / "path-accounting" / ("aux-" + workload + "-A")
    log = (directory / "run.log").read_text()
    data = json.loads(next((directory / "output").glob("*.json")).read_text())
    a, b = [functions(INPUTS / workload / f"{arm}.ir") for arm in ("A", "B")]
    compare = TOPIC / "tactic-investigation/compare" / workload / "compare.tsv"
    with compare.open() as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    result[workload] = {
        "a_path_events": dict(collections.Counter(re.findall(r"PATH_ACCOUNT \S+ (.*)", log))),
        "a_returns": dict(collections.Counter(re.findall(r"ret_val=([^\n]*)", log))),
        "a_summary": data["summary"],
        "changed_functions_raw": [name for name in a if a[name] != b[name]],
        "changed_functions_after_parameter_renaming": [name for name in a if
            normalize_parameters(a[name]) != normalize_parameters(b[name])],
        "strategy_comparison": rows,
        "a_log_sha256": hashlib.sha256((directory / "run.log").read_bytes()).hexdigest(),
    }
(HERE / "audit.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
print(json.dumps({key: value["changed_functions_after_parameter_renaming"] for key, value in result.items()}))
