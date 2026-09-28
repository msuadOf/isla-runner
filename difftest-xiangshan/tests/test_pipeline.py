#!/usr/bin/env python3
"""pipeline.py 的 V 上下文与内存上下文重放测试。"""

import hashlib
import importlib.util
import json
import struct
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("pipeline", ROOT / "pipeline.py")
pipeline = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(pipeline)


class FakePopen:
    """subprocess.Popen 替身：action 为 (stdout, returncode) 或待抛异常。"""

    def __init__(self, action):
        self.action = action
        self.pid = 4194304
        self.returncode = None

    def communicate(self, timeout=None):
        if isinstance(self.action, BaseException):
            raise self.action
        stdout, self.returncode = self.action
        return stdout, None

    def kill(self):
        self.returncode = -9


class FakePopenFactory:
    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def __call__(self, command, **kwargs):
        self.calls.append((command, kwargs))
        return FakePopen(self.script.pop(0))


def synthetic_elf_bytes(ranges):
    """构造只含 ALLOC section 头的最小 ELF64 小端镜像，供 elf_alloc_ranges 解析。"""
    header = bytearray(64)
    header[0:4] = b"\x7fELF"
    header[4] = 2  # ELFCLASS64
    header[5] = 1  # ELFDATA2LSB
    e_shoff = 0x80
    struct.pack_into("<Q", header, 0x28, e_shoff)
    struct.pack_into("<H", header, 0x3A, 64)
    struct.pack_into("<H", header, 0x3C, len(ranges) + 1)
    data = bytearray(header) + bytearray(e_shoff - 64)
    for address, size in [(0, 0), *ranges]:
        # sh_name, sh_type, sh_flags, sh_addr, sh_offset, sh_size + 24B 保留字段补齐到 e_shentsize
        data += struct.pack("<IIQQQQ", 0, 1, 0x2, address, 0x40, size) + bytes(24)
    return bytes(data)


def make_memory_entry(
    address="64'h0000_0000_8000_1000",
    size=8,
    pre_value=None,
    post_value="64'h0000_0000_0000_0000",
    ret_val="Retire_Success(())",
):
    entry = {
        "test-ins": "sd x0, 0x0(x30)",
        "test-ins-encdec": "32'h000f_3023",
        "isa-state": {
            "cur_privilege": "User",
            "x30": "64'h0000_0000_8000_1000",
        },
        "ret_val": ret_val,
        "pre-memory": [{"address": address, "bytes": size, "value": pre_value}],
        "post-memory": [{"address": address, "bytes": size, "value": post_value}],
        "memory-events": [
            {
                "kind": "write",
                "address": address,
                "bytes": size,
                "data": post_value,
            }
        ],
    }
    return entry


class ExpectTrapTests(unittest.TestCase):
    def test_detects_illegal_and_memory_exception(self):
        self.assertTrue(pipeline.expects_trap({"ret_val": "Illegal_Instruction(())"}))
        self.assertTrue(
            pipeline.expects_trap(
                {"ret_val": "Memory_Exception({tuple#%bv64_%union ExceptionType1: E_SAMO_Access_Fault(())})"}
            )
        )
        self.assertFalse(pipeline.expects_trap({"ret_val": "Retire_Success(())"}))
        self.assertFalse(pipeline.expects_trap({}))


