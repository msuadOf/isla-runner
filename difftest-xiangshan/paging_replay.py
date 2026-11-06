#!/usr/bin/env python3
"""P0 定向探针；E0 历史转换与 E1/E2 原址探针，不承担完整 v2 平台验收。"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time

import pipeline

PPN_MASK = ((1 << 44) - 1) << 10
RAM_LIMIT = 1 << 43
FAILURE_REASONS = ("unexpected_trap", "missing_trap", "rd", "mepc", "cause", "tval", "memory")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_decoder(directory):
    path = Path(directory).resolve() / "pt_decode.py"
    spec = importlib.util.spec_from_file_location("e0_pt_decode", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, {"path": str(path), "sha256": sha256(path)}


def decode(sample, decoder):
    decoder.exact(sample, decoder.SAMPLE_FIELDS, "samples v1")
    if sample["schema_version"] != 1:
        raise ValueError("R1: 仅支持 samples v1")
    tlb = sample["pre_registers"]["tlb"]["vector"]
    if any(item != {"ctor": "None<RTLB_Entry>", "value": {"unit": True}} for item in tlb):
        raise ValueError("R5: 非空 TLB")
    decoded = decoder.decode_sample(sample, decoder.Config(True, False, False))
    instruction = decoder.decode_instruction(sample)
    if (decoded["mode"] != "Sv39" or instruction != ("load", 0, 1)
            or decoded["va"] != 0x20000000 or decoded["root_paddr"] != 0x80200000):
        raise ValueError("E0 只支持固定 VA、根表及 ld x2,0(x1)")
    ctor = sample["pre_registers"].get("$instruction")
    if ctor is not None:
        fields = decoder.struct_value(ctor["value"])
        if decoder.bit_value(fields[decoder.LOAD_FIELDS[2]], 5) != 2:
            raise ValueError("E0 要求 rd=x2")
    elif sample["isa_state"]["$instruction"].replace(" ", "") != "ldx2,0(x1)":
        raise ValueError("E0 要求 ld x2,0(x1)")
    return decoded


def predict(sample, decoder, profile="xs"):
    """Sail 使用严格解码；xs 在规范化后的实际内存上独立遍历。"""
    if profile == "sail":
        d = decode(sample, decoder)
        cause = {None: 0, "E_Load_Page_Fault": 13, "E_Load_Access_Fault": 5}[d["exception_type"]]
        return {"cause": cause, "tval": d["va"] if cause else 0,
                "rd": decoder.read_word(decoder.memory_bytes(sample["pre_memory"]), d["paddr_if_success"]) if not cause else None}
    if profile != "xs":
        raise ValueError(f"未知预测配置 {profile}")
    memory = decoder.memory_bytes(sample["pre_memory"])
    registers = sample["pre_registers"]
    status = decoder.bit_value(registers["mstatus"]["struct"]["bits"], 64)
    privilege = registers["cur_privilege"]["enum"]
    if privilege not in {"User", "Supervisor"} or status & (1 << 17):
        raise ValueError("E0 要求原样本有效权限为 U/S，MPRV=0")
    va = decoder.effective_address(sample)
    table = (decoder.bit_value(registers["satp"], 64) & ((1 << 44)-1)) << 12
    cause, rd = 0, None
    for level in (2, 1, 0):
        address = table + ((va >> (12+9*level)) & 511)*8
        if not 0x80000000 <= address < RAM_LIMIT:
            cause = 5
            break
        value = decoder.read_word(memory, address)
        f = decoder.decode_pte(value)
        # E0 的高 PPN 代表没有同时触发 PF；不推断多错误优先级。
        invalid = decoder.classify_pte(value, level, decoder.Config(False, False, False))
        if invalid["failure_reason"]:
            cause = 13
            break
        if f["PPN"] >= 1 << 36 and f["V"]:
            cause = 5
            break
        if invalid["role"] == "pointer":
            if value & 0xd0:
                cause = 13
                break
            table = f["PPN"] << 12
            continue
        if ((privilege == "User" and not f["U"])
                or (privilege == "Supervisor" and f["U"] and not status & (1 << 18))
                or not (f["R"] or (f["X"] and status & (1 << 19))) or not f["A"]):
            cause = 13
            break
        size = 1 << (12+9*level)
        physical = ((f["PPN"] << 12) & ~(size-1)) | (va & (size-1))
        if not 0x80000000 <= physical < RAM_LIMIT:
            cause = 5
        else:
            rd = decoder.read_word(memory, physical)
        break
    else:
        raise ValueError("内部不变量：遍历没有终点")
    return {"cause": cause, "tval": va if cause else 0, "rd": rd}


def relocate_sample(sample, decoder):
    decoded = decode(sample, decoder)
    derived = copy.deepcopy(sample)
    memory = decoder.memory_bytes(sample["pre_memory"])
    root = decoded["root_paddr"]
    blocks = []
    ram_cursor, fault_cursor = 1 << 32, 1 << 44
    occupied = {a & ~4095 for a in memory}

    def relocate(address, size=4096):
        nonlocal ram_cursor, fault_cursor
        base = address & ~(size-1)
        for old, new, span in blocks:
            if old <= address < old+span:
                if base < old or base+size > old+span:
                    raise ValueError("E0 不支持嵌套搬迁块扩大")
                return new+address-old
        ram = decoder.pma_permitted(sample["pre_registers"], address, "load")
        if ram is None:
            raise ValueError("R1: 缺少样本 PMA")
        if address >= RAM_LIMIT or (ram and address >= 0x80100000):
            new = base
        else:
            if base <= root < base+size:
                raise ValueError("R2: 根表落在搬迁块")
            cursor = ram_cursor if ram else fault_cursor
            new = (cursor+size-1) & ~(size-1)
            while (any(new <= page < new+size for page in occupied)
                   or any(new < other+span and other < new+size for old, other, span in blocks)):
                new += size
            if ram:
                ram_cursor = new+size
            else:
                fault_cursor = new+size
        if any(new < other+span and other < new+size for old, other, span in blocks):
            raise ValueError("R6: 重定位目标重叠")
        blocks.append((base, new, size))
        return new+address-base

    # 大块先登记，保证同一超级页内 PTE/数据采用同一个映射。
    for entry in decoded["entries"]:
        if entry["role"] == "leaf" and entry["level"] > 0:
            relocate(entry["fields"]["PPN"] << 12, entry["page_size"])
    replacements = {}
    writes = []
    for entry in decoded["entries"]:
        value = int(entry["value"], 16)
        address = relocate(entry["paddr"])
        if entry["role"] != "data":
            value &= ~(3 << 59)
            f = decoder.decode_pte(value)
            pointer = not (f["R"] or f["W"] or f["X"])
            if pointer:
                value &= ~0xd0
            # invalid 项保留 PPN；它不产生后继访问。
            if entry["role"] != "invalid":
                size = 4096 if pointer else 1 << (12+9*entry["level"])
                ppn = f["PPN"]
                new_base = relocate((ppn << 12) & ~(size-1), size)
                new_ppn = (new_base >> 12) | (ppn & ((1 << (9*entry["level"]))-1) if not pointer else 0)
                value = (value & ~PPN_MASK) | (new_ppn << 10)
            for i in range(8):
                replacements[entry["paddr"]+i] = (value >> (8*i)) & 255
        writes.append({"address": address, "value": value, "role": entry["role"]})
    for name in ("pre_memory", "post_memory"):
        for cell in derived[name]:
            old = cell["address"]
            if old in replacements:
                if decoder.read_word(decoder.memory_bytes(sample[name]), old & ~7) != decoder.read_word(memory, old & ~7):
                    raise ValueError("E0 要求 PTE 不写回")
                cell["value"] = replacements[old]
            cell["address"] = relocate(old)
    if len({w["address"] for w in writes}) != len(writes):
        raise ValueError("R6: 初始化写入重叠")
    expected = predict(derived, decoder)
    return {"sample": derived, "decoded": decoded, "writes": writes,
            "mapping": [{"old": old, "new": new, "bytes": size} for old, new, size in blocks],
            "expected": expected, "sail_expected": predict(sample, decoder, "sail")}


def directed_probe_case(sample, decoder, entry_mode="mprv"):
    """E1/E2：保持原地址和 PTE；期望只取 Isla，拒绝未对齐的平台特性。"""
    decoder.exact(sample, decoder.SAMPLE_FIELDS, "samples v1")
    if sample["schema_version"] != 1 or entry_mode not in {"mprv", "s"}:
        raise ValueError("定向探针要求 samples v1 与 mprv/s 入口")
    registers = sample["pre_registers"]
    if any(item != {"ctor": "None<RTLB_Entry>", "value": {"unit": True}}
           for item in registers["tlb"]["vector"]):
        raise ValueError("R5: 非空 TLB")
    decoded = decoder.decode_sample(sample, decoder.Config(True, False, False))
    access = decoded["access"]
    instruction = decoder.decode_instruction(sample)
    ctor = registers.get("$instruction")
    if ctor is not None:
        fields = decoder.struct_value(ctor["value"])
        register_field = decoder.LOAD_FIELDS[2] if access == "load" else decoder.STORE_FIELDS[1]
        fixed_x2 = decoder.bit_value(fields[register_field], 5) == 2
    else:
        fixed_x2 = sample["isa_state"]["$instruction"].replace(" ", "") == {
            "load": "ldx2,0(x1)", "store": "sdx2,0(x1)"}[access]
    if (decoded["mode"] != "Sv39" or decoded["va"] != 0x20000000
            or decoded["root_paddr"] != 0x80200000
            or instruction != (access, 0, 1) or not fixed_x2
            or registers["cur_privilege"]["enum"] != "Supervisor"
            or decoder.bit_value(registers["mstatus"]["struct"]["bits"], 64) & (1 << 17)):
        raise ValueError("定向探针只支持固定 Sv39 S 态 ld/sd x2,0(x1)")
    for entry in decoded["entries"]:
        if entry["role"] == "data":
            continue
        f = entry["fields"]
        if f["RSW_60t59b"]:
            raise ValueError("配置未对齐：Svrsw60t59b")
        if entry["role"] == "pointer" and int(entry["value"], 16) & 0xd0:
            raise ValueError("R7: 指针 U/A/D 非零")
        if f["N"] or f["PBMT"] or f["reserved"] or f["PPN"] >= 1 << 36:
            raise ValueError("定向探针排除扩展位、保留位与高 PPN")
    if decoded["exception_type"] not in {None, "E_Load_Page_Fault", "E_SAMO_Page_Fault"}:
        raise ValueError("定向探针排除 PMA 不一致的 AF")
    pre = decoder.memory_bytes(sample["pre_memory"], allow_unknown=True)
    post = decoder.memory_bytes(sample["post_memory"])
    if set(pre) != set(post) or any(not 0x80100000 <= a < RAM_LIMIT for a in pre):
        raise ValueError("R9: 定向探针内存必须全部在 DRAM")
    filled = {a: post[a] ^ 255 if value is None else value for a, value in pre.items()}
    writes = []
    for address in sorted({a & ~7 for a in pre}):
        writes.append({"address": address, "value": decoder.read_word(filled, address),
                       "expected_value": decoder.read_word(post, address), "role": "sample"})
    # 真 S 态只补一项取指映射；样本 VA 使用根槽 0，取指使用未被样本占用的槽 2。
    if entry_mode == "s":
        address = 0x80200010
        if any(address+i in pre for i in range(8)) or decoded["vpn"][-1] == 2:
            raise ValueError("R6: S 态取指映射与样本重叠")
        value = ((0x80000000 >> 12) << 10) | 0xcb
        writes.append({"address": address, "value": value, "expected_value": value, "role": "harness_fetch"})
    cause = {None: 0, "E_Load_Page_Fault": 13, "E_SAMO_Page_Fault": 15}[decoded["exception_type"]]
    rd = None
    if access == "load":
        rd = decoder.bit_value(sample["post_registers"]["x2"], 64)
    return {"sample": copy.deepcopy(sample), "decoded": decoded, "writes": writes,
            "entry_mode": entry_mode, "access": access, "directed_probe": True,
            "expected": {"cause": cause, "tval": decoded["va"] if cause else 0, "rd": rd}}


def paging_assembly(case):
    sample, expected = case["sample"], case["expected"]
    registers = sample["pre_registers"]
    status = int(registers["mstatus"]["struct"]["bits"]["bits"], 2)
    privilege = {"User": 0, "Supervisor": 1}[registers["cur_privilege"]["enum"]]
    status = (status & ~((3 << 11) | (1 << 3))) | (1 << 17) | (privilege << 11)
    real_s = case.get("entry_mode") == "s"
    if real_s:
        status &= ~(1 << 17)
    access = case.get("access", "load")
    envcfg = int(registers["menvcfg"]["struct"]["bits"]["bits"], 2)
    if envcfg != 0:
        raise ValueError("E0 要求 menvcfg=0")
    lines = [".section .text.init", ".globl _start", ".option norvc", ".option norelax", "_start:",
             "    csrw satp, zero", "    csrw medeleg, zero", "    csrw mideleg, zero",
             "    csrw mie, zero", "    csrw mcause, zero", "    csrw mtval, zero", "    csrw mepc, zero",
             "    csrw 0x30a, zero", "    la t0, trap_handler", "    csrw mtvec, t0",
             *pipeline.pmp_open_setup()]
    for word in case["writes"]:
        if not 0x80100000 <= word["address"] < RAM_LIMIT:
            raise ValueError("初始化地址不在 XiangShan DRAM")
        lines += [f"    li t0, {word['address']:#x}", f"    li t1, {word['value']:#x}", "    sd t1, 0(t0)"]
    lines += ["    fence rw, rw", f"    li t0, {int(registers['satp']['bits'], 2):#x}", "    csrw satp, t0",
              "    sfence.vma x0, x0", f"    li t0, {status:#x}", "    csrw mstatus, t0"]
    if real_s:
        lines += ["    la t0, s_entry", "    csrw mepc, t0", "    mret", "s_entry:"]
    for index in range(1, 32):
        key = f"x{index}"
        if key in registers:
            lines.append(f"    li {key}, {int(registers[key]['bits'], 2):#x}")
    lines += ["payload_ins:", "    ld x2, 0(x1)" if access == "load" else "    sd x2, 0(x1)"]
    if real_s:
        lines += ["s_return:", "    ecall", "    j fail_missing_trap"]
    else:
        lines += ["    li t0, 0x20000", "    csrc mstatus, t0",
                  "    csrr s0, mcause", "    csrr s1, mtval", "    csrr s2, mepc"]
    if expected["cause"]:
        lines += ["    j fail_missing_trap"]
    else:
        lines += ["    j check_result"]
    lines += [".balign 4", "trap_handler:", "    li t0, 0x20000", "    csrc mstatus, t0",
              "    csrr s0, mcause", "    csrr s1, mtval", "    csrr s2, mepc"]
    if not expected["cause"]:
        if real_s:
            lines += ["    la t0, s_return", "    bne s2, t0, fail_unexpected_trap",
                      "    li t0, 9", "    bne s0, t0, fail_cause", "    bnez s1, fail_tval",
                      "    j check_result"]
        else:
            lines += ["    j fail_unexpected_trap"]
    else:
        lines += ["    la t0, payload_ins", "    bne s2, t0, fail_mepc",
                  f"    li t0, {expected['cause']}", "    bne s0, t0, fail_cause",
                  f"    li t0, {expected['tval']:#x}", "    bne s1, t0, fail_tval", "    j check_result"]
    lines += ["check_result:"]
    if expected["rd"] is not None:
        lines += [f"    li t0, {expected['rd']:#x}", "    bne x2, t0, fail_rd"]
    lines += ["check_memory:"]
    for word in case["writes"]:
        lines += [f"    li t0, {word['address']:#x}", "    ld t2, 0(t0)",
                  f"    li t1, {word.get('expected_value', word['value']):#x}", "    bne t2, t1, fail_memory"]
    lines += ["good_trap:", "    li a0, 0", "good_trap_ins:", "    .4byte 0x0005006b"]
    for reason in FAILURE_REASONS:
        lines += [f"fail_{reason}:", "    li a0, 1", f"fail_{reason}_trap:", "    .4byte 0x0005006b", f"    j fail_{reason}"]
    return "\n".join(lines)+"\n"


def check_exit_layout(disassembly, symbols):
    """核对链接后的出口：GOOD 只能从完整内存检查块顺序落入。"""
    instructions = []
    for line in disassembly.splitlines():
        match = re.match(r"\s*([0-9a-f]+):\s+([0-9a-f]{8})\s+(.+)", line)
        if match:
            instructions.append((int(match[1], 16), int(match[2], 16), match[3]))
    words = {pc: word for pc, word, asm in instructions}
    failure_symbols = {f"fail_{reason}_trap" for reason in FAILURE_REASONS}
    if {name for name in symbols if re.fullmatch(r"fail_.+_trap", name)
        and name not in {f"fail_{reason}" for reason in FAILURE_REASONS}} != failure_symbols:
        raise ValueError("出口静态检查：失败桩符号集合错误")
    trap_addresses = {symbols[name] for name in failure_symbols | {"good_trap_ins"}}
    if len(trap_addresses) != len(FAILURE_REASONS)+1:
        raise ValueError("出口静态检查：失败桩符号地址不唯一")
    if {pc for pc, word, asm in instructions if word & 0x7f == 0x6b} != trap_addresses:
        raise ValueError("出口静态检查：存在未登记的 XSTrap 或出口缺失")
    for name in failure_symbols:
        if words.get(symbols[name]-4) != 0x00100513 or words.get(symbols[name]) != 0x0005006b:
            raise ValueError("出口静态检查：失败桩编码错误")
    check, good, trap = (symbols[name] for name in ("check_memory", "good_trap", "good_trap_ins"))
    if not check < good or trap != good+4 or words.get(good) != 0x00000513 or words.get(trap) != 0x0005006b:
        raise ValueError("出口静态检查：GOOD 桩布局错误")
    failure_entries = {symbols[f"fail_{reason}"] for reason in FAILURE_REASONS}
    for pc, word, asm in instructions:
        opcode = word & 0x7f
        if opcode == 0x67:
            raise ValueError("出口静态检查：不允许间接跳转")
        if opcode in (0x63, 0x6f):
            target = re.search(r"\b([0-9a-f]+)\s+<", asm)
            if target is None:
                raise ValueError("出口静态检查：跳转目标不可解析")
            destination = int(target[1], 16)
            if check < destination <= trap:
                raise ValueError("出口静态检查：跳转绕过内存检查")
            if check <= pc < good and (opcode != 0x63 or destination not in failure_entries):
                raise ValueError("出口静态检查：内存检查块不能顺序落入 GOOD")
    if good-4 not in words or words[good-4] & 0x7f != 0x63:
        raise ValueError("出口静态检查：GOOD 前缺少内存检查")


def build_case(case, output, compiler="riscv64-unknown-elf-gcc"):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    assembly, elf, linker = output/"program.S", output/"program.elf", output/"xiangshan.ld"
    assembly.write_text(paging_assembly(case))
    linker.write_text(pipeline.LINKER)
    command = [compiler, "-nostdlib", "-nostartfiles", "-static", "-fno-pic", "-march=rv64gc", "-mabi=lp64d",
               "-Wl,-T,"+str(linker), "-Wl,-e,_start", "-o", str(elf), str(assembly)]
    compiled = subprocess.run(command, capture_output=True, text=True)
    (output/"build.log").write_text(compiled.stdout+compiled.stderr)
    compiled.check_returncode()
    ranges = pipeline.elf_alloc_ranges(elf)
    if not ranges or any(start < 0x80000000 or end > 0x80100000 for start, end in ranges):
        raise ValueError("R6: ELF 超出代码窗口")
    plan = {"pre": case["sample"]["pre_memory"], "post": case["sample"]["post_memory"], "events": []}
    if pipeline.memory_overlaps_ranges(plan, ranges):
        raise ValueError("R6: ELF 与样本内存重叠")
    nm = subprocess.run([compiler.removesuffix("gcc")+"nm", "-n", str(elf)], capture_output=True, text=True, check=True)
    (output/"symbols.txt").write_text(nm.stdout)
    symbols = {}
    for line in nm.stdout.splitlines():
        parts = line.split()
        if len(parts) == 3:
            if parts[2] in symbols:
                raise ValueError("出口静态检查：重复符号")
            symbols[parts[2]] = int(parts[0], 16)
    objdump = subprocess.run([compiler.removesuffix("gcc")+"objdump", "-d", "-M", "no-aliases", str(elf)],
                             capture_output=True, text=True, check=True)
    (output/"objdump.txt").write_text(objdump.stdout)
    check_exit_layout(objdump.stdout, symbols)
    if symbols["trap_handler"] % 4:
        raise ValueError("handler 未按 4 字节对齐")
    result = {**case, "elf": str(elf), "elf_sha256": sha256(elf), "build_command": command, "symbols": symbols}
    (output/"case.json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n")
    return result


def classify_log(log, returncode, symbols, *, elf_sha256=None, expected_elf_sha256=None):
    text = re.sub(r"\x1b\[[0-9;]*m", "", log)
    l2 = bool(re.search(r"L2TLB resp test[^\n]*failed", text))
    hits = re.findall(r"HIT (?:GOOD|BAD) TRAP", text)
    good, bad = "HIT GOOD TRAP" in hits, "HIT BAD TRAP" in hits
    match = re.search(r"HIT (?:GOOD|BAD) TRAP at pc\s*=\s*(0x[0-9a-fA-F]+)", text)
    pc = int(match[1], 16) if match else None
    names = [name for name, address in symbols.items() if address == pc]
    symbol = names[0] if len(names) == 1 else None
    failure = re.fullmatch(r"fail_(.+)_trap", symbol) if symbol is not None else None
    reason = failure[1] if failure else None
    false_good = good and failure is not None
    hash_matches = elf_sha256 is not None and elf_sha256 == expected_elf_sha256
    limit = bool(re.search(r"EXCEEDING (?:CYCLE|INSTR|CYCLE/INSTR) LIMIT", text))
    agree = (hash_matches and returncode == 0 and len(hits) == 1 and good and not bad
             and pc == symbols.get("good_trap_ins") and pc is not None
             and symbol == "good_trap_ins" and not l2 and "ABORT" not in text and not limit)
    bucket = ("timeout" if returncode is None else "limit" if limit else
              "other-failure" if not hash_matches else
              "xs!=expected" if len(hits) == 1 and failure else
              "framework-abort" if l2 else "xs!=nemu" if "ABORT" in text else
              "agree" if agree else "other-failure")
    return {"agree": agree, "bucket": bucket, "good_trap": good, "bad_trap": bad,
            "abort": "ABORT" in text, "trap_pc": pc, "trap_symbol": symbol,
            "bad_pc": pc if bad else None, "bad_symbol": symbol if bad else None,
            "false_good": false_good, "l2tlb_failed": l2, "reason": reason,
            "hit_count": len(hits), "elf_hash_matches": hash_matches, "limit": limit}


def run_probe(case, emulator, diff_so, timeout=600):
    """沿用 run_case 的命令与进程组止损；E0 保留完整日志且超时不重跑。"""
    if not 0 < timeout <= 600:
        raise ValueError("单次 emu 超时上限是 600 秒")
    directory = Path(case["elf"]).parent
    if sha256(case["elf"]) != case["elf_sha256"]:
        raise ValueError("R0: 运行 ELF 哈希与 case.json 不一致")
    command = [str(Path(emulator).resolve()), "-i", case["elf"], "--diff", str(Path(diff_so).resolve())]
    started = time.monotonic()
    # pipeline.run_case 会丢弃 GOOD 的完整日志，且超时后自动重跑，不能用于 E0 取证。
    with (directory/"difftest.log").open("w") as log:
        proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, cwd=directory, start_new_session=True)
        try:
            returncode = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            returncode = None
    log = (directory/"difftest.log").read_text(errors="replace")
    result = {"id": directory.name, "command": command, "returncode": returncode,
              "elapsed": round(time.monotonic()-started, 3), "log": str(directory/"difftest.log"),
              "elf_sha256": sha256(case["elf"]), "expected_elf_sha256": case["elf_sha256"],
              **classify_log(log, returncode, case["symbols"], elf_sha256=sha256(case["elf"]),
                             expected_elf_sha256=case["elf_sha256"])}
    (directory/"result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    convert = sub.add_parser("convert")
    convert.add_argument("--input", type=Path, required=True)
    convert.add_argument("--sample-id", type=int, required=True)
    convert.add_argument("--pt-decode-dir", type=Path, required=True)
    convert.add_argument("--output", type=Path, required=True)
    build = sub.add_parser("build")
    build.add_argument("--case", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--compiler", default="riscv64-unknown-elf-gcc")
    run = sub.add_parser("run")
    run.add_argument("--case", type=Path, required=True)
    run.add_argument("--emu", default=os.environ.get("XIANGSHAN_EMU"), required="XIANGSHAN_EMU" not in os.environ)
    run.add_argument("--diff", default=os.environ.get("XIANGSHAN_DIFF_SO"), required="XIANGSHAN_DIFF_SO" not in os.environ)
    run.add_argument("--timeout", type=int, default=600)
    classify = sub.add_parser("classify")
    classify.add_argument("--case", type=Path, required=True)
    classify.add_argument("--log", type=Path, required=True)
    classify.add_argument("--returncode", type=int, required=True)
    args = parser.parse_args()
    if args.action == "convert":
        decoder, provenance = load_decoder(args.pt_decode_dir)
        selected = [json.loads(line) for line in args.input.open() if json.loads(line)["sample_id"] == args.sample_id]
        if len(selected) != 1:
            raise ValueError("sample_id 必须恰好匹配一条")
        case = relocate_sample(selected[0], decoder)
        case["pt_decode"] = provenance
        case["source"] = {"path": str(args.input.resolve()), "sha256": sha256(args.input), "sample_id": args.sample_id}
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output/"converted.json").write_text(json.dumps(case, ensure_ascii=False, indent=2)+"\n")
        (args.output/"derived.jsonl").write_text(json.dumps(case["sample"], ensure_ascii=False)+"\n")
    else:
        case = json.loads(args.case.read_text())
        if args.action == "build":
            build_case(case, args.output, args.compiler)
        elif args.action == "run":
            print(json.dumps(run_probe(case, args.emu, args.diff, args.timeout), ensure_ascii=False))
        else:
            print(json.dumps(classify_log(args.log.read_text(), args.returncode, case["symbols"],
                elf_sha256=sha256(case["elf"]), expected_elf_sha256=case["elf_sha256"]), ensure_ascii=False))


if __name__ == "__main__":
    main()
