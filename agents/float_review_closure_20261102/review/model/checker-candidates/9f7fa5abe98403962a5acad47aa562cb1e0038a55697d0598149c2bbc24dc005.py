#!/usr/bin/env python3
"""检查浮点异常、窄饱和、ROD与flags的实际IR控制关系。"""
import argparse
from collections import Counter
from itertools import product
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
IRS = ('rv64d.ir', 'rv32d.ir', 'ir/rv64d_v128_e64.ir',
       'ir/rv64d_v256_e64.ir', 'ir/rv64d_v512_e64.ir')
NARROW = {'zriscv_f16ToI16_pure': (16, True), 'zriscv_f16ToI8_pure': (8, True),
          'zriscv_f16ToUi8_pure': (8, False), 'zriscv_f16ToUi16_pure': (16, False),
          'zriscv_f32ToI16_pure': (16, True), 'zriscv_f32ToUi16_pure': (16, False)}
EXCEPTION_CALLS = {
    'add': ((('inf', 'a'), ('inf', 'b')),
            (('finite', 'a'), ('finite', 'b'))),
    'sub': ((('inf', 'a'), ('inf', 'b')),
            (('finite', 'a'), ('finite', 'b'))),
    'mul': ((('zzero', 'a'), ('inf', 'b')),
            (('inf', 'a'), ('zzero', 'b')),
            (('finite', 'a'), ('finite', 'b'))),
    'div': ((('zzero', 'a'), ('zzero', 'b')),
            (('inf', 'a'), ('inf', 'b')),
            (('finite', 'a'), ('zzero', 'a'), ('zzero', 'b')),
            (('finite', 'a'), ('finite', 'b'), ('zzero', 'b'))),
    'sqrt': ((('nan', 'a'), ('zzero', 'a')),
             (('finite', 'a'), ('zzero', 'a'), ('zzero', 'a'))),
    'fma': ((('zzero', 'a'), ('inf', 'b')),
            (('inf', 'a'), ('zzero', 'b')),
            (('inf', 'c'), ('zzero', 'a'), ('nan', 'a'), ('inf', 'b'),
             ('zzero', 'b'), ('nan', 'b'), ('inf', 'a')),
            (('finite', 'a'), ('finite', 'b'), ('finite', 'c'))),
}


def representative_values(width):
    exponent_width = {16: 5, 32: 8, 64: 11}[width]
    fraction_width = width - exponent_width - 1
    inf = ((1 << exponent_width) - 1) << fraction_width
    normal = ((1 << (exponent_width - 1)) - 1) << fraction_width
    base = (normal, 1, 0, inf, inf | 1, inf | (1 << (fraction_width - 1)))
    return tuple(value | sign << (width - 1) for value in base for sign in (0, 1))


def classify(value, width):
    exponent_width = {16: 5, 32: 8, 64: 11}[width]
    fraction_width = width - exponent_width - 1
    exponent = (value >> fraction_width) & ((1 << exponent_width) - 1)
    fraction = value & ((1 << fraction_width) - 1)
    nan = exponent == (1 << exponent_width) - 1 and fraction != 0
    inf = exponent == (1 << exponent_width) - 1 and fraction == 0
    zero = exponent == 0 and fraction == 0
    return {'sign': bool(value >> (width - 1)), 'nan': nan,
            'inf': inf, 'zero': zero, 'finite': not nan and not inf}


def arguments(expression_text):
    parts, current, level = [], '', 0
    for char in expression_text:
        if char == ',' and level == 0:
            parts.append(current.strip())
            current = ''
            continue
        current += char
        if char == '(':
            level += 1
        elif char == ')':
            level -= 1
    parts.append(current.strip())
    assert level == 0
    return parts


