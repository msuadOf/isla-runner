# E 阶段 RV64 非访存隔离候选：定向证明快照

日期：2026-09-26。此目录只保存本工作包的新 runner、配置、输入和结果；正式 IR、主源码与严格配置的集成状态由议题主状态记录。

## 受测产物与方法

- 完整 V128 候选 IR：SHA-256 `c9e1bfe29e75452568d61fc3b3407e707eb1bd7e48193e212495ec21b885bc75`；构建/删除旧执行器专用分发的来历见议题 D 外部运行记录。隔离 runner 源文件 `runner/main.rs` SHA-256 `c09e84a2390fc9b9788667b8d453948a519f09d191c7e640a0842cf695092ac0`；受测二进制 SHA-256 `bd362465a970a623b561680ae45e15d7ea0e28b4836dc2c439c3e981fc228425`。
- 配置 `inputs/rv64-e.toml` SHA-256 `8247c8d467489111656f6953660670e96097a029fea458b660fe42579f86f987`：`sys_enable_fdext=true`、`cur_privilege=Machine`、MXL64、FS/VS Dirty，向量长度由 IR 固定为 128 位。测试编码由 GNU RISC-V assembler 2.46 生成或对其 vm 位编码核对，代表性汇编在 `inputs/*.s`。
- 每条以真实 32 位字进入 `zext_decode`，核预期 constructor、子操作 enum、寄存器字段与反编码；所有 SAT 完成译码路径的返回值必须完全一致。再以该译码结果进入 `zexecute`，核 `Retire_Success`、唯一完成执行路径。对独立写定的目标/状态寄存器（含完整 `fcsr`）先求 SAT，再对“任一寄存器不等预期”求 UNSAT。失败、Unknown、Poison、额外执行路径均令 runner 非零退出。各 JSON 逐例记录字、字段、写回、路径和毫秒耗时；每例译码为 2 条相同合法路径、执行为 1 条。
- 调用格式：`$E_STAGE/target/debug/isla-float-e-nonmem-runner "$D_STAGE/ir/rv64d_d.ir" "$E_STAGE/inputs/rv64-e.toml" <cases.json> <result.json>`。`E_STAGE`、`D_STAGE` 指向相应外部隔离目录。复制本快照在新目录编译时须将 `runner/main.rs` 用作 Cargo `src/main.rs`，并让 `isla-lib` path 依赖指向 D 候选的 Isla；不能用旧专用分发的主树二进制替代。

| 输入 → 证明结果 | 条数 | 输入 SHA-256 | 结果 SHA-256 | wall/RSS（stderr） |
| --- | ---: | --- | --- | --- |
| `inputs/smoke.json` → `results/smoke-proof.json` | 3 | `257ead7f7648c0d973eb8032f461cdb1962e132adbc453e47d026829fba38394` | `33e2feda31d3d3b3c1e22c05fa4ff4ea31812449dfd8b14ceab6158ca55bf2c0` | 4.89 s / 134628 KiB |
| `inputs/priority.json` → `results/priority.json` | 13 | `b0c2f935c9662c8536e5f5fcbd633969cdfc47f94cf4ec198ff4ed8f93a5c56b` | `0d7a4da03e3f9654f2591910c6f8461d891b5b61e9aedf324151b4a7052baeca` | 6.49 s / 133448 KiB |
| `inputs/vector-cases.json` → `results/vector-cases.json` | 4（含 smoke 的同一基础例） | `ba6e313fc75b94f72e4600baad200369e6c80650ad8a9da6f1d59428d05b23b7` | `8f81f93fb26802678e8d8046b1f8ff513b44d2fcb77865b9e1bde582af3214e0` | 5.04 s / 136448 KiB |
| `inputs/bf16-vector.json` → `results/bf16-vector.json` | 15 | `a18b3f67f0a5927e4a06d24902304fa358b9df8b9d1fbc62e210db1ca5a8d1d5` | `d89fdeb945fc22ab52f6c9e61475c8f46cf1f5900a15db98ff7f628a3709875f` | 6.79 s / 135760 KiB |

## Clause 与子操作边界

