#!/usr/bin/env python3
"""独立核对官方 Z3 枚举声明与类型身份，不更改 Isla。"""
import ctypes as c
import hashlib
import json
from pathlib import Path

lib_path = Path('/home/baiyifan/.local/opt/z3-official-1fd1d3613/lib/libz3.so.5.3').resolve()
z3 = c.CDLL(str(lib_path))
ptr = c.c_void_p


def api(name, result, args):
    function = getattr(z3, name)
    function.restype = result
    function.argtypes = args
    return function


mk_config = api('Z3_mk_config', ptr, [])
del_config = api('Z3_del_config', None, [ptr])
mk_context = api('Z3_mk_context_rc', ptr, [ptr])
del_context = api('Z3_del_context', None, [ptr])
mk_symbol = api('Z3_mk_int_symbol', ptr, [ptr, c.c_int])
mk_enum = api('Z3_mk_enumeration_sort', ptr, [ptr, ptr, c.c_uint, c.POINTER(ptr), c.POINTER(ptr), c.POINTER(ptr)])
sort_ast = api('Z3_sort_to_ast', ptr, [ptr, ptr])
decl_ast = api('Z3_func_decl_to_ast', ptr, [ptr, ptr])
inc_ref = api('Z3_inc_ref', None, [ptr, ptr])
dec_ref = api('Z3_dec_ref', None, [ptr, ptr])
error_message = api('Z3_get_error_msg', c.c_char_p, [ptr, c.c_uint])
equal_sort = api('Z3_is_eq_sort', c.c_bool, [ptr, ptr, ptr])
get_range = api('Z3_get_range', ptr, [ptr, ptr])
handler_type = c.CFUNCTYPE(None, ptr, c.c_uint)
set_handler = api('Z3_set_error_handler', None, [ptr, handler_type])
errors = []


@handler_type
def handler(ctx, code):
    errors.append(error_message(ctx, code).decode())


def context():
    cfg = mk_config()
    ctx = mk_context(cfg)
    del_config(cfg)
    set_handler(ctx, handler)
    return ctx


def enum(ctx, name, members):
    names = (ptr * len(members))(*(mk_symbol(ctx, member) for member in members))
    consts, testers = (ptr * len(members))(), (ptr * len(members))()
    sort = mk_enum(ctx, mk_symbol(ctx, name), len(members), names, consts, testers)
    if sort:
        refs = [sort_ast(ctx, sort)] + [decl_ast(ctx, decl) for decl in list(consts) + list(testers)]
        for ref in refs:
            inc_ref(ctx, ref)
        return sort, list(consts), refs
    return None


ctx = context()
first = enum(ctx, 700, [0, 1])
assert first
assert enum(ctx, 700, [0, 1]) is None
second = enum(ctx, 701, [0, 1])
assert second
assert not equal_sort(ctx, first[0], second[0])
assert equal_sort(ctx, get_range(ctx, first[1][0]), first[0])
assert equal_sort(ctx, get_range(ctx, second[1][0]), second[0])
for ref in first[2]:
    dec_ref(ctx, ref)
assert enum(ctx, 700, [0, 1]) is None
other_ctx = context()
assert enum(other_ctx, 700, [0, 1])
del_context(other_ctx)
del_context(ctx)
print(json.dumps({
    'library_sha256': hashlib.sha256(lib_path.read_bytes()).hexdigest(),
    'duplicate_declaration_errors': errors,
    'different_sorts_with_same_member_symbols': True,
    'same_sort_name_in_new_context': True,
    'duplicate_still_rejected_after_releasing_original_references': True,
}, ensure_ascii=False, indent=2))