def evaluate(value, definitions, values, width):
    if value in values:
        return values[value]
    if value == 'true':
        return True
    if value == 'false':
        return False
    if value.startswith('0b'):
        return int(value[2:], 2)
    if value not in definitions:
        raise AssertionError(f'布尔谓词含未知变量 {value}')
    rhs = definitions[value]
    if re.fullmatch(r'zz\d+|za|zb|zc', rhs):
        return evaluate(rhs, definitions, values, width)
    match = re.fullmatch(r'(\w+)\((.*)\)', rhs)
    assert match, f'未知布尔表达式 {rhs}'
    op, raw = match.groups()
    if op == 'zz5i64zDzKz5i':
        return int(raw)
    args = [evaluate(arg, definitions, values, width) for arg in arguments(raw)]
    if op == 'zbitvector_access':
        return (args[0] >> args[1]) & 1
    if op.startswith('zeq_anything'):
        return args[0] == args[1]
    if op == 'zstrict_and_bool':
        return bool(args[0]) and bool(args[1])
    if op == 'zstrict_or_bool':
        return bool(args[0]) or bool(args[1])
    if op == 'znot_bool':
        return not args[0]
    if op.startswith('zieee_is_'):
        category = op.removeprefix('zieee_is_').replace('zzero', 'zero')
        assert category in ('nan', 'inf', 'zero', 'finite')
        return classify(args[0], width)[category]
    raise AssertionError(f'未支持的原因谓词操作 {op}')


