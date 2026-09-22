# Ara 合法配置（2 lanes / VLEN=2048）bug 家族复验结论

- 基线：Ara commit `34bd3bc1`（= origin/main），emu `ara/ara/hardware/build/verilator/Vara_tb_verilator`（`config=2_lanes`，VLEN=2048，NrLanes=2，ELEN=64）。
- 运行命令：`<emu> -c 2000000 -l ram,<elf>,elf`（**-c 必须在 -l 前**，否则 GNU permute 会把 -c 当作 -l 的参数）。退出码 = 写入 0xD0000000 的值；**emu 超时上限退出码也是 0**，必须看日志中 `Simulation timeout of ... cycles reached` 与 `tohost = N` 行区分。
- 汇编：`riscv64-unknown-elf-gcc (14.2.0) -march=rv64gcv -mabi=lp64d -nostdlib -static -T ara/work-all/elf/ara.ld`。
- 所有用例 `.S` / `.elf` / `.log` 均在本目录。生成脚本 gen.sh / gen2.sh / gen3.sh。

## 逐项结论

### 1. B6（vxrm/vxsat CSR 写丢失）——✅ 复现成立
- `b6_vxrm`：`csrw vxrm,2` → `csrr` 读回 = **0**（应 2）。
- `b6_vxsat`：`csrw vxsat,1` → 读回 = **0**（应 1）。
- 与 VLEN=128 值级对拍一致；上游已有 PR #487/#488/#489 同根未合并，无需新 issue。

### 2. B8a（vsetivli uimm5 不按 VLMAX 钳位）——⚠️ 合法配置下架构性不可达（潜在缺陷，非可触发 bug）
- 探针 `b8a_vsetivli`：`vsetivli x0,31,e64,mf8` → vl=0。**这是正确行为**：spec（/tmp/vspec.adoc L323-327）规定 SEW 超出 `[SEW_MIN, LMUL×ELEN]` 必须 vill（mf8 时 SEW 只能=8；SEW=64 → vill → vl=0）。我最初"e64/mf8 VLMAX=4"的设想的 vtype 本身非法。
- VLEN=2048 下合法 vtype 的最小 VLMAX = 32（e8/mf8 / e16/mf4 / e32/mf2 / e64/m1），而 uimm5 最大 31 → **avl>VLMAX 在 vsetivli 路径永远无法构成**。
- 静态代码仍确认缺陷存在：`ara_dispatcher.sv:670` `csr_vl_d = vlen_t'(insn.vsetivli_type.uimm5);` 无钳位（对照 680-681 行 vsetvli rs1 路径有钳位）。已发布 config（2/4/8/16 lanes，VLEN≥2048）均不可触发；仅当 VLEN≤1024（min VLMAX≤16<31）才可达。VLEN=128 上的历史证据（build-v128）属于违反 config 约束的构建。
- **结论：不值得单独提 issue（可作 PR #486/issue #240 家族的补充评论）。**

### 3. B8b（vsetvli rs1=x0 特例疑互换）——❌ 不成立（非 bug）
- `b8b_keep`（`vsetvli x0,x0,e32,m1`，前值 vl=9）→ 读回 **9** = spec（rs1=x0∧rd=x0 → 保持）。
- `b8b_vlmax`（`vsetvli x31,x0,e32,m1`，前值 9）→ 读回 **64** = spec（rs1=x0∧rd≠x0 → VLMAX；e32/m1@2048 → 64）。
- RTL（`ara_dispatcher.sv:672-677`）与 spec 一致。此前 VLEN=128 的"互换"现象是 spike 侧 rs1=x0 按 avl=0 处理的伪差异（findings 已有记录）。**bugs.md B8b 应改判非 bug。**

### 4. B9（vid.v LMUL≥2 第二寄存器组错）——✅ 复现成立，但 VLEN=2048 下表象不同
- e32/m2/vl=128：v4（组内第 1 寄存器）正确（sanity 探针 byte4=1 ✓）；**v5（第 2 寄存器）完全未被写**：byte0/byte4/byte3/byte64/word4 全 0（应分别为 0x40/0x41/0x00/0x50、word@4=0x41）。
- e64/m2/vl=64 同样：v5 byte0=0（应 0x20）。
- VLEN=128 时表象是"字节紧缩错值"（case-02136 v1.lo=0x07060504），VLEN=2048 表象是"组内第 2 及以后的寄存器保持原值（丢失写入）"。同族（masku.sv VIOTA/VID 通路），上游已有 issue #255（OPEN）——维持"补充证据"定位。

