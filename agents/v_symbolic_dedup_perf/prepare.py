"""从随仓库保存的快照准备可复现的性能测试输入。"""

import gzip
import hashlib
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parent
ISLA = ROOT.parents[1] / "isla"
IR_SHA256 = {
    "base": "adcaf7f7d42380a1d1d68861f06f4e2ea44c18c0a18242adc8ec4cb2cb0318a1",
    "new": "6fc39efd0f72b0ee8eae247d9965e680b6874f9954334c20d748b42c0987792c",
    "history": "7c626989a03056c43c67c81de8f40f611cef4c43ed1069a81526b37856d7e37b",
    "direct": "dde00e1b7ec8eff4d3ee08109fafb3f3c0365bb80248b5c2cef62ddaf68291fa",
}
ISARCH_SHA256 = "534c3b9d5126956847e4b2667dfa58d1ee95a079cade1b780a340e32cd07fc65"


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def prepare(kinds: tuple[str, ...]) -> None:
    binary = ISLA / "target/release/isarch"
    if digest(binary) != ISARCH_SHA256:
        raise RuntimeError(f"需要原测试使用的 release isarch：{binary}，SHA-256 {ISARCH_SHA256}")
    if not (ROOT / "isarch").exists():
        shutil.copy2(binary, ROOT / "isarch")
    if digest(ROOT / "isarch") != ISARCH_SHA256:
        raise RuntimeError("本地 isarch 与原测试版本不一致")
    shutil.copy2(ISLA / "configs/riscv64_difftest.toml", ROOT / "isa.toml")

    for kind in kinds:
        expected = IR_SHA256[kind]
        target_dir = ROOT / kind
        target_dir.mkdir(exist_ok=True)
        target = target_dir / "rv64d.ir"
        if not target.exists() or digest(target) != expected:
            with gzip.open(ROOT / "snapshots" / f"{kind}.rv64d.ir.gz", "rb") as source:
                with target.open("wb") as output:
                    shutil.copyfileobj(source, output)
        if digest(target) != expected:
            raise RuntimeError(f"IR 快照校验失败：{target}")

        for clause in ("masktypei", "vrev8_v", "vimctype"):
            content = (ROOT / "fixtures" / f"{clause}.toml").read_text()
            assert content.count(IR_SHA256["history"]) == 1, clause
            content = content.replace(IR_SHA256["history"], expected)
            if clause == "masktypei" and kind in ("new", "direct"):
                assert "start_line = 1448" in content and "end_line = 1458" in content
                content = content.replace("start_line = 1448", "start_line = 1367")
                content = content.replace("end_line = 1458", "end_line = 1377")
            (target_dir / f"{clause}.toml").write_text(content)


if __name__ == "__main__":
    prepare(tuple(IR_SHA256))
    print("四份 IR 快照及对应配置已准备并校验")
