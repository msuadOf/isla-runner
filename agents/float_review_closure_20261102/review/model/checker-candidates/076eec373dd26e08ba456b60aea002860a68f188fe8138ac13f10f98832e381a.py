#!/usr/bin/env python3
"""检查浮点异常、窄饱和、ROD与flags的实际IR控制关系。"""
import argparse
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
IRS = ('rv64d.ir', 'rv32d.ir', 'ir/rv64d_v128_e64.ir',
       'ir/rv64d_v256_e64.ir', 'ir/rv64d_v512_e64.ir')
NARROW = {'zriscv_f16ToI16_pure': (16, True), 'zriscv_f16ToI8_pure': (8, True),
          'zriscv_f16ToUi8_pure': (8, False), 'zriscv_f16ToUi16_pure': (16, False),
          'zriscv_f32ToI16_pure': (16, True), 'zriscv_f32ToUi16_pure': (16, False)}


def functions(text):
    return {name: [line.strip() for line in body.splitlines() if line.strip()]
            for name, body in re.findall(r'(?ms)^fn ([^(\n]+)\([^\n]*\) \{\n(.*?)^\}', text)}


def defs(lines):
    return {match.group(1): match.group(2) for line in lines
            if (match := re.match(r'(\w+) = (.*?) `', line))}


def successors(lines, pc):
    line = lines[pc]
    target = re.search(r'\bgoto (\d+)', line)
    if line.startswith('jump '):
        return (pc + 1, int(target.group(1)))
    if line.startswith('goto '):
        return (int(target.group(1)),)
    if line == 'end;':
        return ()
    return (pc + 1,) if pc + 1 < len(lines) else ()


def reachable(lines, start, stop=None):
    seen, pending = set(), [start]
    while pending:
        pc = pending.pop()
        if pc in seen or pc == stop:
            continue
        assert 0 <= pc < len(lines), (start, pc)
        seen.add(pc)
        pending.extend(successors(lines, pc))
    return seen


def jump(lines, pc):
    match = re.match(r'jump (\w+) goto (\d+)', lines[pc])
    assert match, (pc, lines[pc])
    return match.group(1), pc + 1, int(match.group(2))


def uses(value, target, definitions, seen=None):
    if value == target:
        return True
    seen = set() if seen is None else seen
    if value in seen or value not in definitions:
        return False
    seen.add(value)
    return any(uses(token, target, definitions, seen.copy())
               for token in re.findall(r'\b(?:zz\d+|zflags)\b', definitions[value]))


def resolves_to(value, pattern, definitions):
    seen = set()
    while value in definitions and value not in seen:
        seen.add(value)
        value = definitions[value]
        if re.search(pattern, value):
            return True
        alias = re.fullmatch(r'zz\d+', value)
        if not alias:
            return False
    return False


def expression(value, definitions):
    seen = set()
    while value in definitions and value not in seen:
        seen.add(value)
        value = definitions[value]
        if not re.fullmatch(r'zz\d+', value):
            break
    return value


def int_value(value, definitions):
    match = re.fullmatch(r'zz5i64zDzKz5i\((\d+)\)', expression(value, definitions))
    assert match, value
    return int(match.group(1))


def slice_of(value, converted, high, low, definitions):
    match = re.fullmatch(r'zsubrange_bits\((\w+), (\w+), (\w+)\)',
                         expression(value, definitions))
    return bool(match and expression(match.group(1), definitions) == expression(converted, definitions) and
                int_value(match.group(2), definitions) == high and
                int_value(match.group(3), definitions) == low)


def field_values(line):
    assert ' = struct ' in line or line.startswith('return = struct '), line
    values = re.findall(r'\w+ = ([^,}]+)', line.split('{', 1)[1])
    assert len(values) == 2, line
    return [value.strip() for value in values]