### 5. B10（vs1r.v 挂起）——✅ 复现成立，且比原描述更小、与 vstart 无关
- 用户指定的最小探针（`csrw vstart,4` + `vadd.vv v1,v2,v3` + 32×`vs1r.v`）**不触发**：1249 周期正常退出（`b10_hang`，对照 `b10_ctl` 一致）。
- 但**原始 167 例超时 ELF 中抽 5 个（vcompress/vnclip/vnclipu/vmadc/vslideup 各 1）直接在合法 2048 emu 上复跑，5/5 全部打到 2M 周期超时**（`orig_case-*.log`）——非 v128 构建伪影。
- 最小复现（干净骨架，无向量装载、无检查循环）：
  - `b10e`：`vcompress.vm v31,v0,v0`（e16/m1，vl=1，**vstart=0**）+ 32×`vs1r.v` → **挂起**。
  - `b10g`：同一 vcompress + **仅 1 条** `vs1r.v v31,(t0)` → **挂起**。
  - `b10f`：仅 vcompress、无 store → 正常退休退出（tohost=0）→ 挂起需要"这类指令之后跟 vs1r"的组合。
  - `b10h`：`vslideup.vi v8,v0,0,v0.t`（e8/m8，vl=0x4b，vstart=0，case-02425 克隆）+ 32×vs1r → **挂起**。
- 触发族（源自 167 例分布）：vslideup 40、vnclip/vnclipu 41、vrgather 52、vmsbc/vmadc 17、vcompress 2、vslidedown 6、vrgatherei16 5——全部 vstart=0 或截断为 0；与 vstart 无关、与 vadd 无关。
- **寄存器级窄化**（`vcompress.vm v31,v0,v0` @ e16/m1/vl=1 后单条访存）：
  - `vs1r.v v0` → 正常退出；`vs1r.v v30` → 正常退出；
  - `vs1r.v v31`（=vcompress 的 vd）→ 挂起；`vse16.v v31` → 同样挂起（**非 vs1r 特有**，任何读该 vd 的向量 store 都触发）；vd=v5 + `vs1r v5` 同样挂起（不限 v31，b10l）；
  - 结论：挂起条件 = "vcompress 类指令退休后，读其目的寄存器的向量访存"。vid.v（同为 MASKU 指令）+ vs1r 不挂（b9 已证）。
- **结论：B10 是真实 bug 且值得提 issue（原创性结论不变），issue 描述应改为"vcompress.vm / masked vslideup 等之后读其 vd 的向量 store 永不完成"。**

### 6. B7 子项（vfmv.v.f tail 是否写 1）——❌ 原疑点不成立；但发现新 bug：vfmv.v.f 在 SEW<64 时整体损坏
- e64：body=0xA5 ✓、tail（vta=0/tu，预填 0xFF）=0xFF 保留 ✓ → **tail 语义正确，不写 1**。
- e32/e16：不 trap，但 **body 被写成 0**（预填 0xFF、f0=0xA5…A5、甚至 v0 预填 0x0F / 换 f5 都不影响——既非拷 vd、非拷 v0、非读 GPR rs1，就是写 0）；tail 仍正确保留。
- e8：直接 illegal trap（mepc 定位到 vfmv.v.f 本身，`b7_diag` offset 0x4c）。
- 机理：`ara_dispatcher.sv` OPMVV funct6=010111 分支（1585 行起）只解码 VCOMPRESS，全仓无 VFMVVF 操作（仅 VFMVFS/VFMVSF=vfmv.f.s/vfmv.s.f）；FUNCTIONALITIES.md L60 却声明支持 `vfmv`。
- 原 6 例"FP 复位态差异"可重新归因为此 bug（SEW≤32 时 Ara 把 body 写 0）。
- **结论：B7 子项关闭（非 bug）；新发现（暂记 B11：vfmv.v.f SEW 8/16/32 损坏）可另行提 issue 或并入后续报告。**

### 附带：A1 / A3 在合法配置的复验
- `a1_vnclip`（vnclip.wi SEW=64）：emu 断言崩溃 `simd_alu.sv:444: unique case, but none matched for '3'h3'` → $stop（与 VLEN=128 批量结论一致）。
- `a3_vcompress`（vcompress.vm + vstart=1）：正常退休退出 0（spec 强制 illegal）→ A3 成立。

## Issue 模板情况
上游 `pulp-platform/ara` 的 `.github/` 只有 `pull_request_template.md` 与 workflows，**没有 ISSUE_TEMPLATE**（本地 clone 与 gh api 均确认）。故 issue 草稿采用通用 bug 报告结构（Description / Minimal reproducer / Build & run / Expected / Actual / Suggested fix / Environment），风格对齐 PR 模板的简洁条目式。

## 产物清单
- 用例：`b6_*`、`b8a_*`、`b8b_*`、`b9_*`（含 p1/p2/e64/e64b）、`b7_*`（diag/diagA/diagB/v16/v32/v64/v8/f5probe/v0probe）、`b10_*`（ctl/hang(=vadd 探针)/e/f/g/h/i/j）、`orig_case-*`、`a1_*`、`a3_*`。
- Issue 草稿：`issue-a1-vnclip-sew64-crash.md`、`issue-a3-vstart-nonzero-mandatory-illegal.md`、`issue-b10-vs1r-hang.md`。
