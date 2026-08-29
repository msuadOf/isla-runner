# agent06: PMA/MMIO validation matrix

日期：2026-04-27

范围：为 PMA/MMIO 阶段设计可重复验证矩阵和命令。本文只定义验证前提、命令、比较字段和判据，不修改生产代码。

## 前提

- `pmpCheck` exact summary 必须显式开启：`ISLA_RISCV_BUILTIN_PMP_CHECK=1`。
- 不使用 PMP-off 诊断捷径：`ISLA_RISCV_ASSUME_PMP_OFF=0`。PMP-off 只能定位下一层热点，不能作为 PMA/MMIO 语义基线。
- VMEM addr builtin 必须关闭，让 `zSTORE` / `zLOAD` 走回 `vmem_*_addr -> phys_access_check -> pmaCheck -> RAM/MMIO` 链路：
  - `ISLA_RISCV_VMEM_BUILTIN_MODE=off`
  - `ISLA_RISCV_BUILTIN_VMEM_WRITE_ADDR=0`
  - `ISLA_RISCV_BUILTIN_VMEM_READ_ADDR=0`
- 固定当前样例宽度：
  - `ISLA_RISCV_TEST_ZSTORE_WIDTH=4`
  - `ISLA_RISCV_TEST_ZLOAD_WIDTH=4`
- 继续保留已验证的局部 summary / guard：
  - `ISLA_RISCV_BUILTIN_RANGE_SUBSET=1`
  - `ISLA_RISCV_BUILTIN_SPLIT_MISALIGNED=1`
  - `ISLA_RISCV_VMEM_ASSUME_ALIGNED=1`
  - `ISLA_RISCV_BUILTIN_PMP_RANGE_MATCH=1`
  - `ISLA_RISCV_BUILTIN_PMP_ADDR_MATCH_TYPE=1`
  - `ISLA_RISCV_BUILTIN_PMP_CHECK_RWX=1`
  - `ISLA_RISCV_BUILTIN_PMP_LOCKED=1`
- 保持 `pmpMatchAddr` 大 summary 关闭：`ISLA_RISCV_BUILTIN_PMP_MATCH_ADDR=0`。它降低 executor fork 深度但吞吐不稳定。
- 开启 profile hook：`ISLA_RISCV_PROFILE_FORKS=1`，用于从 `run.log` 中收集 `fork_profile=<json>`。

当前工作区尚未出现 `ISLA_RISCV_BUILTIN_PMA_CHECK` gate；以下命令把它作为 PMA 阶段约定 gate 使用。若分支还没有实现该 gate，`pma-on` 与 `pma-off` 会退化为同一条执行路径，只能验证基线命令是否可跑，不能声明 PMA summary 收益。

## 验证矩阵

| case | timeout | `ISLA_RISCV_BUILTIN_PMA_CHECK` | 目的 |
| --- | ---: | --- | --- |
| `pma-off-short` | `45s` | `0` | PMP exact summary 后的 PMA/MMIO baseline 短跑，确认无 panic / fallback / `SymbolicLength`。 |
| `pma-on-short` | `45s` | `1` | 快速观察 `pmaCheck` summary 是否降低 `matching_pma_bits_range` / `phys_access_check` / MMIO fork 热点。 |
| `pma-off-long` | `180s` 起，必要时 `300s` | `0` | 生成语义 baseline JSON；没有 baseline JSON 时不能做语义等价结论。 |
| `pma-on-long` | 与 `pma-off-long` 相同 | `1` | 生成待比较 JSON，并与 `pma-off-long` 做 observable 对照。 |

如果 `pma-off-long` 在本机 `180s` 内没有生成 `rv64d_zSTORE.json` / `rv64d_zLOAD.json`，先提升到 `300s`。若 baseline 仍超时，只能记录性能趋势；语义通过必须等到 off/on 双方都有 JSON。

## 对照命令

