#!/usr/bin/env python3
"""Generate strict SYMBOLIC IR from the frozen old source plus activity gate."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import os
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
MODEL = HERE / "model"
OUT = HERE / os.environ.get("ISLA_OLD_GATE_OUTPUT", "generation")
SAIL = ROOT / "isla/target/float-solve-evidence/unified-backend-build/toolchain-a198-v2-20260927/sail-src/sail"
PLUGIN = ROOT / ".tmp/float-full-trace-20260929/fvv-branch-candidate/sail_plugin_isla.cmxs"
CONFIG = ROOT / "isla/ir/provenance/rv64d.json"
PRESERVE = ("encdec_compressed_forwards", "encdec_compressed_forwards_matches",
            "encdec_compressed_backwards", "encdec_compressed_backwards_matches",
            "get_F", "set_F", "set_V", "riscv_f16ToI16", "riscv_f16ToUi16",
            "riscv_f32ToI16", "riscv_f32ToUi16")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


OUT.mkdir(exist_ok=True)
assert not (OUT / "launch.json").exists(), "generation output already used"
sources = {str(path.relative_to(MODEL)): sha(path) for path in MODEL.rglob("*") if path.is_file()}
cmd = ["taskset", "-c", "108", str(SAIL), "-plugin", str(PLUGIN), "-isla",
       "-D", "SYMBOLIC", "--strict-var", "--strict-bitvector",
       "--strict-exponentials", "--require-version", "0.20.1",
       "--memo-z3-path", str(OUT / "sail_smt_cache"), "--all-modules"]
for name in PRESERVE:
    cmd += ["--isla-preserve", name]
cmd += ["--isla-output-dir", str(OUT), "--config", str(CONFIG),
        "-o", "rv64d_v128_e64", "riscv.sail_project"]
record = {"command": cmd, "utc_start": dt.datetime.now(dt.timezone.utc).isoformat(),
          "cpu": 108, "config_sha256": sha(CONFIG), "plugin_sha256": sha(PLUGIN),
          "sail_sha256": sha(SAIL), "sources_sha256": sources}
start = time.monotonic()
with (OUT / "generation.log").open("w") as log:
    proc = subprocess.Popen(cmd, cwd=MODEL, stdout=log, stderr=subprocess.STDOUT,
                            start_new_session=True)
    record["pid"] = proc.pid
    (OUT / "launch.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({"pid": proc.pid, "cpu": 108}), flush=True)
    record["exit_code"] = proc.wait()
record.update(elapsed_s=time.monotonic() - start,
              utc_end=dt.datetime.now(dt.timezone.utc).isoformat(),
              sources_unchanged=all(sha(MODEL / path) == digest for path, digest in sources.items()))
ir = OUT / "rv64d_v128_e64.ir"
if ir.exists():
    record["ir_sha256"] = sha(ir)
(OUT / "result.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps({"exit_code": record["exit_code"],
                  "elapsed_s": record["elapsed_s"],
                  "ir_sha256": record.get("ir_sha256")}), flush=True)
