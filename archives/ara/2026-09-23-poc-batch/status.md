# Status: Ara 处理器批量 PoC 测试

## 当前状态（2026-09-16）

- [x] Clone Ara（`ara/ara`，commit 34bd3bc1）。重 toolchain 子模块用本机工具链替代；`apps/rvv-bench` 未初始化（可选）。
- [x] 环境调研（2 个 Explore agent 报告已消化，结论见 findings）。
- [x] bender 0.31.0 安装；pin 版 Verilator（06263ec7）编译安装；`config=2_lanes` verilate 成功，emu 在 `ara/ara/hardware/build/verilator/Vara_tb_verilator`。
- [x] PoC 生成器 `ara/pipeline.py`：19908/19908 条可生成；FPR 装载、断言崩溃分类、mepc=after_test（MRET 修复）均已支持。
- [x] 抽样批 1798 条（`ara/work-full/`）与全量批 19908 条（`ara/work-all/`）均已跑完，结果见 findings。
- [x] triage 全部完成：Sail vstart 根因 / vnclip RTL 崩溃根因与功能面扫描 / base 指令误判排查，结论均入 findings。
- [x] MRET 专项：mepc 修复后重跑 4 条 → 3 pass + 1 mismatch（`ara/work-mret/`）。注意全量批的 MRET 4 条用的是旧 ELF（fetch fault 假象），以 work-mret 为准。

## 值级 differential（进行中）

- 机制：PoC 尾部签名导出（x1-x31 + vl/vtype/vstart/vcsr + 32×vreg = 792B）→ MOD spike（0003 补丁版，交互从 stdin 读）`until pc sig_done` + 逐字 `mem` 提取 golden → check 模式 ELF 内嵌 golden 逐字比对，退出码 = 不匹配字索引（0=一致）。
- 关键设计：两种 backend **统一链接脚本 + 等长退出序列**（保证 ELF 布局逐字节同构，消除 x2/x31 等地址寄存器伪差异）；init 开头清零全部 GPR（消除 spike bootrom 写 a1/t0 的环境差异）。
- 冒烟：spike 自洽 5/5，emu 值级一致 5/5。
- 全量：spike 侧退休子集 10087 条，提取与 emu 检查进行中。

## Ara 疑点终版（全部有 RTL 行号 + 实验证据 + 原创性核查）

| # | 问题 | 定性 | 原创性（GitHub 全量 issue/PR/commit 比对） |
|---|---|---|---|
| 1 | vnclip/vnclipu ×{.wv,.wx,.wi}× SEW=64：dispatcher 三处缺 `vsew>EW32→illegal` 检查（vnsrl/vnsra 有：872/890、1141/1159、1380/1398），EW128 直发 simd_alu → unique case 断言 $stop。narrowing SEW=目的宽（源=2×SEW），SEW=64 本应 illegal | RTL bug·崩溃 | **✅ 原创**（无任何 SEW64/EW128 崩溃报告；#250 fuzz 作者注明未测 narrowing） |
| 2 | 合法域（SEW≤32）VNCLIP/VNCLIPU 只做 `shifted+rm` 截断、无饱和钳位；fixed_p_rounding 以目的 SEW 视图索引 2×宽源；.wi/.wx 不一致（src=0xFFFFFFFF SEW32 rne sh=0→0） | 功能 bug | ❌ 现象已有 **issue #163**（OPEN，2022-11，54 项失败清单）；仅 PR #230 修过打包。我们的**根因定位是新的**，可作 #163 补充 |
| 3 | spec 强制 vstart≠0→illegal 的指令类（reductions/vcpop/vfirst/vmsbf/vmsif/vmsof/viota/vcompress/vslide1up）被退休 | conformance | **✅ 原创**（全部 vstart 相关 commit 均为功能性支持，无 trap 语义报告） |
| 4 | vsetvli zimm[10:8] 保留位被忽略不置 vill | conformance | ❌ 已有 **PR #486**（OPEN 未合并，2026-08-22，修 `vtype_xlen` 上方 bit；机制同根同修法） |
| 5 | vmadc/vmsbc 的 vd↔源 overlap 检查把 spec 合法编码 trap 掉 | 过度限制 | ⚠️ 已有 **issue #120**（2021 开/2024 关）+ 修复 e99e7b6 在未合并 DRAFT PR #353；我们是 LMUL_1 精确重叠子 case + "e99e7b6 保留检查本身违反 spec"的新论证 |

待办：spike differential test 方案已汇报，等待用户审核后执行。

## 全量批 19908 条结果与定性（终版）