以下命令从 `/tmp` 独立目录运行，所有 `output/`、`solver.dump`、`run.log`、`exit.code` 都落在 case 目录，不覆盖仓库内产物。

```bash
ROOT=/home/baiyifan/workplace-local/isla-runner
ISLA="$ROOT/isla"
RUN=/tmp/isla-pma-mmio-$(date +%Y%m%d-%H%M%S)
mkdir -p "$RUN"

run_case() {
  case_name="$1"
  pma_gate="$2"
  timeout_s="$3"

  mkdir -p "$RUN/$case_name"
  (
    cd "$RUN/$case_name"
    set +e
    env \
      RUST_BACKTRACE=1 \
      ISLA_RISCV_PROFILE_FORKS=1 \
      ISLA_RISCV_TEST_ZSTORE_WIDTH=4 \
      ISLA_RISCV_TEST_ZLOAD_WIDTH=4 \
      ISLA_RISCV_VMEM_ASSUME_ALIGNED=1 \
      ISLA_RISCV_BUILTIN_SPLIT_MISALIGNED=1 \
      ISLA_RISCV_BUILTIN_RANGE_SUBSET=1 \
      ISLA_RISCV_BUILTIN_PMP_RANGE_MATCH=1 \
      ISLA_RISCV_BUILTIN_PMP_ADDR_MATCH_TYPE=1 \
      ISLA_RISCV_BUILTIN_PMP_CHECK_RWX=1 \
      ISLA_RISCV_BUILTIN_PMP_LOCKED=1 \
      ISLA_RISCV_BUILTIN_PMP_MATCH_ADDR=0 \
      ISLA_RISCV_ASSUME_PMP_OFF=0 \
      ISLA_RISCV_BUILTIN_PMP_CHECK=1 \
      ISLA_RISCV_VMEM_BUILTIN_MODE=off \
      ISLA_RISCV_BUILTIN_VMEM_WRITE_ADDR=0 \
      ISLA_RISCV_BUILTIN_VMEM_READ_ADDR=0 \
      ISLA_RISCV_BUILTIN_PMA_CHECK="$pma_gate" \
      timeout "$timeout_s" \
      cargo run --locked --manifest-path "$ISLA/Cargo.toml" --bin isarch --release -- \
        -A "$ISLA/rv64d.ir" \
        -C "$ISLA/configs/riscv64_difftest.toml" \
        --verbose --probe-all --trace-all \
        -I cur_privilege=Machine \
        list-instructions \
        >run.log 2>&1
    status=$?
    printf '%s\n' "$status" >exit.code
    exit 0
  )
}

run_case pma-off-short 0 45s
run_case pma-on-short 1 45s
run_case pma-off-long 0 180s
run_case pma-on-long 1 180s

printf 'results under %s\n' "$RUN"
```

长跑若要升到 `300s`，只重跑 long case 即可：

```bash
run_case pma-off-long-300 0 300s
run_case pma-on-long-300 1 300s
```

## JSON 比较命令

先用现有 normalize 工具比较 `ret_val` 与主要 memory event shape：

```bash
mkdir -p "$RUN/compare"

python3 "$ROOT/agents/zSTORE_path_explosion/normalize_vmem_output.py" \
  "$RUN/pma-off-long/output/rv64d_zSTORE.json" \
  "$RUN/pma-on-long/output/rv64d_zSTORE.json" \
  >"$RUN/compare/zSTORE-normalized.json"

python3 "$ROOT/agents/zSTORE_path_explosion/normalize_vmem_output.py" \
  "$RUN/pma-off-long/output/rv64d_zLOAD.json" \
  "$RUN/pma-on-long/output/rv64d_zLOAD.json" \
  >"$RUN/compare/zLOAD-normalized.json"
```

`normalize_vmem_output.py` 当前覆盖：

- `ret_val`
- `memory-events` 的 `kind`、`region`、`bytes`、`address_model`、`value`、`data`、`is_ifetch`、`is_exclusive`
- 每条 path 的 memory event 数量和事件 multiset