def expected_exception_guards(op, raw, width):
    a = classify(raw[0], width)
    b = classify(raw[1], width) if len(raw) > 1 else None
    c = classify(raw[2], width) if len(raw) > 2 else None
    if op == 'add':
        return (a['inf'] and b['inf'] and a['sign'] != b['sign'],
                a['finite'] and b['finite'])
    if op == 'sub':
        return (a['inf'] and b['inf'] and a['sign'] == b['sign'],
                a['finite'] and b['finite'])
    if op == 'mul':
        return (a['zero'] and b['inf'], a['inf'] and b['zero'],
                a['finite'] and b['finite'])
    if op == 'div':
        return (a['zero'] and b['zero'], a['inf'] and b['inf'],
                a['finite'] and not a['zero'] and b['zero'],
                a['finite'] and b['finite'] and not b['zero'])
    if op == 'sqrt':
        negative_nonzero = a['sign'] and not a['zero']
        return (not a['nan'] and negative_nonzero,
                a['finite'] and not negative_nonzero or a['zero'])
    if op == 'fma':
        product_inf = (a['inf'] and not b['nan'] and not b['zero'] or
                       b['inf'] and not a['nan'] and not a['zero'])
        return (a['zero'] and b['inf'], a['inf'] and b['zero'],
                product_inf and c['inf'] and ((a['sign'] != b['sign']) != c['sign']),
                a['finite'] and b['finite'] and c['finite'])
    raise AssertionError(op)


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
    assert operands and {expression(x, d) for x in operands.groups()} == {
        expression(old, d), 'zflags'}, 'flags: old|new来源变化'
    eq = next((var for var, rhs in d.items() if
               (match := re.fullmatch(r'zeq_anythingzIB5zK\((\w+), (\w+)\)', rhs)) and
               {expression(x, d) for x in match.groups()} ==
               {expression(old, d), expression(joined, d)}), None)
    assert eq is not None, 'flags: changed未比较old与old|flags'
    changed = next(var for var, rhs in d.items() if rhs == f'znot_bool({eq})')
    branches = [pc for pc, line in enumerate(lines) if line.startswith('jump ')]
    guard = next((pc for pc in branches if jump(lines, pc)[0] == changed), None)
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
    check_operand_order(name, lines, role_count)
    op = re.fullmatch(r'zieee_(add|sub|mul|div|sqrt|fma)(16|32|64)_exceptions', name).group(1)
    d = defs(lines)
    source_width = int(re.search(r'(16|32|64)_exceptions', name).group(1))
    expected_roots = ('zstrict_and_bool',) * len(jumps)
    if op == 'sqrt':
        expected_roots = ('zstrict_and_bool', 'zstrict_or_bool')
    for index, (pc, expected) in enumerate(zip(jumps, EXCEPTION_CALLS[op])):
        condition, _, true_arm = jump(lines, pc)
        assert d[condition].startswith(expected_roots[index] + '('), \
            f'{name}: 第{index + 1}原因/finite谓词方向变化'
        seen, pending, actual = set(), [condition], Counter()
        expressions = []
        while pending:
            value = pending.pop()
            if value in seen or value not in d:
                continue
            seen.add(value)
            rhs = d[value]
            expressions.append(rhs)
            match = re.fullmatch(r'zieee_is_(\w+)\((\w+)\)', rhs)
            if match:
                role = expression(match.group(2), d)
                assert role in ('za', 'zb', 'zc'), f'{name}: 分类读取非源角色'
                actual[(match.group(1), role[1:])] += 1
            pending.extend(re.findall(r'\bzz\d+\b', rhs))
        assert actual == Counter(expected), f'{name}: 目标Jump谓词源角色错误 {actual}'
        if op == 'div' and index < 3:
            target = lines[true_arm]
            assert (target.startswith('return = zieee_empty_exceptions(true)') if index < 2
                    else target.startswith('return = zieee_exception_facts(false, true, false, false, false)')), \
                f'{name}: NV/DZ原因出口顺序变化'
        if op in ('add', 'sub') and index == 0:
            parts = re.fullmatch(r'zstrict_and_bool\((\w+), (\w+)\)', d[condition])
            assert parts, f'{name}: Inf抵消不是两条件合取'
            sign = next((part for part in parts.groups() if
                         expression(part, d).startswith(('znot_bool(', 'zeq_anythingzIB1zK('))), None)
            assert sign, f'{name}: Inf抵消未检查两源符号'
            sign_expr = expression(sign, d)
            if op == 'add':
                inverted = re.fullmatch(r'znot_bool\((\w+)\)', sign_expr)
                assert inverted, f'{name}: add异号Inf方向错误'
                sign_expr = expression(inverted.group(1), d)
            assert op != 'sub' or sign_expr.startswith('zeq_anythingzIB1zK('), \
                f'{name}: sub同号Inf方向错误'
            equality = re.fullmatch(r'zeq_anythingzIB1zK\((\w+), (\w+)\)', sign_expr)
            assert equality, f'{name}: Inf符号比较丢失'
            roles = set()
            source_width = int(re.search(r'(16|32|64)_exceptions', name).group(1))
            for bit in equality.groups():
                access = re.fullmatch(r'zbitvector_access\((\w+), (\w+)\)', expression(bit, d))
                assert access and int_value(access.group(2), d) == source_width - 1, \
                    f'{name}: Inf符号位宽错误'
                roles.add(expression(access.group(1), d))
            assert roles == {'za', 'zb'}, f'{name}: Inf符号源角色错误'
        if op == 'div' and pc in jumps[2:]:
            assert any(expr.startswith('znot_bool(') for expr in expressions), \
                f'{name}: 除法非零条件丢失'
    roles = ('za', 'zb', 'zc')[:role_count]
    guards = [jump(lines, pc)[0] for pc in jumps]
    for raw in product(representative_values(source_width), repeat=role_count):
        values = dict(zip(roles, raw))
        actual = tuple(bool(evaluate(guard, d, values, source_width)) for guard in guards)
        expected = expected_exception_guards(op, raw, source_width)
        assert actual == expected, (f'{name}: 特殊行为条件与ISA分类不符 '
                                    f'{tuple(hex(x) for x in raw)} {actual} != {expected}')
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
        assert all(pc not in reachable(lines, 0, i) for i in calls for pc in jumps), \
            f'{name}: 某个行为Jump绕过源分类'
    return len(calls)


