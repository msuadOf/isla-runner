# Ara 批量 PoC + spike Differential 测试留档（2026-09-16/17）

## 环境
- DUT: Ara commit `34bd3bc1`(=origin/main)；emu 两套：`config=2_lanes` VLEN=2048（`hardware/build/verilator`，合法配置，outcome 全量批与 bug 复验用）与 VLEN=128（`hardware/build-v128`，isla 对齐配置，differential 用——注：违反 config/*.mk "VLEN>128" 约束，仅用于交叉验证，bug 提交以 2048 复现为准）
- Golden: Ara pin spike（204b88de）+ 0003 补丁 MOD spike（golden 签名提取）
- 输入: isla `make solve` 输出 19908 条（`isla/output/rv64_z*.json`，VLEN=128 IR，未重跑 solve）
- 生成器: `poc/pipeline.py`（prepare/build/run/diff/golden；mode outcome/dump/check；backend emu/spike）

## 结果一：outcome 级三方矩阵（VLEN=128，19908 条）
| 分类 | 数量 |
|---|---|
| agree_retired | 9837 |
| agree_illegal | 6796 |
| allowance_vstart_arith_spike_stricter | 1787 |
| spike_illegal_ara_retired_other | 1081 |
| CANDIDATE_ara_over_trap | 250 |
| BUG_vill_reserved_bit_ara_retires | 51 |
| BUG_vstart_mandatory_list_ara_retires | 49 |
| outcome_mismatch(retired|other_trap) | 37 |
| BUG_ara_assert_crash | 16 |
| infra_mismatch(timeout|pass_illegal_confirmed) | 4 |

## 结果二：值级签名对拍（spike golden vs emu 自检，spike 退休子集 10087 条）
| 分类 | 数量 |
|---|---|
| 值一致 (pass_success) | 9286 |
| 值不一致（按首异字定位） | 378 |
| emu 判 illegal（已知过度拦截类） | 250 |
| 超时（B10 挂起族） | 167 |

值不一致按签名区域：{'vcsr(vxrm/vxsat)': 162, 'mask寄存器v0': 130, 'v1': 14, 'vl': 8, 'v28': 5, 'v10': 5}

## Bug 报告与原创性（详见 ../bugs.md，含现象与复现）
| # | 现象 | 定性 | 原创性 | 上游 |
|---|---|---|---|---|
| A1 | vnclip/vnclipu SEW=64 仿真器断言崩溃（应 illegal） | RTL bug | ✅原创 | **issue #493 已提交** |
| A2 | vnclip/vnclipu SEW≤32 数值错（无饱和/舍入位错位/.wi-.wx 不一致） | 功能 bug | ❌现象已有 | #163（根因定位新增，未提交） |
| A3 | vstart≠0 强制 illegal 名单（reductions/vcpop/vfirst/vmsbf/vmsif/vmsof/viota/vcompress）未执行 | conformance | ✅原创 | **issue #494 已提交** |
| A4 | vsetvli zimm[10:8] 保留位不置 vill | conformance | ❌已有 | PR #486（OPEN） |
| A5 | vmadc/vmsbc vd↔vs2 overlap 合法编码被判 illegal | 过度限制 | ⚠️边界 | #120 + PR #353 残留 |
| B6 | vxrm/vxsat/vcsr 写入丢失（读回恒 0） | RTL bug（2048 复验 ✓） | ❌已有 | PR #487/#488/#489（OPEN） |
| B7 | mask 目的 tail 写 1 | 非 bug（spec：恒 tail-agnostic） | — | — |
| B8a | vsetivli 不按 VLMAX 钳位 | 真实缺陷但官方配置不可触发 | ⚠️归补充 | #240 |
| B8b | vsetvli rs1=x0 特例互换 | 非 bug（v128 伪差异，2048 复验 ✓ 符合 spec） | — | — |
| B8c | vsetvl rs2 保留位不置 vill | conformance（2048 复验 ✓） | ❌已有 | PR #486（含 rs2 调用点） |
| B9 | vid.v LMUL≥2 跨组错位（2048 复验表象：第二寄存器整组未写） | RTL bug | ⚠️归补充 | #255（#376 修复后残留） |
| B10 | 读 vcompress.vm 目的寄存器的向量 store 永久挂起 | RTL bug（2048 复验 ✓） | ✅原创 | **issue #495 已提交** |
| B11 | vfmv.v.f SEW<64：e8 illegal、e16/e32 body 恒写 0 | RTL bug（2048 复验 ✓，新发现） | ✅原创 | **issue #496 已提交** |

## 留档内容
- `inputs/`：抽样输入 JSON（work-diff 全量 input/retired 子集）+ outcome 矩阵 matrix.json + golden 清单
- `results/`：四份 results.json（2048 outcome 全量 / 128 双 backend outcome / 128 值级 check）
- `poc/`：pipeline.py 与两份链接脚本；`bug-cases/` 为每个 bug 的样例 case（.S + ELF + golden + emu.log）；`legal2048/` 为合法配置复验脚本、verdict 与四个已提交 issue 正文
- `tmp-artifacts/`：triage 期间的一次性探针（vnclip shift 扫描、spike CSR 探针、vstart 探针等）
- 完整现象清单：../bugs.md；工作记录：../status.md 与仓库 agents/findings.md

## 复现路径
`python3 poc/pipeline.py prepare/build/run/diff/golden ...`（参数见文件头注释与 ../bugs.md 各条目）