PMA/MMIO 阶段还必须额外比较：

- raw `memory-events[].address`，因为 PMA/MMIO 边界直接依赖物理地址。
- `ret_val` 中的 exception type，例如 `E_SAMO_Access_Fault`、`E_Load_Access_Fault`、`E_SAMO_Addr_Align`、`E_Load_Addr_Align`。
- `ret_val` 中的 exception address，尤其是 `Memory_Exception(..., paddr)` 的地址表达式。
- store success 约束：write event 的 `value` 字段必须保持等价，不能从 asserted success 变成未约束/可失败 payload。

可用下面的一次性 digest 命令补齐 address 和 exception 摘要，不需要修改仓库脚本：

```bash
python3 - "$RUN/pma-off-long/output/rv64d_zSTORE.json" "$RUN/pma-on-long/output/rv64d_zSTORE.json" "$RUN/compare/zSTORE-observables.json" <<'PY'
import json
import re
import sys
from collections import Counter
from pathlib import Path

def load(path):
    data = json.loads(Path(path).read_text())
    return data["gen"]

def item_key(item):
    ret = item.get("ret_val")
    exc = tuple(re.findall(r"E_[A-Za-z0-9_]+|#x[0-9a-fA-F]+", ret or ""))
    events = []
    for event in item.get("memory-events", []):
        events.append(tuple((field, event.get(field)) for field in (
            "kind", "region", "bytes", "address", "address_model",
            "value", "data", "is_ifetch", "is_exclusive",
        ) if field in event))
    return (ret, exc, tuple(events))

def counter(path):
    return Counter(item_key(item) for item in load(path))

left = counter(sys.argv[1])
right = counter(sys.argv[2])
out = {
    "left_only": [{"key": repr(key), "count": count} for key, count in (left - right).items()],
    "right_only": [{"key": repr(key), "count": count} for key, count in (right - left).items()],
}
Path(sys.argv[3]).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
PY

python3 - "$RUN/pma-off-long/output/rv64d_zLOAD.json" "$RUN/pma-on-long/output/rv64d_zLOAD.json" "$RUN/compare/zLOAD-observables.json" <<'PY'
import json
import re
import sys
from collections import Counter
from pathlib import Path

def load(path):
    data = json.loads(Path(path).read_text())
    return data["gen"]

def item_key(item):
    ret = item.get("ret_val")
    exc = tuple(re.findall(r"E_[A-Za-z0-9_]+|#x[0-9a-fA-F]+", ret or ""))
    events = []
    for event in item.get("memory-events", []):
        events.append(tuple((field, event.get(field)) for field in (
            "kind", "region", "bytes", "address", "address_model",
            "value", "data", "is_ifetch", "is_exclusive",
        ) if field in event))
    return (ret, exc, tuple(events))

def counter(path):
    return Counter(item_key(item) for item in load(path))

left = counter(sys.argv[1])
right = counter(sys.argv[2])
out = {
    "left_only": [{"key": repr(key), "count": count} for key, count in (left - right).items()],
    "right_only": [{"key": repr(key), "count": count} for key, count in (right - left).items()],
}
Path(sys.argv[3]).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
PY
```

通过时，`left_only` / `right_only` 都应为空。若不为空，先判断是否只是 instruction generator 非确定性导致的 path 选择差异；不能解释为非确定性时，视为语义失败。

## profile 比较命令

从 `run.log` 中抽取 `fork_profile`，关注 PMA/MMIO 相关函数：

