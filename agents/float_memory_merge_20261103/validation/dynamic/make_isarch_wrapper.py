#!/usr/bin/env python3
"""仅定向 Make 验收：记录原 argv，并注入固定机器字/前态后 exec 正式 isarch。"""

import hashlib
import json
import os
from pathlib import Path
import sys


def main():
    real = Path(os.environ["FM_REAL_ISARCH"]).resolve(strict=True)
    expected = os.environ["FM_REAL_ISARCH_SHA256"]
    if hashlib.sha256(real.read_bytes()).hexdigest() != expected:
        raise ValueError("正式二进制哈希不符")
    original = sys.argv[1:]
    if original.count("solve-state") != 1 or any(arg == "--instruction-bits" for arg in original):
        raise ValueError("原 Make argv 不符或已经定向")
    point = original.index("solve-state")
    word = os.environ["FM_MACHINE_WORD"]
    prestates = json.loads(os.environ["FM_PRESTATES_JSON"])
    inserted = ["--instruction-bits", word]
    for state in prestates:
        inserted.extend(("--prestate", state))
    final = [*original[:point], *inserted, *original[point:]]
    receipt = {"original_argv": original, "inserted": inserted, "real_binary": str(real),
               "real_binary_sha256": expected, "final_argv": final}
    Path(os.environ["FM_WRAPPER_RECEIPT"]).write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    os.execv(str(real), [str(real), *final])


if __name__ == "__main__":
    main()