def check_integer_wrapper(name, lines, source_width, target_width, unsigned):
    d = defs(lines)
    jumps = [pc for pc, line in enumerate(lines) if line.startswith('jump ')]
    assert len(jumps) == 3, f'{name}: invalid/NaN/sign三分界变化'
    invalid, nan, sign = jumps
    invalid_cond, ordinary, invalid_arm = jump(lines, invalid)
    assert re.fullmatch(r'zieee_has_invalid\((\w+)\)', d[invalid_cond]), \
        f'{name}: invalid谓词来源变化'
    exc = re.fullmatch(r'zieee_has_invalid\((\w+)\)', d[invalid_cond]).group(1)
    assert f'zieee_fp{source_width}_to_int_exceptions(' in d[exc], \
        f'{name}: invalid未使用同源转换异常'
    nan_cond, nonnan, nan_arm = jump(lines, nan)
    assert nan in reachable(lines, invalid_arm) and nan not in reachable(lines, ordinary), \
        f'{name}: NaN分类未受invalid控制'
    assert re.fullmatch(r'zieee_is_nan\((\w+)\)', d[nan_cond]) and \
        expression(re.fullmatch(r'zieee_is_nan\((\w+)\)', d[nan_cond]).group(1), d) == 'za', \
        f'{name}: NaN未分类原始源'
    sign_cond, nonnegative, negative = jump(lines, sign)
    assert sign in reachable(lines, nonnan) and sign not in reachable(lines, nan_arm), \
        f'{name}: sign选择未受非NaN invalid控制'
    sign_test = re.fullmatch(r'zeq_anythingzIB1zK\((\w+), 0b1\)', d[sign_cond])
    assert sign_test, f'{name}: 符号谓词变化'
    bit = re.fullmatch(r'zbitvector_access\((\w+), (\w+)\)',
                       expression(sign_test.group(1), d))
    assert bit and expression(bit.group(1), d) == 'za' and \
        int_value(bit.group(2), d) == source_width - 1, f'{name}: 未取原始源符号位'
    result = next(var for var, rhs in d.items()
                  if re.search(rf'zfp{source_width}_to_(?:signed|unsigned){target_width}\(', rhs))
    merged = next(re.match(r'(\w+) = ', line).group(1) for line in lines
                  if re.match(r'\w+ = ' + re.escape(result) + r' `', line))
    assert any(i in reachable(lines, ordinary) and line.startswith(merged + ' = ' + result)
               for i, line in enumerate(lines)), f'{name}: 合法转换结果未保留'
    positive = (1 << target_width) - 1 if unsigned else (1 << (target_width - 1)) - 1
    negative_value = 0 if unsigned else 1 << (target_width - 1)
    fmt = f'0x{{:0{target_width // 4}X}}'
    assignments = [(i, line) for i, line in enumerate(lines) if line.startswith(merged + ' = ')]
    assert any(i in reachable(lines, nan_arm) and line.startswith(merged + ' = ' + fmt.format(positive))
               for i, line in assignments), f'{name}: NaN正端点错误'
    assert any(i in reachable(lines, nonnegative) and line.startswith(merged + ' = ' + fmt.format(positive))
               for i, line in assignments), f'{name}: 正overflow端点错误'
    assert any(i in reachable(lines, negative) and line.startswith(merged + ' = ' + fmt.format(negative_value))
               for i, line in assignments), f'{name}: 负overflow端点错误'
    return len(jumps)


def check_rod_wrapper(name, lines, source_width, target_width):
    d = defs(lines)
    rm = 'zrm_bits' if source_width == 32 else 'zrm'
    jumps = [pc for pc, line in enumerate(lines) if line.startswith('jump ')]
    assert len(jumps) >= 3, f'{name}: ROD/普通/NaN出口不全'
    mode, ordinary, rod = jump(lines, jumps[0])
    compare = re.fullmatch(r'zeq_bits\((\w+), (\w+)\)', d[mode])
    assert compare and {expression(x, d) for x in compare.groups()} == {rm, '0b110'}, \
        f'{name}: ROD模式不是rm_bits==6'
    ordinary_calls = [i for i, line in enumerate(lines)
                      if f'= zriscv_valid_rm_to_ieee({rm})' in line]
    rod_calls = [i for i, line in enumerate(lines)
                 if f'= zieee_rod{source_width}_to_{target_width}(' in line]
    assert len(ordinary_calls) == len(rod_calls) == 1
    assert ordinary_calls[0] in reachable(lines, ordinary) and \
        ordinary_calls[0] not in reachable(lines, rod), f'{name}: 普通RM仍在ROD臂运行'
    assert rod_calls[0] in reachable(lines, rod) and \
        rod_calls[0] not in reachable(lines, ordinary), f'{name}: ROD helper未受模式Jump控制'
    returns = [i for i, line in enumerate(lines) if line.startswith('return = ')]
    assert len(returns) == 2 and any(i in reachable(lines, ordinary) for i in returns) and \
        any(i in reachable(lines, rod) for i in returns), f'{name}: 模式两臂没有独立flags/result返回'
    return len(jumps)