```bash
python3 - "$RUN/pma-off-short/run.log" "$RUN/pma-on-short/run.log" "$RUN/compare/short-profile-summary.json" <<'PY'
import json
import sys
from collections import Counter
from pathlib import Path

def collect(path):
    profiles = []
    for line in Path(path).read_text(errors="replace").splitlines():
        marker = "fork_profile="
        if marker in line:
            profiles.append(json.loads(line.split(marker, 1)[1]))
    sites = Counter()
    for profile in profiles:
        for site in profile.get("top_sites", []):
            sites[site.get("innermost_function")] += site.get("hits", 0)
    return {
        "path_count": len(profiles),
        "total_fork_events": sum(p.get("fork_events", 0) for p in profiles),
        "max_fork_events": max([p.get("fork_events", 0) for p in profiles] or [0]),
        "hotspots": sites.most_common(20),
    }

out = {
    "pma_off": collect(sys.argv[1]),
    "pma_on": collect(sys.argv[2]),
}
Path(sys.argv[3]).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
PY
```

短跑主要看趋势：

- `pma-on-short` 不应出现 panic、`ExecError`、`SymbolicLength` 或明显的 PMA builtin fallback 风暴。
- `pma-on-short` 的 `max_fork_events` 不应高于 `pma-off-short`。
- `matching_pma_bits_range` / `pmaCheck` / `phys_access_check` 的热点应下降；若热点只是移动到 `within_mmio_readable` / `within_mmio_writable` / `clint_load` / `clint_store`，说明下一阶段定位有效。
- `path_count` 不能单独作为通过判据：更快的实现可能完成更多 path，导致 `total_fork_events` 变大。

## 通过 / 失败判据

语义通过：

- `pma-off-long` 和 `pma-on-long` 均 exit `0`，且都生成：
  - `output/rv64d_zSTORE.json`
  - `output/rv64d_zLOAD.json`
- `zSTORE-normalized.json`、`zLOAD-normalized.json` 中：
  - `path_shape_only_left == []`
  - `path_shape_only_right == []`
  - `event_only_left == []`
  - `event_only_right == []`
- observables digest 中 `left_only == []` 且 `right_only == []`。
- 对 exception path，type 与 address 必须一致；不能把 access fault 改成 alignment fault，不能丢失 exception address。
- 对 memory event path，event 数量、kind、region、bytes、address、address_model、data/value、exclusive/ifetch 标记必须一致。
- 对 store success，`memory-events[].value` 必须保持等价；不能引入未约束成功值或额外 failure path。

性能 / 路径通过：

- `pma-on-short` / `pma-on-long` 无 panic、`ExecError`、运行时 `SymbolicLength("subrange_internal")`。
- `pma-on` 的 `max_fork_events` 不高于 `pma-off`。
- PMA 热点下降，或明确转移到 MMIO/CLINT 谓词与设备函数。
- 若 `pma-on` 完成但 `pma-off` 超时，只能声明“性能趋势通过”，不能声明语义等价通过。

失败：

- 任一 long case 缺少对应 JSON，且没有可复现的更长 timeout baseline。
- `pma-on` 改变 `ret_val`、exception type/address、memory event、success value/constraint。
- `pma-on` 在固定 width/aligned 前提下大量 fallback 到 IR，导致和 off 没有可观察差异。
- 设置了 `ISLA_RISCV_ASSUME_PMP_OFF=1`、`ISLA_RISCV_VMEM_BUILTIN_MODE=plain-ram` 或 `legacy` 后还把结果当作 PMA/MMIO 语义结论。

## 避免覆盖仓库产物

- 不使用 `make run`：它会执行 `cargo fmt`，并覆盖 `isla/log` / `isla/log.1`。
- 不在 `isla/` 目录内运行验证命令；`isarch` 会把 `output/` 和 `solver.dump` 写到当前 cwd。
- 每组 case 使用唯一 `/tmp/isla-pma-mmio-<timestamp>`，并在其下分 `pma-on-*` / `pma-off-*` 子目录。
- 使用 `--manifest-path "$ISLA/Cargo.toml"`、绝对 `-A` 和绝对 `-C`，避免依赖当前工作目录。
- 每个 case 独立保存 `run.log` 和 `exit.code`；比较结果写入 `$RUN/compare/`。
