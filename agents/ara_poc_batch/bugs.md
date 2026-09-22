# Ara 处理器 bug 现象清单（只记现象，不含原因分析）

基线：Ara commit `34bd3bc1`（= origin/main），emu `config=2_lanes vlen=128`（`hardware/build-v128/verilator/Vara_tb_verilator`）。
对照：golden = Ara pin 版 spike（`install/riscv-isa-sim/bin/spike`，`--isa=rv64gcv_zfh_zvfh_zvl128b`）。
复现产物根目录：`ara/work-diff/`（elf-check-emu / elf-x(golden) / rerun）；原始样本 `ara/work-all/`、`ara/work-full/`。
运行方式：emu `-c 20000000 -l ram,<elf>,elf`（-c 在前）；spike `--isa=... <elf>`。单指令 PoC 生成：`ara/pipeline.py`。

## A. outcome 级现象

### A1. vnclip/vnclipu SEW=64 使仿真器崩溃 【原创 ✓】
- 现象：vtype SEW=64（如 0x18）下执行 `vnclip/vnclipu`（.wi/.wv/.wx 任意变体，vl≥1），Verilator emu 直接中止：`%Error: simd_alu.sv:444/461: unique case, but none matched for '3'h3'`（Verilog $stop）。spike 判 illegal-instruction trap。
- 规模：16/19908（批量 `emu_assert_crash` 类）。
- 复现：`work-diff/elf-check-emu/results.json` 搜 `emu_assert_crash`；或手写 `vsetvli zero,t1,0x18` + `vnclip.wi v20,v30,0xe`。

### A2. vnclip/vnclipu 合法域（SEW≤32）数值错误 【现象已有 issue #163（OPEN，2022-11）；根因定位为本项目新增】
- 现象：src elem=0x00000000FFFFFFFF、SEW=32、LMUL=1、vl=1、vxrm=rne 时：shift=0 → 结果 0x0（spike 0xFFFFFFFF）；shift=16 → 0x1（应 0x10000）；shift=31 → `.wi` 得 1、`.wx` 得 2（同移位两变体不一致）；vxsat 不置位。
- 复现：`/tmp/ara-vnclip-test/`（f/g 系列 shift 扫描）。

### A3. spec 强制 vstart≠0→illegal 的指令未 trap 【原创 ✓】
- 现象：对 reductions（vredsum/vredmin…）、vcpop.m、vfirst.m、vmsbf/vmsif/vmsof.m、viota.m、vcompress.vm，在 vstart≠0 初态下执行，Ara 正常退休并写结果；spike 抛 illegal-instruction（RVV 1.0 强制要求）。
- 规模：49 条（`work-diff/matrix.json` 搜 `BUG_vstart_mandatory_list_ara_retires`）。

### A4. vsetvli zimm 保留位不置 vill 【已有 PR #486（OPEN 未合并）同根】
- 现象：`vsetvli` zimm 含 bit[10:8]（如 0x400）时，Ara 将其当作合法 e8/m1 接受（后续向量指令正常退休）；spike 置 vill → illegal。
- 规模：50 条（villa 类）。

### A5. vmadc/vmsbc 合法 overlap 编码被判 illegal 【已有 issue #120（关闭）相关；本 case 为其未覆盖子集】
- 现象：`vmadc/vmsbc`（全 .vi/.vx/.vv/.vim/.vxm/.vvm/.vim 变体）在 vd 与 vs2 同号寄存器（如 `vmadc.vi v0, v0, 0`）时 Ara 抛 illegal；spike 正常退休（spec 对 vmadc/vmsbc 无 overlap 限制）。
- 规模：236 条 outcome 级 + 值级 vmadc 家族散布（`CANDIDATE_ara_over_trap` 中 vmadc/vmsbc 计数）。

## B. 值级现象（spike golden 签名 vs emu，10087 条中 92.1% 一致）

### B6. 向量 CSR（vxrm/vxsat）写入丢失 【❌ 已有：PR #487/#488/#489（OPEN 未合并，flaviens 批量修复）精确同根；main 仍复现】
- 现象：`csrw vxrm, 2`（或写 vxsat/vcsr）之后读回恒为 0（探针：csrw → csrr → 退出码=值，emu=0，spike=写入值）。表现面：所有依赖 vxrm 的定点饱和/舍入指令（vssrl/vssra/vaadd/vaaddu/vasub/vasubu/vsmul/vnclip）的 vcsr 终值与 golden 不一致；vnclip 出结果但 vxsat 不置位。
- 规模：162 条（值级 `unexpected_exit_34`，word33=vcsr）。