def check_rod_helper(name, lines, source_width, target_width):
    d = defs(lines)
    jumps = [pc for pc, line in enumerate(lines) if line.startswith('jump ')]
    assert len(jumps) == 2, f'{name}: finite/inexact目标Jump变化'
    finite_cond, nonfinite, finite = jump(lines, jumps[0])
    assert d[finite_cond].startswith('zieee_is_finite(') and \
        expression(re.fullmatch(r'zieee_is_finite\((\w+)\)', d[finite_cond]).group(1), d) == 'za', \
        f'{name}: 非有限源gate变化'
    exact = [i for i, line in enumerate(lines) if f'= zieee_exact{target_width}_exceptions(' in line]
    assert len(exact) == 1 and exact[0] in reachable(lines, finite) and \
        exact[0] not in reachable(lines, nonfinite), f'{name}: exact阈值计算不受finite gate支配'
    inexact_cond, exact_arm, jam_arm = jump(lines, jumps[1])
    inexact = re.fullmatch(r'zieee_has_inexact\((\w+)\)', d[inexact_cond])
    assert inexact, f'{name}: 奇数化未由NX控制'
    flags = inexact.group(1)
    assert any(line.startswith(flags + ' = zieee_empty_exceptions(') and i in reachable(lines, nonfinite)
               for i, line in enumerate(lines))
    assert any(line.startswith(flags + ' = zieee_mask_exact_exceptions(') and i in reachable(lines, finite)
               for i, line in enumerate(lines)), f'{name}: 两臂flags未在NX前合流'
    assert jumps[1] in reachable(lines, nonfinite) and jumps[1] in reachable(lines, finite), \
        f'{name}: NX Jump被finite gate短路'
    base = next(var for var, rhs in d.items() if rhs.startswith(f'zfp{target_width}_to_ieee('))
    jam = [(i, re.fullmatch(r'(\w+) = zor_vec\((\w+), (\w+)\) `.*', line))
           for i, line in enumerate(lines) if '= zor_vec(' in line]
    assert len(jam) == 1 and jam[0][1], f'{name}: ROD奇数化OR结构变化'
    jam_pc, operation = jam[0]
    assert jam_pc in reachable(lines, jam_arm) and jam_pc not in reachable(lines, exact_arm), \
        f'{name}: 仅非精确臂允许最低位置1'
    assert {expression(value, d) for value in operation.groups()[1:]} == {
        expression(base, d), f'0x{1:0{target_width // 4}X}'}, \
        f'{name}: jam未采用base|1'
    returns = [(i, field_values(line)) for i, line in enumerate(lines)
               if line.startswith('return = struct ')]
    assert len(returns) == 2 and returns[0][1][0] == returns[1][1][0] == flags, \
        f'{name}: exact/inexact返回flags来源不一致'
    assert returns[0][1][1] == base and resolves_to(returns[1][1][1],
                                                     re.escape(operation.group(1)), d), \
        f'{name}: exact/base或jam结果出口变化'
    return len(jumps)


