#!/usr/bin/env python3
"""Isla JSON 到 Ara 仿真器的单指令 PoC 批处理链路。

流程与 difftest-xiangshan/pipeline.py 同构：
  prepare: 从 isla/output/*.json 按 clause 抽样，生成输入样本 JSON
  build:   样本 JSON -> 每用例一个 .S -> 交叉编译成 ELF（含 Ara 测试环境退出序列）
  run:     并行调用 Ara Verilator emu，按退出码分类
  report:  汇总 clause x 结果矩阵

Ara 测试环境约定（commit 34bd3bc1）：
  - ELF 镜像从 0x80000000 起加载（tb "ram" 区域，1 MiB 窗口，无 bootrom）
  - 退出 = 向 CTRL 外设 0xD0000000 写值；进程退出码 = 写入值（bit31 丢失）
  - 向量指令由 CVA6 first-pass decoder 硬件自动 offload 给 Ara，无需软件调度
  - mstatus.VS（以及 FS）必须置 Dirty，否则向量指令按 illegal 处理
  - 只实现 RVV 1.0 base；Zvbb/Zvk* 等扩展指令应 trap illegal
  - emu 参数顺序必须是 `-c N -l ram,FILE,elf`：simctl 先解析并重排 argv，
    若 -l 在前，其值会被挪走导致 memutil 把 -c 当作 -l 的参数
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE_DIR = ROOT.parent / "isla" / "output"
DEFAULT_OUT = ROOT / "work"
# 与 isla 配置对齐（VLEN=128）的 emu；2048 版在 hardware/build/verilator
EMU_DEFAULT = ROOT / "ara" / "hardware" / "build-v128" / "verilator" / "Vara_tb_verilator"
# Ara pin 的 spike（riscv_tests_spike 同款 golden），make riscv-isa-sim 产物
SPIKE_DEFAULT = ROOT / "ara" / "install" / "riscv-isa-sim" / "bin" / "spike"
# 0003 补丁版 spike（Ara vtrace 流程同款）：交互模式支持管道驱动，golden 提取用
SPIKE_MOD_DEFAULT = ROOT / "ara" / "install" / "riscv-isa-sim-mod" / "bin" / "spike"

ENCODING_RE = re.compile(r"(?:32|64)'h([0-9a-fA-F_]+)$")
# 位向量字面量：宽度 + 'h/'b/'d 进制（isla 输出混用 128'h.. 与 128'd0）
BITS_RE = re.compile(r"(\d+)'([hbd])([0-9a-fA-F_]+)$")
VECTOR_RE = re.compile(r"^vr([0-9]|[12][0-9]|3[01])$")
GPR_RE = re.compile(r"^x([0-9]|[12][0-9]|3[01])$")
FPR_RE = re.compile(r"^f([0-9]|[12][0-9]|3[01])$")
# isla-state 中允许出现的键；出现其他键说明生成器落后于数据，直接报错
KNOWN_STATE_KEYS = {
    "cur_privilege", "mstatus", "vcsr", "vl", "vstart", "vtype",
} | {f"vr{i}" for i in range(32)} | {f"x{i}" for i in range(32)} | {f"f{i}" for i in range(32)}

VSTART_CSR = 0x008
VXSAT_CSR = 0x009
VXRM_CSR = 0x00A
T0 = 5
T1 = 6

# 默认 VLEN 与 isla IR 对齐（vlen_exp=7 → 128 bit；ELEN=64）。
# Ara 侧用 config=2_lanes vlen=128 的独立 buildpath 构建，
# spike 侧用 --isa=...zvl128b（Ara runtime.mk 的 RISCV_SIM_OPT 同款参数化）。
DEFAULT_VLEN_BITS = 128

# 退出码（写入 0xD0000000 的值）。ctrl_registers 的 exit_o 是 32 位
# {exit[30:0], 写脉冲}，tb 的 $finish(exit_o >> 1) 只剥离脉冲位，
# 因此进程退出码 = 写入值本身（bit31 丢失，小值不受影响）。
EXIT_PASS_SUCCESS = 0           # 期望 Retire_Success，正常退休
EXIT_RET_UNEXP_ILLEGAL = 2      # isla 说 Success，Ara 退休了但本路径不可达（保留）
EXIT_PASS_ILLEGAL = 4           # 期望 Illegal，确实 mcause=2
EXIT_TRAP_ILLEGAL_UNEXP = 6     # 期望 Success，却 trap illegal
EXIT_TRAP_OTHER_UNEXP = 8       # 期望 Success，却 trap 其他异常
EXIT_TRAP_OTHER_EXP_ILLEGAL = 10  # 期望 Illegal，trap 但 mcause!=2
EXIT_PASS_MEM_EXC = 12          # 期望 Memory_Exception，发生任意 trap
EXIT_RET_UNEXP_MEM_EXC = 14     # 期望 Memory_Exception，却正常退休
EXIT_INIT_TRAP = 32             # 初始化阶段 trap（基础设施问题）

EXIT_CLASS = {
    EXIT_PASS_SUCCESS: "pass_success",
    EXIT_PASS_ILLEGAL: "pass_illegal_confirmed",
    EXIT_PASS_MEM_EXC: "pass_memexc_confirmed",
    EXIT_TRAP_ILLEGAL_UNEXP: "fail_trap_illegal_expected_success",
    EXIT_TRAP_OTHER_UNEXP: "fail_trap_other_expected_success",
    EXIT_RET_UNEXP_ILLEGAL: "mismatch_retired_expected_illegal",
    EXIT_TRAP_OTHER_EXP_ILLEGAL: "mismatch_trap_other_expected_illegal",
    EXIT_RET_UNEXP_MEM_EXC: "mismatch_retired_expected_memexc",
    EXIT_INIT_TRAP: "init_phase_trap",
}

EXPECTED_CLASS = {
    "Retire_Success": "success",
    "Illegal_Instruction": "illegal",
    "Memory_Exception": "mem_exc",
}


def read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict) or not isinstance(value.get("gen"), list):
        raise ValueError(f"{path} 不是 Isla gen JSON")
    return value


# ---------------------------------------------------------------- prepare


def source_entries(paths: list[Path], per_clause: int, clause_filter: re.Pattern | None) -> list[dict]:
    """按 clause（文件名）分组抽样：每个 (clause, ret_val) 桶取前 per_clause 条。"""
    entries: list[dict] = []
    for path in paths:
        clause = path.stem.replace("rv64_z", "")
        if clause_filter and not clause_filter.search(clause):
            continue
        buckets: dict[str, list[dict]] = defaultdict(list)
        for entry in read_json(path)["gen"]:
            ret_val = str(entry.get("ret_val", "")).split("(")[0]
            if ret_val not in EXPECTED_CLASS:
                continue
            if len(buckets[ret_val]) < per_clause:
                buckets[ret_val].append(entry)
        for ret_val, bucket in buckets.items():
            for entry in bucket:
                selected = dict(entry)
                selected["_clause"] = clause
                selected["_ret_val"] = ret_val
                entries.append(selected)
    if not entries:
        raise ValueError("输入 JSON 中没有可用条目")
    return entries


def prepare(args: argparse.Namespace) -> None:
    sources = args.source or sorted(DEFAULT_SOURCE_DIR.glob("rv64_z*.json"))
    paths = [Path(p).resolve() for p in sources]
    entries = source_entries(paths, args.per_clause, args.clause_filter and re.compile(args.clause_filter))
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "metadata": {
            "purpose": "Ara PoC 批量测试抽样",
            "source_json": [str(p) for p in paths],
            "ara_vlen_bits": args.vlen_bits,
            "vreg_zero_extend": True,
            "per_clause_per_bucket": args.per_clause,
            "selection_count": len(entries),
        },
        "gen": entries,
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已写入 {output}（{len(entries)} 条）")


# ---------------------------------------------------------------- 编码辅助


def parse_encoding(value: str) -> int:
    match = ENCODING_RE.fullmatch(value.strip())
    if match is None:
        raise ValueError(f"不支持的 test-ins-encdec: {value!r}")
    return int(match.group(1).replace("_", ""), 16)


def _parse_literal(match: re.Match, name: str) -> tuple[int, int]:
    width = int(match.group(1))
    base = {"h": 16, "b": 2, "d": 10}[match.group(2)]
    digits = match.group(3).replace("_", "")
    value = int(digits, base) if digits else 0
    if value.bit_length() > width:
        raise ValueError(f"{name} 值 {value:#x} 超出声明位宽 {width}")
    return value, width


def parse_bits(value: str, name: str, maximum_width: int = 64) -> int:
    match = BITS_RE.fullmatch(value.strip())
    if match is None:
        raise ValueError(f"{name} 不是无掩码位向量: {value!r}")
    value, width = _parse_literal(match, name)
    if width > maximum_width:
        raise ValueError(f"{name} 宽度 {width} 超过 {maximum_width} 位")
    return value


def parse_vector(value: str, name: str, vlen_bits: int = DEFAULT_VLEN_BITS) -> int:
    """解析向量寄存器值。宽度允许小于目标 VLEN：装载时高位补零。

    默认 VLEN=128 与 isla IR（vlen_exp=7）完全一致，装载即精确；
    仅当 JSON 宽度 < 目标 VLEN 时才零扩展（文档化折衷）。
    """
    match = BITS_RE.fullmatch(value.strip())
    if match is None:
        raise ValueError(f"{name} 不是无掩码位向量: {value!r}")
    value, width = _parse_literal(match, name)
    if width > vlen_bits:
        raise ValueError(f"{name} 宽度 {width} 超过目标 VLEN {vlen_bits}")
    if width not in (8, 16, 32, 64, 128, 256, 512, 1024, 2048):
        raise ValueError(f"{name} 宽度 {width} 不是 2 的幂字节宽度")
    return value


def encode_vsetvli(rd: int, rs1: int, vtypei: int) -> int:
    if not 0 <= vtypei < 1 << 11:
        raise ValueError(f"vsetvli 的 vtypei 超出 11 位: 0x{vtypei:x}")
    return (vtypei << 20) | (rs1 << 15) | (0b111 << 12) | (rd << 7) | 0x57


def encode_csrs(csr: int, rs1: int) -> int:
    return (csr << 20) | (rs1 << 15) | (0b010 << 12) | 0x73


def encode_csrw(csr: int, rs1: int) -> int:
    return (csr << 20) | (rs1 << 15) | (0b001 << 12) | 0x73


def encode_vl1re8(vd: int, rs1: int) -> int:
    """RVV 1.0 whole-register load（nf=1, lumop=01000），与 vtype/vl 无关。"""
    return (1 << 25) | (0b01000 << 20) | (rs1 << 15) | (vd << 7) | 0x07


def encode_vs1r(vd: int, rs1: int) -> int:
    """RVV 1.0 whole-register store（vs1r.v），与 vtype/vl 无关。经汇编器核对：v0,(t0)=0x02828027。"""
    return (1 << 25) | (0b01000 << 20) | (rs1 << 15) | (vd << 7) | 0x27


def signature_size(vlen_bits: int) -> int:
    """签名区大小：x1-x31 + vl/vtype/vstart/vcsr + 32 个向量寄存器。"""
    return (31 + 4) * 8 + 32 * (vlen_bits // 8)


def dump_sequence(vlen_bits: int) -> list[str]:
    """把执行后架构状态导出到 sig_region（t6 作基址）。

    布局：x1..x31（31x8B）| vl,vtype,vstart,vcsr（4x8B）| v0..v31（32xVLEN/8）。
    先用 `sd t6, x31 槽(t6)` 保存 t6 原值（此时 t6 尚未被修改），
    之后 t6 作游标存 x1..x30 与 CSR（t5 作 scratch，已在最后），最后 vs1r.v 导出向量组。
    """
    lines = [
        "    # signature dump",
        "    la t6, sig_region",
        "    sd t6, 240(t6)",  # x31 原值（此刻 t6 尚未被修改；x1..x30 占 0..240）
    ]
    for reg in range(1, 31):  # x1..x30
        lines.append(f"    sd x{reg}, 0(t6)")
        lines.append("    addi t6, t6, 8")
    for name, csr in (("vl", 0xC20), ("vtype", 0xC21), ("vstart", VSTART_CSR), ("vcsr", 0x00F)):
        # csrr = CSRRS rd, csr, x0（rs1 必须为 x0，否则变成写只读 CSR -> illegal）
        lines.append(f"    .4byte 0x{(csr << 20) | (0b010 << 12) | (T1 << 7) | 0x73:08x} # csrr t1, {name}")
        lines.append("    sd t1, 0(t6)")
        lines.append("    addi t6, t6, 8")
    stride = vlen_bits // 8
    lines.append("    mv t1, t6")  # t1 = 向量区基址（此刻 t1 已不再被 CSR 读使用）
    for vd in range(32):
        lines.append(f"    .4byte 0x{encode_vs1r(vd, T1):08x} # vs1r.v v{vd}, (t1)")
        lines.append(f"    addi t1, t1, {stride}")
    return lines


def vtype_is_illegal(vtype: int, vlen_bits: int = DEFAULT_VLEN_BITS) -> bool:
    """vtypei 合法性：bit63(硬编码 vill)、bit[10:8] 非零、SEW/LMUL 组合非法。"""
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


def vtype_vlmax(vtype: int, vlen_bits: int = DEFAULT_VLEN_BITS) -> int:
    vsew = (vtype >> 3) & 0b111
    vlmul = vtype & 0b111
    sew = 1 << (vsew + 3)
    lmul_power = vlmul if vlmul < 4 else vlmul - 8
    numerator = vlen_bits * (1 << max(lmul_power, 0))
    denominator = sew * (1 << max(-lmul_power, 0))
    if numerator % denominator:
        raise ValueError(f"vtype=0x{vtype:x} 在 VLEN={vlen_bits} 下 VLMAX 非整数")
    return numerator // denominator


# ---------------------------------------------------------------- 汇编生成


def vector_context_setup(state: dict, vlen_bits: int = DEFAULT_VLEN_BITS) -> tuple[list[str], list[str]]:
    """vtype + vl 精确重建。vill 时用 zimm=0x400 建立非法类型，vl 必须为 0。

    返回 (装载前序列, 装载后序列)：vsetvli 在向量寄存器装载前执行，
    vstart/vxrm/vxsat 在装载后执行（whole-register load 与 vtype/vl 无关，
    但 vstart 不应被装载序列干扰）。
    """
    context_keys = {"vl", "vtype", "vstart", "vcsr"}.intersection(state)
    if not context_keys:
        return [], []
    if "vtype" not in state:
        raise ValueError("存在 V 上下文，但 isa-state 缺少 vtype")

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
    if not illegal_vtype and vl > vtype_vlmax(vtype, vlen_bits):
        raise ValueError(
            f"vl={vl} 超出 vtype=0x{vtype:x} 在 VLEN={vlen_bits} 下的 VLMAX={vtype_vlmax(vtype, vlen_bits)}"
        )

    vtypei = 0x400 if illegal_vtype else vtype
    comment = "vsetvli zero, t1, 0x400 (建立 VILL)" if illegal_vtype else f"vsetvli zero, t1, 0x{vtypei:x}"
    before_loads = [
        f"    li t1, {vl}",
        f"    .4byte 0x{encode_vsetvli(0, T1, vtypei):08x} # {comment}",
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


def vector_setup(state: dict, vlen_bits: int = DEFAULT_VLEN_BITS) -> tuple[list[str], list[str]]:
    """32 个向量寄存器 whole-register 装载；数据块按目标 VLEN 零扩展。"""
    if not any(VECTOR_RE.fullmatch(key) for key in state):
        return [], []
    words: list[str] = []
    loads: list[str] = ["    la t0, vector_initial_state"]
    word_count = vlen_bits // 64
    for index in range(32):
        name = f"vr{index}"
        value = parse_vector(str(state.get(name, "128'd0")), name, vlen_bits)
        loads.append(f"    .4byte 0x{encode_vl1re8(index, T0):08x} # vl1re8.v v{index}, (t0)")
        loads.append(f"    addi t0, t0, {word_count * 8}")
        for word in range(word_count):
            words.append(f"    .dword 0x{(value >> (64 * word)) & ((1 << 64) - 1):016x}")
    return loads, words


def scalar_setup(state: dict) -> list[str]:
    lines: list[str] = []
    for name in sorted((key for key in state if GPR_RE.fullmatch(key)), key=lambda k: int(k[1:])):
        register = int(name[1:])
        value = parse_bits(str(state[name]), name)
        if register == 0:
            if value != 0:
                raise ValueError("x0 必须为零")
            continue
        lines.append(f"    li {name}, 0x{value:x}")
    return lines


def fpr_setup(state: dict) -> tuple[list[str], list[str]]:
    """FPR 装载：32 个 f 寄存器从数据块 fld。返回 (装载序列, 数据行)。"""
    registers = sorted((key for key in state if FPR_RE.fullmatch(key)), key=lambda k: int(k[1:]))
    if not registers:
        return [], []
    loads = ["    la t0, fpr_initial_state"]
    words: list[str] = []
    for index in range(32):
        name = f"f{index}"
        value = parse_bits(str(state.get(name, "64'd0")), name)
        loads.append(f"    fld f{index}, 0(t0)")
        loads.append(f"    addi t0, t0, 8")
        words.append(f"    .dword 0x{value:016x}")
    return loads, words


def mstatus_setup(state: dict) -> list[str]:
    lines: list[str] = []
    if "mstatus" in state:
        mstatus = parse_bits(str(state["mstatus"]), "mstatus")
        lines += [
            f"    li t0, 0x{mstatus:x}",
            f"    .4byte 0x{encode_csrw(0x300, T0):08x} # csrw mstatus, t0 (isla state)",
        ]
    # 无论 state 如何，VS/FS 必须置 Dirty，否则 CVA6 把向量指令判 illegal
    lines += [
        "    li t0, 0x6600",
        f"    .4byte 0x{encode_csrs(0x300, T0):08x} # csrs mstatus, t0 (VS|FS Dirty)",
    ]
    return lines


def make_assembly(entry: dict, vlen_bits: int = DEFAULT_VLEN_BITS, backend: str = "emu", mode: str = "outcome", golden_words: list[int] | None = None) -> str:
    instruction = str(entry["test-ins"])
    encoding = parse_encoding(str(entry["test-ins-encdec"]))
    state = entry.get("isa-state", {})
    if not isinstance(state, dict):
        raise ValueError("isa-state 必须是对象")
    unknown = set(state) - KNOWN_STATE_KEYS
    if unknown:
        raise ValueError(f"isa-state 含生成器不支持的键: {sorted(unknown)}")

    expectation = EXPECTED_CLASS[entry["_ret_val"]]
    if expectation == "success":
        code_retired = EXIT_PASS_SUCCESS
        code_trap_illegal = EXIT_TRAP_ILLEGAL_UNEXP
        code_trap_other = EXIT_TRAP_OTHER_UNEXP
    elif expectation == "illegal":
        code_retired = EXIT_RET_UNEXP_ILLEGAL
        code_trap_illegal = EXIT_PASS_ILLEGAL
        code_trap_other = EXIT_TRAP_OTHER_EXP_ILLEGAL
    else:  # mem_exc
        code_retired = EXIT_RET_UNEXP_MEM_EXC
        code_trap_illegal = EXIT_PASS_MEM_EXC
        code_trap_other = EXIT_PASS_MEM_EXC

    before_loads, after_loads = vector_context_setup(state, vlen_bits)
    loads, words = vector_setup(state, vlen_bits)
    fpr_loads, fpr_words = fpr_setup(state)
    scalars = scalar_setup(state)
    if "x2" not in state:
        scalars = ["    la sp, _stack_top"] + scalars

    init = [
        # 先清零全部 GPR，消除两个仿真环境的启动差异
        # （spike reset 向量会写 a1/t0 等；Ara/CVA6 直接从 0x80000000 取指）
        *[f"    li x{n}, 0" for n in range(1, 32)],
        "    la t0, init_trap",
        "    csrw mtvec, t0",
        # mepc 指向测试指令后的标签：mret/sret 等控制流指令可返回正常退出路径，
        # 避免跳到复位值 0 触发取指异常（isla 的 MRET 用例无 mepc 初态）
        "    la t0, after_test",
        "    csrw mepc, t0",
        *mstatus_setup(state),
        *before_loads,
        *loads,
        *after_loads,
        *fpr_loads,
        "    la t0, test_trap",
        "    csrw mtvec, t0",
        *scalars,
    ]
    data_parts = []
    if words:
        data_parts.append(".align 3\nvector_initial_state:\n" + "\n".join(words))
    if fpr_words:
        data_parts.append(".align 3\nfpr_initial_state:\n" + "\n".join(fpr_words))
    data = ("\n\n".join(data_parts)) if data_parts else "    .dword 0"

    # 值级模式：测试指令后导出签名；dump 模式自旋等待宿主提取，check 模式内嵌 golden 比对。
    # 值级模式的退休路径退出码 = 签名匹配状态（0=一致，N=第 N 个 8 字节字不一致）。
    if mode == "dump":
        tail = [
            *dump_sequence(vlen_bits),
            "sig_done:",
            "1:  j 1b",
        ]
    elif mode == "check":
        if not golden_words:
            raise ValueError("check 模式需要 golden 签名字列表")
        tail = [
            *dump_sequence(vlen_bits),
            "sig_done:",
            "    # compare signature against golden",
            "    la t0, sig_region",
            "    la t1, golden_signature",
            f"    li t2, {len(golden_words)}",
            "    li a0, 0",
            "1:  ld t3, 0(t0)",
            "    ld t4, 0(t1)",
            "    bne t3, t4, 2f",
            "    addi t0, t0, 8",
            "    addi t1, t1, 8",
            "    addi t2, t2, -1",
            "    bnez t2, 1b",
            "    j _exit",
            "2:  la t5, sig_region",
            "    sub a0, t0, t5",
            "    srli a0, a0, 3",
            "    addi a0, a0, 1",
            "    j _exit",
        ]
        # sig_done 位于 dump 之后、compare 之前：golden 提取在此截停（同一 ELF）
    else:
        tail = [f"    li a0, {code_retired}", "    j _exit"]

    data_sig = [".align 3", f"sig_region:", f"    .space {signature_size(vlen_bits)}"]
    if mode == "check":
        data_sig.append(".align 3")
        data_sig.append("golden_signature:")
        data_sig.extend(f"    .dword 0x{word:016x}" for word in golden_words)

    return "\n".join([
        f"# Isla -> Ara PoC: {instruction} (mode={mode})",
        f"# encoding: 0x{encoding:08x}, ret_val: {entry['_ret_val']}, clause: {entry['_clause']}",
        ".option norvc",
        ".section .text.init",
        ".align 4",
        ".globl _start",
        "_start:",
        *init,
        f"    .4byte 0x{encoding:08x} # {instruction}",
        "after_test:",
        *tail,
        "",
        "    .align 2",
        "test_trap:",
        "    csrr a0, mcause",
        "    li t0, 2",
        "    beq a0, t0, 1f",
        f"    li a0, {code_trap_other}",
        "    j _exit",
        f"1:  li a0, {code_trap_illegal}",
        "    j _exit",
        "",
        "    .align 2",
        "init_trap:",
        f"    li a0, {EXIT_INIT_TRAP}",
        "    j _exit",
        "",
        "    .align 2",
        "_exit:",
        *EXIT_SEQUENCES[backend],
        "1:  j 1b",
        "",
        ".section .data",
        data,
        "",
        *data_sig,
        "",
        ".section .stack",
        ".align 4",
        ".space 4096",
        "_stack_top:",
        "",
        *TOSHOST_TAIL,
    ])


# 退出序列：两种 backend 等长（各 6 条指令），保证同一输入生成的 ELF
# 在两个 backend 下代码/数据布局逐字节同构（值级对拍的前提——x2/x31 等
# 寄存器持有地址值，布局不同会引入伪差异）。
# emu：写 CTRL 外设 0xD0000000，进程退出码 = 写入值。
# spike：HTIF tohost 约定（riscv-tests env/p 同款）——奇数值触发退出，
# 退出码 = value>>1，故写 (code<<1)|1；code=0 时写 1 → 退出码 0。
EXIT_SEQUENCES = {
    "emu": [
        "    li t0, 0xD0000000",
        "    sd a0, 0(t0)",
        "    nop",
        "    nop",
        "    nop",
        "    nop",
    ],
    "spike": [
        "    la t0, tohost",
        "    slli a1, a0, 1",
        "    ori a1, a1, 1",
        "    sd a1, 0(t0)",
        "    nop",
        "    nop",
    ],
}

# tohost 段两种 backend 都生成（emu 侧不执行），保证布局一致
TOSHOST_SECTION = {
    "emu": [],
    "spike": [],
}
TOSHOST_TAIL = [
    ".section .tohost",
    ".align 3",
    ".globl tohost",
    "tohost: .dword 0",
    ".globl fromhost",
    "fromhost: .dword 0",
    "",
]

LINKER = """OUTPUT_ARCH("riscv")
ENTRY(_start)
SECTIONS {
  . = 0x80000000;
  .text.init : { KEEP(*(.text.init)) }
  . = ALIGN(16); .text : { *(.text .text.*) }
  . = ALIGN(16); .data : { *(.data .data.* .sdata .sdata.*) }
  .bss (NOLOAD) : { *(.bss .bss.* COMMON) }
  .stack (NOLOAD) : { *(.stack) }
  /DISCARD/ : { *(.comment) *(.note*) *(.riscv.attributes) }
}
"""


# 值级对拍要求两种 backend 的 ELF 布局完全一致：统一链接脚本，
# .tohost 位于镜像末尾（spike HTIF 只要求 8 字节对齐；emu 侧仅占位）。
LINKER = """OUTPUT_ARCH("riscv")
ENTRY(_start)
SECTIONS {
  . = 0x80000000;
  .text.init : { KEEP(*(.text.init)) }
  . = ALIGN(16); .text : { *(.text .text.*) }
  . = ALIGN(16); .data : { *(.data .data.* .sdata .sdata.*) }
  .bss (NOLOAD) : { *(.bss .bss.* COMMON) }
  .stack (NOLOAD) : { *(.stack) }
  . = ALIGN(16); .tohost : { *(.tohost) }
  /DISCARD/ : { *(.comment) *(.note*) *(.riscv.attributes) }
}
"""

LINKERS = {"emu": LINKER, "spike": LINKER}


def _build_one(args_ns: argparse.Namespace, compiler: str, linker: Path, output: Path, index: int, entry: dict, golden_words: list[int] | None = None) -> dict:
    case_dir = output / f"case-{index:05d}"
    case_dir.mkdir(exist_ok=True)
    assembly = case_dir / "program.S"
    elf = case_dir / "program.elf"
    assembly.write_text(make_assembly(entry, args_ns.vlen_bits, args_ns.backend, args_ns.mode, golden_words), encoding="utf-8")
    command = [
        compiler, "-nostdlib", "-nostartfiles", "-static", "-fno-pic",
        "-march=rv64gc", "-mabi=lp64d",
        "-Wl,-T," + str(linker), "-Wl,-e,_start",
        "-o", str(elf), str(assembly),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"编译失败 case-{index:05d} ({entry.get('test-ins')}):\n{result.stderr}")
    digest = hashlib.sha256(elf.read_bytes()).hexdigest()
    case = {
        "id": case_dir.name,
        "backend": args_ns.backend,
        "mode": args_ns.mode,
        "vlen_bits": args_ns.vlen_bits,
        "clause": entry.get("_clause"),
        "instruction": entry["test-ins"],
        "encoding": entry["test-ins-encdec"],
        "ret_val": entry.get("_ret_val"),
        "isa-state": entry.get("isa-state", {}),
        "elf": str(elf),
        "sha256": digest,
    }
    (case_dir / "case.json").write_text(json.dumps(case, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return case


def build(args: argparse.Namespace) -> None:
    source = read_json(Path(args.input).resolve())
    metadata = source.get("metadata", {})
    source_vlen = metadata.get("ara_vlen_bits")
    if source_vlen is not None and source_vlen != args.vlen_bits:
        raise ValueError(f"样本声明 VLEN={source_vlen}，但构建参数是 {args.vlen_bits}")
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    linker = output / ("ara.ld" if args.backend == "emu" else "ara-spike.ld")
    linker.write_text(LINKERS[args.backend], encoding="utf-8")
    compiler = args.compiler
    golden_dir = Path(args.golden_dir).resolve() if args.golden_dir else None
    def build_pair(pair):
        index, entry = pair
        golden_words = None
        if args.mode == "check":
            # 兼容两种布局：flat 目录 case-NNNNN.bin，或 golden 子命令产出的 case-NNNNN/golden.bin
            golden_file = golden_dir / f"case-{index:05d}.bin"
            if not golden_file.is_file():
                golden_file = golden_dir / f"case-{index:05d}" / "golden.bin"
            if not golden_file.is_file():
                raise FileNotFoundError(f"check 模式缺少 golden 文件: {golden_file}")
            raw = golden_file.read_bytes()
            golden_words = [int.from_bytes(raw[i:i+8], "little") for i in range(0, len(raw), 8)]
        return _build_one(args, compiler, linker, output, index, entry, golden_words)
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        manifest = list(pool.map(build_pair, enumerate(source["gen"])))
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已生成 {len(manifest)} 个 ELF：{output}")


# ---------------------------------------------------------------- 运行与汇总


def classify(returncode: int, timed_out: bool, stdout: str, backend: str) -> str:
    if timed_out:
        return "timeout"
    if returncode < 0:
        return f"killed_by_signal_{-returncode}"
    if backend == "spike":
        # spike 的 HTIF 退出码 = (tohost 值)>>1 = 我们的分类码
        return EXIT_CLASS.get(returncode, f"unexpected_exit_{returncode}")
    if "Assertion failed" in stdout or "%Error" in stdout:
        # RTL 断言/仿真器错误导致 $stop，进程以非零码退出且无 Core Test 标记
        return "emu_assert_crash"
    if "Core Test" not in stdout:
        # 仿真结束但没写退出寄存器（例如 -c 周期上限被打满）
        return f"no_exit_marker_{returncode}"
    return EXIT_CLASS.get(returncode, f"unexpected_exit_{returncode}")


# ---------------------------------------------------------------- spike vs emu 对拍


# 原始执行结果（与 isla 期望无关）
RAW_RETIRED = {"pass_success", "mismatch_retired_expected_illegal", "mismatch_retired_expected_memexc"}
RAW_ILLEGAL = {"pass_illegal_confirmed", "fail_trap_illegal_expected_success"}
RAW_OTHER_TRAP = {"fail_trap_other_expected_success", "mismatch_trap_other_expected_illegal", "pass_memexc_confirmed"}
RAW_INFRA = {"timeout", "init_phase_trap", "emu_assert_crash"}

# RVV 1.0 spec 强制 vstart!=0 -> illegal 的指令基名（v-spec L3907/4196/4218/4259/4295/4332/4383/4797）
VSTART_MUST_ILLEGAL_BASES = {
    "vredsum", "vredsumu", "vredmax", "vredmaxu", "vredmin", "vredminu", "vredand", "vredor",
    "vredxor", "vwredsum", "vwredsumu", "vfredsum", "vfredosum", "vfredusum", "vfredmax", "vfredmin",
    "vfwredsum", "vfwredusum", "vcpop", "vfirst", "vmsbf", "vmsif", "vmsof", "viota", "vcompress",
}


def _raw_outcome(cls: str) -> str:
    if cls in RAW_RETIRED:
        return "retired"
    if cls in RAW_ILLEGAL:
        return "illegal"
    if cls in RAW_OTHER_TRAP:
        return "other_trap"
    if cls == "emu_assert_crash":
        return "assert_crash"
    return "infra"


def _parse_state_int(value) -> int:
    match = BITS_RE.fullmatch(str(value).strip())
    if match is None:
        return 0
    value_int, _ = _parse_literal(match, "state")
    return value_int


def diff_divergence_tag(emu_result: dict, spike_result: dict) -> str:
    """spike 与 emu 原始结果不一致时的细化归因。"""
    emu_raw = _raw_outcome(emu_result["class"])
    spike_raw = _raw_outcome(spike_result["class"])
    state = emu_result.get("isa-state", {})
    vtype = _parse_state_int(state.get("vtype", "64'd0"))
    vstart = _parse_state_int(state.get("vstart", "64'd0"))
    mnemonic = str(emu_result.get("instruction", "")).split()[0]
    base = mnemonic.split(".")[0]

    if spike_raw == "illegal" and emu_raw == "retired":
        if vtype >> 63 or vtype & ~0xFF:
            return "BUG_vill_reserved_bit_ara_retires"  # golden 实锤（上游 PR #486 同根）
        if vstart != 0 and base in VSTART_MUST_ILLEGAL_BASES:
            return "BUG_vstart_mandatory_list_ara_retires"
        if vstart != 0:
            # spike 行使 spec 实现许可（decode_macros.h:169-173），Ara 支持重启执行，双方合法
            return "allowance_vstart_arith_spike_stricter"
        return "spike_illegal_ara_retired_other"
    if spike_raw == "retired" and emu_raw == "illegal":
        return "CANDIDATE_ara_over_trap"  # 如 vmadc/vmsbc overlap 过度限制
    if emu_raw == "assert_crash":
        return "BUG_ara_assert_crash"  # 如 vnclip SEW=64（该子集 spike 判 illegal）
    if spike_raw == "infra" or emu_raw == "infra":
        return f"infra_mismatch({emu_result['class']}|{spike_result['class']})"
    return f"outcome_mismatch({emu_raw}|{spike_raw})"


def diff(args: argparse.Namespace) -> None:
    emu_results = json.loads(Path(args.emu_results).read_text(encoding="utf-8"))
    spike_results = json.loads(Path(args.spike_results).read_text(encoding="utf-8"))
    if len(emu_results) != len(spike_results):
        raise ValueError(f"两侧结果数量不一致：emu={len(emu_results)} spike={len(spike_results)}")
    rows: list[dict] = []
    overall: Counter = Counter()
    by_clause: dict[str, Counter] = defaultdict(Counter)
    for emu_result, spike_result in zip(emu_results, spike_results):
        if emu_result.get("id") != spike_result.get("id"):
            raise ValueError(f"用例对齐失败：{emu_result.get('id')} vs {spike_result.get('id')}")
        emu_raw = _raw_outcome(emu_result["class"])
        spike_raw = _raw_outcome(spike_result["class"])
        if emu_raw == spike_raw:
            tag = f"agree_{emu_raw}"
        else:
            tag = diff_divergence_tag(emu_result, spike_result)
        row = {
            "id": emu_result["id"],
            "clause": emu_result.get("clause"),
            "instruction": emu_result.get("instruction"),
            "isla_ret_val": emu_result.get("ret_val"),
            "emu_class": emu_result["class"],
            "spike_class": spike_result["class"],
            "tag": tag,
        }
        rows.append(row)
        overall[tag] += 1
        by_clause[emu_result.get("clause", "?")][tag] += 1
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "total": len(rows),
        "overall": dict(overall),
        "by_clause": {clause: dict(counter) for clause, counter in sorted(by_clause.items())},
        "rows": rows,
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"总计 {len(rows)} 条")
    for tag, count in overall.most_common():
        print(f"  {tag}: {count}")
    print(f"已写入 {output}")


def run_case(case: dict, emulator: Path, cycles: int, timeout: int, backend: str, spike_isa: str) -> dict:
    if backend == "spike":
        command = [str(emulator), f"--isa={spike_isa}", case["elf"]]
    else:
        # 参数顺序见模块 docstring：-c 必须在 -l 之前
        command = [str(emulator), "-c", str(cycles), "-l", f"ram,{case['elf']},elf"]
    log = Path(case["elf"]).parent / "emu.log"
    try:
        completed = subprocess.run(
            command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        stdout = completed.stdout or ""
        returncode = completed.returncode
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or b"").decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        returncode = -1
        timed_out = True
    log.write_text(stdout, encoding="utf-8")
    result = dict(case)
    result["class"] = classify(returncode, timed_out, stdout, case.get("backend", backend))
    result["returncode"] = returncode
    result["timed_out"] = timed_out
    return result


def run(args: argparse.Namespace) -> None:
    manifest_path = Path(args.manifest).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases = manifest if args.limit is None else manifest[: args.limit]
    backend = args.backend or (cases[0].get("backend") if cases else "emu")
    if args.emulator:
        emulator = Path(args.emulator).resolve()
    else:
        emulator = (EMU_DEFAULT if backend == "emu" else SPIKE_DEFAULT).resolve()
    if not emulator.is_file():
        raise FileNotFoundError(f"找不到仿真器: {emulator}")
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(
            lambda case: run_case(case, emulator, args.cycles, args.timeout, backend, args.spike_isa), cases,
        ))
    results_path = manifest_path.parent / "results.json"
    results_path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = summarize(results)
    (manifest_path.parent / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已写入 {results_path}")
    for line in render_summary(summary):
        print(line)


def summarize(results: list[dict]) -> dict:
    by_clause: dict[str, Counter] = defaultdict(Counter)
    overall: Counter = Counter()
    for result in results:
        by_clause[result.get("clause", "?")][result["class"]] += 1
        overall[result["class"]] += 1
    return {
        "total": len(results),
        "overall": dict(overall),
        "by_clause": {clause: dict(counter) for clause, counter in sorted(by_clause.items())},
    }


def render_summary(summary: dict) -> list[str]:
    lines = [f"总计 {summary['total']} 条：{summary['overall']}"]
    for clause, counter in summary["by_clause"].items():
        lines.append(f"  {clause}: {counter}")
    return lines


# ---------------------------------------------------------------- 入口


# ---------------------------------------------------------------- golden 提取（spike 交互 mem dump）


def _elf_symbols(elf: Path) -> dict[str, int]:
    result = subprocess.run(
        ["riscv64-unknown-elf-nm", str(elf)], capture_output=True, text=True, check=True,
    )
    symbols = {}
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) == 3:
            symbols[parts[2]] = int(parts[0], 16)
    return symbols


MEM_VALUE_RE = re.compile(r"^0x[0-9a-f]{16}$")


def extract_golden_case(case: dict, spike: Path, spike_isa: str, vlen_bits: int, timeout: int) -> dict:
    """对 dump 模式 ELF：MOD spike -d 交互运行到 sig_done 后逐字 mem 导出签名区。

    交互协议（0003 补丁版，Ara vtrace 同款）：命令从 stdin 读、结果走 stdout、
    提示符走 stderr。`until pc 0 <addr>` 跑到 sig_done；`mem <addr>` 每次读一个
    8 字节字并打印 `0x%016x`；输出行与命令顺序一一对应。
    """
    elf = Path(case["elf"])
    symbols = _elf_symbols(elf)
    if "sig_region" not in symbols or "sig_done" not in symbols:
        raise ValueError(f"{elf} 缺少 sig 符号")
    lo = symbols["sig_region"]
    size = signature_size(vlen_bits)
    word_count = size // 8
    addresses = [lo + 8 * i for i in range(word_count)]
    commands = [f"until pc 0 {symbols['sig_done']:x}"]
    commands += [f"mem 0x{addr:x}" for addr in addresses]
    commands.append("quit")
    try:
        completed = subprocess.run(
            [str(spike), "-d", f"--isa={spike_isa}", str(elf)],
            input="\n".join(commands) + "\n", text=True, capture_output=True, timeout=timeout,
        )
        # mem 结果经 sout_ 打到 stderr，与 "(spike)" 提示符同流；按行尾 16 位 hex 提取
        combined = ((completed.stderr or "") + "\n" + (completed.stdout or ""))
    except subprocess.TimeoutExpired as exc:
        err_text = (exc.stderr or b"").decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        out_text = (exc.stdout or b"").decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        combined = err_text + "\n" + out_text
    values = [int(m.group(1), 16) for line in combined.splitlines()
              if (m := re.search(r"(0x[0-9a-f]{16})\s*$", line.strip())) is not None]
    complete = len(values) == word_count
    result = dict(case)
    result["golden_complete"] = complete
    result["golden_words_found"] = len(values)
    if complete:
        blob = bytearray()
        for value in values:
            blob += value.to_bytes(8, "little")
        out = elf.parent / "golden.bin"
        out.write_bytes(bytes(blob))
        result["golden"] = str(out)
    return result


def golden(args: argparse.Namespace) -> None:
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    spike = Path(args.spike).resolve()
    if not spike.is_file():
        raise FileNotFoundError(f"找不到 spike: {spike}")
    def extract(case):
        try:
            return extract_golden_case(case, spike, args.spike_isa, args.vlen_bits, args.timeout)
        except Exception as exc:  # noqa: BLE001 - 单用例失败不能拖垮批量
            failed = dict(case)
            failed["golden_complete"] = False
            failed["golden_error"] = str(exc)
            return failed
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(extract, manifest))
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = sum(1 for r in results if r.get("golden_complete"))
    print(f"golden 完整 {ok}/{len(results)}，已写入 {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_prepare = sub.add_parser("prepare", help="从 isla 输出抽样")
    p_prepare.add_argument("--source", nargs="*", default=None, help="输入 JSON（默认 isla/output/rv64_z*.json）")
    p_prepare.add_argument("--per-clause", type=int, default=10, help="每个 (clause, ret_val) 桶抽样条数")
    p_prepare.add_argument("--clause-filter", default=None, help="clause 正则过滤")
    p_prepare.add_argument("--output", default=str(DEFAULT_OUT / "input.json"))
    p_prepare.add_argument("--vlen-bits", type=int, default=DEFAULT_VLEN_BITS)
    p_prepare.set_defaults(func=prepare)

    p_build = sub.add_parser("build", help="生成并编译 ELF")
    p_build.add_argument("--input", default=str(DEFAULT_OUT / "input.json"))
    p_build.add_argument("--output", default=str(DEFAULT_OUT / "elf"))
    p_build.add_argument("--compiler", default="riscv64-unknown-elf-gcc")
    p_build.add_argument("--jobs", type=int, default=16)
    p_build.add_argument("--backend", choices=["emu", "spike"], default="emu")
    p_build.add_argument("--vlen-bits", type=int, default=DEFAULT_VLEN_BITS)
    p_build.add_argument("--mode", choices=["outcome", "dump", "check"], default="outcome")
    p_build.add_argument("--golden-dir", default=None, help="check 模式的 golden 目录（case-NNNNN.bin）")
    p_build.set_defaults(func=build)

    p_run = sub.add_parser("run", help="批量运行 emu")
    p_run.add_argument("--manifest", default=str(DEFAULT_OUT / "elf" / "manifest.json"))
    p_run.add_argument("--emulator", default=None, help="emu/spike 可执行文件；默认按 backend 选择")
    p_run.add_argument("--backend", choices=["emu", "spike"], default=None, help="不指定时取 manifest 中的 backend")
    p_run.add_argument("--spike-isa", default="rv64gcv_zfh_zvfh_zvl128b", help="Ara runtime.mk RISCV_SIM_OPT 同款（vlen=128）")
    p_run.add_argument("--jobs", type=int, default=8)
    p_run.add_argument("--cycles", type=int, default=2_000_000, help="-c 仿真周期上限")
    p_run.add_argument("--timeout", type=int, default=120, help="单用例墙钟超时（秒）")
    p_run.add_argument("--limit", type=int, default=None)
    p_run.set_defaults(func=run)

    p_diff = sub.add_parser("diff", help="spike vs emu 对拍矩阵")
    p_diff.add_argument("--emu-results", default=str(DEFAULT_OUT / "elf-emu" / "results.json"))
    p_diff.add_argument("--spike-results", default=str(DEFAULT_OUT / "elf-spike" / "results.json"))
    p_diff.add_argument("--output", default=str(DEFAULT_OUT / "matrix.json"))
    p_diff.set_defaults(func=diff)

    p_golden = sub.add_parser("golden", help="从 dump 模式 ELF 提取 spike golden 签名")
    p_golden.add_argument("--manifest", default=str(DEFAULT_OUT / "elf-dump" / "manifest.json"))
    p_golden.add_argument("--spike", default=str(SPIKE_MOD_DEFAULT))
    p_golden.add_argument("--spike-isa", default="rv64gcv_zfh_zvfh_zvl128b")
    p_golden.add_argument("--vlen-bits", type=int, default=DEFAULT_VLEN_BITS)
    p_golden.add_argument("--jobs", type=int, default=16)
    p_golden.add_argument("--timeout", type=int, default=60)
    p_golden.add_argument("--output", default=str(DEFAULT_OUT / "golden.json"))
    p_golden.set_defaults(func=golden)

    args = parser.parse_args()
    try:
        args.func(args)
    except (ValueError, RuntimeError, FileNotFoundError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
