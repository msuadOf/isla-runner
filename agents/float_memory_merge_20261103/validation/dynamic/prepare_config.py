#!/usr/bin/env python3
"""由正式 FD 与 memory 配置生成独立的定向混合访存配置。"""

import argparse
import hashlib
import json
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[4]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def reference(path):
    path = Path(path).resolve()
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fd", type=Path, required=True)
    parser.add_argument("--memory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    fd = args.fd.resolve(strict=True)
    memory = args.memory.resolve(strict=True)
    if args.output.exists() or args.output.with_suffix(".provenance.json").exists():
        raise ValueError("目标配置或 provenance 已存在")
    fd_data = tomllib.loads(fd.read_text())
    memory_data = tomllib.loads(memory.read_text())
    if fd_data.get("memory_regions") or not fd_data["const_primops"]["sys_enable_fdext"]:
        raise ValueError("FD 正式配置不符合叠加前提")
    regions = memory_data["memory_regions"]
    if (len(regions) != 2 or regions[0]["region_type"] != "concrete"
            or regions[1]["region_type"] != "symbolic"
            or int(regions[1]["base"], 0) != 0x80000000):
        raise ValueError("memory 正式配置区域与预期不符")
    lines = [fd.read_text(), "", "# 定向验证：保留正式 FD 配置，叠加 memory 的两块区域。",
             "# RAM 缩至 4 KiB 以约束单地址案例；此配置不能署名完整域。"]
    for region in regions:
        size = "0x1000" if region["name"] == "sym_ram" else region["size"]
        lines.extend(("[[memory_regions]]", f'name = {json.dumps(region["name"])}',
                      f'base = {json.dumps(region["base"])}', f'size = {json.dumps(size)}',
                      f'region_type = {json.dumps(region["region_type"])}', ""))
    content = "\n".join(lines) + "\n"
    parsed = tomllib.loads(content)
    if not parsed["const_primops"]["sys_enable_fdext"] or len(parsed["memory_regions"]) != 2:
        raise ValueError("叠加配置解析失败")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content)
    provenance = {"domain": "directed", "fd": {"path": reference(fd), "sha256": sha(fd)},
                  "memory": {"path": reference(memory), "sha256": sha(memory)},
                  "output": {"path": reference(args.output), "sha256": sha(args.output)},
                  "ram_size": "0x1000", "ram_region_type": "symbolic",
                  "runner_sha256": sha(Path(__file__))}
    args.output.with_suffix(".provenance.json").write_text(json.dumps(provenance, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(provenance, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