| Clause | 本次子操作与独立状态预期 | 对应样例 |
| --- | --- | --- |
| `F_BIN_RM_TYPE_S` | FADD.S，动态 RM=RNE，1.5+2.25=3.75；f32 boxing，旧 NX=1 保留 | `fadd_s` |
| `F_BIN_RM_TYPE_D` | FADD.D，同一精确和；旧 NX=1 保留 | `fadd_d` |
| `FVVTYPE` | VFADD.VV；两活动 f32 lane 求和，sNaN 在 `vstart` 前缀或被 mask 屏蔽时不置 NV，活动时 canonical NaN 且 NV 与旧 NX 累计；`vstart` 清零，向量写回后 mstatus.SD 置位 | `vfadd_vv`、`vfadd_skip_snan`、`vfadd_mask_snan`、`vfadd_active_snan` |
| `FCVT_BF16_S` | 精确 1.5、1+2^-8 的 RNE 中点、qNaN、sNaN；BF16 boxing、NX/NV 累计及 mstatus.SD | `fcvt_bf16_s_*` |
| `FCVT_S_BF16` | 精确 1.5、qNaN、sNaN；f32 boxing、规范 NaN 与 NV 累计 | `fcvt_s_bf16_*` |
| `VFNUNARY0` | **仅** `FNV_CVT_ROD_F_F`：f32→f16 的精确与不精确、f64→f32 的不精确，ROD 使最低有效位为 1 且 NX 累计；`vl=0`、mask=0、`vstart>=vl` 和跳过 sNaN 前缀均保留旧 flags | `vfncvt_rod_*` |
| `VFNCVTBF16_F_F_W` | f32→BF16 两 lane 精确转换与 sNaN，NV 累计 | `vfncvtbf16_*` |
| `VFWCVTBF16_F_F_V` | BF16→f32 两 lane 精确转换与 sNaN，NV 累计 | `vfwcvtbf16_*` |
| `VFWMACCBF16_VV` | 两 lane 有限乘加、活动 sNaN、屏蔽 sNaN lane；旧 NX 保留或 NV 累计 | `vfwmaccbf16_vv_*` |
| `VFWMACCBF16_VF` | 有限乘加；标量 sNaN 在 `vl=0`、全 mask=0、`vstart>=vl` 时原 flags 保留，活动时 NV 累计；旧 flags=0 与非零均测；sNaN 仅在跳过的向量前缀时不贡献 NV | `vfwmaccbf16_vf_*` |

共 35 条结果记录，基础 VFADD 一条在两个输入文件重复，**34 条不同样例、10 个 clause 各至少一个子操作**。这里的 10 是 clause 名称触达数，不表示这些 clause 的全部子操作、RM、SEW 或输入域通过，也不能作为 77 项全量 PASS。

## 失败历史与未覆盖

- 原隔离配置 `sys_enable_fdext=false` 令 FADD.S/FADD.D/VFADD.VV 均译成 `ILLEGAL`；修正为 true 后才重测。未初始化 `cur_privilege` 时 `zext_decode` 有 8 条路径，含 2 个 SAT `Poison`；设为 `Machine` 后稳定为 2 条相同合法路径。Poison 原因未做形式化归因，不能将旧配置结果视为通过。
- BF16 中点及向量写回使 mstatus.SD 置位，最初预期遗漏该位，SAT 差异捕获后加入完整状态预期。ROD 最初以目的 `v3` 与宽源 `v2` 组重叠，真实执行返回 `Illegal_Instruction`；改用非重叠 `v4`。f64→f32 ROD 的两个 64 位源元素位于同一 128 位 `vr2`，修正初版误放在 `vr3` 的输入后通过。这些失败输入不计 PASS。
- 当前 `calls=[]` 是因为 runner 未启用函数调用 trace；它不表示未执行普通 Sail 体。普通体及禁旧分发证据以 D 隔离候选记录为准。本次尚未覆盖 `VFNUNARY0` 的另 7 个 enum、FADD/其他子操作或 BF16 的所有 RM/SEW/NaN payload，以及全部 77 个 RV64 非访存 clause 的逐项验收。每组定向样例并非全符号输入等价证明。
- 负控制 `inputs/negative-control.json` 将 FADD.S 的正确写回末位故意改错，`results/negative-control.stderr` 记录差异查询得到 SAT、runner 退出 101；证明当前 binary 遇到数值差异不会静默记绿。负控制不计入通过样例。

