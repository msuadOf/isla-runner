"""只读汇总并行归因实验；不以运行中记录作最终结论。"""
from pathlib import Path
import importlib.util
import json
import time

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("path_accounting", HERE / "path-accounting/analyze.py")
accounting = importlib.util.module_from_spec(spec)
spec.loader.exec_module(accounting)

while True:
    paths = {name: accounting.analyze(name) for name in ("flags-arithmetic", "sat")}
    results = []
    for path in (HERE / "tactic-investigation/full").rglob("result.json"):
        try:
            result = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        results.append({"workload": result.get("workload"), "tactic": result.get("tactic"),
                        "exit_code": result.get("exit_code"), "gen": result.get("gen")})
    snapshot = {"updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "note": "运行中快照；各实验最终记录及报告优先", "paths": paths, "tactics": results}
    (HERE / "confirmation-live.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n")
    descriptions = []
    for name, counts in paths.items():
        descriptions.append(f"{name}: 主分叉{counts['main_forks']}，执行返回{counts['main_run_returned']}，"
                            f"收集完成{counts['main_collector_done']}，在途{counts['outstanding_queue_plus_active']}")
    print(snapshot["updated_utc"], f"策略整轮已退出{len(results)}/6；", "；".join(descriptions), flush=True)
    if len(results) == 6 and (HERE / "path-accounting/final-finished.json").exists():
        break
    time.sleep(60)