def check_narrow(name, lines, width, signed):
    d = defs(lines)
    converted = next(var for var, rhs in d.items()
                     if re.fullmatch(r'zz\d+\.ztuplez3z5bv5_z5bv321', rhs))
    overflows = [(var, rhs) for var, rhs in d.items() if rhs.startswith('znot_bool(')
                 and any('zeq_anything' in d.get(token, '')
                         for token in re.findall(r'\bzz\d+\b', rhs))]
    assert len(overflows) == 1, f'{name}: 无损窄化谓词不唯一'
    overflow, _ = overflows[0]
    eq = d[re.fullmatch(r'znot_bool\((\w+)\)', d[overflow]).group(1)]
    match = re.fullmatch(r'zeq_anythingzIB(32|16|24)zK\((\w+), (\w+)\)', eq)
    assert match, f'{name}: overflow比较类型变化'
    left, right = match.group(2), match.group(3)
    if signed:
        assert match.group(1) == '32', f'{name}: signed比较位宽错误'
        assert left == converted or right == converted, f'{name}: overflow未比较转换结果'
        extended = right if left == converted else left
        ext = re.fullmatch(r'zsign_extend\((\w+), (\w+)\)', expression(extended, d))
        assert ext and int_value(ext.group(1), d) == 32 and slice_of(
            ext.group(2), converted, width - 1, 0, d), f'{name}: 不是低位符号扩展回比较'
    else:
        assert int(match.group(1)) == 32 - width, f'{name}: unsigned比较位宽错误'
        upper = left if expression(left, d).startswith('zsubrange_bits(') else right
        zeros = right if upper == left else left
        assert slice_of(upper, converted, 31, width, d), f'{name}: unsigned比较的上位来源错误'
        zero = re.fullmatch(r'zzzeros\((\w+)\)', expression(zeros, d))
        assert zero and int_value(zero.group(1), d) == 32 - width, f'{name}: unsigned零扩展位宽错误'
    branches = [pc for pc, line in enumerate(lines) if line.startswith('jump ')]
    assert len(branches) == (2 if signed else 1), f'{name}: 目标Jump数量变化'
    guard = next((pc for pc in branches if uses(jump(lines, pc)[0], overflow, d)), None)
    assert guard is not None, f'{name}: overflow未进入Jump'
    _, normal, saturated = jump(lines, guard)
    end = next(i for i, line in enumerate(lines) if line.startswith('return = '))
    normal_path = reachable(lines, normal, end)
    saturated_path = reachable(lines, saturated, end)
    assert not normal_path & saturated_path, f'{name}: overflow两臂在返回前合并'
    result = re.match(r'return = (\w+)', lines[end]).group(1)
    constructors = [(i, field_values(line)) for i, line in enumerate(lines)
                    if line.startswith(result + ' = struct ')]
    normal_results = [values for i, values in constructors if i in normal_path]
    saturated_results = [values for i, values in constructors if i in saturated_path]
    assert len(normal_results) == 1, f'{name}: 正常结果出口变化'
    assert len(saturated_results) == (2 if signed else 1), f'{name}: 饱和结果出口变化'
    upstream_flags = re.search(r'(zz\d+) = zz\d+\.ztuplez3z5bv5_z5bv32[0] ', '\n'.join(lines))
    assert upstream_flags and normal_results[0][0] == upstream_flags.group(1), f'{name}: 正常flags未保留上游值'
    assert slice_of(normal_results[0][1], converted, width - 1, 0, d), \
        f'{name}: 正常结果不是转换值低{width}位'
    nv = {i: re.match(r'(\w+) = znvFlag', line).group(1)
          for i, line in enumerate(lines) if '= znvFlag(' in line}
    assert not set(nv) & normal_path, f'{name}: 正常臂提前计算NV'
    assert len(set(nv) & saturated_path) == (2 if signed else 1), f'{name}: 饱和臂NV数变化'
    for values in saturated_results:
        assert values[0] in nv.values(), f'{name}: 饱和flags不是仅NV'
    if signed:
        sign = next(pc for pc in branches if pc != guard)
        assert sign in saturated_path and sign not in normal_path, f'{name}: 符号Jump不在overflow真臂'
        condition, positive, negative = jump(lines, sign)
        comparison = d.get(condition, '')
        assert re.fullmatch(r'zeq_anythingzIB1zK\((\w+), 0b1\)', comparison), f'{name}: 符号条件变化'
        bit = re.fullmatch(r'zeq_anythingzIB1zK\((\w+), 0b1\)', comparison).group(1)
        bit_access = re.fullmatch(r'zbitvector_access\((\w+), (\w+)\)', expression(bit, d))
        assert bit_access and expression(bit_access.group(1), d) == expression(converted, d) and \
            int_value(bit_access.group(2), d) == 31, f'{name}: 未取转换结果sign bit31'
        pos_path = reachable(lines, positive, end)
        neg_path = reachable(lines, negative, end)
        limit = (1 << (width - 1)) - 1
        expected = {f'0x{limit:0{width // 4}X}', f'0x{1 << (width - 1):0{width // 4}X}'}
        actual = {values[1] for values in saturated_results}
        assert actual == expected, f'{name}: 正/负饱和端点错误 {actual}'
        assert any(values[1] == f'0x{limit:0{width // 4}X}' and i in pos_path
                   for i, values in constructors), f'{name}: 正端点不在非负臂'
        assert any(values[1] == f'0x{1 << (width - 1):0{width // 4}X}' and i in neg_path
                   for i, values in constructors), f'{name}: 负端点不在负号臂'
    else:
        ones = re.fullmatch(r'zones\((\w+)\)', expression(saturated_results[0][1], d))
        assert ones and int_value(ones.group(1), d) == width, f'{name}: unsigned饱和端点不是全1'
    return len(branches)