### B7. mask 目的寄存器 tail 位写 1 【⚠️ 按 spec 非 bug：mask 目的 tail 恒为 tail-agnostic、与 vta 无关（v-spec :401/:1044）；写全 1 合法】
- 现象：vta=0（tu）的比较类指令（vmseq/vmsltu/vmsne/vmsleu/vmadc 系）写 mask 目的寄存器时，tail 位（vl..VLMAX-1）为全 1；spike/golden 保留初值。body 位（<vl）双方一致。属 agnostic 位预期噪声，不构成 bug。
- 待复核子项：`vfmv.v.f`（非 mask 目的指令）tail 应遵循 vta，若 vta=0 时仍写 1 则为真 bug 且无报告（原创候选，~6 条，此前被并入本类，需单独验证）。【2026-09-17 合法配置复验：tail 疑点不成立（e64 body=0xA5 ✓、tail 0xFF 保留 ✓）；但发现新 bug B11——vfmv.v.f 在 SEW=8 直接 illegal、SEW=16/32 退休但 body 恒写 0（fp 操作数被忽略，预填 0xFF/v0=0x0F/换 f5 均不变），仅 SEW=64 正确；dispatcher 无 VFMVVF 解码（OPMVV 010111 只解 VCOMPRESS），与 FUNCTIONALITIES.md L60 "vfmv" 声明矛盾。原 6 例"FP 复位态差异"应重新归因于此。/tmp/legal2048/v16|v32|v64|v8_body 等】
- 例：`work-diff/elf-check-emu/case-03952`（vmseq，vl=2）。

### B8. vsetvl* 的 vl 回写差异
- B8a `vsetivli` avl(uimm5) > VLMAX 不钳位（avl=7、e32/m1、VLEN=128 → Ara vl=7，golden=4）【⚠️ 已有 issue #240（OPEN，2023）报"vl 可超 VLMAX"现象族（不同触发路径：rs1=x0 保持链）；本项为 uimm5 直通路径的新实例，按规则归补充】。case-03179/03182/03186/03187。【2026-09-17 合法配置复验：VLEN=2048 下合法 vtype 最小 VLMAX=32 > uimm5 上限 31，且"SEW>LMUL×ELEN → vill"（v-spec L323-327）排除了用 mf8 缩 VLMAX 的构造——该不钳位路径在全部已发布 config（VLEN≥2048）架构性不可达，属潜在缺陷（dispatcher:670 仍无钳位）；VLEN=128 证据依赖违规构建。仅 VLEN≤1024（min VLMAX≤16）才可触发】
- B8b `vsetvli` rs1=x0 特例疑似互换【❌ 2026-09-17 合法配置复验判非 bug：探针 `vsetvli x0,x0,e32,m1`（前值 9）→ 9 ✓、`vsetvli x31,x0` → 64=VLMAX ✓，与 spec 及 dispatcher:672-677 静态代码一致；VLEN=128 时"互换"现象为 spike 侧 rs1=x0 按 avl=0 处理的伪差异】
- B8c `vsetvl` rs2 保留位不置 vill【❌ 已有：PR #486（OPEN 未合并）完整覆盖——除改 vtype_xlen 外同时把调用点 `rs2[7:0]` 改为传完整 rs2；main 仍复现】。

### B9. vid.v LMUL≥2 跨寄存器组元素错位 【⚠️ 已有 issue #255（OPEN，2023-07，36 元素 vid 测试，配置类吻合 LMUL≥2）；本项证明 PR #376（2024-12 MASKU 重构）后该现象在 main 仍存在，属修复残留证据/补充 case】
- 现象：LMUL≥2 时 `vid.v` 写寄存器组第 2 个及以后的寄存器，元素索引按字节紧缩错位：SEW=64 例（case-02135）v1 低字=0x302（golden=2）；SEW=32 例（case-02136）v1 低字=0x07060504。组内第一个寄存器正确。
- 规模：14 条（`unexpected_exit_36`，word35=v1）。注：issue #298 是 LMUL=1 的另一机制（非同族）。