## 同日追加：VFNUNARY0 七个 enum 与舍入边界

本节在上述 35 条快照之后追加，不改写上节初版“另 7 个 enum 未测”的历史判断。受测 IR、配置、runner binary 哈希均未变。七条编码由 `inputs/vfnunary0.s` 经 GNU assembler 2.46 生成；输入和结果完整保存，输出 JSON 逐例含 32 位字、enum 与寄存器字段、目标及完整 `fcsr`/`mstatus`/`vstart`、SAT→差异 UNSAT、路径数和毫秒耗时。

| 输入 → 结果 | 条数 | 输入 SHA-256 | 结果 SHA-256 | wall/RSS |
| --- | ---: | --- | --- | --- |
| `inputs/vfnunary0-seven.json` → `results/vfnunary0-seven.json` | 7 | `ff4c379a4d1b354160f84a3994ab14e81bc1d8899d1e779af4ba1d5dc3ea4b0d` | `a87bac7b595a185f83ecd090326cfe6d1bf75a06d7d3d842e9a1226ae7c5bd8a` | 5.12 s / 135692 KiB |
| `inputs/vfnunary0-rm.json` → `results/vfnunary0-rm.json` | 22 | `171964d6b8f6f3b00b96227e6e08b84e6134aa759a942faa827a310db11d96a4` | `efd47c081eac713b0c1415806aa54fc5560ebc50281a5914426693d612cc15e9` | 5.87 s / 133212 KiB |

七个新增 enum 在 SEW16、`vl=2`、非重叠源 `v2`/目的 `v4` 下分别执行：`FNV_CVT_XU_F`（f32→u16）、`FNV_CVT_X_F`（f32→i16）、`FNV_CVT_F_XU`（u32→f16）、`FNV_CVT_F_X`（i32→f16）、`FNV_CVT_F_F`（f32→f16）、`FNV_CVT_RTZ_XU_F`（f32→u16 显式 RTZ）、`FNV_CVT_RTZ_X_F`（f32→i16 显式 RTZ）。前五用精确整数或可精确表示的浮点值检查写回与旧 NX 保留；后两用 ±3.75/4.5 检查截零结果、NX 与旧 NV 累计。加上初版 ROD，`VFNUNARY0` 的 8 个 enum **各有至少一个合法实际编码与执行样例**，不表示各 enum 的全部 SEW 或边界均通过。

22 条舍入边界样例分别对 `FNV_CVT_F_F` 的正负 f32→f16 中点和 `FNV_CVT_X_F` 的正负 1.5，逐项设置动态 FRM=RNE/RTZ/RDN/RUP/RMM，核不同的 16 位写回、NX 与旧 NV 累计；另以 FRM=RMM 核 f32→f16 和 f64→f32 的负非精确输入仍按显式 ROD 置最低有效位，NX 置位。两组均为 2 条相同合法译码路径、1 条完成执行路径，所有状态差异查询 UNSAT。

截至此追加，独立工作包共 **64 条结果记录、63 个不同定向样例、10 个 clause 名称**；`VFNUNARY0` 的 enum 覆盖从 1/8 增至 8/8。仍需其他 SEW、整数越界/NaN/饱和、RM 与 ROD 更多边界以及整组 77 clause 的独立汇总，不能将该 enum 触达数解释为完整语义证明。

## 同日追加：BF16 五种动态舍入模式

受测产物哈希与上节相同。`inputs/bf16-rm.json`（SHA-256 `267329537e4141715cec6e72da01041607a2b9342844b8613ca0e35d4ab4d4e3`）→ `results/bf16-rm.json`（SHA-256 `cb8d0046b2ea50d2367846b93d1fd0b19b1ac9e53164d96309c546e52f5d048e`），20/20 定向样例通过；`results/bf16-rm.stderr` 记录 wall 5.90 s、RSS 136444 KiB。每例依旧 2 条一致合法译码路径、1 条完成执行路径，SAT→差异 UNSAT。

