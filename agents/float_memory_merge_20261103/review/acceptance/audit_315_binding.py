#!/usr/bin/env python3
"""独立重建 315 受约束 IR，核实际输入、来源、前后态保持与双预算。"""
import argparse
import hashlib
import json
import re
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PARTIAL = ("errors", "execution-timeouts", "smt-timeouts", "unfinished-paths",
           "assertion-filtered-paths", "omitted-cases", "model-query-timeouts",
           "encoding-filtered-paths", "pending-batches", "sampled-paths")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def number(value):
    if isinstance(value, int):
        return value
    match = re.fullmatch(r"\d+'h([0-9a-fA-F_]+)", value)
    return int(match[1].replace("_", ""), 16) if match else int(value, 0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    inputs, launch, summary = read(args.inputs), read(args.run / "launch.json"), read(args.run / "summary.json")
    assert launch["input_sha256"] == sha(args.inputs)
    assert launch["count"] == summary["count"] == summary["completed"] == summary["pass"] == 315
    assert launch["seed"] == 17 and launch["threads"] == 1 and launch["tactic"] == "qffp"
    for key in ("model_commit", "isla_commit"):
        assert launch["source"][key] == inputs[key]
    for key in ("binary", "ir", "config", "z3"):
        assert sha(Path(inputs[key]["path"])) == inputs[key]["sha256"] == launch["hashes"][key]
    for key, filename in (("binary", "isarch"), ("ir", "base.ir"), ("config", "base-config.toml"), ("preload", "seed_control.so")):
        assert sha(args.run / filename) == launch["hashes"][key]
    assert launch["hashes"]["expected"] == "6ed44d0afba816a709fe6f4f18f0e34505c8b3202aaed6e1ad306e5aea135891"
    expected = read(ROOT / "agents/float_memory_merge_20261103/validation/dynamic/expected-315.json")
    names = {row["name"] for group in ("cases", "vectors", "bf16") for row in expected[group]}
    assert set(launch["names"]) == names and len(names) == 315
    source = (args.run / "base.ir").read_text()
    rows, seen, preserved, initial_count = [], set(), 0, 0
    for recorded in summary["results"]:
        name = recorded["name"]
        assert name not in seen
        seen.add(name)
        jobdir = args.run / "runs" / name
        result, command = read(jobdir / "result.json"), read(jobdir / "command.json")
        assert all(recorded[key] == value for key, value in result.items())
        assert set(recorded) - set(result) <= {"extra_partial_zero"}
        assert recorded.get("extra_partial_zero", True) is True
        assert result["status"] == "PASS" and result["exit_code"] == 0
        constructor = "z" + command["job"]["clause"]
        struct = re.search(r"  " + constructor + r": %struct (\w+),", source)[1]
        fields = re.findall(r"\n  (\w+): ([^,\n]+)", re.search(r"struct " + struct + r" \{(.*?)\n\}", source, re.S)[1])
        assert len(fields) == len(command["job"]["fields"])
        lines = []
        for index, ((field, ty), value) in enumerate(zip(fields, command["job"]["fields"])):
            literal = "0b" + format(value, "0" + ty[3:] + "b") if isinstance(value, int) else value
            lines.extend([f"  exception_cond{index} : %bool;", f"  exception_unit{index} : %unit;",
                          f"  exception_cond{index} = @eq(zmergez3var as {constructor}.{field}, {literal});",
                          f"  exception_unit{index} = $zsail_assume(exception_cond{index});"])
        marker = "fn zexecute(zmergez3var) {\n"
        assert source.count(marker) == 1
        replacement = ("val zexception_original_execute : (%union zinstruction) -> %union zExecutionResult\n\n"
                       + marker + "\n".join(lines)
                       + "\n  return = zexception_original_execute(zmergez3var);\n  end;\n}\n\nfn zexception_original_execute(zmergez3var) {\n")
        rebuilt = hashlib.sha256(source.replace(marker, replacement, 1).encode()).hexdigest()
        assert rebuilt == command["constrained_ir_sha256"]
        outputs = list((jobdir / "output").glob("*.json"))
        assert len(outputs) == 1 and sha(outputs[0]) == result["output_sha256"]
        data = read(outputs[0])
        assert data["summary"]["status"] == "finished" and all(data["summary"][key] == 0 for key in PARTIAL)
        assert len(data["gen"]) == 1
        for key, row in data["provenance"]["inputs"].items():
            assert (rebuilt if key == "-A" else sha(Path(row["path"]))) == row["sha256"]
        argv = command["argv"]
        assert argv[argv.index("-T") + 1] == "1"
        assert argv[argv.index("--smt-timeout") + 1] == str(launch["timeout_seconds"]) + "s"
        assert argv[argv.index("--tastic") + 1] == "qffp"
        assert str(launch["timeout_seconds"]) + "s" in argv[:6]
        assert sha(jobdir / "config.toml") == command["config_sha256"]
        seedlog = jobdir / "seed-intercept.log"
        assert sha(seedlog) == result["seed_log_sha256"]
        seedlines = seedlog.read_text().splitlines()
        assert seedlines and all(re.fullmatch(r"parameter=(?:seed|random_seed) original=\d+ fixed=17", line) for line in seedlines)
        entry = data["gen"][0]
        pre, post = entry["isa-state-complete"], entry["isa-state-post"]
        configured = tomllib.loads((jobdir / "config.toml").read_text())["initial_state"]
        for key, value in command["job"]["initial"].items():
            assert number(pre[key]) == number(value) == number(configured[key]), (name, key)
            initial_count += 1
        word = number(entry["test-ins-encdec"])
        rd, opcode = word >> 7 & 31, word & 127
        dest = ("vr" if opcode == 0x57 else "x" if opcode == 0x53 and (word >> 25 & ~3) == 96 else "f") + str(rd)
        for key in pre:
            if key not in (dest, "mstatus", "fcsr", "vstart"):
                assert post[key] == pre[key], (name, key)
                preserved += 1
        assert number(post["mstatus"]) == number(pre["mstatus"]) | 0x6000 | (1 << 63)
        assert number(post["vstart"]) == (0 if opcode == 0x57 else number(pre["vstart"]))
        rows.append({"name": name, "json_sha256": sha(outputs[0]), "constrained_ir_sha256": rebuilt})
    assert seen == names
    output = {"scope": "315新JSON的实际来源/重建IR/seed/初态与保持状态；数值由独立SoftFloat另核",
              "launch_sha256": sha(args.run / "launch.json"), "inputs_sha256": sha(args.inputs),
              "count": len(rows), "initial_values": initial_count, "preserved_fields": preserved, "rows": rows, "pass": True}
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({key: value for key, value in output.items() if key != "rows"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