def check_flags(lines):
    d = defs(lines)
    old = next(var for var, rhs in d.items() if rhs.startswith('z_get_Fcsr_FFLAGS('))
    joined = next(var for var, rhs in d.items() if rhs.startswith('zor_vec('))
    operands = re.fullmatch(r'zor_vec\((\w+), (\w+)\)', d[joined])
    assert operands and any(uses(x, old, d) for x in operands.groups()) and any(
        uses(x, 'zflags', d) for x in operands.groups()), 'flags: old|new来源变化'
    eq = next((var for var, rhs in d.items() if
               (match := re.fullmatch(r'zeq_anythingzIB5zK\((\w+), (\w+)\)', rhs)) and
               ((uses(match.group(1), old, d) and uses(match.group(2), joined, d)) or
                (uses(match.group(2), old, d) and uses(match.group(1), joined, d)))), None)
    assert eq is not None, 'flags: changed未比较old与old|flags'
    changed = next(var for var, rhs in d.items() if rhs == f'znot_bool({eq})')
    branches = [pc for pc, line in enumerate(lines) if line.startswith('jump ')]
    guard = next((pc for pc in branches if uses(jump(lines, pc)[0], changed, d)), None)
    assert guard is not None, 'flags: changed没有目标Jump'
    _, unchanged, changed_arm = jump(lines, guard)
    writes = {i for i, line in enumerate(lines) if line.startswith('zmstatus.zbits = ')}
    assert len(writes) == 1, 'flags: mstatus写回数变化'
    assert not writes & reachable(lines, unchanged) and writes & reachable(lines, changed_arm), \
        'flags: changed未支配Dirty写回'
    fs = next(i for i, line in enumerate(lines) if '= z_update_Mstatus_FS(' in line)
    sd = next(i for i, line in enumerate(lines) if '= z_update_Mstatus_SD(' in line)
    assert fs < sd < next(iter(writes)) and all(i in reachable(lines, changed_arm)
                                              for i in (fs, sd)), 'flags: FS/SD更新链错误'
    fs_value = re.search(r'z_update_Mstatus_FS\((\w+), (\w+)\)', lines[fs])
    assert fs_value and resolves_to(fs_value.group(2), r'zextStatus_to_bits\(zDirty\)', d), \
        'flags: FS未置Dirty'
    sd_value = re.search(r'(\w+) = z_update_Mstatus_SD\((\w+), (\w+)\)', lines[sd])
    assert sd_value and sd_value.group(2) == re.match(r'(\w+) = ', lines[fs]).group(1) and \
        sd_value.group(3) == '0b1', 'flags: SD未在FS更新后置1'
    assert lines[next(iter(writes))].startswith('zmstatus.zbits = ' + sd_value.group(1) + '.zbits'), \
        'flags: 写回未采用FS/SD更新结果'
    ext_f = next((pc for pc in branches if pc != guard and
                  'zhartSupports(zExt_F)' in d.get(jump(lines, pc)[0], '')), None)
    assert ext_f is not None and ext_f in reachable(lines, changed_arm) and \
        next(iter(writes)) in reachable(lines, jump(lines, ext_f)[2]) and \
        next(iter(writes)) not in reachable(lines, jump(lines, ext_f)[1]), \
        'flags: Ext_F真臂没有支配状态写回'
    callbacks = [i for i, line in enumerate(lines) if 'zcsr_name_write_callback(' in line]
    assert len(callbacks) == 2 and all(i in reachable(lines, unchanged) and
                                      i in reachable(lines, changed_arm) for i in callbacks), \
        'flags: 两回调不在合流后'
    return len(branches)


