#!/usr/bin/env python3
"""对本轮混合访存 JSON 运行 GCC/Clang 三表示机器字核对。"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CHECKER = ROOT / "agents/float_review_completion_20261102/assembly/check_json.py"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--union", type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.batch):
        parser.error("无效批次名")
    union = args.union.resolve(strict=True)
    if not union.is_relative_to(HERE / "runs"):
        parser.error("只能读取本议题的新混合访存批次")
    out = HERE / "runs" / args.batch / "assembly"
    if out.exists():
        raise ValueError(f"输出批次已存在：{out}")
    out.mkdir(parents=True)
    spec = importlib.util.spec_from_file_location("float_memory_assembly_checker", CHECKER)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    toolchains = {}
    for name, command in checker.DRIVERS.items():
        binary = Path(command[0]).resolve(strict=True)
        toolchains[name] = {"binary": str(binary), "sha256": sha(binary), "arguments": command[1:]}
    results = []
    for path in sorted(union.glob("*/output/*.json")):
        case = path.parent.parent.name
        dest = out / case
        result = {"case": case, "source": str(path), "source_sha256": sha(path), "checker_sha256": sha(CHECKER)}
        try:
            result["checker"] = checker.check(path, dest)
            raw = json.loads((dest / "results.json").read_text())
            result["rows"] = len(raw["checks"])
            result["pass"] = raw["all_pass"] and result["rows"] == 6 * raw["gen"]
        except Exception as exc:
            result["pass"] = False
            result["error"] = repr(exc)
        results.append(result)
    receipt = {"scope": "GCC/Clang mnemonic, .insn, .byte for new mixed JSON",
               "checker_sha256": sha(CHECKER), "runner_sha256": sha(Path(__file__)),
               "toolchains": toolchains, "cases": results,
               "pass": bool(results) and all(row["pass"] for row in results)}
    (out / "result.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    raise SystemExit(0 if receipt["pass"] else 1)


if __name__ == "__main__":
    main()