### B10. 检查序列中的 vs1r.v 长时间不终止 【✅ 原创：无任何 vs1r/whole-register store 挂起报告；挂起类 issue（#250/#450/#455/#437/#477/#480/#474/#465/#365）逐一排除；PR #485 为同族 load 侧功能修复，不同现象】
- 现象：vstart≠0 初态的 vslideup/vrgather/vnclip 等用例，测试指令本身可正常退休（outcome 模式 <2M 周期）；但退休后继续执行 32×`vs1r.v`（whole-register store）签名导出序列时，仿真在 20M 周期（约 31 分钟墙钟，10.6kHz）内不终止、无退出写入。
- 规模：167 条（`work-diff/elf-check-emu/results.json` 的 timeout 类；复跑日志 `work-diff/rerun/`）。
- 【2026-09-17 合法配置复验：真实 bug 成立且与 vstart 无关——原始 5 个超时 ELF（vcompress/vnclip/vnclipu/vmadc/vslideup 各 1，vstart 全为 0 或截断为 0）在合法 2048 emu 上 5/5 复跑仍挂到 2M 超时；最小复现 `vcompress.vm v31,v0,v0`(e16/m1,vl=1,vstart=0) + **单条** `vs1r.v v31` 即挂起；对照：无 store 正常退出、`vs1r v0/v30`（非 vd）正常、`vse16.v v31`（读 vd）同样挂起、vadd+32×vs1r 正常。挂起条件 = 读 vcompress 类指令目的寄存器的向量 store。注意 emu 超时上限的进程退出码也是 0，须看日志 `Simulation timeout` 行区分。/tmp/legal2048/b10e/f/g/h/i/j/k】

## C. 已判非 bug 的分歧（备查）

- vstart≠0 普通算术：spike 行使 spec 实现许可判 illegal，Ara 退休执行——双方合法（1787 条）。
- 操作数重叠类 reserved 编码（widening/slide/vrgather/viota/vcompress/vms* 及 masked vd=v0）：spike 与 isla/Sail 判 illegal，Ara 宽松执行（1081 条，低严重度分歧）。
- vs1/vs2 LMUL 未对齐 reserved：Ara trap 合法（48 条）。
- vstart 超出 VLEN 上界（原 2048 配置下的差异；VLEN 对齐后不再出现）。
- vlm/vsm 内存映射差异（emu 1MiB 窗口 vs spike 映射）：64+37 条平台差异。

## 原创性核查汇总（GitHub pulp-platform/ara 全量 issue/PR/commit 比对，main=34bd3bc1）

| 项 | 结论 | 对应上游 |
|---|---|---|
| A1 vnclip SEW=64 崩溃 | ✅ 原创 | 无 |
| A2 vnclip 合法域数值错 | ❌ 现象已有 | issue #163（OPEN，2022-11）；根因定位为新增 |
| A3 vstart≠0 强制名单未 trap | ✅ 原创 | 无 |
| A4 vsetvli zimm 保留位 | ❌ 已有 | PR #486（OPEN 未合并） |
| A5 vmadc/vmsbc overlap 过度限制 | ⚠️ 边界 | issue #120（关闭）+ 未合并 PR #353 残留 |
| B6 向量 CSR 写丢失 | ❌ 已有 | PR #487/#488/#489（OPEN 未合并，同根精确覆盖） |
| B7 mask tail 写 1 | 非 bug（spec：mask 目的 tail 恒 agnostic）；vfmv.v.f 子项 2026-09-17 复验亦非 bug（tail 保留正确），但引出新 bug B11（vfmv.v.f SEW<64 损坏：e8 illegal、e16/e32 body 写 0） | — |
| B8a vsetivli 不钳位 | ⚠️ 合法配置（VLEN≥2048）架构性不可达，潜在缺陷；VLEN=128 证据依赖违规构建 | issue #240（OPEN，2023-09） |
| B8b rs1=x0 特例互换 | ❌ 2026-09-17 复验非 bug（与 spec 一致；VLEN=128 现象为 spike 伪差异） | — |
| B8c vsetvl rs2 保留位 | ❌ 已有 | PR #486（调用点同步修复，覆盖 rs2 路径） |
| B9 vid.v LMUL≥2 错位 | ⚠️ 归补充（#376 修复后残留证据） | issue #255（OPEN，2023-07） |
| B10 vs1r.v 挂起 | ✅ 原创（2026-09-17 合法配置复验成立：与 vstart 无关，最小= vcompress + 单条读 vd 的向量 store；vadd 不触发） | 无 |

**可提上游的干净原创项**：A1（含最小复现+一行修复）、A3、B10；有价值的新论证/补充：A2 根因分析（补 #163）、A5（e99e7b6 保留检查违反 spec）、B8a（vsetivli uimm5 路径）、B9（#376 后仍复现）。

## 2026-09-17 提交记录（gh，账号 msuadOf）

- #493 = A1 vnclip/vnclipu SEW=64 断言崩溃
- #494 = A3 vstart≠0 强制 illegal 名单未执行
- #495 = B10 读 vcompress.vm 目的寄存器的向量 store 挂起
- #496 = B11 vfmv.v.f SEW<64 恒写 0 / e8 illegal
（均在合法配置 config=2_lanes VLEN=2048 复现；正文含最小复现与 commit 34bd3bc1）