def check_exception(name, lines, role_count, minimum):
    calls = [i for i, line in enumerate(lines) if '= zieee_operand_invalid(' in line]
    jumps = [i for i, line in enumerate(lines) if line.startswith('jump ')]
    assert len(calls) == role_count and len(jumps) >= minimum, f'{name}: 源或原因分界数量变化'
    assert calls[-1] < jumps[0], f'{name}: 源分类被原因Jump短路'
    assert all(i in reachable(lines, 0, pc) for i in calls for pc in jumps), \
        f'{name}: 源分类未支配原因Jump'
    finite = jumps[-1]
    _, skipped, active = jump(lines, finite)
    limited = [i for i, line in enumerate(lines) if re.search(
        r'= zfp(?:16|32|64)_(?:from_ieee|to_fp|add|sub|mul|div|sqrt|fma)\(|= zieee_f(?:16|32|64)_rounded_exceptions\(', line)]
    assert limited and all(i in reachable(lines, active) and i not in reachable(lines, skipped)
                           for i in limited), f'{name}: 有限舍入计算未受finite gate支配'
    assert not any(i < jumps[0] for i in limited), f'{name}: 特殊值路径提前计算有限舍入'
    return len(jumps)


def check_operand_order(name, lines, role_count):
    calls = [i for i, line in enumerate(lines) if '= zieee_operand_invalid(' in line]
    jumps = [i for i, line in enumerate(lines) if line.startswith('jump ')]
    assert len(calls) == role_count, f'{name}: 源角色调用数变化'
    if jumps:
        assert calls[-1] < jumps[0], f'{name}: 源角色在行为Jump之后才分类'
        assert all(i in reachable(lines, 0, pc) for i in calls for pc in jumps), \
            f'{name}: 某个行为Jump绕过源分类'
    return len(calls)


def check(text, path):
    f = functions(text)
    results = {}
    results['accrue_fflags'] = check_flags(f['zaccrue_fflags'])
    for name, (width, signed) in NARROW.items():
        results[name] = check_narrow(name, f[name], width, signed)
    for width in (16, 32, 64):
        for op, roles, jumps in (('add', 2, 2), ('sub', 2, 2), ('mul', 2, 3),
                                 ('div', 2, 4), ('sqrt', 1, 2), ('fma', 3, 4)):
            name = f'zieee_{op}{width}_exceptions'
            results[name] = check_exception(name, f[name], roles, jumps)
    print(f'PASS {path}: {len(results)}个目标函数的实际条件、出口与支配关系')
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ir', type=Path, action='append')
    args = parser.parse_args()
    for path in args.ir or [ROOT / name for name in IRS]:
        check(path.read_text(), path)


if __name__ == '__main__':
    main()
