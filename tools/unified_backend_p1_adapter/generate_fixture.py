#!/usr/bin/env python3
"""Generate a closed, typed Sail call fixture from the reviewed call-site list."""
import argparse
import csv
import json
import re
from pathlib import Path


def split_args(spec):
    if not spec.startswith('('):
        return [spec]
    spec = spec[1:-1]
    parts, start, depth = [], 0, 0
    for i, ch in enumerate(spec):
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        elif ch == ',' and depth == 0:
            parts.append(spec[start:i].strip())
            start = i + 1
    parts.append(spec[start:].strip())
    return parts


def fixed_type(typ, width=None):
    if width is not None:
        typ = typ.replace("'n", str(width))
    return re.sub(r'bits\((\d+)\)', r'bitvector(\1, dec)', typ)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path, help='ieee_fp_primops.sail')
    parser.add_argument('output', type=Path)
    parser.add_argument('--all-bindings', type=Path)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    if args.all_bindings:
        mapping = json.loads(args.all_bindings.read_text())
        selected = {r['sail_name']: r for r in mapping['entries']}
        assert len(selected) == 190, len(selected)
    else:
        with (here / 'native_calls.tsv').open() as file:
            rows = [r for r in csv.DictReader(file, delimiter='\t') if r['call_sites']]
        selected = {r['sail_name']: r for r in rows}
    vals = {}
    for line in args.source.read_text().splitlines():
        match = re.match(r'val (\w+) = (pure|impure) (?:"([^"]+)"|\{c: "([^"]+)"[^}]*\}) : (.*)', line)
        if match and match[1] in selected:
            vals[match[1]] = (match[2], match[3] or match[4], match[5])
    expected = 190 if args.all_bindings else 101
    assert len(selected) == expected, (len(selected), sorted(selected.keys() - vals.keys()))
    assert len(vals) == expected, (len(vals), sorted(selected.keys() - vals.keys()))
    special = {'ite', 'strict_and_bool', 'strict_or_bool', 'isla_bool_to_bit'}
    lines = ['default Order dec', '$include <prelude.sail>', '$include <generic_equality.sail>', '$sail_internal']
    preserved = []
    for name in sorted(selected.keys() - special):
        effect, extern, sig = vals[name]
        if args.all_bindings:
            entry = selected[name]
            assert effect == entry['effect'] and extern == entry['c_primop'] and sig == entry['signature'], name
            cpp = entry['cpp_proposed_name']
        else:
            cpp = f'sail_{name}'
        lines.append(f'val {name} = {effect} {{c: "{extern}", cpp: "{cpp}"}} : {sig}')
        if sig.startswith('forall '):
            sig = sig.split('. ', 1)[1]
        inp, out = sig.rsplit(' -> ', 1)
        widths = [1, 32, 33, 64, 65, 113, 129, 1024] if args.all_bindings else [32, 64]
        for width in (widths if "'n" in inp else [None]):
            in_types = [fixed_type(x, width) for x in split_args(inp)]
            out_type = fixed_type(out, width)
            suffix = f'_{width}' if width else ''
            wrapper = 'probe_' + name + suffix
            preserved.append(wrapper)
            args_decl = ', '.join(f'a{i} : {t}' for i, t in enumerate(in_types))
            call = ', '.join(f'a{i}' for i in range(len(in_types)))
            lines.append(f'function {wrapper}({args_decl}) -> {out_type} = {name}({call})')
    lines += [
        'struct probe_record = { value : float32, raw : bitvector(128, dec) }',
        'val ite = pure {c: "ite"} : forall (\'a : Type). (bool, \'a, \'a) -> \'a',
        'function ite(c, a, b) = if c then a else b',
        'val strict_and_bool = pure {c: "strict_and_bool"} : (bool, bool) -> bool',
        'function strict_and_bool(a, b) = a & b',
        'val strict_or_bool = pure {c: "strict_or_bool"} : (bool, bool) -> bool',
        'function strict_or_bool(a, b) = a | b',
        'val isla_bool_to_bit = pure {c: "isla_bool_to_bit"} : bool -> bit',
        'function isla_bool_to_bit(b) = if b then bitone else bitzero',
        'function probe_ite(c : bool, a : bitvector(128, dec), b : bitvector(128, dec)) -> bitvector(128, dec) = ite(c, a, b)',
        'function probe_strict_and_bool(a : bool, b : bool) -> bool = strict_and_bool(a, b)',
        'function probe_strict_or_bool(a : bool, b : bool) -> bool = strict_or_bool(a, b)',
        'function probe_isla_bool_to_bit(b : bool) -> bit = isla_bool_to_bit(b)',
        'function probe_generic_eq32(a : float32, b : float32) -> bool = eq_anything(a, b)',
        'function probe_generic_neq32(a : float32, b : float32) -> bool = a != b',
        'function probe_ite_float32(c : bool, a : float32, b : float32) -> float32 = ite(c, a, b)',
        'function probe_ite_record(c : bool, a : probe_record, b : probe_record) -> probe_record = ite(c, a, b)',
        'function probe_eq_record(a : probe_record, b : probe_record) -> bool = eq_anything(a, b)',
    ]
    preserved += ['probe_ite', 'probe_strict_and_bool', 'probe_strict_or_bool', 'probe_isla_bool_to_bit',
                  'probe_generic_eq32', 'probe_generic_neq32', 'probe_ite_float32',
                  'probe_ite_record', 'probe_eq_record']
    lines.append('function main() -> unit = ()')
    args.output.write_text('\n'.join(lines) + '\n')
    (args.output.parent / 'preserve.txt').write_text('\n'.join(preserved) + '\n')
    print(f'{len(selected)} declarations, {len(preserved)} generated call wrappers')


if __name__ == '__main__':
    main()