| 类别 | 数量 | 定性 |
|---|---|---|
| pass_success | 8984 | 期望成功且退休 |
| pass_illegal_confirmed | 5234 | 期望非法且确实 mcause=2 |
| fail_trap_illegal_expected_success — 扩展 | 1528 | Zvbb/Zvbc/Zvk* 未实现，illegal 正确 |
| fail_trap_illegal_expected_success — vmadc/vmsbc | 236 | **Ara 过度限制：vd↔vs2 overlap 检查（spec 无此限制）** |
| fail_trap_illegal_expected_success — viota/vcompress/vms* | 48 | vs1/vs2 LMUL 未对齐 reserved 编码，Ara trap 合法；isla/Sail 检查不完整 |
| mismatch_retired_expected_illegal — villa | 50 | **Ara 忽略 zimm[10:8] 保留位（conformance bug）** |
| mismatch_retired_expected_illegal — vstart≥vl | 2589 | 其中 ~49 条命中 spec 强制 vstart≠0→illegal 名单 = **Ara conformance bug**；其余为 VLEN 差异下 reserved |
| mismatch_retired_expected_illegal — 重叠 reserved | 942 | spec reserved 编码；Sail 判 illegal 合法、Ara 执行，低严重度分歧 |
| mismatch_retired_expected_illegal — 其它 | 209 | SEW8 narrowing dest SEW=4 reserved 36 + Sail decode 守卫/vl=0 组 173 |
| mismatch_retired_expected_memexc | 64 | vlm/vsm 落在 Ara 已映射内存（平台映射差异） |
| timeout | 4 | vlm/vsm 访未映射地址 |
| emu_assert_crash | 16 | **vnclip/vnclipu SEW=64 → dispatcher 漏 SEW 检查 + simd_alu 缺 EW64 分支 → $stop（真实 RTL bug）** |




## 关键决策

- **VLEN 语义折衷**：isla 输出为 128-bit vreg，Ara 最小 VLEN=2048（2 lanes）；采用高位零扩展装载（vl/vstart/vtype/vcsr 全部精确重建，body 语义不变，tail 段差异已记录）。
- **退出约定**：写 0xD0000000（CTRL eoc），进程退出码 = 写入值>>1；退出码表见 pipeline.py（0/4/12 为 pass，2/6/8/10/14 为 mismatch，32 为 init 阶段 trap）。
- **特权级**：V1 统一在 M-mode 执行（向量指令无特权语义差异，省去 PMP/mret；记录为保真度折衷）。
- 非法/内存异常期望类：trap handler 读 mcause 分类（mcause=2 → illegal）。

## isla solve 输出画像

- 目录 `isla/output/`，`rv64_z*.json` 共 19908 条 `gen[]`。
- 每条：`test-ins`、`test-ins-encdec`（32-bit 编码）、`isa-state`（初态）、`ret_val`（Retire_Success 10799 / Illegal_Instruction 9045 / Memory_Exception 64）。
- vreg 宽度统一 128-bit；带 vr 约 2200 条；带 GPR 初值 523；带 FPR 108（VFMERGE/VFMVSF）。
- 当前输出无向量 load/store 访存指令；VMTYPE 含 vlm.v/vsm.v（74 条，访存类，预期部分超时/access fault）。

## 热点文件

- `ara/pipeline.py`（harness 主文件）
- `ara/ara/`（Ara 仓库：hardware/Makefile, tb/, apps/common/crt0.S, config/）
- `isla/output/rv64_z*.json`（输入）
- `ara/work-full/`（正式批量样本与结果）


## 值级 differential 终版（四家族定性，证据见 findings.md）

| 家族 | 数量 | 方向 | 根因 | 定性 |
|---|---|---|---|---|
| vcsr | 162 | Ara 错 | `ara_dispatcher.sv:3396-3407/3434-3445` CSRRW/CSRRS 处理 vxrm/vxsat 用指令 rs1 字段位切片而非寄存器值，`csrw vxrm` 被丢 | **bug（高价值：向量 CSR 写通路）** |
| v0/mask | 129 | 主体 Ara 错 | masku 对 mask 目的寄存器未实现 tail-undisturbed（vta=0 时尾写全 1）；另 8 条为 spike 构建 csrw-vstart 死锁伪差异、6 条 FP 复位态伪差异 | **bug（中低危）+ 伪差异剔除** |
| vl 回写 | 8 | Ara 错 | `ara_dispatcher.sv:668-679`：vsetivli 不按 VLMAX 钳位；rs1=x0 特例表做反（rd=x0/≠x0 行为互换）；vsetvl 只查 rs2[7:0] 不置 vill | **bug ×3 形态** |
| vid.v | 14 | Ara 错 | `masku.sv:745-810` LMUL≥2 跨寄存器组元素按字节紧缩错位（128b 结果总线部分选择越界，VP=2） | **bug** |

收尾遗留：167 条超时（vslideup/vrgather/vnclip 长用例）在 20M 周期复跑中（nohup 脱离，`work-diff/rerun/`），完成后可并入值级矩阵；对四个家族定性无影响。
- [x] 留档：agents/ara_poc_batch/snapshot/（REPORT.md + inputs/results/poc/tmp-artifacts，90MB）；issue #493-#496 已提交（gh, msuadOf）。