class SourceEntryFilterTests(unittest.TestCase):
    def test_ret_val_regex_filters_and_stamps_source_file(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / "rv64_zX.json"
            source.write_text(
                json.dumps(
                    {
                        "gen": [
                            {
                                "test-ins": "ok",
                                "test-ins-encdec": "32'h1",
                                "arch": {"xlen": "64"},
                                "ret_val": "Retire_Success(())",
                            },
                            {
                                "test-ins": "bad",
                                "test-ins-encdec": "32'h2",
                                "arch": {"xlen": "64"},
                                "ret_val": "Illegal_Instruction(())",
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            entries = pipeline.source_entries([source], 0, False, r"^Illegal_Instruction")
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["test-ins"], "bad")
            self.assertEqual(entries[0]["source_file"], "rv64_zX.json")
            all_entries = pipeline.source_entries([source], 0, False, None)
            self.assertEqual(len(all_entries), 2)


class TrapAwareAssemblyTests(unittest.TestCase):
    def make_trap_entry(self):
        return {
            "test-ins": "vmerge.vim v0, v30, 0x9, v0",
            "test-ins-encdec": "32'h5de4_b057",
            "isa-state": {
                "cur_privilege": "User",
                "vcsr": "3'h0",
                "vl": "64'h0000_0000_0000_0000",
                "vstart": "64'h0000_0000_0000_0000",
                "vtype": "64'h0000_0000_0000_0019",
            },
            "ret_val": "Illegal_Instruction(())",
        }

    def test_trap_entry_installs_handler_and_sentinel(self):
        assembly = pipeline.make_assembly(self.make_trap_entry(), 128)

        self.assertIn("csrw medeleg, x0", assembly)
        self.assertIn("la t0, trap_handler", assembly)
        self.assertIn("csrw mtvec, t0", assembly)
        self.assertLess(assembly.index("csrw mtvec, t0"), assembly.index("vsetvli"))
        self.assertIn("trap_handler:", assembly)
        self.assertIn("csrr t0, mepc", assembly)
        self.assertIn("la t1, payload_ins", assembly)
        self.assertIn("bne t0, t1, 2f", assembly)
        # payload_ins 紧贴 payload 指令，位于其前
        self.assertLess(assembly.index("payload_ins:"), assembly.index(".4byte 0x5de4b057"))

        payload_instruction = assembly.index(".4byte 0x5de4b057")
        park = assembly.index("1:  j 1b")
        sentinel = assembly.index(".4byte 0x00000000")
        self.assertGreater(sentinel, payload_instruction)
        self.assertLess(sentinel, park)
        # 顺序流不经过 GOODTRAP：只有 payload 处 trap 的 handler 路径才 GOODTRAP
        self.assertNotIn(".4byte 0x0000006b", assembly[payload_instruction:park])

    def test_success_entry_keeps_goodtrap_without_sentinel(self):
        entry = {
            "test-ins": "vadd.vv v8, v4, v12",
            "test-ins-encdec": "32'h0246_0457",
            "isa-state": {
                "cur_privilege": "User",
                "vl": "64'h0000_0000_0000_0007",
                "vtype": "64'h0000_0000_0000_00da",
            },
        }

        assembly = pipeline.make_assembly(entry, 256)

        self.assertNotIn(".4byte 0x00000000", assembly)
        payload_instruction = assembly.index(".4byte 0x02460457")
        park = assembly.index("1:  j 1b")
        self.assertLess(assembly.index(".4byte 0x0000006b"), park)
        self.assertGreater(assembly.index(".4byte 0x0000006b"), payload_instruction)
        self.assertIn("trap_handler:", assembly)
        self.assertIn("2:  j 2b", assembly)
        self.assertNotIn("csrr t0, mepc", assembly)


class VectorContextAssemblyTests(unittest.TestCase):
    def test_replays_vtype_vl_vstart_and_vcsr_before_payload(self):
        entry = {
            "test-ins": "vadd.vv v8, v4, v12",
            "test-ins-encdec": "32'h0246_0457",
            "isa-state": {
                "cur_privilege": "User",
                "vl": "64'h0000_0000_0000_0007",
                "vstart": "64'h0000_0000_0000_0002",
                "vtype": "64'h0000_0000_0000_00da",
                "vcsr": "3'h5",
            },
        }

        assembly = pipeline.make_assembly(entry, 256)

        self.assertIn("li t1, 7", assembly)
        self.assertIn("vsetvli zero, t1, 0xda", assembly)
        self.assertIn("li t0, 2", assembly)
        self.assertIn("csrw vstart, t0", assembly)
        self.assertIn("li t0, 2", assembly)
        self.assertIn("csrw vxrm, t0", assembly)
        self.assertIn("li t0, 1", assembly)
        self.assertIn("csrw vxsat, t0", assembly)
        self.assertIn("csrw pmpaddr0, t0", assembly)
        self.assertIn("csrw pmpcfg0, t0", assembly)
        self.assertIn("mret", assembly)
        self.assertLess(assembly.index("vsetvli zero, t1, 0xda"), assembly.index(".4byte 0x02460457"))

    def test_replays_vill_with_a_reserved_vsetvli_immediate(self):
        entry = {
            "test-ins": "vadd.vv v8, v4, v12",
            "test-ins-encdec": "32'h0246_0457",
            "isa-state": {
                "vl": "64'h0000_0000_0000_0000",
                "vtype": "64'h8000_0000_0000_0000",
            },
        }

        assembly = pipeline.make_assembly(entry, 128)

        self.assertIn("vsetvli zero, t1, 0x400 (建立 VILL)", assembly)

    def test_replays_scalar_registers_after_privilege_setup(self):
        entry = {
            "test-ins": "vsetvl x0, x26, x1",
            "test-ins-encdec": "32'h801d_7057",
            "isa-state": {
                "cur_privilege": "User",
                "vl": "64'h0000_0000_0000_0001",
                "vtype": "64'h0000_0000_0000_0000",
                "x1": "64'h0000_0000_0000_0007",
                "x26": "64'h8000_0000_0000_000c",
            },
        }

        assembly = pipeline.make_assembly(entry, 128)

        payload = assembly.index("payload:")
        payload_instruction = assembly.index(".4byte 0x801d7057")
        self.assertGreater(assembly.index("li x1, 0x7"), payload)
        self.assertGreater(assembly.index("li x26, 0x800000000000000c"), payload)
        self.assertLess(assembly.index("li x1, 0x7"), payload_instruction)
        self.assertLess(assembly.index("li x26, 0x800000000000000c"), payload_instruction)

    def test_rejects_vl_that_vsetvl_would_clamp(self):
        entry = {
            "test-ins": "vadd.vv v8, v4, v12",
            "test-ins-encdec": "32'h0246_0457",
            "isa-state": {
                "vl": "64'h0000_0000_0000_0011",
                "vtype": "64'h0000_0000_0000_0000",
            },
        }

        with self.assertRaisesRegex(ValueError, "VLMAX"):
            pipeline.make_assembly(entry, 128)

    def test_difftest_case_worker_marks_goodtrap(self):
        with TemporaryDirectory() as directory:
            elf = Path(directory) / "program.elf"
            elf.touch()
            case = {"id": "case-000", "elf": str(elf)}
            factory = FakePopenFactory([("HIT GOOD TRAP", 0)])
            with patch.object(pipeline.subprocess, "Popen", side_effect=factory):
                result = pipeline.run_case(case, Path("emu"), Path("ref.so"), 1)

            self.assertEqual(result["category"], "success")
            self.assertEqual(
                (elf.parent / "difftest.log").read_text(encoding="utf-8"),
                "HIT GOOD TRAP\n",
            )
            command, kwargs = factory.calls[0]
            self.assertEqual(
                command, ["emu", "-i", str(elf), "--diff", "ref.so"]
            )
            self.assertNotIn("--force-dump-result", command)
            self.assertIs(kwargs["stderr"], pipeline.subprocess.STDOUT)

    def test_difftest_case_worker_rejects_zero_exit_without_goodtrap(self):
        with TemporaryDirectory() as directory:
            elf = Path(directory) / "program.elf"
            elf.touch()
            case = {"id": "case-000", "elf": str(elf)}
            factory = FakePopenFactory([("", 0)])
            with patch.object(pipeline.subprocess, "Popen", side_effect=factory):
                result = pipeline.run_case(case, Path("emu"), Path("ref.so"), 1)

            self.assertEqual(result["category"], "failure")
            self.assertEqual(len(factory.calls), 1)
            self.assertNotIn("--force-dump-result", factory.calls[0][0])

    def test_difftest_case_worker_records_first_run_output_for_failure(self):
        with TemporaryDirectory() as directory:
            elf = Path(directory) / "program.elf"
            elf.touch()
            case = {"id": "case-000", "elf": str(elf)}
            factory = FakePopenFactory([("abort with different-at", 1)])
            with patch.object(pipeline.subprocess, "Popen", side_effect=factory):
                result = pipeline.run_case(case, Path("emu"), Path("ref.so"), 1)

            self.assertEqual(result["category"], "failure")
            # ABORT 的第一跑 stdout 已含差异信息，不再重跑 trace
            self.assertEqual(len(factory.calls), 1)
            self.assertEqual(
                (elf.parent / "difftest.log").read_text(encoding="utf-8"),
                "abort with different-at",
            )

    def test_difftest_case_worker_records_execution_timeout_as_failure(self):
        with TemporaryDirectory() as directory:
            elf = Path(directory) / "program.elf"
            elf.touch()
            case = {"id": "case-000", "elf": str(elf)}
            timed_out = pipeline.subprocess.TimeoutExpired(["emu"], 1, output="partial run")
            trace_timed_out = pipeline.subprocess.TimeoutExpired(
                ["emu", "--dump-commit-trace"], 1, output="partial trace"
            )
            factory = FakePopenFactory([timed_out, trace_timed_out])
            with patch.object(pipeline.subprocess, "Popen", side_effect=factory):
                with patch.object(
                    pipeline.os,
                    "killpg",
                    side_effect=ProcessLookupError(),
                ):
                    result = pipeline.run_case(case, Path("emu"), Path("ref.so"), 1)

            self.assertEqual(result["category"], "failure")
            log = (elf.parent / "difftest.log").read_text(encoding="utf-8")
            self.assertIn("execution timeout", log)
            self.assertIn("partial trace", log)
            self.assertIn("--dump-commit-trace", factory.calls[1][0])
            self.assertIn("elapsed", result)


class RunIncrementalRecordingTests(unittest.TestCase):
    def make_cases_dir(self, directory: str) -> Path:
        cases_dir = Path(directory)
        elf = cases_dir / "case-000" / "program.elf"
        elf.parent.mkdir(parents=True, exist_ok=True)
        elf.touch()
        manifest = [
            {
                "id": "case-000",
                "instruction": "vmerge.vim v0, v30, 0x9, v0",
                "encoding": "32'h5de4_b057",
                "elf": str(elf),
                "ret_val": "Illegal_Instruction(())",
                "expect_trap": True,
            }
        ]
        (cases_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (cases_dir / "emu").touch()
        (cases_dir / "ref.so").touch()
        return cases_dir

    def test_run_appends_each_result_and_resumes(self):
        with TemporaryDirectory() as directory:
            cases_dir = self.make_cases_dir(directory)
            args = SimpleNamespace(
                cases=str(cases_dir),
                emulator=str(cases_dir / "emu"),
                diff_so=str(cases_dir / "ref.so"),
                jobs=1,
                timeout=5,
            )
            fake = {
                **json.loads((cases_dir / "manifest.json").read_text(encoding="utf-8"))[0],
                "category": "success",
                "returncode": 0,
                "log": "x",
                "elapsed": 0.1,
            }
            with patch.object(pipeline, "run_case", return_value=fake) as run_case_mock:
                pipeline.run(args)

            run_case_mock.assert_called_once()
            ndjson = cases_dir / "results.ndjson"
            lines = ndjson.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0])["id"], "case-000")
            results = json.loads((cases_dir / "results.json").read_text(encoding="utf-8"))
            self.assertEqual(len(results), 1)

            # 再次运行：全部条目已完成，不再执行任何用例，记录不重复
            with patch.object(pipeline, "run_case") as run_case_mock:
                pipeline.run(args)

            run_case_mock.assert_not_called()
            self.assertEqual(
                len(ndjson.read_text(encoding="utf-8").strip().splitlines()), 1
            )

    def test_run_skips_incomplete_ndjson_line(self):
        with TemporaryDirectory() as directory:
            cases_dir = self.make_cases_dir(directory)
            ndjson = cases_dir / "results.ndjson"
            ndjson.write_text('{"id": "case-00', encoding="utf-8")
            args = SimpleNamespace(
                cases=str(cases_dir),
                emulator=str(cases_dir / "emu"),
                diff_so=str(cases_dir / "ref.so"),
                jobs=1,
                timeout=5,
            )
            fake = {
                "id": "case-000",
                "category": "success",
                "returncode": 0,
                "log": "x",
                "elapsed": 0.1,
            }
            with patch.object(pipeline, "run_case", return_value=fake):
                pipeline.run(args)

            lines = ndjson.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 2)
            self.assertEqual(json.loads(lines[1])["id"], "case-000")


class MemoryPlanTests(unittest.TestCase):
    def test_parses_pre_post_and_fills_null_pre_with_0xa5(self):
        entry = make_memory_entry(
            address="64'h0000_0000_8000_1000", size=2, pre_value=None,
            post_value="16'h0102",
        )
        plan = pipeline.memory_plan(entry)

        self.assertEqual(len(plan["pre"]), 1)
        self.assertEqual(plan["pre"][0]["address"], 0x80001000)
        self.assertEqual(plan["pre"][0]["values"], [0xA5, 0xA5])
        self.assertEqual(plan["post"][0]["values"], [0x02, 0x01])  # 小端
        self.assertEqual(plan["counts"]["pre_fill_bytes"], 2)
        self.assertIsNone(plan["skip_entry"])

    def test_non_null_pre_value_is_emitted_little_endian(self):
        entry = make_memory_entry(size=2, pre_value="16'hba98")
        plan = pipeline.memory_plan(entry)

        self.assertEqual(plan["pre"][0]["values"], [0x98, 0xBA])
        self.assertEqual(plan["counts"]["pre_fill_bytes"], 0)

    def test_skips_null_address_segments_and_counts(self):
        entry = make_memory_entry()
        entry["pre-memory"].append({"address": None, "bytes": 8, "value": None})
        entry["post-memory"].append({"address": None, "bytes": 8, "value": "8'h1"})
        plan = pipeline.memory_plan(entry)

        self.assertEqual(plan["counts"]["pre_segments"], 2)
        self.assertEqual(plan["counts"]["pre_emitted"], 1)
        self.assertEqual(plan["counts"]["pre_null_address"], 1)
        self.assertEqual(plan["counts"]["post_null"], 1)
        self.assertEqual(len(plan["post"]), 1)

    def test_post_value_null_skips_segment_and_all_null_skips_entry(self):
        entry = make_memory_entry(
            post_value=None,
        )
        plan = pipeline.memory_plan(entry)
        self.assertEqual(plan["counts"]["post_null"], 1)
        self.assertEqual(plan["post"], [])
        self.assertEqual(plan["skip_entry"], "post-all-null")

    def test_rejects_malformed_segment_value(self):
        entry = make_memory_entry(pre_value="junk")
        with self.assertRaisesRegex(ValueError, "pre-memory"):
            pipeline.memory_plan(entry)


class MstatusPreambleTests(unittest.TestCase):
    def make_fd_entry(self, mstatus=None, privilege="User"):
        state = {"cur_privilege": privilege}
        if mstatus is not None:
            state["mstatus"] = mstatus
        return {
            "test-ins": "fld f8, 0xc0(x15)",
            "test-ins-encdec": "32'h00e7b307",
            "isa-state": state,
            "ret_val": "Retire_Success(())",
        }

    def test_replays_mstatus_model_value_verbatim(self):
        entry = self.make_fd_entry(mstatus="64'h0000_0008_0000_6000")

        assembly = pipeline.make_assembly(entry, 128)

        # 模型值整写（0x0000000800006000：SD=1、FS=Dirty、SXL=01 的 W21 样形）
        self.assertIn("li t0, 0x800006000", assembly)
        self.assertIn("csrw mstatus, t0", assembly)
        # 不再发射默认读改写（OR 0x600）块
        self.assertNotIn("li t1, 0x600", assembly)
        # 整写在特权降权 RMW 之前（mret 只改 MPP/MIE，保留模型值其余位）
        self.assertLess(
            assembly.index("csrw mstatus, t0"),
            assembly.index("csrr t0, mstatus"),
        )

    def test_default_preamble_without_model_value_keeps_rmw(self):
        entry = self.make_fd_entry(mstatus=None)

        assembly = pipeline.make_assembly(entry, 128)

        self.assertIn("csrr t0, mstatus", assembly)
        self.assertIn("li t1, 0x600", assembly)
        self.assertIn("or t0, t0, t1", assembly)
        self.assertIn("csrw mstatus, t0", assembly)

    def test_rejects_unparseable_mstatus_model_value(self):
        entry = self.make_fd_entry(mstatus="garbage")

        with self.assertRaisesRegex(ValueError, "mstatus"):
            pipeline.make_assembly(entry, 128)

    def test_rejects_mstatus_masked_bitvector(self):
        # 带掩码的位向量（x 形式）不是模型值格式，必须硬失败而非静默忽略
        entry = self.make_fd_entry(mstatus="64'hxxxx_0000_0000_6000")

        with self.assertRaisesRegex(ValueError, "mstatus"):
            pipeline.make_assembly(entry, 128)


class CompressedPayloadTests(unittest.TestCase):
    def test_compressed_encoding_emits_two_byte_payload(self):
        entry = {
            "test-ins": "c.fld f8, 0xc0(x15)",
            "test-ins-encdec": "16'h23e0",
            "isa-state": {
                "cur_privilege": "User",
                "mstatus": "64'h0000_0000_0000_6000",
            },
            "ret_val": "Retire_Success(())",
        }

        assembly = pipeline.make_assembly(entry, 128)

        self.assertIn(".2byte 0x23e0", assembly)
        self.assertNotIn(".4byte 0x000023e0", assembly)
        self.assertLess(assembly.index("payload_ins:"), assembly.index(".2byte 0x23e0"))
        # 哨兵与 GOODTRAP 仍是 32 位 .4byte
        self.assertIn(".4byte 0x0000006b", assembly)

    def test_parse_encoding_rejects_width_overflow(self):
        with self.assertRaisesRegex(ValueError, "16"):
            pipeline.parse_encoding("16'h12345")


class PreMemoryAssemblyTests(unittest.TestCase):
    def test_emits_byte_stores_between_privilege_setup_and_scalar_loads(self):
        entry = make_memory_entry(
            address="64'h0000_0000_8000_1000", size=8, pre_value=None
        )

        assembly = pipeline.make_assembly(entry, 128)

        pre = assembly.index("# Isla pre-memory[0]")
        self.assertLess(assembly.index("mret"), pre)
        self.assertLess(pre, assembly.index("li x30, 0x80001000"))
        self.assertLess(assembly.index("li x30, 0x80001000"), assembly.index("payload_ins:"))
        # value null 的 8 个自由字节全部以 0xa5 逐字节 sb 写入
        self.assertIn("li t0, 0x80001000", assembly)
        for offset in range(8):
            self.assertIn(f"li t1, 0xa5", assembly)
            self.assertIn(f"sb t1, {offset}(t0)", assembly)

    def test_multi_byte_value_is_little_endian_per_byte(self):
        entry = make_memory_entry(size=2, pre_value="16'h0f0e")

        assembly = pipeline.make_assembly(entry, 128)

        self.assertIn("li t1, 0x0e", assembly)
        self.assertIn("sb t1, 0(t0)", assembly)
        self.assertIn("li t1, 0x0f", assembly)
        self.assertIn("sb t1, 1(t0)", assembly)
        self.assertNotIn("sb t1, 2(t0)", assembly)

    def test_entry_without_pre_memory_emits_no_stores(self):
        entry = {
            "test-ins": "vadd.vv v8, v4, v12",
            "test-ins-encdec": "32'h0246_0457",
            "isa-state": {},
        }

        assembly = pipeline.make_assembly(entry, 128)

        self.assertNotIn("sb t1", assembly)


class PostMemoryAssemblyTests(unittest.TestCase):
    def test_emits_unsigned_byte_compares_with_per_segment_park(self):
        entry = make_memory_entry(size=2, post_value="16'h0180")

        assembly = pipeline.make_assembly(entry, 128)

        self.assertIn("li t1, 0x80", assembly)
        self.assertIn("lbu t2, 0(t0)", assembly)
        self.assertIn("bne t2, t1, post_park_0", assembly)
        self.assertIn("li t1, 0x01", assembly)
        self.assertIn("lbu t2, 1(t0)", assembly)
        # park 标号专属且死循环
        self.assertIn("post_park_0:\n    j post_park_0", assembly)
        # 检查在 payload 之后、GOODTRAP 之前；park 在 GOODTRAP 之后
        payload = assembly.index(".4byte 0x000f3023")
        first_check = assembly.index("lbu t2, 0(t0)")
        goodtrap = assembly.index(".4byte 0x0000006b")
        park = assembly.index("post_park_0:")
        self.assertLess(payload, first_check)
        self.assertLess(first_check, goodtrap)
        self.assertGreater(park, goodtrap)

    def test_trap_entry_keeps_sentinel_path_without_post_checks(self):
        entry = make_memory_entry(ret_val="Illegal_Instruction(())")

        assembly = pipeline.make_assembly(entry, 128)

        self.assertIn(".4byte 0x00000000", assembly)  # 哨兵保留
        self.assertNotIn("lbu t2", assembly)
        self.assertNotIn("post_park_0", assembly)
        # pre store 仍按重放上下文发射
        self.assertIn("sb t1, 0(t0)", assembly)


class ElfWindowTests(unittest.TestCase):
    def test_elf_alloc_ranges_reads_alloc_sections(self):
        with TemporaryDirectory() as directory:
            elf = Path(directory) / "program.elf"
            elf.write_bytes(
                synthetic_elf_bytes([(0x80000000, 0x120), (0x80001000, 0x10)])
            )
            self.assertEqual(
                pipeline.elf_alloc_ranges(elf),
                [(0x80000000, 0x80000120), (0x80001000, 0x80001010)],
            )

    def test_memory_overlaps_ranges_detects_partial_overlap(self):
        plan = pipeline.memory_plan(make_memory_entry(size=8))
        # pre/post 段 0x80001000..0x80001008 与代码段尾 0x80001004 部分重叠
        ranges = [(0x80000000, 0x80001004)]
        self.assertTrue(pipeline.memory_overlaps_ranges(plan, ranges))
        # 完全在代码之外则不重叠
        self.assertFalse(
            pipeline.memory_overlaps_ranges(plan, [(0x80000000, 0x80001000)])
        )

    def test_memory_overlaps_ranges_includes_event_addresses(self):
        entry = make_memory_entry()
        entry["pre-memory"] = []
        entry["post-memory"] = []
        entry["memory-events"] = [
            {"kind": "write", "address": "64'h0000_0000_8000_0008", "bytes": 8}
        ]
        plan = pipeline.memory_plan(entry)
        self.assertTrue(
            pipeline.memory_overlaps_ranges(plan, [(0x80000000, 0x80000010)])
        )

    def test_compile_case_skips_code_overlap_after_first_pass(self):
        with TemporaryDirectory() as directory:
            output = Path(directory)
            linker = output / "xiangshan.ld"
            linker.write_text(pipeline.LINKER, encoding="utf-8")
            entry = make_memory_entry(address="64'h0000_0000_8000_0000", size=8)
            elf = output / "case-000" / "program.elf"
            calls = []

            def fake_run(command, check=None):
                elf.write_bytes(
                    synthetic_elf_bytes([(0x80000000, 0x120), (0x80001000, 0x10)])
                )
                calls.append(command)
                return None

            with patch.object(pipeline.subprocess, "run", side_effect=fake_run):
                case = pipeline.compile_case(0, entry, output, linker, "gcc", 128)

            self.assertEqual(len(calls), 1)  # 第一遍链接后即判定重叠，不再二次链接
            self.assertEqual(case["skipped_reason"], "code-overlap")
            self.assertNotIn("elf", case)
            self.assertFalse(elf.exists())
            # 汇编保留供诊断
            self.assertTrue((output / "case-000" / "program.S").exists())

    def test_compile_case_rebuilds_final_elf_on_second_pass(self):
        with TemporaryDirectory() as directory:
            output = Path(directory)
            linker = output / "xiangshan.ld"
            linker.write_text(pipeline.LINKER, encoding="utf-8")
            entry = make_memory_entry(address="64'h0000_0000_8000_2000", size=8)
            elf = output / "case-000" / "program.elf"
            calls = []

            def fake_run(command, check=None):
                elf.write_bytes(
                    synthetic_elf_bytes([(0x80000000, 0x120), (0x80001000, 0x10)])
                )
                calls.append(command)
                return None

            with patch.object(pipeline.subprocess, "run", side_effect=fake_run):
                case = pipeline.compile_case(0, entry, output, linker, "gcc", 128)

            # 第二遍重新生成最终 ELF
            self.assertEqual(len(calls), 2)
            self.assertIsNone(case["skipped_reason"])
            self.assertEqual(case["elf"], str(elf))
            self.assertEqual(
                case["sha256"], hashlib.sha256(elf.read_bytes()).hexdigest()
            )
            self.assertEqual(case["path_class"], "ok")
            self.assertEqual(case["memory"]["pre_fill_bytes"], 8)
            self.assertEqual(case["memory"]["pre_segments"], 1)
            recorded = json.loads(
                (output / "case-000" / "case.json").read_text(encoding="utf-8")
            )
            self.assertEqual(recorded["id"], "case-000")
            # memory-events 抄录仅作诊断
            self.assertEqual(len(recorded["memory"]["memory-events"]), 1)

    def test_compile_case_skips_post_all_null_without_linking(self):
        with TemporaryDirectory() as directory:
            output = Path(directory)
            linker = output / "xiangshan.ld"
            entry = make_memory_entry(post_value=None)
            with patch.object(
                pipeline.subprocess, "run"
            ) as run:
                case = pipeline.compile_case(0, entry, output, linker, "gcc", 128)

            run.assert_not_called()
            self.assertEqual(case["skipped_reason"], "post-all-null")
            self.assertNotIn("elf", case)
            self.assertFalse((output / "case-000").exists())


class SamplingTests(unittest.TestCase):
    def test_all_mode_keeps_every_entry(self):
        entries = [{"test-ins-encdec": "32'h1"}, {"test-ins-encdec": "32'h1"}]
        kept, dropped = pipeline.sample_entries(entries, "all")
        self.assertEqual((len(kept), dropped), (2, 0))

    def test_first_per_encoding_keeps_one_per_encoding(self):
        entries = [
            {"test-ins-encdec": "32'h1"},
            {"test-ins-encdec": "32'h1"},
            {"test-ins-encdec": "32'h2"},
        ]
        kept, dropped = pipeline.sample_entries(entries, "first-per-encoding")
        self.assertEqual(len(kept), 2)
        self.assertEqual(dropped, 1)
        self.assertEqual([e["test-ins-encdec"] for e in kept], ["32'h1", "32'h2"])

    def test_unknown_mode_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "sample-mode"):
            pipeline.sample_entries([], "greedy")


class RunSkipsUnbuiltEntriesTests(unittest.TestCase):
    def test_run_ignores_manifest_entries_without_elf(self):
        with TemporaryDirectory() as directory:
            cases_dir = Path(directory)
            elf = cases_dir / "case-000" / "program.elf"
            elf.parent.mkdir(parents=True, exist_ok=True)
            elf.touch()
            manifest = [
                {
                    "id": "case-000",
                    "instruction": "sd x0, 0x0(x30)",
                    "elf": str(elf),
                    "ret_val": "Retire_Success(())",
                    "skipped_reason": None,
                },
                {
                    "id": "case-001",
                    "instruction": "sb x0, 0(x29)",
                    "ret_val": "Retire_Success(())",
                    "skipped_reason": "code-overlap",
                },
            ]
            (cases_dir / "manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            (cases_dir / "emu").touch()
            (cases_dir / "ref.so").touch()
            args = SimpleNamespace(
                cases=str(cases_dir),
                emulator=str(cases_dir / "emu"),
                diff_so=str(cases_dir / "ref.so"),
                jobs=1,
                timeout=5,
            )
            fake = {
                **manifest[0],
                "category": "success",
                "returncode": 0,
                "log": "x",
                "elapsed": 0.1,
            }
            with patch.object(pipeline, "run_case", return_value=fake) as run_case_mock:
                pipeline.run(args)

            run_case_mock.assert_called_once()
            results = json.loads(
                (cases_dir / "results.json").read_text(encoding="utf-8")
            )
            self.assertEqual([item["id"] for item in results], ["case-000"])


def make_fault_entry(
    instruction="sd x0, 0x207(x31)",
    x31="64'h0000_0000_840b_2ff9",
    ret_val="Memory_Exception({tuple#%bv64_%union ExceptionType0: #x00000000840b3200, "
    "tuple#%bv64_%union ExceptionType1: E_SAMO_Access_Fault(())})",
):
    """W12 fault32 形态的 zSTORE 条目：fault 类、无 pre/post/events。"""
    return {
        "test-ins": instruction,
        "test-ins-encdec": "32'h000f_b023",
        "isa-state": {"cur_privilege": "User", "x31": x31},
        "ret_val": ret_val,
        "pre-memory": [],
        "post-memory": [],
        "memory-events": [],
    }


class FaultPreclassTests(unittest.TestCase):
    def test_lowaddr_misaligned_fault_classified_as_mcause_divergence(self):
        # W12 case-001：sh@0x9，NEMU 报错位 mcause6、emu 报 access fault mcause7
        entry = make_fault_entry(instruction="sh x0, 0x9(x0)")
        skip_reason, preclass = pipeline.classify_fault_preclass(entry)
        self.assertEqual(skip_reason, "lowaddr-misaligned-mcause-divergence")

    def test_lowaddr_aligned_fault_is_not_classified(self):
        # W12 探针：低位对齐 fault 两侧一致（sb@0x9、sh@0x2fe）→ 正常重放
        entry = make_fault_entry(instruction="sh x0, 0x2fe(x0)")
        self.assertEqual(pipeline.classify_fault_preclass(entry), (None, None))

    def test_wrapped_high_misaligned_fault_is_not_skipped(self):
        # W12 case-010/017：-1(x0) 回绕成 0xffffffffffffffff，NEMU 按物理地址
        # 位宽截断后可对齐，两侧一致 fault（实测 GOODTRAP），不属低位错位类
        entry = make_fault_entry(instruction="sh x31, -0x1(x0)")
        self.assertEqual(pipeline.classify_fault_preclass(entry), (None, None))

    def test_inmap_aligned_fault_annotated_not_skipped(self):
        # W12 case-015：sd@0x840b3200 图内对齐，Isla 判 fault 属 PMP 假 fault 类；
        # isla 侧钉死 PMP 后应消失，仅标注计数提示上游回归
        entry = make_fault_entry(instruction="sd x0, 0x207(x31)")
        self.assertEqual(
            pipeline.classify_fault_preclass(entry), (None, "in-map-aligned-fault")
        )

    def test_inmap_misaligned_fault_left_unclassified(self):
        # 图内错位：emu 支持错位退休 vs Isla plat_enable_misaligned_access=false，
        # 属 W13 ⑤ 类真分歧，用例集未触发，不在此跳过
        entry = make_fault_entry(instruction="sh x0, 0x202(x31)")
        self.assertEqual(pipeline.classify_fault_preclass(entry), (None, None))

    def test_negative_offset_and_hex_base_are_parsed(self):
        # W12 case-029：sw -0x800(x31)，x31=0x90000800 → 0x90000000 图内对齐
        entry = make_fault_entry(
            instruction="sw x31, -0x800(x31)", x31="64'h0000_0000_9000_0800"
        )
        self.assertEqual(
            pipeline.classify_fault_preclass(entry), (None, "in-map-aligned-fault")
        )

    def test_unparseable_instruction_is_not_classified(self):
        entry = make_fault_entry(instruction="fence iorw, iorw")
        self.assertEqual(pipeline.classify_fault_preclass(entry), (None, None))

    def test_ok_entry_is_never_classified(self):
        entry = make_fault_entry(
            instruction="sh x0, 0x9(x0)", ret_val="Retire_Success(())"
        )
        self.assertEqual(pipeline.classify_fault_preclass(entry), (None, None))


class FaultPreclassCompileTests(unittest.TestCase):
    def test_compile_case_skips_mcause_divergence_before_linking(self):
        with TemporaryDirectory() as directory:
            output = Path(directory)
            linker = output / "xiangshan.ld"
            entry = make_fault_entry(instruction="sh x0, 0x9(x0)")
            with patch.object(pipeline.subprocess, "run") as run:
                case = pipeline.compile_case(0, entry, output, linker, "gcc", 128)

            run.assert_not_called()
            self.assertEqual(
                case["skipped_reason"], "lowaddr-misaligned-mcause-divergence"
            )
            self.assertEqual(case["path_class"], "fault")
            self.assertNotIn("elf", case)
            self.assertFalse((output / "case-000").exists())

    def test_compile_case_annotates_inmap_aligned_fault_but_builds(self):
        with TemporaryDirectory() as directory:
            output = Path(directory)
            linker = output / "xiangshan.ld"
            entry = make_fault_entry(instruction="sd x0, 0x207(x31)")
            elf = output / "case-000" / "program.elf"

            def fake_run(command, check=None):
                elf.write_bytes(
                    synthetic_elf_bytes([(0x80000000, 0x120), (0x80001000, 0x10)])
                )
                return None

            with patch.object(pipeline.subprocess, "run", side_effect=fake_run):
                case = pipeline.compile_case(0, entry, output, linker, "gcc", 128)

            self.assertIsNone(case["skipped_reason"])
            self.assertEqual(case["preclass"], "in-map-aligned-fault")
            self.assertEqual(case["elf"], str(elf))


FAULT_RET_VAL = (
    "Memory_Exception({tuple#%bv64_%union ExceptionType0: #x0000000080001000, "
    "tuple#%bv64_%union ExceptionType1: E_SAMO_Access_Fault(())})"
)


def make_symbolic_boundary_entry(
    ret_val="Retire_Success(())",
    size="64'h0000_0000_0000_1002",
    address="64'h0000_0000_8000_1000",
    empty_memory=False,
):
    """W17 符号边界 zSTORE 条目：isa-state 带 pma_regions.ram.size 侧通道值。

    成功路径带 pre/post/events（样例 case0，size=0x1002 顶界=地址+2）；fault 路径
    三者为空（样例 case1，size=0x1000 顶界=地址）。地址即 x31（偏移 0）。
    """
    entry = {
        "test-ins": "sb x0, 0x0(x31)",
        "test-ins-encdec": "32'h000f_8023",
        "isa-state": {
            "cur_privilege": "User",
            "pma_regions.ram.size": size,
            "x31": address,
        },
        "ret_val": ret_val,
    }
    if empty_memory:
        entry.update({"pre-memory": [], "post-memory": [], "memory-events": []})
    else:
        entry.update({
            "pre-memory": [{"address": address, "bytes": 1, "value": None}],
            "post-memory": [{"address": address, "bytes": 1, "value": "8'h00"}],
            "memory-events": [
                {
                    "kind": "write",
                    "exclusive": False,
                    "region": "default",
                    "address": address,
                    "bytes": 1,
                    "value": "1'h0",
                    "data": "8'h00",
                }
            ],
        })
    return entry


class MapHypothesisParseTests(unittest.TestCase):
    def test_parses_size_base_top_and_effective_address(self):
        hypothesis = pipeline.parse_map_hypothesis(make_symbolic_boundary_entry())

        self.assertEqual(hypothesis["region"], "ram")
        self.assertEqual(hypothesis["size"], 0x1002)
        # base 约定：JSON 不含 base 字段，单 region "ram" 钉 DRAM 基界
        self.assertEqual(hypothesis["base"], 0x80000000)
        self.assertEqual(hypothesis["top"], 0x80001002)
        # 有效地址来自指令偏移+基址寄存器，不依赖 memory-events
        self.assertEqual(hypothesis["address"], 0x80001000)

    def test_fault_path_resolves_address_without_memory_events(self):
        # W17 case1：AccessFault 路径 pre/post/events 全空，地址只能从指令推导
        hypothesis = pipeline.parse_map_hypothesis(
            make_symbolic_boundary_entry(
                ret_val=FAULT_RET_VAL, size="64'h0000_0000_0000_1000", empty_memory=True
            )
        )

        self.assertEqual(hypothesis["size"], 0x1000)
        self.assertEqual(hypothesis["top"], 0x80001000)
        self.assertEqual(hypothesis["address"], 0x80001000)

    def test_entry_without_symbolic_size_returns_none(self):
        self.assertIsNone(pipeline.parse_map_hypothesis(make_memory_entry()))
        self.assertIsNone(pipeline.parse_map_hypothesis(make_fault_entry()))

    def test_malformed_size_value_propagates(self):
        entry = make_symbolic_boundary_entry(size="64'x")
        with self.assertRaisesRegex(ValueError, "pma_regions"):
            pipeline.parse_map_hypothesis(entry)

    def test_unresolvable_address_raises(self):
        # 含符号 size 却解析不出有效地址：无法对照真实地图，宁可构建失败也不放过
        entry = make_symbolic_boundary_entry()
        entry["test-ins"] = "fence iorw, iorw"
        with self.assertRaisesRegex(ValueError, "有效地址"):
            pipeline.parse_map_hypothesis(entry)


class MapHypothesisFilterTests(unittest.TestCase):
    def make_fault_case(self):
        return make_symbolic_boundary_entry(
            ret_val=FAULT_RET_VAL, size="64'h0000_0000_0000_1000", empty_memory=True
        )

    def test_ok_path_inside_real_map_is_replayable(self):
        # W17 case0：地址 0x80001000 在假设顶界内成功，也在真实顶界 0x80000000000 内
        # → 期望行为在真实地图下成立，可重放
        skip, record = pipeline.classify_map_hypothesis(make_symbolic_boundary_entry())

        self.assertIsNone(skip)
        self.assertTrue(record["consistent_with_real_map"])
        self.assertEqual(record["real_limit"], 0x80000000000)
        # base 约定自洽：地址在假设顶界 0x80001002 内
        self.assertTrue(record["hypothesis_consistent"])

    def test_fault_path_inside_real_map_is_skipped(self):
        # W17 case1：假设顶界 0x80001000、地址界外 fault；真实地图地址在界内，
        # fault 不成立 → map-hypothesis-mismatch
        skip, record = pipeline.classify_map_hypothesis(self.make_fault_case())

        self.assertEqual(skip, "map-hypothesis-mismatch")
        self.assertFalse(record["consistent_with_real_map"])
        self.assertTrue(record["hypothesis_consistent"])

    def test_ok_path_beyond_real_map_is_skipped(self):
        # 反向：成功路径但地址 ≥ 真实顶界（符号域上界 2^43 处），重放必 fault
        skip, record = pipeline.classify_map_hypothesis(
            make_symbolic_boundary_entry(address="64'h0000_8000_0000_0000")
        )

        self.assertEqual(skip, "map-hypothesis-mismatch")
        self.assertFalse(record["consistent_with_real_map"])

    def test_fault_path_beyond_real_map_is_replayable(self):
        skip, record = pipeline.classify_map_hypothesis(
            make_symbolic_boundary_entry(
                ret_val=FAULT_RET_VAL, address="64'h0000_8000_0000_0000", empty_memory=True
            )
        )

        self.assertIsNone(skip)
        self.assertTrue(record["consistent_with_real_map"])

    def test_custom_map_limit_changes_verdict(self):
        # 重放平台地图可配：真实顶界收到 0x80001000 时，case0 的成功路径不再成立，
        # case1 的 fault 路径反而与地图一致
        ok_entry = make_symbolic_boundary_entry()

        skip_ok, _ = pipeline.classify_map_hypothesis(ok_entry, map_limit=0x80001000)
        skip_fault, _ = pipeline.classify_map_hypothesis(
            self.make_fault_case(), map_limit=0x80001000
        )

        self.assertEqual(skip_ok, "map-hypothesis-mismatch")
        self.assertIsNone(skip_fault)

    def test_no_symbolic_size_is_never_filtered(self):
        self.assertEqual(pipeline.classify_map_hypothesis(make_memory_entry()), (None, None))
        self.assertEqual(pipeline.classify_map_hypothesis(make_fault_entry()), (None, None))


class MapHypothesisCompileTests(unittest.TestCase):
    def test_compile_case_skips_mismatch_before_linking(self):
        with TemporaryDirectory() as directory:
            output = Path(directory)
            linker = output / "xiangshan.ld"
            entry = make_symbolic_boundary_entry(
                ret_val=FAULT_RET_VAL, size="64'h0000_0000_0000_1000", empty_memory=True
            )
            with patch.object(pipeline.subprocess, "run") as run:
                case = pipeline.compile_case(0, entry, output, linker, "gcc", 128)

            run.assert_not_called()
            self.assertEqual(case["skipped_reason"], "map-hypothesis-mismatch")
            self.assertEqual(case["path_class"], "fault")
            self.assertNotIn("elf", case)
            self.assertFalse((output / "case-000").exists())
            self.assertEqual(case["map_hypothesis"]["size"], 0x1000)
            self.assertFalse(case["map_hypothesis"]["consistent_with_real_map"])

    def test_compile_case_builds_consistent_entry_and_records_hypothesis(self):
        with TemporaryDirectory() as directory:
            output = Path(directory)
            linker = output / "xiangshan.ld"
            linker.write_text(pipeline.LINKER, encoding="utf-8")
            entry = make_symbolic_boundary_entry()
            elf = output / "case-000" / "program.elf"

            def fake_run(command, check=None):
                # 代码窗口只含 .text.init，不与 0x80001000 内存段重叠
                elf.write_bytes(synthetic_elf_bytes([(0x80000000, 0x120)]))
                return None

            with patch.object(pipeline.subprocess, "run", side_effect=fake_run):
                case = pipeline.compile_case(0, entry, output, linker, "gcc", 128)

            self.assertIsNone(case["skipped_reason"])
            self.assertEqual(case["elf"], str(elf))
            self.assertEqual(case["map_hypothesis"]["top"], 0x80001002)
            recorded = json.loads(
                (output / "case-000" / "case.json").read_text(encoding="utf-8")
            )
            self.assertEqual(recorded["map_hypothesis"]["size"], 0x1002)
            self.assertEqual(recorded["map_hypothesis"]["real_limit"], 0x80000000000)

    def test_compile_case_honors_custom_map_limit(self):
        with TemporaryDirectory() as directory:
            output = Path(directory)
            linker = output / "xiangshan.ld"
            entry = make_symbolic_boundary_entry()
            with patch.object(pipeline.subprocess, "run") as run:
                case = pipeline.compile_case(
                    0, entry, output, linker, "gcc", 128, map_limit=0x80001000
                )

            run.assert_not_called()
            self.assertEqual(case["skipped_reason"], "map-hypothesis-mismatch")


class MapHypothesisSummaryTests(unittest.TestCase):
    def test_build_summary_counts_map_hypothesis(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / "in.json"
            source.write_text(
                json.dumps(
                    {
                        "gen": [
                            make_symbolic_boundary_entry(),
                            make_symbolic_boundary_entry(
                                ret_val=FAULT_RET_VAL,
                                size="64'h0000_0000_0000_1000",
                                empty_memory=True,
                            ),
                        ]
                    }
                ),
                encoding="utf-8",
            )
            out = Path(directory) / "elf"
            args = SimpleNamespace(
                input=str(source),
                output=str(out),
                vlen_bits=128,
                compiler="gcc",
                jobs=1,
                sample_mode="all",
                map_limit=pipeline.EMU_RAM_LIMIT,
            )
            built_case = {
                "id": "case-000",
                "path_class": "ok",
                "skipped_reason": None,
                "preclass": None,
                "map_hypothesis": {"region": "ram"},
                "elf": "x",
            }
            skipped_case = {
                "id": "case-001",
                "path_class": "fault",
                "skipped_reason": "map-hypothesis-mismatch",
                "preclass": None,
                "map_hypothesis": {"region": "ram"},
            }
            with patch.object(
                pipeline, "compile_case", side_effect=[built_case, skipped_case]
            ):
                pipeline.build(args)

            summary = json.loads(
                (out / "build-summary.json").read_text(encoding="utf-8")
            )
            self.assertEqual(summary["built"], 1)
            self.assertEqual(summary["skipped"], {"map-hypothesis-mismatch": 1})
            self.assertEqual(summary["map_hypothesis"], {"checked": 2, "skipped": 1})


class DataSectionTests(unittest.TestCase):
    def test_entry_without_vregs_omits_dead_data_section(self):
        # W17 样例访存地址 0x80001000 与 8 字节占位 .data 精确相撞（code-overlap
        # 误伤可重放条目）；无 vreg 条目不引用 vector_initial_state，省去占位段
        assembly = pipeline.make_assembly(make_symbolic_boundary_entry(), 128)

        self.assertNotIn(".section .data", assembly)
        self.assertNotIn("vector_initial_state", assembly)

    def test_entry_with_vregs_keeps_vector_initial_state(self):
        entry = {
            "test-ins": "vadd.vv v8, v4, v12",
            "test-ins-encdec": "32'h0246_0457",
            "isa-state": {
                "cur_privilege": "User",
                "vl": "64'h0000_0000_0000_0007",
                "vtype": "64'h0000_0000_0000_00da",
                "vr8": "128'h0000_0000_0000_0000_0000_0000_0000_0001",
            },
        }

        assembly = pipeline.make_assembly(entry, 128)

        self.assertIn(".section .data", assembly)
        self.assertIn("vector_initial_state:", assembly)


if __name__ == "__main__":
    unittest.main()