def check_rounded(name, lines):
    d = defs(lines)
    jumps = [pc for pc, line in enumerate(lines) if line.startswith('jump ')]
    assert len(jumps) == 3, f'{name}: OF/UF/NX四出口变化'
    expected = (r'return = zieee_exception_facts\(false, false, true, ',
                r'return = zieee_exception_facts\(false, false, false, true, ',
                r'return = zieee_exception_facts\(false, false, false, false, true\)')
    for pc, pattern in zip(jumps, expected):
        _, _, true_arm = jump(lines, pc)
        assert re.match(pattern, lines[true_arm]), f'{name}: 目标Jump未到达对应异常出口'
    overflow, _, overflow_arm = jump(lines, jumps[0])
    underflow, _, underflow_arm = jump(lines, jumps[1])
    inexact, _, _ = jump(lines, jumps[2])
    assert d[overflow].startswith('zstrict_or_bool('), f'{name}: OF条件未来自边界析取'
    assert d[underflow].startswith('zstrict_and_bool(') and uses(underflow, inexact, d), \
        f'{name}: UF条件未结合NX和tiny边界'
    nx = re.fullmatch(r'znot_bool\((\w+)\)', d[inexact])
    assert nx and d[nx.group(1)].startswith('zstrict_and_bool(') and \
        sum('zfp' in d.get(token, '') and '_eq(' in d.get(token, '')
            for token in re.findall(r'\bzz\d+\b', d[nx.group(1)])) == 2, \
        f'{name}: NX未比较lo/hi与目标结果'
    assert re.search(r'zieee_exception_facts\(false, false, true, ' + re.escape(underflow) +
                     r', ' + re.escape(inexact) + r'\)', lines[overflow_arm]), \
        f'{name}: OF真臂未携带同一UF/NX事实'
    assert re.search(r'zieee_exception_facts\(false, false, false, true, ' +
                     re.escape(inexact) + r'\)', lines[underflow_arm]), \
        f'{name}: UF真臂未携带同一NX事实'
    _, no_nx, _ = jump(lines, jumps[-1])
    assert lines[no_nx].startswith('return = zieee_empty_exceptions(false)'), \
        f'{name}: 精确正常出口变化'
    assert len({jump(lines, pc)[0] for pc in jumps}) == 3, f'{name}: 三异常共用了同一个谓词'
    return len(jumps)


def check_mask_exact(lines):
    assert lines[0].startswith('jump zfinite goto '), 'mask_exact: finite条件变化'
    _, nonfinite, finite = jump(lines, 0)
    assert lines[nonfinite].startswith('return = zieee_empty_exceptions(zinvalid)'), \
        'mask_exact: 非有限路径仍计算舍入异常'
    expected = ('zieee_has_overflow(zrounded)', 'zieee_has_underflow(zrounded)',
                'zieee_has_inexact(zrounded)')
    for item in expected:
        calls = [i for i, line in enumerate(lines) if item in line]
        assert len(calls) == 1 and calls[0] in reachable(lines, finite) and \
            calls[0] not in reachable(lines, nonfinite), f'mask_exact: {item}不受finite控制'
    return 1


def check_exact_threshold(lines):
    d = defs(lines)
    jumps = [pc for pc, line in enumerate(lines) if line.startswith('jump ')]
    assert len(jumps) == 3, 'exact_threshold: OF/UF/NX四出口变化'
    overflow, _, of_arm = jump(lines, jumps[0])
    underflow, _, uf_arm = jump(lines, jumps[1])
    inexact, no_nx, nx_arm = jump(lines, jumps[2])
    assert d[overflow].startswith('zstrict_or_bool(') and \
        d[underflow].startswith('zstrict_and_bool(') and uses(underflow, inexact, d), \
        'exact_threshold: OF/UF条件变化'
    exact = re.fullmatch(r'znot_bool\((\w+)\)', d[inexact])
    assert exact and d[exact.group(1)] == 'zfp128_eq(zx, zresult)', \
        'exact_threshold: NX未比较精确值与结果'
    assert lines[of_arm].startswith('return = zieee_exception_facts(false, false, true, ' +
                                    underflow + ', ' + inexact + ')')
    assert lines[uf_arm].startswith('return = zieee_exception_facts(false, false, false, true, ' +
                                    inexact + ')')
    assert lines[nx_arm].startswith('return = zieee_exception_facts(false, false, false, false, true)')
    assert lines[no_nx].startswith('return = zieee_empty_exceptions(false)')
    return len(jumps)


