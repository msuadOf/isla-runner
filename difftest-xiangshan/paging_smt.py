"""修复符号特权实验已有的枚举快照命名问题；不改原查询或断言。"""
import json
import re


def normalize_enum_names(source):
    """只在已确定的枚举类型上下文中，把 k!0 等对应到声明的 k!00 等。"""
    tokens = re.findall(r';[^\n]*|\(|\)|"(?:[^"]|"")*"|\|[^|]*\||[^\s();]+', source.read_text())
    stack, forms = [], []
    for token in tokens:
        if token.startswith(';'):
            continue
        if token == '(':
            stack.append([])
        elif token == ')':
            node = stack.pop()
            if stack:
                stack[-1].append(node)
            else:
                forms.append(node)
        else:
            stack[-1].append(token)
    assert not stack
    sorts, types = {}, {}
    for form in forms:
        if form[0] == 'declare-datatypes':
            assert len(form[1]) == len(form[2]) == 1
            names = [member[0] for member in form[2][0]]
            # 只处理已核实的五种特权枚举序列化形式，其他格式原样保留。
            if names == ['k!00', 'k!10', 'k!20', 'k!30', 'k!40']:
                sorts[form[1][0][0]] = {f'k!{i}': name for i, name in enumerate(names)}
        if form[0] == 'declare-fun':
            types[form[1]] = form[3]
    changes = []

    def inferred(node):
        if isinstance(node, str):
            sort = types.get(node)
            return sort if isinstance(sort, str) and sort in sorts else None
        if node and node[0] == 'ite':
            return inferred(node[2]) or inferred(node[3])
        return None

    def walk(node, expected=None):
        if isinstance(node, str):
            if expected in sorts and node in sorts[expected]:
                new = sorts[expected][node]
                changes.append(dict(old=node, new=new, expected_sort=expected))
                return new
            return node
        if not node or node[0] in ('declare-datatypes', 'declare-fun'):
            return node
        if node[0] in ('=', 'distinct'):
            sort = next((sort for arg in node[1:] if (sort := inferred(arg))), None)
            return [node[0]] + [walk(arg, sort) for arg in node[1:]]
        if node[0] == 'ite':
            sort = expected or inferred(node)
            return ['ite', walk(node[1]), walk(node[2], sort), walk(node[3], sort)]
        return [walk(child) for child in node]

    def emit(node):
        return '('+' '.join(map(emit, node))+')' if isinstance(node, list) else node

    fixed = [walk(form) for form in forms]
    out = source.with_name(source.stem+'-enum-names.smt2')
    out.write_text('; 仅修枚举构造子的序列化名字，全部断言和类型保留\n'
                   +'\n'.join(map(emit, fixed))+'\n')
    out.with_suffix('.normalization.json').write_text(json.dumps(dict(
        original=source.name, normalized=out.name, form_count=len(forms), changes=changes), indent=2)+'\n')
    return out
