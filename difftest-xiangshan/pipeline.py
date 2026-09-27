#!/usr/bin/env python3
"""Isla JSON 到 XiangShan DiffTest 的最小 RVV 批处理链路。"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import signal
import struct
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE = ROOT.parent / "isla" / "output" / "rv64_zVVTYPE.json"
DEFAULT_OUT = ROOT / "work"
ENCODING_RE = re.compile(r"(?:32|64)'h([0-9a-fA-F_]+)$")
BITS_RE = re.compile(r"(\d+)'h([0-9a-fA-F_]+)$")
VECTOR_RE = re.compile(r"^vr([0-9]|[12][0-9]|3[01])$")
GPR_RE = re.compile(r"^x([0-9]|[12][0-9]|3[01])$")
V_CONTEXT_REGISTERS = {"vl", "vstart", "vtype", "vcsr"}
VSTART_CSR = 0x008
VXSAT_CSR = 0x009
VXRM_CSR = 0x00A
PMPCFG0_CSR = 0x3A0
PMPADDR0_CSR = 0x3B0
T0 = 5
T1 = 6
TRAP_RET_VAL_RE = re.compile(r"^(Illegal_Instruction|Memory_Exception)")
RESULTS_NDJSON = "results.ndjson"
PRE_MEMORY_FILL = 0xA5  # pre-memory value=null 的自由字节填充模式（非零、确定性）
SHF_ALLOC = 0x2
SAMPLE_MODES = ("all", "first-per-encoding")
SKIP_POST_ALL_NULL = "post-all-null"
SKIP_CODE_OVERLAP = "code-overlap"
# W13 对账预分类：低位错位 fault 是 emu/NEMU 的 mcause 真分歧（emu 报 access
# fault mcause7、NEMU 报 store misaligned mcause6，difftest 直接 ABORT），两侧
# 都 fault、Isla 判 fault 正确，跳过重放并计数。
SKIP_MCAUSE_DIVERGENCE = "lowaddr-misaligned-mcause-divergence"
# W13 对账预分类标注位：图内对齐 fault（Isla 历史上因 PMP 符号化产出假 fault，
# 全量 107/2479；isla 侧钉死 PMP 后应消失）。不跳过，出现即提示上游回归。
PRECLASS_INMAP_ALIGNED_FAULT = "in-map-aligned-fault"
# emu 实际有效 RAM（W13 探针+源码：SoC.scala:335 memRange、Parameters.scala:568
# SimMemSize=8190GB），[0x80000000,0x80000000000) 8TB；difftest csrc 的 256MB
# DRAM 宏对该 emu 不适用。
EMU_RAM_BASE = 0x80000000
EMU_RAM_LIMIT = 0x80000000000
# S4 地图假设过滤（W17 符号边界用例配套）：`[[pma_regions]] size="symbolic"` 求解
# 后每条路径 isa-state 带 pma_regions.<name>.size 模型值（侧通道）。S4 oracle
# 规则：符号化地图假设的重放必须与目标平台真实地图一致——期望行为（成功/fault）
# 在真实地图下不成立的路径跳过（其价值在生成期多地图假设覆盖，不在固定平台重放）。
SKIP_MAP_HYPOTHESIS_MISMATCH = "map-hypothesis-mismatch"
PMA_SIZE_KEY_RE = re.compile(r"^pma_regions\.([A-Za-z0-9_-]+)\.size$")
# 假设顶界（base+size）推导的基界约定：W17 符号配置单 region "ram" 钉 DRAM 基界，
# JSON 不携带 base 字段（README 记录该约定）；过滤判定本身只依赖真实顶界与有效
# 地址，不依赖该约定。
MAP_HYPOTHESIS_BASE = EMU_RAM_BASE
STORE_EFFECT_RE = re.compile(
    r"^(s[bhwd])\s+\S+,\s*(-?0[xX][0-9a-fA-F]+|-?\d+)\((x(?:[0-9]|[12][0-9]|3[01]))\)$"
)
STORE_ACCESS_SIZE = {"sb": 1, "sh": 2, "sw": 4, "sd": 8}
BUILD_SUMMARY = "build-summary.json"


def expects_trap(entry: dict) -> bool:
    """Isla 预期该条目 payload 触发 trap（非法指令或访存异常）。"""
    return bool(TRAP_RET_VAL_RE.match(str(entry.get("ret_val", ""))))


def store_effective_address(entry: dict) -> tuple[int, int] | None:
    """解析 zSTORE 条目的 (有效地址, 访存宽度)；基址寄存器缺失或不可解析返回 None。"""
    match = STORE_EFFECT_RE.match(str(entry.get("test-ins", "")).strip())
    if match is None:
        return None
    size = STORE_ACCESS_SIZE[match.group(1)]
    try:
        offset = int(match.group(2), 0)
    except ValueError:
        return None
    base = match.group(3)
    if base == "x0":
        base_value = 0
    else:
        raw = (entry.get("isa-state") or {}).get(base)
        if raw is None:
            return None
        try:
            base_value = parse_bits(str(raw), base)
        except ValueError:
            return None
    return (base_value + offset) % (1 << 64), size


def classify_fault_preclass(entry: dict) -> tuple[str | None, str | None]:
    """W13 对账的 fault 条目预分类，返回 (skip 原因, 预分类标注)。

    (i) 有效地址低于 emu RAM 基界且错位：emu/NEMU mcause 分歧（7 vs 6），
    difftest 必 ABORT，跳过重放并计数。只限低位：高位回绕地址（如 -1 →
    0xffffffffffffffff）NEMU 按物理地址位宽截断后可对齐，两侧一致 fault
    （W12 case-010/017 实测 GOODTRAP），不属此类；
    (ii) 有效地址图内且对齐：Isla 假 fault 历史类（PMP 符号化），isla 修复后
    应消失，不跳过、仅标注计数；
    图内错位（emu 支持错位退休 vs Isla plat_enable_misaligned_access=false，
    W13 ⑤）当前用例集未触发，不在此处理。ok 类条目不参与预分类。
    """
    if not expects_trap(entry):
        return None, None
    resolved = store_effective_address(entry)
    if resolved is None:
        return None, None
    address, size = resolved
    misaligned = address % size != 0
    in_map = EMU_RAM_BASE <= address < EMU_RAM_LIMIT
    if address < EMU_RAM_BASE and misaligned:
        return SKIP_MCAUSE_DIVERGENCE, SKIP_MCAUSE_DIVERGENCE
    if in_map and not misaligned:
        return None, PRECLASS_INMAP_ALIGNED_FAULT
    return None, None


def parse_map_hypothesis(entry: dict) -> dict | None:
    """解析符号边界路径的地图假设（W17 侧通道 pma_regions.<name>.size）。

    返回 {regions, region, size, base, top, address}；无符号 size 键返回 None。
    顶界 top = base + size：单符号 region 按约定取 MAP_HYPOTHESIS_BASE（样本配置
    region "ram" 即 DRAM 基界，JSON 未携带 base 字段）；多符号 region 只记录各
    size、top 置 None。有效地址复用 store_effective_address（fault 路径
    memory-events 为空，从指令偏移+基址寄存器解析）；解析失败抛 ValueError——
    含符号 size 却无法核实访存地址的条目宁可构建失败，不可直接重放。
    """
    state = entry.get("isa-state")
    if not isinstance(state, dict):
        return None
    sizes: dict[str, int] = {}
    for key, raw in state.items():
        match = PMA_SIZE_KEY_RE.match(key)
        if match is None:
            continue
        sizes[match.group(1)] = parse_bits(str(raw), key)
    if not sizes:
        return None
    resolved = store_effective_address(entry)
    if resolved is None:
        raise ValueError(
            f"条目含符号 pma_regions size（{sorted(sizes)}）但无法解析有效地址，"
            "S4 地图假设过滤要求可核实的访存地址"
        )
    address, _ = resolved
    hypothesis = {
        "regions": dict(sizes),
        "region": next(iter(sizes)),
        "size": next(iter(sizes.values())),
        "base": MAP_HYPOTHESIS_BASE,
        "top": None,
        "address": address,
    }
    if len(sizes) == 1:
        hypothesis["top"] = (MAP_HYPOTHESIS_BASE + hypothesis["size"]) % (1 << 64)
    return hypothesis


def classify_map_hypothesis(
    entry: dict, map_limit: int = EMU_RAM_LIMIT
) -> tuple[str | None, dict | None]:
    """S4 地图假设过滤：符号边界路径的期望行为必须在真实地图下才可重放。

    成功路径要求有效地址 < map_limit（真实图内），fault 路径（expects_trap）要求
    有效地址 >= map_limit（真实图外）；一致返回 (None, hypothesis 记录)，不一致
    返回 (map-hypothesis-mismatch, 记录)。无符号 size 返回 (None, None)，对既有
    用例零影响。记录中 hypothesis_consistent 是假设自洽性诊断（ret_val 与
    地址/假设顶界 base+size 是否吻合，校验 base 约定），不参与过滤判定。
    """
    hypothesis = parse_map_hypothesis(entry)
    if hypothesis is None:
        return None, None
    address = hypothesis["address"]
    in_real_map = address < map_limit
    fault_expected = expects_trap(entry)
    consistent = in_real_map != fault_expected
    record = dict(hypothesis)
    record["real_limit"] = map_limit
    record["consistent_with_real_map"] = consistent
    top = hypothesis["top"]
    record["hypothesis_consistent"] = (
        None if top is None else (address < top) != fault_expected
    )
    return (None if consistent else SKIP_MAP_HYPOTHESIS_MISMATCH, record)


def read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict) or not isinstance(value.get("gen"), list):
        raise ValueError(f"{path} 不是 Isla gen JSON")
    return value


def source_entries(
    paths: list[Path], count: int, drop_vector_state: bool, ret_val_regex: str | None
) -> list[dict]:
    pattern = re.compile(ret_val_regex) if ret_val_regex else None
    entries: list[dict] = []
    for path in paths:
        for entry in read_json(path)["gen"]:
            instruction = entry.get("test-ins")
            encoding = entry.get("test-ins-encdec")
            arch = entry.get("arch", {})
            if not isinstance(instruction, str) or not isinstance(encoding, str):
                continue
            if arch.get("xlen") not in (64, "64"):
                continue
            if pattern is not None and not pattern.search(str(entry.get("ret_val", ""))):
                continue
            selected = copy.deepcopy(entry)
            selected["source_file"] = path.name
            if drop_vector_state:
                state = selected.get("isa-state", {})
                if isinstance(state, dict):
                    for name in list(state):
                        if VECTOR_RE.fullmatch(name):
                            del state[name]
            entries.append(selected)
            if count and len(entries) == count:
                return entries
    if not entries:
        raise ValueError("输入 JSON 中没有可用的 RV64 指令")
    return entries


def prepare(args: argparse.Namespace) -> None:
    sources = args.source or [str(DEFAULT_SOURCE)]
    entries = source_entries(
        [Path(p).resolve() for p in sources],
        args.count,
        args.drop_vreg_state,
        args.ret_val_regex,
    )
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "purpose": "从现有 Isla V JSON 选取的 XiangShan RVV 小样本",
        "source_json": [str(Path(p).resolve()) for p in sources],
        "vlen_bits": args.vlen_bits,
        "vector_state": "reset-zero" if args.drop_vreg_state else "from-isla-json",
        "selection_count": len(entries),
    }
    if args.ret_val_regex:
        metadata["ret_val_regex"] = args.ret_val_regex
    payload = {"metadata": metadata, "gen": entries}
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已写入 {output}（{len(entries)} 条）")


def parse_encoding(value: str) -> int:
    match = ENCODING_RE.fullmatch(value.strip())
    if match is None:
        raise ValueError(f"不支持的 test-ins-encdec: {value!r}")
    return int(match.group(1).replace("_", ""), 16)


def parse_bits(value: str, name: str, maximum_width: int = 64) -> int:
    match = BITS_RE.fullmatch(value.strip())
    if match is None:
        raise ValueError(f"{name} 不是无掩码十六进制位向量: {value!r}")
    width = int(match.group(1))
    if width < 1 or width > maximum_width:
        raise ValueError(f"{name} 位宽为 {width}，要求在 1..{maximum_width} 内")
    value = int(match.group(2).replace("_", ""), 16)
    if value >= 1 << width:
        raise ValueError(f"{name} 的值超出声明位宽")
    return value


def parse_memory_address(segment: dict, name: str) -> int | None:
    """解析内存段地址位向量；地址为 null 时返回 None（该段跳过）。"""
    value = segment.get("address")
    if value is None:
        return None
    return parse_bits(str(value), name, maximum_width=64)


def segment_size(segment: dict, name: str) -> int:
    size = segment.get("bytes")
    if not isinstance(size, int) or size < 1 or size > 2048:
        raise ValueError(f"{name}.bytes 必须是 1..2048 的整数，得到 {size!r}")
    return size


def segment_byte_values(segment: dict, size: int, fill: int, name: str) -> list[int]:
    """内存段 value → 小端逐字节序列；value 为 null 或超出声明位宽的字节用 fill 填充。"""
    value = segment.get("value")
    if value is None:
        return [fill] * size
    match = BITS_RE.fullmatch(str(value).strip())
    if match is None:
        raise ValueError(f"{name}.value 不是无掩码十六进制位向量: {value!r}")
    width = int(match.group(1))
    number = int(match.group(2).replace("_", ""), 16)
    return [(number >> (8 * index)) & 0xFF if 8 * index < width else fill for index in range(size)]


def memory_plan(entry: dict) -> dict:
    """解析 pre-memory/post-memory/memory-events，生成发射计划与 skip 计数。

    pre：地址 null 的段跳过并计数；value null（首触自由字节）按 0xA5 填充。
    post：地址或 value 为 null 的检查段跳过并计数；全部段皆 null 时整条跳过。
    """
    pre_raw = entry.get("pre-memory") or []
    post_raw = entry.get("post-memory") or []
    events = entry.get("memory-events") or []
    if not all(isinstance(item, list) for item in (pre_raw, post_raw, events)):
        raise ValueError("pre-memory/post-memory/memory-events 必须是数组")

    pre: list[dict] = []
    pre_fill_bytes = 0
    for index, segment in enumerate(pre_raw):
        address = parse_memory_address(segment, f"pre-memory[{index}]")
        if address is None:
            continue
        size = segment_size(segment, f"pre-memory[{index}]")
        values = segment_byte_values(segment, size, PRE_MEMORY_FILL, f"pre-memory[{index}]")
        if segment.get("value") is None:
            pre_fill_bytes += size
        pre.append({"address": address, "bytes": size, "values": values})

    post: list[dict] = []
    post_null = 0
    for index, segment in enumerate(post_raw):
        address = parse_memory_address(segment, f"post-memory[{index}]")
        if address is None or segment.get("value") is None:
            post_null += 1
            continue
        size = segment_size(segment, f"post-memory[{index}]")
        values = segment_byte_values(segment, size, PRE_MEMORY_FILL, f"post-memory[{index}]")
        post.append({"address": address, "bytes": size, "values": values})

    return {
        "pre": pre,
        "post": post,
        "events": events,
        "counts": {
            "pre_segments": len(pre_raw),
            "pre_emitted": len(pre),
            "pre_null_address": len(pre_raw) - len(pre),
            "pre_fill_bytes": pre_fill_bytes,
            "post_segments": len(post_raw),
            "post_emitted": len(post),
            "post_null": post_null,
        },
        "skip_entry": SKIP_POST_ALL_NULL if post_raw and not post else None,
        "raw": {
            "pre-memory": pre_raw,
            "post-memory": post_raw,
            "memory-events": events,
        },
    }


def pre_memory_stores(plan: dict) -> list[str]:
    """按 JSON 给定序（重放序）逐段逐字节 sb 恢复初始内存，仅用 t0/t1。"""
    lines: list[str] = []
    for index, segment in enumerate(plan["pre"]):
        lines.append(
            f"    # Isla pre-memory[{index}] 0x{segment['address']:x} len={segment['bytes']}"
            "（value null 按 0xa5 填充）"
        )
        lines.append(f"    li t0, 0x{segment['address']:x}")
        for offset, value in enumerate(segment["values"]):
            lines.append(f"    li t1, 0x{value:02x}")
            lines.append(f"    sb t1, {offset}(t0)")
    return lines


def post_memory_checks(plan: dict) -> tuple[list[str], list[str]]:
    """逐段逐字节 lbu 比对最终内存；失配跳该段专属 park 标号（死循环，超时判败）。"""
    lines: list[str] = []
    parks: list[str] = []
    for index, segment in enumerate(plan["post"]):
        park = f"post_park_{index}"
        lines.append(
            f"    # Isla post-memory[{index}] 0x{segment['address']:x} len={segment['bytes']}"
            f"：失配跳 {park}"
        )
        lines.append(f"    li t0, 0x{segment['address']:x}")
        for offset, value in enumerate(segment["values"]):
            lines.append(f"    li t1, 0x{value:02x}")
            lines.append(f"    lbu t2, {offset}(t0)")
            lines.append(f"    bne t2, t1, {park}")
        parks.extend([f"{park}:", f"    j {park}"])
    return lines, parks


def elf_alloc_ranges(elf: Path) -> list[tuple[int, int]]:
    """读取 ELF64 小端镜像中所有 ALLOC section 的 [起始, 结束) 区间（含 .bss）。"""
    data = elf.read_bytes()
    if len(data) < 64 or data[:4] != b"\x7fELF" or data[4] != 2 or data[5] != 1:
        raise ValueError(f"{elf} 不是 ELF64 小端文件")
    e_shoff = struct.unpack_from("<Q", data, 0x28)[0]
    e_shentsize = struct.unpack_from("<H", data, 0x3A)[0]
    e_shnum = struct.unpack_from("<H", data, 0x3C)[0]
    ranges: list[tuple[int, int]] = []
    for index in range(e_shnum):
        header = e_shoff + index * e_shentsize
        _, _, sh_flags, sh_addr, _, sh_size = struct.unpack_from("<IIQQQQ", data, header)
        if not sh_flags & SHF_ALLOC or sh_addr == 0 or sh_size == 0:
            continue
        ranges.append((sh_addr, sh_addr + sh_size))
    return ranges


def memory_overlaps_ranges(plan: dict, ranges: list[tuple[int, int]]) -> bool:
    """pre/post 段及 memory-events 触碰地址是否与给定代码区间（部分）重叠。"""

    def hits(address: int, size: int) -> bool:
        return any(address < end and start < address + size for start, end in ranges)

    segments = [(seg["address"], seg["bytes"]) for seg in plan["pre"] + plan["post"]]
    for index, event in enumerate(plan["events"]):
        address = parse_memory_address(event, f"memory-events[{index}]")
        size = event.get("bytes")
        if address is not None and isinstance(size, int) and size > 0:
            segments.append((address, size))
    return any(hits(address, size) for address, size in segments)


def parse_vector(value: str, vlen_bits: int) -> tuple[int, int]:
    try:
        width_text, digits = value.split("'h", 1)
        width = int(width_text)
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"无效向量寄存器值: {value!r}") from exc
    if width != vlen_bits:
        raise ValueError(
            f"JSON 向量状态为 {width} bit，但目标 XiangShan VLEN 为 {vlen_bits} bit；"
            "拒绝截断或补零以避免错误的 DiffTest 结论"
        )
    return int(digits.replace("_", ""), 16), width // 64


def encode_vsetvli(rd: int, rs1: int, vtypei: int) -> int:
    if not 0 <= vtypei < 1 << 11:
        raise ValueError(f"vsetvli 的 vtypei 超出 11 位: 0x{vtypei:x}")
    return (vtypei << 20) | (rs1 << 15) | (0b111 << 12) | (rd << 7) | 0x57


def encode_csrw(csr: int, rs1: int) -> int:
    return (csr << 20) | (rs1 << 15) | (0b001 << 12) | 0x73


def encode_vl1re8(vd: int, rs1: int) -> int:
    return (1 << 25) | (0b01000 << 20) | (rs1 << 15) | (vd << 7) | 0x07


def vtype_is_illegal(vtype: int, vlen_bits: int) -> bool:
    if vtype >> 63:
        return True
    if vtype & ~0xFF:
        return True
    vsew = (vtype >> 3) & 0b111
    vlmul = vtype & 0b111
    if vsew > 3 or vlmul == 0b100:
        return True
    sew = 1 << (vsew + 3)
    lmul_power = vlmul if vlmul < 4 else vlmul - 8
    return vlen_bits * (1 << max(lmul_power, 0)) < sew * (1 << max(-lmul_power, 0))


def vtype_vlmax(vtype: int, vlen_bits: int) -> int:
    if vtype_is_illegal(vtype, vlen_bits):
        raise ValueError(f"非法 vtype 0x{vtype:x} 没有可重建的 VLMAX")
    vsew = (vtype >> 3) & 0b111
    vlmul = vtype & 0b111
    sew = 1 << (vsew + 3)
    lmul_power = vlmul if vlmul < 4 else vlmul - 8
    numerator = vlen_bits * (1 << max(lmul_power, 0))
    denominator = sew * (1 << max(-lmul_power, 0))
    if numerator % denominator:
        raise ValueError(
            f"VLEN={vlen_bits}、vtype=0x{vtype:x} 得到非整数 VLMAX，无法重建硬件上下文"
        )
    return numerator // denominator


def vector_context_setup(state: dict, vlen_bits: int) -> tuple[list[str], list[str]]:
    context_registers = V_CONTEXT_REGISTERS.intersection(state)
    if not context_registers:
        return [], []
    if "vtype" not in state:
        raise ValueError("存在 V 扩展上下文，但 isa-state 缺少 vtype")

    vtype = parse_bits(str(state["vtype"]), "vtype")
    illegal_vtype = vtype_is_illegal(vtype, vlen_bits)
    if "vl" in state:
        vl = parse_bits(str(state["vl"]), "vl")
    elif illegal_vtype:
        vl = 0
    else:
        raise ValueError("合法 vtype 的 V 上下文必须显式提供 vl")
    if illegal_vtype and vl != 0:
        raise ValueError("非法 vtype 的硬件上下文必须具有 vl=0")
    if not illegal_vtype:
        vlmax = vtype_vlmax(vtype, vlen_bits)
        if vl > vlmax:
            raise ValueError(
                f"vl={vl} 超出 vtype=0x{vtype:x} 在 VLEN={vlen_bits} 下的 VLMAX={vlmax}；"
                "VSETVL 会静默截断，拒绝生成语义不一致的测试"
            )

    vtypei = 0x400 if illegal_vtype else vtype
    vsetvli_comment = (
        "vsetvli zero, t1, 0x400 (建立 VILL)"
        if illegal_vtype
        else f"vsetvli zero, t1, 0x{vtypei:x}"
    )
    before_loads = [
        f"    li t1, {vl}",
        f"    .4byte 0x{encode_vsetvli(0, T1, vtypei):08x} # {vsetvli_comment}",
    ]
    after_loads: list[str] = []
    if "vstart" in state:
        vstart = parse_bits(str(state["vstart"]), "vstart")
        after_loads.extend([
            f"    li t0, {vstart}",
            f"    .4byte 0x{encode_csrw(VSTART_CSR, T0):08x} # csrw vstart, t0",
        ])
    if "vcsr" in state:
        vcsr = parse_bits(str(state["vcsr"]), "vcsr", maximum_width=3)
        after_loads.extend([
            f"    li t0, {(vcsr >> 1) & 0b11}",
            f"    .4byte 0x{encode_csrw(VXRM_CSR, T0):08x} # csrw vxrm, t0",
            f"    li t0, {vcsr & 1}",
            f"    .4byte 0x{encode_csrw(VXSAT_CSR, T0):08x} # csrw vxsat, t0",
        ])
    return before_loads, after_loads


def vector_setup(state: dict, vlen_bits: int) -> tuple[list[str], list[str]]:
    registers = sorted((key for key in state if VECTOR_RE.fullmatch(key)), key=lambda key: int(key[2:]))
    if not registers:
        return [], []
    words: list[str] = []
    loads: list[str] = ["    la t0, vector_initial_state"]
    for index, name in enumerate(registers):
        value, word_count = parse_vector(str(state[name]), vlen_bits)
        if index == 0:
            expected_words = word_count
        elif word_count != expected_words:
            raise ValueError("同一 JSON 中存在不同宽度的向量寄存器")
        register = int(name[2:])
        loads.append(f"    .4byte 0x{encode_vl1re8(register, T0):08x} # vl1re8.v v{register}, (t0)")
        loads.append(f"    addi t0, t0, {word_count * 8}")
        for word in range(word_count):
            words.append(f"    .dword 0x{(value >> (64 * word)) & ((1 << 64) - 1):016x}")
    return loads, words


def scalar_setup(state: dict) -> list[str]:
    registers = sorted(
        (key for key in state if GPR_RE.fullmatch(key)), key=lambda key: int(key[1:])
    )
    loads: list[str] = []
    for name in registers:
        register = int(name[1:])
        value = parse_bits(str(state[name]), name)
        if register == 0:
            if value != 0:
                raise ValueError("x0 必须为零")
            continue
        loads.append(f"    li {name}, 0x{value:x}")
    return loads


def privilege_setup(state: dict) -> list[str]:
    privilege = state.get("cur_privilege", "Machine")
    if privilege == "Machine":
        return ["payload:"]
    mpp = {"User": 0, "Supervisor": 1}.get(privilege)
    if mpp is None:
        raise ValueError(f"不支持的 cur_privilege: {privilege!r}")
    return [
        "    li t0, -1",
        f"    .4byte 0x{encode_csrw(PMPADDR0_CSR, T0):08x} # csrw pmpaddr0, t0",
        "    li t0, 0x1f",
        f"    .4byte 0x{encode_csrw(PMPCFG0_CSR, T0):08x} # csrw pmpcfg0, t0",
        "    la t0, payload",
        "    csrw mepc, t0",
        "    csrr t0, mstatus",
        "    li t1, -6145",
        "    and t0, t0, t1",
        f"    li t1, {mpp << 11}",
        "    or t0, t0, t1",
        "    csrw mstatus, t0",
        "    mret",
        "payload:",
    ]


def make_assembly(entry: dict, vlen_bits: int, plan: dict | None = None) -> str:
    instruction = str(entry["test-ins"])
    encoding = parse_encoding(str(entry["test-ins-encdec"]))
    state = entry.get("isa-state", {})
    if not isinstance(state, dict):
        raise ValueError("isa-state 必须是对象")
    context_before_loads, context_after_loads = vector_context_setup(state, vlen_bits)
    loads, words = vector_setup(state, vlen_bits)
    scalar_loads = scalar_setup(state)
    expect_trap = expects_trap(entry)
    if plan is None:
        plan = memory_plan(entry)
    # 装配序固定：[特权/向量上下文] → [pre store] → [标量 li] → payload → [post 检查] → GOODTRAP/park；
    # pre store 只用 t0/t1，必须先于标量装载，避免破坏 JSON 标量值
    pre_lines = pre_memory_stores(plan)
    if expect_trap:
        # fault 路径维持既有哨兵+handler 机制（mepc==payload_ins 判 GOODTRAP），不做 post 检查
        post_lines, park_lines = [], []
    else:
        post_lines, park_lines = post_memory_checks(plan)
    init = [
        "    csrr t0, mstatus",
        "    li t1, 0x600",
        "    or t0, t0, t1",
        "    csrw mstatus, t0",
        "    # 清零 medeleg：emu 默认 medeleg=0x1444 会把 U-mode 非法指令委托到 stvec=0",
        "    csrw medeleg, x0",
        "    # 任何 trap 进入 M-mode trap_handler，由 mepc 是否等于 payload 区分 trap 位置",
        "    la t0, trap_handler",
        "    csrw mtvec, t0",
    ] + context_before_loads + loads + context_after_loads + privilege_setup(state) + pre_lines + scalar_loads
    if expect_trap:
        payload_tail = [
            "    # Isla 预期该指令 trap：payload 未 trap 时，哨兵全零非法指令必然触发，",
            "    # handler 以 mepc!=payload_ins 挂起暴露",
            "    .4byte 0x00000000",
        ]
        trap_handler = [
            "trap_handler:",
            "    csrr t0, mepc",
            "    la t1, payload_ins",
            "    bne t0, t1, 2f",
            "    # payload_ins 处 trap，与 Isla 预期一致",
            "    # XiangShan DiffTest STATE_GOODTRAP custom instruction.",
            "    .4byte 0x0000006b",
            "2:  j 2b",
        ]
    else:
        payload_tail = post_lines + [
            "    # XiangShan DiffTest STATE_GOODTRAP custom instruction.",
            "    .4byte 0x0000006b",
        ]
        trap_handler = [
            "trap_handler:",
            "    # 不预期 trap：任何 trap 在此挂起，由超时判定失败",
            "2:  j 2b",
        ]
    # 无 vreg 条目不发射占位数据段：8 字节 .dword 0 会让 .data 落在链接脚本
    # 0x80001000 对齐位，与以该地址为访存窗口的用例精确相撞（code-overlap 误伤）
    if words:
        tail = [".section .data", ".align 3", "vector_initial_state:", "\n".join(words), ""]
    else:
        tail = []
    return "\n".join([
        ".option norvc", ".section .text.init", ".globl _start", "_start:",
        *init,
        "payload_ins:",
        f"    # Isla: {instruction}", f"    .4byte 0x{encoding:08x}",
        *payload_tail,
        "1:  j 1b",
        *park_lines,
        *trap_handler,
        *tail,
    ])


LINKER = """OUTPUT_ARCH(\"riscv\")
ENTRY(_start)
SECTIONS {
  . = 0x80000000;
  .text.init : { KEEP(*(.text.init)) }
  . = ALIGN(0x1000); .text : { *(.text .text.*) }
  . = ALIGN(0x1000); .data : { *(.data .data.* .sdata .sdata.*) }
  .bss (NOLOAD) : { *(.bss .bss.* COMMON) }
  /DISCARD/ : { *(.comment) *(.note*) *(.riscv.attributes) }
}
"""


def compile_case(
    index: int,
    entry: dict,
    output: Path,
    linker: Path,
    compiler: str,
    vlen_bits: int,
    map_limit: int = EMU_RAM_LIMIT,
) -> dict:
    case_dir = output / f"case-{index:03d}"
    plan = memory_plan(entry)
    case = {
        "id": case_dir.name,
        "instruction": entry["test-ins"],
        "encoding": entry["test-ins-encdec"],
        "isa-state": entry.get("isa-state", {}),
        "ret_val": entry.get("ret_val"),
        "expect_trap": expects_trap(entry),
        "path_class": "fault" if expects_trap(entry) else "ok",
        "source_file": entry.get("source_file"),
        "memory": {**plan["counts"], **plan["raw"]},
        "skipped_reason": None,
        "preclass": None,
        "map_hypothesis": None,
    }
    # S4 地图假设过滤先于 fault 预分类：符号边界假设与真实地图不符的路径直接跳过
    hypothesis_skip, hypothesis = classify_map_hypothesis(entry, map_limit)
    if hypothesis is not None:
        case["map_hypothesis"] = hypothesis
        if hypothesis_skip:
            case["skipped_reason"] = hypothesis_skip
            return case
    if case["expect_trap"]:
        preclass_skip, preclass_tag = classify_fault_preclass(entry)
        case["preclass"] = preclass_tag
        if preclass_skip:
            case["skipped_reason"] = preclass_skip
            return case
    if plan["skip_entry"]:
        case["skipped_reason"] = plan["skip_entry"]
        return case
    case_dir.mkdir(exist_ok=True)
    assembly = case_dir / "program.S"
    elf = case_dir / "program.elf"
    assembly.write_text(make_assembly(entry, vlen_bits, plan), encoding="utf-8")
    command = [compiler, "-nostdlib", "-nostartfiles", "-static", "-fno-pic", "-march=rv64gc", "-mabi=lp64d", "-Wl,-T," + str(linker), "-Wl,-e,_start", "-o", str(elf), str(assembly)]
    # 两遍构建：第一遍链接后读 section 实际占用范围，内存地址与代码重叠的条目精确跳过
    subprocess.run(command, check=True)
    if memory_overlaps_ranges(plan, elf_alloc_ranges(elf)):
        elf.unlink()
        case["skipped_reason"] = SKIP_CODE_OVERLAP
        return case
    # 第二遍：重新生成最终 ELF（多一次链接换取不牺牲可重放条目）
    subprocess.run(command, check=True)
    digest = hashlib.sha256(elf.read_bytes()).hexdigest()
    case["elf"] = str(elf)
    case["sha256"] = digest
    (case_dir / "case.json").write_text(json.dumps(case, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return case


def sample_entries(entries: list[dict], mode: str) -> tuple[list[dict], int]:
    """按采样模式过滤条目；返回 (保留列表, 采样丢弃数)。默认全量。"""
    if mode == "all":
        return list(entries), 0
    if mode == "first-per-encoding":
        kept: list[dict] = []
        seen: set[str] = set()
        for entry in entries:
            key = str(entry.get("test-ins-encdec", ""))
            if key in seen:
                continue
            seen.add(key)
            kept.append(entry)
        return kept, len(entries) - len(kept)
    raise ValueError(f"未知 --sample-mode: {mode!r}，可选 {SAMPLE_MODES}")


def build(args: argparse.Namespace) -> None:
    source = read_json(Path(args.input).resolve())
    metadata = source.get("metadata", {})
    source_vlen = metadata.get("vlen_bits")
    if source_vlen is not None and source_vlen != args.vlen_bits:
        raise ValueError(f"样本声明 VLEN={source_vlen}，但构建参数是 {args.vlen_bits}")
    entries, sampled_out = sample_entries(source["gen"], args.sample_mode)
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    linker = output / "xiangshan.ld"
    linker.write_text(LINKER, encoding="utf-8")
    if args.jobs < 1:
        raise ValueError("--jobs 必须至少为 1")
    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        manifest = list(
            executor.map(
                lambda pair: compile_case(
                    pair[0], pair[1], output, linker, args.compiler, args.vlen_bits, args.map_limit
                ),
                enumerate(entries),
            )
        )
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    skipped: dict[str, int] = {}
    preclass: dict[str, int] = {}
    for case in manifest:
        if case.get("skipped_reason"):
            skipped[case["skipped_reason"]] = skipped.get(case["skipped_reason"], 0) + 1
        if case.get("preclass"):
            preclass[case["preclass"]] = preclass.get(case["preclass"], 0) + 1
    summary = {
        "sample_mode": args.sample_mode,
        "total_entries": len(source["gen"]),
        "sampled_out": sampled_out,
        "built": sum(1 for case in manifest if case.get("elf")),
        "skipped": skipped,
        "preclass": preclass,
        "map_hypothesis": {
            "checked": sum(1 for case in manifest if case.get("map_hypothesis")),
            "skipped": skipped.get(SKIP_MAP_HYPOTHESIS_MISMATCH, 0),
        },
        "path_class": {
            "ok": sum(1 for case in manifest if case["path_class"] == "ok"),
            "fault": sum(1 for case in manifest if case["path_class"] == "fault"),
        },
    }
    (output / BUILD_SUMMARY).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"已生成 {summary['built']} 个 ELF（共 {len(manifest)} 条，跳过 {skipped or '无'}）：{output}"
    )


def timeout_partial_output(exc: subprocess.TimeoutExpired) -> str:
    partial = exc.stdout or ""
    if isinstance(partial, bytes):
        partial = partial.decode(errors="replace")
    return partial


def run_case(case: dict, emulator: Path, diff_so: Path, timeout: int) -> dict:
    started = time.monotonic()
    command = [str(emulator), "-i", case["elf"], "--diff", str(diff_so)]
    log = Path(case["elf"]).parent / "difftest.log"
    proc = None
    try:
        proc = subprocess.Popen(
            command,
            text=True,
            stdout=subprocess.PIPE,
            # 新版 emu 把 HIT GOOD TRAP 输出到 stderr,必须合并才能正确判定
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        stdout, _ = proc.communicate(timeout=timeout)
        completed = subprocess.CompletedProcess(command, proc.returncode, stdout=stdout)
    except subprocess.TimeoutExpired as exc:
        # 杀掉整个进程组(含 emu 的仿真线程 + NEMU so 线程)
        if proc is not None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                proc.kill()
            try:
                output, _ = proc.communicate(timeout=5)
            except Exception:
                output = timeout_partial_output(exc)
        else:
            output = timeout_partial_output(exc)
        try:
            traced_proc = subprocess.Popen(
                command + ["--dump-commit-trace"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            traced_out, _ = traced_proc.communicate(timeout=timeout)
            output = traced_out
        except subprocess.TimeoutExpired as trace_exc:
            try:
                os.killpg(traced_proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError, UnboundLocalError):
                pass
            trace_partial = timeout_partial_output(trace_exc)
            if trace_partial:
                output = trace_partial
        log.write_text(
            f"DiffTest execution timeout after {timeout}s\n{output}",
            encoding="utf-8",
        )
        return {
            **case,
            "returncode": None,
            "category": "failure",
            "log": str(log),
            "elapsed": round(time.monotonic() - started, 3),
        }
    category = (
        "success"
        if completed.returncode == 0 and "HIT GOOD TRAP" in completed.stdout
        else "failure"
    )
    # ABORT/非零退出的第一跑 stdout 已含 different-at/ABORT/REF dump，直接作为日志；
    # 只有 timeout 才重跑 --dump-commit-trace 定位停止点
    log.write_text(
        "HIT GOOD TRAP\n" if category == "success" else completed.stdout,
        encoding="utf-8",
    )
    return {
        **case,
        "returncode": completed.returncode,
        "category": category,
        "log": str(log),
        "elapsed": round(time.monotonic() - started, 3),
    }


def load_recorded_results(ndjson: Path) -> list[dict]:
    """读取已有 results.ndjson，返回完整记录列表；半行（进程中断残留）打印警告后跳过。"""
    results: list[dict] = []
    if not ndjson.is_file():
        return results
    for line in ndjson.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            print(f"警告：{ndjson} 存在不完整行，已跳过: {line[:80]!r}", file=sys.stderr)
            continue
        results.append(record)
    return results


def run(args: argparse.Namespace) -> None:
    cases_dir = Path(args.cases).resolve()
    cases = json.loads((cases_dir / "manifest.json").read_text(encoding="utf-8"))
    emulator, diff_so = Path(args.emulator), Path(args.diff_so)
    if not emulator.is_file() or not diff_so.is_file():
        raise ValueError("XIANGSHAN_EMU 或 XIANGSHAN_DIFF_SO 不存在")
    if args.jobs < 1:
        raise ValueError("--jobs 必须至少为 1")
    ndjson_path = cases_dir / RESULTS_NDJSON
    results = load_recorded_results(ndjson_path)
    completed_ids = {record["id"] for record in results}
    runnable = [case for case in cases if case.get("elf")]
    pending = [case for case in runnable if case["id"] not in completed_ids]
    print(
        f"共 {len(cases)} 条（可运行 {len(runnable)}、构建期跳过 {len(cases) - len(runnable)}）；"
        f"已完成 {len(completed_ids)} 条；本次运行 {len(pending)} 条"
    )
    needs_separator = (
        ndjson_path.is_file()
        and ndjson_path.stat().st_size > 0
        and ndjson_path.read_bytes()[-1:] != b"\n"
    )
    with ndjson_path.open("a", encoding="utf-8") as stream:
        if needs_separator:
            # 上次中断残留的半行没有换行结尾，先隔断，避免新记录拼接成损坏行
            stream.write("\n")
        done = len(completed_ids)
        with ThreadPoolExecutor(max_workers=args.jobs) as executor:
            futures = [
                executor.submit(run_case, case, emulator, diff_so, args.timeout)
                for case in pending
            ]
            for future in as_completed(futures):
                result = future.result()
                stream.write(json.dumps(result, ensure_ascii=False) + "\n")
                stream.flush()
                results.append(result)
                done += 1
                print(f"[{done}/{len(cases)}] {result['id']} {result['category']} ({result['elapsed']}s)")
    results_path = cases_dir / "results.json"
    results_path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    failures = sum(item["category"] != "success" for item in results)
    print(f"DiffTest 完成：{len(results) - failures}/{len(results)} success；{results_path}")
    if failures:
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare-json")
    prepare_parser.add_argument("--source", action="append")
    prepare_parser.add_argument("--count", type=int, default=0, help="保留前 N 条；0 表示保留全部")
    prepare_parser.add_argument("--vlen-bits", type=int, default=128)
    prepare_parser.add_argument(
        "--drop-vreg-state",
        action="store_true",
        help="丢弃与目标 VLEN 不兼容的 Isla vreg 初始状态，使用硬件复位零值",
    )
    prepare_parser.add_argument("--output", default=str(DEFAULT_OUT / "isla-vvtype.json"))
    prepare_parser.add_argument(
        "--ret-val-regex",
        default=None,
        help="仅保留 ret_val 匹配该正则的条目；缺省保留全部",
    )
    build_parser = commands.add_parser("build")
    build_parser.add_argument("--input", default=str(DEFAULT_OUT / "isla-vvtype.json"))
    build_parser.add_argument("--output", default=str(DEFAULT_OUT / "elf"))
    build_parser.add_argument("--vlen-bits", type=int, default=128)
    build_parser.add_argument("--compiler", default="riscv64-unknown-elf-gcc")
    build_parser.add_argument("--jobs", type=int, default=1, help="并行编译的进程数")
    build_parser.add_argument(
        "--sample-mode",
        default="all",
        choices=list(SAMPLE_MODES),
        help="采样模式：all 全量（默认）；first-per-encoding 每个编码仅保留首条",
    )
    build_parser.add_argument(
        "--map-limit",
        type=lambda value: int(value, 0),
        default=EMU_RAM_LIMIT,
        help=(
            "S4 地图假设过滤的目标平台真实 RAM 顶界（支持十六进制；"
            f"默认 emu 实测 0x{EMU_RAM_LIMIT:x}）"
        ),
    )
    run_parser = commands.add_parser("run")
    run_parser.add_argument("--cases", default=str(DEFAULT_OUT / "elf"))
    run_parser.add_argument("--emulator", required=True)
    run_parser.add_argument("--diff-so", required=True)
    run_parser.add_argument("--timeout", type=int, default=120)
    run_parser.add_argument("--jobs", type=int, default=1, help="并行运行的 DiffTest 数量")
    args = parser.parse_args()
    {"prepare-json": prepare, "build": build, "run": run}[args.command](args)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        raise SystemExit(2)