`FCVT_BF16_S` 与 `VFNCVTBF16_F_F_W` 各对正、负 f32→BF16 中点逐项设置 FRM=RNE/RTZ/RDN/RUP/RMM。正中点 `1+2^-8` 预期 BF16 `0x3f80/0x3f81`，负中点 `-1-2^-8` 预期 `0xbf80/0xbf81`，按各模式的近偶、截零、向下、向上、远离零规则独立计算；两类指令均核 boxing/向量目标、NX 与旧 NV 累计、FRM 保留和 mstatus.SD。该组补充的是这两个 BF16 子操作的五 RM 定向覆盖，不外推到其他 NaN payload、溢出或全部输入。

截至此追加，本工作包累计 84 条结果记录、83 个不同定向样例，仍触达 10 个 clause 名称；先前统计是各阶段当时的快照。

## 同日追加：VFNUNARY0 全部合法 SEW 格

Astra 按当前 Sail `valid_narrowing_fp_conversion` 核定 `VFNUNARY0` 的必测格为 8 个 enum×SEW16/32，加 4 个整数目的 enum×SEW8，共 20 格。上两节已有 SEW16 的 8 格与 ROD 的 SEW32 1 格，本节新增 SEW32 其余 7 格、SEW8 的 `FNV_CVT_XU_F` / `FNV_CVT_X_F` / `FNV_CVT_RTZ_XU_F` / `FNV_CVT_RTZ_X_F` 4 格。SEW8 源为 f16、目的为 8 位整数；显式 RTZ 用 3.75/−3.75、4.5 检查非精确截零，旧 NV 与新 NX 累计。SEW32 源为 64 位浮点/整数、目的为 32 位；各自独立设置两个 64 位 lane 于 128 位 `v2`。所有格均核真实译码字段、写回、完整 `fcsr`、`vstart` 与 mstatus.SD，并先 SAT 再差异 UNSAT。

| 输入 → 结果 | 条数 | 输入 SHA-256 | 结果 SHA-256 | wall/RSS |
| --- | ---: | --- | --- | --- |
| `inputs/vfnunary0-sew32.json` → `results/vfnunary0-sew32.json` | 7 | `2157958b1ee7bfa743fc4f4e25087f351a0728796558497da29720b90e3d6a4a` | `5f5ebdf8ae6e496ed4355dbe6865722ad3b9b9fff3bf8022a732e597f9241238` | 5.26 s / 137332 KiB |
| `inputs/vfnunary0-sew8.json` → `results/vfnunary0-sew8.json` | 4 | `d931155046e06f450c96babe6cc1cf6b72ba5f4ab8f9185038fe125e9d153100` | `a7c447a160742280e805175603c5b90c2eb9a6fc32a4a1caa5617b70496a9dea` | 5.01 s / 136368 KiB |

新增 11/11 条通过后，该 clause 的 **20/20 个当前合法 enum×SEW 格各有一条具体执行 proof**。该计数仍不等于每格的全部 RM、NaN、越界与 mask 状态通过。本工作包累计 95 条记录、94 个不同定向样例、10 个 clause 名称。

## 同日追加：舍入奇中点、整数越界、BF16 乘加与非法 FRM

仍使用同一成功路径 runner/IR/配置。下表的前四行每项都完成真实编码→`zext_decode`→预期 enum/字段→反编码→`Retire_Success`，先 SAT 再对完整目标、`fcsr`、`mstatus`、`vstart` 的任意差异求 UNSAT。每例 2 条一致合法译码路径、1 条完成执行路径。

