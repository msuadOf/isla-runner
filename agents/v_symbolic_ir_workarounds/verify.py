"""校验正式 IR、严格 workaround 与 Sail 源码位置的一致性。"""

import argparse
import hashlib
from pathlib import Path
import re
import tomllib


ROOT = Path(__file__).resolve().parents[2]
ISLA = ROOT / "isla"
SAIL = ROOT / "sail-riscv/model"
MOVED_FILES = {"vext_arith_insts.sail", "vext_control.sail", "vext_utils_insts.sail"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ir", type=Path, default=ISLA / "rv64d.ir")
    args = parser.parse_args()
    digest = hashlib.sha256(args.ir.read_bytes()).hexdigest()
    configs = sorted((ISLA / "configs/workarounds").glob("*.toml"))
    assert len(configs) == 79, len(configs)
    regions = 0
    anchors = 0
    errors = []

    for path in configs:
        raw = path.read_text()
        config = tomllib.loads(raw)["execution_limits"]
        if config["strict"] is not True or config["ir_sha256"] != digest:
            errors.append(f"{path.name}: strict/hash 与 {args.ir} 不一致")
        for region in config.get("region_fork_limits", []):
            source = SAIL / region["file"]
            if source.name not in MOVED_FILES:
                continue
            lines = source.read_text().splitlines()
            start = (region["start_line"], region["start_column"])
            end = (region["end_line"], region["end_column"])
            regions += 1
            if not (1 <= start[0] <= len(lines) and 1 <= end[0] <= len(lines)):
                errors.append(f"{path.name}: {source.name} 行号越界 {start}..{end}")
                continue
            if not (start < end and 1 <= start[1] <= len(lines[start[0] - 1]) + 1
                    and 1 <= end[1] <= len(lines[end[0] - 1]) + 1):
                errors.append(f"{path.name}: {source.name} 区间无效 {start}..{end}")
        for match in re.finditer(r"(?m)^# Sail (?:start|end)\s+(\d+):\s*(.*)$", raw):
            following = raw[match.end():]
            source_match = re.search(r'(?m)^file = "([^"]+)"', following)
            assert source_match is not None, path
            source = SAIL / source_match.group(1)
            line_number = int(match.group(1))
            lines = source.read_text().splitlines()
            anchors += 1
            if line_number > len(lines) or lines[line_number - 1].strip() != match.group(2).strip():
                errors.append(f"{path.name}: 注释锚点 {source.name}:{line_number} 不符")

    assert not errors, "\n".join(errors)
    print(f"通过：{len(configs)} 份严格配置、{regions} 个源码 region、{anchors} 处注释锚点，IR SHA-256 {digest}")


if __name__ == "__main__":
    main()
