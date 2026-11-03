"""重映射本次模型合流的 19 份执行预算，并记录两侧 region 来源。"""

from __future__ import annotations

import difflib
import json
from pathlib import Path
import re
import subprocess
import tomllib

ROOT = Path(__file__).resolve().parents[4]
MODEL = ROOT / ".worktree/merge-float-memory-20261104/sail-riscv"
CONFIG = "configs/isla/workarounds"
MEMORY = "c70482a73be2a67c5a89d88b1e6c2bbea224940c"
FLOAT = "0f7b8fbc6724103f91f929ef6918f123df75d6c9"
OUT = Path(__file__).with_name("region-map.json")
REGION = re.compile(r"(?m)^\[\[execution_limits\.region_fork_limits\]\]\n")
NUMBER = re.compile(r"(?m)^(start_line|start_column|end_line|end_column) = (\d+)$")
ANCHOR = re.compile(r"(?m)^(# Sail (?:start|end)\s+)(\d+)(:.*)$")


def show(commit: str, path: str) -> str:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=MODEL, text=True)


class Mapper:
    def __init__(self, side: str, source: str):
        self.old = show(side, "model/" + source).splitlines()
        self.new = (MODEL / "model" / source).read_text().splitlines()
        self.equal = {}
        self.opcodes = difflib.SequenceMatcher(None, self.old, self.new, autojunk=False).get_opcodes()
        for tag, a0, a1, b0, b1 in self.opcodes:
            if tag == "equal":
                self.equal.update((a + 1, b + 1) for a, b in zip(range(a0, a1), range(b0, b1)))

    def line(self, old_line: int, edge: str = "start") -> int:
        if old_line in self.equal:
            return self.equal[old_line]
        old_text = self.old[old_line - 1]
        before = max((n for n in self.equal if n < old_line), default=0)
        after = min((n for n in self.equal if n > old_line), default=len(self.old) + 1)
        guess = self.equal[before] + old_line - before if before else self.equal[after] - (after - old_line)
        candidates = [i + 1 for i, line in enumerate(self.new) if line == old_text]
        near = [n for n in candidates if abs(n - guess) <= 30]
        if near:
            return min(near, key=lambda n: abs(n - guess))
        if 1 <= guess <= len(self.new) and self.new[guess - 1].strip() == old_text.strip():
            return guess
        for tag, a0, a1, b0, b1 in self.opcodes:
            if a0 < old_line <= a1 and tag == "replace" and b1 > b0:
                return b0 + 1 if edge == "start" else b1
        raise ValueError(f"cannot map {old_line}: {old_text!r}; nearest {guess}")


def sections(raw: str):
    matches = list(REGION.finditer(raw))
    header = raw[: matches[0].start()]
    raw_blocks = [raw[m.start() : matches[i + 1].start() if i + 1 < len(matches) else len(raw)] for i, m in enumerate(matches)]
    blocks = []
    carry = ""
    for i, block in enumerate(raw_blocks):
        assignments = list(re.finditer(r"(?m)^[a-z_]+ = .*\n?", block))
        assert assignments, block
        last = assignments[-1].end()
        body, trailing = block[:last], block[last:]
        if i == 0:
            blocks.append(body)
        else:
            blocks.append(carry + body)
        carry = trailing
    if carry:
        blocks[-1] += carry
    return header, blocks


def region(block: str) -> dict:
    return tomllib.loads("[execution_limits]\n" + block)["execution_limits"]["region_fork_limits"][0]


def key(item: dict) -> tuple:
    return tuple(sorted((k, v) for k, v in item.items() if k != "max_forks_per_region"))


