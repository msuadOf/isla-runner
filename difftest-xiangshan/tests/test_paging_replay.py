"""E0 的转换、ELF 与结果归类契约；先于实现运行。"""
import copy
import os
from pathlib import Path
import sys
import tempfile
import unittest

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
        parent = ROOT.parent / "output/e0/unit"
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
        r = replay.classify_log("HIT GOOD TRAP at pc = 0x80000224", 0, symbols)
        self.assertFalse(r["agree"])
        self.assertEqual(r["bucket"], "xs!=expected")
        self.assertTrue(r["false_good"])

    def test_log_classification_checks_returncode_and_exact_bad_symbol(self):
        symbols = {"fail_unexpected_trap": 0x80000300, "fail_unexpected_trap_trap": 0x80000304}
        r = replay.classify_log("HIT BAD TRAP at pc = 0x80000304", 1, symbols)
        self.assertEqual(r["bad_symbol"], "fail_unexpected_trap_trap")
        self.assertFalse(replay.classify_log("HIT GOOD TRAP", 1, {})["agree"])
        r = replay.classify_log("Warning: L2TLB resp test of core 0 sector 0 failed!\nABORT at pc", 1, {})
        self.assertTrue(r["l2tlb_failed"]); self.assertEqual(r["bucket"], "framework-abort")


if __name__ == "__main__":
    unittest.main()
