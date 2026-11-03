#!/usr/bin/env python3
"""仅供独审：将诊断 Rust Debug 值规范化，比较有序列化差异的完整寄存器快照。"""
import json
import re
import sys
from pathlib import Path

TOKEN = re.compile(r'\s*("(?:\\.|[^"\\])*"|-?\d+|[A-Za-z_][A-Za-z_0-9]*|[{}()\[\],:])')


def normalize(text):
    tokens = []
    cursor = 0
    while cursor < len(text):
        match = TOKEN.match(text, cursor)
        if not match:
            raise ValueError((cursor, text[cursor:cursor + 80]))
        tokens.append(match.group(1))
        cursor = match.end()
    cursor = 0

    def take(expected=None):
        nonlocal cursor
        token = tokens[cursor]
        cursor += 1
        if expected is not None and token != expected:
            raise ValueError((expected, token, text))
        return token

    def peek():
        return tokens[cursor] if cursor < len(tokens) else None

    def sequence(close):
        values = []
        while peek() != close:
            values.append(value())
            if peek() != close:
                take(',')
        take(close)
        return values

    def fields(close):
        values = []
        while peek() != close:
            key = value()
            take(':')
            item = value()
            # EnumMember.member 的 ordinal 属于目标 IR，成员名才是跨 IR 身份。
            if key == ['symbol', 'member'] and isinstance(item, str) and '|' in item:
                item = item.split('|', 1)[1]
            values.append([key, item])
            if peek() != close:
                take(',')
        take(close)
        return sorted(values, key=lambda item: json.dumps(item[0], sort_keys=True))

    def value():
        token = take()
        if token.startswith('"'):
            return json.loads(token)
        if re.fullmatch('-?\\d+', token):
            return int(token)
        if token == '[':
            return ['array', sequence(']')]
        if token == '{':
            return ['map', fields('}')]
        if peek() == '(':
            take('(')
            return ['call', token, sequence(')')]
        if peek() == '{':
            take('{')
            return ['record', token, fields('}')]
        return ['symbol', token]

    result = value()
    if cursor != len(tokens):
        raise ValueError(('trailing', tokens[cursor:], text))
    return result


def snapshot(path):
    data = json.loads(Path(path).read_text())
    registers = data.get('concrete_registers', data.get('registers', data))
    return {name: normalize(value) for name, value in sorted(registers.items())}


if __name__ == '__main__':
    left = snapshot(sys.argv[1])
    if len(sys.argv) == 2:
        print(json.dumps(left, ensure_ascii=False, indent=2))
    else:
        right = snapshot(sys.argv[2])
        differences = {name: {'left': left.get(name), 'right': right.get(name)}
                       for name in sorted(left.keys() | right.keys()) if left.get(name) != right.get(name)}
        print(json.dumps({'left_count': len(left), 'right_count': len(right), 'differences': differences},
                         ensure_ascii=False, indent=2))
        sys.exit(bool(differences))