| 输入 → 结果 | 条数 | 输入 SHA-256 | 结果 SHA-256 | wall/RSS |
| --- | ---: | --- | --- | --- |
| `inputs/vfnunary0-rm-extra.json` → `results/vfnunary0-rm-extra.json` | 15 | `4f6df257b5a5985d197ed372a0d36517b1290fad475d307ea6ceb31a2c383fd8` | `c414d6acba63d7966140b38a1ce19cf4d66e3506e9fd39768ab81c164a6ad7c0` | 5.48 s / 134720 KiB |
| `inputs/vfnunary0-overflow.json` → `results/vfnunary0-overflow.json` | 6 | `863b705b8e39f791acaa07921fcf264d1496652322edb95181b1c68ddd7353ad` | `0575fcb781f06b7cdcd7010f690d922a60a7e6f88964e06cd1fa1a7df90ee8ab` | 5.03 s / 136412 KiB |
| `inputs/bf16-macc-rm.json` → `results/bf16-macc-rm.json` | 10 | `66b872782c365a73963332a2432ffb111895984e4eb5a7b2530407153fd94a43` | `d471f4d6916debee02d23501d22337b6ea6a77b9dce1ca6c609dbb2458ad56e1` | 5.52 s / 133760 KiB |
| `inputs/bf16-vf-extra.json` → `results/bf16-vf-extra.json` | 3 | `da4f338717f65d7ffc089e9cf3a1c895d6110b002c0906ba36e6d7f4bc9092c7` | `e32554b41fcbc171f081f97d2f2ff734ececec3437fcf4db6399c55a530cf866` | 4.95 s / 134868 KiB |

- `vfnunary0-rm-extra` 使普通 f32→f16 在正的**奇数最低位中点**逐项跑五 RM；RNE 与 RTZ 得到不同编码，避免只用偶中点的盲点。普通 f64→f32 的正、负偶中点也各跑五 RM，核动态 FRM 路由、NX 与旧 NV 累计。
- `vfnunary0-overflow` 对目标 8/16/32 位各放一条正向有符号与无符号范围外的**非整数**输入。期望分别饱和到目标最大有符号/无符号值，且只置 NV、不因原输入小数部分另置 NX；旧 flags=0，使优先级可观察。浮点源依次为 f16/f32/f64，对应 `vfncvt.x.f.w` 和 `vfncvt.xu.f.w`。
- `bf16-macc-rm` 对 `VFWMACCBF16_VF` 与 `_VV` 各用 BF16 乘积 `1×2^-24` 加 f32 累加器 `1.0`，精确中点按 RNE/RTZ/RDN/RUP/RMM 选择目标 f32；检查 NX 与旧 NV 累计。`bf16-vf-extra` 验证**未正确 NaN boxing** 的 BF16 scalar 被当作 qNaN，目标为规范 f32 NaN 且不产生 NV；另补 scalar sNaN 在 mask 全关、`vstart>=vl` 时旧 flags=0 的保留。合法 boxed sNaN 在活动 lane 中置 NV、旧 flags=0/非零的样例见上节。

为验证非法 FRM 没有被 ROD helper 内部的 RM=6 意外放行，另从固定成功 runner 源独立编译 `illegal_runner/main.rs`：仅增加输入 `expected_result`，要求明确的 `Illegal_Instruction` 与目标/flags 状态保持。此**独立非法路径 runner** 二进制 SHA-256 `e265b79839c1e3b6721342b435d1c974574c7424d47b2edda92246d9f41802b3`，源 SHA-256 `42ed0bec5ce9f3e6718a9dfa804dd47d521c2d55ba7f55834a6724285508dda8`，不改成功 runner 的接受条件。`inputs/illegal-frm.json`（SHA-256 `fd5a5de400209b3028396283dc40c3b694f2351f4c1779c35c10f9147bc09a63`）→ `results/illegal-frm.json`（SHA-256 `b1abb6fd3e7c45969531d8205225b00312e84786f04c3dca7503f8b377b0dc7b`）：FRM=5/6/7 各对 `VFNUNARY0` ROD、`FCVT_BF16_S`、`VFWMACCBF16_VF` 测一项，共 **9/9 非法路径正确拒绝**，目标和完整 `fcsr`/mstatus 不变；wall 5.21 s、RSS 135432 KiB。非法路径不计入上面的成功样例总数。

至此独占工作包为 **129 条成功结果记录、128 个不同定向样例、10 个 clause 名称，另 9 条非法 FRM 样例**。BF16 四个向量 clause 的合法 SEW 由当前 Sail 映射限制为 16，本工作包已在 SEW16 测各自有限值及关键 NaN/活动状态；此处不宣称非法 SEW 译码或所有输入域已验证。其他 agent 的标量/向量 clause 证明须另行汇总，不并入本计数。