def check_fp_to_int_core(lines):
    assert lines[0].startswith('jump zfinite goto '), 'fp_to_int_core: finite入口变化'
    _, invalid, finite = jump(lines, 0)
    assert lines[invalid].startswith('return = zieee_empty_exceptions(true)'), \
        'fp_to_int_core: 非有限路径没有直接NV'
    calculations = [i for i, line in enumerate(lines) if '= zfp128_from_ieee(' in line]
    assert calculations and all(i in reachable(lines, finite) and
                                i not in reachable(lines, invalid) for i in calculations), \
        'fp_to_int_core: 整数上下界在非有限路径提前计算'
    jumps = [pc for pc, line in enumerate(lines) if line.startswith('jump ')]
    assert len(jumps) == 3
    invalid_cond, invalid_arm, valid_arm = jump(lines, jumps[1])
    assert defs(lines)[invalid_cond].startswith('zstrict_and_bool(') and \
        lines[invalid_arm].startswith('return = zieee_empty_exceptions(true)'), \
        'fp_to_int_core: 整数边界NV出口变化'
    nx_cond, exact_arm, nx_arm = jump(lines, jumps[2])
    assert jumps[2] in reachable(lines, valid_arm) and \
        defs(lines)[nx_cond].startswith('znot_bool(') and \
        lines[exact_arm].startswith('return = zieee_empty_exceptions(false)') and \
        lines[nx_arm].startswith('return = zieee_exception_facts(false, false, false, false, true)'), \
        'fp_to_int_core: 合法舍入NX出口变化'
    return len(jumps)


def check_round(name, lines, width):
    d = defs(lines)
    calls = [i for i, line in enumerate(lines) if '= zieee_operand_invalid(' in line]
    assert len(calls) == 1 and calls[0] < 8, f'{name}: 源NaN分类变化'
    jumps = [pc for pc, line in enumerate(lines) if line.startswith('jump ')]
    assert len(jumps) == 2, f'{name}: finite/NX分界变化'
    finite_cond, nonfinite, finite = jump(lines, jumps[0])
    assert re.fullmatch(r'zieee_is_finite\((\w+)\)', d[finite_cond]) and \
        expression(re.fullmatch(r'zieee_is_finite\((\w+)\)', d[finite_cond]).group(1), d) == 'za', \
        f'{name}: finite源变化'
    assert lines[nonfinite].startswith('return = zieee_empty_exceptions('), \
        f'{name}: 非有限出口变化'
    value = [i for i, line in enumerate(lines) if f'= zfp{width}_from_ieee(za)' in line]
    assert len(value) == 1 and value[0] in reachable(lines, finite) and \
        value[0] not in reachable(lines, nonfinite), f'{name}: 特殊源提前运行数值比较'
    nx_cond, exact, inexact = jump(lines, jumps[1])
    assert jumps[1] in reachable(lines, finite) and jumps[1] not in reachable(lines, nonfinite)
    assert d[nx_cond].startswith('zstrict_and_bool(zraise_inexact, ') and \
        lines[exact].startswith('return = zieee_empty_exceptions(') and \
        lines[inexact].startswith('return = zieee_exception_facts(') and \
        lines[inexact].split('`', 1)[0].strip().endswith('false, true)'), \
        f'{name}: NX条件或出口变化'
    return len(jumps)


