#!/usr/bin/env python3
"""核查实际 IR 中溢出/changed Jump 的控制关系；旧 IR 应为红。"""
import argparse
from pathlib import Path
import re

NARROW = {
    "zriscv_f16ToI16_pure": 2,
    "zriscv_f16ToI8_pure": 2,
    "zriscv_f16ToUi8_pure": 1,
    "zriscv_f16ToUi16_pure": 1,
    "zriscv_f32ToI16_pure": 2,
    "zriscv_f32ToUi16_pure": 1,
}


def body(text, name):
    match = re.search(r"(?ms)^fn " + re.escape(name) + r"\([^\n]*\) \{\n(.*?)^\}", text)
    if not match:
        raise AssertionError(f"缺少函数 {name}")
    return [line.strip() for line in match.group(1).splitlines() if line.strip()]


def successors(lines, pc):
    line = lines[pc]
    target = re.search(r"\bgoto (\d+)", line)
    if line.startswith("jump "):
        return (pc + 1, int(target.group(1)))
    if line.startswith("goto "):
        return (int(target.group(1)),)
    if line == "end;":
        return ()
    return (pc + 1,) if pc + 1 < len(lines) else ()


def reachable(lines, start, stop=None):
    pending, seen = [start], set()
    while pending:
        pc = pending.pop()
        if pc in seen or pc == stop:
            continue
        assert 0 <= pc < len(lines), (start, pc)
        seen.add(pc)
        pending.extend(successors(lines, pc))
    return seen


def definitions(lines):
    result = {}
    for line in lines:
        match = re.match(r"(\w+) = (.*?) `", line)
        if match:
            result[match.group(1)] = match.group(2)
    return result


def depends(value, anchor, defs, seen=None):
    if value == anchor:
        return True
    seen = seen or set()
    if value in seen or value not in defs:
        return False
    seen.add(value)
    return any(depends(token, anchor, defs, seen.copy())
               for token in re.findall(r"\bzz\d+\b", defs[value]))


def branch_effect(lines, pc, pattern):
    left, right = successors(lines, pc)
    lset, rset = reachable(lines, left), reachable(lines, right)
    lonly, ronly = lset - rset, rset - lset
    # 两臂应各自到达语义写回，且目标 Jump 支配两臂写回。
    effects = [i for i, line in enumerate(lines) if re.search(pattern, line)]
    return (any(i in lonly for i in effects) and any(i in ronly for i in effects)
            and all(i not in reachable(lines, 0, pc) for i in effects if i in lonly | ronly))


def guarded_write(lines, pc, pattern):
    left, right = successors(lines, pc)
    lset, rset = reachable(lines, left), reachable(lines, right)
    effects = {i for i, line in enumerate(lines) if re.search(pattern, line)}
    pre = reachable(lines, 0, pc)
    return (bool(effects & (lset - rset)) != bool(effects & (rset - lset))
            and not effects & pre)


def check_narrow(text, name, minimum):
    lines = body(text, name)
    defs = definitions(lines)
    anchors = [var for var, rhs in defs.items() if rhs.startswith("znot_bool(")
               and any("zeq_anything" in defs.get(token, "")
                       for token in re.findall(r"\bzz\d+\b", rhs))]
    assert anchors, f"{name}: 未找到无损窄化 overflow 谓词"
    jumps = [i for i, line in enumerate(lines) if line.startswith("jump ")]
    if len(jumps) < minimum:
        raise AssertionError(f"{name}: 目标 Jump {len(jumps)}，需至少 {minimum}")
    result = re.search(r"return = (\w+) `", "\n".join(lines))
    assert result, name
    effect = r"^" + re.escape(result.group(1)) + r" = (?:struct|0x|0b|zz)"
    target = [pc for pc in jumps if any(depends(re.match(r"jump (\w+)", lines[pc]).group(1),
                                                 anchor, defs) for anchor in anchors)]
    if not target or not any(branch_effect(lines, pc, effect) for pc in target):
        raise AssertionError(f"{name}: overflow Jump 未支配两臂不同结果构造")
    if minimum == 2:
        # signed 的正/负饱和分界必须位于 overflow 臂，不能预先计算为 ITE。
        nested = any(other != pc and other in (reachable(lines, successors(lines, pc)[0])
                                             ^ reachable(lines, successors(lines, pc)[1]))
                     for pc in target for other in jumps)
        if not nested:
            raise AssertionError(f"{name}: overflow 臂内缺少正/负饱和 Jump")


def check_flags(text):
    name = "zaccrue_fflags"
    lines = body(text, name)
    defs = definitions(lines)
    # changed 是 old 与 old|flags 比较的否定；Ext_F Jump 不能冒充它。
    anchors = [var for var, rhs in defs.items() if rhs.startswith("znot_bool(")
               and any("zeq_anything" in defs.get(token, "")
                       for token in re.findall(r"\bzz\d+\b", rhs))]
    assert len(anchors) == 1, f"{name}: changed 定义不唯一"
    jumps = [(pc, re.match(r"jump (\w+) goto", line).group(1))
             for pc, line in enumerate(lines) if line.startswith("jump ")]
    candidates = [pc for pc, cond in jumps if depends(cond, anchors[0], defs)]
    if not candidates:
        raise AssertionError(f"{name}: changed 未进入目标 Jump")
    if not any(guarded_write(lines, pc, r"^zmstatus = ") for pc in candidates):
        raise AssertionError(f"{name}: changed Jump 未支配 Dirty 状态写回")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ir", type=Path, required=True)
    args = parser.parse_args()
    text = args.ir.read_text()
    failures = []
    for name, minimum in NARROW.items():
        try:
            check_narrow(text, name, minimum)
            print(f"PASS {name}")
        except AssertionError as exc:
            failures.append(str(exc))
    try:
        check_flags(text)
        print("PASS zaccrue_fflags")
    except AssertionError as exc:
        failures.append(str(exc))
    for failure in failures:
        print("FAIL " + failure)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
