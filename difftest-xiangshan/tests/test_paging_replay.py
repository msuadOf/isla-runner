"""E0 的转换、ELF 与结果归类契约；先于实现运行。"""
import copy
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import paging_replay as replay


def bits(value):
    return {"bits": f"{value:064b}"}


def cells(words):
    return [{"address": address + i, "bytes": 1, "value": (word >> (8*i)) & 255}
            for address, word in words.items() for i in range(8)]


def sample():
    region = lambda base, size: {"struct": {"base": bits(base), "size": bits(size),
        "attributes": {"struct": {"readable": {"bool": True}, "writable": {"bool": True}}},
        "include_in_device_tree": {"bool": True}}}
    words = {0x80200000: (0x4000 << 10) | 1 | (3 << 59) | 0xd0,
             0x4000800: (0x5000 << 10) | 1, 0x5000000: (0x6000 << 10) | 0xc3,
             0x6000000: 0x123456789abcdef0}
    return dict(schema_version=1, sample_id=7, mode="merge", path_signature=0, class_id=0,
        truncated=False, pre_registers={"satp": bits(0x8000000000080200),
            "x1": bits(0x20000000), "x2": bits(0),
            "mstatus": {"struct": {"bits": bits(0)}}, "cur_privilege": {"enum": "Supervisor"},
            "menvcfg": {"struct": {"bits": bits(0)}}, "tlb": {"vector": []},
            "pma_regions": {"list": [region(0x80000000, 2**43-0x80000000), region(0x4000000, 0x7c000000)]}},
        post_registers={"x2": bits(words[0x6000000])}, isa_state={"$instruction": "ld x2, 0(x1)"},
        pre_memory=cells(words), post_memory=cells(words),
        result={"ctor": "Retire_Success", "value": {"unit": True}}, ret_val="Retire_Success(())")


def fault(s, cause):
    s["result"] = {"ctor": "Memory_Exception", "value": {"struct": {
        "tuple#%bv64_%union zExceptionType0": bits(0x20000000),
        "tuple#%bv64_%union zExceptionType1": {"ctor": "E_Load_Page_Fault" if cause == 13 else "E_Load_Access_Fault", "value": {"unit": True}}}}}
    s["ret_val"] = "Memory_Exception"


class ReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decoder, cls.provenance = replay.load_decoder(Path(os.environ["PT_DECODE_DIR"]))

    def test_decode_and_elf_bind_dynamic_operands_and_root(self):
        from test_paging_fuzz import FuzzTests
        fixture = FuzzTests()
        fixture.decoder, _ = replay.load_decoder(os.environ['PT_DECODE_DIR'], standard_paging=True)
        parent = Path(os.environ.get('PAGING_TEST_OUTPUT_DIR', ROOT.parent / 'output/e0/unit'))
        parent.mkdir(parents=True, exist_ok=True)
        for register in (0, 5, 8, 31):
            with self.subTest(register=register):
                s = fixture.dynamic_seed('sv39', 'load', 0x20007008, register=register, typed=True)
                decoded = replay.decode(s, self.decoder)
                self.assertEqual(decoded['va'], 0x20007008)
                self.assertEqual(decoded['root_paddr'], 0x80500000)
                c = replay.relocate_sample(s, self.decoder)
                self.assertEqual(c['expected']['rd'], 0 if register == 0 else 0x1234)
                asm = replay.paging_assembly(c)
                saved = 'x30' if register == 31 else 'x31'
                self.assertIn(f'ld x{register}, -24(x11)\n    mv {saved}, x{register}', asm)
                self.assertIn(f'li x11, {0x20007008+24:#x}', asm)
                self.assertIn(f'bne {saved}, t0, fail_rd', asm)
                self.assertLess(asm.index(f'trap_handler:\n    mv {saved},'),
                                asm.index('csrr s0, mcause', asm.index('trap_handler:')))
                with tempfile.TemporaryDirectory(dir=parent) as directory:
                    built = replay.build_case(c, directory)
                    text = (Path(directory)/'objdump.txt').read_text()
                    self.assertRegex(text, rf"{built['symbols']['payload_ins']:x}:\s+{c['instruction']['word']:08x}\s")

    def test_damaged_constructor_does_not_fall_back_to_assembly(self):
        from test_paging_fuzz import FuzzTests
        fixture = FuzzTests()
        fixture.decoder = self.decoder
        s = fixture.dynamic_seed('sv39', 'load', 0x20001000, typed=True)
        s['isa_state']['$instruction'] = 'ld x12, -24(x11)'
        del s['pre_registers']['$instruction']['value']['struct'][self.decoder.LOAD_FIELDS[2]]
        with self.assertRaises(ValueError):
            replay.instruction_binding(s, self.decoder)

    def test_relocates_shared_frames_and_normalizes_both_memories(self):
        s = sample(); before = copy.deepcopy(s)
        c = replay.relocate_sample(s, self.decoder)
        self.assertEqual(s, before)
        self.assertEqual(c["sample"]["pre_registers"], s["pre_registers"])
        self.assertEqual(c["expected"], {"cause": 0, "tval": 0, "rd": 0x123456789abcdef0})
        self.assertEqual(c["sample"]["pre_memory"], c["sample"]["post_memory"])
        self.assertEqual(len(c["writes"]), 4)
        for w in c["writes"]:
            self.assertTrue(w["address"] == 0x80200000 or w["address"] >= 0x100000000)
            if w["role"] == "pointer":
                self.assertEqual(w["value"] & ((3 << 59) | 0xd0), 0)

    def test_rejects_result_mismatch_and_nonempty_tlb(self):
        s = sample(); fault(s, 13)
        with self.assertRaisesRegex(ValueError, "result_mismatch"):
            replay.relocate_sample(s, self.decoder)
        s = sample(); s["pre_registers"]["tlb"] = {"vector": [{"ctor": "Some", "value": {}}]}
        with self.assertRaisesRegex(ValueError, "R5"):
            replay.relocate_sample(s, self.decoder)

    def test_nonram_pointer_moves_to_af_region_without_materializing(self):
        s = sample(); s["pre_memory"] = cells({0x80200000: 1}); s["post_memory"] = s["pre_memory"]
        fault(s, 5)
        c = replay.relocate_sample(s, self.decoder)
        self.assertEqual(c["expected"]["cause"], 5)
        self.assertEqual(c["writes"][0]["value"] >> 10, 2**32)
        self.assertEqual(len(c["writes"]), 1)

    def test_high_ppn_remains_high(self):
        s = sample(); words = {0x80200000: (0x4000 << 10) | 1,
            0x4000800: (0x5000 << 10) | 1, 0x5000000: (2**36 << 10) | 0xc3}
        s["pre_memory"] = cells(words); s["post_memory"] = cells(words); fault(s, 5)
        c = replay.relocate_sample(s, self.decoder)
        self.assertEqual(c["expected"]["cause"], 5)
        self.assertTrue(any(w["value"] >> 10 == 2**36 for w in c["writes"]))

    def test_reserved_bit_stays_reserved_and_v_zero_is_page_fault(self):
        for bit, clear_v in ((54, False), (0, True)):
            s = sample()
            for field in ("pre_memory", "post_memory"):
                s[field] = [c for c in s[field] if not 0x6000000 <= c["address"] < 0x6000008]
                for cell in s[field]:
                    if cell["address"] == 0x5000000 + bit//8:
                        if clear_v:
                            cell["value"] &= ~1
                        else:
                            cell["value"] |= 1 << (bit%8)
            fault(s, 13)
            c = replay.relocate_sample(s, self.decoder)
            self.assertEqual(c["expected"]["cause"], 13)
            if not clear_v:
                self.assertTrue(any(w["value"] & (1 << 54) for w in c["writes"]))

    def test_real_elf_is_compact_handler_aligned_and_negative_input_unchanged(self):
        parent = Path(os.environ.get("PAGING_TEST_OUTPUT_DIR", ROOT.parent / "output/e0/unit"))
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as directory:
            c = replay.relocate_sample(sample(), self.decoder)
            built = replay.build_case(c, Path(directory))
            self.assertEqual(built["symbols"]["trap_handler"] % 4, 0)
            self.assertTrue(all(0x80000000 <= start < end <= 0x80100000
                for start, end in replay.pipeline.elf_alloc_ranges(Path(built["elf"]))))
            wrong = copy.deepcopy(c)
            wrong["expected"] = {"cause": 13, "tval": 0x20000000, "rd": None}
            self.assertEqual(c["writes"], wrong["writes"])
            self.assertIn("j fail_missing_trap", replay.paging_assembly(wrong))

    def test_assembly_order_and_negative_expectation(self):
        c = replay.relocate_sample(sample(), self.decoder)
        asm = replay.paging_assembly(c)
        keys = ["csrw satp, zero", "sd t1, 0(t0)", "csrw satp, t0", "sfence.vma", "csrw mstatus, t0", "li x1,", "payload_ins:"]
        positions = [asm.index(k) for k in keys]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("csrw medeleg, zero", asm); self.assertIn("csrw mideleg, zero", asm)
        self.assertIn(".balign 4\ntrap_handler:", asm)
        self.assertIn("fail_unexpected_trap:", asm)
        self.assertIn(".4byte 0x0005006b", asm)
        self.assertIn("csrr s0, mcause", asm); self.assertIn("csrr s1, mtval", asm)

    def test_good_at_failure_symbol_is_never_agreement(self):
        symbols = {"fail_unexpected_trap_trap": 0x80000224}
        r = replay.classify_log("HIT GOOD TRAP at pc = 0x80000224", 0, symbols, elf_sha256="abc", expected_elf_sha256="abc")
        self.assertFalse(r["agree"])
        self.assertEqual(r["bucket"], "xs!=expected")
        self.assertTrue(r["false_good"])

    def test_log_classification_checks_returncode_and_exact_bad_symbol(self):
        symbols = {"fail_unexpected_trap": 0x80000300, "fail_unexpected_trap_trap": 0x80000304}
        r = replay.classify_log("HIT BAD TRAP at pc = 0x80000304", 1, symbols, elf_sha256="abc", expected_elf_sha256="abc")
        self.assertEqual(r["bad_symbol"], "fail_unexpected_trap_trap")
        self.assertFalse(replay.classify_log("HIT GOOD TRAP", 1, {})["agree"])
        r = replay.classify_log("Warning: L2TLB resp test of core 0 sector 0 failed!\nABORT at pc", 1, {}, elf_sha256="abc", expected_elf_sha256="abc")
        self.assertTrue(r["l2tlb_failed"]); self.assertEqual(r["bucket"], "framework-abort")

    def test_agreement_requires_one_exact_good_pc_and_matching_elf(self):
        symbols = {"good_trap_ins": 0x80000244, "check_memory": 0x80000200}
        good = "HIT GOOD TRAP at pc = 0x80000244"
        def classify(log, code=0, actual="abc", expected="abc"):
            return replay.classify_log(log, code, symbols, elf_sha256=actual,
                                       expected_elf_sha256=expected)
        self.assertTrue(classify(good)["agree"])
        for log, code in [(good, 1), ("HIT GOOD TRAP at pc = 0x80000999", 0),
                          ("HIT GOOD TRAP at pc = 0x80000200", 0), ("HIT GOOD TRAP", 0),
                          ("", 0), (good+"\n"+good, 0), (good+"\nABORT", 0),
                          (good+"\nHIT BAD TRAP at pc = 0x80000244", 0)]:
            with self.subTest(log=log, code=code):
                self.assertFalse(classify(log, code)["agree"])
        self.assertFalse(classify(good, actual="def")["agree"])
        self.assertFalse(classify(good, actual=None, expected=None)["agree"])
        for limit in ("EXCEEDING CYCLE LIMIT", "EXCEEDING INSTR LIMIT", "EXCEEDING CYCLE/INSTR LIMIT"):
            r = classify(good+"\n"+limit)
            self.assertFalse(r["agree"])
            self.assertEqual(r["bucket"], "limit")
        self.assertEqual(classify(good, code=None)["bucket"], "timeout")

    def test_failure_pc_returns_reason_for_good_and_bad(self):
        for reason in replay.FAILURE_REASONS:
            for label in ("GOOD", "BAD"):
                symbol = f"fail_{reason}_trap"
                r = replay.classify_log(f"HIT {label} TRAP at pc = 0x80000304", 0,
                    {symbol: 0x80000304}, elf_sha256="abc", expected_elf_sha256="abc")
                self.assertEqual(r["bucket"], "xs!=expected")
                self.assertEqual(r["reason"], reason)

    def test_build_rejects_bypassed_checks_extra_trap_and_aliased_failure(self):
        c = replay.relocate_sample(sample(), self.decoder)
        assembly = replay.paging_assembly(c)
        variants = [assembly.replace("payload_ins:", "    j good_trap\npayload_ins:"),
                    assembly.replace("payload_ins:", "    j good_trap_ins\npayload_ins:"),
                    assembly.replace("payload_ins:", "    .4byte 0x0000006b\npayload_ins:"),
                    assembly.replace("fail_rd:", "fail_alias_trap:\nfail_rd:")]
        parent = Path(os.environ.get("PAGING_TEST_OUTPUT_DIR", ROOT.parent / "output/exit/unit"))
        parent.mkdir(parents=True, exist_ok=True)
        for variant in variants:
            with self.subTest(variant=variants.index(variant)):
                with tempfile.TemporaryDirectory(dir=parent) as directory:
                    with patch.object(replay, "paging_assembly", return_value=variant):
                        with self.assertRaisesRegex(ValueError, "出口静态检查"):
                            replay.build_case(c, directory)

    def test_directed_probe_keeps_addresses_pte_and_isla_expectation(self):
        s = replay.relocate_sample(sample(), self.decoder)["sample"]
        before = copy.deepcopy(s)
        c = replay.directed_probe_case(s, self.decoder)
        self.assertEqual(s, before)
        self.assertEqual({w["address"]: w["value"] for w in c["writes"]},
                         {e["paddr"]: int(e["value"], 16) for e in c["decoded"]["entries"]})
        self.assertEqual(c["expected"]["rd"], int(s["post_registers"]["x2"]["bits"], 2))
        with self.assertRaisesRegex(ValueError, "Svrsw60t59b"):
            replay.directed_probe_case(sample(), self.decoder)

    def test_directed_store_fills_null_with_inverse_post_value(self):
        s = replay.relocate_sample(sample(), self.decoder)["sample"]
        walk = self.decoder.decode_sample(s, self.decoder.Config(True, False, False))
        leaf = next(e["paddr"] for e in walk["entries"] if e["role"] == "leaf")
        for name in ("pre_memory", "post_memory"):
            next(cell for cell in s[name] if cell["address"] == leaf)["value"] |= 4
        s["isa_state"]["$instruction"] = "sd x2, 0(x1)"
        data = next(e["paddr"] for e in self.decoder.decode_sample(
            s, self.decoder.Config(True, False, False))["entries"] if e["role"] == "data")
        for cell in s["pre_memory"]:
            if data <= cell["address"] < data+8:
                cell["value"] = None
        c = replay.directed_probe_case(s, self.decoder)
        word = next(w for w in c["writes"] if w["address"] == data)
        self.assertEqual(word["value"] ^ word["expected_value"], (1 << 64)-1)
        self.assertIsNone(c["expected"]["rd"])
        self.assertIn("sd x2, 0(x1)", replay.paging_assembly(c))

    def test_directed_real_s_has_distinct_fetch_mapping_and_returns_via_ecall(self):
        s = replay.relocate_sample(sample(), self.decoder)["sample"]
        c = replay.directed_probe_case(s, self.decoder, "s")
        fetch = [w for w in c["writes"] if w["role"] == "harness_fetch"]
        self.assertEqual(len(fetch), 1)
        self.assertEqual(fetch[0]["address"], 0x80200010)
        self.assertEqual(fetch[0]["value"] & 0xff, 0xcb)
        asm = replay.paging_assembly(c)
        self.assertIn("mret\ns_entry:", asm)
        self.assertIn("s_return:\n    ecall", asm)
        parent = Path(os.environ.get("PAGING_TEST_OUTPUT_DIR", ROOT.parent / "output/e1-e4/unit"))
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as directory:
            built = replay.build_case(c, directory)
            self.assertGreater(built["symbols"]["payload_ins"], built["symbols"]["s_entry"])


if __name__ == "__main__":
    unittest.main()