def check_conversion_gate(name, lines, source_width, exact_name):
    d = defs(lines)
    calls = [i for i, line in enumerate(lines) if '= zieee_operand_invalid(' in line]
    assert len(calls) == 1, f'{name}: NaN源分类变化'
    jumps = [pc for pc, line in enumerate(lines) if line.startswith('jump ')]
    assert len(jumps) == 1 and calls[0] < jumps[0], f'{name}: finite gate/源分类变化'
    condition, nonfinite, finite = jump(lines, jumps[0])
    assert re.fullmatch(r'zieee_is_finite\((\w+)\)', d[condition]) and \
        expression(re.fullmatch(r'zieee_is_finite\((\w+)\)', d[condition]).group(1), d) == 'za'
    assert lines[nonfinite].startswith('return = zieee_empty_exceptions('), \
        f'{name}: 非有限出口变化'
    exact = [i for i, line in enumerate(lines) if f'= {exact_name}(' in line]
    masked = [i for i, line in enumerate(lines) if 'return = zieee_mask_exact_exceptions(' in line]
    assert len(exact) == len(masked) == 1 and all(
        i in reachable(lines, finite) and i not in reachable(lines, nonfinite)
        for i in (exact[0], masked[0])), f'{name}: exact/flags计算不受finite gate支配'
    if source_width in (32, 64):
        widened = [i for i, line in enumerate(lines) if f'= zfp{source_width}_from_ieee(za)' in line]
        if widened:
            assert all(i in reachable(lines, finite) and i not in reachable(lines, nonfinite)
                       for i in widened), f'{name}: 源扩宽提前运行'
    return len(jumps)


def check(text, path):
    f = functions(text)
    results = {}
    xlen = re.search(r'(?m)^val zrX : \(%i64\) ->  %bv(32|64)$', text)
    assert xlen, f'{path}: 无法核实XLEN'
    results['accrue_fflags'] = check_flags(f['zaccrue_fflags'])
    for name, (width, signed) in NARROW.items():
        results[name] = check_narrow(name, f[name], width, signed)
    for width in (16, 32, 64):
        for op, roles, jumps in (('add', 2, 2), ('sub', 2, 2), ('mul', 2, 3),
                                 ('div', 2, 4), ('sqrt', 1, 2), ('fma', 3, 4)):
            name = f'zieee_{op}{width}_exceptions'
            results[name] = check_exception(name, f[name], roles, jumps)
        for target in (32, 64):
            for unsigned in (False, True):
                name = f'zriscv_f{width}To{"Ui" if unsigned else "I"}{target}'
                if name not in f:
                    assert xlen.group(1) == '32' and width == 16 and target == 64, \
                        f'{path}: 非RV32例外包装函数缺失 {name}'
                    continue
                results[name] = check_integer_wrapper(name, f[name], width, target, unsigned)
    for source, target in ((32, 16), (64, 32)):
        wrapper = f'zriscv_f{source}ToF{target}'
        helper = f'zieee_rod{source}_to_{target}'
        results[wrapper] = check_rod_wrapper(wrapper, f[wrapper], source, target)
        results[helper] = check_rod_helper(helper, f[helper], source, target)
    for width in (16, 32, 64):
        name = f'zieee_f{width}_rounded_exceptions'
        results[name] = check_rounded(name, f[name])
    results['zieee_mask_exact_exceptions'] = check_mask_exact(f['zieee_mask_exact_exceptions'])
    results['zieee_exact_threshold_exceptions'] = check_exact_threshold(
        f['zieee_exact_threshold_exceptions'])
    results['zieee_fp_to_int_core'] = check_fp_to_int_core(f['zieee_fp_to_int_core'])
    for width in (16, 32, 64):
        name = f'zieee_round{width}_exceptions'
        results[name] = check_round(name, f[name], width)
    for name, source, exact in (
            ('zieee_bf16_from_f32_exceptions', 32, 'zieee_exact_bf16_exceptions'),
            ('zieee_convert32_to_16_exceptions', 32, 'zieee_exact16_exceptions'),
            ('zieee_convert64_to_16_exceptions', 64, 'zieee_exact16_exceptions'),
            ('zieee_convert64_to_32_exceptions', 64, 'zieee_exact32_exceptions')):
        results[name] = check_conversion_gate(name, f[name], source, exact)
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