def main():
    conflicts = (list(json.loads(OUT.read_text())) if OUT.exists() else
                 subprocess.check_output(["git", "diff", "--name-only", "--diff-filter=U"], cwd=MODEL, text=True).splitlines())
    assert len(conflicts) == 19, conflicts
    mappers = {}
    report = {}
    for path in conflicts:
        assert path.startswith(CONFIG + "/"), path
        sides = {}
        for label, commit in (("memory", MEMORY), ("float", FLOAT)):
            header, blocks = sections(show(commit, path))
            side_items = []
            for index, block in enumerate(blocks, 1):
                old = region(block)
                if label == "float" and path.endswith(("vexttype.toml", "vxtype.toml")) and old["file"] == "extensions/V/vext_utils_insts.sail" and old["start_line"] == 284:
                    side_items.append({"index": index, "original": old, "mapped": None, "merged_index": None, "decision": "retired: memory get_start_element is direct nat without old trap branch"})
                    continue
                source = old["file"]
                mapper = mappers.setdefault((commit, source), Mapper(commit, source))
                mapped = dict(old)
                for field in ("start_line", "end_line"):
                    mapped[field] = mapper.line(old[field], "start" if field == "start_line" else "end")
                for edge in ("start", "end"):
                    old_line = old[edge + "_line"]
                    new_line = mapped[edge + "_line"]
                    if mapper.old[old_line - 1] != mapper.new[new_line - 1]:
                        mapped[edge + "_column"] = 2 if edge == "start" else len(mapper.new[new_line - 1]) + 1
                if path.endswith("vexttype.toml") and source == "extensions/V/vext_utils_insts.sail" and old["start_line"] == 46:
                    mapped["end_line"] = 47
                    mapped["end_column"] = len(mapper.new[46]) + 1
                if not ((mapped["start_line"], mapped["start_column"]) < (mapped["end_line"], mapped["end_column"])):
                    raise ValueError((path, label, index, old, mapped))
                for field in ("start", "end"):
                    n = mapped[field + "_line"]
                    c = mapped[field + "_column"]
                    if c < 1 or c > len(mapper.new[n - 1]) + 1:
                        raise ValueError((path, label, index, field, n, c, mapper.new[n - 1]))
                def number_match(match):
                    return f'{match.group(1)} = {mapped[match.group(1)]}'
                updated = NUMBER.sub(number_match, block)
                def anchor_match(match):
                    old_line = int(match.group(2))
                    new_line = mapper.line(old_line)
                    anchor_text = match.group(3)[1:].strip()
                    if mapper.new[new_line - 1].strip() != anchor_text:
                        candidates = [i + 1 for i, line in enumerate(mapper.new) if line.strip() == anchor_text]
                        if not candidates:
                            raise ValueError((path, label, old_line, anchor_text))
                        new_line = min(candidates, key=lambda n: abs(n - new_line))
                    return match.group(1) + str(new_line) + match.group(3)
                updated = ANCHOR.sub(anchor_match, updated)
                side_items.append({"index": index, "original": old, "mapped": mapped, "block": updated})
            sides[label] = {"header": header, "items": side_items}
        selected = []
        keys = {}
        for label in ("memory", "float"):
            for item in sides[label]["items"]:
                if item["mapped"] is None:
                    continue
                k = key(item["mapped"])
                if k not in keys:
                    keys[k] = len(selected) + 1
                    selected.append(item["block"])
                item["merged_index"] = keys[k]
                item["decision"] = "new region" if keys[k] == len(selected) and (label == "memory" or k not in {key(x["mapped"]) for x in sides["memory"]["items"] if x["mapped"] is not None}) else "same mapped region"
                if label == "float" and k in {key(x["mapped"]) for x in sides["memory"]["items"] if x["mapped"] is not None}:
                    original = next(x for x in sides["memory"]["items"] if x["mapped"] is not None and key(x["mapped"]) == k)
                    if original["mapped"] != item["mapped"]:
                        item["decision"] = "same source region; retain target memory budget"
        # Memory header keeps the fixed target's purpose and parameters; float-only regions follow.
        final = sides["memory"]["header"] + "".join(selected)
        def remap_anchor(match):
            rest = final[match.end():]
            source_match = re.search(r'(?m)^file = "([^"]+)"', rest)
            assert source_match is not None, path
            source = source_match.group(1)
            lines = (MODEL / "model" / source).read_text().splitlines()
            target_match = re.search(r'(?m)^' + ("start_line" if "start" in match.group(1) else "end_line") + r' = (\d+)', rest)
            target = int(target_match.group(1)) if target_match else int(match.group(2))
            content = match.group(3)[1:].strip()
            candidates = [i + 1 for i, line in enumerate(lines) if line.strip() == content]
            if not candidates:
                raise ValueError((path, source, content))
            chosen = min(candidates, key=lambda n: abs(n - target))
            return match.group(1) + str(chosen) + match.group(3)
        final = ANCHOR.sub(remap_anchor, final)
        if path.endswith("mvvtype.toml"):
            final = final.replace(
                "# 未限制的基线在 1686、1694、1702、1709 行持续产生新路径。区域预算为 0 后，\n# 这些数据相关分支在该循环内进行确定性采样，而循环外的指令与运行态分派不受影响。",
                "# 历史基线在除法与余数 arm 的逐 lane 判断上持续产生新路径。区域预算为 1，\n# 限制同一路径在该循环内重复 fork；循环外的指令与运行态分派不受影响。")
        if path.endswith("vexttype.toml"):
            final = final.replace("合法性/起始元素 helper", "合法性 helper")
            final = final.replace("# get_start_element已改为直接读取vstart，无旧陷阱分支需要限制。",
                                  "# get_start_element 已改为直接读取 vstart，旧陷阱分支不再设 region。\n# 以下仅限制 execute 内按 num_elem 展开的逐 lane 循环。")
        if path.endswith("vxtype.toml"):
            final = final.replace("也不覆盖 571 行的 funct6 分派。", "也不覆盖 funct6 分派。")
            final = final.replace("# init_masked_result 调用的 vstart 合法上界检查。带现有逐 lane 限制的\n# 60 秒 ITRACE 中，该比较仍累计 33 次 fork；最慢的多条已完成路径均在这里\n# 花费 23-30 秒后走 Err/Illegal。只限制这个比较，不固定 vstart 的具体值。",
                                  "# memory 的 get_start_element 直接返回 nat，旧 vstart 陷阱分支已删除。\n# 下方从 VX_VSADDU 的逐 lane mask/saturation 分支开始。")
        if path.endswith("vvtype.toml"):
            final = final.replace("# 配置终点使用紧随函数后的空行 634:1。", "# 配置终点使用紧随函数后的空行 682:1。")
        tomllib.loads(final)
        (MODEL / path).write_text(final)
        report[path] = {
            "memory_regions": len(sides["memory"]["items"]),
            "float_regions": len(sides["float"]["items"]),
            "merged_regions": len(selected),
            "mapping": {label: [{k: v for k, v in item.items() if k != "block"} for item in sides[label]["items"]] for label in ("memory", "float")},
        }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"mapped {len(report)} configurations, {sum(v['merged_regions'] for v in report.values())} regions")


if __name__ == "__main__":
    main()
